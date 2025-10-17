from __future__ import annotations

import logging
from pathlib import Path

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request

from .arduino import ArduinoController
from .config import load_settings
from .donation_manager import DonationManager
from .models import DonationRequest, Settings
from .sleep import is_sleep_mode_active

LOGGER = logging.getLogger(__name__)

APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent.parent
SETTINGS_PATH = ROOT_DIR / "config" / "settings.json"


def create_app(settings_path: Path | None = None) -> FastAPI:
    settings = load_settings(settings_path or SETTINGS_PATH)
    arduino = ArduinoController(settings.serial)
    manager = DonationManager(settings, arduino)

    app = FastAPI(title="Cat Shelter Donation Queue")
    app.add_event_handler("startup", manager.start)
    app.add_event_handler("shutdown", manager.stop)

    app.state.settings = settings
    app.state.manager = manager

    templates = Jinja2Templates(directory=str(ROOT_DIR / "templates"))
    app.mount("/static", StaticFiles(directory=str(ROOT_DIR / "static")), name="static")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.post("/donations", status_code=201)
    async def enqueue_donation(
        donation: DonationRequest, manager: DonationManager = Depends(get_manager)
    ):
        donation_record = await manager.add_donation(donation)
        return donation_record.to_payload()

    @app.get("/donations/recent")
    async def list_recent_donations(manager: DonationManager = Depends(get_manager)):
        donations = [item.to_payload() for item in manager.recent_donations()]
        return {"items": donations}

    @app.get("/sleep-mode")
    async def sleep_mode_status(settings: Settings = Depends(get_settings)):
        active = is_sleep_mode_active(settings.sleep_mode)
        return {"active": active, "config": settings.sleep_mode.__dict__}

    @app.get("/overlay", response_class=HTMLResponse)
    async def overlay_page(request: Request):
        return templates.TemplateResponse("overlay.html", {"request": request})

    @app.get("/sleep-status", response_class=HTMLResponse)
    async def sleep_status_page(
        request: Request, settings: Settings = Depends(get_settings)
    ):
        active = is_sleep_mode_active(settings.sleep_mode)
        return templates.TemplateResponse(
            "sleep_status.html",
            {
                "request": request,
                "active": active,
                "sleep_mode": settings.sleep_mode,
            },
        )

    @app.websocket("/ws/alerts")
    async def websocket_alerts(websocket: WebSocket, manager: DonationManager = Depends(get_manager)):
        await websocket.accept()
        queue = manager.register_subscriber()
        LOGGER.info("Overlay connected")
        try:
            while True:
                payload = await queue.get()
                await websocket.send_json({"type": "donation", "data": payload})
        except WebSocketDisconnect:
            LOGGER.info("Overlay disconnected")
        except Exception:
            LOGGER.exception("Unexpected error in websocket handler")
        finally:
            manager.unregister_subscriber(queue)

    return app


async def get_manager(request: Request) -> DonationManager:
    return request.app.state.manager


async def get_settings(request: Request) -> Settings:
    return request.app.state.settings


app = create_app()

