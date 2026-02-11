from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from .ai import SeverityModel
from .auth import create_token, decode_token, hash_password, verify_password
from .config import RATE_LIMIT_PER_HOUR, SUSPICIOUS_VERIFICATION_THRESHOLD, UPLOAD_DIR
from .cv_utils import validate_images
from .db import get_conn, init_db, now_iso

app = FastAPI(title="SLSU Emergency AI MVP")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

severity_model = SeverityModel()


@app.on_event("startup")
def startup() -> None:
    init_db()
    severity_model.load()
    seed_accounts()


def seed_accounts() -> None:
    with get_conn() as conn:
        for email, role in [("admin@slsu.local", "admin"), ("responder@slsu.local", "responder")]:
            exists = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
            if not exists:
                conn.execute(
                    "INSERT INTO users (email,password_hash,role,created_at) VALUES (?,?,?,?)",
                    (email, hash_password("password123"), role, now_iso()),
                )


def write_audit(user_id: int | None, action: str, request: Request, device_id: str | None = None, details: str = "") -> None:
    ip = request.client.host if request.client else "unknown"
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO audit_logs (user_id,action,ip_address,device_id,details,created_at) VALUES (?,?,?,?,?,?)",
            (user_id, action, ip, device_id, details, now_iso()),
        )


def get_current_user(authorization: str = Header(default="")) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return decode_token(authorization.replace("Bearer ", "", 1))


def role_guard(user: dict, allowed: set[str]) -> None:
    if user.get("role") not in allowed:
        raise HTTPException(status_code=403, detail="Forbidden")


def update_user_risk_score(user_id: int, *, increase_by: float = 0.0, flagged: bool | None = None) -> None:
    with get_conn() as conn:
        row = conn.execute("SELECT risk_score, account_flagged FROM users WHERE id=?", (user_id,)).fetchone()
        if not row:
            return
        risk_score = float(row["risk_score"]) + increase_by
        account_flagged = int(row["account_flagged"])
        if flagged is True:
            account_flagged = 1
        conn.execute(
            "UPDATE users SET risk_score=?, account_flagged=? WHERE id=?",
            (round(risk_score, 2), account_flagged, user_id),
        )


def enforce_rate_limit(user_id: int) -> int:
    """Return count in the last hour. If limit exceeded, flag user and block submission."""
    with get_conn() as conn:
        count = conn.execute(
            "SELECT COUNT(*) as c FROM reports WHERE user_id=? AND created_at >= datetime('now','-1 hour')",
            (user_id,),
        ).fetchone()["c"]

    if count >= RATE_LIMIT_PER_HOUR:
        update_user_risk_score(user_id, increase_by=25, flagged=True)
        raise HTTPException(status_code=429, detail="Rate limit exceeded: max 3 reports per hour. Account flagged.")
    return int(count)


def safe_save(upload: UploadFile, prefix: str) -> Path:
    ext = Path(upload.filename or "img.jpg").suffix.lower() or ".jpg"
    filename = f"{prefix}_{uuid4().hex}{ext}"
    target = UPLOAD_DIR / filename
    target.write_bytes(upload.file.read())
    return target


def _build_pdf_summary(reports: list[dict]) -> bytes:
    buff = io.BytesIO()
    pdf = canvas.Canvas(buff, pagesize=letter)
    width, height = letter

    y = height - 40
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(40, y, "SLSU Emergency Reports Summary")
    y -= 18
    pdf.setFont("Helvetica", 10)
    pdf.drawString(40, y, f"Generated: {now_iso()}")
    y -= 20

    for r in reports:
        if y < 140:
            pdf.showPage()
            y = height - 40

        pdf.setStrokeColor(colors.darkblue)
        pdf.rect(35, y - 95, width - 70, 90, stroke=1, fill=0)
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(45, y - 15, f"Report #{r['id']} | {r['emergency_type']} | {r['severity_label']} | {r['status']}")
        pdf.setFont("Helvetica", 9)
        pdf.drawString(45, y - 30, f"User: {r.get('reporter_email', 'N/A')}")
        pdf.drawString(45, y - 43, f"Verification: {r['verification_score']}  |  Time: {r['created_at']}")
        pdf.drawString(45, y - 56, f"Location: {r['latitude']}, {r['longitude']}")

        selfie = UPLOAD_DIR / Path(r["selfie_path"]).name
        accident = UPLOAD_DIR / Path(r["accident_path"]).name

        img_y = y - 90
        for idx, p in enumerate([selfie, accident]):
            x = 380 + (idx * 100)
            if p.exists():
                try:
                    pdf.drawImage(ImageReader(str(p)), x, img_y, width=85, height=55, preserveAspectRatio=True)
                except Exception:
                    pdf.setFont("Helvetica", 8)
                    pdf.drawString(x, img_y + 25, "img err")

        y -= 105

    pdf.save()
    buff.seek(0)
    return buff.read()


