"""
BM25 sparse index for hybrid search: build from (chunk_id, text), persist by project_id, search by query.
Corpus and query are lemmatized for BM25 only.
"""
import os
from typing import List, Tuple, Any

try:
    from rank_bm25 import BM25Okapi
    import numpy as np
    _HAS_BM25 = True
except ImportError:
    _HAS_BM25 = False

from Utils.NLPPreprocess import lemmatize_text, tokenize


def _get_index_dir() -> str:
    try:
        from Helpers.Config import get_settings
        d = getattr(get_settings(), "BM25_INDEX_DIR", None)
        if d:
            return d
    except Exception:
        pass
    return os.path.join(os.path.dirname(__file__), "..", "..", "data", "bm25")


def _index_path(project_id: int) -> str:
    base = _get_index_dir()
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, f"bm25_{project_id}.joblib")


class BM25Index:
    """Build, persist, and search BM25 index keyed by project_id."""

    @staticmethod
    def build_index(project_id: int, chunks: List[Any]) -> bool:
        """
        Build BM25 index from chunks (objects with chunk_id and chunk_text).
        Lemmatizes text for indexing. Persists to disk.
        """
        if not _HAS_BM25:
            return False
        if not chunks:
            return False
        chunk_ids = []
        corpus_tokens = []
        for c in chunks:
            chunk_ids.append(getattr(c, "chunk_id", c[0]) if hasattr(c, "chunk_id") else c[0])
            text = getattr(c, "chunk_text", c[1]) if hasattr(c, "chunk_text") else c[1]
            normalized = lemmatize_text(text or "")
            tokens = normalized.split() if normalized else []
            corpus_tokens.append(tokens)
        try:
            bm25 = BM25Okapi(corpus_tokens)
            import joblib
            joblib.dump({"chunk_ids": chunk_ids, "bm25": bm25}, _index_path(project_id))
            return True
        except Exception:
            return False

    @staticmethod
    def search(project_id: int, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        """
        Search BM25 index for project_id. Returns list of (chunk_id, score) sorted by score desc.
        """
        if not _HAS_BM25:
            return []
        path = _index_path(project_id)
        if not os.path.isfile(path):
            return []
        try:
            import joblib
            data = joblib.load(path)
            chunk_ids = data["chunk_ids"]
            bm25 = data["bm25"]
        except Exception:
            return []
        query_norm = lemmatize_text(query or "")
        query_tokens = query_norm.split() if query_norm else []
        if not query_tokens:
            return []
        scores = bm25.get_scores(query_tokens)
        if not len(scores):
            return []
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [(chunk_ids[i], float(scores[i])) for i in top_indices if scores[i] > 0]

    @staticmethod
    def delete_index(project_id: int) -> bool:
        """Remove persisted index for project_id."""
        path = _index_path(project_id)
        if os.path.isfile(path):
            try:
                os.remove(path)
                return True
            except Exception:
                pass
        return False
