"""
Gemini-based architecture analyzer for STRIDE threat modeling.

Sends cloud architecture diagram images to Google Gemini and receives
a structured STRIDE threat analysis report.

Model selection guide (set via GEMINI_MODEL env var):
  gemini-2.0-flash-lite  → default — free tier, separate quota, great for testing
  gemini-2.0-flash       → better accuracy for dense / complex diagrams
"""

import io
import json
import logging
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from PIL import Image
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Image sizing constants
# ---------------------------------------------------------------------------
# Gemini tokenises images in 768×768 pixel tiles (258 tokens each).
# Resolution vs. token budget trade-off for a typical 16:9 architecture diagram:
#
#   max_side | approx tiles | image tokens | icon readability
#   ---------|--------------|--------------|------------------
#   1024 px  |  2×2  =  4  |  ~1 032      | fair
#   1536 px  |  2×2  =  4  |  ~1 032      | good  ← chosen default
#   2048 px  |  3×2  =  6  |  ~1 548      | excellent (text labels very clear)
#   3072 px  |  4×3  = 12  |  ~3 096      | overkill for most diagrams
#
# 1536 px keeps the per-request token footprint identical to 1024 px for most
# 16:9 diagrams (still 4 tiles) while giving Gemini much more pixel data to
# read small icon labels — directly improving component identification accuracy.
#
# With Gemini 2.0 Flash-Lite's 10 M batch-enqueued-token limit and a typical
# request cost of ~1 500 tokens (image 1 032 + prompt 250 + margin):
#   estimated tests per day ≈ 10 000 000 / 1 500 ≈ 6 600
IMAGE_MAX_SIDE = 1536

# ---------------------------------------------------------------------------
# STRIDE prompt — concise but complete
# ---------------------------------------------------------------------------
STRIDE_ANALYSIS_PROMPT = """You are a cloud security expert. Analyse the architecture diagram and produce a STRIDE threat model report in Markdown.

Output exactly these five sections:

## 1. Identified Components
Table with columns: Component | Provider | Service | Role

## 2. Architecture Overview
Describe data flows, trust boundaries, internet-facing entry points, and sensitive data stores.

## 3. Threat Analysis by Component
For each component identified in section 1, evaluate all six STRIDE categories:
- **S (Spoofing)** – identity impersonation
- **T (Tampering)** – data or code modification
- **R (Repudiation)** – untracked actions / missing audit logs
- **I (Information Disclosure)** – sensitive data exposure
- **D (Denial of Service)** – resource exhaustion or availability attacks
- **E (Elevation of Privilege)** – IAM / RBAC misconfigs, container escapes

For each applicable threat, give one specific, actionable mitigation. Mark N/A if the category truly does not apply.

## 4. Mitigation Recommendations
Prioritised list of the top mitigations across the whole architecture.

## 5. Risk Summary
Table with columns: STRIDE Category | Overall Risk (Critical / High / Medium / Low) | Rationale

Be specific and reference the actual components in the image."""


# ---------------------------------------------------------------------------
# Usage tracking
# ---------------------------------------------------------------------------
_USAGE_FILE = Path("/tmp/stride_token_usage.json")
_usage_lock = threading.Lock()


@dataclass
class UsageStats:
    """Token counts returned by a single Gemini API call."""
    prompt_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


@dataclass
class SessionTokenTracker:
    """
    Accumulates token usage across requests within a calendar day.

    Persists to ``_USAGE_FILE`` so counts survive gunicorn worker restarts
    (but reset when the date changes or the file is deleted).
    """
    _totals: dict = field(default_factory=lambda: {"date": "", "prompt": 0, "output": 0, "total": 0})

    def __post_init__(self):
        self._load()

    def _today(self) -> str:
        from datetime import date
        return date.today().isoformat()

    def _load(self):
        try:
            if _USAGE_FILE.exists():
                data = json.loads(_USAGE_FILE.read_text())
                if data.get("date") == self._today():
                    self._totals = data
                    return
        except Exception:
            pass
        self._totals = {"date": self._today(), "prompt": 0, "output": 0, "total": 0}

    def add(self, usage: UsageStats):
        with _usage_lock:
            if self._totals.get("date") != self._today():
                self._load()  # new day — reset
            self._totals["prompt"] += usage.prompt_tokens
            self._totals["output"] += usage.output_tokens
            self._totals["total"] += usage.total_tokens
            try:
                _USAGE_FILE.write_text(json.dumps(self._totals))
            except Exception:
                pass

    @property
    def session_total(self) -> int:
        with _usage_lock:
            if self._totals.get("date") != self._today():
                self._load()
            return self._totals["total"]


# Module-level singleton shared across gunicorn workers via the JSON file
_tracker = SessionTokenTracker()


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------
class QuotaExceededError(Exception):
    """
    Raised when the Gemini API returns a 429 RESOURCE_EXHAUSTED error.

    Attributes:
        is_daily        – True when the per-day quota bucket is empty.
        retry_seconds   – Suggested retry delay in seconds (from the API), or None.
        consumed_tokens – Total tokens used this session (tracked locally).
    """
    def __init__(
        self,
        message: str,
        is_daily: bool = False,
        retry_seconds: Optional[int] = None,
        consumed_tokens: int = 0,
    ):
        super().__init__(message)
        self.is_daily = is_daily
        self.retry_seconds = retry_seconds
        self.consumed_tokens = consumed_tokens


