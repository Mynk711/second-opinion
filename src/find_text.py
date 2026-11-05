import argparse
import json

from config import settings

parser = argparse.ArgumentParser(description="Find chunks that contain an exact phrase")
parser.add_argument("phrase")
parser.add_argument("--ticker")
args = parser.parse_args()

matches = 0
for line in (settings.data.processed_dir / "chunks.jsonl").open():
    c = json.loads(line)
    if args.ticker and c["ticker"] != args.ticker.upper():
        continue
    i = c["text"].lower().find(args.phrase.lower())
    if i >= 0:
        matches += 1
        snippet = c["text"][max(0, i - 120): i + 200].replace("\n", " ")
        print(f"\n{c['chunk_id']}  (Item {c['item']})\n   ...{snippet}...")
print(f"\n{matches} chunk(s) contain this phrase")