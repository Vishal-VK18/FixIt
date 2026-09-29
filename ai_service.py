"""Real AI vision analysis service for CampusCare maintenance issues."""

import json
import os
import re
from typing import Any

from dotenv import load_dotenv

load_dotenv()

import db
from gemini_client import generate_content

CATEGORIES = (
    "Electrical",
    "Plumbing",
    "Furniture",
    "Civil",
    "IT/Network",
    "Sanitation",
    "Other",
)

PRIORITIES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")

EMERGENCY_KEYWORDS = [
    "fire",
    "flooding",
    "water near electricity",
    "water near electrical equipment",
    "exposed electrical wire",
    "spark",
    "sparks",
    "smoke",
    "burning",
    "explosion",
    "exposed wire",
    "exposed live wire",
    "bare wire",
    "electrical shock",
    "flooding near electricity",
    "gas leak",
    "structural collapse",
    "hazardous chemical",
]


def is_ai_configured() -> bool:
    """Check whether the server has a Gemini API key configured."""
    return bool(os.getenv("GEMINI_API_KEY", "").strip())


def get_security_contact() -> str | None:
    """Retrieve security contact number or None if unconfigured."""
    contact = os.getenv("SECURITY_CONTACT_NUMBER", "").strip()
    return contact if contact else None


def analyze_image_with_ai(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict[str, Any]:
    """Analyze image using Google's Gemini API.
    
    If unconfigured, raises ValueError with required spec message.
    Never returns fake or fabricated data.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    if not api_key:
        raise ValueError("AI analysis is not configured. Set GEMINI_API_KEY in the server .env file.")

    prompt = (
        "You are the CampusCare AI Diagnostic Assistant. Analyze the provided image of a university/campus facility issue.\n"
        "Identify the core problem, categorize it, determine the severity priority, suggest an actionable fix, and detect if this is a severe safety hazard.\n\n"
        "Return ONLY a valid JSON object with these exact keys:\n"
        "{\n"
        '  "issue": "concise description of the specific damage or malfunction",\n'
        '  "category": "one of: Electrical, Plumbing, Furniture, Civil, IT/Network, Sanitation, Other",\n'
        '  "priority": "one of: LOW, MEDIUM, HIGH, CRITICAL",\n'
        '  "suggested_fix": "recommended physical maintenance action protocol",\n'
        '  "is_emergency": true or false (true if active fire, sparks, bare live wiring, severe flooding near power, or imminent personal injury danger)\n'
        "}\n\n"
        "Urgency rules: CRITICAL for fire, sparks, exposed live wires, flooding or water near electricity, or immediate danger; HIGH for loss of an essential service or active damage; MEDIUM for broken but usable items; LOW for minor cosmetic issues. If is_emergency is true, priority MUST be CRITICAL."
    )

    raw_response_text = generate_content(prompt, image_bytes, mime_type)

    # Parse JSON output from model
    clean_json = raw_response_text.strip()
    if "```" in clean_json:
        # Extract markdown json block
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", clean_json, re.DOTALL)
        if match:
            clean_json = match.group(1)

    try:
        parsed = json.loads(clean_json)
    except json.JSONDecodeError:
        raise RuntimeError(f"AI response could not be parsed as JSON: {raw_response_text[:120]}")

    if not isinstance(parsed, dict) or any(
        key not in parsed for key in ("issue", "category", "priority", "suggested_fix", "is_emergency")
    ):
        raise RuntimeError("AI response is missing one or more required fields.")
    if not all(isinstance(parsed[key], str) and parsed[key].strip() for key in ("issue", "category", "priority", "suggested_fix")) or not isinstance(parsed["is_emergency"], bool):
        raise RuntimeError("AI response contains invalid field values.")
    issue = parsed["issue"].strip()
    category = str(parsed.get("category", "Other")).strip()
    if category not in CATEGORIES:
        raise RuntimeError("AI response contains an invalid category.")

    priority = str(parsed.get("priority", "MEDIUM")).strip().upper()
    if priority not in PRIORITIES:
        raise RuntimeError("AI response contains an invalid priority.")

    suggested_fix = str(parsed.get("suggested_fix", "")).strip()
    is_emergency = parsed["is_emergency"]

    # Detect keyword-based emergency hazards as required by section 12
    combined_text = f"{issue} {suggested_fix}".lower()
    for kw in EMERGENCY_KEYWORDS:
        if kw in combined_text:
            is_emergency = True
            priority = "CRITICAL"
            break

    if is_emergency:
        priority = "CRITICAL"

    return {
        "issue": issue,
        "category": category,
        "priority": priority,
        "department": db.DEPARTMENT_MAP[category],
        "suggested_fix": suggested_fix,
        "is_emergency": is_emergency,
    }
