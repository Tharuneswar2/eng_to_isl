"""
English text preprocessing for the ISL Translator.

Handles:
- Lowercasing
- Punctuation removal
- Whitespace normalization
- Tokenization
- Contraction expansion
- Basic lemmatization (with spaCy fallback)
"""

import re
from . import config

logger = config.get_logger(__name__)

# ─── Contraction map ──────────────────────────────────────────────────────────
CONTRACTIONS = {
    "i'm": "i am",
    "i've": "i have",
    "i'll": "i will",
    "i'd": "i would",
    "you're": "you are",
    "you've": "you have",
    "you'll": "you will",
    "you'd": "you would",
    "he's": "he is",
    "he'll": "he will",
    "he'd": "he would",
    "she's": "she is",
    "she'll": "she will",
    "she'd": "she would",
    "it's": "it is",
    "it'll": "it will",
    "it'd": "it would",
    "we're": "we are",
    "we've": "we have",
    "we'll": "we will",
    "we'd": "we would",
    "they're": "they are",
    "they've": "they have",
    "they'll": "they will",
    "they'd": "they would",
    "that's": "that is",
    "that'll": "that will",
    "that'd": "that would",
    "who's": "who is",
    "who'll": "who will",
    "who'd": "who would",
    "what's": "what is",
    "what'll": "what will",
    "what'd": "what would",
    "where's": "where is",
    "where'll": "where will",
    "where'd": "where would",
    "when's": "when is",
    "when'll": "when will",
    "when'd": "when would",
    "why's": "why is",
    "why'll": "why will",
    "why'd": "why would",
    "how's": "how is",
    "how'll": "how will",
    "how'd": "how would",
    "isn't": "is not",
    "aren't": "are not",
    "wasn't": "was not",
    "weren't": "were not",
    "hasn't": "has not",
    "haven't": "have not",
    "hadn't": "had not",
    "doesn't": "does not",
    "don't": "do not",
    "didn't": "did not",
    "won't": "will not",
    "wouldn't": "would not",
    "shan't": "shall not",
    "shouldn't": "should not",
    "can't": "cannot",
    "couldn't": "could not",
    "mustn't": "must not",
    "let's": "let us",
    "there's": "there is",
    "here's": "here is",
}

# ─── Basic lemma map (fallback when spaCy unavailable) ────────────────────────
BASIC_LEMMAS = {
    "going": "go",
    "goes": "go",
    "went": "go",
    "gone": "go",
    "coming": "come",
    "comes": "come",
    "came": "come",
    "eating": "eat",
    "eats": "eat",
    "ate": "eat",
    "eaten": "eat",
    "drinking": "drink",
    "drinks": "drink",
    "drank": "drink",
    "drunk": "drink",
    "helping": "help",
    "helps": "help",
    "helped": "help",
    "wanting": "want",
    "wants": "want",
    "wanted": "want",
    "needing": "need",
    "needs": "need",
    "needed": "need",
    "thanking": "thank",
    "thanks": "thank",
    "thanked": "thank",
    "foods": "food",
    "waters": "water",
    "schools": "school",
    "homes": "home",
    "houses": "house",
    "mornings": "morning",
    "humans": "human",
    "children": "child",
    "people": "person",
    "men": "man",
    "women": "woman",
    "said": "say",
    "says": "say",
    "saying": "say",
    "told": "tell",
    "tells": "tell",
    "telling": "tell",
    "gives": "give",
    "giving": "give",
    "gave": "give",
    "given": "give",
    "sees": "see",
    "seeing": "see",
    "saw": "see",
    "seen": "see",
    "knows": "know",
    "knowing": "know",
    "knew": "know",
    "known": "know",
    "thinks": "think",
    "thinking": "think",
    "thought": "think",
    "makes": "make",
    "making": "make",
    "made": "make",
    "takes": "take",
    "taking": "take",
    "took": "take",
    "taken": "take",
}


def _try_spacy_lemmatize(tokens: list[str]) -> list[str] | None:
    """Attempt lemmatization with spaCy. Returns None if unavailable."""
    try:
        import spacy

        try:
            nlp = spacy.load("en_core_web_sm")
        except OSError:
            return None

        text = " ".join(tokens)
        doc = nlp(text)
        return [token.lemma_.lower() for token in doc]
    except ImportError:
        return None


def _basic_lemmatize(tokens: list[str]) -> list[str]:
    """Simple dictionary-based lemmatization fallback."""
    result = []
    for token in tokens:
        lemma = BASIC_LEMMAS.get(token, token)
        result.append(lemma)
    return result


def preprocess(text: str, use_spacy: bool = False) -> list[str]:
    """Preprocess English text into normalized tokens.

    Args:
        text: Raw English text input.
        use_spacy: Whether to attempt spaCy lemmatization.

    Returns:
        List of normalized, lowercased tokens.

    Example:
        >>> preprocess("I need water.")
        ['i', 'need', 'water']
        >>> preprocess("I'm going home!")
        ['i', 'am', 'going', 'home']
    """
    if not text or not text.strip():
        logger.warning("Empty input text")
        return []

    logger.debug(f"Preprocessing: '{text}'")

    # Step 1: Lowercase
    text = text.lower().strip()

    # Step 2: Expand contractions
    for contraction, expansion in CONTRACTIONS.items():
        # Use word boundary matching to avoid partial replacements
        pattern = r"\b" + re.escape(contraction) + r"\b"
        text = re.sub(pattern, expansion, text)

    # Step 3: Remove punctuation (keep apostrophes within words)
    text = re.sub(r"[^\w\s']", " ", text)
    # Remove standalone apostrophes
    text = re.sub(r"(?<!\w)'|'(?!\w)", " ", text)

    # Step 4: Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # Step 5: Tokenize
    tokens = text.split()

    if not tokens:
        return []

    # Step 6: Lemmatize
    if use_spacy:
        spacy_result = _try_spacy_lemmatize(tokens)
        if spacy_result is not None:
            tokens = spacy_result
            logger.debug(f"spaCy lemmatized: {tokens}")
        else:
            tokens = _basic_lemmatize(tokens)
            logger.debug(f"Basic lemmatized (spaCy unavailable): {tokens}")
    else:
        tokens = _basic_lemmatize(tokens)
        logger.debug(f"Basic lemmatized: {tokens}")

    logger.debug(f"Preprocessed tokens: {tokens}")
    return tokens
