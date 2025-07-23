# data_utils.py

import zipfile
import pandas as pd
import json
from pathlib import Path

from src.config import KEYWORDS_FILE, HIDDEN_IDS_FILE, OUTPUT_DIR, CACHE_DIR, ASSETS_DIR, PERSISTENCE_DIR

# effects: loads and returns a set of hidden solicitation ids from a json file, or an empty set if the file is not found or invalid
def load_hidden_ids() -> set[str]:
    try:
        return set(json.loads(Path(HIDDEN_IDS_FILE).read_text(encoding='utf-8')))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


# requires: df is a pandas DataFrame
# effects: filters the DataFrame based on hidden ids and keyword hits, returns a new DataFrame with filtered and sorted records
def filter_by_keywords(df: pd.DataFrame) -> pd.DataFrame:
    try:
        with open(KEYWORDS_FILE, 'r', encoding='utf-8') as f:
            keywords = [line.strip().lower() for line in f if line.strip()]
    except FileNotFoundError:
        return df

    if df.empty:
        return pd.DataFrame()
    
    if not keywords:
        df = df.copy()
        df['Keyword Hits'] = 0
        return df.reset_index(drop=True)

    hits = []
    for idx, row in df[df['title'].notna()].iterrows():
        text = row['title'].lower()
        count = sum(text.count(kw) for kw in keywords)
        if count:
            hits.append((idx, count))
    if not hits:
        return pd.DataFrame()

    indices, counts = zip(*hits)
    filtered = df.loc[list(indices)].copy().reset_index(drop=True)
    filtered['Keyword Hits'] = list(counts)
    return filtered.sort_values(by='Keyword Hits', ascending=False).reset_index(drop=True)


# requires: excel_path is a Path object pointing to an excel file
# modifies: the hidden ids json file
# effects: reads the excel file, extracts hidden solicitation ids, and updates the hidden ids json file with the union of existing and new hidden ids
def sync_hidden_from_excel(
    excel_path: Path = OUTPUT_DIR / "rfp_scraping_output.xlsx"
) -> None:
    path = Path(HIDDEN_IDS_FILE)
    try:
        existing = set(json.loads(path.read_text(encoding='utf-8')))
    except (FileNotFoundError, json.JSONDecodeError):
        existing = set()

    try:
        df = pd.read_excel(excel_path, header=None, sheet_name=0, engine="openpyxl")
    except (FileNotFoundError, PermissionError):
        return

    try:
        data = df.iloc[1:, [0, 3]].copy()
        data.columns = ['Hide', 'Solicitation#']
    except IndexError:
        return

    newly = set(data.loc[data['Hide'] == True, 'Solicitation#'].astype(str).tolist())

    all_ids = sorted(existing.union(newly))
    path.write_text(json.dumps(all_ids, indent=2), encoding='utf-8')


# requires: df is a pandas DataFrame
# effects: returns a tuple of (visible, hidden) DataFrames
#   visible: rows matching filter_by_keywords AND not manually hidden
#   hidden: all other rows (manually hidden or no keyword hits)
def split_by_keywords(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    kw_visible = filter_by_keywords(df)

    hidden_ids = load_hidden_ids()

    code_col = 'code'
    visible = kw_visible.loc[
        ~kw_visible[code_col].astype(str).isin(hidden_ids)
    ].reset_index(drop=True)

    manual_mask = df[code_col].astype(str).isin(hidden_ids)

    dropped_idx = df.index.difference(kw_visible.index)

    hidden_mask = manual_mask.copy()
    hidden_mask.loc[dropped_idx] = True

    hidden = df.loc[hidden_mask].reset_index(drop=True)

    return visible, hidden


# requires: 
# modifies: filesystem (may create directories)
# effects: ensures necessary output/cache directories exist
def ensure_dirs_exist():
    for d in (ASSETS_DIR, OUTPUT_DIR, CACHE_DIR, PERSISTENCE_DIR):
        d.mkdir(parents=True, exist_ok=True)


# requires: keywords.txt exists at KEYWORDS_FILE
# effects: returns a list of non-empty, stripped keyword strings
def load_keywords() -> list[str]:
    if not KEYWORDS_FILE.exists():
        raise FileNotFoundError(f"Missing keywords.txt at {KEYWORDS_FILE}")
    with open(KEYWORDS_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]