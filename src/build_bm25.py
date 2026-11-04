import json
import pickle
import time

from rank_bm25 import BM25Okapi

from config import settings
from lexical import tokenize

DIR = settings.data.processed_dir
chunks = [json.loads(line) for line in (DIR / "chunks.jsonl").open()]

start = time.time()
# Same text the embeddings saw: context header plus chunk text
corpus = [tokenize(f"{c['context']}\n{c['text']}") for c in chunks]
bm25 = BM25Okapi(corpus)

# Save the index so searches don't rebuild it every time
with (DIR / "bm25.pkl").open("wb") as f:
    pickle.dump(bm25, f)
print(f"BM25 index over {len(chunks):,} chunks built in {time.time() - start:.0f}s")