@app.post("/auth/register")
def register(email: str = Form(...), password: str = Form(...), request: Request = None):
    with get_conn() as conn:
        existing = conn.execute("SELECT id FROM users WHERE email=?", (email.lower(),)).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="Email already exists")
        conn.execute(
            "INSERT INTO users (email,password_hash,role,created_at) VALUES (?,?,?,?)",
            (email.lower(), hash_password(password), "citizen", now_iso()),
        )
        user = conn.execute("SELECT id,email,role,risk_score,account_flagged FROM users WHERE email=?", (email.lower(),)).fetchone()

    if request:
        write_audit(user["id"], "register", request)
    token = create_token({"user_id": user["id"], "email": user["email"], "role": user["role"]})
    return {"token": token, "user": dict(user)}


@app.post("/auth/login")
def login(email: str = Form(...), password: str = Form(...), request: Request = None):
    with get_conn() as conn:
        user = conn.execute(
            "SELECT id,email,role,password_hash,risk_score,account_flagged FROM users WHERE email=?",
            (email.lower(),),
        ).fetchone()
    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if request:
        write_audit(user["id"], "login", request)
    token = create_token({"user_id": user["id"], "email": user["email"], "role": user["role"]})
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "role": user["role"],
            "risk_score": user["risk_score"],
            "account_flagged": bool(user["account_flagged"]),
        },
    }


@app.post("/reports")
def create_report(
    request: Request,
    emergency_type: str = Form(...),
    description: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    device_id: str = Form("unknown-device"),
    lora_payload: str = Form(""),
    selfie: UploadFile = File(...),
    accident_photo: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    recent_count = enforce_rate_limit(user["user_id"])

    selfie_path = safe_save(selfie, "selfie")
    accident_path = safe_save(accident_photo, "accident")

    risk_score = 0.8 if emergency_type.lower() in {"fire", "crime", "accident"} else 0.5
    severity_label, confidence = severity_model.predict(emergency_type, description, risk_score)
    verification = validate_images(selfie_path, accident_path)

    status_label = "Pending"
    if verification["verification_score"] < SUSPICIOUS_VERIFICATION_THRESHOLD:
        status_label = "Needs Review"
        verification["suspicious"] = True
        update_user_risk_score(user["user_id"], increase_by=12)
    if verification["verification_score"] < 20:
        status_label = "Rejected"

    # Escalate risk score for frequent submissions near threshold.
    if recent_count == RATE_LIMIT_PER_HOUR - 1:
        update_user_risk_score(user["user_id"], increase_by=8)

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO reports (
                user_id,device_id,emergency_type,description,latitude,longitude,selfie_path,accident_path,lora_payload,
                severity_label,severity_confidence,verification_score,face_ok,accident_image_ok,suspicious,status,created_at,updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                user["user_id"],
                device_id,
                emergency_type,
                description,
                latitude,
                longitude,
                str(selfie_path.relative_to(UPLOAD_DIR.parent)),
                str(accident_path.relative_to(UPLOAD_DIR.parent)),
                lora_payload,
                severity_label,
                confidence,
                verification["verification_score"],
                int(verification["face_ok"]),
                int(verification["accident_image_ok"]),
                int(verification["suspicious"]),
                status_label,
                now_iso(),
                now_iso(),
            ),
        )
        report_id = conn.execute("SELECT last_insert_rowid() as id").fetchone()["id"]

    write_audit(user["user_id"], "create_report", request, device_id, f"report_id={report_id}")
    return {
        "id": report_id,
        "severity": {"label": severity_label, "confidence": confidence},
        "verification": verification,
        "status": status_label,
    }


