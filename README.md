# SECond Opinion

A research agent that answers questions about US public companies from their SEC 10-K filings, with citations to the exact filing section. Explanations come from retrieved filing text; exact financial figures will come from SEC's structured XBRL data, not from the language model.

**Status:** retrieval pipeline and evaluation complete. Agent, XBRL tool, and UI in progress.

## What is built

1. **Data pipeline:** downloads 10-K filings from SEC EDGAR (with pagination for high-volume filers like banks), currently 20 filings across 10 companies in tech, banking, pharma, and autos.
2. **Section-aware parsing:** splits each filing into its 10-K Items (Risk Factors, MD&A, Financial Statements, ...). Handles filings that use cross-references, such as JPMorgan placing its MD&A and financial statements in an appended annual report, by detecting pointer sections and relocating the real content. A validation report checks every filing.
3. **Chunking:** about 600-token chunks with overlap, tables kept separate from prose, running headers and footers removed, and a context header on every chunk (company, fiscal year, section).
4. **Hybrid retrieval:** dense embeddings (BGE-small) plus BM25 keyword search, fused with weighted Reciprocal Rank Fusion, with metadata filters and an optional cross-encoder reranker.
5. **Evaluation:** a 50-question retrieval eval set covering risk, MD&A, business, numeric, cross-company, and year-specific questions, labeled by content so labels survive re-chunking.

## Retrieval results (50 questions)

| Method | Hit@5 | Hit@10 | Hit@50 | MRR | Seconds per query |
|---|---|---|---|---|---|
| BM25 | 0.48 | 0.56 | 0.90 | 0.32 | 0.02 |
| Dense (BGE-small) | 0.62 | 0.82 | 0.98 | 0.48 | 0.04 |
| Hybrid, weighted RRF (dense 2 : BM25 1) | 0.66 | 0.80 | 0.98 | 0.47 | 0.02 |
| Hybrid + MiniLM cross-encoder rerank | 0.68 | 0.80 | 0.98 | 0.55 | 0.54 |

Key findings from evaluation:
- Standard RRF dropped chunks that only one retriever found: in one case, dense search ranked the correct chunk #1 and fusion pushed it to #28. Weighting the dense list 2x fixed this and improved all four metrics.
- A larger reranker (bge-reranker-base) scored lower than the small MiniLM reranker and was about 14x slower.
- Numeric questions are the weakest category for retrieval, which is why exact figures will come from XBRL data instead.

## How to run

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # then put your name and email in .env (SEC requires it)

python src/download.py          # download filings from SEC EDGAR
python src/parse_all.py         # split filings into sections + validation report
python src/build_chunks.py      # chunk sections
python src/build_index.py       # embeddings
python src/build_bm25.py        # keyword index

python src/search.py "What are Apple's supply chain risks?" --ticker AAPL
python src/evaluate_retrieval.py
```

Settings (companies, chunk size, models, fusion weights) live in `config.yaml`.

## Roadmap

- [x] EDGAR data pipeline, section parsing, chunking
- [x] Hybrid retrieval with evaluation
- [ ] XBRL tool for exact financial figures
- [ ] LangGraph agent with search, numbers, and calculator tools; cited answers
- [ ] Answer-level evals: correctness, citation accuracy, hallucination rate, cost and latency
- [ ] FastAPI service, Docker, UI, and a live demo