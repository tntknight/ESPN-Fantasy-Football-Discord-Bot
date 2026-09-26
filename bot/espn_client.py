"""Thin wrapper around espn_api.football.League.

Keeps all the espn_api-specific attribute access in one place, since that
library's attribute names have shifted slightly between versions -- if ESPN
or espn_api changes something, this is the one file that needs updating.
"""

import logging
import time

from espn_api.football import League

from bot.config import Config

log = logging.getLogger(__name__)

# league.current_week / currentMatchupPeriod / team records are plain
# attributes espn_api sets once when the League object is built (or when
# .refresh() is called) -- they never update on their own. Since the League
# object below is cached for the life of the process, every method here
# routes through league() so a single throttle keeps all of them (current
# week, box scores, standings) from silently running on data frozen at
# whatever it was when the bot last started.
REFRESH_INTERVAL_SECONDS = 60


class EspnClient:
    def __init__(self, config: Config):
        self._config = config
        self._league: League | None = None
        self._last_refreshed = 0.0

    def league(self) -> League:
        if self._league is None:
            self._league = League(
                league_id=self._config.espn_league_id,
                year=self._config.espn_year,
                espn_s2=self._config.espn_s2,
                swid=self._config.espn_swid,
            )
            self._last_refreshed = time.monotonic()
        elif time.monotonic() - self._last_refreshed >= REFRESH_INTERVAL_SECONDS:
            self._league.refresh()
            self._last_refreshed = time.monotonic()
        return self._league

    def refresh(self) -> League:
        self._league = None
        return self.league()

    def current_week(self) -> int:
        return self.league().current_week

    def box_scores(self, week: int | None = None):
        return self.league().box_scores(week=week) if week else self.league().box_scores()

    def standings(self) -> list:
        return self.league().standings()
