"""Comprehensive Test Suite for Axioma Go Sovereign HTTP Server & UI Assets.

Verifies:
- Pure Python 3.14 standard library HTTP server lifecycle
- Static file delivery (index.html, style.css, app.js) with zero external CDNs
- Security: Path traversal protection
- JSON REST API endpoints:
  - GET /api/health
  - GET /api/state
  - POST /api/play
  - POST /api/pass
  - POST /api/undo
  - POST /api/reset
  - GET /api/showcases
  - GET /api/showcases/<id>
  - POST /api/showcases/<id>/fork
- All 6 canonical Go capture showcases (Snapback, Ladder, Geta, Crane's Nest, Double Atari, Ishi-no-shita)
"""

from __future__ import annotations

import io
import json
from pathlib import Path
import unittest

from apps.axioma_go.src.server import AxiomaGoRequestHandler, GLOBAL_STATE
from apps.axioma_go.src.engine import CANONICAL_SHOWCASES


class MockSocket:
    """Mock socket implementing rfile and wfile streams for hermetic in-memory HTTP testing."""

    def __init__(self, data: bytes):
        self.rfile = io.BytesIO(data)
        self.wfile = io.BytesIO()

    def makefile(self, mode: str, *args, **kwargs):
        if "r" in mode:
            return self.rfile
        return self.wfile

    def sendall(self, data: bytes):
        self.wfile.write(data)


def simulate_http_request(
    method: str,
    path: str,
    body: bytes = b"",
    headers_dict: dict | None = None
) -> tuple[int, dict, bytes]:
    """Simulates an HTTP request against AxiomaGoRequestHandler in-memory."""
    hdrs = f"Host: localhost\r\nContent-Length: {len(body)}\r\n"
    if headers_dict:
        for k, v in headers_dict.items():
            hdrs += f"{k}: {v}\r\n"

    raw_req = f"{method} {path} HTTP/1.1\r\n{hdrs}\r\n".encode("utf-8") + body
    sock = MockSocket(raw_req)

    # Initialize handler (this executes request parsing and handle() synchronously)
    AxiomaGoRequestHandler(sock, ("127.0.0.1", 12345), None)

    sock.wfile.seek(0)
    raw_response = sock.wfile.read()

    parts = raw_response.split(b"\r\n\r\n", 1)
    header_lines = parts[0].decode("utf-8", errors="replace").split("\r\n")
    resp_body = parts[1] if len(parts) > 1 else b""

    status_line = header_lines[0]
    status_code = int(status_line.split()[1]) if len(status_line.split()) > 1 else 500

    resp_headers = {}
    for line in header_lines[1:]:
        if ":" in line:
            k, v = line.split(":", 1)
            resp_headers[k.strip().lower()] = v.strip()

    return status_code, resp_headers, resp_body


