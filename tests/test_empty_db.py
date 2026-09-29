"""Verify clean behavior and proper empty states when the database contains no tickets."""

from pathlib import Path
import sqlite3
import pytest
import db


def test_empty_database_behavior(tmp_path):
    """Ensure database returns proper zero/empty states without crashing when empty."""
    temp_db = tmp_path / "empty_tickets.db"
    
    # Temporarily point db to empty_db
    orig_path = db.DB_PATH
    db.DB_PATH = temp_db
    try:
        db.init_db()

        # 1. Metrics on empty DB
        metrics = db.get_metrics()
        assert metrics == {"total": 0, "open": 0, "critical_open": 0, "fixed": 0}

        # 2. Predictive warnings on empty DB
        warnings = db.get_predictive_warnings(threshold=4)
        assert warnings == []

        # 3. Hotspot matrix on empty DB
        matrix_data = db.get_hotspot_matrix()
        assert matrix_data["total_tickets"] == 0
        for block in matrix_data["blocks"]:
            for cat in matrix_data["categories"]:
                assert matrix_data["matrix"][block][cat] == 0

        # 4. Block counts on empty DB
        counts = db.get_block_issue_counts()
        for block in db.BLOCKS:
            assert counts[block] == 0

        # 5. Tickets list on empty DB
        tickets = db.get_tickets()
        assert tickets == []

        # 6. Analytics on empty DB
        analytics = db.get_analytics_data()
        assert analytics["metrics"]["total"] == 0
        assert sum(analytics["by_category"].values()) == 0

    finally:
        db.DB_PATH = orig_path
