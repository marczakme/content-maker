import os, json
import pandas as pd
from datetime import datetime

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

GUIDELINES_PATH = os.path.join(DATA_DIR, "guidelines.json")
OUTLINE_PATH = os.path.join(DATA_DIR, "outline.json")
KEYWORDS_PATH = os.path.join(DATA_DIR, "keywords.csv")
GENERATED_DIR = os.path.join(DATA_DIR, "generated")
os.makedirs(GENERATED_DIR, exist_ok=True)

def read_json(path: str, default: dict) -> dict:
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def write_json(path: str, payload: dict) -> None:
    payload = dict(payload)
    payload["_updated_at"] = datetime.utcnow().isoformat() + "Z"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

def read_keywords() -> pd.DataFrame:
    if not os.path.exists(KEYWORDS_PATH):
        return pd.DataFrame(columns=["phrase", "target_count", "notes"])
    df = pd.read_csv(KEYWORDS_PATH)
    for col in ["phrase", "target_count", "notes"]:
        if col not in df.columns:
            df[col] = "" if col != "target_count" else 0
    df["phrase"] = df["phrase"].astype(str).str.strip()
    df["target_count"] = pd.to_numeric(df["target_count"], errors="coerce").fillna(0).astype(int)
    df["notes"] = df["notes"].astype(str)
    df = df[df["phrase"].str.len() > 0].copy()
    return df.reset_index(drop=True)

def write_keywords(df: pd.DataFrame) -> None:
    df.to_csv(KEYWORDS_PATH, index=False)

def guidelines_get() -> dict:
    return read_json(GUIDELINES_PATH, {"prompt": ""})

def guidelines_set(prompt: str) -> None:
    write_json(GUIDELINES_PATH, {"prompt": prompt})

def outline_get() -> dict:
    return read_json(OUTLINE_PATH, {"outline": ""})

def outline_set(outline: str) -> None:
    write_json(OUTLINE_PATH, {"outline": outline})
