# los_angeles.py
# url: https://camisvr.co.la.ca.us/LACoBids/BidLookUp/OpenBidList

import logging
import re
import requests

from bs4 import BeautifulSoup
import pandas as pd

from scraper.core.requests_scraper import RequestsScraper
from src.config import COUNTY_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords
from scraper.core.errors import (
    SearchTimeoutError,
    DataExtractionError,
    ElementNotFoundError,
    ScraperError,
)

# a scraper for Los Angeles County open bids using Requests
class LosAngelesScraper(RequestsScraper):

    # modifies: self
    # effects: initializes with base list URL and sets up logger
    def __init__(self):
        super().__init__(COUNTY_RFP_URL_MAP["california"]["los angeles"])
        self.logger = logging.getLogger(__name__)


    # requires: page (int), page_size (int)
    # modifies: none
    # effects: issues GET to the open‐bid list with pagination & sorting params, returns HTML
    def search(self, page=1, page_size=100, **kwargs):
        params = {
            "page":           page,
            "TextSearch":     "|||",
            "FieldSort":      "BidCloseDate",
            "DirectionSort":  "Asc",
            "PageSize":       page_size,
        }
        try:
            resp = self.session.get(self.base_url, params=params, timeout=15)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as e:
            self.logger.error(f"search HTTP error (page={page}): {e}", exc_info=False)
            raise SearchTimeoutError("LosAngeles search HTTP error") from e


    # requires: html (str) containing <tbody id="searchTbl1">
    # effects: parses table rows into raw records with code, title, type, department, end_date, link
    def extract_data(self, html):
        if not html:
            raise DataExtractionError("Empty HTML in LosAngeles extract_data")

        soup = BeautifulSoup(html, "html.parser")
        tbody = soup.find("tbody", id="searchTbl1")
        if not tbody:
            raise ElementNotFoundError("LA results tbody not found")

        records = []
        for row in tbody.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) < 5:
                continue

            link_tag = cols[0].find("a", href=True)
            if not link_tag or "selectBid" not in link_tag["href"]:
                continue
            code = link_tag.get_text(strip=True)
            m = re.search(r"selectBid\('(\d+)'\)", link_tag["href"])
            bid_id = m.group(1) if m else ""
            link = self.base_url

            title_lbl = cols[1].find("label", {"name": "BidTitleEllipsis"})
            title = title_lbl.get_text(strip=True) if title_lbl else cols[1].get_text(" ", strip=True)

            end_date = cols[4].get_text(strip=True).lstrip("\u00a0")

            records.append({
                "code":       code,
                "title":      title,
                "end_date":   end_date,
                "link":       link,
            })

        return records


    # effects: orchestrates pagination -> extract_data -> filter; returns filtered records
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Los Angeles County")
        all_records = []
        page = 1
        page_size = 100

        try:
            while True:
                self.logger.info(f"Fetching page {page}")
                html = self.search(page=page, page_size=page_size)
                batch = self.extract_data(html)
                if not batch:
                    self.logger.info("No more records; ending pagination")
                    break
                all_records.extend(batch)
                page += 1

            df = pd.DataFrame(all_records)
            self.logger.info(f"Total raw records before filtering: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total records after filtering: {len(filtered)}")
            return filtered.to_dict("records")

        except (SearchTimeoutError, DataExtractionError, ElementNotFoundError) as e:
            self.logger.error(f"LosAngeles scrape failed: {e}", exc_info=True)
            raise
        except Exception as e:
            self.logger.error(f"LosAngeles scrape unexpected error: {e}", exc_info=True)
            raise ScraperError("LosAngeles scrape failed") from e
