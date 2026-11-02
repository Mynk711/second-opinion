import json

import pandas as pd

from chunking import chunk_section, find_boilerplate
from config import settings

SECTIONS_DIR = settings.data.processed_dir / "sections"
OUT = settings.data.processed_dir / "chunks.jsonl"
skip = set(settings.chunking.skip_items)

chunks = []
for path in sorted(SECTIONS_DIR.glob("*/*.json")):
    sections = json.loads(path.read_text())
    boilerplate = find_boilerplate(sections)

    for s in sections:
        if s["item"] in skip or s["char_count"] < settings.chunking.min_chars:
            continue
        # Short header that tells the embedding model and the LLM where this text came from
        context = (f"{s['ticker']} {s['form']}, fiscal year ended {s['fiscal_year_end']}, "
                   f"Item {s['item']}: {s['title']}")
        for n, (kind, text) in enumerate(chunk_section(s, boilerplate)):
            chunks.append({
                "chunk_id": f"{s['ticker']}_{s['fiscal_year_end']}_{s['item']}_{n:04d}",
                "ticker": s["ticker"],
                "form": s["form"],
                "fiscal_year_end": s["fiscal_year_end"],
                "item": s["item"],
                "title": s["title"],
                "url": s["url"],
                "relocated_from": s["relocated_from"],
                "kind": kind,
                "context": context,
                "text": text,
                "char_count": len(text),
            })
    print(f"chunked {path.parent.name}/{path.name}: removed {len(boilerplate)} repeated header/footer lines")

# One chunk per line (JSON Lines), easy to stream and append to
with OUT.open("w") as f:
    for c in chunks:
        f.write(json.dumps(c) + "\n")

df = pd.DataFrame(chunks)
print(f"\nTotal chunks: {len(df):,}  (~{df.char_count.sum() // 4:,} tokens)")
print("\nChunks per company:")
print(df.groupby("ticker").size().to_string())
print("\nChunk size (characters):")
print(df.char_count.describe(percentiles=[0.05, 0.5, 0.95]).round(0).to_string())
print(f"\nTable chunks: {(df.kind == 'table').mean():.0%}")

sample = df[(df.ticker == "AAPL") & (df.item == "1A")].iloc[5]
print("\n--- Sample chunk ---")
print(sample.context)
print(sample.text[:1200])