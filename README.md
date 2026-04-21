# Astang Yoga — Attendance & Class Management System

A web-based management system for yoga studios. Handles student registration, batch attendance via QR codes, fee tracking, and task assignments.

---

## Features

- **QR Attendance** — Each batch has a permanent QR code. Students scan to mark attendance when a session is active. Late arrival detected automatically.
- **Student Registration** — Students self-register by scanning a static QR → fill form → admin approves → account created.
- **9 Batch Classes** — Morning (06:15–11:15) and Evening (05:15–07:15) batches pre-configured.
- **Fee Management** — Monthly fee tracking with grace period. Overdue fees block QR attendance.
- **Task Assignment** — Instructors assign yoga tasks to individual students or entire batches.
- **Role-Based Access** — Admin, Instructor, and Student roles with separate dashboards.
- **Wall Display** — Full-screen QR display page for tablets/TVs mounted in the studio (no login required).
- **Password Reset** — Admin generates a one-time reset link for students.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.13 / Flask 3.0.3 |
| Database | SQLite (dev) / PostgreSQL (production) |
| ORM | Flask-SQLAlchemy 3.1.1 |
| Auth | Flask-Login 0.6.3 |
| Forms | Flask-WTF + WTForms |
| QR Codes | qrcode + Pillow |
| Tokens | itsdangerous (signed, permanent class tokens) |
| Frontend | Bootstrap 5.3 + Bootstrap Icons |

---

## Project Structure

```
Astang Yoga/
├── app/
│   ├── __init__.py          # App factory, blueprint registration
│   ├── models.py            # All DB models
│   ├── utils.py             # QR generation, token helpers, CSV export
│   ├── decorators.py        # @admin_required, @instructor_required, etc.
│   ├── auth/                # Login, logout, register, password reset
│   ├── admin/               # User/class/fee/attendance management
│   ├── instructor/          # Session start/end, live view, tasks
│   ├── student/             # Student dashboard, task submissions
│   ├── attendance/          # QR verify, wall display
│   ├── static/css/style.css # Saffron yoga theme
│   └── templates/           # Jinja2 HTML templates
├── config.py                # All configuration via environment variables
├── run.py                   # Dev server entry point (port 8001)
├── requirements.txt
└── .env                     # Local secrets (not committed)
```

---

## Local Setup

### 1. Clone and create virtual environment

```bash
git clone <repo-url>
cd "Astang Yoga"
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
SECRET_KEY=your-very-secret-key-here
DATABASE_URL=sqlite:///astang_yoga.db
GRACE_PERIOD_DAYS=5
LATE_THRESHOLD_MINUTES=10
```

### 4. Initialize database and create admin

```bash
flask --app run init-db
flask --app run create-admin "Your Name" admin@example.com yourpassword
```

### 5. Run the development server

```bash
python run.py
```

App runs at: `http://localhost:8001`

---

## Login URLs

| Role | URL |
|---|---|
| All users | `http://localhost:8001/auth/login` |
| Admin dashboard | `http://localhost:8001/admin/` |
| Instructor dashboard | `http://localhost:8001/instructor/` |
| Student dashboard | `http://localhost:8001/student/dashboard` |

---

## Attendance QR Flow

1. **Admin/Instructor** starts a session from the dashboard.
2. **Wall tablet** shows the batch QR at `/attendance/class/<id>/display` (no login needed).
3. **Student** scans QR → logs in → attendance marked automatically.
   - Within 10 min of session start → **Present**
   - After 10 min → **Late**
   - Fee overdue → **Blocked**
4. Instructor sees live attendance on the session page (auto-refreshes every 20s).

---

## Batch QR Display URLs (bookmark on tablets)

| Batch | URL |
|---|---|
| Morning 06:15 | `/attendance/class/1/display` |
| Morning 07:15 | `/attendance/class/2/display` |
| Morning 08:15 | `/attendance/class/3/display` |
| Morning 09:15 | `/attendance/class/4/display` |
| Morning 10:15 | `/attendance/class/5/display` |
| Morning 11:15 | `/attendance/class/6/display` |
| Evening 05:15 | `/attendance/class/7/display` |
| Evening 06:15 | `/attendance/class/8/display` |
| Evening 07:15 | `/attendance/class/9/display` |

---

## Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | *(required)* | Flask sessions + token signing |
| `DATABASE_URL` | `sqlite:///astang_yoga.db` | Switch to `postgresql://...` for production |
| `GRACE_PERIOD_DAYS` | `5` | Days into month before fees go overdue |
| `SESSION_TIMEOUT_MINUTES` | `15` | Unused (class tokens are permanent) |
| `LATE_THRESHOLD_MINUTES` | `10` | Minutes after session start = late |

---

## Production Deployment (Railway)

### 1. Add these files to the project root

**`Procfile`**
```
web: gunicorn "app:create_app()" --bind 0.0.0.0:$PORT
```

**`runtime.txt`**
```
python-3.13.5
```

### 2. Set environment variables on Railway

```
SECRET_KEY=<strong-random-key>
DATABASE_URL=<railway-postgres-url>
FLASK_ENV=production
```

### 3. Switch to PostgreSQL

Set `DATABASE_URL` to the Railway PostgreSQL connection string — the app uses SQLAlchemy and works with both SQLite and PostgreSQL without code changes.

---

## Default Fees

- Monthly fee per batch: **₹2,500/month**
- Grace period: **5 days** from start of month
- After grace period: fee status becomes **Overdue** and QR attendance is blocked

---

## License

Private — Astang Yoga School. All rights reserved.
