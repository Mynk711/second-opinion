import json
import time

import numpy as np

from config import settings
from embeddings import embed_passages

CHUNKS = settings.data.processed_dir / "chunks.jsonl"
VECTORS = settings.data.processed_dir / "embeddings.npy"

chunks = [json.loads(line) for line in CHUNKS.open()]

# Embed the context header together with the text, so each vector "knows"
# which company, year, and section it came from
texts = [f"{c['context']}\n{c['text']}" for c in chunks]

start = time.time()
vectors = embed_passages(texts)

# Row i of this file belongs to line i of chunks.jsonl; keep that order intact
np.save(VECTORS, vectors)
print(f"Embedded {len(chunks):,} chunks in {time.time() - start:.0f}s -> shape {vectors.shape}")