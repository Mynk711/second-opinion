from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

from config import settings

cfg = settings.embedding


@lru_cache(maxsize=1)
def _model():
    # Downloaded from Hugging Face on first use, then cached on disk
    return SentenceTransformer(cfg.model_name)


def embed_passages(texts):
    """Embed chunks. Vectors are normalized, so a dot product equals cosine similarity."""
    vectors = _model().encode(texts, batch_size=cfg.batch_size, normalize_embeddings=True,
                              show_progress_bar=True, convert_to_numpy=True)
    return vectors.astype(np.float32)


def embed_query(query):
    """Embed one search question, with the model's recommended prefix."""
    vector = _model().encode([cfg.query_prefix + query], normalize_embeddings=True,
                             convert_to_numpy=True)[0]
    return vector.astype(np.float32)