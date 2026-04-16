from unittest.mock import AsyncMock

import numpy as np
import pytest
from fastapi.testclient import TestClient

from memory_service.main import app


class FakeEmbedder:
    """Deterministic embedder for tests — returns normalized random vectors seeded by content hash."""

    dimension = 1024

    def encode_documents(self, texts: list[str]) -> np.ndarray:
        vectors = []
        for text in texts:
            rng = np.random.default_rng(seed=hash(text) % (2**32))
            vec = rng.standard_normal(self.dimension).astype(np.float32)
            vec /= np.linalg.norm(vec)
            vectors.append(vec)
        return np.array(vectors)

    def encode_query(self, text: str) -> np.ndarray:
        rng = np.random.default_rng(seed=hash(text) % (2**32))
        vec = rng.standard_normal(self.dimension).astype(np.float32)
        vec /= np.linalg.norm(vec)
        return vec


@pytest.fixture
def fake_embedder():
    return FakeEmbedder()


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.upsert = AsyncMock(return_value=None)
    db.search = AsyncMock(return_value=[])
    db.delete = AsyncMock(return_value=0)
    db.list_since = AsyncMock(return_value=[])
    return db


@pytest.fixture
def client(fake_embedder, mock_db):
    app.state.embedder = fake_embedder
    app.state.db = mock_db
    return TestClient(app, raise_server_exceptions=True)
