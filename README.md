# AI-Powered Emergency Response and Location Intelligence System (SLSU Capstone MVP)

Phase 2 enhancement of the MVP with professional UI/UX, analytics, PDF export, risk flagging, and model evaluation metrics.

## Project Structure

```text
backend/                # FastAPI API, SQLite DB, CV checks, severity model, analytics/export
dashboard/              # React + Vite responder/admin dashboard with charts + modal details
mobile/                 # Flutter Android app with map preview + offline LoRa simulation

data/
  severity_dataset.csv  # synthetic training data
  model.pkl             # generated after training

src/emergency_ai/       # previous prototype package (kept for continuity)
tests/                  # previous prototype tests
```

---

## System Architecture Explanation

1. **Mobile Flutter Client** captures emergency reports, GPS, selfie, and accident photo.
2. **Offline/LoRa Simulation Layer** queues reports locally and generates a distress payload hash.
3. **FastAPI Backend** validates images, classifies severity, stores reports, and applies anti-prank controls.
4. **SQLite Database** persists users, reports, and audit logs (easy migration path to MySQL).
5. **Responder Dashboard (React)** visualizes incidents, analytics charts, flagged users, and export-ready summaries.

---

## AI Severity Model Explanation

- Model: **scikit-learn Logistic Regression** with pipeline.
- Features:
  - `emergency_type` (categorical one-hot)
  - `description` (TF-IDF n-grams)
  - `hour_of_day` (numeric)
  - `risk_score` stub (numeric)
- Training data: `data/severity_dataset.csv`.
- Output: `Low / Medium / Critical` + confidence score.
- Evaluation endpoint: `GET /model/metrics` returns accuracy, precision, recall, F1, confusion matrix.

---

## Computer Vision Validation Explanation

Image checks run on report submission:
- **Selfie**: face detection (OpenCV Haar cascade)
- **Accident Image**:
  - non-blank
  - blur threshold
  - not duplicate of selfie
- Output fields:
  - `verification_score`
  - `face_ok`
  - `accident_image_ok`
  - `suspicious`

Fallback mode exists when OpenCV is unavailable, using safe heuristics.

---

## LoRa Simulation Explanation

When mobile user enables offline mode:
1. Report payload is queued in local storage.
2. Simulated LoRa payload is generated:
   - `device_id`, `timestamp`, `lat`, `lng`, `emergency_type`, `hash`
3. Payload is shown to user.
4. On reconnection, queued reports are synced to backend.

---

## Risk Mitigation Strategy

Phase 2 risk controls:
- Verification threshold: low verification auto-marked suspicious (`Needs Review` / `Rejected`).
- Per-user report rate control: max 3 reports/hour.
- Over-limit behavior: user account auto-flag + risk score increase.
- User risk profiling:
  - `risk_score` numeric field
  - `account_flagged` boolean field
- Dashboard shows flagged users for responder/admin review.
- All actions captured in `audit_logs`.

---

## Backend API (Phase 2)

### Auth
- `POST /auth/register`
- `POST /auth/login`

### Reports
- `POST /reports`
- `GET /reports/me`
- `GET /reports`
- `PATCH /reports/{id}/status`

### Analytics / Export / Evaluation
- `GET /reports/analytics`
- `GET /reports/export/pdf`
- `GET /model/metrics`

### Other
- `GET /audit-logs`
- `GET /lora/payload-preview`
- `GET /health`

---

## Dashboard (Phase 2)

Implemented upgrades:
- Sidebar admin layout
- Top metric cards:
  - Total Reports
  - Critical Cases
  - Pending Verification
  - Resolved Cases
- Severity badges + filters
- Modal popup details with embedded map preview iframe
- Navigate button (`https://www.google.com/maps?q=LAT,LNG`)
- Charts via Recharts:
  - Bar: reports per type
  - Pie: severity distribution
  - Line: reports over time
- Export as PDF button (downloads backend-generated report)

---

## Mobile App (Phase 2)

Implemented upgrades:
- Emergency-themed dark blue/red UI
- Card-based report list
- Severity badge colors
- Verification score progress bar
- Map preview using OpenStreetMap (`flutter_map`) before submission
- User can tap map to correct coordinates
- Confirmation dialog before final submit
- Full-screen loading indicator while uploading

---

## Setup & Run

## Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python train_model.py   # optional (auto-trains on startup if missing)
uvicorn app.main:app --reload --port 8000
```

Seed accounts:
- `admin@slsu.local / password123`
- `responder@slsu.local / password123`

## Dashboard
```bash
cd dashboard
npm install
npm run dev
```
Open: `http://localhost:5173`

## Mobile (Flutter)
```bash
cd mobile
flutter pub get
flutter run
```

---

## Limitations

- Token auth is custom and simplified; replace with production JWT package.
- SQLite is local MVP storage; migrate to MySQL/PostgreSQL + migrations.
- CV checks are baseline and should be upgraded with robust object detection models.
- Map interaction on mobile uses tap-to-adjust marker (practical MVP alternative to full drag interaction).
- LoRa integration is simulated and not yet connected to physical LoRa hardware.

## Future Enhancements

- Full JWT + refresh token flow and secure key rotation.
- Real LoRa hardware integration (ESP32 + gateway).
- Advanced CV (object detection / VLM-based incident validation).
- Notification pipeline for dispatch events.
- Expanded analytics with geospatial heatmaps and responder SLA tracking.