# ---------------------------------------------------------------------------
# Main analyzer class
# ---------------------------------------------------------------------------
class GeminiAnalyzer:
    """
    Analyses cloud architecture images using Google Gemini and produces
    STRIDE threat model reports.

    Model selection (GEMINI_MODEL env var):
        gemini-2.0-flash-lite  – default; free-tier friendly, separate quota
        gemini-2.0-flash        – higher accuracy for complex / dense diagrams
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Args:
            api_key: Gemini API key. Reads from GEMINI_API_KEY env var if not set.
            model:   Gemini model name. Reads from GEMINI_MODEL env var if not set.
                     Defaults to 'gemini-2.0-flash-lite'.
        """
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Gemini API key is required. Set the GEMINI_API_KEY environment variable."
            )

        self.model_name = (
            model
            or os.environ.get("GEMINI_MODEL")
            or "gemini-2.0-flash-lite"
        )
        self.client = genai.Client(api_key=self.api_key)
        logger.info(f"GeminiAnalyzer initialised — model: {self.model_name}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def analyze_image(self, image_bytes: bytes, filename: str = "architecture.png") -> tuple[str, UsageStats]:
        """
        Sends an architecture image to Gemini and returns the STRIDE analysis.

        Args:
            image_bytes: Raw bytes of the image file.
            filename:    Original filename (used to detect MIME type).

        Returns:
            (report_markdown, UsageStats) tuple.

        Raises:
            QuotaExceededError: When the API returns a 429 RESOURCE_EXHAUSTED.
            RuntimeError:       For any other API failure.
        """
        # 1. Resize to cap input token usage while preserving readability
        image_bytes, mime_type = self._resize_image(image_bytes, max_side=IMAGE_MAX_SIDE)
        logger.info(f"Sending '{filename}' ({len(image_bytes):,} bytes, {mime_type}) to {self.model_name}")

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                            types.Part.from_text(text=STRIDE_ANALYSIS_PROMPT),
                        ],
                    )
                ],
                config=types.GenerateContentConfig(
                    # Low temperature → consistent, factual threat reports
                    temperature=0.2,
                    # 4 096 tokens covers a full 5-section STRIDE report with headroom
                    max_output_tokens=4096,
                    # Disable Automatic Function Calling (AFC).
                    # The SDK enables AFC by default (up to 10 chained API calls).
                    # Since this is a pure prompt+image → text flow with no tools
                    # defined, AFC can only cause extra billable requests.
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(
                        disable=True
                    ),
                ),
            )

            report = response.text

            # Capture token usage from the API response
            meta = response.usage_metadata
            usage = UsageStats(
                prompt_tokens=getattr(meta, "prompt_token_count", 0) or 0,
                output_tokens=getattr(meta, "candidates_token_count", 0) or 0,
                total_tokens=getattr(meta, "total_token_count", 0) or 0,
            )
            _tracker.add(usage)
            logger.info(
                f"Analysis complete — {len(report):,} chars | "
                f"tokens: prompt={usage.prompt_tokens}, output={usage.output_tokens}, "
                f"total={usage.total_tokens} | session_total={_tracker.session_total:,}"
            )
            return report, usage

        except Exception as e:
            self._handle_api_error(e)  # always raises

    def analyze_image_from_path(self, image_path: Path) -> tuple[str, UsageStats]:
        """Convenience method to analyse an image from a file path."""
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        return self.analyze_image(image_bytes, filename=image_path.name)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _resize_image(image_bytes: bytes, max_side: int = IMAGE_MAX_SIDE) -> tuple[bytes, str]:
        """
        Resizes an image so its longest side is at most `max_side` pixels.

        At 1536 px (default) a typical 16:9 diagram stays within 2×2 Gemini
        tiles (4 × 258 = 1 032 image tokens) while giving Gemini enough pixel
        density to read small icon labels and text annotations accurately.
        """
        img = Image.open(io.BytesIO(image_bytes))
        width, height = img.size

        if max(width, height) > max_side:
            scale = max_side / max(width, height)
            new_w, new_h = int(width * scale), int(height * scale)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            logger.info(f"Image resized: {width}×{height} → {new_w}×{new_h}")
        else:
            logger.info(f"Image {width}×{height} is within the {max_side}px limit — no resize")

        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="PNG")
        return buf.getvalue(), "image/png"

    @staticmethod
    def _handle_api_error(exc: Exception) -> None:
        """
        Inspects an API exception and re-raises it as QuotaExceededError or
        RuntimeError with a clean, actionable message.

        Always raises — never returns.
        """
        err_str = str(exc)

        # Detect 429 / RESOURCE_EXHAUSTED
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
            is_daily = "PerDay" in err_str or "per_day" in err_str.lower()

            # Try to extract the suggested retry delay (e.g. "retryDelay: 2s")
            retry_seconds: Optional[int] = None
            import re
            m = re.search(r"retryDelay.*?(\d+)s", err_str)
            if m:
                retry_seconds = int(m.group(1))

            logger.warning(f"Quota exceeded (daily={is_daily}, retry={retry_seconds}s)")
            raise QuotaExceededError(
                "quota_exceeded",
                is_daily=is_daily,
                retry_seconds=retry_seconds,
                consumed_tokens=_tracker.session_total,
            ) from exc

        # Any other API error
        logger.error(f"Gemini API call failed: {exc}")
        raise RuntimeError(f"Failed to analyse image: {exc}") from exc

    @staticmethod
    def _get_mime_type(filename: str) -> str:
        """Determines the MIME type based on file extension."""
        ext = Path(filename).suffix.lower()
        mime_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
        }
        return mime_map.get(ext, "image/png")
