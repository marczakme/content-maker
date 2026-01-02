import os, json
import pandas as pd
from datetime import datetime

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

GUIDELINES_PATH = os.path.join(DATA_DIR, "guidelines.json")
OUTLINE_PATH = os.path.join(DATA_DIR, "outline.json")
KEYWORDS_PATH = os.path.join(DATA_DIR, "keywords.csv")
GENERATED_DIR = os.path.join(DATA_DIR, "generated")
REPORTS_DIR = os.path.join(DATA_DIR, "reports")

os.makedirs(GENERATED_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

def _utc_now():
    return datetime.utcnow().isoformat() + "Z"

def read_json(path: str, default: dict) -> dict:
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def write_json(path: str, payload: dict) -> None:
    payload = dict(payload)
    payload["_updated_at"] = _utc_now()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

def guidelines_get() -> dict:
    return read_json(GUIDELINES_PATH, {"prompt": "", "_updated_at": None})

def guidelines_set(prompt: str) -> None:
    write_json(GUIDELINES_PATH, {"prompt": prompt})

def outline_get() -> dict:
    return read_json(OUTLINE_PATH, {"outline": "", "_updated_at": None})

def outline_set(outline: str) -> None:
    write_json(OUTLINE_PATH, {"outline": outline})

def read_keywords() -> pd.DataFrame:
    if not os.path.exists(KEYWORDS_PATH):
        return pd.DataFrame(columns=["phrase"])
    df = pd.read_csv(KEYWORDS_PATH)
    if "phrase" not in df.columns:
        df["phrase"] = ""
    df["phrase"] = df["phrase"].astype(str).str.strip()
    df = df[df["phrase"].str.len() > 0].drop_duplicates(subset=["phrase"]).reset_index(drop=True)
    return df[["phrase"]]

def write_keywords(phrases: list[str]) -> None:
    # unique, keep order
    seen = set()
    out = []
    for p in phrases:
        s = (p or "").strip()
        if not s:
            continue
        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    pd.DataFrame({"phrase": out}).to_csv(KEYWORDS_PATH, index=False)

def get_last_modified(path: str) -> str | None:
    if not os.path.exists(path):
        return None
    return datetime.utcfromtimestamp(os.path.getmtime(path)).isoformat() + "Z"
