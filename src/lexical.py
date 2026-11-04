import re

import snowballstemmer

# Words and numbers, keeping things like "10-k", "u.s." and "company’s" together
TOKEN = re.compile(r"[a-z0-9]+(?:[.'’-][a-z0-9]+)*")

# Reduces words to a common root: "revenues" and "revenue" both become "revenu"
_stemmer = snowballstemmer.stemmer("english")


def tokenize(text):
    """Lowercase text, split it into words, and stem each word for keyword search."""
    return _stemmer.stemWords(TOKEN.findall(text.lower()))