"""
STRIDE Threat Analyzer — Flask Web Application

A web application that accepts cloud architecture diagram images and
generates STRIDE threat model reports using Google Gemini.
"""

import logging
import sys
import os

from flask import Flask, render_template, request, jsonify
import markdown

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("stride_analyzer")

# Create Flask app
app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "static"),
)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max upload

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "bmp"}


def allowed_file(filename: str) -> bool:
    """Check if the file extension is allowed."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    """Serve the main upload page."""
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    """
    Receive an architecture image, send it to Gemini for STRIDE analysis,
    and return the report as HTML.
    """
    # Validate that a file was uploaded
    if "image" not in request.files:
        return jsonify({"error": "No image file provided."}), 400

    file = request.files["image"]

    if file.filename == "" or file.filename is None:
        return jsonify({"error": "No file selected."}), 400

    if not allowed_file(file.filename):
        return jsonify({
            "error": f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        }), 400

    try:
        # Lazy import to defer API key validation until first request
        from src.services.gemini_analyzer import GeminiAnalyzer

        # Read the image bytes
        image_bytes = file.read()
        logger.info(f"Received image: {file.filename} ({len(image_bytes)} bytes)")

        # Analyze the image with Gemini
        analyzer = GeminiAnalyzer()
        report_md = analyzer.analyze_image(image_bytes, filename=file.filename)

        # Convert Markdown to HTML for display
        report_html = markdown.markdown(
            report_md,
            extensions=["tables", "fenced_code", "nl2br"],
        )

        return jsonify({
            "report_html": report_html,
            "report_md": report_md,
        })

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return jsonify({"error": str(e)}), 500

    except RuntimeError as e:
        logger.error(f"Analysis error: {e}")
        return jsonify({"error": str(e)}), 500

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


if __name__ == "__main__":
    # Local development mode
    app.run(host="0.0.0.0", port=5000, debug=True)
