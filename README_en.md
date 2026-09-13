# Iridium

MCDReforged plugin: item share / wear on head / player head / calculator / join MOTD.

| | |
|---|---|
| Version | **26.9.14** |
| Author | 云镜之端/SKYMirror |
| License | All Rights Reserved |
| Requires | MCDReforged `>= 2.6.0` |
| Minecraft | **1.7.10+** (feature-gated by version) |
| Python deps | None |

## Features

| Command | Description |
|---------|-------------|
| `!!share` | Share held item: name in chat, hover for full data |
| `!!hat` | Swap main-hand item with head slot |
| `!!head [player]` | Get **one** player head (default: yourself); cooldown |
| `!!c <expression>` | In-game calculator: `+ - * / // % ** ^` |
| Join MOTD | Uptime days, custom lines, clickable links, `§` colors |
| Join tips | Command list; click fills chat |

### Version support

| Feature | 1.7.10 | 1.8–1.12 | 1.13–1.16 | 1.17–1.20.4 | 1.20.5+ |
|---------|:------:|:--------:|:---------:|:-----------:|:-------:|
| `!!c` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `!!head` | ✅ | ✅ | ✅ | ✅ | ✅ profile |
| `!!share` | ❌ | ✅ entitydata | ✅ data get | ✅ | ✅ |
| `!!hat` | ❌ | ✅ RCON | ✅ RCON | ✅ RCON | ✅ RCON |
| MOTD / tips | ✅ | ✅ | ✅ | ✅ | ✅ |

## Install

1. Download `Iridium.mcdr`
2. Put it in MCDR `plugins/`
3. `!!MCDR reload plugin` or restart MCDR

### RCON (required for `!!hat`)

```properties
enable-rcon=true
rcon.port=25575
rcon.password=your_password
```

## Config

Path: `config/iridium/iridium.yml` (YAML with `#` comments; auto-created on first load; migrates legacy JSON configs)

| Field | Default | Description |
|------|---------|-------------|
| `permission` | `1` | Min permission for commands |
| `head_cooldown_seconds` | `60` | `!!head` cooldown; `0` = none |
| `hat_cooldown_seconds` | `3` | `!!hat` cooldown; `0` = none |
| `share_sound` | `true` | Sound on `!!share` |
| `force_version` | `""` | Force MC version; empty = auto |
| `join_tip` | `true` | Command tips on join |
| `join_tip_delay_seconds` | `1.5` | Join message delay |
| `motd_enabled` | `true` | Send join MOTD |
| `motd_start_day` | today | Server start date `YYYY-MM-DD` (day 1 = that date) |
| `motd_lines` | see file | MOTD lines with placeholders |

Default `motd_lines` (QQ group is clickable):

```text
§6Welcome §e{player}§6 !
§7Server has been open for §b{days}§7 days
§7Website: {link:§bOpen website|https://www.skymirror.top}
§7QQ: {link:§f985402607|https://skymirror.top/qq}
```

### MOTD placeholders

| Token | Meaning |
|-------|---------|
| `{player}` | Joining player |
| `{days}` / `{day}` | Days since `motd_start_day` |
| `{online}` | Online count or `?` |
| `{link:text\|https://url}` | Clickable link |
| `{link:https://url}` | Clickable URL |
| `§` | Vanilla color/style codes |

## Security

- Calculator: AST whitelist, no arbitrary Python
- Player names sanitized to `[A-Za-z0-9_]` before game commands
- Newlines stripped from console commands
- MOTD links limited to `http(s)` only

## Copyright

Copyright (c) 2026 云镜之端/SKYMirror. All Rights Reserved. See `LICENSE`.
