"""
NLP preprocessing for BM25: tokenization and lemmatization.
Used to normalize corpus and query text for sparse retrieval only; dense embeddings use original text.
"""
from typing import List
import re

_NLTK_DOWNLOADED = False


def _ensure_nltk() -> None:
    global _NLTK_DOWNLOADED
    if _NLTK_DOWNLOADED:
        return
    try:
        import nltk
        nltk.download("wordnet", quiet=True)
        nltk.download("punkt", quiet=True)
        nltk.download("omw-1.4", quiet=True)
        _NLTK_DOWNLOADED = True
    except Exception:
        pass


def tokenize(text: str) -> List[str]:
    """Tokenize text into words (after nltk download). Falls back to simple split if nltk unavailable."""
    if not text or not text.strip():
        return []
    _ensure_nltk()
    try:
        from nltk import word_tokenize
        return word_tokenize(text.lower())
    except Exception:
        return re.findall(r"\b\w+\b", text.lower())


def lemmatize_text(text: str) -> str:
    """
    Lemmatize text for BM25: tokenize, lemmatize each token, rejoin.
    Returns normalized string for indexing or querying.
    """
    if not text or not text.strip():
        return ""
    _ensure_nltk()
    try:
        from nltk import word_tokenize
        from nltk.stem import WordNetLemmatizer
        lemmatizer = WordNetLemmatizer()
        tokens = word_tokenize(text.lower())
        lemmas = [lemmatizer.lemmatize(t) for t in tokens]
        return " ".join(lemmas)
    except Exception:
        return text.lower()


def lemmatize_tokens(tokens: List[str]) -> List[str]:
    """Lemmatize a list of tokens."""
    if not tokens:
        return []
    _ensure_nltk()
    try:
        from nltk.stem import WordNetLemmatizer
        lemmatizer = WordNetLemmatizer()
        return [lemmatizer.lemmatize(t) for t in tokens]
    except Exception:
        return tokens
