#!/usr/bin/env python3
"""
Inspect the bridgeconn/sign-dictionary-isl dataset.

Reads the local TAR shards and prints:
- Sample structure (files per sample)
- JSON metadata schema
- Dataset statistics
- Word/transcript patterns
"""

import tarfile
import json
import sys
from pathlib import Path
from collections import Counter

DATA_DIR = Path("data/sign_dictionary")


def inspect_single_sample(tar_path: Path) -> dict:
    """Read the first JSON sample from a shard and return its structure."""
    with tarfile.open(tar_path, "r") as tar:
        members = tar.getmembers()
        json_member = next(
            (m for m in members if m.name.endswith(".json")), None
        )
        if json_member is None:
            return {}

        file_obj = tar.extractfile(json_member)
        data = json.load(file_obj)

        sample_id = json_member.name.rsplit(".", 1)[0]
        related_files = [
            m for m in members if m.name.startswith(f"{sample_id}.")
        ]

        return {
            "sample_id": sample_id,
            "json_data": data,
            "related_files": [
                {"name": m.name, "size": m.size} for m in related_files
            ],
        }


def scan_all_shards(data_dir: Path) -> list[dict]:
    """Scan all shards and collect transcript metadata."""
    shards = sorted(data_dir.glob("shard_*-train.tar"))
    all_entries = []

    for shard in shards:
        shard_name = shard.name
        print(f"  Scanning {shard_name}...", flush=True)
        with tarfile.open(shard, "r") as tar:
            for member in tar.getmembers():
                if not member.name.endswith(".json"):
                    continue
                file_obj = tar.extractfile(member)
                data = json.load(file_obj)
                sample_id = member.name.replace(".json", "")
                transcript = data.get("transcript", {}).get("text", "")
                fps = data.get("fps", 0)
                duration = data.get("duration_sec", 0)
                width = data.get("width", 0)
                height = data.get("height", 0)
                all_entries.append({
                    "word": transcript,
                    "sample_id": sample_id,
                    "shard": shard_name,
                    "fps": fps,
                    "duration": duration,
                    "width": width,
                    "height": height,
                })

    return all_entries


def main():
    print("=" * 70)
    print("  bridgeconn/sign-dictionary-isl — Dataset Inspector")
    print("=" * 70)

    shards = sorted(DATA_DIR.glob("shard_*-train.tar"))
    if not shards:
        print(f"\nERROR: No shard files found in {DATA_DIR}")
        sys.exit(1)

    print(f"\nFound {len(shards)} shard files:")
    total_size = 0
    for s in shards:
        size_mb = s.stat().st_size / (1024 * 1024)
        total_size += size_mb
        print(f"  {s.name:40s} {size_mb:>8.1f} MB")
    print(f"  {'TOTAL':40s} {total_size:>8.1f} MB")

    # --- Single sample inspection ---
    print("\n" + "=" * 70)
    print("  Sample Structure (first sample from shard_00001)")
    print("=" * 70)

    sample = inspect_single_sample(shards[0])
    if sample:
        print(f"\nSample ID: {sample['sample_id']}")
        print(f"\nRelated files:")
        for f in sample["related_files"]:
            ext = f["name"].split(".", 1)[1] if "." in f["name"] else "?"
            print(f"  .{ext:30s} {f['size']:>10,} bytes")

        print(f"\nJSON metadata:")
        print(json.dumps(sample["json_data"], indent=2))

    # --- Full scan ---
    print("\n" + "=" * 70)
    print("  Scanning all shards for statistics...")
    print("=" * 70)

    entries = scan_all_shards(DATA_DIR)
    print(f"\n  Total sign entries: {len(entries)}")

    # FPS distribution
    fps_counter = Counter(e["fps"] for e in entries)
    print(f"\n  FPS distribution:")
    for fps, count in fps_counter.most_common():
        print(f"    {fps} fps: {count} videos")

    # Resolution distribution
    res_counter = Counter(f"{e['width']}x{e['height']}" for e in entries)
    print(f"\n  Resolution distribution:")
    for res, count in res_counter.most_common():
        print(f"    {res}: {count} videos")

    # Duration stats
    durations = [e["duration"] for e in entries if e["duration"] > 0]
    if durations:
        print(f"\n  Duration stats:")
        print(f"    Min:  {min(durations):.2f}s")
        print(f"    Max:  {max(durations):.2f}s")
        print(f"    Mean: {sum(durations)/len(durations):.2f}s")

    # Word patterns
    words = [e["word"] for e in entries]
    has_parens = [w for w in words if "(" in w]
    has_amp = [w for w in words if "&" in w]
    single_word = [w for w in words if " " not in w and "(" not in w]

    print(f"\n  Word patterns:")
    print(f"    Simple words:          {len(single_word)}")
    print(f"    With variants (...):   {len(has_parens)}")
    print(f"    With synonyms (&):     {len(has_amp)}")

    # Check target words
    print("\n" + "=" * 70)
    print("  Target word availability")
    print("=" * 70)

    targets = [
        "i", "water", "need", "help", "want", "food", "hello",
        "home", "go", "school", "thank", "good", "morning",
        "where", "you", "what", "yes", "no",
    ]
    for target in targets:
        matches = [
            e for e in entries
            if e["word"].lower() == target
            or e["word"].lower().startswith(f"{target} (")
            or target in e["word"].lower().split(" & ")
        ]
        if matches:
            best = matches[0]
            print(f"  {target:15s} ✓  '{best['word']}' "
                  f"(shard={best['shard']}, id={best['sample_id']})")
        else:
            print(f"  {target:15s} ✗  NOT FOUND")

    print("\n" + "=" * 70)
    print("  Inspection complete.")
    print("=" * 70)


if __name__ == "__main__":
    main()
