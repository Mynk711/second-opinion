import json

import pandas as pd

from config import settings
from sections import parse_sections
from text_cleaning import html_to_text

KEY_ITEMS = ["1", "1A", "7", "8"]   # sections the agent relies on most
OUT_DIR = settings.data.processed_dir / "sections"

rows = []
for html_path in sorted(settings.data.raw_dir.glob("*/*.html")):
    meta = json.loads(html_path.with_suffix(".json").read_text())
    sections = parse_sections(html_to_text(html_path))

    # Attach filing details to every section; chunks and citations will need them later
    for s in sections:
        s.update(ticker=meta["ticker"], form=meta["form"],
                 fiscal_year_end=meta["report_date"], url=meta["url"])

    out = OUT_DIR / meta["ticker"] / f"{html_path.stem}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(sections, indent=2))

    # Validation checks
    warnings = []
    if not sections:
        warnings.append("NO SECTIONS FOUND")
    else:
        by_item = {s["item"]: s for s in sections}
        missing = [i for i in KEY_ITEMS if i not in by_item]
        short_keys = [i for i in KEY_ITEMS if i in by_item and by_item[i]["is_short"]]
        biggest = max(sections, key=lambda s: s["char_count"])
        share = biggest["char_count"] / sum(s["char_count"] for s in sections)
        if missing:
            warnings.append("missing " + ",".join(missing))
        if short_keys:
            warnings.append("short " + ",".join(short_keys))
        if share > 0.6:
            warnings.append(f"Item {biggest['item']} is {share:.0%} of filing")
        relocated = [s["item"] for s in sections if s["relocated_from"]]
        if relocated:
            warnings.append("moved " + ",".join(relocated) + " from Item 15")

    by_item = {s["item"]: s["char_count"] for s in sections}
    rows.append({
        "ticker": meta["ticker"],
        "year": meta["report_date"][:4],
        "sections": len(sections),
        "1A": by_item.get("1A", 0),
        "7": by_item.get("7", 0),
        "8": by_item.get("8", 0),
        "15": by_item.get("15", 0),
        "warnings": "; ".join(warnings) or "ok",
    })
    print(f"parsed {html_path.parent.name}/{html_path.name}")

report = pd.DataFrame(rows)
pd.set_option("display.width", 200)
print("\nVALIDATION REPORT")
print(report.to_string(index=False))