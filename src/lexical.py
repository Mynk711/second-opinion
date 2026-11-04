import re

# Words and numbers, keeping things like "10-k", "u.s." and "company’s" together
TOKEN = re.compile(r"[a-z0-9]+(?:[.'’-][a-z0-9]+)*")


def tokenize(text):
    """Lowercase text and split it into words for keyword search."""
    return TOKEN.findall(text.lower())