# English → Indian Sign Language (ISL) Translator

A working prototype that converts English text into Indian Sign Language (ISL) videos using the [bridgeconn/sign-dictionary-isl](https://huggingface.co/datasets/bridgeconn/sign-dictionary-isl) dataset.

## Project Objective

Convert English sentences into playable ISL sign videos by:
1. Preprocessing English text (tokenization, lemmatization)
2. Converting to ISL gloss sequence (SOV word order)
3. Looking up real sign videos from the local dataset
4. Combining individual sign videos into a single output

## Architecture

```
English Input
      │
      ▼
Text Preprocessing (preprocessing.py)
      │
      ▼
English → ISL Gloss (gloss_converter.py)
      │
      ▼
ISL Dictionary Lookup (dictionary.py → SQLite index)
      │
      ▼
Video Extraction (video_extractor.py → TAR shards)
      │
      ▼
Video Combination (video_builder.py → FFmpeg)
      │
      ▼
Final ISL Video (outputs/final_isl.mp4)
```

## Dataset Information

- **Name**: bridgeconn/sign-dictionary-isl
- **Source**: Bridge Connectivity Solutions Pvt. Ltd.
- **License**: Creative Commons - Attribution-ShareAlike (CC BY-SA)
- **Size**: ~7.1 GB across 7 TAR shards
- **Signs**: ~3,188 ISL sign videos
- **Format**: Each sample contains `.json` metadata + `.mp4` video

## Installation

### Prerequisites
- Python 3.10+
- FFmpeg
- The bridgeconn/sign-dictionary-isl dataset (downloaded separately)

### Setup

```bash
# Clone the project
cd ~/Personal_Designs/eng_to_isl

# Activate virtual environment
source .venv/bin/activate

# Install dependencies (most are already installed)
pip install -r requirements.txt

# Optional: Install Gradio for web UI
pip install gradio
```

## Dataset Setup

Place the downloaded TAR shards in:
```
data/sign_dictionary/
├── shard_00001-train.tar
├── shard_00002-train.tar
├── shard_00003-train.tar
├── shard_00004-train.tar
├── shard_00005-train.tar
├── shard_00006-train.tar
└── shard_00007-train.tar
```

## Index Creation

Build the SQLite index (one-time step):

```bash
python scripts/build_index.py
```

This creates `data/index/sign_dictionary.db` with searchable word mappings.

## CLI Usage

```bash
# Basic usage
python main.py "I need water"

# Without auto-opening the video
python main.py --no-open "I want food"

# Verbose output
python main.py --verbose "Thank you"

# Custom output path
python main.py --output my_video.mp4 "Good morning"
```

### Example Output

```
==================================================
  English → Indian Sign Language
==================================================

  Input:
  I need water

  ISL Gloss:
  I WATER NEED

  Sign lookup:
    I               ✓  (i)
    WATER           ✓  (water (1))
    NEED            ✓  (need (1))

  ✓ Translation completed
  Output: outputs/i_need_water_isl.mp4

==================================================
```

## Web UI Usage

```bash
python app.py
```

Opens a Gradio web interface at `http://localhost:7860` with:
- Text input
- Translate button
- ISL gloss display
- Sign lookup report
- Embedded video player

## Project Structure

```
eng_to_isl/
├── src/eng_to_isl/
│   ├── __init__.py
│   ├── config.py           # Paths, video settings, logging
│   ├── preprocessing.py    # Text tokenization & normalization
│   ├── gloss_converter.py  # English → ISL gloss (rule-based)
│   ├── dictionary.py       # SQLite-backed sign lookup
│   ├── video_extractor.py  # Extract .mp4 from TAR shards
│   ├── video_builder.py    # FFmpeg video concatenation
│   └── translator.py       # Main orchestrator
├── scripts/
│   ├── inspect_dataset.py  # Dataset inspection tool
│   └── build_index.py      # One-time index builder
├── data/
│   ├── sign_dictionary/    # TAR shards (not in git)
│   ├── index/              # SQLite index
│   └── isl_rules.json      # Configurable ISL grammar rules
├── tests/
│   └── test_translator.py
├── main.py                 # CLI entry point
├── app.py                  # Gradio web UI
├── requirements.txt
└── README.md
```

## Example Translations

| English | ISL Gloss | Signs Found |
|---|---|---|
| I need water | I WATER NEED | ✓ All |
| I want food | I FOOD WANT | ✓ All |
| Hello | HELLO | ✓ |
| Good morning | GOOD MORNING | ✓ All |
| Thank you | THANK YOU | ✓ All |
| I am going home | I HOME GO | ✓ All |

## Limitations

1. **Rule-based gloss conversion**: The current system uses simple SOV reordering rules, not full ISL grammar. This is a documented prototype assumption.
2. **Bible dictionary**: The dataset is from the ISL Bible Dictionary project, so it contains many biblical proper nouns alongside common words.
3. **Single-sign lookup**: Each word maps to one sign video. The system does not handle compound signs or classifiers.
4. **No fingerspelling**: If a word is not in the dictionary, it is reported as missing (fingerspelling support depends on alphabet video availability).
5. **No ML**: This is a deterministic prototype. The architecture is designed to support a future Transformer-based gloss converter.

## Dataset License & Attribution

The ISL sign videos are from the **bridgeconn/sign-dictionary-isl** dataset:
- **Source**: Bridge Connectivity Solutions Pvt. Ltd.
- **Project**: Indian Sign Language Bible (ISLV) Dictionary
- **License**: Creative Commons - Attribution-ShareAlike (CC BY-SA)

This project does not claim commercial usability. Users must comply with the dataset's license terms.

## Future ML Architecture

The system is designed for easy ML integration:

```python
# Current (rule-based)
converter = RuleBasedGlossConverter()

# Future (ML-based, drop-in replacement)
converter = TransformerGlossConverter(model_path="...")

# Both implement the same interface:
gloss = converter.convert(tokens)
```

Potential training data sources:
- bridgeconn/sign-dictionary-isl
- iSign dataset
- CISLR dataset

