"""Streamlit admin dashboard for campus maintenance tickets."""

import sqlite3

import pandas as pd
import streamlit as st

import db


PRIORITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
PRIORITY_COLORS = {"CRITICAL": "#b42318", "HIGH": "#d97706", "MEDIUM": "#2563eb", "LOW": "#16803c"}


def _heat_color(value: int) -> str:
    if not value:
        return "background-color: #f3f4f6; color: #6b7280"
    strength = min(value / 6, 1)
    red, green, blue = 254, int(243 - 90 * strength), int(199 - 155 * strength)
    return f"background-color: rgb({red}, {green}, {blue}); color: #1f2937"


def render_dashboard() -> None:
    st.title("Campus Maintenance Dashboard")
    st.caption("Monitor reported issues, identify hotspots, and track maintenance activity.")

    metrics = db.get_metrics()
    columns = st.columns(4)
    for column, label, key in zip(columns, ("Total Tickets", "Open Tickets", "Critical Open", "Fixed Tickets"), ("total", "open", "critical_open", "fixed")):
        column.metric(label, metrics[key])

    st.subheader("Predictive Maintenance")
    warnings = db.get_predictive_warnings()
    if warnings:
        for warning in warnings:
            st.warning(warning["message"], icon="⚠️")
    else:
        st.info("No predictive maintenance warnings at this time.")

    st.subheader("Issue Hotspots")
    hotspot_data = db.get_hotspot_data()
    if hotspot_data:
        matrix = pd.DataFrame(0, index=sorted({row["block"] for row in hotspot_data}), columns=db.CATEGORIES)
        matrix.index.name = "Block"
        for row in hotspot_data:
            matrix.loc[row["block"], row["category"]] = row["count"]
        st.caption("Block x Category | all recorded tickets")
        st.dataframe(matrix.style.map(_heat_color), use_container_width=True)
        st.subheader("Issues by Block")
        block_counts = db.get_block_issue_counts()
        st.bar_chart(pd.Series(block_counts, name="Number of Issues"), x_label="Block", y_label="Number of Issues")
    else:
        st.info("No tickets to display yet.")

    st.subheader("Tickets")
    status_filter = st.selectbox("Filter by status", ("All", *db.STATUSES), key="ticket_status_filter")
    tickets = db.get_tickets(None if status_filter == "All" else status_filter)
    if tickets:
        frame = pd.DataFrame(tickets)
        frame["_priority_order"] = frame["priority"].map(PRIORITY_ORDER)
        frame = frame.sort_values(["_priority_order", "updated_at"], ascending=[True, False])
        st.dataframe(
            frame[["id", "issue", "category", "priority", "department", "block", "room", "status", "report_count", "created_at", "updated_at"]]
            .rename(columns={"id": "ID", "issue": "Issue", "category": "Category", "priority": "Priority", "department": "Department", "block": "Block", "room": "Room", "status": "Status", "report_count": "Reports", "created_at": "Created", "updated_at": "Updated"})
            .style.map(lambda value: f"color: {PRIORITY_COLORS.get(value, '#111827')}; font-weight: 700"),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No tickets match this status.")

    st.subheader("Manage Ticket")
    if not tickets:
        st.caption("There are no tickets available to update.")
        return
    labels = {item["id"]: f"#{item['id']} - {item['issue']}" for item in tickets}
    selected_id = st.selectbox("Select Ticket", list(labels), format_func=labels.get, key="manage_ticket_id")
    selected = db.get_ticket(selected_id)
    if selected:
        st.write(f"**{selected['category']} | {selected['priority']}** | Block {selected['block']}, Room {selected['room']} | {selected['department']}")
        st.write(selected["issue"])
        st.caption(f"Suggested fix: {selected['suggested_fix'] or 'Not provided'}")
        new_status = st.selectbox("Status", db.STATUSES, index=db.STATUSES.index(selected["status"]), key=f"status_{selected_id}")
        if st.button("Update Status", type="primary"):
            try:
                if db.update_ticket_status(selected_id, new_status):
                    st.success(f"Ticket #{selected_id} status updated successfully.")
                    st.rerun()
                st.error(f"Ticket #{selected_id} was not found.")
            except (ValueError, sqlite3.Error) as error:
                st.error(f"Could not update ticket status: {error}")


if __name__ == "__main__":
    try:
        render_dashboard()
    except sqlite3.Error:
        st.error("The ticket database could not be read. Please try again or contact the application administrator.")
