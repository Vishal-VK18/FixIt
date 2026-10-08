"""Compatibility entry point for CampusCare image analysis."""

from typing import Any

from ai_service import analyze_image_with_ai


def analyze_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict[str, Any]:
    """Analyze an uploaded image using the configured real AI provider."""
    return analyze_image_with_ai(image_bytes, mime_type)
