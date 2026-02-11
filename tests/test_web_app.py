import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

from emergency_ai.web_app import EmergencyWebHandler


def _start_test_server() -> tuple[ThreadingHTTPServer, threading.Thread, int]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), EmergencyWebHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, server.server_port


def test_web_root_serves_html() -> None:
    server, thread, port = _start_test_server()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/") as response:
            html = response.read().decode()
            assert response.status == 200
            assert "Emergency Response &amp; Location Intelligence" in html
    finally:
        server.shutdown()
        thread.join(timeout=1)


def test_api_plan_returns_recommendations() -> None:
    server, thread, port = _start_test_server()
    try:
        payload = json.dumps(
            {
                "incident_text": "Explosion and smoke with trapped victims.",
                "latitude": 40.733,
                "longitude": -73.993,
            }
        ).encode()
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/plan",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(request) as response:
            data = json.loads(response.read().decode())
            assert response.status == 200
            assert data["triage"]["incident_type"] == "fire"
            assert data["recommendations"]
            assert data["actions"]
    finally:
        server.shutdown()
        thread.join(timeout=1)
