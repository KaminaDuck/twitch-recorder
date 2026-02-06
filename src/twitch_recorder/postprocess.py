"""Post-processing — merge segments with ffmpeg and clean up temp files."""

from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path

log = logging.getLogger(__name__)


def remux_single(src: Path, dest: Path, ffmpeg: str = "ffmpeg") -> bool:
    """Remux a single .ts file into an .mp4 container."""
    log.info("Remuxing %s → %s", src.name, dest.name)
    return _run_ffmpeg(
        [ffmpeg, "-i", str(src), "-c", "copy", "-movflags", "+faststart", str(dest), "-y"],
        ffmpeg,
    )


def merge_segments(segments: list[Path], dest: Path, ffmpeg: str = "ffmpeg") -> bool:
    """Concatenate multiple .ts segments into a single .mp4."""
    log.info("Merging %d segments → %s", len(segments), dest.name)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for seg in segments:
            f.write(f"file '{seg}'\n")
        concat_list = Path(f.name)

    try:
        success = _run_ffmpeg(
            [
                ffmpeg,
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_list),
                "-c", "copy",
                "-movflags", "+faststart",
                str(dest),
                "-y",
            ],
            ffmpeg,
        )
    finally:
        concat_list.unlink(missing_ok=True)

    return success


def cleanup(files: list[Path]) -> None:
    """Delete a list of files."""
    for f in files:
        f.unlink(missing_ok=True)
        log.debug("Deleted %s", f.name)
    log.info("Cleaned up %d file(s).", len(files))


def postprocess(
    segments: list[Path],
    final_path: Path,
    *,
    merge: bool = True,
    clean: bool = True,
    ffmpeg: str = "ffmpeg",
) -> Path | None:
    """Run the full post-processing pipeline and return the final file path,
    or None if nothing was produced."""
    if not segments:
        log.info("No segments to process.")
        return None

    if len(segments) == 1:
        success = remux_single(segments[0], final_path, ffmpeg)
    elif merge:
        success = merge_segments(segments, final_path, ffmpeg)
    else:
        log.info(
            "%d segments saved. Merge disabled — skipping.",
            len(segments),
        )
        return segments[0]

    if success and final_path.exists() and final_path.stat().st_size > 0:
        size_mb = final_path.stat().st_size / (1024 * 1024)
        log.info("Final recording: %s (%.1f MB)", final_path.name, size_mb)
        if clean:
            cleanup(segments)
        return final_path

    log.error("Post-processing failed. Keeping original segment files.")
    return None


# --- Internals ---------------------------------------------------------------

def _run_ffmpeg(cmd: list[str], ffmpeg: str) -> bool:
    """Run an ffmpeg command, logging output. Returns True on success."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=3600
        )
        if result.returncode != 0:
            log.error("ffmpeg failed (exit %d): %s", result.returncode, result.stderr)
            return False
        return True
    except FileNotFoundError:
        log.error("%s not found. Is ffmpeg installed and on your PATH?", ffmpeg)
        return False
    except subprocess.TimeoutExpired:
        log.error("ffmpeg timed out after 1 hour.")
        return False
