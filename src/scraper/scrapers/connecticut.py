# connecticut.py
# url: https://portal.ct.gov/das/ctsource/bidboard?language=en_US

import logging
from datetime import datetime

import pandas as pd
import pytz
import requests

from scraper.core.requests_scraper import RequestsScraper
from scraper.utils.data_utils import filter_by_keywords
from scraper.config.settings import STATE_RFP_URL_MAP

# a scraper for Connecticut RFP data using Requests
class ConnecticutScraper(RequestsScraper):
    # modifies: self
    # effects: initializes with Connecticut's RFP API url, sets up logging, and configures JSON headers
    def __init__(self):
        super().__init__("https://webprocure.proactiscloud.com/wp-full-text-search/search/sols")
        self.logger = logging.getLogger(__name__)
        self.session.headers.update({
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json",
        })

    # requires: offset is an integer, customerid is an integer
    # effects: fetches a JSON page from the API and returns the parsed JSON
    def _fetch_page(self, offset, customerid):
        params = {
            "customerid": customerid,
            "q": "*",
            "from": offset,
            "sort": "r",
            "f": "ps=Open",
            "oids": "",
        }
        try:
            resp = self.session.get(self.base_url, params=params, timeout=20)
            resp.raise_for_status()
        except requests.exceptions.RequestException as re:
            self.logger.error(f"HTTP request failed (offset={offset}): {re}", exc_info=False)
            raise

        content_type = resp.headers.get("Content-Type", "")
        if "application/json" not in content_type.lower():
            snippet = resp.text[:200].replace("\n", " ")
            self.logger.error(f"Expected JSON but got: {snippet!r}")
            raise

        try:
            return resp.json()
        except Exception as e:
            snippet = resp.text[:200].replace("\n", " ")
            self.logger.error(
                f"JSON parsing failed (offset={offset}): {e}; snippet: {snippet!r}", exc_info=False
            )
            raise

    # effects: fetches the first JSON page, returns total_hits, page_size, and page data
    def search(self, **kwargs):
        customerid = kwargs.get("customerid", 51)
        self.logger.info("fetching first page of JSON (offset=0)...")
        try:
            first_page = self._fetch_page(offset=0, customerid=customerid)
            total_hits = first_page.get("hits", 0)
            page_size = len(first_page.get("records", []))
            self.logger.info(f"total_hits={total_hits}, page_size={page_size}")
            return total_hits, page_size, first_page
        except Exception as e:
            self.logger.error(f"search failed: {e}", exc_info=True)
            raise

    # requires: page_content is a dict containing a "records" key
    # effects: parses the JSON records into standardized record dicts
    def extract_data(self, page_content):
        if not page_content or "records" not in page_content:
            self.logger.error('no page_content or missing "records" key')
            raise

        output = []
        pacific = pytz.timezone("US/Pacific")
        try:
            for rec in page_content["records"]:
                title = rec.get("title", "").strip()
                code = rec.get("bidNumber", "").strip()
                end_ts = rec.get("openDate")
                if end_ts is not None:
                    try:
                        dt_utc = datetime.fromtimestamp(end_ts / 1000, tz=pytz.UTC)
                        dt_pst = dt_utc.astimezone(pacific)
                        end_str = dt_pst.strftime("%Y-%m-%d %H:%M:%S %Z")
                    except Exception:
                        end_str = str(end_ts)
                else:
                    end_str = ""
                link = STATE_RFP_URL_MAP['connecticut']
                output.append({
                    "title": title,
                    "code": code,
                    "end_date": end_str,
                    "link": link,
                })
            return output
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise

    # effects: orchestrates search -> pagination -> extract -> filter; returns filtered records
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Connecticut")
        all_records = []
        try:
            total_hits, page_size, first_page = self.search(**kwargs)
            self.logger.info("Processing page 1")
            all_records.extend(self.extract_data(first_page))

            customerid = kwargs.get("customerid", 51)
            offset = page_size
            page_num = 2
            while offset < total_hits:
                self.logger.info(f"Processing page {page_num}")
                page_json = self._fetch_page(offset=offset, customerid=customerid)
                batch = self.extract_data(page_json)
                all_records.extend(batch)
                offset += page_size
                page_num += 1

            self.logger.info("Completed parsing")
            df = pd.DataFrame(all_records)
            self.logger.info("Applying filters")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Found {len(filtered)} records after filtering")
            return filtered.to_dict("records")
        except Exception as e:
            self.logger.error(f"Connecticut scrape failed: {e}", exc_info=True)
            raise
