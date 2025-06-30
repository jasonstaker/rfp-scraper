# arkansas.py
# url: https://arbuy.arkansas.gov/bso/view/search/external/advancedSearchBid.xhtml?openBids=true

import logging
import requests

from bs4 import BeautifulSoup
import pandas as pd

from scraper.core.requests_scraper import RequestsScraper
from scraper.config.settings import STATE_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords

# a scraper for Arkansas RFP data using Requests
class ArkansasScraper(RequestsScraper):
    # modifies: self
    # effects: initializes the scraper with Arkansas's RFP url and sets up logging
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP["arkansas"])
        self.logger = logging.getLogger(__name__)

    # modifies: self.current_response
    # effects: performs a GET request to fetch the Arkansas RFP page and returns its HTML
    def search(self, **kwargs):
        try:
            response = self.session.get(self.base_url, timeout=15)
            response.raise_for_status()
            self.current_response = response.text
            return response.text
        except requests.exceptions.RequestException as re:
            self.logger.error(f"search HTTP error: {re}", exc_info=False)
            raise
        except Exception as e:
            self.logger.error(f"search failed: {e}", exc_info=True)
            raise

    # requires: html is a string containing HTML page source
    # effects: parses the HTML table and returns a list of raw record dicts
    def extract_data(self, html):
        if not html:
            self.logger.error("no HTML provided to extract_data")
            raise
        try:
            soup = BeautifulSoup(html, "html.parser")
            table = soup.find("table", {"role": "grid"})
            if not table:
                self.logger.error("results table not found")
                raise
            records = []
            for row in table.find_all("tr"):
                cols = row.find_all("td")
                if len(cols) < 8:
                    continue
                link_tag = cols[0].find("a", href=True)
                if not link_tag:
                    continue
                code = link_tag.text.strip()
                href = link_tag["href"]
                label = cols[6].get_text(strip=True)
                end = cols[7].get_text(strip=True)
                full_link = f"https://arbuy.arkansas.gov{href}" if href.startswith("/") else href
                records.append({
                    "Label": label,
                    "Code": code,
                    "End (UTC-7)": end,
                    "Keyword Hits": "",
                    "Link": full_link,
                })
            return records
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise

    # effects: orchestrates search -> extract -> filter; returns filtered records or raises on failure
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Arkansas")
        try:
            html = self.search(**kwargs)
            if not html:
                self.logger.warning("Search returned no HTML; aborting scrape")
                raise
            self.logger.info("Processing data")
            raw_records = self.extract_data(html)
            df = pd.DataFrame(raw_records)
            self.logger.info("Applying filters")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Found {len(filtered)} records after filtering")
            return filtered.to_dict("records")
        except Exception as e:
            self.logger.error(f"Scrape failed: {e}", exc_info=True)
            raise
