#!/usr/bin/env python3
"""
Tests for the English → ISL Translator.

Tests preprocessing, gloss conversion, dictionary lookup, and full translation.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from eng_to_isl import config
from eng_to_isl.preprocessing import preprocess
from eng_to_isl.gloss_converter import RuleBasedGlossConverter
from eng_to_isl.dictionary import ISLDictionary

config.setup_logging()


def test_preprocessing():
    """Test text preprocessing."""
    print("=" * 60)
    print("  TEST: Preprocessing")
    print("=" * 60)

    cases = [
        ("I need water.", ["i", "need", "water"]),
        ("I want food!", ["i", "want", "food"]),
        ("I'm going home", ["i", "am", "go", "home"]),
        ("Don't stop", ["do", "not", "stop"]),
        ("HELLO", ["hello"]),
        ("  Good   morning  ", ["good", "morning"]),
        ("", []),
    ]

    passed = 0
    for text, expected in cases:
        result = preprocess(text)
        status = "✓" if result == expected else "✗"
        if status == "✓":
            passed += 1
        print(f"  {status} preprocess('{text}')")
        print(f"      Expected: {expected}")
        print(f"      Got:      {result}")

    print(f"\n  Result: {passed}/{len(cases)} passed\n")
    return passed == len(cases)


def test_gloss_conversion():
    """Test gloss conversion."""
    print("=" * 60)
    print("  TEST: Gloss Conversion")
    print("=" * 60)

    converter = RuleBasedGlossConverter()

    cases = [
        (["i", "need", "water"], ["I", "WATER", "NEED"]),
        (["i", "want", "food"], ["I", "FOOD", "WANT"]),
        (["good", "morning"], ["GOOD", "MORNING"]),
        (["hello"], ["HELLO"]),
        (["i", "home", "go"], ["I", "HOME", "GO"]),
    ]

    passed = 0
    for tokens, expected in cases:
        result = converter.convert(tokens)
        status = "✓" if result == expected else "✗"
        if status == "✓":
            passed += 1
        print(f"  {status} convert({tokens})")
        print(f"      Expected: {expected}")
        print(f"      Got:      {result}")

    print(f"\n  Result: {passed}/{len(cases)} passed\n")
    return passed == len(cases)


def test_dictionary_lookup():
    """Test dictionary lookups."""
    print("=" * 60)
    print("  TEST: Dictionary Lookup")
    print("=" * 60)

    try:
        dictionary = ISLDictionary()
    except FileNotFoundError:
        print("  ✗ Index not built. Run: python scripts/build_index.py")
        return False

    test_words = [
        "water", "need", "help", "i", "want", "food",
        "hello", "go", "good", "morning", "thank",
        "where", "you", "come", "eat", "drink",
    ]

    passed = 0
    total = len(test_words)

    for word in test_words:
        sign = dictionary.find_sign(word)
        if sign:
            print(f"  ✓ find_sign('{word}') → {sign}")
            passed += 1
        else:
            print(f"  ✗ find_sign('{word}') → SIGN_NOT_FOUND")

    dictionary.close()
    print(f"\n  Result: {passed}/{total} found\n")
    return passed > 0


def test_full_translation():
    """Test full translation pipeline on example sentences."""
    print("=" * 60)
    print("  TEST: Full Translation Pipeline")
    print("=" * 60)

    from eng_to_isl.translator import ISLTranslator

    sentences = [
        "Hello",
        "I need water",
        "I want water",
        "I want food",
        "I need help",
        "Thank you",
        "Good morning",
        "I am going home",
        "Where is school",
    ]

    try:
        translator = ISLTranslator()
    except FileNotFoundError as e:
        print(f"  ✗ {e}")
        return False

    results = []
    for sentence in sentences:
        print(f"\n  --- '{sentence}' ---")
        result = translator.translate(sentence)
        print(f"  Tokens:  {result.tokens}")
        print(f"  Gloss:   {' '.join(result.gloss)}")
        print(f"  Found:   {list(result.found.keys())}")
        print(f"  Missing: {result.missing}")
        print(f"  Video:   {result.output_video}")
        if result.errors:
            print(f"  Errors:  {result.errors}")
        results.append(result)

    translator.close()

    successful = sum(1 for r in results if r.success)
    print(f"\n  Videos produced: {successful}/{len(sentences)}")
    print()
    return successful > 0


def main():
    print("\n" + "=" * 60)
    print("  English → ISL Translator — Test Suite")
    print("=" * 60 + "\n")

    all_passed = True

    if not test_preprocessing():
        all_passed = False

    if not test_gloss_conversion():
        all_passed = False

    if not test_dictionary_lookup():
        all_passed = False

    if not test_full_translation():
        all_passed = False

    print("=" * 60)
    if all_passed:
        print("  ✓ All tests passed!")
    else:
        print("  ✗ Some tests failed.")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
