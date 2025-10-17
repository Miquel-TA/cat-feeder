from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

from .models import SleepMode


def parse_time(value: str) -> time:
    hour, minute = value.split(":", 1)
    return time(int(hour), int(minute))


def is_sleep_mode_active(config: SleepMode, *, now: datetime | None = None) -> bool:
    if not config.enabled:
        return False

    tz = ZoneInfo(config.timezone)
    now = now or datetime.now(tz)
    if now.tzinfo is None:
        now = now.replace(tzinfo=tz)
    else:
        now = now.astimezone(tz)

    start_time = parse_time(config.start)
    end_time = parse_time(config.end)

    start_dt = now.replace(hour=start_time.hour, minute=start_time.minute, second=0, microsecond=0)
    end_dt = now.replace(hour=end_time.hour, minute=end_time.minute, second=0, microsecond=0)

    if start_time <= end_time:
        return start_dt <= now < end_dt

    # Window crosses midnight
    return now >= start_dt or now < end_dt

