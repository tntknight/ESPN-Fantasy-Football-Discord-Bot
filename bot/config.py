"""Loads and validates all settings from environment variables."""

import os
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _day_to_weekday(day: str) -> int:
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    try:
        return days.index(day[:3].title())
    except ValueError:
        raise RuntimeError(f"Invalid day '{day}', expected one of {days}")


@dataclass(frozen=True)
class Config:
    discord_token: str
    discord_channel_id: int

    espn_league_id: int
    espn_year: int
    espn_swid: str | None
    espn_s2: str | None

    timezone: ZoneInfo

    recap_weekday: int
    recap_hour: int
    preview_weekday: int
    preview_hour: int

    live_poll_minutes: int
    live_close_margin: float

    state_file: str


def load_config() -> Config:
    return Config(
        discord_token=_required("DISCORD_TOKEN"),
        discord_channel_id=int(_required("DISCORD_CHANNEL_ID")),
        espn_league_id=int(_required("ESPN_LEAGUE_ID")),
        espn_year=int(os.environ.get("ESPN_YEAR", "2026")),
        espn_swid=os.environ.get("ESPN_SWID") or None,
        espn_s2=os.environ.get("ESPN_S2") or None,
        timezone=ZoneInfo(os.environ.get("TIMEZONE", "America/New_York")),
        recap_weekday=_day_to_weekday(os.environ.get("RECAP_DAY", "Tue")),
        recap_hour=int(os.environ.get("RECAP_HOUR", "9")),
        preview_weekday=_day_to_weekday(os.environ.get("PREVIEW_DAY", "Thu")),
        preview_hour=int(os.environ.get("PREVIEW_HOUR", "18")),
        live_poll_minutes=int(os.environ.get("LIVE_POLL_MINUTES", "15")),
        live_close_margin=float(os.environ.get("LIVE_CLOSE_MARGIN", "15")),
        state_file=os.environ.get("STATE_FILE", "state.json"),
    )
