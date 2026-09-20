"""On-demand /standings command. No background loop -- purely reactive."""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot import formatting

log = logging.getLogger(__name__)


class Standings(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.espn = bot.espn

    @app_commands.command(name="standings", description="Post the current league standings")
    async def standings_command(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        try:
            embed = formatting.build_standings_embed(self.espn.standings())
            await interaction.followup.send(embed=embed)
        except Exception as e:
            log.exception("Standings command failed")
            await interaction.followup.send(f"Failed to fetch standings: {e}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Standings(bot))
