# runner.py

import logging
import datetime
from pathlib import Path
import pandas as pd
import threading
import time

from scraper.scrapers.states import SCRAPER_MAP as STATE_SCRAPERS
from scraper.scrapers.counties import SCRAPER_MAP as COUNTY_SCRAPERS
from scraper.exporters.excel_exporter import export_all
from scraper.utils.data_utils import sync_hidden_from_excel
from scraper.utils.date_utils import filter_by_dates
from scraper.utils.text_utils import sanitize
from src.config import (
    CACHE_DIR,
    DEFAULT_TIMEOUT,
    KEYWORDS_FILE,
    OUTPUT_DIR,
    MAX_RETRIES,
    MAX_CACHE_FILES,
    OUTPUT_FILE_EXTENSION,
    OUTPUT_FILENAME_PREFIX
)
from scraper.core.errors import (
    SearchTimeoutError,
    DataExtractionError,
    PaginationError,
    ScraperError,
)


# requires: states list, keywords list, optional cancel_event
# modifies: KEYWORDS_FILE, CACHE_DIR, OUTPUT_DIR
# effects: orchestrates the full scrape, returning cleaned dataframes, path, and timings
def run_scraping(
    states: list[str],
    keywords: list[str],
    counties: dict[str, list[str]] | None = None,
    cancel_event: threading.Event | None = None
) -> tuple[
    dict[str, pd.DataFrame],            # cleaned state_to_df
    dict[str, dict[str, pd.DataFrame]], # cleaned county_to_df
    Path,                               # excel file path
    dict[str, float],                   # state durations
    dict[str, dict[str, float]]         # county durations
]:
    _write_keywords(keywords)
    cancel_event = _init_cancel_event(cancel_event)
    sync_hidden_from_excel()

    state_to_df, state_durations = _scrape_states(states, cancel_event)
    county_to_df, county_durations = _scrape_counties(counties, cancel_event)
    _enforce_not_empty(state_to_df, county_to_df, cancel_event)

    _prune_old_cache()

    state_export_map  = _build_state_export_map(state_to_df)
    county_export_map = _build_county_export_map(county_to_df)

    cache_path = _write_outputs(state_export_map, county_export_map)
    return state_to_df, county_to_df, cache_path, state_durations, county_durations


# requires: writeable KEYWORDS_FILE path
# modifies: KEYWORDS_FILE
# effects: persists the provided keywords to disk
def _write_keywords(keywords: list[str]) -> None:
    KEYWORDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(KEYWORDS_FILE, "w", encoding="utf-8") as kw_file:
        for kw in keywords:
            kw_file.write(f"{kw}\n")
    logging.info(f"Wrote {len(keywords)} keyword(s) to {KEYWORDS_FILE}")


# effects: returns a valid cancel_event
def _init_cancel_event(cancel_event: threading.Event | None) -> threading.Event:
    return cancel_event or threading.Event()


# requires: list of state keys, cancel_event
# effects: runs each state scraper, cleans results, returns state→DataFrame and durations
def _scrape_states(
    states: list[str], cancel_event: threading.Event
) -> tuple[dict[str, pd.DataFrame], dict[str, float]]:
    state_to_df: dict[str, pd.DataFrame] = {}
    state_durations: dict[str, float] = {}
    for state in states:
        if cancel_event.is_set():
            logging.info(f"Cancellation before state [{state}]")
            break
        logging.info(f"[{state}] Starting scrape...")
        df, elapsed = _run_single_scraper(state, STATE_SCRAPERS, cancel_event)
        cleaned = _clean_dataframe(df)
        state_to_df[state] = cleaned
        state_durations[state] = elapsed
    return state_to_df, state_durations


# requires: mapping of state→counties or None, cancel_event
# effects: runs each county scraper, cleans results, returns key->DataFrame and durations
def _scrape_counties(
    counties: dict[str, list[str]] | None, cancel_event: threading.Event
) -> tuple[dict[str, dict[str, pd.DataFrame]], dict[str, dict[str, float]]]:
    county_to_df: dict[str, dict[str, pd.DataFrame]] = {}
    county_durations: dict[str, dict[str, float]] = {}
    if not counties:
        return {}, {}

    for state, county_list in counties.items():
        scraper_map = COUNTY_SCRAPERS.get(state, {})
        county_to_df[state] = {}
        county_durations[state] = {}
        for county in county_list:
            if cancel_event.is_set():
                logging.info(f"Cancellation before county [{county}]")
                break

            logging.info(f"[{county}] Starting scrape...")

            scraper_cls = scraper_map.get(county)
            if not scraper_cls:
                logging.error(f"No county scraper for [{county}]")
                continue

            df, elapsed = _run_single_scraper(county, scraper_map, cancel_event)
            cleaned = _clean_dataframe(df)
            county_to_df[state][county] = cleaned
            county_durations[state][county] = elapsed
    return county_to_df, county_durations


# requires: DataFrame possibly with 'success' column
# effects: returns sanitized, deduplicated, date‐filtered DataFrame
def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df2 = df.drop_duplicates().copy()
    for col in df2.select_dtypes(include='object').columns:
        df2[col] = df2[col].apply(sanitize)
    if 'end_date' in df2.columns:
        df2 = filter_by_dates(df2)
    return df2


