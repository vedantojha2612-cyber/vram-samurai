#!/usr/bin/env python3
"""
VRAM-Samurai CLI
Real-time KV-cache & PagedAttention profiler for local LLMs.
"""

from __future__ import annotations

import argparse
import asyncio
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
import sys
import threading
import time
import webbrowser

# Ensure repository root is in python path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from sampler.server import TelemetryServer

BANNER = r"""
  ╔═══════════════════════════════════════════════════════════════════════════╗
  ║  ⚔️  VRAM-SAMURAI // LOCAL LLM INFERENCE & KV-CACHE PROFILER              ║
  ║  ═══════════════════════════════════════════════════════════════════════  ║
  ║  100% Local · Zero-Allocation Ring Buffers · 3.15 µs Sampling Overhead    ║
  ╚═══════════════════════════════════════════════════════════════════════════╝
"""


def run_overhead_benchmark() -> int:
    """Executes the microsecond-precision overhead benchmark."""
    print(BANNER)
    from tests.benchmark_overhead import run_benchmark
    run_benchmark()
    return 0


def run_unit_tests() -> int:
    """Executes the unit test suite."""
    print(BANNER)
    import unittest
    loader = unittest.TestLoader()
    suite = loader.discover(os.path.join(ROOT_DIR, "tests"))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


def run_terminal_ui(model: str | None = None, api_base: str = "http://127.0.0.1:11434") -> None:
    """Launches the zero-dependency ANSI Terminal UI."""
    from tui.app import run_live_tui
    asyncio.run(run_live_tui(model=model, api_base=api_base))


def start_http_server(directory: str, port: int) -> ThreadingHTTPServer:
    """Starts a lightweight static HTTP server for the 3D Web HUD."""
    class CustomHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=directory, **kwargs)

        def log_message(self, format, *args):
            # Suppress noisy HTTP asset requests in console
            pass

    server = ThreadingHTTPServer(("127.0.0.1", port), CustomHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def open_browser_delayed(url: str, delay: float = 0.6) -> None:
    """Opens browser with slight delay to ensure server bind."""
    def _open():
        time.sleep(delay)
        try:
            webbrowser.open(url)
        except Exception:
            pass

    threading.Thread(target=_open, daemon=True).start()


def run_telemetry_hub(
    host: str = "127.0.0.1",
    ws_port: int = 8765,
    http_port: int = 8080,
    open_hud: bool = True,
    model: str | None = None,
    api_base: str = "http://127.0.0.1:11434",
) -> None:
    """Starts the WebSocket telemetry hub and serves the 3D Web HUD."""
    print(BANNER)
    web_dir = os.path.join(ROOT_DIR, "web")
    hud_url = f"http://{host}:{http_port}/index.html"

    if open_hud:
        start_http_server(web_dir, http_port)
        print(f"  🌐 3D Web HUD:        {hud_url}")
        open_browser_delayed(hud_url)

    print(f"  ⚡ WebSocket Stream:   ws://{host}:{ws_port}")
    print(f"  🎯 Inference Endpoint: {api_base} (Model: {model or 'Synthetic Demo Stream'})")
    print(f"  💡 To view Terminal UI side-by-side, open another tab and run:")
    print(f"     python cli.py --tui\n")
    print("  [Ctrl+C to quit]\n")

    server = TelemetryServer(host=host, port=ws_port)
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\n  [Telemetry Hub stopped cleanly. ⚔️]")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="VRAM-Samurai: Real-time KV-cache & PagedAttention visualizer for local LLMs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--tui", action="store_true", help="Launch live ANSI Terminal UI")
    parser.add_argument("--web", action="store_true", help="Launch WebSocket Hub and open 3D Web HUD in browser")
    parser.add_argument("--server", action="store_true", help="Launch WebSocket telemetry server only")
    parser.add_argument("--benchmark", action="store_true", help="Run sub-microsecond sampling overhead benchmark")
    parser.add_argument("--test", action="store_true", help="Run automated test suite")
    parser.add_argument("--port", type=int, default=8765, help="WebSocket port (default: 8765)")
    parser.add_argument("--http-port", type=int, default=8080, help="HTTP port for 3D Web HUD (default: 8080)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--model", type=str, default=None, help="Ollama/vLLM model name (uses mock stream if omitted)")
    parser.add_argument("--api-base", type=str, default="http://127.0.0.1:11434", help="Inference API endpoint")
    parser.add_argument("--no-browser", action="store_true", help="Do not auto-open browser")

    args = parser.parse_args()

    if args.benchmark:
        sys.exit(run_overhead_benchmark())
    elif args.test:
        sys.exit(run_unit_tests())
    elif args.tui:
        run_terminal_ui(model=args.model, api_base=args.api_base)
    elif args.server:
        run_telemetry_hub(
            host=args.host,
            ws_port=args.port,
            http_port=args.http_port,
            open_hud=False,
            model=args.model,
            api_base=args.api_base,
        )
    else:
        # Default action: run full telemetry hub and open 3D HUD
        run_telemetry_hub(
            host=args.host,
            ws_port=args.port,
            http_port=args.http_port,
            open_hud=not args.no_browser,
            model=args.model,
            api_base=args.api_base,
        )


if __name__ == "__main__":
    main()
