"""
Central configuration for the English → ISL Translator.

All paths, video settings, and logging configuration are defined here.
"""

import logging
from pathlib import Path

# ─── Project paths ────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

DATA_DIR = PROJECT_ROOT / "data"
SIGN_DICTIONARY_DIR = DATA_DIR / "sign_dictionary"
INDEX_DIR = DATA_DIR / "index"
DB_PATH = INDEX_DIR / "sign_dictionary.db"

ISL_RULES_PATH = DATA_DIR / "isl_rules.json"

CACHE_DIR = PROJECT_ROOT / "cache" / "signs"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

# ─── Video normalization settings ─────────────────────────────────────────────
VIDEO_WIDTH = 640
VIDEO_HEIGHT = 480
VIDEO_FPS = 30
VIDEO_CODEC = "libx264"
VIDEO_PIXEL_FORMAT = "yuv420p"

# ─── Logging ──────────────────────────────────────────────────────────────────

def setup_logging(level: int = logging.INFO) -> None:
    """Configure logging for the translator."""
    logging.basicConfig(
        level=level,
        format="[%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()],
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger for the given module name."""
    return logging.getLogger(name)