# requires: state/county data, cancel_event
# effects: raises RuntimeError if canceled or no data scraped
def _enforce_not_empty(
    state_to_df: dict[str, pd.DataFrame],
    county_to_df: dict[str, dict[str, pd.DataFrame]],
    cancel_event: threading.Event
) -> None:
    if cancel_event.is_set():
        raise RuntimeError("Scrape was canceled by user.")
    if not state_to_df and not county_to_df:
        raise RuntimeError("No records scraped for any state or county.")


# requires: CACHE_DIR exists
# modifies: deletes old .xlsx files in CACHE_DIR
# effects: keeps only 5 most recent cache files
def _prune_old_cache() -> None:
    all_files = sorted(
        [p for p in CACHE_DIR.iterdir() if p.suffix.lower() == OUTPUT_FILE_EXTENSION],
        key=lambda p: p.stat().st_mtime
    )
    if len(all_files) < MAX_CACHE_FILES:
        return
    for old in all_files[:-MAX_CACHE_FILES]:
        try:
            old.unlink()
            logging.info(f"Deleted old cache file: {old.name}")
        except Exception as e:
            logging.warning(f"Failed to delete {old.name}: {e}")


# requires: cleaned state_to_df with possible 'success' column
# effects: returns non-empty, non-placeholder state DataFrames
def _build_state_export_map(state_to_df: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    def should_export(df: pd.DataFrame) -> bool:
        if "success" in df.columns:
            placeholder = (
                df.shape[0] == 1 and
                df["success"].iat[0] and
                df.drop(columns=["success"]).iloc[0].isna().all()
            )
            return not placeholder
        return False
    
    export_map: dict[str, pd.DataFrame] = {}
    for state, df in state_to_df.items():
        if should_export(df):
            export_map[state] = df
        else:
            logging.info(f"Skipping export for empty results of [{state}]")
    return export_map


# requires: cleaned county_to_df with possible 'success' columns
# effects: returns nested dict[state][county] of non-placeholder DataFrames
def _build_county_export_map(
    county_to_df: dict[str, dict[str, pd.DataFrame]]
) -> dict[str, dict[str, pd.DataFrame]]:
    def should_export(df: pd.DataFrame) -> bool:
        if "success" in df.columns:
            placeholder = (
                df.shape[0] == 1
                and df["success"].iat[0]
                and df.drop(columns=["success"]).iloc[0].isna().all()
            )
            return not placeholder
        return False

    export_map: dict[str, dict[str, pd.DataFrame]] = {}
    for state, county_dict in county_to_df.items():
        for county, df in county_dict.items():
            if should_export(df):
                export_map.setdefault(state, {})[county] = df
            else:
                logging.info(f"Skipping export for empty results of [{county}, {state}]")
    return export_map


# modifies: writes timestamped and latest Excel files
# effects: returns the Path to the timestamped cache file
def _write_outputs(
    state_map: dict[str, pd.DataFrame],
    county_map: dict[str, dict[str, pd.DataFrame]]
) -> Path:
    now = datetime.datetime.now()
    ts = now.strftime("%Y%m%d_%H%M%S")
    cache_path = CACHE_DIR / f"{OUTPUT_FILENAME_PREFIX}{ts}{OUTPUT_FILE_EXTENSION}"

    if state_map or county_map:
        with pd.ExcelWriter(cache_path, engine="xlsxwriter") as writer:
            export_all(state_map, county_map, writer)
        logging.info(f"Saved new cache file: {cache_path.name}")

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        desktop_path = OUTPUT_DIR / f"{OUTPUT_FILENAME_PREFIX}{OUTPUT_FILE_EXTENSION}"
        with pd.ExcelWriter(desktop_path, engine="xlsxwriter") as writer:
            export_all(state_map, county_map, writer)
        logging.info(f"Saved new desktop file: {desktop_path.name}")

    return cache_path


# requires: scraper_map contains str of only state names and type is a core scraper type
# effects: runs the scraper for the given state
def _run_single_scraper(
    key: str,
    scraper_map: dict[str, type],
    cancel_event: threading.Event
) -> tuple[pd.DataFrame, float]:
    start = time.perf_counter()
    records: list[dict] = []
    success = False

    for attempt in range(1, MAX_RETRIES + 1):
        if cancel_event.is_set():
            break
        scraper_cls = scraper_map.get(key)
        if not scraper_cls:
            logging.error(f"No scraper for key [{key}]")
            break
        scraper = scraper_cls()
        try:
            records = scraper.scrape(timeout=DEFAULT_TIMEOUT)
            success = True
            break
        except (SearchTimeoutError, PaginationError, ScraperError) as retryable:
            logging.warning(f"[{key}] retryable error on attempt {attempt}: {retryable}")
        except DataExtractionError as de:
            logging.error(f"[{key}] unrecoverable data error: {de}")
            break
        finally:
            scraper.close()

    if not success:
        df = pd.DataFrame([{
            'title': None, 'code': None, 'end_date': None,
            'Keyword Hits': None, 'link': None, 'success': False
        }])
    else:
        df = pd.DataFrame(records) if records else pd.DataFrame([{
            'title': None, 'code': None, 'end_date': None,
            'Keyword Hits': None, 'link': None, 'success': True
        }])
        df['success'] = True

    elapsed = time.perf_counter() - start
    return df, elapsed
