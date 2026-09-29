"""CampusCare Maintenance Platform - Full-stack FastAPI application."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import ai_service
import db

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

# Ensure database is initialized on startup
db.init_db()

app = FastAPI(
    title="CampusCare Maintenance Platform",
    description="Real campus maintenance and issue reporting platform with AI diagnostics.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class TicketCreate(BaseModel):
    issue: str = Field(..., min_length=3)
    category: str
    priority: str
    department: Optional[str] = None
    suggested_fix: Optional[str] = None
    block: str
    room: str


class TicketStatusUpdate(BaseModel):
    status: str


class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = ""


class ConfigUpdate(BaseModel):
    security_contact: Optional[str] = None
    openai_key: Optional[str] = None
    gemini_key: Optional[str] = None
    threshold: Optional[int] = None


# -------------------------------------------------------------
# Frontend Routes
# -------------------------------------------------------------

def _render_index(initial_view: str = "report-issue") -> HTMLResponse:
    index_file = TEMPLATES_DIR / "index.html"
    if not index_file.exists():
        return HTMLResponse("<h1>CampusCare UI template missing</h1>", status_code=500)
    content = index_file.read_text(encoding="utf-8")
    content = content.replace("{{INITIAL_VIEW}}", initial_view)
    return HTMLResponse(content)


@app.get("/", response_class=HTMLResponse)
async def route_root():
    return _render_index("report-issue")


@app.get("/report-issue", response_class=HTMLResponse)
async def route_report_issue():
    return _render_index("report-issue")


@app.get("/student-dashboard", response_class=HTMLResponse)
async def route_student_dashboard():
    return _render_index("report-issue")


@app.get("/my-reports", response_class=HTMLResponse)
async def route_my_reports():
    return _render_index("my-reports")


@app.get("/maintenance-dashboard", response_class=HTMLResponse)
async def route_maintenance_dashboard():
    return _render_index("maintenance-dashboard")


@app.get("/admin", response_class=HTMLResponse)
async def route_admin():
    return _render_index("maintenance-dashboard")


@app.get("/predictive-maintenance", response_class=HTMLResponse)
async def route_predictive_maintenance():
    return _render_index("predictive-maintenance")


@app.get("/maintenance-tickets", response_class=HTMLResponse)
async def route_maintenance_tickets():
    return _render_index("maintenance-tickets")


@app.get("/analytics", response_class=HTMLResponse)
async def route_analytics():
    return _render_index("analytics")


@app.get("/settings", response_class=HTMLResponse)
async def route_settings():
    return _render_index("settings")


# -------------------------------------------------------------
# REST API Endpoints
# -------------------------------------------------------------

@app.post("/api/tickets")
async def create_ticket(ticket: TicketCreate):
    """Submit a ticket. Adheres to shared ticket contract returning (ticket_id, merged)."""
    try:
        payload = ticket.model_dump()
        ticket_id, merged = db.add_ticket(payload)
        saved_ticket = db.get_ticket(ticket_id)
        return {
            "success": True,
            "ticket_id": ticket_id,
            "merged": merged,
            "ticket": saved_ticket,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/api/tickets")
async def list_tickets(
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    block: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: str = Query("priority"),
):
    """Retrieve tickets with search, filtering, and priority sorting."""
    try:
        tickets = db.get_tickets(
            status=status,
            category=category,
            block=block,
            priority=priority,
            search=search,
            sort_by=sort_by,
        )
        return {"success": True, "count": len(tickets), "tickets": tickets}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/api/tickets/{ticket_id}")
async def get_ticket_details(ticket_id: int):
    """Retrieve detailed information for a single ticket."""
    ticket = db.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket #{ticket_id} not found.")
    return {"success": True, "ticket": ticket}


@app.patch("/api/tickets/{ticket_id}/status")
async def update_status(ticket_id: int, body: TicketStatusUpdate):
    """Update ticket status and refresh updated_at."""
    try:
        success = db.update_ticket_status(ticket_id, body.status)
        if not success:
            raise HTTPException(status_code=404, detail=f"Ticket #{ticket_id} not found.")
        updated_ticket = db.get_ticket(ticket_id)
        return {"success": True, "ticket": updated_ticket}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/api/metrics")
async def get_metrics():
    """Retrieve dynamic ticket metrics from database."""
    try:
        return {"success": True, "metrics": db.get_metrics()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/api/predictive-warnings")
async def get_predictive_warnings(threshold: int = 4):
    """Retrieve predictive maintenance warnings for 30-day grouped tickets."""
    try:
        warnings = db.get_predictive_warnings(threshold=threshold)
        return {"success": True, "threshold": threshold, "warnings": warnings}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/api/predictive-patterns")
async def get_predictive_patterns(threshold: int = 4):
    """Retrieve detailed recurring patterns with correlated tickets."""
    try:
        patterns = db.get_predictive_patterns(threshold=threshold)
        return {"success": True, "patterns": patterns}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/api/hotspots")
async def get_hotspots():
    """Retrieve the Block x Category cross-tabulation matrix."""
    try:
        return {"success": True, "data": db.get_hotspot_matrix()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/api/block-counts")
async def get_block_counts():
    """Retrieve issue distribution by block."""
    try:
        return {"success": True, "counts": db.get_block_issue_counts()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/api/analytics")
async def get_analytics():
    """Retrieve full analytics charts data from database."""
    try:
        return {"success": True, "analytics": db.get_analytics_data()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/api/check-duplicate")
async def check_duplicate(
    block: str = Query(...),
    room: str = Query(...),
    category: str = Query(...),
):
    """Check if an open ticket exists for duplicate detection preview."""
    match = db.check_duplicate_open_ticket(block, room, category)
    return {
        "exists": match is not None,
        "existing_ticket": match,
    }


@app.post("/api/analyze-image")
async def analyze_image(
    file: Optional[UploadFile] = File(None),
):
    """Analyze image using real AI vision service.
    
    If unconfigured, returns clean configuration error.
    Never returns fake data.
    """
    if not file:
        raise HTTPException(status_code=400, detail="An image file is required for analysis.")

    # Validate mime type
    mime_type = file.content_type or "image/jpeg"
    if not mime_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be a valid image format.")

    image_bytes = await file.read()
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="The selected image file is empty.")

    # Limit file size to 10MB
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image file exceeds maximum 10MB limit.")

    try:
        analysis = ai_service.analyze_image_with_ai(image_bytes, mime_type)
        return {"success": True, "analysis": analysis}
    except ValueError as e:
        # Expected unconfigured credentials error
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "configured": False,
                "error": str(e),
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "configured": True,
                "error": f"AI service error: {str(e)}",
            },
        )


@app.post("/api/tickets/{ticket_id}/review")
async def submit_review(ticket_id: int, review: ReviewCreate):
    """Submit resident resolution feedback for a resolved ticket."""
    ticket = db.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket #{ticket_id} not found.")
    try:
        review_id = db.add_ticket_review(ticket_id, review.rating, review.comment or "")
        return {"success": True, "review_id": review_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/api/config")
async def get_config():
    """Retrieve platform configuration details."""
    threshold = int(os.getenv("PREDICTIVE_THRESHOLD", "4"))
    return {
        "security_contact": ai_service.get_security_contact(),
        "ai_configured": ai_service.is_ai_configured(),
        "predictive_threshold": threshold,
        "blocks": list(db.BLOCKS),
        "categories": list(db.CATEGORIES),
        "priorities": list(db.PRIORITIES),
        "statuses": list(db.STATUSES),
    }


@app.post("/api/config")
async def update_config(config: ConfigUpdate):
    """Update settings in-memory and write to .env."""
    env_path = BASE_DIR / ".env"
    existing_lines = []
    if env_path.exists():
        existing_lines = env_path.read_text(encoding="utf-8").splitlines()

    env_dict = {}
    for line in existing_lines:
        line_clean = line.strip()
        if line_clean and not line_clean.startswith("#") and "=" in line_clean:
            k, v = line_clean.split("=", 1)
            env_dict[k.strip()] = v.strip()

    if config.security_contact is not None:
        os.environ["SECURITY_CONTACT_NUMBER"] = config.security_contact.strip()
        env_dict["SECURITY_CONTACT_NUMBER"] = config.security_contact.strip()

    if config.openai_key is not None:
        os.environ["OPENAI_API_KEY"] = config.openai_key.strip()
        env_dict["OPENAI_API_KEY"] = config.openai_key.strip()

    if config.gemini_key is not None:
        os.environ["GEMINI_API_KEY"] = config.gemini_key.strip()
        env_dict["GEMINI_API_KEY"] = config.gemini_key.strip()

    if config.threshold is not None and config.threshold >= 1:
        os.environ["PREDICTIVE_THRESHOLD"] = str(config.threshold)
        env_dict["PREDICTIVE_THRESHOLD"] = str(config.threshold)

    # Write back to .env
    output_lines = [f"{k}={v}" for k, v in env_dict.items()]
    env_path.write_text("\n".join(output_lines) + "\n", encoding="utf-8")

    return {
        "success": True,
        "config": {
            "security_contact": ai_service.get_security_contact(),
            "ai_configured": ai_service.is_ai_configured(),
            "predictive_threshold": int(os.getenv("PREDICTIVE_THRESHOLD", "4")),
        },
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    print(f"Starting CampusCare Maintenance Platform on http://{host}:{port} ...")
    uvicorn.run("app:app", host=host, port=port, reload=True)

