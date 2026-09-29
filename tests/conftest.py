"""Pytest configuration and test cleanup fixtures for CampusCare."""

import pytest
import sqlite3
import db


@pytest.fixture(autouse=True)
def clean_test_tickets():
    """Clean up any temporary test rows from tickets.db before and after tests."""
    def _do_clean():
        with db._connection() as con:
            con.execute("DELETE FROM tickets WHERE room LIKE 'RM-%' OR room LIKE 'API-%' OR room LIKE 'SORT-%' OR room LIKE 'OLD-%' OR room LIKE 'REV-%'")
            con.execute("DELETE FROM ticket_reviews WHERE comment LIKE 'Fast turnaround%' OR comment LIKE 'Resident review%'")

    _do_clean()
    yield
    _do_clean()
