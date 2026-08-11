"""
ISL Video Builder.

Concatenates individual ISL sign videos into a single output video.
Uses FFmpeg for normalization and concatenation.

Normalizes:
- Resolution (640x480 default)
- Frame rate (30 fps default)
- Codec (H.264)
- Pixel format (yuv420p)
"""

import subprocess
import tempfile
from pathlib import Path

from . import config

logger = config.get_logger(__name__)


def _check_ffmpeg() -> bool:
    """Check if FFmpeg is available."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def _normalize_video(
    input_path: Path,
    output_path: Path,
    width: int = config.VIDEO_WIDTH,
    height: int = config.VIDEO_HEIGHT,
    fps: int = config.VIDEO_FPS,
) -> bool:
    """Normalize a single video to standard resolution/fps/codec.

    Args:
        input_path: Path to the input video.
        output_path: Path to write the normalized video.
        width: Target width.
        height: Target height.
        fps: Target frame rate.

    Returns:
        True if successful, False otherwise.
    """
    cmd = [
        "ffmpeg",
        "-y",  # Overwrite
        "-i", str(input_path),
        "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
               f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black",
        "-r", str(fps),
        "-c:v", config.VIDEO_CODEC,
        "-pix_fmt", config.VIDEO_PIXEL_FORMAT,
        "-an",  # Remove audio
        "-preset", "fast",
        "-crf", "23",
        str(output_path),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            logger.error(f"FFmpeg normalize failed: {result.stderr[:500]}")
            return False
        return True
    except subprocess.TimeoutExpired:
        logger.error(f"FFmpeg normalize timed out: {input_path}")
        return False
    except Exception as e:
        logger.error(f"FFmpeg normalize error: {e}")
        return False


def build_video(
    video_paths: list[Path],
    output_path: Path | None = None,
) -> Path | None:
    """Combine multiple sign videos into a single output video.

    Normalizes all videos to the same resolution/fps, then concatenates
    them using FFmpeg's concat demuxer.

    Args:
        video_paths: List of paths to individual sign videos.
        output_path: Path for the final combined video.
                     Defaults to outputs/final_isl.mp4.

    Returns:
        Path to the combined video, or None on failure.
    """
    if not video_paths:
        logger.error("No video paths provided")
        return None

    if not _check_ffmpeg():
        logger.error(
            "FFmpeg is not installed or not in PATH. "
            "Install FFmpeg to combine videos."
        )
        return None

    if output_path is None:
        output_path = config.OUTPUT_DIR / "final_isl.mp4"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Combining {len(video_paths)} videos...")

    # If only one video, just normalize and copy
    if len(video_paths) == 1:
        logger.info("Single video — normalizing directly")
        success = _normalize_video(video_paths[0], output_path)
        if success:
            logger.info(f"Output: {output_path}")
            return output_path
        return None

    # Create a temp directory for normalized videos
    with tempfile.TemporaryDirectory(
        dir=str(config.PROJECT_ROOT),
        prefix=".isl_build_",
    ) as tmp_dir:
        tmp_path = Path(tmp_dir)
        normalized_paths = []

        # Step 1: Normalize each video
        for i, vp in enumerate(video_paths):
            norm_path = tmp_path / f"part_{i:03d}.mp4"
            logger.info(f"  Normalizing: {vp.name}")
            if _normalize_video(vp, norm_path):
                normalized_paths.append(norm_path)
            else:
                logger.warning(f"  Skipping (normalize failed): {vp.name}")

        if not normalized_paths:
            logger.error("No videos were successfully normalized")
            return None

        # Step 2: Create concat file list
        concat_file = tmp_path / "concat.txt"
        with open(concat_file, "w") as f:
            for np in normalized_paths:
                f.write(f"file '{np}'\n")

        # Step 3: Concatenate
        concat_cmd = [
            "ffmpeg",
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c", "copy",
            str(output_path),
        ]

        try:
            result = subprocess.run(
                concat_cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                logger.error(
                    f"FFmpeg concat failed: {result.stderr[:500]}"
                )
                return None

            file_size = output_path.stat().st_size
            logger.info(
                f"Output: {output_path} ({file_size / 1024:.1f} KB)"
            )
            return output_path

        except subprocess.TimeoutExpired:
            logger.error("FFmpeg concat timed out")
            return None
        except Exception as e:
            logger.error(f"FFmpeg concat error: {e}")
            return None
