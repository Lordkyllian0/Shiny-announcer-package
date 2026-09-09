from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ShinyAnnouncementConfig",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("guild_id", models.BigIntegerField()),
                ("channel_id", models.BigIntegerField()),
            ],
            options={
                "db_table": "shiny_announcer_config",
                "verbose_name": "Shiny announcer configuration",
                "verbose_name_plural": "Shiny announcer configuration",
            },
        ),
    ]
