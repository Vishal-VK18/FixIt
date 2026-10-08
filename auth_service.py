"""Database-backed authentication helpers for CampusCare."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import sqlite3
from datetime import datetime
from typing import Any

import db

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
ROLES = ("student", "admin")


def _public(row: sqlite3.Row | dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    value = dict(row)
    value.pop("password_hash", None)
    return value


def validate_email(email: str) -> str:
    email = (email or "").strip().lower()
    if not EMAIL_RE.match(email):
        raise ValueError("Please enter a valid email address.")
    return email


def validate_password(password: str) -> str:
    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")
    return password


def hash_password(password: str) -> str:
    validate_password(password)
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
    return f"scrypt$16384$8$1${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        _, n, r, p, salt_hex, digest_hex = encoded.split("$")
        digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=int(n), r=int(r), p=int(p))
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def create_user(name: str, email: str, password: str, role: str, student_id: str | None = None) -> dict[str, Any]:
    name = (name or "").strip()
    if not name:
        raise ValueError("Name is required.")
    email = validate_email(email)
    validate_password(password)
    if role not in ROLES:
        raise ValueError("Invalid account role.")
    student_id = (student_id or "").strip() or None
    if role == "student" and not student_id:
        raise ValueError("Student ID is required.")
    now = datetime.now().isoformat(timespec="seconds", sep=" ")
    try:
        with db._connection() as conn:
            cur = conn.execute(
                """INSERT INTO users (name, email, password_hash, role, student_id, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (name, email, hash_password(password), role, student_id, now, now),
            )
            row = conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
            return _public(row) or {}
    except sqlite3.IntegrityError as exc:
        message = str(exc).lower()
        if "student_id" in message:
            raise ValueError("An account with this student ID already exists.") from exc
        raise ValueError("An account with this email already exists.") from exc


def authenticate(email: str, password: str, role: str) -> dict[str, Any] | None:
    email = (email or "").strip().lower()
    with db._connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if not row or row["role"] != role or not verify_password(password or "", row["password_hash"]):
        return None
    return _public(row)


def get_user(user_id: int) -> dict[str, Any] | None:
    with db._connection() as conn:
        return _public(conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone())
