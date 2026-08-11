"""
ISL Sign Video Extractor.

Extracts individual .mp4 sign videos from TAR shards on demand.
Uses a local cache to avoid re-extraction.
Only extracts the specific video needed — never the full shard.
"""

import tarfile
from pathlib import Path

from . import config
from .dictionary import SignEntry

logger = config.get_logger(__name__)


class VideoExtractor:
    """Extracts sign videos from TAR shards with caching."""

    def __init__(
        self,
        data_dir: Path | None = None,
        cache_dir: Path | None = None,
    ):
        self.data_dir = data_dir or config.SIGN_DICTIONARY_DIR
        self.cache_dir = cache_dir or config.CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, sign: SignEntry) -> Path:
        """Get the cache file path for a sign entry."""
        # Use normalized word + sample_id to avoid collisions
        safe_name = (
            sign.word_normalized
            .replace(" ", "_")
            .replace("&", "and")
            .replace("/", "_")
        )
        return self.cache_dir / f"{safe_name}_{sign.sample_id}.mp4"

    def extract_sign_video(self, sign: SignEntry) -> Path | None:
        """Extract a sign video from its TAR shard.

        Args:
            sign: SignEntry with shard and sample_id information.

        Returns:
            Path to the extracted .mp4 file, or None on failure.
        """
        cache_path = self._get_cache_path(sign)

        # Check cache first
        if cache_path.exists() and cache_path.stat().st_size > 0:
            logger.info(
                f"Using cached video: {sign.word_normalized} → {cache_path.name}"
            )
            return cache_path

        # Locate the shard
        shard_path = self.data_dir / sign.shard
        if not shard_path.exists():
            logger.error(f"Shard file not found: {shard_path}")
            return None

        # Extract the specific .mp4 from the tar
        mp4_name = f"{sign.sample_id}.mp4"
        logger.info(
            f"Extracting video: {sign.word_normalized} "
            f"({mp4_name} from {sign.shard})"
        )

        try:
            with tarfile.open(shard_path, "r") as tar:
                try:
                    member = tar.getmember(mp4_name)
                except KeyError:
                    logger.error(
                        f"MP4 not found in shard: {mp4_name} "
                        f"in {sign.shard}"
                    )
                    return None

                file_obj = tar.extractfile(member)
                if file_obj is None:
                    logger.error(f"Could not read {mp4_name} from shard")
                    return None

                # Write to cache
                with open(cache_path, "wb") as out:
                    out.write(file_obj.read())

                logger.info(
                    f"Extracted: {cache_path.name} "
                    f"({cache_path.stat().st_size / 1024:.1f} KB)"
                )
                return cache_path

        except tarfile.TarError as e:
            logger.error(f"Error reading shard {sign.shard}: {e}")
            return None
        except OSError as e:
            logger.error(f"IO error extracting {mp4_name}: {e}")
            return None

    def extract_sign_videos(
        self, signs: list[SignEntry]
    ) -> list[tuple[SignEntry, Path | None]]:
        """Extract multiple sign videos.

        Args:
            signs: List of SignEntry objects to extract.

        Returns:
            List of (SignEntry, Path|None) tuples.
        """
        results = []
        for sign in signs:
            path = self.extract_sign_video(sign)
            results.append((sign, path))
        return results

    def clear_cache(self) -> int:
        """Remove all cached sign videos.

        Returns:
            Number of files removed.
        """
        count = 0
        for f in self.cache_dir.glob("*.mp4"):
            f.unlink()
            count += 1
        logger.info(f"Cleared {count} cached videos")
        return count
