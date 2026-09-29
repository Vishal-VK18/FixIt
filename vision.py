"""AI Vision Analysis Module for FixIt Campus Maintenance.

Provides image analysis using Google Gemini,
validates and normalizes responses, applies application-side emergency
overrides, maps categories to departments, and returns safe fallbacks on failure.
"""

import io
import json
import logging
import os
import re
from typing import Any, Dict, Optional, Tuple

from PIL import Image

import config
from gemini_client import generate_content

logger = logging.getLogger("fixit.vision")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("[%(asctime)s] [%(levelname)s] fixit.vision: %(message)s")
    )
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Vision Prompt with Strict Urgency and Schema Rules
VISION_SYSTEM_PROMPT = """You are an expert campus maintenance inspector AI for a university facility management system.
Analyze the provided image of a campus maintenance issue.

Evaluate the urgency based on these strict rules:
- CRITICAL: Immediate safety hazards such as fire, sparks, electrical arcing, exposed live electrical wires, water near electrical equipment, flooding creating safety hazards, or other clearly dangerous situations. Do NOT downgrade an obvious safety emergency!
- HIGH: Loss of essential services, active water leakage, active damage, major electrical failure without immediate emergency, or problems that can rapidly become dangerous.
- MEDIUM: Broken furniture that is still usable, non-critical equipment failures, functional problems that do not immediately threaten safety.
- LOW: Minor defects, cosmetic damage, peeling paint, small non-urgent maintenance problems.

You MUST respond ONLY with a raw, valid JSON object without markdown code fences, backticks, or any conversational text.
Your JSON must strictly adhere to this schema:
{
  "issue": "Short description of the problem",
  "category": "Electrical | Plumbing | Furniture | Civil | IT/Network | Sanitation | Other",
  "priority": "LOW | MEDIUM | HIGH | CRITICAL",
  "suggested_fix": "Recommended action",
  "is_emergency": false
}
"""

# Normalized category mappings
CATEGORY_NORMALIZATION_MAP = {
    "electrical": "Electrical",
    "electric": "Electrical",
    "wiring": "Electrical",
    "plumbing": "Plumbing",
    "plumber": "Plumbing",
    "water": "Plumbing",
    "leak": "Plumbing",
    "leakage": "Plumbing",
    "furniture": "Furniture",
    "chair": "Furniture",
    "desk": "Furniture",
    "table": "Furniture",
    "civil": "Civil",
    "structure": "Civil",
    "wall": "Civil",
    "paint": "Civil",
    "masonry": "Civil",
    "it/network": "IT/Network",
    "it": "IT/Network",
    "network": "IT/Network",
    "wifi": "IT/Network",
    "internet": "IT/Network",
    "computer": "IT/Network",
    "sanitation": "Sanitation",
    "hygiene": "Sanitation",
    "cleaning": "Sanitation",
    "restroom": "Sanitation",
    "trash": "Sanitation",
    "garbage": "Sanitation",
    "other": "Other",
}

# Normalized priority mappings
PRIORITY_NORMALIZATION_MAP = {
    "low": "LOW",
    "medium": "MEDIUM",
    "med": "MEDIUM",
    "normal": "MEDIUM",
    "high": "HIGH",
    "critical": "CRITICAL",
    "urgent": "CRITICAL",
    "emergency": "CRITICAL",
}


def get_safe_fallback(custom_issue: Optional[str] = None) -> Dict[str, Any]:
    """Return a guaranteed valid fallback analysis result."""
    fallback = config.DEFAULT_FALLBACK_RESULT.copy()
    if custom_issue:
        fallback["issue"] = custom_issue
    fallback["department"] = config.DEPARTMENT_MAP.get(
        fallback["category"], "General Maintenance"
    )
    return fallback


