"""Authentication, authorization, and student ticket ownership tests."""

from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import pytest
import secrets
import auth

import db
import database
from app import app


def register(client, name, email, student_id):
    password = secrets.token_urlsafe(18)
    result = client.post("/api/auth/register", json={
        "name": name,
        "email": email,
        "student_id": student_id,
        "password": password,
    })
    assert result.status_code == 200, result.text
    if not hasattr(client, "test_passwords"):
        client.test_passwords = {}
    client.test_passwords[email] = password
    return result.json()["user"]


def test_authentication_and_admin_routes_are_protected(client):
    with TestClient(app) as anonymous:
        assert anonymous.get("/api/metrics").status_code == 401
        assert anonymous.get("/api/tickets").status_code == 401
        assert anonymous.post("/api/config", json={"threshold": 1}).status_code == 401
        assert anonymous.post("/api/tickets", json={
            "issue": "Test issue", "category": "Other", "priority": "LOW", "block": "Block A", "room": "101",
        }).status_code == 401
        for path in ("/api/analytics", "/api/hotspots", "/api/block-counts", "/api/predictive-warnings", "/api/predictive-patterns"):
            assert anonymous.get(path).status_code == 401
        assert anonymous.get("/maintenance-dashboard", follow_redirects=False).status_code == 303

    signed_in = client.post("/api/auth/student/login", json={"email": "student@example.test", "password": client.test_student_password})
    assert signed_in.status_code == 200
    cookie = signed_in.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie
    assert client.get("/api/auth/me").json()["user"]["role"] == "student"
    assert client.get("/api/metrics").status_code == 403
    assert client.get("/api/analytics").status_code == 403
    assert client.get("/api/predictive-patterns").status_code == 403
    assert client.get("/api/config").status_code == 403
    assert client.post("/api/config", json={"threshold": 2}).status_code == 403
    assert client.post("/api/auth/admin/login", json={"email": "student@example.test", "password": client.test_student_password}).status_code == 401


def test_student_ownership_duplicate_merge_and_admin_status_flow(client):
    student_a = register(client, "Student A", "student-a@example.test", "STU-A")
    first_payload = {
        "issue": "Broken classroom fan",
        "category": "Electrical",
        "priority": "LOW",
        "block": "Block C",
        "room": "204",
        "suggested_fix": "Inspect and repair the fan",
    }
    first = client.post("/api/tickets", json=first_payload)
    assert first.status_code == 200, first.text
    ticket_id = first.json()["ticket_id"]
    assert first.json()["merged"] is False

    with db._connection() as connection:
        row = connection.execute("SELECT password_hash FROM users WHERE id = ?", (student_a["id"],)).fetchone()
        assert row["password_hash"] != client.test_passwords["student-a@example.test"]
        assert "pbkdf2_sha256$" in row["password_hash"]

    with TestClient(app) as student_b_client:
        student_b = register(student_b_client, "Student B", "student-b@example.test", "STU-B")
        assert student_b["role"] == "student"
        assert student_b_client.get("/api/tickets").json()["tickets"] == []
        assert student_b_client.get(f"/api/tickets/{ticket_id}").status_code == 404

        duplicate = student_b_client.post("/api/tickets", json=first_payload)
        assert duplicate.status_code == 200, duplicate.text
        assert duplicate.json()["merged"] is True
        assert duplicate.json()["ticket_id"] == ticket_id
        assert duplicate.json()["ticket"]["report_count"] == 2
        assert duplicate.json()["ticket"]["priority"] == "MEDIUM"
        assert [item["id"] for item in student_b_client.get("/api/tickets").json()["tickets"]] == [ticket_id]

        admin_login = student_b_client.post("/api/auth/admin/login", json={
            "email": "admin@example.test", "password": client.test_admin_password,
        })
        assert admin_login.status_code == 200
        assert [item["id"] for item in student_b_client.get("/api/tickets").json()["tickets"]] == [ticket_id]
        assert student_b_client.patch(f"/api/tickets/{ticket_id}/status", json={"status": "Assigned"}).status_code == 200
        fixed = student_b_client.patch(f"/api/tickets/{ticket_id}/status", json={"status": "Fixed"})
        assert fixed.status_code == 200
        assert fixed.json()["ticket"]["status"] == "Fixed"
        student_b_client.post("/api/auth/student/login", json={"email": "student-b@example.test", "password": student_b_client.test_passwords["student-b@example.test"]})
        after_fixed = student_b_client.post("/api/tickets", json=first_payload)
        assert after_fixed.status_code == 200
        assert after_fixed.json()["merged"] is False
        assert after_fixed.json()["ticket_id"] != ticket_id

    own = client.get("/api/tickets")
    assert [item["id"] for item in own.json()["tickets"]] == [ticket_id]
    assert own.json()["tickets"][0]["status"] == "Fixed"


