# texas.py
# url: https://www.txsmartbuy.gov/esbd?page=1&status=1

import logging
import pandas as pd
import requests

from scraper.core.requests_scraper import RequestsScraper
from src.config import STATE_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords
from scraper.utils.date_utils import parse_date_generic
from scraper.core.errors import (
    SearchTimeoutError,
    DataExtractionError,
    ScraperError,
)

# a scraper for Texas RFP data using Requests
class TexasScraper(RequestsScraper):

    # modifies: self
    # effects: initializes the scraper with Texas’s ESBD service URL and sets up logging & headers
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP['texas'])
        self.logger = logging.getLogger(__name__)
        self.session.headers.update({
            'Accept':           'application/json, text/javascript, */*; q=0.01',
            'Content-Type':     'application/json; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer':          'https://www.txsmartbuy.gov/esbd?page=1&status=1',
            'User-Agent':       (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/137.0.0.0 Safari/537.36'
            ),
        })


    # effects: paginates through POST requests until duplicate internalid appears
    def search(self, **kwargs):
        url = self.base_url
        base_payload = {
            "lines": [],
            "page": 1,
            "status": "1",
            "urlRoot": "esbd",
            "agencies": [],
            "recordsPerPage": 24,
            "totalRecordsFound": 0,
            "agency": "",
            "agencyNumber": "",
            "nigp": "",
            "keyword": "",
            "solicitationId": "",
            "dateRange": "custom",
            "startDate": "",
            "endDate": "",
        }

        all_lines = []
        seen_ids = set()
        page = 1
        agencies_cache = []

        try:
            while True:
                payload = base_payload.copy()
                payload['page'] = page

                if agencies_cache:
                    payload['agencies'] = agencies_cache

                self.logger.info(f"Fetching Texas RFP page {page}")
                resp = self.session.post(url, json=payload, timeout=30)
                resp.raise_for_status()
                data = resp.json()

                if page == 1:
                    agencies_cache = data.get('agencies', [])

                lines = data.get('lines', [])
                if not lines:
                    self.logger.info(f"No lines on page {page}, stopping pagination")
                    break

                for entry in lines:
                    iid = entry.get('internalid')
                    if iid in seen_ids:
                        self.logger.info(f"Duplicate internalid {iid} found, stopping pagination")
                        return { 'lines': all_lines }
                    seen_ids.add(iid)
                    all_lines.append(entry)

                page += 1

            return { 'lines': all_lines }

        except requests.exceptions.RequestException as re:
            self.logger.error(f"search HTTP error: {re}", exc_info=False)
            raise SearchTimeoutError("Texas search HTTP error") from re
        except ValueError as ve:
            self.logger.error(f"search JSON decode failed: {ve}", exc_info=False)
            raise DataExtractionError("Texas JSON decode failed") from ve
        except Exception as e:
            self.logger.error(f"search() failed: {e}", exc_info=True)
            raise ScraperError("Texas search failed") from e


    # requires: response_json from search()
    # effects: transforms the JSON into a list of standardized record dicts
    def extract_data(self, response_json):
        if not response_json or 'lines' not in response_json:
            self.logger.error("No 'lines' key in Texas response JSON")
            raise DataExtractionError("Invalid Texas JSON structure")

        records = []
        try:
            for entry in response_json['lines']:
                code = entry.get("solicitationId", "").strip()
                title = entry.get("title", "").strip()

                raw_date = entry.get("responseDue", "").strip()
                raw_time = entry.get("responseTime", "").strip()
                if raw_date and raw_time:
                    end_str = parse_date_generic(f"{raw_date} {raw_time}")
                else:
                    end_str = ""

                link = f"https://www.txsmartbuy.gov/esbd/{code}"
                records.append({
                    "title": title,
                    "code": code,
                    "end_date": end_str,
                    "link": link,
                })
            return records

        except Exception as e:
            self.logger.error(f"extract_data entry parsing failed: {e}", exc_info=True)
            raise DataExtractionError("Texas extract_data failed") from e


    # effects: orchestrates search -> extract_data -> filter_by_keywords; returns filtered list of dicts
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Texas")
        try:
            data = self.search(**kwargs)
            raw_records = self.extract_data(data)

            df = pd.DataFrame(raw_records)
            self.logger.info(f"Total raw records: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total after filtering: {len(filtered)}")

            return filtered.to_dict("records")
        except (SearchTimeoutError, DataExtractionError, ScraperError):
            raise
        except Exception as e:
            self.logger.error(f"Texas scrape failed: {e}", exc_info=True)
            raise ScraperError("Texas scrape failed") from e
