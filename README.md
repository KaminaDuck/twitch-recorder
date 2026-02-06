# Twitch Stream Recorder

Automatically record Twitch live streams with reconnection handling, segment
merging, and Jellyfin-friendly output. Designed for unattended, scheduled
recording.

## Features

- **Wait for stream** — starts before the broadcast and polls until it goes live
- **Automatic reconnection** — detects mid-stream drops and resumes recording
- **Segment merging** — combines all parts into a single `.mp4` via ffmpeg
- **Clean filenames** — outputs `ChannelName - 2026-02-05.mp4` for Jellyfin
- **Configurable** — YAML config file or CLI flags, your choice

## Requirements

- Python 3.10+
- [streamlink](https://streamlink.github.io/)
- [ffmpeg](https://ffmpeg.org/) (optional, for remuxing/merging)

## Installation

```bash
# Clone or copy the project, then install
cd twitch-recorder
pip install .

# Or install in editable/development mode
pip install -e .
```

This gives you the `twitch-recorder` command.

## Quick Start

```bash
# Record a channel right now (waits for it to go live)
twitch-recorder somechannel -o /media/jellyfin/twitch

# Use a config file
cp config.example.yaml config.yaml
# Edit config.yaml with your settings
twitch-recorder -c config.yaml

# Skip waiting — exit immediately if offline
twitch-recorder somechannel --no-wait
```

## Configuration

You can configure the recorder via:

1. **YAML config file** (`-c config.yaml`) — see `config.example.yaml`
2. **CLI flags** — override any config file setting
3. **Defaults** — sensible values built in

CLI flags always take priority over the config file.

### Key Options

| Option              | Default | Description                                  |
|---------------------|---------|----------------------------------------------|
| `channel`           | —       | Twitch username to record                    |
| `output_dir`        | —       | Where to save recordings                     |
| `quality`           | `best`  | Stream quality (best, 1080p60, 720p, etc.)   |
| `initial_wait`      | 7200    | Max seconds to wait for stream to start      |
| `reconnect_grace_period` | 300 | Seconds to wait after a mid-stream drop     |
| `max_reconnects`    | 10      | Max reconnection attempts per session        |
| `merge_segments`    | true    | Merge all parts into one .mp4                |

## Scheduling with Cron

Set up a cron job that fires shortly before the stream's usual start time:

```bash
crontab -e
```

```cron
# Every Saturday at 10:55 PM
55 22 * * 6 /path/to/venv/bin/twitch-recorder -c /path/to/config.yaml >> /var/log/twitch-recorder.log 2>&1
```

## Scheduling with systemd

For a more robust setup, create a systemd service and timer:

**`/etc/systemd/system/twitch-recorder.service`**:
```ini
[Unit]
Description=Twitch Stream Recorder
After=network-online.target

[Service]
Type=oneshot
User=youruser
ExecStart=/path/to/venv/bin/twitch-recorder -c /path/to/config.yaml
StandardOutput=journal
StandardError=journal
TimeoutStopSec=30
```

**`/etc/systemd/system/twitch-recorder.timer`**:
```ini
[Unit]
Description=Run Twitch recorder every Saturday night

[Timer]
OnCalendar=Sat 22:55
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now twitch-recorder.timer
```

## Jellyfin Integration

Point a **Home Videos** or **Movies** library at your `output_dir`. The
recorder produces files named `ChannelName - 2026-02-05.mp4` which Jellyfin
will pick up on its next library scan.

## Project Structure

```
twitch-recorder/
├── pyproject.toml                # Package metadata & dependencies
├── config.example.yaml           # Example configuration
├── README.md
└── src/
    └── twitch_recorder/
        ├── __init__.py
        ├── cli.py                # Entry point & argument parsing
        ├── config.py             # YAML config loader & dataclass
        ├── recorder.py           # Core recording loop & session state
        ├── stream.py             # Live-check & wait utilities
        └── postprocess.py        # ffmpeg merge & cleanup
```

## License

MIT
