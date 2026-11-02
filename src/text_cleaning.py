import re
import warnings
from pathlib import Path

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

# 10-K files are XHTML; we use the lenient HTML parser on purpose, so silence this warning
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# Tags that start a new line on the page. Inline tags (span, b, a) stay within the sentence.
BLOCK_TAGS = ["p", "div", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6", "table"]


def html_to_text(path):
    """Turn a 10-K HTML file into clean plain text, keeping paragraph breaks."""
    soup = BeautifulSoup(Path(path).read_bytes(), "lxml")

    # Remove things a reader never sees: scripts, styles, and hidden XBRL blocks
    for tag in soup.find_all(["script", "style"]):
        tag.decompose()
    for tag in soup.find_all(style=re.compile(r"display:\s*none")):
        tag.decompose()

    # Line breaks only where the page really breaks lines
    for br in soup.find_all("br"):
        br.replace_with("\n")

    # Separate table cells with " | " so numbers in a row don't stick together
    for cell in soup.find_all(["td", "th"]):
        cell.append(" | ")

    for tag in soup.find_all(BLOCK_TAGS):
        tag.append("\n")

    text = soup.get_text()                     # no separator: inline tags join naturally
    text = text.replace("\xa0", " ")           # non-breaking spaces -> normal spaces
    text = re.sub(r"[ \t]+", " ", text)        # many spaces or tabs -> one space

    lines = []
    for line in text.split("\n"):
        line = re.sub(r"(\s*\|\s*)+", " | ", line)  # empty cells: "| | |" -> one "|"
        lines.append(line.strip(" |"))             # drop pipes and spaces at line ends
    text = "\n".join(lines)
    text = re.sub(r"\$ \| ", "$", text)   # "$ | 178,353" -> "$178,353"
    text = re.sub(r" \| %", "%", text)    # "7 | %" -> "7%"

    text = re.sub(r"\n{3,}", "\n\n", text)     # runs of blank lines -> one blank line
    return text.strip()