"""Display server for donation events."""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
import uvicorn

from .config import AppConfig
from .sleep import SleepController

LOGGER = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    async def broadcast(self, payload: Dict[str, Any]) -> None:
        async with self._lock:
            connections = list(self._connections)
        message = json.dumps(payload)
        for connection in connections:
            try:
                await connection.send_text(message)
            except WebSocketDisconnect:
                await self.disconnect(connection)
            except RuntimeError:
                LOGGER.debug("Connection closed during broadcast")


class DisplayServer:
    def __init__(
        self,
        config: AppConfig,
        sleep_controller: SleepController,
    ) -> None:
        self._config = config
        self._sleep_controller = sleep_controller
        self._donation_ws = WebSocketManager()
        self._sleep_ws = WebSocketManager()
        self._app = FastAPI()
        self._setup_routes()
        self._server: uvicorn.Server | None = None

    def _setup_routes(self) -> None:
        static_path = Path(__file__).parent / "static"
        templates_path = Path(__file__).parent / "templates"
        self._templates = Jinja2Templates(directory=str(templates_path))
        self._app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

        @self._app.get("/", response_class=HTMLResponse)
        async def donations_page(request: Request) -> HTMLResponse:
            return self._templates.TemplateResponse("donations.html", {"request": request})

        @self._app.get("/sleep", response_class=HTMLResponse)
        async def sleep_page(request: Request) -> HTMLResponse:
            state = self._sleep_controller.get_state()
            return self._templates.TemplateResponse(
                "sleep_status.html",
                {
                    "request": request,
                    "is_sleeping": state.is_sleeping,
                    "next_transition": state.next_transition.isoformat(),
                },
            )

        @self._app.websocket("/ws/donations")
        async def donations_socket(websocket: WebSocket) -> None:
            await self._donation_ws.connect(websocket)
            try:
                while True:
                    await websocket.receive_text()
            except WebSocketDisconnect:
                await self._donation_ws.disconnect(websocket)

        @self._app.websocket("/ws/sleep")
        async def sleep_socket(websocket: WebSocket) -> None:
            await self._sleep_ws.connect(websocket)
            state = self._sleep_controller.get_state()
            await websocket.send_text(
                json.dumps(
                    {
                        "sleeping": state.is_sleeping,
                        "next_transition": state.next_transition.isoformat(),
                    }
                )
            )
            try:
                while True:
                    await websocket.receive_text()
            except WebSocketDisconnect:
                await self._sleep_ws.disconnect(websocket)

        @self._app.post("/sleep/toggle")
        async def toggle_sleep(payload: Dict[str, Any]) -> JSONResponse:
            override = payload.get("override")
            if override not in (True, False, None):
                raise HTTPException(status_code=400, detail="Invalid override value")
            await self._sleep_controller.set_manual_override(override)
            state = self._sleep_controller.get_state()
            return JSONResponse(
                {
                    "sleeping": state.is_sleeping,
                    "next_transition": state.next_transition.isoformat(),
                }
            )

        @self._app.get("/health")
        async def healthcheck() -> Dict[str, Any]:
            return {"status": "ok"}

    async def broadcast_donation(self, payload: Dict[str, Any]) -> None:
        await self._donation_ws.broadcast({"type": "donation", "payload": payload})

    async def broadcast_sleep(self, sleeping: bool) -> None:
        state = self._sleep_controller.get_state()
        await self._sleep_ws.broadcast(
            {
                "type": "sleep",
                "payload": {
                    "sleeping": sleeping,
                    "next_transition": state.next_transition.isoformat(),
                },
            }
        )

    async def run(self) -> None:
        settings = self._config.server
        config = uvicorn.Config(self._app, host=settings.host, port=settings.port, log_level="info")
        self._server = uvicorn.Server(config)
        LOGGER.info("Starting display server on %s:%s", settings.host, settings.port)
        await self._server.serve()

    async def stop(self) -> None:
        if self._server is not None:
            self._server.should_exit = True
