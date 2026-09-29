"""Comprehensive Automated Test Suite for Person 1: AI Vision Analysis + Student Reporting.

Tests all required scenarios from Section 16:
- Test 1: Normal issue (Broken chair -> Furniture, MEDIUM, is_emergency=False)
- Test 2: Cosmetic issue (Peeling paint -> Civil, LOW, is_emergency=False)
- Test 3: Electrical emergency (Sparking electrical panel -> Electrical, CRITICAL, is_emergency=True)
- Test 4: Flooding (Severe water flooding -> priority=CRITICAL, is_emergency=True)
- Test 5: API failure (provider failure is surfaced, never replaced with fake analysis)
- Test 6: Duplicate report (Matches unresolved ticket -> merged, duplicate count incremented)
- Test 7: New ticket (Unique issue -> new ticket created with ticket_ref)
- Emergency overrides & department mapping tests
- JSON normalization & markdown fence stripping tests
"""

import io
import os
import unittest
from unittest.mock import MagicMock, patch

from PIL import Image, PngImagePlugin

import config
import database
import vision


def create_dummy_image(text_hint: str = "") -> bytes:
    """Helper to generate a valid PNG image byte stream with optional metadata hint."""
    img = Image.new("RGB", (64, 64), color=(73, 109, 137))
    buf = io.BytesIO()
    info = PngImagePlugin.PngInfo()
    if text_hint:
        info.add_text("description", text_hint)
    img.save(buf, format="PNG", pnginfo=info)
    return buf.getvalue()


def analyze_with_mock(issue: str, category: str, priority: str, suggested_fix: str, is_emergency: bool = False) -> dict:
    result = {
        "issue": issue,
        "category": category,
        "priority": priority,
        "department": config.DEPARTMENT_MAP[category],
        "suggested_fix": suggested_fix,
        "is_emergency": is_emergency,
    }
    with patch("vision.config.GEMINI_API_KEY", "test-key"), patch("vision._call_gemini_vision", return_value=result):
        return vision.analyze_image(create_dummy_image())


