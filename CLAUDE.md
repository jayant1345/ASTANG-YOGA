# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup & Running

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env: set SECRET_KEY (required for production)

# Initialize DB and create first admin
flask --app run init-db
flask --app run create-admin "Admin Name" admin@example.com password123

# Run dev server
python run.py
# or
flask --app run run --debug
```

## Key Commands

| Command | Purpose |
|---|---|
| `flask --app run init-db` | Create all DB tables |
| `flask --app run create-admin "Name" email pass` | Create first admin (signup disabled) |
| `python run.py` | Start dev server on port 5000 |

## Architecture

**App Factory Pattern** — `app/__init__.py::create_app()` initializes Flask, SQLAlchemy, Flask-Login, and CSRF, then registers six blueprints.

### Blueprints

| Blueprint | Prefix | Who Uses It |
|---|---|---|
| `auth` | `/login`, `/logout` | Everyone |
| `admin` | `/admin/` | Admin only |
| `instructor` | `/instructor/` | Admin + Instructor |
| `student` | `/student/` | Student only |
| `attendance` | `/attendance/` | All authenticated |
| `tasks` | `/tasks/` | Reserved for future APIs |

### Models (`app/models.py`)

- **User** — roles: `admin`, `instructor`, `student`. `is_active` controls login access. Has `get_fee_status(class_id)` and `has_overdue_fees()`.
- **YogaClass** — instructor FK, monthly fee amount. `get_enrolled_students()` helper.
- **StudentClass** — many-to-many join. Unique constraint on `(student_id, class_id)`.
- **ClassSession** — created when instructor hits "Start Session". Holds `signed_token` (itsdangerous).
- **Attendance** — one row per student per session. `overridden_by_admin=True` bypasses fee gate.
- **FeeRecord** — `paid_for_month` is `YYYY-MM` string. Fee status computed in `User.get_fee_status()` — not stored.
- **Task / TaskSubmission** — Task targets either `assigned_to_student_id` OR `assigned_to_class_id`. Each student gets their own `TaskSubmission`.

### Fee Status Logic (`app/models.py:User.get_fee_status`)

Checks latest `FeeRecord.paid_for_month >= current_month`. If no payment:
- Day of month ≤ `GRACE_PERIOD_DAYS` → `pending`
- Day of month > `GRACE_PERIOD_DAYS` → `overdue` (blocks QR attendance)

### QR Attendance Flow

1. Instructor → `POST /instructor/session/start/<class_id>` → creates `ClassSession`, generates `itsdangerous` signed token.
2. Live page shows QR encoding `GET /attendance/verify?token=<token>` as full URL.
3. Student scans via `html5-qrcode` on `/attendance/scan` → browser navigates to verify URL.
4. `/attendance/verify` decodes token (15-min expiry), checks enrollment, checks fee status (blocks if overdue), records `Attendance` (late if > `LATE_THRESHOLD_MINUTES`).
5. Admin can override via `POST /admin/attendance/session/<id>/mark/<student_id>` — sets `overridden_by_admin=True`.

### Role Decorators (`app/decorators.py`)

- `@admin_required` — admin only
- `@instructor_required` — admin or instructor
- `@student_required` — student only
- `@fees_clear_required` — reads `class_id` from URL kwargs or query params; renders `attendance/blocked.html` if overdue

### File Uploads

Saved via `app/utils.py::save_upload(file, subfolder)` to `app/static/uploads/<subfolder>/`. Served as static files. Subfolders: `profiles`, `proofs`, `qrcodes`.

## Config

All settings flow through `config.py::Config` and `.env`:

| Var | Default | Purpose |
|---|---|---|
| `SECRET_KEY` | (required in prod) | Flask sessions + itsdangerous |
| `DATABASE_URL` | `sqlite:///astang_yoga.db` | Switch to `postgresql://...` for Postgres |
| `GRACE_PERIOD_DAYS` | `5` | Days into month before fees go overdue |
| `SESSION_TIMEOUT_MINUTES` | `15` | QR code expiry |
| `LATE_THRESHOLD_MINUTES` | `10` | Minutes after session start = late |

## Database

SQLite in dev (`instance/astang_yoga.db`). Switch to Postgres by setting `DATABASE_URL=postgresql://user:pass@host/db` in `.env`. No migration tool configured — tables are created via `db.create_all()`. Add Flask-Migrate if schema changes become frequent.
