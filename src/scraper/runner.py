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
from src.config import CACHE_DIR, DEFAULT_TIMEOUT, KEYWORDS_FILE, OUTPUT_DIR

from scraper.core.errors import (
    SearchTimeoutError,
    DataExtractionError,
    PaginationError,
    ScraperError,
)


# requires: states list, keywords list, optional cancel_event
# modifies: KEYWORDS_FILE, CACHE_DIR, OUTPUT_DIR
# effects: orchestrates the full scrape, returning dataframes, path, and timings
def run_scraping(
    states: list[str],
    keywords: list[str],
    counties: dict[str, list[str]] | None = None,
    cancel_event: threading.Event | None = None
) -> tuple[
    dict[str, pd.DataFrame],  # state_to_df
    dict[str, pd.DataFrame],  # county_to_df
    Path,                     # excel file path
    dict[str, float],         # state durations
    dict[str, float]          # county durations
]:
    _write_keywords(keywords)
    cancel_event = _init_cancel_event(cancel_event)
    sync_hidden_from_excel()

    state_to_df, state_durations = _scrape_states(states, cancel_event)
    county_to_df, county_durations = _scrape_counties(counties, cancel_event)
    _enforce_not_empty(state_to_df, county_to_df, cancel_event)

    _prune_old_cache()
    export_map = _build_export_map(state_to_df, county_to_df)
    cache_path = _write_outputs(export_map)

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
# effects: runs each state scraper, returns state→DataFrame and durations
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
        state_to_df[state] = df
        state_durations[state] = elapsed
    return state_to_df, state_durations


# requires: mapping of state→counties or None, cancel_event
# modifies: none
# effects: runs each county scraper, returns key→DataFrame and durations
def _scrape_counties(
    counties: dict[str, list[str]] | None, cancel_event: threading.Event
) -> tuple[dict[str, pd.DataFrame], dict[str, float]]:
    county_to_df: dict[str, pd.DataFrame] = {}
    county_durations: dict[str, float] = {}
    if not counties:
        return county_to_df, county_durations
    for state, county_list in counties.items():
        for county in county_list:
            key = f"{state}:{county}"
            if cancel_event.is_set():
                logging.info(f"Cancellation before county [{key}]")
                break
            logging.info(f"[{key}] Starting scrape...")
            df, elapsed = _run_single_scraper(county, COUNTY_SCRAPERS.get(state, {}), cancel_event)
            county_to_df[key] = df
            county_durations[key] = elapsed
    return county_to_df, county_durations


# requires: state/county data, cancel_event
# effects: raises RuntimeError if canceled or no data scraped
def _enforce_not_empty(
    state_to_df: dict[str, pd.DataFrame],
    county_to_df: dict[str, pd.DataFrame],
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
        [p for p in CACHE_DIR.iterdir() if p.suffix.lower() == ".xlsx"],
        key=lambda p: p.stat().st_mtime
    )
    if len(all_files) < 5:
        return
    for old in all_files[:-5]:
        try:
            old.unlink()
            logging.info(f"Deleted old cache file: {old.name}")
        except Exception as e:
            logging.warning(f"Failed to delete {old.name}: {e}")


# requires: dataframes with 'success' column
# effects: returns only non-empty, non-placeholder sheets
def _build_export_map(
    state_to_df: dict[str, pd.DataFrame],
    county_to_df: dict[str, pd.DataFrame]
) -> dict[str, pd.DataFrame]:
    def should_export(df: pd.DataFrame) -> bool:
        if 'success' in df.columns:
            placeholder = (
                df.shape[0] == 1 and
                df['success'].iat[0] and
                df.drop(columns=['success']).isna().all().item()
            )
            return not placeholder
        return True

    export_map: dict[str, pd.DataFrame] = {}
    for name, df in {**state_to_df, **county_to_df}.items():
        if should_export(df):
            export_map[name] = df
        else:
            logging.info(f"Skipping export for empty results of [{name}]")
    return export_map


# requires: export_map of DataFrames
# modifies: writes timestamped and latest Excel files
# effects: returns the Path to the timestamped cache file
def _write_outputs(export_map: dict[str, pd.DataFrame]) -> Path:
    now = datetime.datetime.now()
    ts = now.strftime("%Y%m%d_%H%M%S")
    cache_path = CACHE_DIR / f"rfp_scraping_output_{ts}.xlsx"

    if export_map:
        with pd.ExcelWriter(cache_path, engine="xlsxwriter") as writer:
            export_all(export_map, writer)
        logging.info(f"Saved new cache file: {cache_path.name}")

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        desktop_path = OUTPUT_DIR / "rfp_scraping_output.xlsx"
        with pd.ExcelWriter(desktop_path, engine="xlsxwriter") as writer:
            export_all(export_map, writer)
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

    for attempt in range(1, 4):
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
    print(df)
    return df, elapsed