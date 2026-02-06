"""Configuration management for the Twitch recorder."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Config:
    """All configuration for a recording session."""

    # --- Required ---
    channel: str = "channelname"
    output_dir: str = "/path/to/jellyfin/library/TwitchRecordings"

    # --- Stream options ---
    quality: str = "best"
    stream_timeout: int = 120  # seconds before considering the stream dead

    # --- Scheduling / initial wait ---
    initial_wait: int = 7200  # max seconds to wait for the stream to start
    retry_interval: int = 30  # seconds between "is it live?" checks

    # --- Reconnection ---
    reconnect_grace_period: int = 300  # seconds to wait after a drop
    reconnect_check_interval: int = 15  # seconds between checks during grace
    max_reconnects: int = 10

    # --- Post-processing ---
    merge_segments: bool = True
    cleanup_segments: bool = True
    ffmpeg_path: str = "ffmpeg"

    # --- Streamlink extras ---
    streamlink_args: list[str] = field(default_factory=lambda: [
        "--twitch-disable-ads",
        "--twitch-disable-hosting",
    ])

    @classmethod
    def from_yaml(cls, path: str | Path) -> Config:
        """Load configuration from a YAML file, falling back to defaults for
        any keys not specified."""
        raw = yaml.safe_load(Path(path).read_text()) or {}
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in raw.items() if k in known_fields}
        return cls(**filtered)

    def validate(self) -> None:
        """Raise on obviously bad config."""
        if not self.channel or self.channel == "channelname":
            raise ValueError("Please set a valid 'channel' in your config.")
        out = Path(self.output_dir)
        if not out.exists():
            out.mkdir(parents=True, exist_ok=True)
