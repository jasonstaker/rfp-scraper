# maine.py
# url: https://www.maine.gov/dafs/bbm/procurementservices/vendors/rfps

import logging
import pandas as pd
from bs4 import BeautifulSoup
import requests

from scraper.core.requests_scraper import RequestsScraper
from scraper.utils.data_utils import filter_by_keywords
from scraper.config.settings import STATE_RFP_URL_MAP

from scraper.core.errors import (
    SearchTimeoutError,
    DataExtractionError,
    ScraperError,
)

# a scraper for Maine RFP data using Requests
class MaineScraper(RequestsScraper):

    # modifies: self
    # effects: initializes scraper with Maine RFP URL and configures session headers
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP.get("maine"))
        self.logger = logging.getLogger(__name__)
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })


    # effects: GETs the main page, parses the RFP table into DataFrame or raises
    def search(self, **kwargs):
        self.logger.info("Fetching Maine RFP HTML page")
        try:
            resp = self.session.get(self.base_url, timeout=20)
            resp.raise_for_status()
        except requests.exceptions.RequestException as re:
            self.logger.error(f"search HTTP error: {re}", exc_info=False)
            raise SearchTimeoutError("Maine search HTTP error") from re

        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table", id="datatable")
        if not table:
            self.logger.error("RFP table not found in HTML")
            raise DataExtractionError("Maine datatable missing")

        tbody = table.find("tbody") or table
        rows = tbody.find_all("tr")

        records = []
        for row in rows:
            try:
                cols = row.find_all("td")
                if len(cols) < 6:
                    continue
                a = cols[0].find("a", href=True)
                title = a.get_text(strip=True) if a else ""
                link = f"https://www.maine.gov{a['href']}" if a else self.base_url
                code = cols[1].get_text(strip=True)
                due_date_tag = cols[5].find("time")
                due_date = due_date_tag.get_text(strip=True) if due_date_tag else cols[5].get_text(strip=True)
                records.append({
                    "title": title,
                    "code": code,
                    "end_date": due_date,
                    "link": link,
                })
            except Exception as e:
                self.logger.warning(f"Failed to parse row: {e}")
                continue

        df = pd.DataFrame(records)
        self.logger.info(f"Parsed {len(df)} RFP records from Maine table")
        return df


    # effects: wraps search + filter_by_keywords; returns final list or raises
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Maine via HTML table")
        try:
            df = self.search(**kwargs)
        except (SearchTimeoutError, DataExtractionError):
            raise
        except Exception as e:
            self.logger.error(f"Maine search failed: {e}", exc_info=True)
            raise ScraperError("Maine search failed") from e

        try:
            self.logger.info(f"Total raw records before filtering: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total records after filtering: {len(filtered)}")
            return filtered.to_dict("records")
        except Exception as e:
            self.logger.error(f"Maine scrape failed: {e}", exc_info=True)
            raise ScraperError("Maine scrape failed") from e