def test_logout_revokes_session(client):
    assert client.get("/api/auth/me").status_code == 200
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/auth/me").status_code == 401


def test_legacy_ticket_database_is_disabled(monkeypatch):
    monkeypatch.delenv("CAMPUSCARE_ALLOW_LEGACY_DB", raising=False)
    with pytest.raises(RuntimeError, match="retired"):
        database.init_db()


def test_admin_is_created_only_through_operator_command(monkeypatch, client):
    answers = iter(("Bootstrapped Admin", "bootstrap@example.test"))
    password = secrets.token_urlsafe(18)
    passwords = iter((password, password))
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    monkeypatch.setattr(auth, "getpass", lambda _prompt: next(passwords))
    monkeypatch.setattr(auth.sys, "argv", ["auth.py", "create-admin"])
    auth.create_admin_cli()
    with db._connection() as connection:
        admin_row = connection.execute("SELECT role, password_hash FROM users WHERE email = ?", ("bootstrap@example.test",)).fetchone()
    assert admin_row["role"] == "admin"
    assert password not in admin_row["password_hash"]
    signed_in = client.post("/api/auth/admin/login", json={"email": "bootstrap@example.test", "password": password})
    assert signed_in.status_code == 200


def test_signup_rejects_weak_password_without_echoing_it(client):
    password = "short"
    response = client.post("/api/auth/register", json={
        "name": "Weak Password User",
        "email": "weak@example.test",
        "student_id": "STU-WEAK",
        "password": password,
    })
    assert response.status_code == 400
    assert '"input":"short"' not in response.text


def test_public_registration_cannot_select_admin_role(client):
    response = client.post("/api/auth/register", json={
        "name": "Public Admin Attempt",
        "email": "public-admin@example.test",
        "student_id": "STU-PUBLIC-ADMIN",
        "password": secrets.token_urlsafe(18),
        "role": "admin",
    })
    assert response.status_code == 422
    assert db.get_user_by_email("public-admin@example.test") is None


def test_predictive_patterns_use_only_recent_database_tickets(client):
    client.post("/api/auth/student/login", json={"email": "student@example.test", "password": client.test_student_password})
    for index in range(4):
        response = client.post("/api/tickets", json={
            "issue": f"Electrical fault {index}", "category": "Electrical", "priority": "LOW",
            "block": "Block C", "room": f"QA-{index}",
        })
        assert response.status_code == 200

    old = (datetime.now() - timedelta(days=45)).isoformat(timespec="seconds", sep=" ")
    with db._connection() as connection:
        for index in range(4):
            connection.execute(
                """INSERT INTO tickets(issue, category, priority, department, block, room, status, report_count, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, 'Reported', 1, ?, ?)""",
                (f"Old plumbing fault {index}", "Plumbing", "LOW", db.DEPARTMENT_MAP["Plumbing"], "Block D", f"OLD-{index}", old, old),
            )

    client.post("/api/auth/admin/login", json={"email": "admin@example.test", "password": client.test_admin_password})
    response = client.get("/api/predictive-warnings?threshold=4")
    assert response.status_code == 200
    warnings = response.json()["warnings"]
    assert any(item["block"] == "Block C" and item["category"] == "Electrical" and item["count"] == 4 for item in warnings)
    assert not any(item["block"] == "Block D" and item["category"] == "Plumbing" for item in warnings)
