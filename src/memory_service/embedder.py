import logging

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class Embedder:
    def __init__(self, model_name: str, device: str = "cuda"):
        logger.info("Loading embedding model %s on %s...", model_name, device)
        self.model = SentenceTransformer(model_name, device=device)
        self.dimension = self.model.get_embedding_dimension()
        logger.info("Model loaded. Dimension: %d", self.dimension)

    def encode_documents(self, texts: list[str]) -> np.ndarray:
        return self.model.encode(texts, normalize_embeddings=True)

    def encode_query(self, text: str) -> np.ndarray:
        prefixed = f"{QUERY_PREFIX}{text}"
        return self.model.encode([prefixed], normalize_embeddings=True)[0]
