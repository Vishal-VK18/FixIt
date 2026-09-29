# CampusCare Maintenance Platform

**CampusCare** is an intelligent, full-stack campus maintenance and civic utility operations platform. It features real persistent SQLite storage, browser-based camera and image capture, AI vision diagnostics (with strict unconfigured notifications), automated duplicate ticket detection with priority escalation, a live heatmap matrix, predictive maintenance pattern analysis, and an operations dashboard adhering to the Stitch-designed civic utility theme.

---

## 🚀 Key Features

### 1. Student Issue Reporting & AI Diagnostics
- **Photo Upload & Camera Capture**: Live HTML5 camera preview, snap frame, retake, and image drag-and-drop.
- **Real AI Vision Analysis**: Powered by Google Gemini Vision using server-side `GEMINI_API_KEY`. Extracts issue title, category, priority, suggested fix, and emergency status.
- **Strict No-Fake-Fallbacks**: If `GEMINI_API_KEY` is missing, the application reports the configuration error without generating fake predictions.
- **Severe Safety Alert**: When emergency hazards (fire, sparks, exposed wires, live water leaks near electricity) are detected, displays an emergency banner with configurable `SECURITY_CONTACT_NUMBER`. If unconfigured, clearly states *"Security contact number not configured."*
- **Campus Block & Room Validation**: Validated residential facilities (`Block A`, `Block B`, `Block C`, `Block D`, `Block E`).
- **Live Duplicate Detection Preview**: Real-time checking against the database to alert students if a matching open ticket already exists in the same room.
- **Shared Ticket Contract**: Implements `add_ticket(t) -> (ticket_id, merged)`.

### 2. Duplicate Detection & Escalation Engine
- Checks for an existing open ticket (`Reported` or `Assigned`) matching the same `block`, `room`, and `category`.
- If matched: Increments `report_count += 1`, escalates priority (`LOW` → `MEDIUM` → `HIGH` → `CRITICAL`), updates `updated_at`, and returns `(existing_ticket_id, True)`.
- If no open match: Creates a new ticket with status `Reported` and returns `(new_ticket_id, False)`.
- **Fixed Ticket Rule**: A `Fixed` ticket never blocks a new report—submitting for the same location after resolution creates a fresh new ticket.

### 3. Student My Reports & Ticket Tracker
- Real database metrics: Total Reports, Open Tickets, In Progress, Fixed & Resolved.
- Dynamic filtering by search query, status (`Reported`, `Assigned`, `Fixed`), category, and sorting.
- Sticky live ticket preview drawer with real-time maintenance timeline.
- Resolution rating widget for resolved tickets storing ratings and feedback in SQLite.

### 4. Admin Maintenance Operations Dashboard
- 4 Bento Metric Cards: Total Tickets, Open Tickets, Critical Open, Fixed Tickets.
- Predictive Maintenance Alert Banner: Evaluates the last 30 days and dynamically triggers warnings when recurring issues meet threshold.
- Maintenance Hotspots Heatmap: Block × Category matrix with real intensity scaling and click-to-filter capability.
- Issues by Campus Block SVG Bar Chart: Rendered with live database counts and standout highlight on the highest wing.
- Active Priority Tickets Table: Fast-track quick action status updates (`Reported` → `Assigned` → `Fixed`).

### 5. Predictive Maintenance Engine
- Evaluates 30-day ticket patterns grouped by block and category (default threshold: 4 issues).
- Generates dynamic pattern cards showing root cause hypotheses, recommended actions, and correlated student tickets.
- Diagnostics scan button to re-evaluate campus telemetry.

### 6. Admin Ticket Directory & Analytics
- Complete searchable, filterable table with status editing modal.
- Analytics charts broken down by Block, Category, Priority, and Status.
- Settings page to configure emergency contacts, AI API keys, and predictive thresholds.

---

## 🛠️ Technology Stack
- **Backend**: Python 3.12, FastAPI, Uvicorn, SQLite 3, Pydantic v2
- **Frontend**: Stitch-generated HTML5 UI, Tailwind CSS (Design Tokens & Color Palette: `#8FBFE3` Icy Blue, `#F6EBC3` Buttermilk, `#1b1c19` Slate), Material Symbols Outlined, Inter typography
- **AI Diagnostics**: Google Gemini Vision (`gemini-3.8-flash`)
- **Testing**: Pytest, FastAPI TestClient

---

## 📦 Installation & Setup

1. **Clone / Navigate to Project Directory**:
   ```powershell
   cd D:\FixIt
   ```

2. **Install Dependencies**:
   ```powershell
   py -m pip install -r FixIt/requirements.txt
   ```

3. **Configure Environment Variables**:
   Copy `.env.example` to `.env` in `FixIt/`:
   ```powershell
   cp FixIt/.env.example FixIt/.env
   ```

   Edit `FixIt/.env` to provide optional credentials:
   ```env
   PORT=8000
   HOST=0.0.0.0
   SECURITY_CONTACT_NUMBER=555-0199
   GEMINI_API_KEY=your_gemini_api_key_here
   GEMINI_MODEL=gemini-3.8-flash
   GEMINI_TIMEOUT_SECONDS=60
   PREDICTIVE_THRESHOLD=4
   ```

---

## ▶️ Running the Application

Start the web application from `D:\FixIt` or `D:\FixIt\FixIt`:

```powershell
# From D:\FixIt
py app.py

# Or from D:\FixIt\FixIt
cd FixIt
py app.py
```

The application will be live at:
👉 **`http://localhost:8000`**

### Available Routes:
- Student Report Issue: `http://localhost:8000/report-issue`
- Student My Reports: `http://localhost:8000/my-reports`
- Admin Maintenance Dashboard: `http://localhost:8000/maintenance-dashboard`
- Admin Predictive Maintenance: `http://localhost:8000/predictive-maintenance`
- Admin Maintenance Tickets: `http://localhost:8000/maintenance-tickets`
- Campus Analytics: `http://localhost:8000/analytics`
- Platform Settings: `http://localhost:8000/settings`
- Interactive API Docs (Swagger): `http://localhost:8000/docs`

---

## 🧪 Running Automated Tests

Run the test suite to verify database contracts, duplicate escalation, and AI behavior:

```powershell
cd D:\FixIt\FixIt
py -m pytest -v
```
