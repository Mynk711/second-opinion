from datetime import datetime

import pandas as pd
import yaml

from config import ROOT
from retrieval import search

MODES = ["dense", "bm25", "hybrid"]
K = 10  # look at the top 10 so we can report Hit@5, Hit@10, and MRR


def is_relevant(chunk, q):
    """A chunk is correct if it matches the company, one of the sections, and one phrase."""
    rel = q["relevant"]
    if rel.get("tickers") and chunk["ticker"] not in rel["tickers"]:
        return False
    if rel.get("items") and chunk["item"] not in rel["items"]:
        return False
    text = chunk["text"].lower()
    return any(phrase.lower() in text for phrase in rel["contains_any"])


questions = yaml.safe_load((ROOT / "evals" / "retrieval_questions.yaml").read_text())

rows = []
for q in questions:
    for mode in MODES:
        results = search(q["question"], mode=mode, top_k=K, **q.get("filters", {}))
        # Rank of the first correct chunk, or None if none in the top K
        rank = next((n for n, r in enumerate(results, start=1) if is_relevant(r["chunk"], q)), None)
        rows.append({"id": q["id"], "type": q["type"], "mode": mode, "rank": rank})

df = pd.DataFrame(rows)
df["hit@5"] = df["rank"].le(5)
df["hit@10"] = df["rank"].notna()
df["mrr"] = (1 / df["rank"]).fillna(0)

print(f"\n{len(questions)} questions\n")
print("OVERALL")
print(df.groupby("mode")[["hit@5", "hit@10", "mrr"]].mean().round(2).to_string())

print("\nHIT@5 BY QUESTION TYPE")
print(df.pivot_table(index="type", columns="mode", values="hit@5").round(2).to_string())

print("\nHYBRID MISSES (not in top 5)")
misses = df[(df["mode"] == "hybrid") & ~df["hit@5"]]
print(misses[["id", "type", "rank"]].to_string(index=False) if len(misses) else "none")

# Save every run, so we can compare before/after each change
out = ROOT / "evals" / "results" / f"retrieval_{datetime.now():%Y%m%d_%H%M}.csv"
out.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(out, index=False)
print(f"\nSaved {out.relative_to(ROOT)}")