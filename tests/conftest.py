"""Keep all test accounts, sessions, settings, and tickets isolated from user data."""

from pathlib import Path
import secrets
import uuid

import pytest
from fastapi.testclient import TestClient

import app as app_module
import auth
import db


@pytest.fixture(autouse=True)
def isolated_database(monkeypatch):
    test_dir = Path(__file__).resolve().parent
    test_db = test_dir / f"campuscare-{uuid.uuid4().hex}.db"
    test_env = test_dir / ".env"
    previous_env = test_env.read_bytes() if test_env.exists() else None
    monkeypatch.setattr(db, "DB_PATH", test_db)
    monkeypatch.setattr(app_module, "BASE_DIR", test_dir)
    for name in ("PREDICTIVE_THRESHOLD", "SECURITY_CONTACT_NUMBER"):
        monkeypatch.delenv(name, raising=False)
    db.init_db()
    yield
    if test_db.exists():
        test_db.unlink()
    if previous_env is None:
        test_env.unlink(missing_ok=True)
    else:
        test_env.write_bytes(previous_env)


@pytest.fixture
def client(isolated_database):
    from app import app

    student_password = secrets.token_urlsafe(18)
    admin_password = secrets.token_urlsafe(18)
    student = auth.create_account("Test Student", "student@example.test", student_password, "STU-TEST")
    admin = auth.create_account("Test Admin", "admin@example.test", admin_password, role="admin")
    with TestClient(app) as test_client:
        response = test_client.post("/api/auth/admin/login", json={"email": admin["email"], "password": admin_password})
        assert response.status_code == 200
        test_client.test_student = student
        test_client.test_admin = admin
        test_client.test_student_password = student_password
        test_client.test_admin_password = admin_password
        yield test_client
