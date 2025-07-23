# nebraska.py
# url: https://das.nebraska.gov/materiel/bid-opportunities.html

import logging
from urllib.parse import urljoin

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

# a scraper for Nebraska RFP data using Requests
class NebraskaScraper(RequestsScraper):

    # modifies: self
    # effects: initialize with base URL and logger
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP["nebraska"])
        self.logger = logging.getLogger(__name__)
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": STATE_RFP_URL_MAP["nebraska"],
        })


    # effects: GET page and parse HTML table into DataFrame or raises
    def search(self, **kwargs):
        self.logger.info("Fetching Nebraska bid opportunities page")
        try:
            resp = self.session.get(self.base_url, timeout=30)
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"search HTTP error: {e}", exc_info=False)
            raise SearchTimeoutError("Nebraska search HTTP error") from e
        
        try:
            soup = BeautifulSoup(resp.text, "html.parser")
            table = soup.find("table", class_="table table-bordered table-striped table-responsive")
            if not table:
                self.logger.error("Bids table not found on Nebraska page")
                raise DataExtractionError("Nebraska bids table missing")

            tbody = table.find("tbody") or table
            records = []
            for row in tbody.find_all("tr"):
                cols = row.find_all("td")
                if len(cols) < 8:
                    continue
                a = cols[1].find("a", href=True)
                title = a.get_text(strip=True) if a else cols[1].get_text(strip=True)
                link = urljoin(self.base_url, a["href"]) if a else self.base_url
                code = cols[6].get_text(strip=True)
                end_date = cols[3].get_text(strip=True)
                records.append({
                    "title": title,
                    "code": code,
                    "end_date": end_date,
                    "link": link,
                })
            df = pd.DataFrame(records)
            self.logger.info(f"Parsed {len(df)} records from Nebraska bids table")
            return df
        except DataExtractionError:
            raise
        except Exception as e:
            self.logger.error(f"extract_data HTML parsing error: {e}", exc_info=True)
            raise DataExtractionError("Nebraska HTML extract_data failed") from e


    # effects: wrap search + filter; returns list of dicts or raises
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Nebraska")
        try:
            df = self.search(**kwargs)
        except (SearchTimeoutError, DataExtractionError):
            raise
        except Exception as e:
            self.logger.error(f"Nebraska search failed: {e}", exc_info=True)
            raise ScraperError("Nebraska scrape failed during search") from e

        try:
            self.logger.info(f"Total raw records before filtering: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total records after filtering: {len(filtered)}")
            return filtered.to_dict("records")
        except Exception as e:
            self.logger.error(f"Nebraska filter failed: {e}", exc_info=True)
            raise ScraperError("Nebraska scrape failed during filter") from e
