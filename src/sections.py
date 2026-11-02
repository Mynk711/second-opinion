import re

# Every item a 10-K can have, in the order they appear
ITEM_TITLES = {
    "1": "Business", "1A": "Risk Factors", "1B": "Unresolved Staff Comments",
    "1C": "Cybersecurity", "2": "Properties", "3": "Legal Proceedings",
    "4": "Mine Safety Disclosures", "5": "Market for Common Equity", "6": "Reserved",
    "7": "Management's Discussion and Analysis", "7A": "Market Risk Disclosures",
    "8": "Financial Statements", "9": "Changes in and Disagreements with Accountants",
    "9A": "Controls and Procedures", "9B": "Other Information",
    "9C": "Foreign Jurisdictions that Prevent Inspections",
    "10": "Directors and Corporate Governance", "11": "Executive Compensation",
    "12": "Security Ownership", "13": "Related Transactions", "14": "Accountant Fees",
    "15": "Exhibits", "16": "Form 10-K Summary",
}
ITEM_RANK = {item: i for i, item in enumerate(ITEM_TITLES)}

# A heading is a line that starts with "Item <number><optional letter>"
HEADING = re.compile(r"^item\s+(\d{1,2}[a-c]?)\b", re.IGNORECASE | re.MULTILINE)

# Words that show a short section only points to content elsewhere
POINTER = re.compile(r"refer to|appears? on pages?|included on pages?|set forth in|"
                     r"incorporated (herein )?by reference", re.IGNORECASE)

# Where moved content starts inside Item 15. Whole-line matches only, so index
# entries like "Report of ... Firm (PCAOB ID: 238)" do not count.
MDA_START = re.compile(r"^management[’']s discussion and analysis$", re.IGNORECASE | re.MULTILINE)
FS_START = re.compile(r"^report of independent registered public accounting firm$",
                      re.IGNORECASE | re.MULTILINE)

STUB_CHARS = 2000            # sections shorter than this may only point elsewhere
MIN_GAP_AFTER_ITEM_1 = 1000  # real Item 1 is long; the table-of-contents entry is not


def make_section(item, text, relocated_from=None):
    """Build one section dict with its size and stub flags."""
    body = text.strip()
    is_short = len(body) < STUB_CHARS
    return {
        "item": item,
        "title": ITEM_TITLES[item],
        "text": body,
        "char_count": len(body),
        "is_short": is_short,
        "is_pointer": is_short and bool(POINTER.search(body)),
        "relocated_from": relocated_from,
    }


def find_headings(text):
    """All item headings as (item, position), in document order."""
    return [(m.group(1).upper(), m.start()) for m in HEADING.finditer(text)]


def find_body_start(headings):
    """Rule 1: the first 'Item 1' followed by a long gap is where the real document begins."""
    for i, (item, pos) in enumerate(headings[:-1]):
        next_pos = headings[i + 1][1]
        if item == "1" and next_pos - pos > MIN_GAP_AFTER_ITEM_1:
            return pos
    return 0


def relocate_from_item_15(sections):
    """
    Some filers (like JPM and NVDA) put MD&A or the financial statements after Item 15,
    leaving only a short pointer under Item 7 or 8. Move that content to the right item.
    """
    by_item = {s["item"]: s for s in sections}
    if "15" not in by_item:
        return sections
    text_15 = by_item["15"]["text"]

    # Find where each moved part starts inside Item 15
    cuts = {}
    if "7" in by_item and by_item["7"]["is_short"]:
        match = MDA_START.search(text_15)
        if match:
            cuts["7"] = match.start()
    if "8" in by_item and by_item["8"]["is_short"]:
        match = FS_START.search(text_15, cuts.get("7", 0))
        if match:
            cuts["8"] = match.start()
    if not cuts:
        return sections

    # Split Item 15 at those points: the part before stays Item 15, the rest is moved
    points = sorted(cuts.items(), key=lambda kv: kv[1])
    moved = []
    for i, (item, start) in enumerate(points):
        end = points[i + 1][1] if i + 1 < len(points) else len(text_15)
        moved.append(make_section(item, text_15[start:end], relocated_from="15"))
    new_15 = make_section("15", text_15[:points[0][1]])

    # Drop the pointer stubs, swap in the shortened Item 15, add the moved sections
    result = [new_15 if s["item"] == "15" else s for s in sections if s["item"] not in cuts]
    result += moved
    return sorted(result, key=lambda s: ITEM_RANK[s["item"]])


def parse_sections(text):
    """Split a 10-K's text into its items. Returns a list of section dicts."""
    headings = find_headings(text)
    body_start = find_body_start(headings)

    # Rule 2: keep a heading only if it comes later in the item order than the last one kept
    kept, last_rank = [], -1
    for item, pos in headings:
        if pos < body_start or item not in ITEM_RANK:
            continue
        if ITEM_RANK[item] > last_rank:
            kept.append((item, pos))
            last_rank = ITEM_RANK[item]

    # Rule 3: each section runs from its heading to the next kept heading
    sections = []
    for i, (item, start) in enumerate(kept):
        end = kept[i + 1][1] if i + 1 < len(kept) else len(text)
        sections.append(make_section(item, text[start:end]))

    return relocate_from_item_15(sections)