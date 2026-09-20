"""Thin wrapper around espn_api.football.League.

Keeps all the espn_api-specific attribute access in one place, since that
library's attribute names have shifted slightly between versions -- if ESPN
or espn_api changes something, this is the one file that needs updating.
"""

import logging

from espn_api.football import League

from bot.config import Config

log = logging.getLogger(__name__)


class EspnClient:
    def __init__(self, config: Config):
        self._config = config
        self._league: League | None = None

    def league(self) -> League:
        # Recreated lazily / on-demand rather than cached forever, so a
        # transient ESPN API error doesn't permanently wedge the bot.
        if self._league is None:
            self._league = League(
                league_id=self._config.espn_league_id,
                year=self._config.espn_year,
                espn_s2=self._config.espn_s2,
                swid=self._config.espn_swid,
            )
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
