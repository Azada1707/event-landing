"""Event registration landing — Flask application.

Routes
------
GET  /                        Landing page
GET  /privacy                 Privacy policy
POST /api/register            Create a registration (JSON)
GET  /api/registrations       Guest list as JSON (CRM-ready, admin auth)
GET  /admin                   Admin panel (guest list)
GET  /admin/export.csv        Guest list as CSV
GET  /admin/export.xlsx       Guest list as Excel workbook

Run:  python app.py   (or: flask --app app run)
"""

from __future__ import annotations

import csv
import functools
import io
import os
import re
import secrets
from datetime import datetime, timezone

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from flask import (
    Flask,
    Response,
    jsonify,
    render_template,
    request,
    send_file,
)

import db

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Simple HTTP-Basic credential for the admin panel / guest list.
# Override ADMIN_USER / ADMIN_PASSWORD in the environment for production.
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
# Maximum registrations allowed from one IP per window, to limit abuse.
RATE_LIMIT_MAX = 5
RATE_LIMIT_WINDOW = 60 * 60  # seconds
# A registration form must be a recent issue; used for a light CSRF defence.
CSRF_TTL = 60 * 30  # 30 minutes

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY", secrets.token_hex(32)
)
# Emit real UTF-8 (not \uXXXX escapes) in JSON responses.
app.json.ensure_ascii = False

# Ensure the schema exists as soon as the app is imported (covers gunicorn/WSGI,
# which do not run the `__main__` block). Idempotent (CREATE TABLE IF NOT EXISTS).
db.init_db()

# In-memory request throttle: {ip: [epoch_seconds, ...]}
_attempts: dict[str, list[float]] = {}

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# Accepts international and local formats: +7 ..., 8 ..., with spaces/dashes/parens.
PHONE_RE = re.compile(r"^\+?[0-9][0-9\s\-()]{6,24}$")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean(value: str | None) -> str:
    """Trim and collapse whitespace; never trust raw input."""
    if value is None:
        return ""
    return " ".join(str(value).split())


def _check_rate_limit(ip: str) -> bool:
    window_start = datetime.now(timezone.utc).timestamp() - RATE_LIMIT_WINDOW
    stamps = [t for t in _attempts.get(ip, []) if t > window_start]
    if len(stamps) >= RATE_LIMIT_MAX:
        return False
    stamps.append(datetime.now(timezone.utc).timestamp())
    _attempts[ip] = stamps
    return True


def require_admin():
    """HTTP Basic auth guard for admin/guest-list endpoints."""

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            auth = request.authorization
            if not (
                auth
                and secrets.compare_digest(auth.username or "", ADMIN_USER)
                and secrets.compare_digest(auth.password or "", ADMIN_PASSWORD)
            ):
                return Response(
                    "Для доступа требуются учетные данные администратора.",
                    401,
                    {"WWW-Authenticate": 'Basic realm="Event Admin"'},
                )
            return fn(*args, **kwargs)

        return wrapper

    return decorator


# --------------------------------------------------------------------------- #
# Pages
# --------------------------------------------------------------------------- #
@app.get("/")
def index():
    return render_template("index.html")


@app.get("/privacy")
def privacy():
    return render_template("privacy.html")


# --------------------------------------------------------------------------- #
# Registration API
# --------------------------------------------------------------------------- #
@app.post("/api/register")
def register():
    ip = request.remote_addr or "unknown"
    if not _check_rate_limit(ip):
        return jsonify({"ok": False, "error": "Слишком много запросов. Попробуйте позже."}), 429

    payload = request.get_json(silent=True) or {}

    first_name = clean(payload.get("first_name"))
    last_name = clean(payload.get("last_name"))
    company = clean(payload.get("company"))
    position = clean(payload.get("position"))
    phone = clean(payload.get("phone"))
    email = clean(payload.get("email")).lower()
    comments = clean(payload.get("comments"))
    consent = payload.get("consent") in (True, "true", "on", 1, "1")

    errors: dict[str, str] = {}
    if len(first_name) < 2:
        errors["first_name"] = "Укажите имя (минимум 2 символа)."
    if len(last_name) < 2:
        errors["last_name"] = "Укажите фамилию (минимум 2 символа)."
    if len(company) < 2:
        errors["company"] = "Укажите название компании."
    if len(position) < 2:
        errors["position"] = "Укажите должность."
    if not PHONE_RE.match(phone):
        errors["phone"] = "Укажите корректный номер телефона."
    if not EMAIL_RE.match(email):
        errors["email"] = "Укажите корректный адрес электронной почты."
    if not consent:
        errors["consent"] = "Необходимо согласие на обработку персональных данных."

    if errors:
        return jsonify({"ok": False, "errors": errors}), 422

    if db.email_exists(email):
        return jsonify(
            {
                "ok": False,
                "error": "Регистрация с таким e-mail уже существует. "
                "Свяжитесь с организаторами, если это ошибка.",
            }
        ), 409

    db.insert_registration(
        {
            "first_name": first_name,
            "last_name": last_name,
            "company": company,
            "position": position,
            "phone": phone,
            "email": email,
            "comments": comments,
            "consent": consent,
        }
    )
    return jsonify(
        {"ok": True, "message": "Спасибо! Ваша регистрация подтверждена."}
    )


