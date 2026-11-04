"""Embeddings pluggables. Même interface pour le mode dev (hash) et le vrai modèle."""
import hashlib
import itertools
import math
import re
from functools import lru_cache
from typing import Protocol

from app.config import settings

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*|\d+")
_CAMEL_RE = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+")


class Embedder(Protocol):
    name: str
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


def subtokens(text: str) -> list[str]:
    """`getUserById` / `get_user_by_id` -> get, user, by, id (+ l'identifiant entier)."""
    out: list[str] = []
    for raw in _TOKEN_RE.findall(text):
        parts = [p.lower() for p in _CAMEL_RE.findall(raw)]
        out.extend(parts)
        if len(parts) > 1:
            out.append(raw.lower())
    return out


class HashingEmbedder:
    """Sac de sous-tokens hashés (signed hashing trick), normalisé L2.

    Pas sémantique (« auth » ≠ « login »), mais déterministe, instantané et sans
    dépendance : idéal pour les tests, la CI et le développement hors-ligne.
    """

    def __init__(self, dim: int = 384):
        self.dim = dim
        self.name = f"hash-{dim}"

    def _vec(self, text: str) -> list[float]:
        v = [0.0] * self.dim
        toks = subtokens(text)
        for t in toks + [f"{a}_{b}" for a, b in itertools.pairwise(toks)]:
            h = int.from_bytes(hashlib.blake2b(t.encode(), digest_size=8).digest(), "big")
            v[h % self.dim] += 1.0 if (h >> 63) & 1 else -1.0
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]


class SentenceTransformerEmbedder:
    def __init__(self, model: str, dim: int):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:  # pragma: no cover
            raise RuntimeError(
                "sentence-transformers non installé : pip install -r requirements-ml.txt"
            ) from e
        self._model = SentenceTransformer(model)
        real = self._model.get_sentence_embedding_dimension()
        if real != dim:
            raise ValueError(
                f"Le modèle produit {real} dimensions mais EMBEDDING_DIM={dim} "
                "(la colonne vector(N) doit être recréée)."
            )
        self.dim, self.name = dim, model

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(texts, normalize_embeddings=True).tolist()


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    if settings.embedding_backend == "sentence-transformers":
        return SentenceTransformerEmbedder(settings.embedding_model, settings.embedding_dim)
    return HashingEmbedder(settings.embedding_dim)
