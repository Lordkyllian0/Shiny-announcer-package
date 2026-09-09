# BallsDex Shiny Announcer

External package for BallsDex DiscordBot v3.

It announces newly caught cards whose Special is named `Shiny` in one configured Discord text channel.

## Features

- `/config shiny announcer` sets the current text channel as the global shiny announcement channel.
- `/config shiny announcer channel:#channel` can target another text channel.
- Only BallsDex bot owners/staff (the same Django staff concept used by BallsDex admin commands) can configure it.
- Announcements use the BallsDex hexadecimal instance ID, e.g. `#186CBB`.
- New shiny catches from any server are announced in the configured channel.
- Dropped/existing BallInstances that are re-caught are not announced as newly caught shinies.
- Announcement style:

  `✨ Shiny Card Caught! ✨`

  `@Player caught a shiny Card Name (#186CBB)!`

## Install

Add the package to your BallsDex `config/extra.toml`:

```toml
[[ballsdex.packages]]
location = "git+https://github.com/Lordkyllian0/Shiny-announcer-package"
path = "shinyannouncer"
enabled = true
```

Then rebuild and start BallsDex:

```bash
docker compose build
docker compose up -d
```

The Django migration creates the `shiny_announcer_config` table.

After loading the package, refresh the command tree if necessary:

```text
@YourBot reload shinyannouncer.package
@YourBot reloadtree
```

## Configure

Run this in the channel that should receive shiny announcements:

```text
/config shiny announcer
```

Or choose a different text channel:

```text
/config shiny announcer channel:#shiny-catches
```

Running the command again moves the global announcer to the newly selected channel.

## Important

The package expects the special to be named exactly `Shiny` (case-insensitive).
