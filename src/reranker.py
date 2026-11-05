from functools import lru_cache

from sentence_transformers import CrossEncoder

from config import settings

cfg = settings.reranker


@lru_cache(maxsize=1)
def _model():
    # Reads at most 512 tokens per (question, chunk) pair; longer chunks are cut off
    return CrossEncoder(cfg.model_name, max_length=512)


def rerank_scores(query, chunks):
    """Score every (question, chunk) pair together. Higher score = better answer."""
    pairs = [(query, f"{c['context']}\n{c['text']}") for c in chunks]
    return _model().predict(pairs, batch_size=cfg.batch_size, show_progress_bar=False)