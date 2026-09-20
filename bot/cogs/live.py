"""Polls in-progress box scores during typical NFL game windows and posts
an alert on a lead change or a game that's within LIVE_CLOSE_MARGIN points.

This is a simple heuristic, not tied to real game-clock/quarter data (the
espn_api box score doesn't reliably expose that for fantasy matchups) -- it
just compares scores between polls. Tune LIVE_POLL_MINUTES / LIVE_CLOSE_MARGIN
in .env, and adjust the game-window check below if your league wants
different days/hours watched.
"""

import logging

import discord
from discord import app_commands
from discord.ext import commands, tasks

from bot import formatting

log = logging.getLogger(__name__)

# weekday(): Mon=0 ... Sun=6. Games roughly run Thu evening, Sun midday-night,
# Mon evening -- widen/narrow this if your league also has real-world
# preferences (e.g. only care about Sunday afternoon games).
GAME_DAYS = {3, 6, 0}  # Thu, Sun, Mon
GAME_WINDOW_HOURS = range(12, 24)  # local hour, inclusive-exclusive


def _matchup_key(week: int, index: int) -> str:
    return f"{week}:{index}"


class Live(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = bot.app_config
        self.espn = bot.espn
        self.state = bot.state
        self.check_live.change_interval(minutes=self.config.live_poll_minutes)
        self.check_live.start()

    def cog_unload(self):
        self.check_live.cancel()

    def _in_game_window(self) -> bool:
        import datetime

        now = datetime.datetime.now(self.config.timezone)
        return now.weekday() in GAME_DAYS and now.hour in GAME_WINDOW_HOURS

    async def _channel(self):
        return self.bot.get_channel(self.config.discord_channel_id) or await self.bot.fetch_channel(
            self.config.discord_channel_id
        )

    async def _check_week(self, week: int):
        live_state = self.state.get("live", {})
        week_state = live_state.get(str(week), {})
        box_scores = self.espn.box_scores(week)
        channel = None

        for i, bs in enumerate(box_scores):
            if not bs.away_team or not bs.home_team:
                continue

            key = _matchup_key(week, i)
            entry = week_state.get(key, {"leader": None, "close_alerted": False})

            home_name = formatting.team_name(bs.home_team)
            away_name = formatting.team_name(bs.away_team)
            home_score, away_score = bs.home_score, bs.away_score

            if home_score == 0 and away_score == 0:
                week_state[key] = entry
                continue

            leader = "home" if home_score >= away_score else "away"
            margin = abs(home_score - away_score)

            if entry["leader"] is not None and entry["leader"] != leader:
                channel = channel or await self._channel()
                await channel.send(
                    embed=formatting.build_lead_change_embed(home_name, away_name, home_score, away_score)
                )
            entry["leader"] = leader

            if not entry["close_alerted"] and margin <= self.config.live_close_margin:
                channel = channel or await self._channel()
                await channel.send(
                    embed=formatting.build_close_game_embed(home_name, away_name, home_score, away_score)
                )
                entry["close_alerted"] = True

            week_state[key] = entry

        live_state[str(week)] = week_state
        self.state.set("live", live_state)

    @tasks.loop(minutes=15)
    async def check_live(self):
        if not self._in_game_window():
            return
        try:
            await self._check_week(self.espn.current_week())
        except Exception:
            log.exception("Live score poll failed")

    @check_live.before_loop
    async def before_check_live(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="live", description="Force a live-score check right now, ignoring the game-window schedule")
    async def live_command(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            await self._check_week(self.espn.current_week())
            await interaction.followup.send("Checked for lead changes / close games.", ephemeral=True)
        except Exception as e:
            log.exception("Manual live command failed")
            await interaction.followup.send(f"Failed to check live scores: {e}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Live(bot))
