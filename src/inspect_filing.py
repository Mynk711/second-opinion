import re
import sys
from pathlib import Path
import warnings
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

# 10-K files are XHTML; we use the lenient HTML parser on purpose, so silence this warning
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

path = Path(sys.argv[1])
soup = BeautifulSoup(path.read_bytes(), "lxml")

# Remove things a reader never sees: scripts, styles, and hidden XBRL blocks
for tag in soup.find_all(["script", "style"]):
    tag.decompose()
for tag in soup.find_all(style=re.compile(r"display:\s*none")):
    tag.decompose()

text = soup.get_text("\n")
text = text.replace("\xa0", " ")           # non-breaking spaces -> normal spaces
text = re.sub(r"\n\s*\n+", "\n\n", text)   # collapse runs of blank lines

print(f"Characters: {len(text):,}  (~{len(text) // 4:,} tokens)")

# Where do the main sections start? Each heading usually appears twice:
# once in the table of contents, once where the section really begins.
print("\nSection headings found:")
for match in re.finditer(r"\n\s*(item\s+(1a|1b|1|7a|7|8)\b\.?)", text, flags=re.IGNORECASE):
    print(f"  {match.group(1).strip():<10} at position {match.start():>9,}")

print("\n--- Sample text ---\n")
print(text[30000:31500])