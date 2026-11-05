import argparse

from retrieval import search

parser = argparse.ArgumentParser(description="Search 10-K chunks")
parser.add_argument("query", help="your question, in quotes")
parser.add_argument("--ticker", help="only search one company, e.g. AAPL")
parser.add_argument("--item", help="only search one section, e.g. 1A")
parser.add_argument("--year", help="only search filings for one fiscal year, e.g. 2024")
parser.add_argument("--all-years", action="store_true", help="search every year, not just the latest")
parser.add_argument("--mode", choices=["dense", "bm25", "hybrid", "rerank"], default="hybrid")
parser.add_argument("-k", type=int, help="how many results to show")
args = parser.parse_args()

results = search(args.query, mode=args.mode, top_k=args.k, ticker=args.ticker,
                 item=args.item, year=args.year, all_years=args.all_years)

for n, r in enumerate(results, start=1):
    c = r["chunk"]
    found_by = f"dense #{r['dense_rank'] or '-'}, bm25 #{r['bm25_rank'] or '-'}"
    print(f"\n#{n}  {c['chunk_id']}  ({found_by})")
    print("   " + c["text"][:300].replace("\n", " ") + " ...")