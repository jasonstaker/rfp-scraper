# florida.py
# url: https://vendor.myfloridamarketplace.com/search/bids

import logging
import time

import pandas as pd
import requests

from scraper.core.requests_scraper import RequestsScraper
from scraper.config.settings import STATE_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords

# a scraper class for Florida VBS data, using the real SearchAdvertisements endpoint.
class FloridaScraper(RequestsScraper):

    # requires: nothing
    # modifies: self
    # effects: initializes the scraper with Florida's RFP URL and sets up logging
    def __init__(self):
        # Make sure the map points at the correct JSON-POST endpoint:
        super().__init__(STATE_RFP_URL_MAP.get("florida"))
        self.logger = logging.getLogger(__name__)

    # requires: nothing
    # modifies: nothing
    # effects: issues a POST to the Florida endpoint for the given page; returns a list of JSON objects or None on failure
    def search(self, page: int = 1, **kwargs):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
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
            # inspect the status / content before calling .json()
            if resp.status_code != 200:
                self.logger.error(f"search HTTP status {resp.status_code} on page={page}: {resp.text!r}")
                return None

            # if the body is empty (or not valid JSON), this will raise ValueError
            data = resp.json()
            if not isinstance(data, list):
                self.logger.error(f"Expected JSON list but got: {data}")
                return None

            return data

        except requests.exceptions.RequestException as re:
            self.logger.error(f"search HTTP error (page={page}): {re}", exc_info=False)
            return None

        except ValueError as ve:
            # this happens if resp.text is empty or not-JSON
            self.logger.error(f"JSON decode failed (page={page}), response was: {resp.text!r}", exc_info=False)
            return None

        except Exception as e:
            self.logger.error(f"search failed (page={page}): {e}", exc_info=True)
            return None

    # requires: page_data is a list of dictionaries representing JSON objects
    # modifies: nothing
    # effects: transforms each JSON dict into a record with Label, Code, End date, Keyword Hits, and Link; returns a list of records
    def extract_data(self, page_data: list[dict]):
        if not page_data:
            return []

        records = []
        try:
            for item in page_data:
                ad_id = item.get("advertisementId")
                if ad_id is None:
                    continue

                code = 'AD-' + str(ad_id)
                label = item.get("title", "").strip()
                close_iso = item.get("closeDate", "").strip()

                detail_link = f"https://vendor.myfloridamarketplace.com/search/bids/detail/{ad_id}"

                records.append({
                    "Label": label,
                    "Code": code,
                    "End (UTC-7)": close_iso,
                    "Keyword Hits": "",
                    "Link": detail_link,
                })

            return records

        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            return []

    # requires: nothing
    # modifies: nothing
    # effects: orchestrates pagination through search & extract_data, applies keyword filtering, returns filtered records or raises on failure
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Florida")
        all_records = []

        try:
            page_num = 1
            while True:
                self.logger.info(f"Fetching Florida page {page_num}")
                page_data = self.search(page=page_num)
                if page_data is None:
                    self.logger.warning(f"search returned None for page {page_num}; aborting")
                    break

                if not page_data:
                    self.logger.info(f"No more advertisements on page {page_num}; stopping pagination")
                    break

                all_records.extend(self.extract_data(page_data))

                page_num += 1

            df = pd.DataFrame(all_records)
            self.logger.info(f"Total raw records before filtering: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total records after filtering: {len(filtered)}")
            return filtered.to_dict("records")

        except Exception as e:
            self.logger.error(f"Florida scrape failed: {e}", exc_info=True)
            raise
