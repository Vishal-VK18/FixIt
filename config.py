"""Configuration settings for FixIt Campus Maintenance Application.

Contains campus configuration, security contacts, priority levels,
department mappings, and AI vision settings.
"""

import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Database Configuration
DATABASE_PATH = os.environ.get("DATABASE_PATH", str(BASE_DIR / "fixit.db"))

# Security & Campus Emergency Contacts
SECURITY_CONTACT_NUMBER = os.environ.get(
    "SECURITY_CONTACT_NUMBER",
    "Campus Security: (555) 123-SAFE / +1-555-019-4321",
)

# Campus Blocks
BLOCKS = [
    "Block A - Humanities & Arts",
    "Block B - Sciences & Computing",
    "Block C - Engineering Hall",
    "Block D - Management Studies",
    "Block E - Architecture & Design",
    "Central Library",
    "Student Center & Recreation",
    "Hostel 1 - North Wing",
    "Hostel 2 - South Wing",
    "Sports Complex",
    "Dining Hall & Cafeteria",
]

# Supported Maintenance Categories
CATEGORIES = [
    "Electrical",
    "Plumbing",
    "Furniture",
    "Civil",
    "IT/Network",
    "Sanitation",
    "Other",
]

# Maintenance Priority Levels
PRIORITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

# Category to Department Deterministic Mapping
DEPARTMENT_MAP = {
    "Electrical": "Electrical Department",
    "Plumbing": "Plumbing Department",
    "Furniture": "Furniture Department",
    "Civil": "Civil Department",
    "IT/Network": "IT Department",
    "Sanitation": "Sanitation Department",
    "Other": "General Maintenance",
}

# Standard Safe Fallback Analysis Result
DEFAULT_FALLBACK_RESULT = {
    "issue": "Unable to automatically identify the issue",
    "category": "Other",
    "priority": "MEDIUM",
    "suggested_fix": "Maintenance staff should inspect the reported issue.",
    "is_emergency": False,
    "department": "General Maintenance",
}

# Application-Side Emergency Keywords / Patterns
EMERGENCY_KEYWORDS = [
    "fire",
    "flame",
    "burning",
    "spark",
    "sparking",
    "sparks",
    "electrical arcing",
    "electric arc",
    "arcing",
    "exposed live",
    "exposed wire",
    "exposed electrical",
    "bare wire",
    "bare live",
    "flooding",
    "flooded",
    "severe flood",
    "water near electrical",
    "water near electricity",
    "water near socket",
    "water near outlet",
    "water near switch",
    "water near power",
    "submerged electrical",
]

# Image Upload Constraints
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_MIME_TYPES = ["image/jpeg", "image/png", "image/webp", "image/jpg"]

# Vision LLM Configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
VISION_MODEL = os.environ.get("VISION_MODEL", "gemini-2.0-flash")
