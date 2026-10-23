"""
Real-time WebSocket telemetry server for VRAM-Samurai.
Bridges backend inference/VRAM probes to the 3D Web HUD and terminal listeners.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Set
import websockets
from websockets.server import WebSocketServerProtocol

from .inference import StreamInferenceProfiler
from .metrics import InferenceMetrics
from .vram import VRAMProbe

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("vram_samurai.server")


class TelemetryServer:
    """
    High-throughput WebSocket telemetry broadcast hub.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8765) -> None:
        self.host = host
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()
        self.vram_probe = VRAMProbe()
        self.profiler = StreamInferenceProfiler()
        self._running = False

    async def register(self, ws: WebSocketServerProtocol) -> None:
        self.clients.add(ws)
        logger.info(f"Client connected: {ws.remote_address}. Total active: {len(self.clients)}")
        # Send initial hardware VRAM snapshot
        vram_sample = self.vram_probe.sample(active_tokens=0)
        await ws.send(json.dumps({
            "type": "vram_snapshot",
            "data": vram_sample.model_dump(),
        }))

    async def unregister(self, ws: WebSocketServerProtocol) -> None:
        self.clients.discard(ws)
        logger.info(f"Client disconnected. Total active: {len(self.clients)}")

    async def broadcast(self, message_type: str, data: dict) -> None:
        if not self.clients:
            return
        payload = json.dumps({"type": message_type, "data": data})
        dead_clients = set()
        for ws in self.clients:
            try:
                await ws.send(payload)
            except Exception:
                dead_clients.add(ws)
        for dead in dead_clients:
            self.clients.discard(dead)

    async def handler(self, ws: WebSocketServerProtocol) -> None:
        await self.register(ws)
        try:
            async for message in ws:
                data = json.loads(message)
                action = data.get("action")
                if action == "trigger_burst":
                    asyncio.create_task(self.run_burst())
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister(ws)

    async def run_burst(self) -> None:
        """Trigger an inference burst simulation and broadcast live telemetry."""
        logger.info("Starting inference burst...")
        accumulated_tokens = 0

        async for token_delta, stats in self.profiler.mock_stream():
            accumulated_tokens += 1
            vram_sample = self.vram_probe.sample(active_tokens=accumulated_tokens * 64)

            await self.broadcast("token_delta", {
                "token": token_delta.model_dump(),
                "metrics": stats.model_dump(),
                "vram": vram_sample.model_dump(),
            })

        logger.info(f"Burst completed. Total tokens: {accumulated_tokens}")

    async def start(self) -> None:
        self._running = True
        logger.info(f"VRAM-Samurai Telemetry Server starting on ws://{self.host}:{self.port}")
        async with websockets.serve(self.handler, self.host, self.port):
            await asyncio.Future()  # run forever


def main():
    server = TelemetryServer()
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logger.info("Server terminated.")


if __name__ == "__main__":
    main()
