import asyncio
import logging

import discord
from discord.ext import commands

from bot.config import load_config
from bot.espn_client import EspnClient
from bot.state import State

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("fantasy_bot")

COGS = ["bot.cogs.recap", "bot.cogs.preview", "bot.cogs.live", "bot.cogs.standings"]


class FantasyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        self.app_config = load_config()
        self.espn = EspnClient(self.app_config)
        self.state = State(self.app_config.state_file)

    async def setup_hook(self):
        for cog in COGS:
            await self.load_extension(cog)
        synced = await self.tree.sync()
        log.info("Synced %d slash commands", len(synced))

    async def on_ready(self):
        log.info("Logged in as %s (id: %s)", self.user, self.user.id)


async def main():
    bot = FantasyBot()
    async with bot:
        await bot.start(bot.app_config.discord_token)


if __name__ == "__main__":
    asyncio.run(main())
