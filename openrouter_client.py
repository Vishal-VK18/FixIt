"""OpenRouter chat-completions client for CampusCare image analysis."""

import base64
from io import BytesIO
import logging
import time

import httpx
from PIL import Image, ImageOps

import config

logger = logging.getLogger("fixit.openrouter")
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
MAX_IMAGE_SIDE = 2560
MAX_IMAGE_BYTES = 4 * 1024 * 1024
MAX_ATTEMPTS = 2


class OpenRouterError(RuntimeError):
    """Safe user-facing error raised for OpenRouter request failures."""

    def __init__(self, message: str, status_code: int = 502, configured: bool = True):
        super().__init__(message)
        self.status_code = status_code
        self.configured = configured


def prepare_image(image_bytes: bytes, mime_type: str) -> tuple[bytes, str]:
    """Validate MIME against the image and reduce only oversized uploads."""
    try:
        with Image.open(BytesIO(image_bytes)) as source:
            detected_mime = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}.get(source.format or "")
            if detected_mime and max(source.size) <= MAX_IMAGE_SIDE and len(image_bytes) <= MAX_IMAGE_BYTES:
                logger.info("OpenRouter image ready bytes=%d mime=%s dimensions=%dx%d", len(image_bytes), detected_mime, *source.size)
                return image_bytes, detected_mime

            image = ImageOps.exif_transpose(source)
            image.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE), Image.Resampling.LANCZOS)
            if "A" in image.getbands():
                rgba = image.convert("RGBA")
                rgb = Image.new("RGB", rgba.size, "white")
                rgb.paste(rgba, mask=rgba.getchannel("A"))
                image = rgb
            else:
                image = image.convert("RGB")
            jpeg, png = BytesIO(), BytesIO()
            image.save(jpeg, format="JPEG", quality=90, optimize=True)
            image.save(png, format="PNG", optimize=True)
            result, result_mime = (png.getvalue(), "image/png") if len(png.getvalue()) < len(jpeg.getvalue()) else (jpeg.getvalue(), "image/jpeg")
    except Exception as exc:
        raise OpenRouterError("The uploaded image could not be prepared for analysis.", 400) from exc

    logger.info("OpenRouter image prepared source_bytes=%d request_bytes=%d mime=%s dimensions=%dx%d", len(image_bytes), len(result), result_mime, *image.size)
    return result, result_mime


def request_vision(prompt: str, image_bytes: bytes, mime_type: str) -> str:
    """Send the prompt and actual image to OpenRouter, retrying transient failures once."""
    api_key = (config.OPENROUTER_API_KEY or "").strip()
    if not api_key:
        raise OpenRouterError("AI analysis is not configured. Set OPENROUTER_API_KEY in the server .env file.", 400, configured=False)

    image_bytes, mime_type = prepare_image(image_bytes, mime_type)
    model = config.OPENROUTER_MODEL.strip()
    timeout_seconds = config.OPENROUTER_TIMEOUT_SECONDS
    timeout = httpx.Timeout(timeout_seconds, connect=min(10.0, timeout_seconds))
    image_url = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": image_url}},
        ]}],
        "response_format": {"type": "json_object"},
    }

    for attempt in range(1, MAX_ATTEMPTS + 1):
        started = time.monotonic()
        logger.info("OpenRouter request started attempt=%d/%d model=%s image_bytes=%d mime=%s timeout_seconds=%s", attempt, MAX_ATTEMPTS, model, len(image_bytes), mime_type, timeout_seconds)
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(ENDPOINT, json=payload, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "HTTP-Referer": "https://campuscare.local", "X-Title": "CampusCare"})
        except httpx.TimeoutException as exc:
            logger.warning("OpenRouter request timed out attempt=%d duration_seconds=%.2f", attempt, time.monotonic() - started)
            if attempt < MAX_ATTEMPTS:
                time.sleep(1)
                continue
            raise OpenRouterError("OpenRouter image analysis timed out. Please try again with a smaller image or check the AI service connection.", 504) from exc
        except httpx.NetworkError as exc:
            logger.warning("OpenRouter connection failed attempt=%d error_type=%s", attempt, type(exc).__name__)
            if attempt < MAX_ATTEMPTS:
                time.sleep(1)
                continue
            raise OpenRouterError("Unable to reach OpenRouter. Check the AI service connection and try again.", 503) from exc

        status = response.status_code
        logger.info("OpenRouter request completed attempt=%d status=%d duration_seconds=%.2f", attempt, status, time.monotonic() - started)
        if status in (401, 403):
            raise OpenRouterError("OpenRouter API key authentication failed. Check OPENROUTER_API_KEY.", 401)
        if status == 429:
            if attempt < MAX_ATTEMPTS:
                retry_after = response.headers.get("Retry-After", "")
                try:
                    delay = float(retry_after) if retry_after else 5.0
                except ValueError:
                    delay = 5.0
                if 0 <= delay <= 30:
                    time.sleep(max(5.0, delay))
                    continue
            raise OpenRouterError("OpenRouter rate limit reached. Please wait and try again.", 429)
        if 500 <= status < 600:
            if attempt < MAX_ATTEMPTS:
                time.sleep(1)
                continue
            raise OpenRouterError("OpenRouter service is temporarily unavailable. Please try again shortly.", 502)
        if status != 200:
            logger.error("OpenRouter rejected request status=%d", status)
            raise OpenRouterError("OpenRouter rejected the image-analysis request. Check the model and image configuration.", 400)

        try:
            content = response.json()["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError("empty content")
            return content
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            logger.warning("OpenRouter returned an invalid response structure")
            raise OpenRouterError("OpenRouter returned an invalid analysis response. Please try again.", 502) from exc

    raise OpenRouterError("OpenRouter service is temporarily unavailable. Please try again shortly.", 502)
