"""Password hashing, database sessions, and first-admin provisioning."""

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets
import sys
from getpass import getpass

import db

PASSWORD_ITERATIONS = 600_000
SESSION_HOURS = 12


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("Password must contain at least 12 characters.")
    salt = secrets.token_bytes(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt.hex()}${hashed.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations))
        return hmac.compare_digest(actual.hex(), expected)
    except (ValueError, TypeError):
        return False


def public_user(user: dict) -> dict:
    return {key: user[key] for key in ("id", "name", "email", "student_id", "role") if key in user}


def create_account(name: str, email: str, password: str, student_id: str | None = None, *, role: str = "student") -> dict:
    name, email = name.strip(), email.strip().lower()
    if not name or len(name) > 120:
        raise ValueError("Enter a valid name.")
    if not email or len(email) > 254 or "@" not in email:
        raise ValueError("Enter a valid email address.")
    student_id = student_id.strip() if student_id else None
    if role == "student" and (not student_id or len(student_id) > 80):
        raise ValueError("Enter a valid student ID.")
    if role == "admin":
        student_id = None
    user = db.create_user_record(name, email, student_id, hash_password(password), role)
    return public_user(user)


def authenticate(email: str, password: str, role: str) -> dict | None:
    user = db.get_user_by_email(email)
    if not user or user["role"] != role or not verify_password(password, user["password_hash"]):
        return None
    return public_user(user)


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires = (datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)).replace(tzinfo=None)
    db.save_session(token_hash, user_id, expires.isoformat(sep=" ", timespec="seconds"))
    return token


def session_user(token: str | None) -> dict | None:
    if not token:
        return None
    return db.get_session_user(hashlib.sha256(token.encode()).hexdigest())


def revoke_session(token: str | None) -> None:
    if token:
        db.delete_session(hashlib.sha256(token.encode()).hexdigest())


def create_admin_cli() -> None:
    """Provision an admin without exposing a default password or public signup."""
    db.init_db()
    if len(sys.argv) != 2 or sys.argv[1] != "create-admin":
        print("Usage: py auth.py create-admin")
        raise SystemExit(2)
    name = input("Admin name: ").strip()
    email = input("Admin email: ").strip()
    password = getpass("Admin password (12+ characters): ")
    confirmation = getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")
    try:
        user = create_account(name, email, password, role="admin")
    except Exception as exc:
        raise SystemExit(f"Could not create admin: {exc}") from exc
    print(f"Admin account created for {user['email']}.")


if __name__ == "__main__":
    create_admin_cli()
