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
    # Keep letters/digits + Polish chars. Split on whitespace.
    phrase = phrase.strip()
    if not phrase:
        return []
    # normalize multiple spaces
    phrase = re.sub(r"\s+", " ", phrase)
    return phrase.split(" ")


def _stem_like(token: str) -> str:
    """
    Heuristic "stem": take prefix to match inflections.
    - For short tokens keep whole token
    - For longer tokens use prefix length 4-6 (balanced to reduce false positives)
    """
    t = token.strip()
    if len(t) <= 3:
        return t
    if len(t) <= 6:
        return t[:4]
    return t[:5]


def build_fuzzy_regex(phrase: str) -> str:
    """
    Build a fuzzy regex that matches phrase words with inflections:
    each token is matched as: <prefix>\w*
    tokens separated by any whitespace / punctuation
    """
    tokens = _tokenize_phrase(phrase)
    if not tokens:
        return r"^$"

    parts = []
    for tok in tokens:
        # escape token prefix safely
        pref = re.escape(_stem_like(tok).lower())
        # allow word chars continuation for inflection
        parts.append(rf"{pref}\w*")

    # allow separators: whitespace or punctuation between tokens
    sep = r"(?:[\s\.,;:\-\(\)\[\]\"'„”/]+)"
    pattern = sep.join(parts)

    # word boundary-ish (avoid matching inside longer strings too aggressively)
    # still allow Polish letters with \w
    return rf"(?i)(?<!\w){pattern}(?!\w)"


def count_phrase_fuzzy(text: str, phrase: str) -> Tuple[int, str]:
    """
    Count occurrences using fuzzy regex.
    Returns (count, pattern_used)
    """
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
        # fallback: simple literal contains
        return text.lower().count(phrase.lower()), re.escape(phrase)


def validate_keywords(text: str, phrases: List[str]) -> List[KeywordHit]:
    out: List[KeywordHit] = []
    for p in phrases:
        c, pat = count_phrase_fuzzy(text, p)
        out.append(KeywordHit(phrase=p, count=c, found=c > 0, pattern=pat))
    return out
