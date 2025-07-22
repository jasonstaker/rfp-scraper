# georgia.py
# url: https://ssl.doas.state.ga.us/gpr/index

import logging

import pandas as pd
import requests

from scraper.core.requests_scraper import RequestsScraper
from scraper.config.settings import STATE_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords
from scraper.utils.date_utils import parse_date_generic

# a scraper for Georgia RFP data using Requests
class GeorgiaScraper(RequestsScraper):
    # modifies: self
    # effects: initializes the scraper with Georgia's RFP URL and sets up logging
    def __init__(self):
        base = STATE_RFP_URL_MAP.get("georgia", "https://ssl.doas.state.ga.us/gpr/eventSearch")
        super().__init__(base)
        self.logger = logging.getLogger(__name__)

    # modifies: self.session (cookies)
    # effects: performs an initial GET to establish session cookies, then issues a POST to Georgia's eventSearch endpoint; returns the parsed JSON dict or None on failure
    def search(self, **kwargs):
        index_url = "https://ssl.doas.state.ga.us/gpr/index?persisted=true"
        headers_get = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/136.0.0.0 Safari/537.36"
            )
        }
        try:
            init_resp = self.session.get(index_url, headers=headers_get, timeout=15)
            if init_resp.status_code != 200:
                self.logger.error(f"Initial GET failed: {init_resp.status_code}")
                raise
        except requests.exceptions.RequestException as re:
            self.logger.error(f"Initial GET HTTP error: {re}", exc_info=False)
            raise
        except Exception as e:
            self.logger.error(f"Initial GET failed: {e}", exc_info=True)
            raise

        # POST with full DataTables payload
        headers_post = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "https://ssl.doas.state.ga.us",
            "Referer": "https://ssl.doas.state.ga.us/gpr/index?persisted=true",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/136.0.0.0 Safari/136.0.0.0"
            ),
            "X-Requested-With": "XMLHttpRequest",
        }

        payload = {
            "draw": 1,
            "columns[0][data]": "function",
            "columns[0][name]": "",
            "columns[0][searchable]": "true",
            "columns[0][orderable]": "false",
            "columns[0][search][value]": "",
            "columns[0][search][regex]": "false",
            "columns[1][data]": "function",
            "columns[1][name]": "",
            "columns[1][searchable]": "true",
            "columns[1][orderable]": "true",
            "columns[1][search][value]": "",
            "columns[1][search][regex]": "false",
            "columns[2][data]": "title",
            "columns[2][name]": "",
            "columns[2][searchable]": "true",
            "columns[2][orderable]": "true",
            "columns[2][search][value]": "",
            "columns[2][search][regex]": "false",
            "columns[3][data]": "agencyName",
            "columns[3][name]": "",
            "columns[3][searchable]": "true",
            "columns[3][orderable]": "true",
            "columns[3][search][value]": "",
            "columns[3][search][regex]": "false",
            "columns[4][data]": "function",
            "columns[4][name]": "",
            "columns[4][searchable]": "true",
            "columns[4][orderable]": "true",
            "columns[4][search][value]": "",
            "columns[4][search][regex]": "false",
            "columns[5][data]": "function",
            "columns[5][name]": "",
            "columns[5][searchable]": "true",
            "columns[5][orderable]": "true",
            "columns[5][search][value]": "",
            "columns[5][search][regex]": "false",
            "columns[6][data]": "function",
            "columns[6][name]": "",
            "columns[6][searchable]": "true",
            "columns[6][orderable]": "false",
            "columns[6][search][value]": "",
            "columns[6][search][regex]": "false",
            "columns[7][data]": "status",
            "columns[7][name]": "",
            "columns[7][searchable]": "true",
            "columns[7][orderable]": "false",
            "columns[7][search][value]": "",
            "columns[7][search][regex]": "false",
            "order[0][column]": 5,
            "order[0][dir]": "asc",
            "start": 0,
            "length": 10000,
            "search[value]": "",
            "search[regex]": "false",
            "responseType": "ALL",
            "eventStatus": "OPEN",
            "eventIdTitle": "",
            "govType": "ALL",
            "govEntity": "",
            "catType": "ALL",
            "eventProcessType": "ALL",
            "dateRangeType": "",
            "rangeStartDate": "",
            "rangeEndDate": "",
            "isReset": "false",
            "persisted": "false",
            "refreshSearchData": "true",
        }

        try:
            resp = self.session.post(self.base_url, data=payload, headers=headers_post, timeout=20)
            if resp.status_code != 200:
                self.logger.error(f"search HTTP status {resp.status_code}: {resp.text!r}")
                raise

            try:
                data = resp.json()
            except ValueError as ve:
                self.logger.error(f"JSON decode failed: {ve}; response: {resp.text!r}", exc_info=False)
                raise

            return data

        except requests.exceptions.RequestException as re:
            self.logger.error(f"search HTTP error: {re}", exc_info=False)
            raise
        except Exception as e:
            self.logger.error(f"search() failed: {e}", exc_info=True)
            raise

    # requires: response_json is a dict containing a "data" key with a list of event records
    # effects: parses the JSON "data" array into a list of standardized record dicts; returns that list
    def extract_data(self, response_json: dict):
        if not response_json or "data" not in response_json:
            self.logger.error('no valid "data" field in response for extract_data')
            raise

        records = []
        try:
            for item in response_json["data"]:
                title = item.get("title", "").strip()
                code = item.get("esourceNumber", "").strip()
                closing_date_str = parse_date_generic(item.get("closingDateStr", "").strip())
                source_id = item.get("sourceId", "").strip()
                esource_number = code

                # construct detail link using eSourceNumber and sourceId
                link = (
                    "https://ssl.doas.state.ga.us/gpr/eventDetails"
                    f"?eSourceNumber={esource_number}&sourceSystemType={source_id}"
                )

                records.append({
                    "title": title,
                    "code": code,
                    "end_date": closing_date_str,
                    "link": link,
                })

            return records
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise

    # effects: orchestrates search -> extract_data -> filter_by_keywords; returns filtered records or raises on failure
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Georgia")
        try:
            response_json = self.search(**kwargs)
            if response_json is None:
                self.logger.warning("search returned no data; aborting scrape")
                raise

            records = self.extract_data(response_json)
            df = pd.DataFrame(records)
            self.logger.info(f"Total raw records before filtering: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total records after filtering: {len(filtered)}")
            return filtered.to_dict("records")

        except Exception as e:
            self.logger.error(f"Georgia scrape failed: {e}", exc_info=True)
            raise
