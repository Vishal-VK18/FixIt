"""CampusCare Maintenance Platform - Full-stack FastAPI application."""

import os
import logging
from io import BytesIO
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, Response, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from PIL import Image, UnidentifiedImageError

import ai_service
import auth
import db
from gemini_client import GeminiVisionError

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
logger = logging.getLogger(__name__)

STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

# Ensure database is initialized on startup
db.init_db()

app = FastAPI(
    title="CampusCare Maintenance Platform",
    description="Real campus maintenance and issue reporting platform with AI diagnostics.",
    version="1.0.0",
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
    threshold: Optional[int] = None


class StudentRegister(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    email: str = Field(..., min_length=3, max_length=254)
    student_id: str = Field(..., min_length=1, max_length=80)
    password: str = Field(..., min_length=12, max_length=256)


class LoginRequest(BaseModel):
    email: str
    password: str


def current_user(request: Request) -> dict:
    user = auth.session_user(request.cookies.get("campuscare_session"))
    if not user:
        raise HTTPException(status_code=401, detail="Sign in to continue.")
    return user


def require_student(user: dict = Depends(current_user)) -> dict:
    if user["role"] != "student":
        raise HTTPException(status_code=403, detail="Student access is required.")
    return user


def require_admin(user: dict = Depends(current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    return user


def _set_session_cookie(response: Response, token: str) -> None:
    secure = os.getenv("COOKIE_SECURE", "").lower() in ("1", "true", "yes") or os.getenv("ENVIRONMENT", "").lower() == "production"
    response.set_cookie("campuscare_session", token, max_age=auth.SESSION_HOURS * 3600,
                        httponly=True, secure=secure, samesite="lax", path="/")


def _login_page(request: Request) -> Response:
    index_file = TEMPLATES_DIR / "login.html"
    if not index_file.exists():
        return HTMLResponse("Login page unavailable.", status_code=500)
    next_path = request.query_params.get("next", "/")
    if not next_path.startswith("/") or next_path.startswith("//"):
        next_path = "/"
    return HTMLResponse(index_file.read_text(encoding="utf-8").replace("{{NEXT_PATH}}", next_path))


def _protected_page(request: Request, initial_view: str, role: str) -> Response:
    user = auth.session_user(request.cookies.get("campuscare_session"))
    if not user:
        return RedirectResponse(f"/login?next={request.url.path}", status_code=303)
    if user["role"] != role:
        return RedirectResponse("/" if user["role"] == "student" else "/maintenance-dashboard", status_code=303)
    return _render_index(initial_view)


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
async def route_root(request: Request):
    user = auth.session_user(request.cookies.get("campuscare_session"))
    role = user["role"] if user else "student"
    view = "maintenance-dashboard" if role == "admin" else "report-issue"
    return _protected_page(request, view, role)


@app.get("/login", response_class=HTMLResponse)
async def route_login(request: Request):
    return _login_page(request)


@app.post("/api/auth/register")
async def register_student(body: StudentRegister, response: Response):
    import sqlite3
    try:
        user = auth.create_account(body.name, body.email, body.password, body.student_id, role="student")
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="That email or student ID is already registered.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _set_session_cookie(response, auth.create_session(user["id"]))
    return {"success": True, "user": user}


@app.post("/api/auth/student/login")
async def student_login(body: LoginRequest, response: Response):
    user = auth.authenticate(body.email, body.password, "student")
    if not user:
        raise HTTPException(status_code=401, detail="Invalid student email or password.")
    _set_session_cookie(response, auth.create_session(user["id"]))
    return {"success": True, "user": user}


@app.post("/api/auth/admin/login")
async def admin_login(body: LoginRequest, response: Response):
    user = auth.authenticate(body.email, body.password, "admin")
    if not user:
        raise HTTPException(status_code=401, detail="Invalid admin email or password.")
    _set_session_cookie(response, auth.create_session(user["id"]))
    return {"success": True, "user": user}


@app.get("/api/auth/me")
async def who_am_i(user: dict = Depends(current_user)):
    return {"success": True, "user": user}


@app.post("/api/auth/logout")
async def logout(request: Request, response: Response):
    auth.revoke_session(request.cookies.get("campuscare_session"))
    response.delete_cookie("campuscare_session", path="/", httponly=True, samesite="lax")
    return {"success": True}


@app.get("/report-issue", response_class=HTMLResponse)
async def route_report_issue(request: Request):
    return _protected_page(request, "report-issue", "student")


@app.get("/student-dashboard", response_class=HTMLResponse)
async def route_student_dashboard(request: Request):
    return _protected_page(request, "report-issue", "student")


@app.get("/my-reports", response_class=HTMLResponse)
async def route_my_reports(request: Request):
    return _protected_page(request, "my-reports", "student")


@app.get("/maintenance-dashboard", response_class=HTMLResponse)
async def route_maintenance_dashboard(request: Request):
    return _protected_page(request, "maintenance-dashboard", "admin")


@app.get("/admin", response_class=HTMLResponse)
async def route_admin(request: Request):
    return _protected_page(request, "maintenance-dashboard", "admin")


@app.get("/predictive-maintenance", response_class=HTMLResponse)
async def route_predictive_maintenance(request: Request):
    return _protected_page(request, "predictive-maintenance", "admin")


@app.get("/maintenance-tickets", response_class=HTMLResponse)
async def route_maintenance_tickets(request: Request):
    return _protected_page(request, "maintenance-tickets", "admin")


@app.get("/analytics", response_class=HTMLResponse)
async def route_analytics(request: Request):
    return _protected_page(request, "analytics", "admin")


@app.get("/settings", response_class=HTMLResponse)
async def route_settings(request: Request):
    return _protected_page(request, "settings", "admin")


# -------------------------------------------------------------
# REST API Endpoints
# -------------------------------------------------------------

@app.post("/api/tickets")
async def create_ticket(ticket: TicketCreate, user: dict = Depends(require_student)):
    """Submit a ticket. Adheres to shared ticket contract returning (ticket_id, merged)."""
    try:
        payload = ticket.model_dump()
        ticket_id, merged = db.add_ticket(payload, owner_id=user["id"])
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
    user: dict = Depends(current_user),
):
    """Retrieve tickets with search, filtering, and priority sorting."""
    try:
        filters = dict(
            status=status,
            category=category,
            block=block,
            priority=priority,
            search=search,
            sort_by=sort_by,
        )
        tickets = db.get_tickets(**filters) if user["role"] == "admin" else db.get_tickets_for_owner(user["id"], **filters)
        return {"success": True, "count": len(tickets), "tickets": tickets}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/api/tickets/{ticket_id}")
async def get_ticket_details(ticket_id: int, user: dict = Depends(current_user)):
    """Retrieve detailed information for a single ticket."""
    ticket = db.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket #{ticket_id} not found.")
    if user["role"] == "student" and not db.owns_ticket(ticket_id, user["id"]):
        raise HTTPException(status_code=404, detail="Ticket not found.")
    return {"success": True, "ticket": ticket}


@app.patch("/api/tickets/{ticket_id}/status")
async def update_status(ticket_id: int, body: TicketStatusUpdate, _user: dict = Depends(require_admin)):
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
async def get_metrics(_user: dict = Depends(require_admin)):
    """Retrieve dynamic ticket metrics from database."""
    try:
        return {"success": True, "metrics": db.get_metrics()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/api/predictive-warnings")
async def get_predictive_warnings(threshold: Optional[int] = None, _user: dict = Depends(require_admin)):
    """Retrieve predictive maintenance warnings for 30-day grouped tickets."""
    try:
        effective_threshold = threshold if threshold is not None else int(os.getenv("PREDICTIVE_THRESHOLD", "4"))
        warnings = db.get_predictive_warnings(threshold=effective_threshold)
        return {"success": True, "threshold": effective_threshold, "warnings": warnings}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/api/predictive-patterns")
async def get_predictive_patterns(threshold: Optional[int] = None, _user: dict = Depends(require_admin)):
    """Retrieve detailed recurring patterns with correlated tickets."""
    try:
        effective_threshold = threshold if threshold is not None else int(os.getenv("PREDICTIVE_THRESHOLD", "4"))
        patterns = db.get_predictive_patterns(threshold=effective_threshold)
        return {"success": True, "threshold": effective_threshold, "patterns": patterns}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/api/hotspots")
async def get_hotspots(_user: dict = Depends(require_admin)):
    """Retrieve the Block x Category cross-tabulation matrix."""
    try:
        return {"success": True, "data": db.get_hotspot_matrix()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/api/block-counts")
async def get_block_counts(_user: dict = Depends(require_admin)):
    """Retrieve issue distribution by block."""
    try:
        return {"success": True, "counts": db.get_block_issue_counts()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/api/analytics")
async def get_analytics(_user: dict = Depends(require_admin)):
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
    _user: dict = Depends(require_student),
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
    _user: dict = Depends(require_student),
):
    """Analyze image using real AI vision service.
    
    If unconfigured, returns clean configuration error.
    Never returns fake data.
    """
    if not file:
        raise HTTPException(status_code=400, detail="An image file is required for analysis.")

    # Validate mime type
    mime_type = file.content_type or "image/jpeg"
    formats = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}
    if mime_type not in formats:
        raise HTTPException(status_code=400, detail="Upload a JPEG, PNG, or WEBP image.")

    image_bytes = await file.read()
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="The selected image file is empty.")

    # Limit file size to 10MB
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image file exceeds maximum 10MB limit.")
    try:
        image = Image.open(BytesIO(image_bytes))
        image.verify()
        if image.format != formats[mime_type]:
            raise HTTPException(status_code=400, detail="Image content does not match its file type.")
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as e:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid image.") from e

    try:
        analysis = await run_in_threadpool(ai_service.analyze_image_with_ai, image_bytes, mime_type)
        return {"success": True, "analysis": analysis}
    except GeminiVisionError as e:
        logger.warning("Gemini image analysis failed: %s", e)
        return JSONResponse(
            status_code=e.status_code,
            content={"success": False, "configured": True, "error": str(e)},
        )
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
    except Exception:
        logger.exception("Unexpected AI image analysis failure")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "configured": True,
                "error": "AI analysis failed unexpectedly. Please retry or enter the issue manually.",
            },
        )


@app.post("/api/tickets/{ticket_id}/review")
async def submit_review(ticket_id: int, review: ReviewCreate, user: dict = Depends(require_student)):
    """Submit resident resolution feedback for a resolved ticket."""
    ticket = db.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket #{ticket_id} not found.")
    if ticket["status"] != "Fixed":
        raise HTTPException(status_code=400, detail="Feedback is only available after a ticket is Fixed.")
    if not db.owns_ticket(ticket_id, user["id"]):
        raise HTTPException(status_code=404, detail="Ticket not found.")
    try:
        review_id = db.add_ticket_review(ticket_id, review.rating, review.comment or "")
        return {"success": True, "review_id": review_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/api/config")
async def get_config(_user: dict = Depends(require_admin)):
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


@app.get("/api/app-config")
async def get_app_config(_user: dict = Depends(current_user)):
    """Return safe settings used by both role-specific UI surfaces."""
    return {
        "security_contact": ai_service.get_security_contact(),
        "ai_configured": ai_service.is_ai_configured(),
        "predictive_threshold": int(os.getenv("PREDICTIVE_THRESHOLD", "4")),
        "blocks": list(db.BLOCKS),
        "categories": list(db.CATEGORIES),
        "priorities": list(db.PRIORITIES),
        "statuses": list(db.STATUSES),
    }


@app.post("/api/config")
async def update_config(config: ConfigUpdate, _user: dict = Depends(require_admin)):
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
    uvicorn.run("app:app", host=host, port=port, reload=True, reload_dirs=[str(BASE_DIR)])

