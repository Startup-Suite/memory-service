import numpy as np

from tests.conftest import FakeEmbedder


def test_encode_documents_shape():
    embedder = FakeEmbedder()
    vectors = embedder.encode_documents(["hello", "world"])
    assert vectors.shape == (2, 1024)


def test_encode_documents_normalized():
    embedder = FakeEmbedder()
    vectors = embedder.encode_documents(["test sentence"])
    norm = np.linalg.norm(vectors[0])
    assert abs(norm - 1.0) < 1e-5


def test_encode_query_shape():
    embedder = FakeEmbedder()
    vec = embedder.encode_query("search query")
    assert vec.shape == (1024,)


def test_encode_query_normalized():
    embedder = FakeEmbedder()
    vec = embedder.encode_query("search query")
    norm = np.linalg.norm(vec)
    assert abs(norm - 1.0) < 1e-5


def test_encode_deterministic():
    embedder = FakeEmbedder()
    v1 = embedder.encode_documents(["same text"])
    v2 = embedder.encode_documents(["same text"])
    assert np.allclose(v1, v2)


def test_encode_different_texts_produce_different_vectors():
    embedder = FakeEmbedder()
    v1 = embedder.encode_documents(["text one"])[0]
    v2 = embedder.encode_documents(["text two"])[0]
    assert not np.allclose(v1, v2)