class TestPerson1VisionAndReporting(unittest.TestCase):
    def setUp(self):
        # Use an in-memory or temporary database for testing
        self.test_db_path = "test_fixit.db"
        config.DATABASE_PATH = self.test_db_path
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except Exception:
                pass
        database.init_db()

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except Exception:
                pass

    # =========================================================================
    # Test 1 â€” Normal issue: Broken chair
    # Expected: category = Furniture, priority = MEDIUM, is_emergency = false
    # =========================================================================
    def test_01_normal_issue_broken_chair(self):
        result = analyze_with_mock("Broken chair with unstable leg", "Furniture", "MEDIUM", "Replace the damaged leg.")

        self.assertEqual(result["category"], "Furniture")
        self.assertEqual(result["priority"], "MEDIUM")
        self.assertFalse(result["is_emergency"])
        self.assertEqual(result["department"], "Furniture Department")
        self.assertTrue(len(result["issue"]) > 0)
        self.assertTrue(len(result["suggested_fix"]) > 0)

    # =========================================================================
    # Test 2 â€” Cosmetic issue: Peeling paint
    # Expected: category = Civil, priority = LOW, is_emergency = false
    # =========================================================================
    def test_02_cosmetic_issue_peeling_paint(self):
        result = analyze_with_mock("Peeling paint on wall", "Civil", "LOW", "Prepare and repaint the wall.")

        self.assertEqual(result["category"], "Civil")
        self.assertEqual(result["priority"], "LOW")
        self.assertFalse(result["is_emergency"])
        self.assertEqual(result["department"], "Civil Department")

    # =========================================================================
    # Test 3 â€” Electrical emergency: Sparking electrical panel
    # Expected: category = Electrical, priority = CRITICAL, is_emergency = true
    # =========================================================================
    def test_03_electrical_emergency_sparking_panel(self):
        result = analyze_with_mock("Sparking electrical panel", "Electrical", "CRITICAL", "Isolate power and inspect the panel.", True)

        self.assertEqual(result["category"], "Electrical")
        self.assertEqual(result["priority"], "CRITICAL")
        self.assertTrue(result["is_emergency"])
        self.assertEqual(result["department"], "Electrical Department")

    # =========================================================================
    # Test 4 â€” Flooding: Severe water flooding
    # Expected: priority = CRITICAL, is_emergency = true
    # =========================================================================
    def test_04_flooding_emergency(self):
        result = analyze_with_mock("Severe flooding near power", "Plumbing", "CRITICAL", "Isolate power and stop the leak.", True)

        self.assertEqual(result["priority"], "CRITICAL")
        self.assertTrue(result["is_emergency"])
        self.assertIn("Department", result["department"])

    # =========================================================================
    # Test 5 â€” API failure simulation
    # Expected: provider failures are surfaced instead of fabricated results
    # =========================================================================
    def test_05_api_failure_handling(self):
        img_bytes = create_dummy_image("any photo")

        with patch("vision.config.GEMINI_API_KEY", "test-key"):
            with patch("vision._call_gemini_vision", side_effect=RuntimeError("API Timeout / Network Down")):
                with self.assertRaises(RuntimeError):
                    vision.analyze_image(img_bytes)

    # =========================================================================
    # Test 6 & 7 â€” New Ticket Creation & Duplicate Report Detection
    # Expected:
    # - New ticket is created with unique ticket_ref
    # - Duplicate report in same block, room, and category is merged
    # =========================================================================
    def test_06_and_07_ticket_creation_and_duplicate_merging(self):
        # 1. Submit First Ticket (New Ticket - Test 7)
        ticket_payload_1 = {
            "student_id": "STU-1001",
            "student_name": "Student A",
            "block": "Block A - Humanities & Arts",
            "room": "Room 204",
            "issue": "Broken chair with detached armrest",
            "category": "Furniture",
            "priority": "MEDIUM",
            "department": "Furniture Department",
            "suggested_fix": "Replace armrest screw",
            "is_emergency": False,
        }
        is_dup_1, ticket_1 = database.create_or_merge_ticket(ticket_payload_1)

        self.assertFalse(is_dup_1, "First report should create a new ticket, not duplicate.")
        self.assertIsNotNone(ticket_1["ticket_ref"])
        self.assertTrue(ticket_1["ticket_ref"].startswith("TICK-"))
        self.assertEqual(ticket_1["duplicate_count"], 1)

        # 2. Submit Duplicate Report (Test 6)
        # Same block, room ("204" normalized), same category
        ticket_payload_2 = {
            "student_id": "STU-2002",
            "student_name": "Student B",
            "block": "Block A - Humanities & Arts",
            "room": "204",  # Normalized match with "Room 204"
            "issue": "Damaged chair in classroom 204",
            "category": "Furniture",
            "priority": "MEDIUM",
            "department": "Furniture Department",
            "suggested_fix": "Inspect chair",
            "is_emergency": False,
        }
        is_dup_2, ticket_2 = database.create_or_merge_ticket(ticket_payload_2)

        self.assertTrue(is_dup_2, "Second report in same room and category should be detected as duplicate.")
        self.assertEqual(ticket_2["ticket_ref"], ticket_1["ticket_ref"], "Should merge into existing ticket.")
        self.assertEqual(ticket_2["duplicate_count"], 2, "Duplicate count should increment to 2.")
        self.assertIn("Student B", ticket_2["notes"])

        # 3. Submit Different Category in Same Room (Should NOT be duplicate)
        ticket_payload_3 = {
            "student_id": "STU-3003",
            "student_name": "Student C",
            "block": "Block A - Humanities & Arts",
            "room": "Room 204",
            "issue": "Flickering overhead light fixture",
            "category": "Electrical",
            "priority": "HIGH",
            "department": "Electrical Department",
            "suggested_fix": "Replace fluorescent tube",
            "is_emergency": False,
        }
        is_dup_3, ticket_3 = database.create_or_merge_ticket(ticket_payload_3)

        self.assertFalse(is_dup_3, "Different category in same room should create a separate ticket.")
        self.assertNotEqual(ticket_3["ticket_ref"], ticket_1["ticket_ref"])

    # =========================================================================
    # Emergency Override Unit Tests (Section 3)
    # Even if LLM returns LOW or MEDIUM, emergency hazards MUST be forced to CRITICAL
    # =========================================================================
    def test_emergency_override_forces_critical(self):
        # Case A: LLM incorrectly says LOW for exposed live electrical wires
        raw_llm_output = {
            "issue": "Exposed electrical wires hanging from ceiling",
            "category": "Electrical",
            "priority": "LOW",  # LLM erroneously downgraded
            "suggested_fix": "Tape wires",
            "is_emergency": False,
        }
        normalized = vision.validate_and_normalize_result(raw_llm_output)
        self.assertEqual(normalized["priority"], "CRITICAL")
        self.assertTrue(normalized["is_emergency"])

        # Case B: LLM says MEDIUM for active fire hazard
        raw_fire_output = {
            "issue": "Small fire and smoke emitting from socket",
            "category": "Electrical",
            "priority": "MEDIUM",
            "suggested_fix": "Extinguish and inspect",
            "is_emergency": False,
        }
        normalized_fire = vision.validate_and_normalize_result(raw_fire_output)
        self.assertEqual(normalized_fire["priority"], "CRITICAL")
        self.assertTrue(normalized_fire["is_emergency"])

        # Case C: Water near electricity
        raw_water_elec = {
            "issue": "Water leaking near electrical socket and switchboard",
            "category": "Electrical",
            "priority": "HIGH",
            "suggested_fix": "Isolate power",
            "is_emergency": False,
        }
        normalized_water = vision.validate_and_normalize_result(raw_water_elec)
        self.assertEqual(normalized_water["priority"], "CRITICAL")
        self.assertTrue(normalized_water["is_emergency"])

    # =========================================================================
    # Deterministic Department Mapping Tests (Section 4)
    # =========================================================================
    def test_department_mapping_completeness(self):
        expected_mappings = {
            "Electrical": "Electrical Department",
            "Plumbing": "Plumbing Department",
            "Furniture": "Furniture Department",
            "Civil": "Civil Department",
            "IT/Network": "IT Department",
            "Sanitation": "Sanitation Department",
            "Other": "General Maintenance",
        }
        for cat, expected_dept in expected_mappings.items():
            self.assertEqual(config.DEPARTMENT_MAP.get(cat), expected_dept)
            result = vision.validate_and_normalize_result({
                "issue": "Routine check",
                "category": cat,
                "priority": "LOW",
                "suggested_fix": "Check",
                "is_emergency": False,
            })
            self.assertEqual(result["department"], expected_dept)

    # =========================================================================
    # Markdown Code Fence and Malformed JSON Stripping Tests (Section 1)
    # =========================================================================
    def test_markdown_fence_and_malformed_json_handling(self):
        # LLM returns json wrapped in markdown code fence
        fenced_str = """```json
{
  "issue": "Broken faucet running constantly",
  "category": "Plumbing",
  "priority": "HIGH",
  "suggested_fix": "Replace faucet cartridge",
  "is_emergency": false
}
```"""
        result = vision.validate_and_normalize_result(fenced_str)
        self.assertEqual(result["category"], "Plumbing")
        self.assertEqual(result["department"], "Plumbing Department")
        self.assertEqual(result["priority"], "HIGH")
        self.assertFalse(result["is_emergency"])

        # LLM returns conversational commentary around JSON
        conversational_str = """Here is your maintenance analysis:
{
  "issue": "Slow Wi-Fi access point",
  "category": "IT/Network",
  "priority": "LOW",
  "suggested_fix": "Reboot router",
  "is_emergency": false
}
Hope this helps!"""
        result_conv = vision.validate_and_normalize_result(conversational_str)
        self.assertEqual(result_conv["category"], "IT/Network")
        self.assertEqual(result_conv["department"], "IT Department")

        # Completely invalid string -> safe fallback
        garbage_str = "Sorry, I cannot process this image."
        fallback_res = vision.validate_and_normalize_result(garbage_str)
        self.assertEqual(fallback_res["category"], "Other")
        self.assertEqual(fallback_res["priority"], "MEDIUM")
        self.assertEqual(fallback_res["department"], "General Maintenance")


if __name__ == "__main__":
    unittest.main()
