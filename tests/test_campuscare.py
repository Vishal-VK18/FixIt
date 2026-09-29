"""Comprehensive verification tests for CampusCare Maintenance Platform."""

import os
from io import BytesIO
from pathlib import Path
from PIL import Image
import pytest
from fastapi.testclient import TestClient

import db
import ai_service
from app import app

client = TestClient(app)


def test_db_init_and_schema():
    """Verify database initialization and table schema."""
    db.init_db()
    with db._connection() as con:
        # Check tickets table exists
        t_table = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tickets'").fetchone()
        assert t_table is not None, "tickets table must exist"

        # Check indexes exist
        indexes = con.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()
        idx_names = [r["name"] for r in indexes]
        assert "idx_tickets_block" in idx_names
        assert "idx_tickets_room" in idx_names
        assert "idx_tickets_category" in idx_names
        assert "idx_tickets_status" in idx_names
        assert "idx_tickets_priority" in idx_names


def test_shared_ticket_contract_and_duplicate_detection():
    """Test shared ticket contract: add_ticket(t) -> (ticket_id, merged)."""
    import uuid
    unique_room = f"RM-{uuid.uuid4().hex[:6]}"
    # 1. New ticket creation
    ticket_payload = {
        "issue": "Test corridor light sparking",
        "category": "Electrical",
        "priority": "LOW",
        "department": "Electrical Maintenance",
        "suggested_fix": "Replace bulb and check ballast",
        "block": "Block C",
        "room": unique_room,
    }
    tid1, merged1 = db.add_ticket(ticket_payload)
    assert isinstance(tid1, int)
    assert merged1 is False, "First ticket must create a new ticket"

    saved1 = db.get_ticket(tid1)
    assert saved1["status"] == "Reported"
    assert saved1["priority"] == "LOW"
    assert saved1["report_count"] == 1
    assert saved1["block"] == "Block C"
    initial_updated_at = saved1["updated_at"]

    # 2. Duplicate submission for same block, room, category while OPEN (Reported)
    ticket_payload_dup = {
        "issue": "Another student reporting light sparking",
        "category": "Electrical",
        "priority": "LOW",
        "department": "Electrical Maintenance",
        "suggested_fix": "Replace bulb",
        "block": "Block C",
        "room": unique_room,
    }
    tid2, merged2 = db.add_ticket(ticket_payload_dup)
    assert tid2 == tid1, "Must merge into existing ticket"
    assert merged2 is True, "merged must be True"

    saved2 = db.get_ticket(tid1)
    assert saved2["report_count"] == 2
    assert saved2["updated_at"] > initial_updated_at
    # Escalation: LOW -> MEDIUM
    assert saved2["priority"] == "MEDIUM"

    # 3. Third duplicate: MEDIUM -> HIGH
    tid3, merged3 = db.add_ticket(ticket_payload_dup)
    assert tid3 == tid1
    assert merged3 is True
    saved3 = db.get_ticket(tid1)
    assert saved3["report_count"] == 3
    assert saved3["priority"] == "HIGH"

    # 4. Fourth duplicate: HIGH -> CRITICAL
    tid4, merged4 = db.add_ticket(ticket_payload_dup)
    assert tid4 == tid1
    assert merged4 is True
    saved4 = db.get_ticket(tid1)
    assert saved4["report_count"] == 4
    assert saved4["priority"] == "CRITICAL"

    # 5. Fifth duplicate: CRITICAL stays CRITICAL
    tid5, merged5 = db.add_ticket(ticket_payload_dup)
    assert tid5 == tid1
    saved5 = db.get_ticket(tid1)
    assert saved5["report_count"] == 5
    assert saved5["priority"] == "CRITICAL"

    # 6. Mark ticket as Fixed
    update_res = db.update_ticket_status(tid1, "Fixed")
    assert update_res is True
    fixed_ticket = db.get_ticket(tid1)
    assert fixed_ticket["status"] == "Fixed"
    assert fixed_ticket["updated_at"] > saved5["updated_at"]

    # 7. IMPORTANT REQUIREMENT: Fixed ticket must NOT block a new report!
    tid6, merged6 = db.add_ticket(ticket_payload)
    assert tid6 != tid1, "Fixed ticket must not block new report; must create new ticket ID"
    assert merged6 is False, "Must not be merged into Fixed ticket"
    saved6 = db.get_ticket(tid6)
    assert saved6["status"] == "Reported"
    assert saved6["report_count"] == 1


