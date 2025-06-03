# main.py

import argparse
import os
import shutil
import logging
import datetime
from pathlib import Path

from src.config import ensure_dirs_exist, LOG_FILE
from scraper.logging_config import configure_logging
from scraper.runner import run_scraping
from scraper.scrapers import SCRAPER_MAP

def main():
    # ensure output/, cache/, persistence/ all exist
    ensure_dirs_exist()

    # log separation (blank line)
    with open(LOG_FILE, "a"):
        pass

    # configure logging to go into LOG_FILE
    configure_logging(LOG_FILE)
    logging.info("=" * 80)
    logging.info(f"Starting scraper run at {datetime.datetime.now().isoformat()}")
    logging.info("=" * 80)

    # parse CLI arguments
    parser = argparse.ArgumentParser(description="Run multiple RFP scrapers")
    parser.add_argument(
        "--states",
        nargs="+",
        required=True,
        help="Which states to scrape, or 'all'",
    )
    args = parser.parse_args()

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

    # call run_scraping (no cancel_event passed here)
    try:
        cache_path = run_scraping(to_run)
    except Exception as e:
        logging.error(f"run_scraping failed: {e}")
        return

    # copy the resulting .xlsx to Desktop
    desktop = Path.home() / "Desktop"
    if not desktop.is_dir():
        logging.warning(f"Desktop not found at {desktop}; skipping copy.")
    else:
        dest = desktop / "rfp_scraping_output.xlsx"
        try:
            shutil.copy2(cache_path, dest)
            logging.info(f"Copied latest output to {dest}")
            try:
                os.startfile(dest)
            except Exception:
                pass
        except Exception as e:
            logging.warning(f"Failed to copy to Desktop: {e}")

    logging.info("Scraper run complete.")

if __name__ == "__main__":
    main()
