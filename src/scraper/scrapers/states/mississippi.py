# mississippi.py
# url: https://www.ms.gov/dfa/contract_bid_search/Bid?autoloadGrid=true

import logging
import requests
import pandas as pd

from scraper.core.requests_scraper import RequestsScraper
from scraper.utils.data_utils import filter_by_keywords
from scraper.config.settings import STATE_RFP_URL_MAP

from scraper.core.errors import (
    SearchTimeoutError,
    DataExtractionError,
    ScraperError,
)

# a scraper for Mississippi RFP data using Requests
class MississippiScraper(RequestsScraper):

    # modifies: self
    # effects: initializes the scraper with Mississippi's BidData endpoint and sets up logging
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP["mississippi"])
        self.logger = logging.getLogger(__name__)
        self.session.headers.update({
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": "https://www.ms.gov",
            "Referer": "https://www.ms.gov/dfa/contract_bid_search/Bid?autoloadGrid=False",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/114.0.0.0 Safari/537.36"
            ),
        })


    # effects: issues a POST to the BidData endpoint; returns JSON dict or raises
    def search(self, **kwargs):
        self.logger.info("Fetching Mississippi bid data via POST")
        data = {
            "sEcho": 1,
            "iColumns": 9,
            "sColumns": "," * 8,
            "iDisplayStart": 0,
            "iDisplayLength": 9999,
            "mDataProp_0": "Agency", "bSortable_0": "true",
            "mDataProp_1": "BidNumber", "bSortable_1": "true",
            "mDataProp_2": "ObjectID", "bSortable_2": "true",
            "mDataProp_3": "VerNumber", "bSortable_3": "true",
            "mDataProp_4": "BidStatus", "bSortable_4": "true",
            "mDataProp_5": "AdvertiseDate", "bSortable_5": "true",
            "mDataProp_6": "SubmissionDate", "bSortable_6": "true",
            "mDataProp_7": "OpeningDate", "bSortable_7": "true",
            "mDataProp_8": "BidID", "bSortable_8": "false",
            "iSortCol_0": 0, "sSortDir_0": "asc", "iSortingCols": 1,
        }
        try:
            resp = self.session.post(self.base_url, data=data, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as re:
            self.logger.error(f"search HTTP error: {re}", exc_info=False)
            raise SearchTimeoutError("Mississippi search HTTP error") from re
        except ValueError as ve:
            self.logger.error(f"search JSON decode failed: {ve}", exc_info=False)
            raise DataExtractionError("Mississippi JSON decode failed") from ve
        except Exception as e:
            self.logger.error(f"search failed: {e}", exc_info=True)
            raise ScraperError("Mississippi search failed") from e


    # requires: response_data is a dict with "aaData" list
    # effects: transforms JSON records into standardized dicts
    def extract_data(self, response_data):
        self.logger.info("Extracting data from Mississippi JSON")
        aa = response_data.get("aaData")
        if not isinstance(aa, list):
            self.logger.error("Unexpected response format: no aaData list")
            raise DataExtractionError("Mississippi extract_data missing aaData")

        records = []
        for item in aa:
            try:
                bid_id = item.get("BidID")
                bid_num = item.get("BidNumber", "").strip()
                desc = item.get("BidDescription", "").strip()
                sub_ts = item.get("SubmissionDate")

                end_str = ""
                if isinstance(sub_ts, str) and sub_ts.startswith("/Date("):
                    ms = int(sub_ts.lstrip("/Date(").rstrip(")/"))
                    dt = pd.to_datetime(ms, unit="ms", utc=True)
                    end_str = dt.strftime("%Y-%m-%d %H:%M:%S %Z")

                detail_url = (
                    f"https://www.ms.gov/dfa/contract_bid_search/Bid/Details/{bid_id}?AppId=1"
                    if bid_id is not None else STATE_RFP_URL_MAP["mississippi"]
                )

                records.append({
                    "title": desc,
                    "code": bid_num,
                    "end_date": end_str,
                    "link": detail_url,
                })
            except Exception as e:
                self.logger.warning(f"Failed to parse record {bid_id}: {e}")
                continue

        return records


    # effects: orchestrates search -> extract_data -> filter; returns filtered list or raises
    def scrape(self, **kwargs):
        self.logger.info("Starting Mississippi scrape")
        try:
            data = self.search(**kwargs)
            recs = self.extract_data(data)
            df = pd.DataFrame(recs)
            self.logger.info(f"Total raw records: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Records after filtering: {len(filtered)}")
            return filtered.to_dict("records")
        except (SearchTimeoutError, DataExtractionError, ScraperError):
            raise
        except Exception as e:
            self.logger.error(f"Mississippi scrape failed: {e}", exc_info=True)
            raise ScraperError("Mississippi scrape failed") from e