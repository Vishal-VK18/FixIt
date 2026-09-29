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
    """Create the ticket and reviews tables and required indexes."""
    with _connection() as connection:
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

        # Performance indexes as required by spec #34
        connection.execute("CREATE INDEX IF NOT EXISTS idx_tickets_block ON tickets(block);")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_tickets_room ON tickets(room);")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_tickets_category ON tickets(category);")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_tickets_priority ON tickets(priority);")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_tickets_created_at ON tickets(created_at);")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_tickets_open_lookup ON tickets(block, room, category, status);")

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


def add_ticket(t: dict) -> tuple[int, bool]:
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
    department = t.get("department")
    if not department or not str(department).strip():
        department = DEPARTMENT_MAP.get(category, "General Campus Operations")
    else:
        department = str(department).strip()

    suggested_fix = t.get("suggested_fix")
    if suggested_fix is not None and not isinstance(suggested_fix, str):
        raise ValueError("'suggested_fix' must be a string.")
    suggested_fix = suggested_fix.strip() if suggested_fix else None

    raw_block = _required_text(t, "block")
    block = _normalize_block(raw_block)
    room = _required_text(t, "room")

    if category not in CATEGORIES:
        raise ValueError(f"Invalid category '{category}'. Choose one of: {', '.join(CATEGORIES)}.")
    if priority not in PRIORITIES:
        raise ValueError(f"Invalid priority '{priority}'. Choose one of: {', '.join(PRIORITIES)}.")

    now = datetime.now().isoformat(timespec="seconds", sep=" ")
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
            return int(existing["id"]), True

        cursor = connection.execute(
            """INSERT INTO tickets
               (issue, category, priority, department, suggested_fix, block, room, status,
                report_count, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'Reported', 1, ?, ?)""",
            (issue, category, priority, department, suggested_fix, block, room, now, now),
        )
        return int(cursor.lastrowid), False


def get_tickets(
    status: str | None = None,
    category: str | None = None,
    block: str | None = None,
    priority: str | None = None,
    search: str | None = None,
    sort_by: str = "priority",
) -> list[dict]:
    """Retrieve tickets with optional filtering and priority sorting."""
    init_db()
    if status is not None and status != "All" and status not in STATUSES:
        raise ValueError(f"Invalid status. Choose one of: {', '.join(STATUSES)}.")

    conditions = []
    params: list[Any] = []

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
    now = datetime.now().isoformat(timespec="seconds", sep=" ")
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

            pattern_id = f"PTN-2026-{block.replace('Block ', '')}{idx+1:02d}"

            results.append(
                {
                    "id": pattern_id,
                    "block": block,
                    "category": category,
                    "count": count,
                    "message": w["message"],
                    "root_cause": root_cause_map.get(category, f"Correlated component degradation in {block}."),
                    "recommended_action": recommended_action_map.get(
                        category, f"Schedule comprehensive inspection for {block}."
                    ),
                    "confidence": min(85 + count * 2, 98),
                    "severity": "CRITICAL" if count >= 6 or category == "Electrical" else "HIGH",
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
