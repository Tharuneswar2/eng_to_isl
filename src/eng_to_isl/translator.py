"""
ISL Translator — Main orchestrator.

Coordinates the full pipeline:
    English text → preprocess → gloss → lookup → extract → combine → output

Usage:
    from eng_to_isl.translator import ISLTranslator
    translator = ISLTranslator()
    result = translator.translate("I need water")
"""

from dataclasses import dataclass, field
from pathlib import Path

from . import config
from .preprocessing import preprocess
from .gloss_converter import RuleBasedGlossConverter, GlossConverter
from .dictionary import ISLDictionary, SignEntry
from .video_extractor import VideoExtractor
from .video_builder import build_video

logger = config.get_logger(__name__)


@dataclass
class TranslationResult:
    """Result of an ISL translation."""
    input_text: str
    tokens: list[str]
    gloss: list[str]
    found: dict[str, SignEntry] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
    video_paths: dict[str, Path] = field(default_factory=dict)
    output_video: Path | None = None
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Whether at least one sign was found and a video was produced."""
        return self.output_video is not None and self.output_video.exists()

    @property
    def all_found(self) -> bool:
        """Whether all gloss tokens have corresponding signs."""
        return len(self.missing) == 0

    def summary(self) -> str:
        """Generate a human-readable summary."""
        lines = []
        lines.append("=" * 50)
        lines.append("  English → Indian Sign Language")
        lines.append("=" * 50)
        lines.append("")
        lines.append(f"  Input:")
        lines.append(f"  {self.input_text}")
        lines.append("")
        lines.append(f"  ISL Gloss:")
        lines.append(f"  {' '.join(self.gloss)}")
        lines.append("")
        lines.append(f"  Sign lookup:")

        for g in self.gloss:
            g_lower = g.lower()
            if g_lower in self.found:
                sign = self.found[g_lower]
                lines.append(f"    {g:15s} ✓  ({sign.word})")
            else:
                lines.append(f"    {g:15s} ✗")

        if self.missing:
            lines.append("")
            lines.append(f"  Missing signs:")
            for m in self.missing:
                lines.append(f"    {m}")

        if self.errors:
            lines.append("")
            lines.append(f"  Errors:")
            for e in self.errors:
                lines.append(f"    {e}")

        if self.output_video:
            lines.append("")
            if self.success:
                lines.append(f"  ✓ Translation completed")
            lines.append(f"  Output: {self.output_video}")
        elif not self.found:
            lines.append("")
            lines.append(f"  ✗ No signs found — cannot produce video")

        lines.append("")
        lines.append("=" * 50)
        return "\n".join(lines)


class ISLTranslator:
    """English → ISL video translator.

    Orchestrates the full translation pipeline.
    """

    def __init__(
        self,
        gloss_converter: GlossConverter | None = None,
        dictionary: ISLDictionary | None = None,
        video_extractor: VideoExtractor | None = None,
    ):
        """Initialize the translator with optional custom components.

        Args:
            gloss_converter: Custom gloss converter (default: RuleBased).
            dictionary: Custom dictionary (default: SQLite-backed).
            video_extractor: Custom video extractor (default: TAR-based).
        """
        self.gloss_converter = gloss_converter or RuleBasedGlossConverter()
        self.dictionary = dictionary or ISLDictionary()
        self.video_extractor = video_extractor or VideoExtractor()

    def translate(
        self,
        text: str,
        output_path: Path | None = None,
    ) -> TranslationResult:
        """Translate English text to an ISL video.

        Args:
            text: English input text.
            output_path: Optional custom output video path.

        Returns:
            TranslationResult with all translation details.
        """
        result = TranslationResult(input_text=text, tokens=[], gloss=[])

        # Validate input
        if not text or not text.strip():
            result.errors.append("Empty input text")
            logger.error("Empty input text")
            return result

        logger.info(f"Input: {text}")

        # Step 1: Preprocess
        tokens = preprocess(text)
        result.tokens = tokens
        logger.info(f"Tokens: {tokens}")

        if not tokens:
            result.errors.append("No tokens after preprocessing")
            return result

        # Step 2: Convert to ISL gloss
        gloss = self.gloss_converter.convert(tokens)
        result.gloss = gloss
        logger.info(f"Gloss: {' '.join(gloss)}")

        if not gloss:
            result.errors.append("No gloss produced")
            return result

        # Step 3: Look up signs
        found_signs = {}
        missing = []
        for g in gloss:
            g_lower = g.lower()
            sign = self.dictionary.find_sign(g_lower)
            if sign is not None:
                found_signs[g_lower] = sign
            else:
                missing.append(g)

        result.found = found_signs
        result.missing = missing

        if not found_signs:
            result.errors.append(
                "No signs found in dictionary for any gloss token"
            )
            logger.warning("No signs found — cannot produce video")
            return result

        # Step 4: Extract videos (in gloss order, skip missing)
        logger.info("Extracting videos")
        video_paths_ordered = []
        for g in gloss:
            g_lower = g.lower()
            if g_lower not in found_signs:
                continue
            sign = found_signs[g_lower]
            video_path = self.video_extractor.extract_sign_video(sign)
            if video_path:
                result.video_paths[g_lower] = video_path
                video_paths_ordered.append(video_path)
            else:
                result.errors.append(
                    f"Failed to extract video for '{g}'"
                )

        if not video_paths_ordered:
            result.errors.append("No videos could be extracted")
            logger.error("No videos extracted — cannot produce output")
            return result

        # Step 5: Combine videos
        logger.info("Combining videos")
        if output_path is None:
            # Use a sanitized filename based on input
            safe_name = (
                text.lower()
                .replace(" ", "_")[:30]
                .strip("_")
            )
            safe_name = "".join(
                c for c in safe_name if c.isalnum() or c == "_"
            )
            output_path = config.OUTPUT_DIR / f"{safe_name}_isl.mp4"

        combined = build_video(video_paths_ordered, output_path)
        if combined:
            result.output_video = combined
            logger.info(f"Output: {combined}")
        else:
            result.errors.append("Failed to combine videos")
            logger.error("Video combination failed")

        return result

    def close(self) -> None:
        """Clean up resources."""
        self.dictionary.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
