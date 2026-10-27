"""Sovereign HTTP Server for Axioma Go (10x10 Board).

Pure Python 3.14 standard library HTTP server:
- Serves static directory `static/` at `/`
- Exposes JSON REST API endpoints on port 8082
- Thread-safe game state and showcase fork operations
"""

import argparse
from http.server import HTTPServer, ThreadingHTTPServer, BaseHTTPRequestHandler
import json
import mimetypes
import os
from pathlib import Path
import sys
import threading
from typing import Dict, Any, Optional
import urllib.parse

# Ensure local package resolution
CUR_DIR = Path(__file__).resolve().parent
APP_ROOT = CUR_DIR.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

try:
    from src.engine import GoEngine, CANONICAL_SHOWCASES, coord_to_str
except ImportError:
    from engine import GoEngine, CANONICAL_SHOWCASES, coord_to_str

STATIC_DIR = APP_ROOT / "static"

class AxiomaGoState:
    """Thread-safe state manager for the active Go board."""

    def __init__(self):
        self.lock = threading.Lock()
        self.engine = GoEngine(10)
        self.mode = "free_play"
        self.active_showcase_id: Optional[str] = None
        self.active_ply: int = 0

    def get_state(self) -> Dict[str, Any]:
        with self.lock:
            state = self.engine.get_state()
            state["mode"] = self.mode
            state["active_showcase_id"] = self.active_showcase_id
            state["active_ply"] = self.active_ply
            return state

    def play(self, x: int, y: int, color: Optional[str] = None) -> Dict[str, Any]:
        with self.lock:
            ok, msg = self.engine.play(x, y, color)
            state = self.engine.get_state()
            state["success"] = ok
            state["message"] = msg
            state["mode"] = "free_play"
            self.mode = "free_play"
            return state

    def pass_turn(self, color: Optional[str] = None) -> Dict[str, Any]:
        with self.lock:
            ok, msg = self.engine.pass_turn(color)
            state = self.engine.get_state()
            state["success"] = ok
            state["message"] = msg
            return state

    def undo(self) -> Dict[str, Any]:
        with self.lock:
            ok, msg = self.engine.undo()
            state = self.engine.get_state()
            state["success"] = ok
            state["message"] = msg
            return state

    def reset(self) -> Dict[str, Any]:
        with self.lock:
            self.engine.reset()
            self.mode = "free_play"
            self.active_showcase_id = None
            self.active_ply = 0
            state = self.engine.get_state()
            state["success"] = True
            state["message"] = "Board reset to empty."
            return state

    def fork_showcase(self, showcase_id: str, ply: int) -> Dict[str, Any]:
        with self.lock:
            if showcase_id not in CANONICAL_SHOWCASES:
                return {
                    "success": False,
                    "error": f"Showcase '{showcase_id}' not found",
                    "state": self.engine.get_state()
                }

            sc = CANONICAL_SHOWCASES[showcase_id]
            steps = sc["steps"]
            if ply < 0:
                ply = 0
            if ply >= len(steps):
                ply = len(steps) - 1

            target_step = steps[ply]
            step_state = target_step["state"]

            # Initialize a new live engine with the exact board state at this ply
            new_eng = GoEngine(10)
            board_cells = step_state["board"]
            for y in range(10):
                for x in range(10):
                    cell = board_cells[y][x]
                    if cell in ("B", "W"):
                        new_eng.board[y][x] = cell

            new_eng.current_player = step_state.get("current_player", "B")
            new_eng.captures = dict(step_state.get("captures", {"B": 0, "W": 0}))
            new_eng.last_move = step_state.get("last_move")
            new_eng.history = []  # Forked free play begins with fresh undo history

            self.engine = new_eng
            self.mode = "free_play"
            self.active_showcase_id = showcase_id
            self.active_ply = ply

            res_state = self.engine.get_state()
            res_state["mode"] = self.mode
            res_state["active_showcase_id"] = showcase_id
            res_state["active_ply"] = ply
            res_state["success"] = True
            res_state["message"] = f"Forked showcase '{sc['name']}' at ply {ply} into Free Play!"
            res_state["forked_from"] = {
                "showcase_id": showcase_id,
                "name": sc["name"],
                "ply": ply,
                "badge": target_step["badge"],
                "japanese_term": target_step["japanese_term"],
                "explanation": target_step["explanation"]
            }
            return res_state


GLOBAL_STATE = AxiomaGoState()


class AxiomaGoRequestHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler serving static files and REST API."""

    server_port: int = 8082

    def log_message(self, format: str, *args):
        """Clean minimal log formatting."""
        # Suppress spammy log outputs in tests
        pass

    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def send_json(self, data: Any, status: int = 200):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, message: str, status: int = 400):
        self.send_json({"error": message, "status": "ERROR"}, status=status)

    def parse_json_body(self) -> Dict[str, Any]:
        content_len = int(self.headers.get("Content-Length", 0))
        if content_len == 0:
            return {}
        try:
            raw = self.rfile.read(content_len).decode("utf-8")
            return json.loads(raw)
        except Exception:
            return {}

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # REST API endpoints
        if path == "/api/health":
            self.send_json({
                "status": "HEALTHY",
                "service": "axioma_go",
                "port": self.server_port,
                "board_size": 10,
                "showcases_available": len(CANONICAL_SHOWCASES)
            })
            return

        if path == "/api/state":
            state = GLOBAL_STATE.get_state()
            self.send_json(state)
            return

        if path == "/api/showcases":
            summary_list = []
            for sc_id, sc in CANONICAL_SHOWCASES.items():
                summary_list.append({
                    "id": sc["id"],
                    "name": sc["name"],
                    "japanese_term": sc["japanese_term"],
                    "description": sc["description"],
                    "step_count": len(sc["steps"]),
                    "plies": [s["badge"] for s in sc["steps"]]
                })
            self.send_json({"showcases": summary_list})
            return

        if path.startswith("/api/showcases/"):
            sc_id = path[len("/api/showcases/"):].strip("/")
            if sc_id in CANONICAL_SHOWCASES:
                self.send_json(CANONICAL_SHOWCASES[sc_id])
            else:
                self.send_error_json(f"Showcase '{sc_id}' not found", status=404)
            return

        # Static file serving
        self.serve_static_file(path)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self.parse_json_body()

        if path == "/api/play":
            if "x" not in body or "y" not in body:
                self.send_error_json("Missing 'x' or 'y' integer coordinates in payload")
                return
            try:
                x = int(body["x"])
                y = int(body["y"])
            except ValueError:
                self.send_error_json("Coordinates 'x' and 'y' must be integers")
                return
            color = body.get("color")
            res = GLOBAL_STATE.play(x, y, color)
            self.send_json(res, status=200 if res.get("success", False) else 400)
            return

        if path == "/api/pass":
            color = body.get("color")
            res = GLOBAL_STATE.pass_turn(color)
            self.send_json(res)
            return

        if path == "/api/undo":
            res = GLOBAL_STATE.undo()
            self.send_json(res, status=200 if res.get("success", False) else 400)
            return

        if path == "/api/reset":
            res = GLOBAL_STATE.reset()
            self.send_json(res)
            return

        if path.startswith("/api/showcases/") and path.endswith("/fork"):
            parts = path.strip("/").split("/")
            # Expecting ["api", "showcases", "<id>", "fork"]
            if len(parts) == 4 and parts[0] == "api" and parts[1] == "showcases" and parts[3] == "fork":
                sc_id = parts[2]
                ply = int(body.get("ply", 0))
                res = GLOBAL_STATE.fork_showcase(sc_id, ply)
                if not res.get("success", False):
                    self.send_error_json(res.get("error", "Fork failed"), status=404)
                else:
                    self.send_json(res)
                return
            self.send_error_json("Invalid fork URL format", status=400)
            return

        self.send_error_json(f"Unknown POST endpoint: {path}", status=404)

    def serve_static_file(self, rel_path: str):
        """Serves files from STATIC_DIR with security checks against traversal."""
        clean_path = rel_path.lstrip("/")
        if not clean_path or clean_path == "/":
            clean_path = "index.html"

        # Special alias for dashboard.html or telemetry_dashboard.html
        if clean_path in ("dashboard.html", "telemetry_dashboard.html"):
            # Check static dir, or epoch dir, or fallback to an informative dashboard placeholder
            candidate = STATIC_DIR / clean_path
            if not candidate.exists():
                candidate = APP_ROOT / clean_path
            if candidate.exists() and candidate.is_file():
                self._send_file(candidate)
                return

        file_path = (STATIC_DIR / clean_path).resolve()
        # Security check: must reside inside STATIC_DIR
        try:
            file_path.relative_to(STATIC_DIR.resolve())
        except ValueError:
            self.send_error_json("Access forbidden", status=403)
            return

        if not file_path.exists() or not file_path.is_file():
            self.send_error_json(f"File '{clean_path}' not found", status=404)
            return

        self._send_file(file_path)

    def _send_file(self, file_path: Path):
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type is None:
            if file_path.suffix == ".js":
                mime_type = "application/javascript"
            elif file_path.suffix == ".css":
                mime_type = "text/css"
            elif file_path.suffix == ".svg":
                mime_type = "image/svg+xml"
            elif file_path.suffix == ".html":
                mime_type = "text/html"
            else:
                mime_type = "application/octet-stream"

        if "text" in mime_type or mime_type in ("application/javascript", "application/json", "image/svg+xml"):
            mime_type += "; charset=utf-8"

        try:
            content = file_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error_json(f"Failed to read file: {e}", status=500)


def create_server(host: str = "0.0.0.0", port: int = 8082) -> ThreadingHTTPServer:
    """Factory to create the ThreadingHTTPServer instance."""
    AxiomaGoRequestHandler.server_port = port
    server = ThreadingHTTPServer((host, port), AxiomaGoRequestHandler)
    return server


def run_server(host: str = "0.0.0.0", port: int = 8082):
    server = create_server(host, port)
    print("=" * 70)
    print("  AXIOMA GO // 碁 (10x10) — Sovereign HTTP Server")
    print("=" * 70)
    print(f"  Server listening on: http://{host if host != '0.0.0.0' else 'localhost'}:{port}")
    print(f"  Health Check:        http://localhost:{port}/api/health")
    print(f"  Tactile Board UI:    http://localhost:{port}/")
    print("=" * 70)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down Axioma Go server...")
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Axioma Go Sovereign HTTP Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8082, help="Port (default: 8082)")
    args = parser.parse_args()
    run_server(args.host, args.port)
