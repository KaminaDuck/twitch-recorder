"""Core recording logic — drives Streamlink and manages segments."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .config import Config
from .stream import wait_for_reconnect, TWITCH_URL

log = logging.getLogger(__name__)


@dataclass
class RecordingSession:
    """Tracks state across a single recording session (one stream broadcast)."""

    config: Config
    session_date: str = field(init=False)
    segments: list[Path] = field(default_factory=list)
    reconnect_count: int = 0

    def __post_init__(self) -> None:
        self.session_date = datetime.now().strftime("%Y-%m-%d")

    @property
    def session_id(self) -> str:
        return f"{self.config.channel}_{self.session_date}"

    @property
    def output_dir(self) -> Path:
        return Path(self.config.output_dir)

    @property
    def final_filename(self) -> Path:
        return self.output_dir / f"{self.config.channel} - {self.session_date}.mp4"

    def next_segment_path(self) -> Path:
        num = len(self.segments) + 1
        return self.output_dir / f"{self.session_id}_part{num:02d}.ts"

    # --- Recording -----------------------------------------------------------

    def record_segment(self) -> Path | None:
        """Record a single segment. Returns the path if successful, else None."""
        segment_path = self.next_segment_path()
        url = TWITCH_URL.format(channel=self.config.channel)

        cmd = [
            "streamlink",
            url,
            self.config.quality,
            "--output", str(segment_path),
            "--stream-timeout", str(self.config.stream_timeout),
            "--hls-live-restart",
            *self.config.streamlink_args,
        ]

        log.info("Recording segment %d → %s", len(self.segments) + 1, segment_path.name)
        log.debug("Command: %s", " ".join(cmd))

        try:
            process = subprocess.run(cmd, capture_output=True, text=True)

            if process.stdout:
                for line in process.stdout.strip().splitlines():
                    log.debug("[streamlink] %s", line)
            if process.stderr:
                for line in process.stderr.strip().splitlines():
                    log.debug("[streamlink] %s", line)

        except FileNotFoundError:
            log.error("streamlink not found. Is it installed and on your PATH?")
            return None
        except Exception as exc:
            log.error("Error running streamlink: %s", exc)
            return None

        # Validate the segment
        if not segment_path.exists() or segment_path.stat().st_size == 0:
            log.warning("Segment file is empty or missing — discarding.")
            segment_path.unlink(missing_ok=True)
            return None

        size_mb = segment_path.stat().st_size / (1024 * 1024)
        log.info("Segment saved: %s (%.1f MB)", segment_path.name, size_mb)
        self.segments.append(segment_path)
        return segment_path

    # --- Session loop --------------------------------------------------------

    def run(self) -> None:
        """Main recording loop: record, detect drops, reconnect, repeat."""
        while True:
            self.record_segment()

            if self.reconnect_count >= self.config.max_reconnects:
                log.warning(
                    "Max reconnections (%d) reached. Ending session.",
                    self.config.max_reconnects,
                )
                break

            came_back = wait_for_reconnect(
                channel=self.config.channel,
                quality=self.config.quality,
                grace_period=self.config.reconnect_grace_period,
                check_interval=self.config.reconnect_check_interval,
            )

            if came_back:
                self.reconnect_count += 1
                log.info(
                    "Reconnecting (attempt %d/%d)...",
                    self.reconnect_count,
                    self.config.max_reconnects,
                )
            else:
                log.info("Stream appears to have ended.")
                break

        log.info(
            "Session complete: %d segment(s), %d reconnection(s).",
            len(self.segments),
            self.reconnect_count,
        )
