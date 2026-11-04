"""Embeddings de code déterministes (hashing) sans dépendance à un modèle lourd."""
import hashlib
import math
import re

_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|\d+|[^\sA-Za-z0-9_]")
DEFAULT_DIMENSIONS = 256


def _bucket(token: str, dimensions: int) -> tuple[int, float]:
    digest = hashlib.md5(token.encode("utf-8"), usedforsecurity=False).digest()
    index = int.from_bytes(digest[:4], "big") % dimensions
    sign = 1.0 if digest[4] % 2 == 0 else -1.0
    return index, sign


def embed_text(text: str, dimensions: int = DEFAULT_DIMENSIONS) -> list[float]:
    vector = [0.0] * dimensions
    tokens = _TOKEN_RE.findall(text.lower())
    for token in tokens:
        index, sign = _bucket(token, dimensions)
        vector[index] += sign
        for cursor in range(len(token) - 2):
            index, sign = _bucket(token[cursor : cursor + 3], dimensions)
            vector[index] += 0.5 * sign
    norm = math.sqrt(sum(value * value for value in vector))
    if norm:
        vector = [round(value / norm, 6) for value in vector]
    return vector


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("Embeddings de dimensions différentes")
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    return round(max(-1.0, min(1.0, dot)), 6)


class CodeEmbedder:
    def __init__(self, dimensions: int = DEFAULT_DIMENSIONS):
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        return embed_text(text, self.dimensions)

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(text) for text in texts]

    def similarity(self, a: str, b: str) -> float:
        return cosine_similarity(self.embed(a), self.embed(b))
