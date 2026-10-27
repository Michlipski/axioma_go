#!/usr/bin/env python3
"""Axioma Go Sovereign Mesh Cluster Service Entrypoint (`run.py`).

Starts the Sovereign HTTP Server on port 8082 (default) serving the
Tactile 10x10 Board UI and Go Capture Engine REST API.
"""

import argparse
from pathlib import Path
import sys

# Add app directory to sys.path
APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from src.server import run_server

ASCII_BANNER = r"""
    ___    _  __ ____ ____   __  ___ ___       ______ ____ 
   /   |  | |/ //  _// __ \ /  |/  //   |     / ____// __ \
  / /| |  |   / / / / / / // /|_/ // /| |    / / __ / / / /
 / ___ | /   |_/ / / /_/ // /  / // ___ |   / /_/ // /_/ / 
/_/  |_|/_/|_/___/ \____//_/  /_//_/  |_|   \____/ \____/  
   >> Sovereign Tactile 10x10 Go Substrate & Capture Showcase <<
"""


def main():
    parser = argparse.ArgumentParser(description="Run Axioma Go Sovereign Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8082, help="Port (default: 8082)")
    args = parser.parse_args()

    print(ASCII_BANNER)
    print(f"  ⚡ Node Architecture:  Meta-Axioma Generation 4b Mesh")
    print(f"  ⚡ Grid Topology:      10x10 Intersections (A1 to K10)")
    print(f"  ⚡ Capture Showcases:  Snapback, Ladder, Geta, Crane's Nest, Double Atari, Ishi-no-shita")
    print(f"  ⚡ Local Web Endpoint: http://localhost:{args.port}/")
    print(f"  ⚡ REST Health Probe:  http://localhost:{args.port}/api/health")
    print("=" * 75)
    print("Press Ctrl+C to stop server.\n")

    run_server(args.host, args.port)


if __name__ == "__main__":
    main()