def validate_image_bytes(photo_bytes: Any) -> Tuple[bool, str, Optional[str]]:
    """Validate image bytes, checking format, readability, and file size.

    Returns:
        (is_valid, error_message, mime_type)
    """
    if not photo_bytes:
        return False, "No image data provided.", None

    if not isinstance(photo_bytes, (bytes, bytearray)):
        return False, "Image input must be bytes or bytearray.", None

    if len(photo_bytes) == 0:
        return False, "Image data is empty (0 bytes).", None

    if len(photo_bytes) > config.MAX_FILE_SIZE_BYTES:
        return (
            False,
            f"Image file size exceeds maximum allowed {config.MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB.",
            None,
        )

    try:
        image = Image.open(io.BytesIO(photo_bytes))
        image.verify()  # Fast structural verification

        # Re-open after verify() because verify() invalidates the image handle
        image = Image.open(io.BytesIO(photo_bytes))
        img_format = (image.format or "JPEG").upper()

        format_to_mime = {
            "JPEG": "image/jpeg",
            "JPG": "image/jpeg",
            "PNG": "image/png",
            "WEBP": "image/webp",
        }
        mime_type = format_to_mime.get(img_format)
        if not mime_type:
            # Attempt to convert or handle as jpeg
            mime_type = "image/jpeg"

        return True, "", mime_type
    except Exception as exc:
        logger.warning("Image verification failed: %s", exc)
        return False, f"Invalid or corrupt image format: {exc}", None


def detect_emergency_override(result: Dict[str, Any]) -> bool:
    """Application-side emergency detection.

    Inspects issue, suggested fix, and category for safety hazard markers:
    - fire (fire, flames, burning)
    - sparks (sparks, sparking, electrical arcing, arcing)
    - exposed electrical wires (exposed live wires, bare wires)
    - flooding (flooding, flooded, severe flood)
    - water near electricity (water leaking near electrical socket, outlet, etc.)

    Returns True if an immediate emergency hazard is identified.
    """
    text_to_scan = (
        f"{result.get('issue', '')} {result.get('suggested_fix', '')} {result.get('category', '')}"
    ).lower()

    # 1. Fire / burning hazards
    if re.search(r"\b(fire|flames?|burning)\b", text_to_scan):
        return True

    # 2. Electrical sparks / arcing hazards
    if re.search(r"\b(sparks?|sparking|electrical arcing|electric arc|arcing)\b", text_to_scan):
        return True

    # 3. Exposed electrical wires
    if re.search(
        r"\b(exposed|bare|live)\s+(?:electrical\s+|live\s+)?(?:wires?|wiring|cables?)\b",
        text_to_scan,
    ):
        return True
    if "exposed wire" in text_to_scan or "bare wire" in text_to_scan or "exposed electrical" in text_to_scan:
        return True

    # 4. Flooding hazards
    if re.search(r"\b(flooding|flooded|severe flood)\b", text_to_scan):
        return True

    # 5. Water near electricity / electrical sockets / panels
    if re.search(
        r"\b(water|leak|leaking|leakage|flooding)\b.*?\b(near|around|on|at|touching|beside)\b.*?\b(electr\w*|socket|outlet|switchboard|power|panel|wire|breaker)\b",
        text_to_scan,
    ):
        return True
    if re.search(
        r"\b(electr\w*|socket|outlet|switchboard|power|panel|wire|breaker)\b.*?\b(near|under|touching|in)\b.*?\b(water|leak|leaking|leakage|flood)\b",
        text_to_scan,
    ):
        return True

    # 6. Check any specific keywords from config
    for keyword in config.EMERGENCY_KEYWORDS:
        pattern = r"\b" + re.escape(keyword) + r"\b"
        if re.search(pattern, text_to_scan, re.IGNORECASE) or keyword in text_to_scan:
            return True

    return False


