"""SQLite storage and operations for CampusCare maintenance tickets."""

from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
from typing import Iterator, Any

DB_PATH = Path(__file__).resolve().parent / "tickets.db"

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
STATUSES = ("Reported", "Assigned", "Fixed")
OPEN_STATUSES = ("Reported", "Assigned")

BLOCKS = ("Block A", "Block B", "Block C", "Block D", "Block E")

DEPARTMENT_MAP = {
    "Electrical": "Electrical Maintenance",
    "Plumbing": "Plumbing & Water Works",
    "Furniture": "Carpentry & Facilities",
    "Civil": "Civil Works",
    "IT/Network": "IT Support",
    "Sanitation": "Sanitation",
    "Other": "General Maintenance",
}


@contextmanager
def _connection() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _normalize_block(block: str) -> str:
    """Normalize block string to standard 'Block X' format."""
    cleaned = block.strip()
    if cleaned.upper() in ("A", "B", "C", "D", "E"):
        return f"Block {cleaned.upper()}"
    if cleaned.upper().startswith("BLOCK "):
        letter = cleaned[6:].strip().upper()
        if letter in ("A", "B", "C", "D", "E"):
            return f"Block {letter}"
    return cleaned


def init_db() -> None:
    """Create and migrate the authoritative CampusCare database schema."""
    with _connection() as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                student_id TEXT COLLATE NOCASE UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('student', 'admin')),
                created_at TEXT NOT NULL,
                CHECK((role = 'student' AND student_id IS NOT NULL) OR
                      (role = 'admin' AND student_id IS NULL))
            )"""
        )
        connection.execute(
            """CREATE TABLE IF NOT EXISTS auth_sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                expires_at TEXT NOT NULL
            )"""
        )
        connection.execute(
            """CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                issue TEXT NOT NULL,
                category TEXT NOT NULL,
                priority TEXT NOT NULL,
                department TEXT NOT NULL,
                suggested_fix TEXT,
                block TEXT NOT NULL,
                room TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Reported',
                report_count INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )"""
        )

        connection.execute(
            """CREATE TABLE IF NOT EXISTS ticket_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL,
                rating INTEGER NOT NULL,
                comment TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (ticket_id) REFERENCES tickets(id)
            )"""
        )
        connection.execute(
            """CREATE TABLE IF NOT EXISTS ticket_owners (
                ticket_id INTEGER NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                PRIMARY KEY (ticket_id, user_id)
            )"""
        )

        # Performance indexes as required by spec #34
        connection.execute("CREATE INDEX IF NOT EXISTS idx_tickets_block ON tickets(block);")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_tickets_room ON tickets(room);")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_tickets_category ON tickets(category);")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_tickets_priority ON tickets(priority);")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_tickets_created_at ON tickets(created_at);")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_tickets_open_lookup ON tickets(block, room, category, status);")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_ticket_owners_user ON ticket_owners(user_id, ticket_id);")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_sessions_expiry ON auth_sessions(expires_at);")

        # Migrate any single-letter blocks ('A' -> 'Block A')
        connection.execute(
            """UPDATE tickets
               SET block = 'Block ' || block
               WHERE block IN ('A', 'B', 'C', 'D', 'E')"""
        )


def _required_text(ticket: dict, field: str) -> str:
    value = ticket.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{field}' must be a non-empty string.")
    return value.strip()


def check_duplicate_open_ticket(block: str, room: str, category: str) -> dict | None:
    """Check if an open ticket exists for the same block, room, and category."""
    init_db()
    norm_block = _normalize_block(block)
    room_clean = room.strip()
    with _connection() as connection:
        row = connection.execute(
            """SELECT * FROM tickets
               WHERE block = ? AND room = ? AND category = ?
               AND status IN (?, ?) ORDER BY id LIMIT 1""",
            (norm_block, room_clean, category, *OPEN_STATUSES),
        ).fetchone()
        return dict(row) if row else None


def add_ticket(t: dict, owner_id: int | None = None) -> tuple[int, bool]:
    """Insert a ticket, or merge it into a matching open ticket.
    
    MUST return (ticket_id, merged).
    merged = False means a new ticket was created.
    merged = True means the new report was merged into an existing open ticket.
    """
    if not isinstance(t, dict):
        raise ValueError("Ticket must be a dictionary.")
    issue = _required_text(t, "issue")
    category = _required_text(t, "category")
    priority = _required_text(t, "priority")

    suggested_fix = t.get("suggested_fix")
    if suggested_fix is not None and not isinstance(suggested_fix, str):
        raise ValueError("'suggested_fix' must be a string.")
    suggested_fix = suggested_fix.strip() if suggested_fix else None

    raw_block = _required_text(t, "block")
    block = _normalize_block(raw_block)
    room = _required_text(t, "room")

    if category not in CATEGORIES:
        raise ValueError(f"Invalid category '{category}'. Choose one of: {', '.join(CATEGORIES)}.")
    department = DEPARTMENT_MAP[category]
    if priority not in PRIORITIES:
        raise ValueError(f"Invalid priority '{priority}'. Choose one of: {', '.join(PRIORITIES)}.")
    if block not in BLOCKS:
        raise ValueError(f"Invalid block '{raw_block}'. Choose one of: {', '.join(BLOCKS)}.")

    now = datetime.now().isoformat(timespec="microseconds", sep=" ")
    init_db()
    with _connection() as connection:
        existing = connection.execute(
            """SELECT id, priority, report_count FROM tickets
               WHERE block = ? AND room = ? AND category = ?
               AND status IN (?, ?) ORDER BY id LIMIT 1""",
            (block, room, category, *OPEN_STATUSES),
        ).fetchone()
        if existing:
            old_index = PRIORITIES.index(existing["priority"])
            escalated = PRIORITIES[min(old_index + 1, len(PRIORITIES) - 1)]
            connection.execute(
                "UPDATE tickets SET priority = ?, report_count = report_count + 1, updated_at = ? WHERE id = ?",
                (escalated, now, existing["id"]),
            )
            if owner_id is not None:
                connection.execute(
                    "INSERT OR IGNORE INTO ticket_owners(ticket_id, user_id) VALUES (?, ?)",
                    (existing["id"], owner_id),
                )
            return int(existing["id"]), True

        cursor = connection.execute(
            """INSERT INTO tickets
               (issue, category, priority, department, suggested_fix, block, room, status,
                report_count, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'Reported', 1, ?, ?)""",
            (issue, category, priority, department, suggested_fix, block, room, now, now),
        )
        ticket_id = int(cursor.lastrowid)
        if owner_id is not None:
            connection.execute(
                "INSERT INTO ticket_owners(ticket_id, user_id) VALUES (?, ?)",
                (ticket_id, owner_id),
            )
        return ticket_id, False


def get_tickets_for_owner(user_id: int, **filters: Any) -> list[dict]:
    """Return only tickets associated with one authenticated student."""
    return get_tickets(**filters, owner_id=user_id)


def owns_ticket(ticket_id: int, user_id: int) -> bool:
    init_db()
    with _connection() as connection:
        return connection.execute(
            "SELECT 1 FROM ticket_owners WHERE ticket_id = ? AND user_id = ?",
            (ticket_id, user_id),
        ).fetchone() is not None


def create_user_record(name: str, email: str, student_id: str | None, password_hash: str, role: str) -> dict:
    if role not in ("student", "admin") or (role == "student") != (student_id is not None):
        raise ValueError("Invalid user role or student ID.")
    init_db()
    now = datetime.now().isoformat(timespec="seconds", sep=" ")
    with _connection() as connection:
        cursor = connection.execute(
            "INSERT INTO users(name, email, student_id, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (name.strip(), email.strip().lower(), student_id.strip() if student_id else None, password_hash, role, now),
        )
        return dict(connection.execute(
            "SELECT id, name, email, student_id, role, created_at FROM users WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone())


def get_user_by_email(email: str) -> dict | None:
    init_db()
    with _connection() as connection:
        row = connection.execute("SELECT * FROM users WHERE email = ? COLLATE NOCASE", (email.strip(),)).fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    init_db()
    with _connection() as connection:
        row = connection.execute(
            "SELECT id, name, email, student_id, role, created_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None


def save_session(token_hash: str, user_id: int, expires_at: str) -> None:
    init_db()
    with _connection() as connection:
        connection.execute("DELETE FROM auth_sessions WHERE expires_at <= datetime('now')")
        connection.execute(
            "INSERT INTO auth_sessions(token_hash, user_id, expires_at) VALUES (?, ?, ?)",
            (token_hash, user_id, expires_at),
        )


def get_session_user(token_hash: str) -> dict | None:
    init_db()
    with _connection() as connection:
        row = connection.execute(
            """SELECT u.id, u.name, u.email, u.student_id, u.role
               FROM auth_sessions s JOIN users u ON u.id = s.user_id
               WHERE s.token_hash = ? AND s.expires_at > datetime('now')""",
            (token_hash,),
        ).fetchone()
        return dict(row) if row else None


def delete_session(token_hash: str) -> None:
    init_db()
    with _connection() as connection:
        connection.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (token_hash,))


def get_tickets(
    status: str | None = None,
    category: str | None = None,
    block: str | None = None,
    priority: str | None = None,
    search: str | None = None,
    sort_by: str = "priority",
    owner_id: int | None = None,
) -> list[dict]:
    """Retrieve tickets with optional filtering and priority sorting."""
    init_db()
    if status is not None and status != "All" and status not in STATUSES:
        raise ValueError(f"Invalid status. Choose one of: {', '.join(STATUSES)}.")

    conditions = []
    params: list[Any] = []

    if owner_id is not None:
        conditions.append("EXISTS (SELECT 1 FROM ticket_owners WHERE ticket_id = tickets.id AND user_id = ?)")
        params.append(owner_id)

    if status and status != "All":
        conditions.append("status = ?")
        params.append(status)

    if category and category != "All":
        conditions.append("category = ?")
        params.append(category)

    if block and block != "All":
        conditions.append("block = ?")
        params.append(_normalize_block(block))

    if priority and priority != "All":
        conditions.append("priority = ?")
        params.append(priority)

    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        conditions.append(
            "(LOWER(issue) LIKE ? OR LOWER(room) LIKE ? OR LOWER(block) LIKE ? OR CAST(id AS TEXT) LIKE ? OR LOWER(department) LIKE ?)"
        )
        params.extend([term, term, term, term, term])

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    if sort_by == "priority":
        order_clause = """ORDER BY 
            CASE priority 
                WHEN 'CRITICAL' THEN 0 
                WHEN 'HIGH' THEN 1 
                WHEN 'MEDIUM' THEN 2 
                WHEN 'LOW' THEN 3 
                ELSE 4 
            END ASC, 
            updated_at DESC, id DESC"""
    elif sort_by == "newest":
        order_clause = "ORDER BY created_at DESC, id DESC"
    elif sort_by == "oldest":
        order_clause = "ORDER BY created_at ASC, id ASC"
    elif sort_by == "reports":
        order_clause = "ORDER BY report_count DESC, updated_at DESC"
    else:
        order_clause = "ORDER BY updated_at DESC, id DESC"

    query = f"SELECT * FROM tickets {where_clause} {order_clause}"

    with _connection() as connection:
        rows = connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def get_ticket(ticket_id: int) -> dict | None:
    """Retrieve a single ticket by ID."""
    init_db()
    with _connection() as connection:
        row = connection.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        return dict(row) if row else None


def update_ticket_status(ticket_id: int, status: str) -> bool:
    """Update ticket status and refresh updated_at."""
    if status not in STATUSES:
        raise ValueError(f"Invalid status. Choose one of: {', '.join(STATUSES)}.")
    init_db()
    now = datetime.now().isoformat(timespec="microseconds", sep=" ")
    with _connection() as connection:
        cursor = connection.execute(
            "UPDATE tickets SET status = ?, updated_at = ? WHERE id = ?",
            (status, now, ticket_id),
        )
        return cursor.rowcount == 1


def get_metrics() -> dict[str, int]:
    """Calculate dashboard metrics dynamically from the database."""
    init_db()
    with _connection() as connection:
        row = connection.execute(
            """SELECT COUNT(*) AS total,
                      SUM(CASE WHEN status IN ('Reported', 'Assigned') THEN 1 ELSE 0 END) AS open,
                      SUM(CASE WHEN priority = 'CRITICAL' AND status IN ('Reported', 'Assigned') THEN 1 ELSE 0 END) AS critical_open,
                      SUM(CASE WHEN status = 'Fixed' THEN 1 ELSE 0 END) AS fixed
               FROM tickets"""
        ).fetchone()
        return {key: int(row[key] or 0) for key in ("total", "open", "critical_open", "fixed")}


def get_predictive_warnings(threshold: int = 4) -> list[dict]:
    """Analyze issues from the last 30 days grouped by block and category."""
    if threshold < 1:
        raise ValueError("Threshold must be at least 1.")
    cutoff = (datetime.now() - timedelta(days=30)).isoformat(timespec="seconds", sep=" ")
    init_db()
    with _connection() as connection:
        rows = connection.execute(
            """SELECT block, category, COUNT(*) AS count FROM tickets
               WHERE created_at >= ? GROUP BY block, category HAVING COUNT(*) >= ?
               ORDER BY count DESC, block, category""",
            (cutoff, threshold),
        ).fetchall()
        return [
            {
                "block": row["block"],
                "category": row["category"],
                "count": int(row["count"]),
                "message": f"{row['block']} has had {row['count']} {row['category'].lower()} issues this month, recommend an inspection.",
            }
            for row in rows
        ]


def get_predictive_patterns(threshold: int = 4) -> list[dict]:
    """Get rich pattern diagnostics including correlated tickets for predictive maintenance UI."""
    warnings = get_predictive_warnings(threshold=threshold)
    cutoff = (datetime.now() - timedelta(days=30)).isoformat(timespec="seconds", sep=" ")
    results = []
    with _connection() as connection:
        for idx, w in enumerate(warnings):
            block = w["block"]
            category = w["category"]
            count = w["count"]

            correlated_rows = connection.execute(
                """SELECT id, issue, room, priority, status, created_at FROM tickets
                   WHERE block = ? AND category = ? AND created_at >= ?
                   ORDER BY created_at DESC LIMIT 6""",
                (block, category, cutoff),
            ).fetchall()

            correlated = [dict(r) for r in correlated_rows]

            # Generate realistic root cause hypothesis based on category and block
            root_cause_map = {
                "Electrical": f"Main circuit breaker or transformer load exceeding capacity in {block}, causing circuit trips, overheating, and switch contact wear.",
                "Plumbing": f"Water pressure surges or aging supply joints across {block} plumbing risers resulting in recurring leaks and valve failure.",
                "Furniture": f"High wear-and-tear in common learning areas of {block} causing repeated hinge, latch, and seat frame stress fractures.",
                "Civil": f"Seasonal foundation shifting or moisture intrusion affecting {block} corridor plaster, masonry, and floor tiles.",
                "IT/Network": f"Sub-switch port buffer saturation or wireless access point power anomalies on {block} floor distribution cabinets.",
                "Sanitation": f"Drainage slope limitation or high footfall load in {block} waste disposal lines requiring preventative auguring.",
                "Other": f"Multiple generalized maintenance anomalies reported across {block} facilities.",
            }

            recommended_action_map = {
                "Electrical": f"Dispatch Senior Electrical Specialist for full panel thermal imaging & load analysis in {block}.",
                "Plumbing": f"Deploy plumbing team to perform pressure gradient inspection & seal replacements on {block} mains.",
                "Furniture": f"Conduct scheduled carpentry overhaul and structural hardware reinforcement in {block}.",
                "Civil": f"Execute masonry structural audit and reseal damp spots in {block}.",
                "IT/Network": f"Run network diagnostics, firmware reboot, and physical cable patch testing on {block} rack.",
                "Sanitation": f"Schedule heavy chemical clean and drain mechanical clearing for {block}.",
                "Other": f"Initiate preventative facility maintenance walk-through in {block}.",
            }

            pattern_id = f"PTN-{block.replace('Block ', '')}{idx+1:02d}"

            results.append(
                {
                    "id": pattern_id,
                    "block": block,
                    "category": category,
                    "count": count,
                    "threshold": threshold,
                    "message": w["message"],
                    "root_cause": root_cause_map.get(category, f"Correlated component degradation in {block}."),
                    "recommended_action": recommended_action_map.get(
                        category, f"Schedule comprehensive inspection for {block}."
                    ),
                    "severity": "CRITICAL" if count >= 6 else "HIGH",
                    "correlated_tickets": correlated,
                }
            )
    return results


def get_hotspot_matrix() -> dict[str, Any]:
    """Calculate the complete Block x Category ticket matrix from the database."""
    init_db()
    with _connection() as connection:
        rows = connection.execute(
            """SELECT block, category, COUNT(*) AS count
               FROM tickets
               GROUP BY block, category"""
        ).fetchall()

        matrix = {b: {c: 0 for c in CATEGORIES} for b in BLOCKS}
        for row in rows:
            b = _normalize_block(row["block"])
            c = row["category"]
            if b in matrix and c in matrix[b]:
                matrix[b][c] = int(row["count"])

        block_totals = {b: sum(matrix[b].values()) for b in BLOCKS}
        category_totals = {c: sum(matrix[b][c] for b in BLOCKS) for c in CATEGORIES}
        total_tickets = sum(block_totals.values())

        return {
            "blocks": list(BLOCKS),
            "categories": list(CATEGORIES),
            "matrix": matrix,
            "block_totals": block_totals,
            "category_totals": category_totals,
            "total_tickets": total_tickets,
        }


def get_block_issue_counts() -> dict[str, int]:
    """Get total issues per block for SVG and chart rendering."""
    init_db()
    with _connection() as connection:
        rows = connection.execute(
            "SELECT block, COUNT(*) AS count FROM tickets GROUP BY block"
        ).fetchall()
        counts = {b: 0 for b in BLOCKS}
        for row in rows:
            b = _normalize_block(row["block"])
            if b in counts:
                counts[b] = int(row["count"])
        return counts


def get_analytics_data() -> dict[str, Any]:
    """Retrieve full analytics data strictly from real database queries."""
    init_db()
    with _connection() as connection:
        # Category counts
        cat_rows = connection.execute(
            "SELECT category, COUNT(*) as count FROM tickets GROUP BY category ORDER BY count DESC"
        ).fetchall()
        by_category = {c: 0 for c in CATEGORIES}
        for r in cat_rows:
            if r["category"] in by_category:
                by_category[r["category"]] = int(r["count"])

        # Block counts
        by_block = get_block_issue_counts()

        # Priority counts
        pri_rows = connection.execute(
            "SELECT priority, COUNT(*) as count FROM tickets GROUP BY priority"
        ).fetchall()
        by_priority = {p: 0 for p in PRIORITIES}
        for r in pri_rows:
            if r["priority"] in by_priority:
                by_priority[r["priority"]] = int(r["count"])

        # Status counts
        st_rows = connection.execute(
            "SELECT status, COUNT(*) as count FROM tickets GROUP BY status"
        ).fetchall()
        by_status = {s: 0 for s in STATUSES}
        for r in st_rows:
            if r["status"] in by_status:
                by_status[r["status"]] = int(r["count"])

        # 30-day timeline trend
        cutoff = (datetime.now() - timedelta(days=30)).isoformat(timespec="seconds", sep=" ")
        trend_rows = connection.execute(
            """SELECT substr(created_at, 1, 10) as day, COUNT(*) as count
               FROM tickets
               WHERE created_at >= ?
               GROUP BY day
               ORDER BY day ASC""",
            (cutoff,),
        ).fetchall()
        timeline = [{"date": r["day"], "count": int(r["count"])} for r in trend_rows]

        return {
            "by_category": by_category,
            "by_block": by_block,
            "by_priority": by_priority,
            "by_status": by_status,
            "timeline": timeline,
            "metrics": get_metrics(),
        }


def add_ticket_review(ticket_id: int, rating: int, comment: str = "") -> int:
    """Store resident feedback on past resolved tickets."""
    init_db()
    if rating < 1 or rating > 5:
        raise ValueError("Rating must be between 1 and 5.")
    now = datetime.now().isoformat(timespec="seconds", sep=" ")
    with _connection() as connection:
        cursor = connection.execute(
            "INSERT INTO ticket_reviews (ticket_id, rating, comment, created_at) VALUES (?, ?, ?, ?)",
            (ticket_id, rating, comment.strip(), now),
        )
        return int(cursor.lastrowid)


def insert_sample_tickets(tickets: list[tuple]) -> None:
    """Insert development fixtures with explicit historical dates and statuses."""
    init_db()
    with _connection() as connection:
        normalized_tickets = []
        for t in tickets:
            # (issue, category, priority, department, fix, block, room, status, created, updated)
            issue, cat, pri, dept, fix, raw_block, room, status, created, updated = t
            norm_b = _normalize_block(raw_block)
            normalized_tickets.append(
                (issue, cat, pri, dept, fix, norm_b, room, status, created, updated)
            )

        connection.executemany(
            """INSERT INTO tickets
               (issue, category, priority, department, suggested_fix, block, room, status,
                report_count, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)""",
            normalized_tickets,
        )
