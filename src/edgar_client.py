import json
import time
from functools import lru_cache

import requests

from config import settings

HEADERS = {"User-Agent": settings.sec_user_agent}


def _get(url):
    # Pause between requests to stay under SEC's rate limit
    time.sleep(settings.sec.request_delay_seconds)
    response = requests.get(url, headers=HEADERS, timeout=settings.sec.timeout_seconds)
    response.raise_for_status()
    return response


@lru_cache(maxsize=1)
def _ticker_map():
    # Download the ticker -> CIK table once and reuse it
    data = _get("https://www.sec.gov/files/company_tickers.json").json()
    return {row["ticker"].upper(): str(row["cik_str"]).zfill(10) for row in data.values()}


def get_cik(ticker):
    cik = _ticker_map().get(ticker.upper())
    if cik is None:
        raise ValueError(f"Unknown ticker: {ticker}")
    return cik


def _matching(page, form):
    """Pick out filings of one form type from one page of SEC's filing list."""
    rows = zip(page["form"], page["accessionNumber"], page["primaryDocument"],
               page["filingDate"], page["reportDate"])
    return [
        {"form": f, "accession": a, "document": d, "filing_date": fd, "report_date": rd}
        for f, a, d, fd, rd in rows if f == form
    ]


def list_filings(cik, form, limit):
    """Return the most recent filings of one type, newest first."""
    submissions = _get(f"https://data.sec.gov/submissions/CIK{cik}.json").json()
    filings = _matching(submissions["filings"]["recent"], form)

    # Big filers (like banks) file so often that "recent" covers less than a year.
    # Older filings live in extra pages listed under "files"; read them until we have enough.
    for extra in submissions["filings"].get("files", []):
        if len(filings) >= limit:
            break
        page = _get(f"https://data.sec.gov/submissions/{extra['name']}").json()
        filings += _matching(page, form)

    return filings[:limit]


def download_filing(ticker, cik, filing):
    """Save the filing's HTML plus a small JSON file with its metadata."""
    accession = filing["accession"].replace("-", "")
    url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/{filing['document']}"
    out = settings.data.raw_dir / ticker / f"{filing['form']}_{filing['report_date']}.html"
    if out.exists():
        return out  # already downloaded, skip

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(_get(url).content)
    metadata = {**filing, "ticker": ticker, "cik": cik, "url": url}
    out.with_suffix(".json").write_text(json.dumps(metadata, indent=2))
    return out