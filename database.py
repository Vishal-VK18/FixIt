"""Database and Ticket Persistence Module for FixIt Campus Maintenance.

Handles SQLite connection, schema migrations, ticket storage,
and duplicate ticket detection and merging.
"""

import contextlib
import datetime
import os
import re
import sqlite3
from typing import Any, Dict, Generator, List, Optional, Tuple

import config


@contextlib.contextmanager
def get_db_session() -> Generator[sqlite3.Connection, None, None]:
    """Context manager yielding a SQLite connection and ensuring it is always closed."""
    conn = sqlite3.connect(config.DATABASE_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def get_db_connection() -> sqlite3.Connection:
    """Create and return a database connection with row factory enabled."""
    conn = sqlite3.connect(config.DATABASE_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize SQLite tables for FixIt maintenance system."""
    with get_db_session() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_ref TEXT UNIQUE NOT NULL,
                student_id TEXT NOT NULL,
                student_name TEXT NOT NULL,
                block TEXT NOT NULL,
                room TEXT NOT NULL,
                issue TEXT NOT NULL,
                category TEXT NOT NULL,
                priority TEXT NOT NULL,
                department TEXT NOT NULL,
                suggested_fix TEXT,
                is_emergency BOOLEAN NOT NULL DEFAULT 0,
                image_path TEXT,
                status TEXT NOT NULL DEFAULT 'OPEN',
                duplicate_count INTEGER NOT NULL DEFAULT 1,
                merged_into_id INTEGER,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (merged_into_id) REFERENCES tickets(id)
            );
            """
        )
        # Create indexes for fast lookup during duplicate detection
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_tickets_duplicate_lookup
            ON tickets (block, room, category, status);
            """
        )
        conn.commit()


def normalize_room(room_str: str) -> str:
    """Normalize room string for robust comparison (e.g. 'Room 204' -> '204')."""
    if not room_str:
        return ""
    cleaned = room_str.strip().lower()
    # Normalize common prefixes: "room 204", "rm 204", "rm. 204", "r-204"
    cleaned = re.sub(r"^(?:room|rm\.?|r-?)\s*", "", cleaned)
    # Remove excessive internal whitespace
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def find_duplicate_ticket(
    block: str,
    room: str,
    category: str,
    conn: Optional[sqlite3.Connection] = None,
) -> Optional[Dict[str, Any]]:
    """Detect if an active unresolved ticket exists for the same block, room, and category.

    Args:
        block: Campus block name.
        room: Room or area description.
        category: Maintenance category (e.g. Electrical, Plumbing).
        conn: Optional existing sqlite connection.

    Returns:
        Existing ticket dict if a duplicate is found, otherwise None.
    """
    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        # Query open tickets in the same block and category
        cursor.execute(
            """
            SELECT * FROM tickets
            WHERE LOWER(block) = LOWER(?)
              AND category = ?
              AND status NOT IN ('RESOLVED', 'CLOSED')
              AND merged_into_id IS NULL
            ORDER BY created_at DESC
            """,
            (block.strip(), category.strip()),
        )
        candidates = cursor.fetchall()
        target_norm_room = normalize_room(room)

        for candidate in candidates:
            cand_norm_room = normalize_room(candidate["room"])
            # Match if normalized room strings match, or one contains the other if specific
            if (
                cand_norm_room == target_norm_room
                or (len(target_norm_room) > 2 and target_norm_room in cand_norm_room)
                or (len(cand_norm_room) > 2 and cand_norm_room in target_norm_room)
            ):
                return dict(candidate)

        return None
    finally:
        if should_close:
            conn.close()


def create_or_merge_ticket(ticket_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """Create a new maintenance ticket or merge into an existing duplicate ticket.

    Args:
        ticket_data: Dictionary containing:
            - student_id
            - student_name
            - block
            - room
            - issue
            - category
            - priority
            - department
            - suggested_fix
            - is_emergency
            - image_path (optional)
            - notes (optional)

    Returns:
        Tuple of (is_duplicate: bool, ticket_record: Dict[str, Any])
    """
    init_db()
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    block = ticket_data.get("block", "").strip()
    room = ticket_data.get("room", "").strip()
    category = ticket_data.get("category", "Other").strip()
    priority = ticket_data.get("priority", "MEDIUM").strip().upper()
    department = ticket_data.get("department") or config.DEPARTMENT_MAP.get(
        category, "General Maintenance"
    )
    is_emergency = bool(ticket_data.get("is_emergency", False))
    student_id = ticket_data.get("student_id", "STU-ANON")
    student_name = ticket_data.get("student_name", "Student")
    issue = ticket_data.get("issue", "Reported maintenance issue")
    suggested_fix = ticket_data.get("suggested_fix", "")
    image_path = ticket_data.get("image_path", "")
    notes = ticket_data.get("notes", "")

    with get_db_session() as conn:
        cursor = conn.cursor()

        # Step 1: Check for existing duplicate ticket
        duplicate = find_duplicate_ticket(block, room, category, conn=conn)

        if duplicate is not None:
            # DUPLICATE DETECTED: Merge into existing ticket
            existing_id = duplicate["id"]
            new_duplicate_count = duplicate["duplicate_count"] + 1

            merge_note = (
                f"\n[{now_iso}] Merged report from {student_name} ({student_id}): {issue}"
            )
            updated_notes = (duplicate["notes"] or "") + merge_note

            # Emergency escalation: if this new report is CRITICAL/emergency, escalate existing ticket
            new_emergency = duplicate["is_emergency"] or is_emergency
            new_priority = duplicate["priority"]
            if is_emergency or priority == "CRITICAL":
                new_emergency = 1
                new_priority = "CRITICAL"

            cursor.execute(
                """
                UPDATE tickets
                SET duplicate_count = ?,
                    notes = ?,
                    is_emergency = ?,
                    priority = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    new_duplicate_count,
                    updated_notes,
                    1 if new_emergency else 0,
                    new_priority,
                    now_iso,
                    existing_id,
                ),
            )
            conn.commit()

            # Retrieve updated record
            cursor.execute("SELECT * FROM tickets WHERE id = ?", (existing_id,))
            updated_ticket = dict(cursor.fetchone())
            return True, updated_ticket

        # Step 2: NOT a duplicate: Create completely new ticket
        cursor.execute("SELECT MAX(id) FROM tickets")
        row = cursor.fetchone()
        max_id = row[0] if (row and row[0] is not None) else 0
        new_id = max_id + 1
        ticket_ref = f"TICK-{1000 + new_id}"

        cursor.execute(
            """
            INSERT INTO tickets (
                ticket_ref, student_id, student_name, block, room,
                issue, category, priority, department, suggested_fix,
                is_emergency, image_path, status, duplicate_count,
                merged_into_id, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', 1, NULL, ?, ?, ?)
            """,
            (
                ticket_ref,
                student_id,
                student_name,
                block,
                room,
                issue,
                category,
                priority,
                department,
                suggested_fix,
                1 if is_emergency else 0,
                image_path,
                notes,
                now_iso,
                now_iso,
            ),
        )
        conn.commit()

        cursor.execute("SELECT * FROM tickets WHERE ticket_ref = ?", (ticket_ref,))
        new_ticket = dict(cursor.fetchone())
        return False, new_ticket


def get_ticket_by_ref(ticket_ref: str) -> Optional[Dict[str, Any]]:
    """Retrieve ticket details by ticket reference code."""
    with get_db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tickets WHERE ticket_ref = ?", (ticket_ref,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_recent_tickets(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve the most recent tickets."""
    init_db()
    with get_db_session() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM tickets ORDER BY created_at DESC LIMIT ?", (limit,)
        )
        return [dict(r) for r in cursor.fetchall()]


def get_tickets_by_student(student_id: str) -> List[Dict[str, Any]]:
    """Retrieve tickets reported by a specific student."""
    init_db()
    with get_db_session() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM tickets WHERE student_id = ? ORDER BY created_at DESC",
            (student_id,),
        )
        return [dict(r) for r in cursor.fetchall()]
