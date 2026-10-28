from config import settings
from edgar_client import download_filing, get_cik, list_filings

cfg = settings.download

for ticker in cfg.tickers:
    cik = get_cik(ticker)
    for filing in list_filings(cik, form=cfg.form, limit=cfg.filings_per_company):
        path = download_filing(ticker, cik, filing)
        size_mb = path.stat().st_size / 1e6
        print(f"{ticker:<6} {filing['report_date']}  {size_mb:5.1f} MB  {path.name}")