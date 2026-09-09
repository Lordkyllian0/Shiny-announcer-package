import logging
from typing import TYPE_CHECKING

from .cog import ShinyAnnouncer

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

log = logging.getLogger("ballsdex.packages.shinyannouncer")


async def setup(bot: "BallsDexBot"):
    cog = ShinyAnnouncer(bot)
    await bot.add_cog(cog)
    await cog.install()
    log.info("Shiny announcer package loaded successfully.")


async def teardown(bot: "BallsDexBot"):
    cog = bot.get_cog("ShinyAnnouncer")
    if isinstance(cog, ShinyAnnouncer):
        await cog.uninstall()
