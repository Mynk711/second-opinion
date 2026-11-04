import argparse
import json

import numpy as np

from config import settings
from embeddings import embed_query

parser = argparse.ArgumentParser(description="Search 10-K chunks by meaning")
parser.add_argument("query", help="your question, in quotes")
parser.add_argument("--ticker", help="only search one company, e.g. AAPL")
parser.add_argument("--item", help="only search one section, e.g. 1A")
parser.add_argument("-k", type=int, default=5, help="how many results to show")
args = parser.parse_args()

chunks = [json.loads(line) for line in (settings.data.processed_dir / "chunks.jsonl").open()]
vectors = np.load(settings.data.processed_dir / "embeddings.npy")

# Cosine similarity of the question with every chunk (all vectors are normalized)
scores = vectors @ embed_query(args.query)

# Metadata filters: chunks that don't match get the lowest possible score
for i, c in enumerate(chunks):
    if (args.ticker and c["ticker"] != args.ticker.upper()) or \
       (args.item and c["item"] != args.item.upper()):
        scores[i] = -np.inf

for rank, i in enumerate(np.argsort(-scores)[:args.k], start=1):
    if scores[i] == -np.inf:
        break
    c = chunks[i]
    print(f"\n#{rank}  score {scores[i]:.3f}  {c['chunk_id']}")
    print("   " + c["text"][:300].replace("\n", " ") + " ...")