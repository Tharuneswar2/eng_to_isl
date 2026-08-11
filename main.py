#!/usr/bin/env python3
"""
English → Indian Sign Language (ISL) Translator — CLI

Usage:
    python main.py "I need water"
    python main.py "I want food"
    python main.py --no-open "Thank you"

Options:
    --no-open       Don't auto-open the output video
    --output PATH   Custom output video path
    --verbose       Enable debug logging
"""

import argparse
import subprocess
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from eng_to_isl import config
from eng_to_isl.translator import ISLTranslator


def open_video(path: Path) -> None:
    """Try to open the video with the system's default player."""
    try:
        subprocess.Popen(
            ["xdg-open", str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass  # xdg-open not available, silently skip


def main():
    parser = argparse.ArgumentParser(
        description="English → Indian Sign Language (ISL) Translator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            '  python main.py "I need water"\n'
            '  python main.py "I want food"\n'
            '  python main.py "Thank you"\n'
            '  python main.py --no-open "Hello"\n'
        ),
    )
    parser.add_argument(
        "text",
        help="English text to translate to ISL",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Don't auto-open the output video",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Custom output video path",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    # Setup logging
    import logging
    level = logging.DEBUG if args.verbose else logging.INFO
    config.setup_logging(level)

    # Run translation
    try:
        with ISLTranslator() as translator:
            result = translator.translate(
                args.text,
                output_path=args.output,
            )

        # Print summary
        print(result.summary())

        # Auto-open if successful and not disabled
        if result.success and not args.no_open:
            open_video(result.output_video)

        # Exit code
        sys.exit(0 if result.success else 1)

    except FileNotFoundError as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        print(
            "\nMake sure you've run: python scripts/build_index.py",
            file=sys.stderr,
        )
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)
    except Exception as e:
        print(f"\nUnexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
