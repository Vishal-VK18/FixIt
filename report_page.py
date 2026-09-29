"""Student Maintenance Reporting Page for FixIt.

Provides photo capture / file upload, location entry (Block & Room),
AI vision analysis trigger, emergency alert presentation,
ticket submission, and duplicate ticket notification.
"""

import os
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from PIL import Image
import streamlit as st

import auth
import config
import database
import vision


def save_image_to_disk(image_bytes: bytes, extension: str = "jpg") -> str:
    """Safely persist an uploaded image to disk and return its relative path."""
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"report_{uuid.uuid4().hex[:10]}.{extension.lstrip('.')}"
    file_path = config.UPLOAD_DIR / filename
    with open(file_path, "wb") as f:
        f.write(image_bytes)
    return str(file_path)


def render_priority_badge(priority: str) -> str:
    """Return HTML markup for priority indicator with distinct urgency colors."""
    p_upper = (priority or "MEDIUM").upper()
    color_map = {
        "CRITICAL": {
            "bg": "#fee2e2",
            "text": "#b91c1c",
            "border": "#ef4444",
            "icon": "🚨",
        },
        "HIGH": {
            "bg": "#ffedd5",
            "text": "#c2410c",
            "border": "#f97316",
            "icon": "⚠️",
        },
        "MEDIUM": {
            "bg": "#fef3c7",
            "text": "#b45309",
            "border": "#f59e0b",
            "icon": "⚡",
        },
        "LOW": {
            "bg": "#dcfce7",
            "text": "#15803d",
            "border": "#22c55e",
            "icon": "✅",
        },
    }
    cfg = color_map.get(p_upper, color_map["MEDIUM"])

    return f"""
    <span style="
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background-color: {cfg['bg']};
        color: {cfg['text']};
        border: 1px solid {cfg['border']};
        padding: 4px 12px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 0.875rem;
        letter-spacing: 0.05em;
    ">
        <span>{cfg['icon']}</span>
        <span>{p_upper}</span>
    </span>
    """


