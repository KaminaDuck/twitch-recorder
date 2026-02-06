"""Utilities for checking whether a Twitch channel is live."""

from __future__ import annotations

import logging
import time

import streamlink

log = logging.getLogger(__name__)

TWITCH_URL = "https://twitch.tv/{channel}"


def is_live(channel: str, quality: str = "best") -> bool:
    """Return True if *channel* is currently streaming."""
    url = TWITCH_URL.format(channel=channel)
    try:
        session = streamlink.Streamlink()
        streams = session.streams(url)
        return quality in streams or "best" in streams
    except streamlink.NoPluginError:
        log.warning("Streamlink does not recognise URL: %s", url)
        return False
    except streamlink.PluginError as exc:
        log.debug("Plugin error checking stream status: %s", exc)
        return False
    except Exception as exc:
        log.debug("Unexpected error checking stream status: %s", exc)
        return False


def wait_until_live(
    channel: str,
    quality: str = "best",
    timeout: int = 7200,
    interval: int = 30,
) -> bool:
    """Block until the channel goes live or *timeout* seconds elapse.

    Returns True if the stream came online, False if we timed out.
    """
    log.info(
        "Waiting for %s to go live (timeout: %ss, checking every %ss)...",
        channel,
        timeout,
        interval,
    )
    waited = 0
    while waited < timeout:
        if is_live(channel, quality):
            log.info("Stream is LIVE!")
            return True
        time.sleep(interval)
        waited += interval
        log.debug("Still offline... (%s/%ss)", waited, timeout)

    log.warning("Stream did not go live within %ss.", timeout)
    return False


def wait_for_reconnect(
    channel: str,
    quality: str = "best",
    grace_period: int = 300,
    check_interval: int = 15,
) -> bool:
    """After a disconnect, wait up to *grace_period* seconds to see if the
    stream comes back.

    Returns True if the stream returned, False if the grace period expired.
    """
    log.info(
        "Stream dropped. Waiting up to %ss for it to return...", grace_period
    )
    waited = 0
    while waited < grace_period:
        time.sleep(check_interval)
        waited += check_interval
        if is_live(channel, quality):
            log.info("Stream is back online!")
            return True
        log.debug("Still offline... (%s/%ss)", waited, grace_period)

    log.info("Stream did not return within %ss.", grace_period)
    return False
