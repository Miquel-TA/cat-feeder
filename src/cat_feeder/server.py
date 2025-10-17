"""FastAPI server to expose overlay and status pages."""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from .models import Donation, QueueStatus

logger = logging.getLogger(__name__)


class OverlayBroadcaster:
    """Manage WebSocket connections for overlay alerts."""

    def __init__(self):
        self._connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)
        logger.info("Overlay websocket connected (%d clients)", len(self._connections))

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)
        logger.info("Overlay websocket disconnected (%d clients)", len(self._connections))

    async def broadcast(self, payload: Dict) -> None:
        message = json.dumps(payload)
        disconnects: List[WebSocket] = []
        async with self._lock:
            for connection in self._connections:
                try:
                    await connection.send_text(message)
                except WebSocketDisconnect:
                    disconnects.append(connection)
                except Exception:  # pragma: no cover
                    logger.exception("Failed to send overlay update")
                    disconnects.append(connection)
            for connection in disconnects:
                self._connections.discard(connection)


class OverlayServer:
    """FastAPI application to serve overlays and broadcast donations."""

    def __init__(self, static_dir: Path, template_dir: Path, status_interval: float = 5.0):
        self._app = FastAPI(title="Cat Feeder Overlay")
        self._broadcaster = OverlayBroadcaster()
        self._templates = Jinja2Templates(directory=str(template_dir))
        self._sleep_mode_flag = False
        self._latest_queue_status: Optional[QueueStatus] = None
        self._status_interval = status_interval

        self._app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

        @self._app.get("/overlay", response_class=HTMLResponse)
        async def overlay(request: Request):
            return self._templates.TemplateResponse("overlay.html", {"request": request})

        @self._app.get("/sleep", response_class=HTMLResponse)
        async def sleep(request: Request):
            return self._templates.TemplateResponse(
                "sleep_mode.html", {"request": request, "status_interval": self._status_interval}
            )

        @self._app.get("/api/status")
        async def api_status():
            if not self._latest_queue_status:
                return {
                    "sleep_mode": self._sleep_mode_flag,
                    "queue_active": False,
                    "seconds_until_wake": None,
                }
            return {
                "sleep_mode": self._latest_queue_status.sleep_mode,
                "queue_active": self._latest_queue_status.active,
                "seconds_until_wake": self._latest_queue_status.seconds_until_wake,
            }

        @self._app.websocket("/ws/overlay")
        async def overlay_ws(websocket: WebSocket):
            await self._broadcaster.connect(websocket)
            try:
                while True:
                    await websocket.receive_text()
            except WebSocketDisconnect:
                await self._broadcaster.disconnect(websocket)

        @self._app.websocket("/ws/status")
        async def status_ws(websocket: WebSocket):
            await websocket.accept()
            try:
                while True:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "sleep_mode": self._sleep_mode_flag,
                                "queue_active": bool(self._latest_queue_status and self._latest_queue_status.active),
                                "seconds_until_wake": (
                                    self._latest_queue_status.seconds_until_wake
                                    if self._latest_queue_status
                                    else None
                                ),
                            }
                        )
                    )
                    await asyncio.sleep(self._status_interval)
            except WebSocketDisconnect:
                return

    @property
    def app(self) -> FastAPI:
        return self._app

    async def send_donation(self, donation: Donation, tier_animation: str, tier_sound: str) -> None:
        payload = {
            "username": donation.username,
            "coins": donation.coins,
            "tier": donation.tier,
            "tier_name": donation.tier_name,
            "message": donation.message,
            "animation": tier_animation,
            "sound": tier_sound,
        }
        await self._broadcaster.broadcast({"type": "donation", "payload": payload})

    async def send_queue_status(self, status: QueueStatus) -> None:
        self._latest_queue_status = status
        self._sleep_mode_flag = status.sleep_mode
        await self._broadcaster.broadcast(
            {
                "type": "status",
                "payload": {
                    "sleep_mode": status.sleep_mode,
                    "queue_active": status.active,
                    "seconds_until_wake": status.seconds_until_wake,
                },
            }
        )
