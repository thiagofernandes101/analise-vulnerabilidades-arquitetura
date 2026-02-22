"""
Gemini-based architecture analyzer for STRIDE threat modeling.

Sends cloud architecture diagram images to Google Gemini and receives
a structured STRIDE threat analysis report.
"""

import io
import logging
import os
from pathlib import Path
from typing import Optional

from PIL import Image
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# The prompt instructs Gemini to perform STRIDE analysis on the architecture.
# Kept intentionally concise to minimise token usage on the free tier.
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


class GeminiAnalyzer:
    """
    Analyzes cloud architecture images using Google Gemini
    and produces STRIDE threat model reports.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.0-flash-lite"):
        """
        Args:
            api_key: Gemini API key. If not provided, reads from GEMINI_API_KEY env var.
            model: Gemini model to use for analysis.
        """
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Gemini API key is required. Set the GEMINI_API_KEY environment variable "
                "or pass it directly to GeminiAnalyzer."
            )

        self.model_name = model
        self.client = genai.Client(api_key=self.api_key)
        logger.info(f"GeminiAnalyzer initialized with model: {self.model_name}")

    def analyze_image(self, image_bytes: bytes, filename: str = "architecture.png") -> str:
        """
        Sends an architecture image to Gemini and returns the STRIDE analysis.

        Args:
            image_bytes: Raw bytes of the image file.
            filename: Original filename (used to detect MIME type).

        Returns:
            Markdown-formatted STRIDE threat model report.
        """
        # Determine MIME type from filename
        mime_type = self._get_mime_type(filename)

        # Resize image to reduce input token usage
        image_bytes, mime_type = self._resize_image(image_bytes, max_side=1024)

        logger.info(f"Analyzing image '{filename}' ({len(image_bytes)} bytes, {mime_type})")

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
                    temperature=0.2,  # Lower temperature for factual, deterministic analysis
                    max_output_tokens=4096,  # Capped to reduce token consumption on free tier
                ),
            )

            report = response.text
            logger.info(f"Analysis complete. Report length: {len(report)} characters")
            return report

        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            raise RuntimeError(f"Failed to analyze image: {e}") from e

    def analyze_image_from_path(self, image_path: Path) -> str:
        """
        Convenience method to analyze an image from a file path.

        Args:
            image_path: Path to the image file.

        Returns:
            Markdown-formatted STRIDE threat model report.
        """
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        with open(image_path, "rb") as f:
            image_bytes = f.read()

        return self.analyze_image(image_bytes, filename=image_path.name)

    @staticmethod
    def _resize_image(image_bytes: bytes, max_side: int = 1024) -> tuple[bytes, str]:
        """
        Resizes an image so its longest side is at most `max_side` pixels.

        Gemini tokenises images in 768×768 tiles (258 tokens each). Keeping
        the image small (≤1024px) ensures at most ~4 tiles (~1032 tokens)
        instead of 20+ tiles for a large hi-res diagram, significantly
        reducing free-tier input token consumption.

        Args:
            image_bytes: Raw image bytes.
            max_side: Maximum pixels on the longest dimension.

        Returns:
            Tuple of (resized_bytes, mime_type). Always re-encodes as PNG.
        """
        img = Image.open(io.BytesIO(image_bytes))
        width, height = img.size

        if max(width, height) > max_side:
            scale = max_side / max(width, height)
            new_size = (int(width * scale), int(height * scale))
            img = img.resize(new_size, Image.LANCZOS)
            logger.info(f"Image resized from {width}×{height} to {new_size[0]}×{new_size[1]}")
        else:
            logger.info(f"Image dimensions {width}×{height} are within limit, no resize needed")

        # Re-encode to PNG in memory
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="PNG")
        return buf.getvalue(), "image/png"

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
