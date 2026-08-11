"""
ISL Sign Dictionary lookup module.

Searches the SQLite index for ISL sign entries matching English words.
Supports multiple lookup strategies:
  1. Exact match
  2. Lowercase match
  3. Normalized match (strip parenthetical numbers)
  4. Lemma match
  5. Variant match (ampersand synonyms)
"""

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from . import config

logger = config.get_logger(__name__)


@dataclass
class SignEntry:
    """Represents a single ISL sign from the dictionary."""
    id: int
    word: str
    word_normalized: str
    shard: str
    sample_id: str
    duration_sec: float
    fps: float
    width: int
    height: int

    def __str__(self) -> str:
        return (
            f"SignEntry('{self.word}', shard={self.shard}, "
            f"sample={self.sample_id})"
        )


class ISLDictionary:
    """ISL Sign Dictionary backed by SQLite.

    Provides fast word → sign lookups with multiple fallback strategies.
    """

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or config.DB_PATH
        self._conn: sqlite3.Connection | None = None
        self._connect()

    def _connect(self) -> None:
        """Connect to the SQLite database."""
        if not self.db_path.exists():
            raise FileNotFoundError(
                f"ISL dictionary index not found: {self.db_path}\n"
                f"Run 'python scripts/build_index.py' first."
            )
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        logger.info(f"Loading ISL dictionary index")

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._connect()
        return self._conn

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def _row_to_entry(self, row: sqlite3.Row) -> SignEntry:
        """Convert a database row to a SignEntry."""
        return SignEntry(
            id=row["id"],
            word=row["word"],
            word_normalized=row["word_normalized"],
            shard=row["shard"],
            sample_id=row["sample_id"],
            duration_sec=row["duration_sec"],
            fps=row["fps"],
            width=row["width"],
            height=row["height"],
        )

    def find_sign(self, word: str) -> SignEntry | None:
        """Find an ISL sign for the given English word.

        Tries multiple lookup strategies in order:
        1. Exact variant match
        2. Normalized word match
        3. Basic lemma forms

        Args:
            word: English word to look up (case-insensitive).

        Returns:
            SignEntry if found, None if SIGN_NOT_FOUND.
        """
        word_lower = word.lower().strip()
        logger.info(f"Searching sign: {word_lower}")

        # Strategy 1: Variant table lookup (handles exact, lowercase,
        # stripped parens, and ampersand synonyms)
        row = self.conn.execute(
            """SELECT s.* FROM word_variants wv
               JOIN signs s ON wv.sign_id = s.id
               WHERE wv.variant = ?
               ORDER BY s.duration_sec ASC
               LIMIT 1""",
            (word_lower,),
        ).fetchone()

        if row:
            entry = self._row_to_entry(row)
            logger.info(f"Found sign: {word_lower} → '{entry.word}'")
            return entry

        # Strategy 2: Normalized word column
        row = self.conn.execute(
            """SELECT * FROM signs
               WHERE word_normalized = ?
               ORDER BY duration_sec ASC
               LIMIT 1""",
            (word_lower,),
        ).fetchone()

        if row:
            entry = self._row_to_entry(row)
            logger.info(
                f"Found sign (normalized): {word_lower} → '{entry.word}'"
            )
            return entry

        # Strategy 3: Partial/LIKE match
        row = self.conn.execute(
            """SELECT s.* FROM word_variants wv
               JOIN signs s ON wv.sign_id = s.id
               WHERE wv.variant LIKE ?
               ORDER BY LENGTH(wv.variant) ASC, s.duration_sec ASC
               LIMIT 1""",
            (f"{word_lower}%",),
        ).fetchone()

        if row:
            entry = self._row_to_entry(row)
            logger.info(
                f"Found sign (partial): {word_lower} → '{entry.word}'"
            )
            return entry

        logger.warning(f"SIGN_NOT_FOUND: {word_lower}")
        return None

    def find_signs(self, words: list[str]) -> dict[str, SignEntry | None]:
        """Look up ISL signs for multiple words.

        Args:
            words: List of English words to look up.

        Returns:
            Dictionary mapping each word to its SignEntry or None.
        """
        results = {}
        for word in words:
            results[word] = self.find_sign(word)
        return results

    def get_all_words(self) -> list[str]:
        """Get all unique normalized words in the dictionary."""
        rows = self.conn.execute(
            "SELECT DISTINCT variant FROM word_variants ORDER BY variant"
        ).fetchall()
        return [row["variant"] for row in rows]

    def count(self) -> int:
        """Get the total number of sign entries."""
        row = self.conn.execute("SELECT COUNT(*) as cnt FROM signs").fetchone()
        return row["cnt"]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
