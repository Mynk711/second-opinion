import json
import pickle
from functools import lru_cache

import numpy as np

from config import settings
from embeddings import embed_query
from lexical import tokenize

DIR = settings.data.processed_dir
cfg = settings.retrieval


@lru_cache(maxsize=1)
def load_index():
    """Load chunks, their vectors, and the BM25 index once per process."""
    chunks = [json.loads(line) for line in (DIR / "chunks.jsonl").open()]
    vectors = np.load(DIR / "embeddings.npy")
    with (DIR / "bm25.pkl").open("rb") as f:
        bm25 = pickle.load(f)
    return chunks, vectors, bm25


def filter_mask(chunks, ticker=None, item=None, year=None, all_years=False):
    """True for chunks that pass the filters. By default, only each company's latest filing."""
    latest = {}
    for c in chunks:
        latest[c["ticker"]] = max(latest.get(c["ticker"], ""), c["fiscal_year_end"])

    mask = []
    for c in chunks:
        ok = (not ticker or c["ticker"] == ticker.upper()) and \
             (not item or c["item"] == item.upper())
        if year:
            ok = ok and c["fiscal_year_end"].startswith(str(year))
        elif not all_years:
            ok = ok and c["fiscal_year_end"] == latest[c["ticker"]]
        mask.append(ok)
    return np.array(mask)


def _top(scores, mask, n):
    """Indices of the n best-scoring chunks that pass the mask."""
    scores = np.where(mask, scores, -np.inf)
    order = np.argsort(-scores)[:n]
    return [int(i) for i in order if scores[i] != -np.inf]


def dense_search(query, mask, n):
    _, vectors, _ = load_index()
    return _top(vectors @ embed_query(query), mask, n)


def bm25_search(query, mask, n):
    _, _, bm25 = load_index()
    return _top(bm25.get_scores(tokenize(query)), mask, n)


def rrf(rank_lists, k):
    """Reciprocal Rank Fusion: a chunk scores 1/(k + rank) in every list it appears in."""
    scores = {}
    for ranks in rank_lists:
        for rank, i in enumerate(ranks, start=1):
            scores[i] = scores.get(i, 0.0) + 1.0 / (k + rank)
    return sorted(scores, key=scores.get, reverse=True)


def search(query, mode="hybrid", top_k=None, **filters):
    """Search chunks with "dense", "bm25", or "hybrid" (both, fused with RRF)."""
    chunks, _, _ = load_index()
    mask = filter_mask(chunks, **filters)

    dense = dense_search(query, mask, cfg.candidates) if mode in ("dense", "hybrid") else []
    lexical = bm25_search(query, mask, cfg.candidates) if mode in ("bm25", "hybrid") else []
    order = {"dense": dense, "bm25": lexical}.get(mode) or rrf([dense, lexical], cfg.rrf_k)

    # Keep each result's rank in both lists, so we can see which method found it
    dense_rank = {i: r for r, i in enumerate(dense, start=1)}
    bm25_rank = {i: r for r, i in enumerate(lexical, start=1)}
    return [{"chunk": chunks[i], "dense_rank": dense_rank.get(i), "bm25_rank": bm25_rank.get(i)}
            for i in order[:top_k or cfg.top_k]]