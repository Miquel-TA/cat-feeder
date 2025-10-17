"""TikTok donation client wrapper with reconnection logic."""
from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable

try:
    from tiktoklive import TikTokLiveClient
    from tiktoklive.events import GiftEvent, FollowEvent, SubscribeEvent
except ImportError:  # pragma: no cover - optional dependency
    TikTokLiveClient = None
    GiftEvent = None
    FollowEvent = None
    SubscribeEvent = None

logger = logging.getLogger(__name__)

DonationCallback = Callable[[str, int, str | None], Awaitable[None]]


class TikTokDonationClient:
    """Connect to TikTok live stream and emit donation events."""

    def __init__(self, username: str, reconnect_delay: float = 5.0):
        if not username:
            raise ValueError("TikTok username is required")
        self._username = username
        self._reconnect_delay = reconnect_delay
        self._callback: DonationCallback | None = None
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._live_client = None

        if TikTokLiveClient is None:
            logger.warning("tiktoklive package is not installed; donation stream disabled")

    def start(self, callback: DonationCallback) -> None:
        self._callback = callback
        if self._task and not self._task.done():
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stop_event.set()
        if self._live_client:
            try:
                await self._live_client.stop()
            except Exception:  # pragma: no cover
                pass
        if self._task:
            await self._task

    async def _run(self) -> None:
        if TikTokLiveClient is None:
            logger.error("Cannot start TikTok client without tiktoklive dependency")
            return

        while not self._stop_event.is_set():
            client = TikTokLiveClient(unique_id=self._username)
            self._live_client = client

            @client.on("gift")
            async def on_gift(event: GiftEvent):  # type: ignore
                if not self._callback:
                    return
                repeat_end = getattr(event, "repeat_end", True)
                streakable = getattr(getattr(event, "gift", None), "streakable", False)
                if streakable and not repeat_end:
                    return
                coins = getattr(event.gift, "diamond_count", 0) * max(1, getattr(event, "repeat_count", 1))
                username_obj = getattr(event, "user", None)
                if username_obj:
                    username = getattr(username_obj, "nickname", getattr(username_obj, "unique_id", "Unknown"))
                else:
                    username = "Unknown"
                comment = getattr(event, "comment", None)
                await self._callback(username, coins, comment)

            @client.on("subscribe")
            async def on_sub(event: SubscribeEvent):  # type: ignore
                if not self._callback:
                    return
                username = getattr(event, "user", None)
                if username:
                    username = getattr(username, "nickname", getattr(username, "unique_id", "Unknown"))
                else:
                    username = "Unknown"
                await self._callback(username, 50, "Subscription")

            @client.on("follow")
            async def on_follow(event: FollowEvent):  # type: ignore
                if not self._callback:
                    return
                username = getattr(event, "user", None)
                if username:
                    username = getattr(username, "nickname", getattr(username, "unique_id", "Unknown"))
                else:
                    username = "Unknown"
                await self._callback(username, 1, "Follow")

            try:
                logger.info("Connecting to TikTok live stream for %s", self._username)
                await client.start()
            except Exception:
                logger.exception("TikTok client disconnected, retrying in %ss", self._reconnect_delay)
                await asyncio.sleep(self._reconnect_delay)
            finally:
                try:
                    await client.close()
                except Exception:  # pragma: no cover
                    pass

            if self._stop_event.is_set():
                break

        self._live_client = None
