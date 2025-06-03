# main.py

# standard library imports
import argparse
import datetime
import os
import logging
import shutil

# third-party imports
import pandas as pd

# project imports
from scraper.scrapers import SCRAPER_MAP
from scraper.exporters.excel_exporter import export_all
from scraper.utils.data_utils import sync_hidden_from_excel
from scraper.logging_config import configure_logging

def main():
    # ensure output directory exists (for logs & cache)
    output_dir = "./output"
    os.makedirs(output_dir, exist_ok=True)

    # create (or ensure) cache subfolder
    cache_dir = os.path.join(output_dir, "cache")
    os.makedirs(cache_dir, exist_ok=True)

    # separate log sessions
    log_file = os.path.join(output_dir, "scraper.log")
    with open(log_file, 'a') as f:
        f.write("\n")

    # suppress WDM and TF logs
    os.environ['WDM_LOG'] = "0"
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = "3"

    # sync hidden RFPs
    sync_hidden_from_excel()

    # configure logging
    configure_logging(log_file)
    logging.info("=" * 80)
    logging.info(f"Starting scraper run at {datetime.datetime.now().isoformat()}")
    logging.info("=" * 80)

    # parse command-line args
    parser = argparse.ArgumentParser(description="Run multiple scrapers")
    parser.add_argument(
        "--states",
        nargs="+",
        required=True,
        help="States to scrape, or 'all'"
    )
    args = parser.parse_args()

    # determine which scrapers to run
    requested = [s.lower() for s in args.states]
    if "all" in requested:
        to_run = list(SCRAPER_MAP.keys())
    else:
        to_run = [s for s in requested if s in SCRAPER_MAP]
        bad = [s for s in requested if s not in SCRAPER_MAP]
        if bad:
            logging.error(f"No scraper(s) found for: {bad}")
    if not to_run:
        return

    # determine the “Desktop” location for writing latest output
    desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
    if not os.path.isdir(desktop_dir):
        logging.warning(f"Could not find Desktop folder at {desktop_dir}. Falling back to current directory.")
        desktop_dir = os.getcwd()
    desktop_path = os.path.join(desktop_dir, "rfp_scraping_output.xlsx")

    # before writing the new file, enforce cache-size limit (keep only the latest 5)
    existing_files = [
        os.path.join(cache_dir, f)
        for f in os.listdir(cache_dir)
        if f.lower().endswith(".xlsx")
    ]
    # if there are already 5 or more files, delete the single oldest one
    if len(existing_files) >= 5:
        oldest = min(existing_files, key=lambda p: os.path.getmtime(p))
        try:
            os.remove(oldest)
            logging.info(f"Removed oldest cache file: {oldest}")
        except Exception as e:
            logging.warning(f"Could not delete oldest cache file {oldest}: {e}")

    # build a timestamped filename for the new cache file
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    cache_filename = f"rfp_scraping_output_{timestamp}.xlsx"
    cache_path = os.path.join(cache_dir, cache_filename)

    # run each scraper and collect DataFrames
    state_to_df_map = {}
    for state in to_run:
        logging.info(f"[{state}] Instantiating and scraping (up to 3 attempts)")
        records = []
        success = False

        # retry loop: instantiate a fresh scraper each attempt
        for attempt in range(1, 4):
            scraper = SCRAPER_MAP[state]()
            try:
                scraped = scraper.scrape()
                # if scrape() returns normally, mark success
                records = scraped
                success = True
                break
            except Exception as e:
                logging.error(f"[{state}] attempt {attempt} failed: {e}")
                if attempt < 3:
                    logging.info(f"[{state}] retrying (attempt {attempt + 1}) …")
                else:
                    logging.error(f"[{state}] All 3 attempts failed; moving on with empty results")
            finally:
                logging.info("Closing scraper")
                scraper.close()

        # convert results (possibly empty) into a DataFrame
        df = pd.DataFrame(records)
        if df.empty:
            logging.info(f"[{state}] No records found")
            continue
        logging.info(f"[{state}] Scraped {len(df)} records")
        state_to_df_map[state] = df

    if not state_to_df_map:
        logging.info("No records scraped for any state; exiting.")
        return

    # write the new output to cache (timestamped file)
    try:
        with pd.ExcelWriter(cache_path, engine="xlsxwriter") as writer:
            export_all(state_to_df_map, writer)
    except Exception as e:
        logging.error(f"Failed to write Excel to cache ({cache_path}): {e}")
        return

    logging.info(f"Cached new output: {cache_path}")

    # copy the fresh cache file to Desktop as a fixed filename
    try:
        shutil.copy2(cache_path, desktop_path)
        logging.info(f"Copied latest output to desktop: {desktop_path}")
    except Exception as e:
        logging.warning(f"Could not copy to desktop ({desktop_path}): {e}")

    # log out the current cache contents in chronological order
    all_cached = [
        os.path.join(cache_dir, f)
        for f in os.listdir(cache_dir)
        if f.lower().endswith(".xlsx")
    ]
    # sort by modification time (oldest first)
    all_cached.sort(key=lambda p: os.path.getmtime(p))
    logging.info("Current cache files (oldest -> newest):")
    for idx, path in enumerate(all_cached, start=1):
        mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(path))
        logging.info(f"  {idx}. {os.path.basename(path)} (modified: {mod_time.isoformat()})")

    # optionally attempt to open the Desktop file (Windows)
    try:
        os.startfile(os.path.abspath(desktop_path))
    except Exception as e:
        logging.warning(f"Could not open the Desktop file automatically: {e}")

if __name__ == "__main__":
    main()
