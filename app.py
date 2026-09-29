"""FixIt Campus Maintenance System - Main Streamlit Application Entrypoint.

Coordinates navigation between Student Reporting, Ticket Tracking,
and Campus Safety guidelines.
"""

import streamlit as st

import auth
import config
import database
import report_page

# Configure application metadata
st.set_page_config(
    page_title="FixIt - Campus Facility Maintenance",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS styling for accessible, modern campus portal UI
st.markdown(
    """
    <style>
    /* Main container clean spacing */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1000px;
    }
    /* Buttons */
    div.stButton > button:first-child {
        border-radius: 8px;
        font-weight: 600;
        padding: 0.5rem 1.25rem;
    }
    /* Sidebar header */
    .sidebar-brand {
        font-size: 1.5rem;
        font-weight: 800;
        color: #0f172a;
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 0.5rem;
    }
    .sidebar-sub {
        font-size: 0.85rem;
        color: #64748b;
        margin-bottom: 1.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_sidebar() -> str:
    """Render sidebar navigation and student session details."""
    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-brand">🔧 FixIt Campus</div>
            <div class="sidebar-sub">AI-Powered Facility & Maintenance Hub</div>
            """,
            unsafe_allow_html=True,
        )

        user = auth.get_current_user()

        with st.expander("👤 Student Profile", expanded=False):
            new_id = st.text_input("Student ID", value=user["student_id"])
            new_name = st.text_input("Full Name", value=user["name"])
            if st.button("Update Profile"):
                auth.set_current_user(new_id, new_name)
                st.success("Profile updated!")
                st.rerun()

        st.markdown("---")

        page = st.radio(
            "Navigation",
            options=["Report Issue", "Track My Tickets", "Safety & Contacts"],
            index=0,
        )

        st.markdown("---")
        st.markdown(
            f"""
            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px;">
                <span style="font-size: 12px; font-weight: 700; color: #475569; text-transform: uppercase;">Campus Security</span>
                <div style="font-size: 14px; font-weight: 800; color: #b91c1c; margin-top: 4px;">
                    📞 {config.SECURITY_CONTACT_NUMBER}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        return page


def render_ticket_tracker() -> None:
    """Render ticket tracker view showing submitted issues, status, and duplicates."""
    st.markdown(
        """
        <div style="margin-bottom: 24px;">
            <h1 style="font-weight: 800; color: #1e293b;">📋 Maintenance Tickets</h1>
            <p style="color: #64748b; font-size: 16px;">Track your submitted requests and monitor duplicate reports.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tickets = database.get_recent_tickets(limit=50)

    if not tickets:
        st.info("No maintenance tickets have been submitted yet.")
        return

    for t in tickets:
        p_badge = report_page.render_priority_badge(t["priority"])
        is_emerg = bool(t["is_emergency"])
        border_color = "#ef4444" if is_emerg else "#e2e8f0"

        st.markdown(
            f"""
            <div style="
                background: white;
                border: 1px solid {border_color};
                border-left: 5px solid {'#ef4444' if is_emerg else '#3b82f6'};
                border-radius: 8px;
                padding: 16px;
                margin-bottom: 12px;
                box-shadow: 0 1px 2px rgba(0,0,0,0.04);
            ">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div>
                        <span style="font-weight: 800; font-size: 16px; color: #0f172a;">#{t['ticket_ref']}</span>
                        <span style="color: #64748b; font-size: 14px; margin-left: 8px;">({t['block']} - {t['room']})</span>
                    </div>
                    <div>
                        {p_badge}
                    </div>
                </div>
                <div style="font-size: 15px; font-weight: 600; color: #334155; margin-bottom: 6px;">
                    {t['issue']}
                </div>
                <div style="display: flex; gap: 16px; font-size: 13px; color: #64748b;">
                    <span>🏢 <strong>Department:</strong> {t['department']}</span>
                    <span>📊 <strong>Status:</strong> {t['status']}</span>
                    <span>📑 <strong>Merged Reports:</strong> {t['duplicate_count']}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_safety_page() -> None:
    """Render campus safety guidelines and emergency directory."""
    st.markdown(
        """
        <div style="margin-bottom: 24px;">
            <h1 style="font-weight: 800; color: #b91c1c;">🚨 Campus Safety & Emergency</h1>
            <p style="color: #64748b; font-size: 16px;">Critical protocols for electrical, structural, and flooding emergencies.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    report_page.render_emergency_alert()

    st.markdown(
        """
        ### What to do during a facility hazard:
        1. **Electrical Sparks / Fire**: Clear the immediate area, do not touch electrical switches or exposed wiring, and notify campus security immediately.
        2. **Severe Flooding**: Avoid stepping into standing water near electrical sockets or power points to prevent electrocution.
        3. **Structural / Civil Damage**: Vacate the room if ceiling plaster or heavy fixtures are loose.
        """
    )


def main() -> None:
    page = render_sidebar()

    if page == "Report Issue":
        report_page.render_report_page()
    elif page == "Track My Tickets":
        render_ticket_tracker()
    elif page == "Safety & Contacts":
        render_safety_page()


if __name__ == "__main__":
    main()
