# florida.py
# url: https://vendor.myfloridamarketplace.com/search/bids

import logging

import pandas as pd
import requests

from scraper.core.requests_scraper import RequestsScraper
from src.config import STATE_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords

from scraper.core.errors import (
    SearchTimeoutError,
    DataExtractionError,
    ScraperError,
)

# a scraper for Florida RFP data using Requests
class FloridaScraper(RequestsScraper):

    # modifies: self
    # effects: initializes the scraper with Florida's RFP URL and sets up logging
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP.get("florida"))
        self.logger = logging.getLogger(__name__)


    # effects: issues a POST to the Florida endpoint for the given page; returns JSON list or raises on failure
    def search(self, page: int = 1, **kwargs):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                          " AppleWebKit/537.36 (KHTML, like Gecko)"
                          " Chrome/114.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Content-Type": "application/json;charset=UTF-8",
            "Origin": "https://vendor.myfloridamarketplace.com",
            "Referer": "https://vendor.myfloridamarketplace.com/mfmp/pub/search/bids",
        }
        payload = {
            "pageSize": 100,
            "type": [],
            "status": ["OPEN"],
            "agency": [],
            "adNumber": "",
            "agencyAdvertisementNumber": "",
            "title": "",
            "publishedDate": "",
            "openDate": "",
            "endDate": "",
            "commodityCodes": [],
            "intendsToParticipate": "",
            "assignee": "",
            "page": page
        }
        try:
            resp = self.session.post(self.base_url, json=payload, headers=headers, timeout=15)
            resp.raise_for_status()
        except requests.exceptions.RequestException as re:
            self.logger.error(f"search HTTP error (page={page}): {re}", exc_info=False)
            raise SearchTimeoutError(f"Florida search HTTP error on page {page}") from re

        try:
            data = resp.json()
        except ValueError as ve:
            self.logger.error(f"JSON decode failed (page={page}): {ve}", exc_info=False)
            raise DataExtractionError(f"Florida JSON decode failed on page {page}") from ve

        if not isinstance(data, list):
            self.logger.error(f"Expected JSON list but got: {data}")
            raise DataExtractionError(f"Florida search returned non‑list JSON on page {page}")

        return data


    # requires: page_data is a list of dicts
    # effects: transforms each JSON dict into a record dict; returns list of records
    def extract_data(self, page_data: list[dict]):
        if not isinstance(page_data, list):
            self.logger.error("extract_data received invalid page_data")
            raise DataExtractionError("Florida extract_data expected list input")
        records = []
        try:
            for item in page_data:
                ad_id = item.get("advertisementId")
                if ad_id is None:
                    continue
                code = "AD-" + str(ad_id)
                title = item.get("title", "").strip()
                close_iso = item.get("closeDate", "").strip()
                detail_link = f"https://vendor.myfloridamarketplace.com/search/bids/detail/{ad_id}"
                records.append({
                    "title": title,
                    "code": code,
                    "end_date": close_iso,
                    "link": detail_link,
                })
            return records
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise DataExtractionError("Florida extract_data failed") from e


    # effects: paginates through search & extract_data, filters results; returns filtered records
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Florida")
        all_records = []
        try:
            page_num = 1
            while True:
                self.logger.info(f"Fetching Florida page {page_num}")
                page_data = self.search(page=page_num)
                if not page_data:
                    self.logger.info(f"No more advertisements on page {page_num}; stopping")
                    break
                all_records.extend(self.extract_data(page_data))
                page_num += 1

            df = pd.DataFrame(all_records)
            self.logger.info(f"Total raw records before filtering: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total records after filtering: {len(filtered)}")
            return filtered.to_dict("records")

        except (SearchTimeoutError, DataExtractionError):
            raise
        except Exception as e:
            self.logger.error(f"Florida scrape failed: {e}", exc_info=True)
            raise ScraperError("Florida scrape failed") from e