def validate_and_normalize_result(raw_data: Any) -> Dict[str, Any]:
    """Parse, validate, and normalize the raw LLM output.

    Handles:
    - JSON strings with markdown code fences
    - Raw dicts
    - Missing or malformed fields
    - Invalid categories and priorities
    - Application-side emergency detection
    - Deterministic department assignment
    """
    parsed: Dict[str, Any] = {}

    if isinstance(raw_data, dict):
        parsed = raw_data
    elif isinstance(raw_data, str):
        # Strip markdown fences and search for JSON block
        cleaned_text = raw_data.strip()
        cleaned_text = re.sub(
            r"^```(?:json)?\s*", "", cleaned_text, flags=re.IGNORECASE
        )
        cleaned_text = re.sub(r"\s*```$", "", cleaned_text)

        # Extract first JSON object substring if surrounded by extra text
        match = re.search(r"(\{.*\})", cleaned_text, re.DOTALL)
        if match:
            cleaned_text = match.group(1)

        try:
            parsed = json.loads(cleaned_text)
            if not isinstance(parsed, dict):
                logger.warning(
                    "Parsed JSON is not an object: %s", type(parsed)
                )
                return get_safe_fallback()
        except Exception as exc:
            logger.warning("Failed to decode JSON from model response: %s", exc)
            return get_safe_fallback()
    else:
        logger.warning("Unsupported response data type: %s", type(raw_data))
        return get_safe_fallback()

    # 1. Normalize Issue
    issue = str(parsed.get("issue") or "").strip()
    if not issue:
        issue = "Unspecified campus maintenance issue"

    # 2. Normalize Category
    raw_cat = str(parsed.get("category") or "").strip().lower()
    category = CATEGORY_NORMALIZATION_MAP.get(raw_cat)
    if not category:
        # Attempt partial match
        for key, val in CATEGORY_NORMALIZATION_MAP.items():
            if key in raw_cat:
                category = val
                break
    if not category or category not in config.CATEGORIES:
        category = "Other"

    # 3. Normalize Priority
    raw_pri = str(parsed.get("priority") or "").strip().lower()
    priority = PRIORITY_NORMALIZATION_MAP.get(raw_pri)
    if not priority or priority not in config.PRIORITIES:
        priority = "MEDIUM"

    # 4. Normalize Suggested Fix
    suggested_fix = str(parsed.get("suggested_fix") or "").strip()
    if not suggested_fix:
        suggested_fix = "Maintenance staff should inspect the reported issue."

    # 5. Normalize is_emergency
    raw_emergency = parsed.get("is_emergency")
    if isinstance(raw_emergency, bool):
        is_emergency = raw_emergency
    elif isinstance(raw_emergency, str):
        is_emergency = raw_emergency.strip().lower() in ("true", "1", "yes")
    elif isinstance(raw_emergency, (int, float)):
        is_emergency = bool(raw_emergency)
    else:
        is_emergency = False

    validated = {
        "issue": issue,
        "category": category,
        "priority": priority,
        "suggested_fix": suggested_fix,
        "is_emergency": is_emergency,
    }

    # 6. APPLICATION-SIDE EMERGENCY OVERRIDE (Section 3)
    # If the text identifies fire, sparks, exposed electrical wires, flooding,
    # or water near electricity, force priority = CRITICAL and is_emergency = true
    if detect_emergency_override(validated):
        logger.info("Emergency override triggered based on hazard detection.")
        validated["priority"] = "CRITICAL"
        validated["is_emergency"] = True
    elif is_emergency and validated["priority"] != "CRITICAL":
        validated["priority"] = "CRITICAL"

    # 7. DETERMINISTIC DEPARTMENT MAPPING (Section 4)
    validated["department"] = config.DEPARTMENT_MAP.get(
        validated["category"], "General Maintenance"
    )

    return validated


def _call_gemini_vision(
    photo_bytes: bytes, mime_type: str
) -> Optional[Dict[str, Any]]:
    """Call Google Gemini Vision API via direct REST endpoint."""
    api_key = config.GEMINI_API_KEY
    if not api_key:
        return None

    text_content = generate_content(VISION_SYSTEM_PROMPT, photo_bytes, mime_type)
    return validate_and_normalize_result(text_content)


def analyze_image(photo_bytes: bytes) -> Dict[str, Any]:
    is_valid, err_msg, mime_type = validate_image_bytes(photo_bytes)
    if not is_valid:
        raise ValueError(err_msg)
    if not config.GEMINI_API_KEY:
        raise ValueError("AI analysis is not configured. Set GEMINI_API_KEY in the server .env file.")
    result = _call_gemini_vision(photo_bytes, mime_type or "image/jpeg")
    if result is None:
        raise RuntimeError("Gemini Vision analysis failed. Check the server logs and API configuration.")
    return result
