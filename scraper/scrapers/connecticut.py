# connecticut.py

import logging
from datetime import datetime

import pandas as pd
import pytz
import requests

from scraper.core.requests_scraper import RequestsScraper
from scraper.utils.data_utils import filter_by_keywords
from scraper.config.settings import STATE_RFP_URL_MAP


class ConnecticutScraper(RequestsScraper):
    def __init__(self):
        # the full-text-search endpoint includes all required query parameters
        super().__init__("https://webprocure.proactiscloud.com/wp-full-text-search/search/sols")
        self.logger = logging.getLogger(__name__)
        # instruct server to return JSON
        self.session.headers.update(
            {
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json",
            }
        )

    def _fetch_page(self, offset, customerid):
        # helper to GET one JSON page at the given offset
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
            self.logger.debug(f"GET {resp.url} → {resp.status_code}")
            resp.raise_for_status()
        except requests.exceptions.RequestException as re:
            self.logger.error(f"HTTP request failed (offset={offset}): {re}", exc_info=False)
            return None

        content_type = resp.headers.get("Content-Type", "")
        if "application/json" not in content_type.lower():
            snippet = resp.text[:200].replace("\n", " ")
            self.logger.error(f"Expected JSON but got: {snippet!r}")
            return None

        try:
            return resp.json()
        except Exception as e:
            snippet = resp.text[:200].replace("\n", " ")
            self.logger.error(
                f"JSON parsing failed (offset={offset}): {e}; snippet: {snippet!r}", exc_info=False
            )
            return None

    def search(self, **kwargs):
        # fetch the first JSON page (offset=0) to determine total_hits and page_size
        customerid = kwargs.get("customerid", 51)
        self.logger.info("fetching first page of JSON (offset=0)...")
        try:
            first_page = self._fetch_page(offset=0, customerid=customerid)
            if not first_page:
                self.logger.warning("first page fetch returned no data")
                return None, None, None

            total_hits = first_page.get("hits", 0)
            page_size = len(first_page.get("records", []))
            self.logger.info(f"total_hits={total_hits}, page_size={page_size}")
            return total_hits, page_size, first_page
        except Exception as e:
            self.logger.error(f"search failed: {e}", exc_info=True)
            return None, None, None

    def next_page(self):
        # not used; pagination handled in scrape()
        return None

    def extract_data(self, page_content):
        # parse one JSON page’s “records” into a list of dicts
        if not page_content or "records" not in page_content:
            self.logger.error('no page_content or missing "records" key')
            return []

        output = []
        pacific = pytz.timezone("US/Pacific")

        try:
            for rec in page_content["records"]:
                label = rec.get("title", "").strip()
                code = rec.get("bidNumber", "").strip()

                end_ts = rec.get("prtcpEndDate")
                if end_ts is not None:
                    try:
                        dt_utc = datetime.fromtimestamp(end_ts / 1000, tz=pytz.UTC)
                        dt_pst = dt_utc.astimezone(pacific)
                        end_str = dt_pst.strftime("%Y-%m-%d %H:%M:%S %Z")
                    except Exception as e:
                        self.logger.warning(f"Failed to convert timestamp {end_ts}: {e}", exc_info=False)
                        end_str = str(end_ts)
                else:
                    end_str = ""

                # No per-record link available, use base URL as placeholder
                link = STATE_RFP_URL_MAP['connecticut']

                output.append(
                    {
                        "Label": label,
                        "Code": code,
                        "End (UTC-7)": end_str,
                        "Keyword Hits": "",
                        "Link": link,
                    }
                )
            return output

        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            return []

    def scrape(self, **kwargs):
        # high-level orchestration: search → paginate through offsets → extract → filter → return
        self.logger.info("starting Connecticut scrape")
        all_records = []
        try:
            total_hits, page_size, first_page = self.search(**kwargs)
            if total_hits is None:
                self.logger.warning("search() returned no total_hits; aborting scrape")
                return []

            batch = self.extract_data(first_page)
            all_records.extend(batch)
            self.logger.info(f"collected {len(batch)} records from offset=0")

            customerid = kwargs.get("customerid", 51)
            offset = page_size

            while offset < total_hits:
                self.logger.info(f"fetching next page: offset={offset}")
                page_json = self._fetch_page(offset=offset, customerid=customerid)
                if not page_json:
                    self.logger.error(f"failed to fetch page at offset={offset}; stopping pagination")
                    break

                batch = self.extract_data(page_json)
                all_records.extend(batch)
                self.logger.info(f"collected {len(batch)} records from offset={offset}")
                offset += page_size

            df = pd.DataFrame(all_records)
            self.logger.info(f"total records before filter: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"total records after filter: {len(filtered)}")
            return filtered.to_dict("records")

        except Exception as e:
            self.logger.error(f"connecticut scrape failed: {e}", exc_info=True)
            return []
        finally:
            self.close()