@app.get("/reports/me")
def my_reports(user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, emergency_type, description, latitude, longitude, severity_label, severity_confidence, verification_score, status, created_at FROM reports WHERE user_id=? ORDER BY id DESC",
            (user["user_id"],),
        ).fetchall()
    return [dict(r) for r in rows]


@app.get("/reports")
def all_reports(user: dict = Depends(get_current_user)):
    role_guard(user, {"admin", "responder"})
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT r.*, u.email as reporter_email, u.risk_score, u.account_flagged
            FROM reports r JOIN users u ON u.id = r.user_id
            ORDER BY r.id DESC
            """
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["selfie_url"] = f"/uploads/{Path(d['selfie_path']).name}"
        d["accident_url"] = f"/uploads/{Path(d['accident_path']).name}"
        d["map_url"] = f"https://www.google.com/maps?q={d['latitude']},{d['longitude']}"
        out.append(d)
    return out


@app.get("/reports/analytics")
def reports_analytics(user: dict = Depends(get_current_user)):
    role_guard(user, {"admin", "responder"})
    with get_conn() as conn:
        by_type = conn.execute(
            "SELECT emergency_type as name, COUNT(*) as value FROM reports GROUP BY emergency_type ORDER BY value DESC"
        ).fetchall()
        by_severity = conn.execute(
            "SELECT severity_label as name, COUNT(*) as value FROM reports GROUP BY severity_label ORDER BY value DESC"
        ).fetchall()
        by_day = conn.execute(
            "SELECT substr(created_at,1,10) as day, COUNT(*) as value FROM reports GROUP BY day ORDER BY day"
        ).fetchall()
        status_counts = conn.execute(
            "SELECT status as name, COUNT(*) as value FROM reports GROUP BY status ORDER BY value DESC"
        ).fetchall()
        flagged_users = conn.execute(
            "SELECT id,email,risk_score,account_flagged FROM users WHERE account_flagged=1 OR risk_score>=20 ORDER BY risk_score DESC"
        ).fetchall()

    return {
        "reports_per_type": [dict(r) for r in by_type],
        "severity_distribution": [dict(r) for r in by_severity],
        "reports_over_time": [dict(r) for r in by_day],
        "status_distribution": [dict(r) for r in status_counts],
        "flagged_users": [dict(r) for r in flagged_users],
    }


@app.get("/reports/export/pdf")
def export_reports_pdf(user: dict = Depends(get_current_user)):
    role_guard(user, {"admin", "responder"})
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT r.*, u.email as reporter_email
            FROM reports r JOIN users u ON u.id = r.user_id
            ORDER BY r.id DESC
            LIMIT 100
            """
        ).fetchall()
    content = _build_pdf_summary([dict(r) for r in rows])
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=emergency_reports_summary.pdf"},
    )


@app.patch("/reports/{report_id}/status")
def update_status(report_id: int, status_label: str = Form(...), request: Request = None, user: dict = Depends(get_current_user)):
    role_guard(user, {"admin", "responder"})
    with get_conn() as conn:
        report = conn.execute("SELECT id FROM reports WHERE id=?", (report_id,)).fetchone()
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        conn.execute("UPDATE reports SET status=?, updated_at=? WHERE id=?", (status_label, now_iso(), report_id))
    if request:
        write_audit(user["user_id"], "update_status", request, details=f"report_id={report_id};status={status_label}")
    return {"ok": True, "report_id": report_id, "status": status_label}


@app.get("/audit-logs")
def audit_logs(user: dict = Depends(get_current_user)):
    role_guard(user, {"admin", "responder"})
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 300").fetchall()
    return [dict(r) for r in rows]


@app.get("/model/metrics")
def model_metrics(user: dict = Depends(get_current_user)):
    role_guard(user, {"admin", "responder"})
    return severity_model.evaluate()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/lora/payload-preview")
def lora_payload_preview(device_id: str, emergency_type: str, latitude: float, longitude: float):
    payload = {
        "device_id": device_id,
        "timestamp": now_iso(),
        "lat": latitude,
        "lng": longitude,
        "emergency_type": emergency_type,
    }
    payload["hash"] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]
    return payload
