from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

import discord
from discord import app_commands
from discord.ext import commands

from ballsdex.core.utils.checks import get_user_for_check
from ballsdex.packages.countryballs.countryball import BallSpawnView
from shinyannouncer.models import ShinyAnnouncementConfig

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot
    from bd_models.models import BallInstance

log = logging.getLogger("ballsdex.packages.shinyannouncer")

SHINY_NAME = "shiny"


async def is_bot_staff(interaction: discord.Interaction["BallsDexBot"]) -> bool:
    """Use the same Django staff/owner concept as BallsDex's bot-admin commands."""
    user = await get_user_for_check(interaction.client, interaction.user)

    if user is True:
        return True
    if user is False:
        return False

    return bool(user.is_staff)


class ShinyAnnouncer(commands.Cog):
    def __init__(self, bot: "BallsDexBot"):
        self.bot = bot
        self.shiny_group: app_commands.Group | None = None
        self._original_catch_ball: Any = None

    async def install(self) -> None:
        self._install_config_command()
        self._install_catch_hook()

    async def uninstall(self) -> None:
        self._remove_config_command()
        self._remove_catch_hook()

    async def cog_unload(self) -> None:
        # discord.py calls this when the extension/cog is unloaded or reloaded.
        await self.uninstall()

    def _install_config_command(self) -> None:
        config_group = self.bot.tree.get_command("config")

        if not isinstance(config_group, app_commands.Group):
            raise RuntimeError(
                "Could not find BallsDex's /config command group. "
                "Make sure the guildconfig package is enabled."
            )

        # Clean up a stale copy after an extension reload.
        existing = config_group.get_command("shiny")
        if existing is not None:
            config_group.remove_command("shiny")

        shiny_group = app_commands.Group(
            name="shiny",
            description="Configure shiny-card features.",
        )

        async def announcer(
            interaction: discord.Interaction,
            channel: discord.TextChannel | None = None,
        ) -> None:
            """Set the channel where shiny catches are announced."""
            if not await is_bot_staff(interaction):
                await interaction.response.send_message(
                    "Only BallsDex bot staff can configure the shiny announcer.",
                    ephemeral=True,
                )
                return

            if interaction.guild is None:
                await interaction.response.send_message(
                    "This command can only be used in a server.",
                    ephemeral=True,
                )
                return

            if channel is None:
                if isinstance(interaction.channel, discord.TextChannel):
                    channel = interaction.channel
                else:
                    await interaction.response.send_message(
                        "Use this command in a text channel, or choose a text channel explicitly.",
                        ephemeral=True,
                    )
                    return

            permissions = channel.permissions_for(interaction.guild.me)
            missing: list[str] = []
            if not permissions.view_channel:
                missing.append("View Channel")
            if not permissions.send_messages:
                missing.append("Send Messages")
            if not permissions.embed_links:
                missing.append("Embed Links")

            if missing:
                await interaction.response.send_message(
                    f"I cannot use {channel.mention}. Missing: **{', '.join(missing)}**.",
                    ephemeral=True,
                )
                return

            # This package intentionally has one global announcement destination.
            # Running the command again moves the announcer to the new channel.
            config = await ShinyAnnouncementConfig.objects.afirst()
            if config is None:
                config = await ShinyAnnouncementConfig.objects.acreate(
                    guild_id=interaction.guild.id,
                    channel_id=channel.id,
                )
            else:
                config.guild_id = interaction.guild.id
                config.channel_id = channel.id
                await config.asave(update_fields=("guild_id", "channel_id"))

            await interaction.response.send_message(
                f"✨ Shiny catches will now be announced in {channel.mention}.",
                ephemeral=True,
            )

        command = app_commands.Command(
            name="announcer",
            description="Set the channel used for shiny catch announcements.",
            callback=announcer,
        )
        shiny_group.add_command(command)
        config_group.add_command(shiny_group)
        self.shiny_group = shiny_group

        log.info("Registered /config shiny announcer")

    def _remove_config_command(self) -> None:
        config_group = self.bot.tree.get_command("config")
        if isinstance(config_group, app_commands.Group):
            existing = config_group.get_command("shiny")
            if existing is self.shiny_group or existing is not None:
                config_group.remove_command("shiny")

        self.shiny_group = None

    def _install_catch_hook(self) -> None:
        current = BallSpawnView.catch_ball

        # If a previous reload left our wrapper behind, unwrap it first.
        original = getattr(current, "__shiny_announcer_original__", current)
        self._original_catch_ball = original
        cog = self

        async def wrapped_catch_ball(
            spawn_view: BallSpawnView,
            user: discord.User | discord.Member,
            *,
            player,
            guild: discord.Guild | None,
        ):
            # Existing dropped cards are transfers, not newly generated catches.
            was_existing_instance = spawn_view.ballinstance is not None

            ball, is_new = await original(
                spawn_view,
                user,
                player=player,
                guild=guild,
            )

            if not was_existing_instance:
                special = ball.specialcard
                if special and special.name.casefold() == SHINY_NAME:
                    task = asyncio.create_task(
                        cog.announce_shiny(
                            ball=ball,
                            catcher_id=user.id,
                        )
                    )
                    task.add_done_callback(cog._announcement_task_done)

            return ball, is_new

        wrapped_catch_ball.__shiny_announcer_original__ = original  # type: ignore[attr-defined]
        BallSpawnView.catch_ball = wrapped_catch_ball  # type: ignore[method-assign]

        log.info("Installed shiny catch hook")

    def _remove_catch_hook(self) -> None:
        if self._original_catch_ball is not None:
            BallSpawnView.catch_ball = self._original_catch_ball  # type: ignore[method-assign]
            self._original_catch_ball = None

    def _announcement_task_done(self, task: asyncio.Task) -> None:
        try:
            task.result()
        except Exception:
            log.exception("Failed to send shiny announcement")

    async def announce_shiny(
        self,
        *,
        ball: "BallInstance",
        catcher_id: int,
    ) -> None:
        config = await ShinyAnnouncementConfig.objects.afirst()
        if config is None:
            return

        channel = self.bot.get_channel(config.channel_id)

        if channel is None:
            try:
                channel = await self.bot.fetch_channel(config.channel_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                log.warning(
                    "Configured shiny announcement channel %s could not be fetched",
                    config.channel_id,
                )
                return

        if not isinstance(channel, discord.TextChannel):
            log.warning(
                "Configured shiny announcement channel %s is not a text channel",
                config.channel_id,
            )
            return

        # If the catcher belongs to the announcement server, Discord resolves this
        # as their normal member mention. If not, Discord shows the raw user-ID mention,
        # matching the desired cross-server announcement style.
        catcher = f"<@{catcher_id}>"

        embed = discord.Embed(
            title="✨ Shiny Card Caught! ✨",
            description=(
                f"{catcher} caught a shiny "
                f"**{ball.countryball.country}** "
                f"(#{ball.pk:0X})!"
            ),
            color=discord.Color.gold(),
        )

        await channel.send(
            embed=embed,
            allowed_mentions=discord.AllowedMentions(users=True),
        )
