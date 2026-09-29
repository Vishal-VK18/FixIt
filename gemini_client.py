"""Shared, bounded Gemini REST client for image analysis."""

import base64
from io import BytesIO
import logging
import time

import httpx
from PIL import Image, ImageOps

import config

logger = logging.getLogger("fixit.gemini")
MODEL = "gemini-3.8-flash"
MAX_IMAGE_SIDE = 2560
MAX_IMAGE_BYTES = 4 * 1024 * 1024
MAX_ATTEMPTS = 2


class GeminiVisionError(RuntimeError):
    """Safe user-facing error raised for Gemini request failures."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def _timeout_seconds() -> float:
    return config.GEMINI_TIMEOUT_SECONDS


def prepare_image(image_bytes: bytes, mime_type: str) -> tuple[bytes, str]:
    """Validate MIME against the actual image, resizing/compressing large uploads."""
    try:
        with Image.open(BytesIO(image_bytes)) as source:
            detected_mime = {
                "JPEG": "image/jpeg",
                "PNG": "image/png",
                "WEBP": "image/webp",
            }.get(source.format or "")
            if detected_mime and max(source.size) <= MAX_IMAGE_SIDE and len(image_bytes) <= MAX_IMAGE_BYTES:
                logger.info(
                    "Gemini image ready source_bytes=%d request_bytes=%d source_mime=%s request_mime=%s dimensions=%dx%d",
                    len(image_bytes), len(image_bytes), mime_type, detected_mime, *source.size,
                )
                return image_bytes, detected_mime

            image = ImageOps.exif_transpose(source)
            image.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE), Image.Resampling.LANCZOS)
            if "A" in image.getbands():
                rgba = image.convert("RGBA")
                background = Image.new("RGB", rgba.size, "white")
                background.paste(rgba, mask=rgba.getchannel("A"))
                image = background
            else:
                image = image.convert("RGB")
            jpeg = BytesIO()
            image.save(jpeg, format="JPEG", quality=90, optimize=True)
            png = BytesIO()
            image.save(png, format="PNG", optimize=True)
            if len(png.getvalue()) < len(jpeg.getvalue()):
                result, result_mime = png.getvalue(), "image/png"
            else:
                result, result_mime = jpeg.getvalue(), "image/jpeg"
    except Exception as exc:
        raise GeminiVisionError("The uploaded image could not be prepared for Gemini Vision.") from exc

    logger.info(
        "Gemini image prepared source_bytes=%d request_bytes=%d source_mime=%s request_mime=%s dimensions=%dx%d",
        len(image_bytes), len(result), mime_type, result_mime, *image.size,
    )
    return result, result_mime


def generate_content(prompt: str, image_bytes: bytes, mime_type: str) -> str:
    """Send one image and prompt to Gemini, retrying at most once when transient."""
    api_key = (config.GEMINI_API_KEY or "").strip()
    if not api_key:
        raise GeminiVisionError("AI analysis is not configured. Set GEMINI_API_KEY in the server .env file.")

    image_bytes, mime_type = prepare_image(image_bytes, mime_type)
    timeout_seconds = _timeout_seconds()
    model = (config.GEMINI_MODEL or MODEL).strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "contents": [{"parts": [
            {"text": prompt},
            {"inlineData": {"mimeType": mime_type, "data": base64.b64encode(image_bytes).decode("ascii")}},
        ]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    timeout = httpx.Timeout(timeout_seconds, connect=min(10.0, timeout_seconds))

    for attempt in range(1, MAX_ATTEMPTS + 1):
        started = time.monotonic()
        logger.info(
            "Gemini request started attempt=%d/%d model=%s image_bytes=%d mime=%s timeout_seconds=%s",
            attempt, MAX_ATTEMPTS, model, len(image_bytes), mime_type, timeout_seconds,
        )
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(url, json=payload, headers={"x-goog-api-key": api_key})
        except httpx.TimeoutException as exc:
            elapsed = time.monotonic() - started
            logger.warning(
                "Gemini request timed out attempt=%d duration_seconds=%.2f error=%s",
                attempt, elapsed, exc,
            )
            if attempt < MAX_ATTEMPTS:
                time.sleep(1)
                continue
            raise GeminiVisionError(
                "Gemini Vision analysis timed out. Please try again with a smaller image or check the AI service connection.",
                504,
            ) from exc
        except httpx.NetworkError as exc:
            elapsed = time.monotonic() - started
            logger.warning(
                "Gemini connection failed attempt=%d duration_seconds=%.2f error_type=%s error=%s",
                attempt, elapsed, type(exc).__name__, exc,
            )
            if attempt < MAX_ATTEMPTS:
                time.sleep(1)
                continue
            raise GeminiVisionError("Unable to reach Gemini service. Check the AI service connection and try again.", 503) from exc

        duration = time.monotonic() - started
        status = response.status_code
        logger.info("Gemini request completed attempt=%d status=%d duration_seconds=%.2f", attempt, status, duration)
        if status in (401, 403):
            raise GeminiVisionError("Gemini API key authentication failed. Check GEMINI_API_KEY.")
        if status == 404:
            raise GeminiVisionError("Gemini model is unavailable. Check GEMINI_MODEL.")
        if status == 429:
            if attempt < MAX_ATTEMPTS:
                time.sleep(1)
                continue
            raise GeminiVisionError("Gemini rate limit reached. Please wait and try again.", 429)
        if 500 <= status < 600:
            if attempt < MAX_ATTEMPTS:
                time.sleep(1)
                continue
            raise GeminiVisionError("Gemini service is temporarily unavailable. Please try again shortly.")
        if status != 200:
            logger.error("Gemini rejected request status=%d", status)
            raise GeminiVisionError("Gemini rejected the image-analysis request. Check the image and model configuration.")

        try:
            parts = response.json()["candidates"][0]["content"]["parts"]
            return "".join(part["text"] for part in parts if "text" in part)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            logger.exception("Gemini returned an invalid response structure")
            raise GeminiVisionError("Gemini returned an invalid analysis response. Please try again.") from exc

    raise GeminiVisionError("Gemini service is temporarily unavailable. Please try again shortly.")
