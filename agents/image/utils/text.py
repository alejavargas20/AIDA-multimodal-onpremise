import re

_whitespace_re = re.compile(r"[ \t]+")
_newlines_re = re.compile(r"\n{3,}")

def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _whitespace_re.sub(" ", text)
    text = _newlines_re.sub("\n\n", text)
    return text.strip()

