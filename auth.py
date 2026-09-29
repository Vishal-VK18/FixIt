"""Authentication and Student Identity Module for FixIt.

Manages student session state and user identity for ticket reporting.
"""

from typing import Any, Dict


def get_current_user() -> Dict[str, Any]:
    """Retrieve the currently authenticated student session.

    Falls back to a default student profile if not already initialized in session.
    """
    default_user = {
        "student_id": "STU-2026-0842",
        "name": "Alex Rivera",
        "email": "arivera@campus.edu",
        "role": "student",
    }

    try:
        import streamlit as st

        if "user" not in st.session_state:
            st.session_state["user"] = default_user
        return st.session_state["user"]
    except Exception:
        return default_user


def set_current_user(
    student_id: str, name: str, email: str = ""
) -> Dict[str, Any]:
    """Update current user profile in the active session."""
    user = {
        "student_id": student_id.strip(),
        "name": name.strip(),
        "email": email.strip() or f"{student_id.lower()}@campus.edu",
        "role": "student",
    }
    try:
        import streamlit as st

        st.session_state["user"] = user
    except Exception:
        pass
    return user
