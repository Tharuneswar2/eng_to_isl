"""
English → ISL Gloss Converter.

Converts a list of English tokens into an ISL-oriented gloss sequence.
Uses configurable rules loaded from data/isl_rules.json.

Architecture:
    GlossConverter (abstract base)
        └── RuleBasedGlossConverter  (current)
        └── TransformerGlossConverter (future ML replacement)
"""

import json
from abc import ABC, abstractmethod
from pathlib import Path

from . import config

logger = config.get_logger(__name__)


class GlossConverter(ABC):
    """Abstract base class for gloss conversion."""

    @abstractmethod
    def convert(self, tokens: list[str]) -> list[str]:
        """Convert English tokens to ISL gloss sequence.

        Args:
            tokens: Preprocessed English tokens (lowercase).

        Returns:
            List of ISL gloss tokens (uppercase).
        """
        ...


class RuleBasedGlossConverter(GlossConverter):
    """Rule-based English → ISL gloss converter.

    Applies:
    1. Stop word removal (configurable)
    2. SOV reordering (Subject-Object-Verb)
    3. Gloss uppercasing

    Rules are loaded from data/isl_rules.json so they can be modified
    without changing Python code.
    """

    def __init__(self, rules_path: Path | None = None):
        self.rules_path = rules_path or config.ISL_RULES_PATH
        self._load_rules()

    def _load_rules(self) -> None:
        """Load ISL grammar rules from JSON file."""
        if not self.rules_path.exists():
            logger.warning(
                f"ISL rules file not found: {self.rules_path}. "
                "Using minimal defaults."
            )
            self.stop_words = {"a", "an", "the", "is", "am", "are", "to"}
            self.preserve_words = set()
            self.verb_indicators = {"go", "come", "want", "need", "help"}
            return

        with open(self.rules_path) as f:
            rules = json.load(f)

        self.stop_words = set(rules.get("stop_words", []))
        self.preserve_words = set(rules.get("preserve_words", []))
        self.verb_indicators = set(rules.get("verb_indicators", []))

        logger.debug(
            f"Loaded ISL rules: {len(self.stop_words)} stop words, "
            f"{len(self.preserve_words)} preserve words, "
            f"{len(self.verb_indicators)} verb indicators"
        )

    def convert(self, tokens: list[str]) -> list[str]:
        """Convert English tokens to ISL gloss sequence.

        Example:
            ['i', 'need', 'water']  → ['I', 'WATER', 'NEED']
            ['i', 'want', 'food']   → ['I', 'FOOD', 'WANT']
            ['i', 'am', 'go', 'home'] → ['I', 'HOME', 'GO']
            ['good', 'morning']     → ['GOOD', 'MORNING']

        Args:
            tokens: Preprocessed English tokens (lowercase).

        Returns:
            ISL gloss sequence (uppercase).
        """
        if not tokens:
            return []

        logger.debug(f"Converting to gloss: {tokens}")

        # Step 1: Remove stop words, but preserve meaningful words
        filtered = []
        for token in tokens:
            if token in self.preserve_words:
                filtered.append(token)
            elif token not in self.stop_words:
                filtered.append(token)
            else:
                logger.debug(f"  Removed stop word: '{token}'")

        if not filtered:
            # If everything was filtered, return original tokens
            logger.warning("All tokens were stop words; keeping originals")
            filtered = list(tokens)

        # Step 2: SOV reordering
        # Identify verbs and move them to the end
        reordered = self._sov_reorder(filtered)

        # Step 3: Uppercase for ISL gloss convention
        gloss = [token.upper() for token in reordered]

        logger.debug(f"Gloss result: {gloss}")
        return gloss

    def _sov_reorder(self, tokens: list[str]) -> list[str]:
        """Apply Subject-Object-Verb reordering.

        Moves verb(s) to the end of the token list while preserving
        the relative order of non-verb tokens.

        Example:
            ['i', 'need', 'water'] → ['i', 'water', 'need']
            ['i', 'go', 'home']    → ['i', 'home', 'go']
            ['good', 'morning']    → ['good', 'morning'] (no verb)
        """
        if len(tokens) <= 1:
            return tokens

        verbs = []
        non_verbs = []

        for token in tokens:
            if token in self.verb_indicators:
                verbs.append(token)
            else:
                non_verbs.append(token)

        if not verbs:
            # No verbs identified, keep original order
            return tokens

        # SOV: non-verbs first, then verbs at end
        result = non_verbs + verbs
        if result != tokens:
            logger.debug(f"  SOV reorder: {tokens} → {result}")

        return result
