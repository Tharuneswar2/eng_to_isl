#!/usr/bin/env python3
"""
Build a searchable SQLite index from the bridgeconn/sign-dictionary-isl dataset.

Scans all TAR shards, extracts JSON metadata, and creates a SQLite database
at data/index/sign_dictionary.db with normalized word lookups.

This script only needs to be run ONCE (or when the dataset changes).
"""

import tarfile
import json
import sqlite3
import re
import sys
from pathlib import Path

DATA_DIR = Path("data/sign_dictionary")
INDEX_DIR = Path("data/index")
DB_PATH = INDEX_DIR / "sign_dictionary.db"


def normalize_word(text: str) -> str:
    """Normalize a transcript text for lookup.

    Examples:
        'Water (1)'  -> 'water'
        'I & me'     -> 'i'  (first part)
        'house & home' -> 'house'
    """
    text = text.lower().strip()
    # Remove parenthetical suffixes like '(1)', '(2)', '(his brother peter)'
    text = re.sub(r"\s*\(.*?\)\s*$", "", text)
    # If ampersand, take the first part
    if " & " in text:
        text = text.split(" & ")[0].strip()
    return text.strip()


def extract_variants(text: str) -> list[str]:
    """Extract all searchable word variants from a transcript text.

    Examples:
        'Water (1)'     -> ['water', 'water (1)']
        'I & me'        -> ['i', 'me', 'i & me']
        'house & home'  -> ['house', 'home', 'house & home']
        'good (1)'      -> ['good', 'good (1)']
        'need (2)'      -> ['need', 'need (2)']
    """
    original_lower = text.lower().strip()
    variants = set()
    variants.add(original_lower)

    # Strip parenthetical suffix
    base = re.sub(r"\s*\(.*?\)\s*$", "", original_lower).strip()
    if base:
        variants.add(base)

    # Split ampersand synonyms
    if " & " in original_lower:
        parts = original_lower.split(" & ")
        for part in parts:
            part = part.strip()
            # Also strip parens from individual parts
            part_clean = re.sub(r"\s*\(.*?\)\s*$", "", part).strip()
            if part_clean:
                variants.add(part_clean)
            if part:
                variants.add(part)

    return list(variants)


def create_database(db_path: Path) -> sqlite3.Connection:
    """Create the SQLite database and tables."""
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Remove existing DB to rebuild cleanly
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    conn.executescript("""
        CREATE TABLE signs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL,
            word_normalized TEXT NOT NULL,
            shard TEXT NOT NULL,
            sample_id TEXT NOT NULL,
            duration_sec REAL,
            fps REAL,
            width INTEGER,
            height INTEGER,
            license TEXT,
            source TEXT
        );

        CREATE TABLE word_variants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            variant TEXT NOT NULL,
            sign_id INTEGER NOT NULL,
            FOREIGN KEY (sign_id) REFERENCES signs(id)
        );

        CREATE INDEX idx_signs_word ON signs(word);
        CREATE INDEX idx_signs_word_normalized ON signs(word_normalized);
        CREATE INDEX idx_variants_variant ON word_variants(variant);
    """)

    return conn


def build_index():
    """Main index building function."""
    shards = sorted(DATA_DIR.glob("shard_*-train.tar"))
    if not shards:
        print(f"ERROR: No shard files found in {DATA_DIR}")
        sys.exit(1)

    print("=" * 60)
    print("  Building ISL Sign Dictionary Index")
    print("=" * 60)
    print(f"\n  Database: {DB_PATH}")
    print(f"  Shards:   {len(shards)}")
    print()

    conn = create_database(DB_PATH)
    total_signs = 0
    total_variants = 0

    for shard in shards:
        shard_name = shard.name
        shard_count = 0
        print(f"  Processing {shard_name}...", end=" ", flush=True)

        with tarfile.open(shard, "r") as tar:
            for member in tar.getmembers():
                if not member.name.endswith(".json"):
                    continue

                try:
                    file_obj = tar.extractfile(member)
                    if file_obj is None:
                        continue
                    data = json.load(file_obj)
                except (json.JSONDecodeError, Exception) as e:
                    print(f"\n    WARNING: Could not read {member.name}: {e}")
                    continue

                sample_id = member.name.replace(".json", "")
                transcript = data.get("transcript", {}).get("text", "")
                if not transcript:
                    continue

                word_normalized = normalize_word(transcript)
                duration = data.get("duration_sec", 0)
                fps = data.get("fps", 0)
                width = data.get("width", 0)
                height = data.get("height", 0)
                license_text = data.get("license", "")
                source = data.get("source", "")

                cursor = conn.execute(
                    """INSERT INTO signs
                       (word, word_normalized, shard, sample_id,
                        duration_sec, fps, width, height, license, source)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (transcript, word_normalized, shard_name, sample_id,
                     duration, fps, width, height, license_text, source),
                )
                sign_id = cursor.lastrowid

                # Insert word variants
                variants = extract_variants(transcript)
                for variant in variants:
                    conn.execute(
                        "INSERT INTO word_variants (variant, sign_id) "
                        "VALUES (?, ?)",
                        (variant, sign_id),
                    )
                    total_variants += 1

                shard_count += 1
                total_signs += 1

        conn.commit()
        print(f"{shard_count} signs")

    # Print summary
    print()
    print("=" * 60)
    print(f"  Total signs indexed:    {total_signs}")
    print(f"  Total word variants:    {total_variants}")
    print(f"  Database size:          {DB_PATH.stat().st_size / 1024:.1f} KB")
    print("=" * 60)

    # Quick verification
    print("\n  Verification — sample lookups:")
    test_words = ["water", "need", "help", "i", "want", "food", "hello", "go"]
    for word in test_words:
        row = conn.execute(
            """SELECT s.word, s.shard, s.sample_id
               FROM word_variants wv
               JOIN signs s ON wv.sign_id = s.id
               WHERE wv.variant = ?
               LIMIT 1""",
            (word,),
        ).fetchone()
        if row:
            print(f"    {word:15s} ✓  '{row[0]}' ({row[1]}, id={row[2]})")
        else:
            print(f"    {word:15s} ✗  NOT FOUND")

    conn.close()
    print(f"\n  Index saved to: {DB_PATH}")
    print("  Done!")


if __name__ == "__main__":
    build_index()
