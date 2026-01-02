import re
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class KeywordHit:
    phrase: str
    count: int
    found: bool
    pattern: str

def _tokenize_phrase(phrase: str) -> List[str]:
    phrase = re.sub(r"\s+", " ", (phrase or "").strip())
    return phrase.split(" ") if phrase else []

def _stem_like(token: str) -> str:
    t = (token or "").strip()
    if len(t) <= 3:
        return t
    if len(t) <= 6:
        return t[:4]
    return t[:5]

def build_fuzzy_regex(phrase: str) -> str:
    tokens = _tokenize_phrase(phrase)
    if not tokens:
        return r"^$"
    parts = []
    for tok in tokens:
        pref = re.escape(_stem_like(tok).lower())
        parts.append(rf"{pref}\w*")
    sep = r"(?:[\s\.,;:\-\(\)\[\]\"'„”/]+)"
    pattern = sep.join(parts)
    return rf"(?i)(?<!\w){pattern}(?!\w)"

def count_phrase_fuzzy(text: str, phrase: str) -> Tuple[int, str]:
    if not text:
        return 0, ""
    phrase = (phrase or "").strip()
    if not phrase:
        return 0, ""
    pattern = build_fuzzy_regex(phrase)
    try:
        matches = list(re.finditer(pattern, text, flags=re.IGNORECASE))
        return len(matches), pattern
    except re.error:
        return text.lower().count(phrase.lower()), re.escape(phrase)

def validate_keywords(text: str, phrases: List[str]) -> List[KeywordHit]:
    out: List[KeywordHit] = []
    for p in phrases:
        c, pat = count_phrase_fuzzy(text, p)
        out.append(KeywordHit(phrase=p, count=c, found=c > 0, pattern=pat))
    return out
