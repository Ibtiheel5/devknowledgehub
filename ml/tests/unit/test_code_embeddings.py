import math

from dkh_ml.models.code_embeddings import CodeEmbedder, cosine_similarity, embed_text

CODE_A = "def calculate_total(items):\n    return sum(item.price for item in items)\n"
CODE_B = "def compute_total(products):\n    return sum(product.price for product in products)\n"
CODE_C = "SELECT * FROM users WHERE active = true;\n"


def test_embedding_is_deterministic_and_normalized():
    first = embed_text(CODE_A, dimensions=64)
    second = embed_text(CODE_A, dimensions=64)
    assert first == second
    assert len(first) == 64
    assert math.isclose(math.sqrt(sum(v * v for v in first)), 1.0, rel_tol=1e-4)


def test_similar_code_scores_higher_than_unrelated_code():
    embedder = CodeEmbedder(dimensions=128)
    related = embedder.similarity(CODE_A, CODE_B)
    unrelated = embedder.similarity(CODE_A, CODE_C)
    assert related > unrelated


def test_cosine_similarity_identical_vectors():
    vector = embed_text(CODE_A, dimensions=32)
    assert cosine_similarity(vector, vector) == 1.0
