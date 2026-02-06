"""Command-line interface for the Twitch recorder."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .config import Config
from .recorder import RecordingSession
from .stream import wait_until_live
from .postprocess import postprocess

log = logging.getLogger("twitch_recorder")


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger("twitch_recorder")
    root.setLevel(level)
    root.addHandler(handler)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="twitch-recorder",
        description="Record Twitch streams with automatic reconnection. "
        "Designed for unattended use with Jellyfin.",
    )
    p.add_argument(
        "channel",
        nargs="?",
        help="Twitch channel name (overrides config file)",
    )
    p.add_argument(
        "-c", "--config",
        type=Path,
        default=None,
        help="Path to a YAML config file",
    )
    p.add_argument(
        "-o", "--output-dir",
        type=str,
        default=None,
        help="Output directory (overrides config file)",
    )
    p.add_argument(
        "-q", "--quality",
        type=str,
        default=None,
        help="Stream quality: best, 1080p60, 720p, etc. (default: best)",
    )
    p.add_argument(
        "--no-merge",
        action="store_true",
        help="Skip merging segments into a single file",
    )
    p.add_argument(
        "--keep-segments",
        action="store_true",
        help="Keep individual segment files after merging",
    )
    p.add_argument(
        "--no-wait",
        action="store_true",
        help="Don't wait for the stream to start — exit immediately if offline",
    )
    p.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    setup_logging(verbose=args.verbose)

    # --- Build config --------------------------------------------------------
    if args.config and args.config.exists():
        log.info("Loading config from %s", args.config)
        config = Config.from_yaml(args.config)
    else:
        config = Config()

    # CLI overrides
    if args.channel:
        config.channel = args.channel
    if args.output_dir:
        config.output_dir = args.output_dir
    if args.quality:
        config.quality = args.quality
    if args.no_merge:
        config.merge_segments = False
    if args.keep_segments:
        config.cleanup_segments = False

    try:
        config.validate()
    except ValueError as exc:
        log.error("Config error: %s", exc)
        return 1

    log.info("=" * 50)
    log.info("Twitch Stream Recorder")
    log.info("  Channel:  %s", config.channel)
    log.info("  Quality:  %s", config.quality)
    log.info("  Output:   %s", config.output_dir)
    log.info("=" * 50)

    # --- Wait for stream to go live ------------------------------------------
    if args.no_wait:
        from .stream import is_live
        if not is_live(config.channel, config.quality):
            log.info("Channel is offline and --no-wait is set. Exiting.")
            return 0
    else:
        live = wait_until_live(
            channel=config.channel,
            quality=config.quality,
            timeout=config.initial_wait,
            interval=config.retry_interval,
        )
        if not live:
            return 0

    # --- Record --------------------------------------------------------------
    session = RecordingSession(config=config)
    session.run()

    # --- Post-process --------------------------------------------------------
    result = postprocess(
        segments=session.segments,
        final_path=session.final_filename,
        merge=config.merge_segments,
        clean=config.cleanup_segments,
        ffmpeg=config.ffmpeg_path,
    )

    if result:
        log.info("Recording saved: %s", result)
    elif session.segments:
        log.warning("Post-processing failed. Segments are still available.")
    else:
        log.info("No recording produced.")

    log.info("=" * 50)
    log.info("Done!")
    log.info("=" * 50)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