class TestAxiomaGoServer(unittest.TestCase):
    """Hermetic unit and integration tests for Axioma Go HTTP server and UI."""

    def setUp(self):
        GLOBAL_STATE.reset()

    def _get(self, path: str):
        return simulate_http_request("GET", path)

    def _post(self, path: str, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        status, headers, raw = simulate_http_request(
            "POST",
            path,
            body=body,
            headers_dict={"Content-Type": "application/json"}
        )
        data = json.loads(raw.decode("utf-8")) if raw else {}
        return status, headers.get("content-type", ""), data

    # -----------------------------------------------------------------------
    # Health & Meta Endpoints
    # -----------------------------------------------------------------------

    def test_health_endpoint(self):
        status, headers, body = self._get("/api/health")
        self.assertEqual(status, 200)
        self.assertIn("application/json", headers.get("content-type", ""))
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["status"], "HEALTHY")
        self.assertEqual(data["service"], "axioma_go")
        self.assertEqual(data["board_size"], 10)
        self.assertEqual(data["showcases_available"], 6)

    # -----------------------------------------------------------------------
    # Static Assets Delivery (Zero CDN Dependencies)
    # -----------------------------------------------------------------------

    def test_serve_index_html(self):
        status, headers, body = self._get("/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers.get("content-type", ""))
        html_str = body.decode("utf-8")
        self.assertIn("AXIOMA GO", html_str)
        self.assertIn("goBoardSvg", html_str)
        # Verify strictly zero external CDN references
        self.assertNotIn("googleapis.com", html_str)
        self.assertNotIn("cdnjs.cloudflare.com", html_str)
        self.assertNotIn("unpkg.com", html_str)

    def test_serve_style_css(self):
        status, headers, body = self._get("/style.css")
        self.assertEqual(status, 200)
        self.assertIn("text/css", headers.get("content-type", ""))
        css_str = body.decode("utf-8")
        self.assertIn("theme-kaya", css_str)
        self.assertIn("@keyframes atariRingPulse", css_str)
        self.assertIn("wood-grain-layer", css_str)

    def test_serve_app_js(self):
        status, headers, body = self._get("/app.js")
        self.assertEqual(status, 200)
        ctype = headers.get("content-type", "")
        self.assertTrue("javascript" in ctype or "application/javascript" in ctype)
        js_str = body.decode("utf-8")
        self.assertIn("BOARD_SIZE = 10", js_str)
        self.assertIn("COLUMNS", js_str)
        self.assertIn("apiForkShowcase", js_str)

    def test_path_traversal_protection(self):
        status, _, _ = self._get("/../../server.py")
        self.assertIn(status, (403, 404))

    # -----------------------------------------------------------------------
    # Game State & Free Play Actions
    # -----------------------------------------------------------------------

    def test_get_state(self):
        status, headers, body = self._get("/api/state")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["size"], 10)
        self.assertEqual(data["current_player"], "B")
        self.assertEqual(len(data["board"]), 10)
        self.assertEqual(len(data["board"][0]), 10)
        self.assertEqual(data["captures"], {"B": 0, "W": 0})
        self.assertEqual(data["move_count"], 0)

    def test_play_valid_moves_and_turn_alternation(self):
        # Play Black at E5 (x=4, y=4)
        status, _, data = self._post("/api/play", {"x": 4, "y": 4})
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])
        self.assertEqual(data["board"][4][4], "B")
        self.assertEqual(data["current_player"], "W")
        self.assertEqual(data["move_count"], 1)

        # Play White at E6 (x=4, y=5)
        status, _, data = self._post("/api/play", {"x": 4, "y": 5})
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])
        self.assertEqual(data["board"][5][4], "W")
        self.assertEqual(data["current_player"], "B")
        self.assertEqual(data["move_count"], 2)

    def test_play_occupied_intersection_rejected(self):
        self._post("/api/play", {"x": 3, "y": 3})
        status, _, data = self._post("/api/play", {"x": 3, "y": 3})
        self.assertEqual(status, 400)
        self.assertFalse(data.get("success", False))
        self.assertIn("occupied", data.get("message", "").lower())

    def test_functorial_undo(self):
        # Play move 1
        self._post("/api/play", {"x": 2, "y": 2})
        # Play move 2
        self._post("/api/play", {"x": 7, "y": 7})

        state1 = GLOBAL_STATE.get_state()
        self.assertEqual(state1["move_count"], 2)

        # Undo move 2
        status, _, data = self._post("/api/undo", {})
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])
        self.assertEqual(data["move_count"], 1)
        self.assertEqual(data["board"][7][7], ".")
        self.assertEqual(data["current_player"], "W")

        # Undo move 1
        status, _, data = self._post("/api/undo", {})
        self.assertEqual(status, 200)
        self.assertEqual(data["move_count"], 0)
        self.assertEqual(data["board"][2][2], ".")
        self.assertEqual(data["current_player"], "B")

    def test_pass_and_consecutive_passes(self):
        status, _, data = self._post("/api/pass", {})
        self.assertEqual(status, 200)
        self.assertEqual(data["current_player"], "W")
        self.assertFalse(data["game_over"])

        # Second consecutive pass
        status, _, data = self._post("/api/pass", {})
        self.assertEqual(status, 200)
        self.assertTrue(data["game_over"])

    def test_reset_board(self):
        self._post("/api/play", {"x": 1, "y": 1})
        self._post("/api/play", {"x": 8, "y": 8})
        status, _, data = self._post("/api/reset", {})
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])
        self.assertEqual(data["move_count"], 0)
        for row in data["board"]:
            for cell in row:
                self.assertEqual(cell, ".")

    # -----------------------------------------------------------------------
    # Capture Showcases Library & Fork
    # -----------------------------------------------------------------------

    def test_get_showcases_list(self):
        status, _, body = self._get("/api/showcases")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        scs = data["showcases"]
        self.assertEqual(len(scs), 6)
        ids = [s["id"] for s in scs]
        self.assertIn("snapback", ids)
        self.assertIn("ladder", ids)
        self.assertIn("geta", ids)
        self.assertIn("cranes_nest", ids)
        self.assertIn("double_atari", ids)
        self.assertIn("ishi_no_shita", ids)

    def test_get_showcase_details_for_all_6(self):
        for sc_id in ["snapback", "ladder", "geta", "cranes_nest", "double_atari", "ishi_no_shita"]:
            status, _, body = self._get(f"/api/showcases/{sc_id}")
            self.assertEqual(status, 200)
            data = json.loads(body.decode("utf-8"))
            self.assertEqual(data["id"], sc_id)
            self.assertGreater(len(data["steps"]), 1)
            for step in data["steps"]:
                self.assertIn("ply", step)
                self.assertIn("badge", step)
                self.assertIn(step["badge"], ("CALM", "WARNING", "ATARI", "CAPTURED"))
                self.assertIn("explanation", step)
                self.assertIn("state", step)

    def test_fork_showcase_into_free_play(self):
        # Fork snapback at ply 2 (White took bait, in atari with only E5 left)
        status, _, data = self._post("/api/showcases/snapback/fork", {"ply": 2})
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])
        self.assertEqual(data["mode"], "free_play")
        self.assertEqual(data["current_player"], "B")

        # Now execute the snapback winning move at E5 (x=4, y=4) in Free Play!
        play_status, _, play_data = self._post("/api/play", {"x": 4, "y": 4})
        self.assertEqual(play_status, 200)
        self.assertTrue(play_data["success"])
        # White stones wiped out!
        self.assertGreaterEqual(play_data["captures"]["B"], 7)
        self.assertGreater(play_data["last_move"]["captured"], 0)


if __name__ == "__main__":
    unittest.main()