def render_emergency_alert() -> None:
    """Render a prominent red emergency alert for urgent safety hazards."""
    security_number = config.SECURITY_CONTACT_NUMBER
    st.markdown(
        f"""
        <div style="
            background-color: #fef2f2;
            border: 2px solid #ef4444;
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
            box-shadow: 0 4px 6px -1px rgba(239, 68, 68, 0.1);
        ">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 8px;">
                <span style="font-size: 28px;">🚨</span>
                <span style="font-size: 22px; font-weight: 800; color: #991b1b; letter-spacing: 0.02em;">
                    EMERGENCY ALERT
                </span>
            </div>
            <p style="color: #7f1d1d; font-size: 16px; font-weight: 600; margin: 4px 0 12px 0;">
                This issue may present an immediate safety hazard requiring urgent action.
            </p>
            <div style="
                background-color: #fee2e2;
                border-left: 4px solid #b91c1c;
                padding: 12px 16px;
                border-radius: 6px;
            ">
                <span style="color: #991b1b; font-weight: 600; font-size: 14px; display: block; margin-bottom: 4px;">
                    Contact Campus Security immediately:
                </span>
                <span style="color: #b91c1c; font-size: 20px; font-weight: 800; font-family: monospace;">
                    📞 {security_number}
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def reset_report_form() -> None:
    """Reset session state to allow filing a fresh maintenance report."""
    for key in [
        "analysis_result",
        "current_image_bytes",
        "current_image_format",
        "submission_outcome",
        "is_analyzing",
        "is_submitting",
    ]:
        if key in st.session_state:
            del st.session_state[key]


def render_report_page() -> None:
    """Main student reporting view."""
    # Ensure database is ready
    database.init_db()

    # Identify authenticated student
    user = auth.get_current_user()

    # Header section
    st.markdown(
        """
        <div style="margin-bottom: 24px;">
            <h1 style="margin-bottom: 4px; font-weight: 800; color: #1e293b;">
                🔧 Report a Campus Issue
            </h1>
            <p style="color: #64748b; font-size: 16px; margin: 0;">
                Capture or upload a photo of the maintenance problem. Our AI will analyze the hazard, identify the category, and route it to the proper facility department.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Student Badge
    st.markdown(
        f"""
        <div style="
            display: inline-flex;
            align-items: center;
            gap: 10px;
            background: #f1f5f9;
            padding: 6px 14px;
            border-radius: 8px;
            margin-bottom: 20px;
            border: 1px solid #e2e8f0;
        ">
            <span style="color: #475569; font-size: 13px; font-weight: 600;">Reporter:</span>
            <span style="color: #0f172a; font-weight: 700; font-size: 14px;">{user['name']}</span>
            <span style="background: #e2e8f0; color: #334155; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-family: monospace;">
                {user['student_id']}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Check if a ticket submission was just completed
    if "submission_outcome" in st.session_state:
        outcome = st.session_state["submission_outcome"]
        is_duplicate = outcome["is_duplicate"]
        ticket = outcome["ticket"]

        if is_duplicate:
            st.markdown(
                f"""
                <div style="
                    background-color: #fffbeb;
                    border: 2px solid #f59e0b;
                    border-radius: 10px;
                    padding: 20px;
                    margin: 20px 0;
                ">
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                        <span style="font-size: 24px;">ℹ️</span>
                        <span style="font-size: 20px; font-weight: 700; color: #b45309;">
                            This report was merged into an existing ticket.
                        </span>
                    </div>
                    <p style="color: #92400e; font-size: 15px; margin: 6px 0 14px 0;">
                        Our system detected that an open ticket is already active for this issue at <strong>{ticket['block']} - {ticket['room']}</strong>.
                        Your report has been attached to expedite resolution.
                    </p>
                    <div style="background: white; border: 1px solid #fde68a; padding: 12px 16px; border-radius: 6px;">
                        <div style="font-size: 16px; font-weight: 700; color: #78350f;">
                            Existing Ticket Reference: <span style="font-family: monospace; color: #b45309;">#{ticket['ticket_ref']}</span>
                        </div>
                        <div style="font-size: 14px; color: #92400e; margin-top: 4px;">
                            Department: <strong>{ticket['department']}</strong> | Status: <strong>{ticket['status']}</strong> | Reports Count: <strong>{ticket['duplicate_count']}</strong>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div style="
                    background-color: #f0fdf4;
                    border: 2px solid #22c55e;
                    border-radius: 10px;
                    padding: 20px;
                    margin: 20px 0;
                ">
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                        <span style="font-size: 24px;">✅</span>
                        <span style="font-size: 20px; font-weight: 700; color: #15803d;">
                            Ticket submitted successfully.
                        </span>
                    </div>
                    <p style="color: #166534; font-size: 15px; margin: 6px 0 14px 0;">
                        Your maintenance request has been registered and dispatched.
                    </p>
                    <div style="background: white; border: 1px solid #bbf7d0; padding: 12px 16px; border-radius: 6px;">
                        <div style="font-size: 16px; font-weight: 700; color: #14532d;">
                            Generated Ticket Reference: <span style="font-family: monospace; color: #16a34a;">#{ticket['ticket_ref']}</span>
                        </div>
                        <div style="font-size: 14px; color: #166534; margin-top: 4px;">
                            Assigned Department: <strong>{ticket['department']}</strong> | Priority: <strong>{ticket['priority']}</strong>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        if st.button("Submit Another Issue", type="primary"):
            reset_report_form()
            st.rerun()
        return

    # Section 1: Location Entry
    st.subheader("1. Location Information")
    col1, col2 = st.columns(2)

    with col1:
        block = st.selectbox(
            "Campus Block *",
            options=config.BLOCKS,
            index=0,
            help="Select the campus facility or residential block where the issue is located.",
        )

    with col2:
        room = st.text_input(
            "Room / Specific Location *",
            placeholder="e.g. Room 204, Chemistry Lab 3, 2nd Floor Restroom",
            help="Enter the exact room number, laboratory, or area.",
        )

    st.markdown("---")

    # Section 2: Photo Input (Both File Upload and Camera Capture)
    st.subheader("2. Issue Photo")
    st.caption("Provide an image of the problem via camera capture or file upload.")

    input_mode = st.radio(
        "Choose image input method:",
        options=["File Upload", "Camera Capture"],
        horizontal=True,
    )

    image_bytes: Optional[bytes] = None
    image_format = "JPEG"

    if input_mode == "File Upload":
        uploaded_file = st.file_uploader(
            "Upload an image (JPG, PNG, WEBP)",
            type=["jpg", "jpeg", "png", "webp"],
            help="Select a photo of the maintenance problem from your device.",
        )
        if uploaded_file is not None:
            image_bytes = uploaded_file.getvalue()
            # Determine format
            if uploaded_file.name.lower().endswith(".png"):
                image_format = "PNG"
            elif uploaded_file.name.lower().endswith(".webp"):
                image_format = "WEBP"
    else:
        camera_photo = st.camera_input("Take a photo of the maintenance issue")
        if camera_photo is not None:
            image_bytes = camera_photo.getvalue()
            image_format = "JPEG"

    # Image Preview
    if image_bytes:
        st.session_state["current_image_bytes"] = image_bytes
        st.session_state["current_image_format"] = image_format

        try:
            pil_img = Image.open(io.BytesIO(image_bytes))
            st.image(
                pil_img,
                caption=f"Selected Photo Preview ({pil_img.size[0]}x{pil_img.size[1]} px)",
                use_container_width=True,
            )
        except Exception:
            st.error("The selected file could not be rendered as an image.")
            image_bytes = None
    elif "current_image_bytes" in st.session_state:
        image_bytes = st.session_state["current_image_bytes"]
        image_format = st.session_state.get("current_image_format", "JPEG")
        st.image(
            Image.open(io.BytesIO(image_bytes)),
            caption="Selected Photo Preview",
            use_container_width=True,
        )

    st.markdown("---")

    # Section 3: Analyze Button
    st.subheader("3. AI Hazard & Issue Analysis")

    # Disable button during operations to prevent duplicate clicks
    is_busy = st.session_state.get("is_analyzing", False) or st.session_state.get(
        "is_submitting", False
    )

    analyze_clicked = st.button(
        "🔍 Analyze",
        type="primary",
        disabled=is_busy,
        help="Run AI Vision inspection on the photo to detect the issue, hazard level, and department.",
    )

    if analyze_clicked:
        # Step 1: Validation
        if not image_bytes:
            st.error("⚠️ Please upload or capture an image before analyzing.")
            return

        if not room or not room.strip():
            st.error(
                "⚠️ Please specify the Room Number / Area before running analysis."
            )
            return

        # Step 2: Run Analysis with Loading State
        st.session_state["is_analyzing"] = True
        try:
            with st.spinner(
                "Analyzing image with Vision AI... Inspecting hazard indicators & routing..."
            ):
                result = vision.analyze_image(image_bytes)
                st.session_state["analysis_result"] = result
        except Exception as exc:
            st.error(f"Analysis error: {exc}")
            st.session_state["analysis_result"] = vision.get_safe_fallback()
        finally:
            st.session_state["is_analyzing"] = False
            st.rerun()

    # Section 4: Display Analysis Results (Only if analyzed)
    if "analysis_result" in st.session_state:
        result = st.session_state["analysis_result"]
        is_emergency = result.get("is_emergency", False)

        st.markdown("### AI Analysis Result")

        # Emergency UI
        if is_emergency:
            render_emergency_alert()

        # Result Details Card
        priority_html = render_priority_badge(result.get("priority", "MEDIUM"))

        st.markdown(
            f"""
            <div style="
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                padding: 24px;
                margin: 16px 0 24px 0;
                box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
            ">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px; margin-bottom: 20px;">
                    <div>
                        <span style="font-size: 13px; font-weight: 600; color: #64748b; text-transform: uppercase;">Category</span>
                        <div style="font-size: 18px; font-weight: 700; color: #0f172a; margin-top: 4px;">
                            {result.get('category', 'Other')}
                        </div>
                    </div>
                    <div>
                        <span style="font-size: 13px; font-weight: 600; color: #64748b; text-transform: uppercase;">Priority</span>
                        <div style="margin-top: 4px;">
                            {priority_html}
                        </div>
                    </div>
                    <div>
                        <span style="font-size: 13px; font-weight: 600; color: #64748b; text-transform: uppercase;">Assigned Department</span>
                        <div style="font-size: 18px; font-weight: 700; color: #0f172a; margin-top: 4px;">
                            🏢 {result.get('department', 'General Maintenance')}
                        </div>
                    </div>
                </div>
                <div style="border-top: 1px solid #f1f5f9; padding-top: 16px; margin-bottom: 16px;">
                    <span style="font-size: 13px; font-weight: 600; color: #64748b; text-transform: uppercase;">Identified Issue</span>
                    <div style="font-size: 16px; color: #1e293b; font-weight: 600; margin-top: 4px;">
                        {result.get('issue', 'Unspecified')}
                    </div>
                </div>
                <div style="border-top: 1px solid #f1f5f9; padding-top: 16px;">
                    <span style="font-size: 13px; font-weight: 600; color: #64748b; text-transform: uppercase;">Suggested Fix</span>
                    <div style="font-size: 15px; color: #475569; margin-top: 4px;">
                        💡 {result.get('suggested_fix', 'Inspect and resolve.')}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Optional notes input
        additional_notes = st.text_area(
            "Additional Notes (Optional)",
            placeholder="Add any helpful details for the maintenance crew (e.g., best time to access, noise levels)...",
        )

        st.markdown("---")

        # Section 5: Submit Ticket
        st.subheader("4. Submit Maintenance Ticket")

        submit_disabled = st.session_state.get(
            "is_submitting", False
        ) or st.session_state.get("is_analyzing", False)

        submit_clicked = st.button(
            "📤 Submit Ticket",
            type="primary",
            disabled=submit_disabled,
            help="Submit this analyzed report to the campus facility management system.",
        )

        if submit_clicked:
            if not image_bytes:
                st.error("Photo is missing. Please select a photo again.")
                return

            if not room or not room.strip():
                st.error("Room location is missing.")
                return

            st.session_state["is_submitting"] = True
            try:
                with st.spinner("Submitting ticket & checking for duplicates..."):
                    # 1. Save photo to uploads directory
                    saved_path = save_image_to_disk(
                        image_bytes,
                        extension="png" if image_format == "PNG" else "jpg",
                    )

                    # 2. Build ticket payload
                    ticket_payload = {
                        "student_id": user["student_id"],
                        "student_name": user["name"],
                        "block": block,
                        "room": room.strip(),
                        "issue": result["issue"],
                        "category": result["category"],
                        "priority": result["priority"],
                        "department": result["department"],
                        "suggested_fix": result["suggested_fix"],
                        "is_emergency": result["is_emergency"],
                        "image_path": saved_path,
                        "notes": additional_notes.strip()
                        if additional_notes
                        else "",
                    }

                    # 3. Create or merge ticket
                    is_dup, ticket_record = database.create_or_merge_ticket(
                        ticket_payload
                    )

                    st.session_state["submission_outcome"] = {
                        "is_duplicate": is_dup,
                        "ticket": ticket_record,
                    }
            except Exception as exc:
                st.error(f"Failed to submit ticket: {exc}")
            finally:
                st.session_state["is_submitting"] = False
                st.rerun()