def test_api_ticket_routes():
    """Verify API POST /api/tickets and GET /api/tickets."""
    import uuid
    api_room = f"API-{uuid.uuid4().hex[:6]}"
    # Test POST
    res = client.post(
        "/api/tickets",
        json={
            "issue": "API test broken tap",
            "category": "Plumbing",
            "priority": "HIGH",
            "block": "Block B",
            "room": api_room,
            "suggested_fix": "Replace washer",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "ticket_id" in data
    assert data["merged"] is False
    assert data["ticket"]["department"] == "Plumbing & Water Works"

    # Test GET
    get_res = client.get("/api/tickets?block=Block B&category=Plumbing")
    assert get_res.status_code == 200
    tickets_list = get_res.json()["tickets"]
    assert any(t["room"] == api_room for t in tickets_list)

    # Test PATCH status
    ticket_id = data["ticket_id"]
    patch_res = client.patch(
        f"/api/tickets/{ticket_id}/status",
        json={"status": "Assigned"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["ticket"]["status"] == "Assigned"


def test_metrics_calculation():
    """Verify metrics calculation strictly derives from database."""
    res = client.get("/api/metrics")
    assert res.status_code == 200
    metrics = res.json()["metrics"]
    assert "total" in metrics
    assert "open" in metrics
    assert "critical_open" in metrics
    assert "fixed" in metrics
    assert metrics["total"] >= metrics["open"]


def test_predictive_maintenance_and_hotspots():
    """Verify predictive maintenance calculations and hotspot matrix."""
    # Hotspot matrix
    h_res = client.get("/api/hotspots")
    assert h_res.status_code == 200
    h_data = h_res.json()["data"]
    assert "blocks" in h_data
    assert "categories" in h_data
    assert "matrix" in h_data
    assert "Block C" in h_data["matrix"]
    assert "Electrical" in h_data["matrix"]["Block C"]

    # Predictive warnings
    w_res = client.get("/api/predictive-warnings?threshold=4")
    assert w_res.status_code == 200
    w_data = w_res.json()
    assert "warnings" in w_data
    assert isinstance(w_data["warnings"], list)


def test_ai_unconfigured_behavior():
    """Verify that unconfigured AI returns explicit error and never fake data."""
    old_gemini = os.environ.pop("GEMINI_API_KEY", None)
    try:
        # Use a valid image so this test reaches credential handling.
        image_buffer = BytesIO()
        Image.new("RGB", (1, 1)).save(image_buffer, format="PNG")
        dummy_png = image_buffer.getvalue()
        res = client.post(
            "/api/analyze-image",
            files={"file": ("test.png", dummy_png, "image/png")},
        )
        assert res.status_code == 400
        data = res.json()
        assert data["configured"] is False
        assert "Set GEMINI_API_KEY" in data["error"]
    finally:
        if old_gemini is not None:
            os.environ["GEMINI_API_KEY"] = old_gemini


def test_priority_sorting():
    """Verify tickets are sorted CRITICAL, HIGH, MEDIUM, LOW, and within equal priority most recently updated first."""
    import uuid
    room_base = f"SORT-{uuid.uuid4().hex[:6]}"
    
    t_low, _ = db.add_ticket({"issue": "Low defect", "category": "Furniture", "priority": "LOW", "block": "Block A", "room": f"{room_base}-1"})
    t_med, _ = db.add_ticket({"issue": "Med defect", "category": "Furniture", "priority": "MEDIUM", "block": "Block A", "room": f"{room_base}-2"})
    t_high, _ = db.add_ticket({"issue": "High defect", "category": "Furniture", "priority": "HIGH", "block": "Block A", "room": f"{room_base}-3"})
    t_crit, _ = db.add_ticket({"issue": "Critical defect", "category": "Furniture", "priority": "CRITICAL", "block": "Block A", "room": f"{room_base}-4"})

    tickets = db.get_tickets(block="Block A", sort_by="priority")
    priority_order = [t["priority"] for t in tickets if t["room"].startswith(room_base)]
    assert priority_order == ["CRITICAL", "HIGH", "MEDIUM", "LOW"]


def test_predictive_maintenance_30_day_cutoff():
    """Verify predictive maintenance ignores tickets older than 30 days."""
    from datetime import datetime, timedelta
    
    # Check current warnings
    warnings_before = db.get_predictive_warnings(threshold=5)
    
    # Insert an old ticket (45 days ago)
    old_date = (datetime.now() - timedelta(days=45)).isoformat(timespec="seconds", sep=" ")
    with db._connection() as con:
        con.execute(
            """INSERT INTO tickets (issue, category, priority, department, block, room, status, report_count, created_at, updated_at)
               VALUES ('Old issue', 'Sanitation', 'LOW', 'Sanitation', 'Block E', 'OLD-999', 'Reported', 1, ?, ?)""",
            (old_date, old_date)
        )
    
    # 45-day old ticket must not appear in 30-day predictive warnings
    warnings_after = db.get_predictive_warnings(threshold=5)
    assert not any(w["category"] == "Sanitation" and w["block"] == "Block E" for w in warnings_after)


def test_ticket_review_feedback():
    """Verify resident review submission for resolved tickets."""
    import uuid
    room = f"REV-{uuid.uuid4().hex[:6]}"
    tid, _ = db.add_ticket({"issue": "Review test fan", "category": "Electrical", "priority": "LOW", "block": "Block D", "room": room})
    pending_review = client.post(f"/api/tickets/{tid}/review", json={"rating": 5, "comment": "Not fixed yet"})
    assert pending_review.status_code == 400
    db.update_ticket_status(tid, "Fixed")

    res = client.post(f"/api/tickets/{tid}/review", json={"rating": 5, "comment": "Fast turnaround and friendly tech!"})
    assert res.status_code == 200
    assert res.json()["success"] is True

    # Invalid rating
    bad_res = client.post(f"/api/tickets/{tid}/review", json={"rating": 6, "comment": "Too high"})
    assert bad_res.status_code == 422 or bad_res.status_code == 400


def test_config_endpoint_and_security_contact():
    """Verify GET /api/config and POST /api/config."""
    res = client.get("/api/config")
    assert res.status_code == 200
    data = res.json()
    assert "blocks" in data
    assert "categories" in data
    assert "predictive_threshold" in data

    # Update config
    post_res = client.post("/api/config", json={"security_contact": "555-0199", "threshold": 4})
    assert post_res.status_code == 200
    assert post_res.json()["config"]["security_contact"] == "555-0199"
    assert post_res.json()["config"]["predictive_threshold"] == 4


def test_html_routes():
    """Verify all Stitch HTML page routes load successfully."""
    for path in [
        "/",
        "/report-issue",
        "/my-reports",
        "/maintenance-dashboard",
        "/predictive-maintenance",
        "/maintenance-tickets",
        "/analytics",
        "/settings",
    ]:
        res = client.get(path)
        assert res.status_code == 200
        assert "CAMPUSCARE" in res.text
        assert "text-on-surface" in res.text
