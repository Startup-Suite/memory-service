import logging
from typing import Protocol

import httpx
import numpy as np

logger = logging.getLogger(__name__)

QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class Embedder(Protocol):
    dimension: int

    def encode_documents(self, texts: list[str]) -> np.ndarray: ...

    def encode_query(self, text: str) -> np.ndarray: ...


class LocalEmbedder:
    def __init__(self, model_name: str, device: str = "cuda"):
        from sentence_transformers import SentenceTransformer

        logger.info("Loading embedding model %s on %s...", model_name, device)
        self.model = SentenceTransformer(model_name, device=device)
        self.dimension = self.model.get_sentence_embedding_dimension()
        logger.info("Model loaded. Dimension: %d", self.dimension)

    def encode_documents(self, texts: list[str]) -> np.ndarray:
        return self.model.encode(texts, normalize_embeddings=True)

    def encode_query(self, text: str) -> np.ndarray:
        prefixed = f"{QUERY_PREFIX}{text}"
        return self.model.encode([prefixed], normalize_embeddings=True)[0]


class HttpEmbedder:
    def __init__(self, base_url: str, model: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.client = httpx.Client(timeout=timeout)
        logger.info("Probing remote embedder at %s (model=%s)...", self.base_url, self.model)
        self.dimension = len(self._encode(["probe"])[0])
        logger.info("Remote embedder ready. Dimension: %d", self.dimension)

    def _encode(self, inputs: list[str]) -> list[list[float]]:
        resp = self.client.post(
            f"{self.base_url}/v1/embeddings",
            json={"model": self.model, "input": inputs},
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        return [item["embedding"] for item in sorted(data, key=lambda d: d["index"])]

    def encode_documents(self, texts: list[str]) -> np.ndarray:
        return np.asarray(self._encode(texts), dtype=np.float32)

    def encode_query(self, text: str) -> np.ndarray:
        prefixed = f"{QUERY_PREFIX}{text}"
        return np.asarray(self._encode([prefixed])[0], dtype=np.float32)


def make_embedder(settings) -> Embedder:
    if settings.embedding_backend == "http":
        if not settings.embedding_url:
            raise ValueError("MEMORY_EMBEDDING_URL must be set when MEMORY_EMBEDDING_BACKEND=http")
        return HttpEmbedder(settings.embedding_url, settings.embedding_model)
    return LocalEmbedder(settings.embedding_model, settings.embedding_device)
