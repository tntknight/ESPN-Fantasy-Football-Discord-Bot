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


# Stat breakdown keys (already human-readable via espn_api's PLAYER_STATS_MAP)
# that indicate a player was directly involved in scoring a touchdown.
# defensivePlusSpecialTeamsTouchdowns is a rollup of D/ST's various TD types,
# used instead of the individual defensive/return TD stats to avoid
# double-counting a single score.
TD_STAT_INFO = {
    "passingTouchdowns": {"label": "threw a touchdown"},
    "rushingTouchdowns": {"label": "rushed for a touchdown"},
    "receivingTouchdowns": {"label": "caught a touchdown"},
    "fumbleRecoveredForTD": {"label": "recovered a fumble for a touchdown"},
    "defensivePlusSpecialTeamsTouchdowns": {"label": "scored a defensive/special teams touchdown"},
}

BENCHED_SLOTS = {"BE", "IR"}


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

    async def _check_touchdowns(self, week: int):
        alerts_enabled = self.state.get("touchdown_alerts_enabled", True)
        td_state = self.state.get("touchdowns", {})
        week_state = td_state.get(str(week), {})
        box_scores = self.espn.box_scores(week)
        channel = None

        for bs in box_scores:
            for team, lineup in ((bs.home_team, bs.home_lineup), (bs.away_team, bs.away_lineup)):
                if not team:
                    continue
                fantasy_team_name = formatting.team_name(team)

                for player in lineup:
                    if player.slot_position in BENCHED_SLOTS:
                        continue

                    player_key = str(player.playerId)
                    # First time we've ever tracked this player this week (bot just
                    # started, or state was reset) -- there's no previous poll to
                    # diff against, so seed the baseline silently instead of treating
                    # every touchdown they already have as brand new (which would
                    # also make their yardage-since-last-poll equal to their full
                    # weekly total instead of a single play).
                    first_sighting = player_key not in week_state
                    prev_stats = week_state.get(player_key, {})

                    if not first_sighting and alerts_enabled:
                        for stat_key, info in TD_STAT_INFO.items():
                            count = player.breakdown.get(stat_key, 0)
                            if count > prev_stats.get(stat_key, 0):
                                channel = channel or await self._channel()
                                await channel.send(
                                    embed=formatting.build_touchdown_embed(
                                        player.name, player.proTeam, fantasy_team_name, info["label"]
                                    )
                                )

                    week_state[player_key] = {k: player.breakdown.get(k, 0) for k in TD_STAT_INFO}

        td_state[str(week)] = week_state
        self.state.set("touchdowns", td_state)

    @tasks.loop(minutes=15)
    async def check_live(self):
        if not self._in_game_window():
            return
        try:
            week = self.espn.current_week()
            await self._check_week(week)
            await self._check_touchdowns(week)
        except Exception:
            log.exception("Live score poll failed")

    @check_live.before_loop
    async def before_check_live(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="scores", description="Show live scores for all of this week's games")
    async def scores_command(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        try:
            week = self.espn.current_week()
            embed = formatting.build_live_scores_embed(week, self.espn.box_scores(week))
            await interaction.followup.send(embed=embed)
        except Exception as e:
            log.exception("Scores command failed")
            await interaction.followup.send(f"Failed to fetch live scores: {e}", ephemeral=True)

    @app_commands.command(name="live", description="Force a live-score check right now, ignoring the game-window schedule")
    async def live_command(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            week = self.espn.current_week()
            await self._check_week(week)
            await self._check_touchdowns(week)
            await interaction.followup.send("Checked for lead changes / close games / touchdowns.", ephemeral=True)
        except Exception as e:
            log.exception("Manual live command failed")
            await interaction.followup.send(f"Failed to check live scores: {e}", ephemeral=True)

    @app_commands.command(name="touchdowns", description="Turn touchdown alerts on or off")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.choices(
        enabled=[
            app_commands.Choice(name="on", value="on"),
            app_commands.Choice(name="off", value="off"),
        ]
    )
    async def touchdowns_command(self, interaction: discord.Interaction, enabled: app_commands.Choice[str]):
        is_enabled = enabled.value == "on"
        self.state.set("touchdown_alerts_enabled", is_enabled)
        await interaction.response.send_message(
            f"Touchdown alerts are now **{'on' if is_enabled else 'off'}**.", ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Live(bot))
