from django.db import models


class ShinyAnnouncementConfig(models.Model):
    """Global destination used for shiny catch announcements."""

    guild_id = models.BigIntegerField()
    channel_id = models.BigIntegerField()

    class Meta:
        db_table = "shiny_announcer_config"
        verbose_name = "Shiny announcer configuration"
        verbose_name_plural = "Shiny announcer configuration"

    def __str__(self) -> str:
        return f"Guild {self.guild_id} -> channel {self.channel_id}"
