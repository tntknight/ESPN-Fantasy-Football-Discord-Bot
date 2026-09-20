"""Posts this week's matchups + projected scores once, shortly after
PREVIEW_DAY/PREVIEW_HOUR (config), local to TIMEZONE.
"""

import datetime
import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks

from bot import formatting

log = logging.getLogger(__name__)


class Preview(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = bot.app_config
        self.espn = bot.espn
        self.state = bot.state
        self.check_preview.start()

    def cog_unload(self):
        self.check_preview.cancel()

    async def _post_preview(self, week: int) -> discord.Embed:
        box_scores = self.espn.box_scores(week)
        embed = formatting.build_preview_embed(week, box_scores)
        channel = self.bot.get_channel(self.config.discord_channel_id) or await self.bot.fetch_channel(
            self.config.discord_channel_id
        )
        await channel.send(embed=embed)
        return embed

    @tasks.loop(minutes=30)
    async def check_preview(self):
        now = datetime.datetime.now(self.config.timezone)
        if now.weekday() != self.config.preview_weekday or now.hour != self.config.preview_hour:
            return

        week = self.espn.current_week()
        if self.state.get("last_preview_week") == week:
            return

        try:
            await self._post_preview(week)
            self.state.set("last_preview_week", week)
        except Exception:
            log.exception("Failed to post matchup preview")

    @check_preview.before_loop
    async def before_check_preview(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="preview", description="Post the matchup preview for a given week (defaults to the current week)")
    @app_commands.describe(week="Week number, defaults to the current week")
    async def preview_command(self, interaction: discord.Interaction, week: Optional[int] = None):
        await interaction.response.defer(thinking=True, ephemeral=True)
        target_week = week or self.espn.current_week()
        try:
            await self._post_preview(target_week)
            await interaction.followup.send(f"Posted the Week {target_week} preview.", ephemeral=True)
        except Exception as e:
            log.exception("Manual preview command failed")
            await interaction.followup.send(f"Failed to post preview: {e}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Preview(bot))
