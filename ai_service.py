"""Real AI vision analysis service for CampusCare maintenance issues."""

import json
import os
from typing import Any

import config
import db
from openrouter_client import request_vision

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
REQUIRED_FIELDS = {"issue", "category", "priority", "department", "suggested_fix", "is_emergency"}

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
    """Check whether the server has an OpenRouter API key configured."""
    return bool((config.OPENROUTER_API_KEY or "").strip())


def get_security_contact() -> str | None:
    """Retrieve security contact number or None if unconfigured."""
    contact = os.getenv("SECURITY_CONTACT_NUMBER", "").strip()
    return contact if contact else None


class AIAnalysisError(RuntimeError):
    """The provider response did not satisfy CampusCare's analysis contract."""


def analyze_image_with_ai(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict[str, Any]:
    """Analyze an image with OpenRouter and validate the CampusCare contract."""
    prompt = (
        "You are the CampusCare AI Diagnostic Assistant. Analyze the provided image of a university/campus facility issue.\n"
        "Return only strict JSON with exactly these six keys and no markdown or extra fields:\n"
        "{\n"
        '  "issue": "concise description of the specific damage or malfunction",\n'
        '  "category": "one of: Electrical, Plumbing, Furniture, Civil, IT/Network, Sanitation, Other",\n'
        '  "priority": "one of: LOW, MEDIUM, HIGH, CRITICAL",\n'
        '  "department": "the matching department listed below",\n'
        '  "suggested_fix": "recommended physical maintenance action protocol",\n'
        '  "is_emergency": true or false\n'
        "}\n"
        "Department mapping: " + "; ".join(f"{category}={department}" for category, department in db.DEPARTMENT_MAP.items()) + ".\n"
        "Priority rules: CRITICAL for sparks, exposed live wires, fire, flooding, water near electricity, or immediate safety hazards; HIGH for essential service failure, active damage, or major electrical/plumbing failure; MEDIUM for broken but usable equipment or normal maintenance; LOW for minor/cosmetic issues. Any fire, sparks, flooding, exposed electrical hazard, or immediate safety hazard MUST set is_emergency=true and priority=CRITICAL."
    )

    raw_response_text = request_vision(prompt, image_bytes, mime_type)
    try:
        parsed = json.loads(raw_response_text)
    except json.JSONDecodeError as exc:
        raise AIAnalysisError("OpenRouter returned malformed JSON. Please retry the image analysis.") from exc

    if not isinstance(parsed, dict) or set(parsed) != REQUIRED_FIELDS:
        raise AIAnalysisError("OpenRouter response must contain exactly the required CampusCare fields.")
    if not all(isinstance(parsed[key], str) and parsed[key].strip() for key in ("issue", "category", "priority", "department", "suggested_fix")) or not isinstance(parsed["is_emergency"], bool):
        raise AIAnalysisError("OpenRouter response contains invalid CampusCare field values.")
    issue = parsed["issue"].strip()
    category = parsed["category"].strip()
    if category not in CATEGORIES:
        raise AIAnalysisError("OpenRouter response contains an invalid category.")

    priority = parsed["priority"].strip().upper()
    if priority not in PRIORITIES:
        raise AIAnalysisError("OpenRouter response contains an invalid priority.")

    department = db.DEPARTMENT_MAP[category]
    if parsed["department"].strip() != department:
        raise AIAnalysisError("OpenRouter response contains an invalid department.")

    suggested_fix = parsed["suggested_fix"].strip()
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
        "department": department,
        "suggested_fix": suggested_fix,
        "is_emergency": is_emergency,
    }
