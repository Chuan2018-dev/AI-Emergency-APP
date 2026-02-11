from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from emergency_ai.models import Coordinates, IncidentReport, ResponseUnit, RiskZone
from emergency_ai.system import EmergencyResponseSystem

WEB_DIR = Path(__file__).parent / "web"


def build_default_system() -> EmergencyResponseSystem:
    units = [
        ResponseUnit(
            unit_id="MED-12",
            unit_type="ambulance",
            location=Coordinates(40.741, -73.989),
            speed_kmh=70,
            capabilities=["Paramedic", "Ambulance", "Advanced Life Support"],
        ),
        ResponseUnit(
            unit_id="FIRE-7",
            unit_type="fire engine",
            location=Coordinates(40.729, -73.997),
            speed_kmh=65,
            capabilities=["Fire Engine", "Hazmat", "Ladder"],
        ),
        ResponseUnit(
            unit_id="POL-9",
            unit_type="patrol",
            location=Coordinates(40.749, -73.976),
            speed_kmh=85,
            capabilities=["Law Enforcement", "Crowd Control"],
        ),
        ResponseUnit(
            unit_id="SAR-3",
            unit_type="rescue",
            location=Coordinates(40.751, -73.971),
            speed_kmh=60,
            capabilities=["Search and Rescue", "Boat Rescue"],
        ),
    ]

    risk_zones = [
        RiskZone(
            zone_id="FLOOD-A",
            center=Coordinates(40.735, -73.995),
            radius_km=3.5,
            risk_type="urban flood risk",
            severity_modifier=1.0,
        ),
        RiskZone(
            zone_id="IND-4",
            center=Coordinates(40.726, -74.003),
            radius_km=2.0,
            risk_type="industrial hazard zone",
            severity_modifier=1.2,
        ),
    ]
    return EmergencyResponseSystem(risk_zones=risk_zones, units=units)


class EmergencyWebHandler(BaseHTTPRequestHandler):
    system = build_default_system()

    def _send(self, body: bytes, content_type: str = "text/plain", status: HTTPStatus = HTTPStatus.OK) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, filename: str, content_type: str) -> None:
        path = WEB_DIR / filename
        if not path.exists():
            self._send(b"Not found", status=HTTPStatus.NOT_FOUND)
            return
        self._send(path.read_bytes(), content_type=content_type)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in {"/", "/index.html"}:
            self._serve_file("index.html", "text/html; charset=utf-8")
            return
        if self.path == "/styles.css":
            self._serve_file("styles.css", "text/css; charset=utf-8")
            return
        if self.path == "/app.js":
            self._serve_file("app.js", "application/javascript; charset=utf-8")
            return

        self._send(b"Not found", status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/plan":
            self._send(b"Not found", status=HTTPStatus.NOT_FOUND)
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        payload = self.rfile.read(content_length)

        try:
            data = json.loads(payload or b"{}")
            incident_text = str(data.get("incident_text", "")).strip()
            latitude = float(data.get("latitude"))
            longitude = float(data.get("longitude"))
            if not incident_text:
                raise ValueError("incident_text is required")
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            error = json.dumps({"error": f"Invalid input: {exc}"}).encode()
            self._send(error, content_type="application/json", status=HTTPStatus.BAD_REQUEST)
            return

        report = IncidentReport(
            incident_id="UI-REQUEST",
            caller_text=incident_text,
            location=Coordinates(latitude=latitude, longitude=longitude),
        )

        plan = self.system.build_plan(report)
        response = {
            "triage": {
                "incident_type": plan.triage.incident_type,
                "severity_score": plan.triage.severity_score,
                "urgent_signals": plan.triage.urgent_signals,
            },
            "risk_context": plan.risk_context,
            "recommendations": [
                {
                    "unit_id": rec.unit_id,
                    "suitability": rec.suitability,
                    "distance_km": rec.distance_km,
                    "eta_minutes": rec.eta_minutes,
                }
                for rec in plan.recommendations
            ],
            "actions": plan.actions,
        }

        body = json.dumps(response).encode()
        self._send(body, content_type="application/json")


def run(host: str = "0.0.0.0", port: int = 8080) -> None:
    server = ThreadingHTTPServer((host, port), EmergencyWebHandler)
    print(f"Emergency web app running on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run()
