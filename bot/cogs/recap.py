"""Posts a recap of the previous week's final scores + standings, once,
shortly after RECAP_DAY/RECAP_HOUR (config), local to TIMEZONE.
"""

import datetime
import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks

from bot import formatting

log = logging.getLogger(__name__)


class Recap(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = bot.app_config
        self.espn = bot.espn
        self.state = bot.state
        self.check_recap.start()

    def cog_unload(self):
        self.check_recap.cancel()

    async def _post_recap(self, week: int) -> discord.Embed:
        box_scores = self.espn.box_scores(week)
        embed = formatting.build_recap_embed(week, box_scores)
        channel = self.bot.get_channel(self.config.discord_channel_id) or await self.bot.fetch_channel(
            self.config.discord_channel_id
        )
        await channel.send(embed=embed)
        standings_embed = formatting.build_standings_embed(self.espn.standings())
        await channel.send(embed=standings_embed)
        return embed

    @tasks.loop(minutes=30)
    async def check_recap(self):
        now = datetime.datetime.now(self.config.timezone)
        if now.weekday() != self.config.recap_weekday or now.hour != self.config.recap_hour:
            return

        week_to_recap = self.espn.current_week() - 1
        if week_to_recap < 1:
            return
        if self.state.get("last_recap_week") == week_to_recap:
            return

        try:
            await self._post_recap(week_to_recap)
            self.state.set("last_recap_week", week_to_recap)
        except Exception:
            log.exception("Failed to post weekly recap")

    @check_recap.before_loop
    async def before_check_recap(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="recap", description="Post the recap for a given week (defaults to last week)")
    @app_commands.describe(week="Week number, defaults to the most recently completed week")
    async def recap_command(self, interaction: discord.Interaction, week: Optional[int] = None):
        await interaction.response.defer(thinking=True, ephemeral=True)
        target_week = week or (self.espn.current_week() - 1)
        try:
            await self._post_recap(target_week)
            await interaction.followup.send(f"Posted the Week {target_week} recap.", ephemeral=True)
        except Exception as e:
            log.exception("Manual recap command failed")
            await interaction.followup.send(f"Failed to post recap: {e}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Recap(bot))