# --------------------------------------------------------------------------- #
# CRM-ready JSON endpoint
# --------------------------------------------------------------------------- #
@app.get("/api/registrations")
@require_admin()
def api_registrations():
    rows = db.list_registrations()
    return jsonify(
        {
            "event": "Сила партнерства для бизнеса — 2 декабря",
            "count": len(rows),
            "registrations": [
                {
                    "id": r["id"],
                    "first_name": r["first_name"],
                    "last_name": r["last_name"],
                    "company": r["company"],
                    "position": r["position"],
                    "phone": r["phone"],
                    "email": r["email"],
                    "comments": r["comments"],
                    "consent": bool(r["consent"]),
                    "created_at": r["created_at"],
                }
                for r in rows
            ],
        }
    )


# --------------------------------------------------------------------------- #
# Admin panel + exports
# --------------------------------------------------------------------------- #
@app.get("/admin")
@require_admin()
def admin():
    rows = db.list_registrations()
    return render_template("admin.html", registrations=rows, count=len(rows))


@app.get("/admin/export.csv")
@require_admin()
def export_csv():
    rows = db.list_registrations()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["ID", "Имя", "Фамилия", "Компания", "Должность",
         "Телефон", "Email", "Комментарий", "Согласие", "Дата регистрации"]
    )
    for r in rows:
        writer.writerow(
            [r["id"], r["first_name"], r["last_name"], r["company"],
             r["position"], r["phone"], r["email"], r["comments"],
             "Да" if r["consent"] else "Нет", r["created_at"]]
        )
    buffer.seek(0)
    return Response(
        "\ufeff" + buffer.getvalue(),  # BOM so Excel opens UTF-8 correctly
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=guests.csv"},
    )


@app.get("/admin/export.xlsx")
@require_admin()
def export_xlsx():
    rows = db.list_registrations()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Гости"

    headers = ["ID", "Имя", "Фамилия", "Компания", "Должность",
               "Телефон", "Email", "Комментарий", "Согласие", "Дата регистрации"]
    header_fill = PatternFill("solid", fgColor="E4D7C1")
    header_font = Font(bold=True, color="000000")
    ws.append(headers)
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for r in rows:
        ws.append(
            [r["id"], r["first_name"], r["last_name"], r["company"],
             r["position"], r["phone"], r["email"], r["comments"],
             "Да" if r["consent"] else "Нет", r["created_at"]]
        )

    widths = [6, 16, 18, 22, 22, 18, 26, 30, 10, 24]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[chr(64 + i)].width = w
    ws.freeze_panes = "A2"

    out = io.BytesIO()
    wb.save(out)
    out.seek(0)
    return send_file(
        out,
        mimetype=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        as_attachment=True,
        download_name="guests.xlsx",
    )


# --------------------------------------------------------------------------- #
# Entrypoint
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    db.init_db()
    print("=" * 60)
    print(" Event landing:  http://127.0.0.1:8000")
    print(" Network:        http://<ваш-IP-в-сети>:8000  (слушает 0.0.0.0)")
    print(" Admin panel:    http://127.0.0.1:8000/admin")
    print("   login:  admin / admin123   (set ADMIN_PASSWORD to override)")
    print("=" * 60)
    app.run(host="0.0.0.0", port=8000, debug=True)