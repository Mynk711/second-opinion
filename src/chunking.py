import re
from collections import Counter

from config import settings

cfg = settings.chunking
PAGE_NUMBER = re.compile(r"^\d{1,3}$")       # a line that is only a page number
SYMBOLS_ONLY = re.compile(r"^[\W_]+$")       # a line with no letters or digits, like "$" or ")"

DIGITS = re.compile(r"\d+")


def footer_key(line):
    """Mask digits so one running footer matches on every page ("... | 7", "... | 8")."""
    return DIGITS.sub("#", line)

SENTENCE_END = re.compile(r"(?<=[.!?])\s+")  # split point between sentences


def find_boilerplate(sections):
    """
    Running headers and footers in one filing. Two kinds:
    - short lines that repeat next to page numbers (table headings like "(In millions)" stay)
    - short lines naming the form, like "Apple Inc. | 2025 Form 10-K | 7", even with "|" in them
    """
    total, near_page, footers = Counter(), Counter(), Counter()
    for s in sections:
        lines = [line for line in s["text"].split("\n") if line]
        for i, line in enumerate(lines):
            if len(line) < 100 and "form 10-k" in line.lower():
                footers[footer_key(line)] += 1
            if "|" in line or len(line) >= 100 or PAGE_NUMBER.match(line):
                continue
            total[line] += 1
            neighbours = lines[max(0, i - 2): i + 3]
            if any(PAGE_NUMBER.match(n) for n in neighbours):
                near_page[line] += 1

    repeated = {line for line, n in total.items()
                if n >= cfg.repeat_limit and near_page[line] / n >= 0.5}
    form_footers = {key for key, n in footers.items() if n >= cfg.repeat_limit}
    return repeated | form_footers


def clean_lines(text, boilerplate):
    """Drop empty lines, page numbers, symbol-only fragments, and headers/footers."""
    return [line for line in text.split("\n")
            if line
            and not PAGE_NUMBER.match(line)
            and not SYMBOLS_ONLY.match(line)
            and line not in boilerplate
            and footer_key(line) not in boilerplate]


def split_long(line):
    """Break a paragraph longer than one chunk into pieces at sentence ends."""
    if len(line) <= cfg.chunk_chars:
        return [line]
    pieces, current = [], ""
    for sentence in SENTENCE_END.split(line):
        if current and len(current) + len(sentence) + 1 > cfg.chunk_chars:
            pieces.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        pieces.append(current)
    return pieces


def to_blocks(lines):
    """Group consecutive lines into ("text", lines) and ("table", rows) blocks."""
    blocks = []
    for line in lines:
        kind = "table" if " | " in line else "text"
        if blocks and blocks[-1][0] == kind:
            blocks[-1][1].append(line)
        else:
            blocks.append((kind, [line]))
    return blocks


def pack(units):
    """Join lines into chunks of about chunk_chars, repeating about overlap_chars between chunks."""
    chunks, current, size = [], [], 0
    for unit in units:
        if current and size + len(unit) > cfg.chunk_chars:
            chunks.append("\n".join(current))
            # Carry the last few lines into the next chunk as overlap
            overlap, overlap_size = [], 0
            for u in reversed(current):
                if overlap_size + len(u) > cfg.overlap_chars:
                    break
                overlap.insert(0, u)
                overlap_size += len(u) + 1
            current, size = overlap, overlap_size
        current.append(unit)
        size += len(unit) + 1
    if current:
        chunks.append("\n".join(current))
    return chunks


def merge_small(pieces):
    """Attach tiny pieces (like a table caption) to the next piece so no chunk is too small."""
    merged, carry = [], ""
    for kind, text in pieces:
        if carry:
            text = carry + "\n" + text
            carry = ""
        if len(text) < cfg.min_chars:
            carry = text
        else:
            merged.append((kind, text))
    if carry:
        if merged:
            kind, text = merged[-1]
            merged[-1] = (kind, text + "\n" + carry)
        else:
            merged.append(("text", carry))
    return merged


def chunk_section(section, boilerplate):
    """Split one section into (kind, text) pieces; tables are chunked apart from prose."""
    pieces = []
    for kind, lines in to_blocks(clean_lines(section["text"], boilerplate)):
        units = lines if kind == "table" else [p for line in lines for p in split_long(line)]
        pieces += [(kind, chunk) for chunk in pack(units)]
    return merge_small(pieces)