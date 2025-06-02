# arizona.py

import logging
from io import StringIO
from urllib.parse import parse_qsl, urlencode, urljoin

import pandas as pd
from bs4 import BeautifulSoup
import requests

from scraper.core.requests_scraper import RequestsScraper
from scraper.config.settings import FALLBACK_CSRF, STATE_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords


class ArizonaScraper(RequestsScraper):
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP["arizona"])
        self.logger = logging.getLogger(__name__)
        self.hidden_fields = {}
        self.previous_df = None
        self.current_df = None
        self.page_num = 2  # next_page() starts at page 2

    def _scrape_hidden_fields(self, html_text):
        # extract hidden input values for POST payloads
        soup = BeautifulSoup(html_text, "html.parser")
        return {
            inp["name"]: inp.get("value", "")
            for inp in soup.find_all("input", type="hidden")
            if inp.get("name")
        }

    def _build_search_payload(self):
        # construct form data for the initial search request
        data = {**self.hidden_fields}
        data.update(
            {
                "hdnUserValue": "%2Cbody_x_txtRfpAwarded_1",
                "__LASTFOCUS": "body_x_prxFilterBar_x_cmdSearchBtn",
                "__EVENTTARGET": "body:x:prxFilterBar:x:cmdSearchBtn",
                "REQUEST_METHOD": "POST",
                "body:x:txtRfpAwarded_1": "False",
                "hdnRowCountbody_x_grid_grd": "100",
                "maxpageindexbody_x_grid_grd": "6",
                "ajaxrowsiscountedbody_x_grid_grd": "True",
                "CSRFToken": self.hidden_fields.get("CSRFToken", FALLBACK_CSRF),
            }
        )
        params = urlencode(data, safe=":/|%")
        return params

    def _build_pagination_payload(self, page_num):
        # construct form data for next page requests
        focus = page_num - 1
        prev_index = page_num - 2
        data = {
            "__LASTFOCUS": f"body_x_grid_PagerBtn{focus}Page",
            "__EVENTTARGET": "body_x_grid_grd",
            "__EVENTARGUMENT": f"Page|{focus}",
            **self.hidden_fields,
            "hdnCurrentPageIndexbody_x_grid_grd": str(prev_index),
            "CSRFToken": self.hidden_fields.get("CSRFToken", FALLBACK_CSRF),
        }
        return urlencode(data, safe=":/|%")

    def search(self, **kwargs):
        # initial GET to load hidden form state, then POST to retrieve first page
        self.logger.info("starting search for Arizona RFPs")
        try:
            resp = self.session.get(self.base_url, timeout=15)
            if resp.status_code != 200:
                self.logger.error(f"GET failed: {resp.status_code}")
                return None

            self.hidden_fields = self._scrape_hidden_fields(resp.text)
            payload = self._build_search_payload()
            resp = self.session.post(self.base_url, data=dict(parse_qsl(payload)), timeout=15)
            if resp.status_code != 200:
                self.logger.error(f"POST failed: {resp.status_code}")
                return None

            self.hidden_fields = self._scrape_hidden_fields(resp.text)
            self.current_response = resp
            self.page_num = 2
            return resp.text

        except requests.exceptions.RequestException as re:
            self.logger.error(f"search HTTP error: {re}", exc_info=False)
            return None
        except Exception as e:
            self.logger.error(f"search failed: {e}", exc_info=True)
            return None

    def next_page(self):
        # fetch the next page via POST, return new HTML text or None if none left
        if not getattr(self, "current_response", None):
            return None

        try:
            payload = self._build_pagination_payload(self.page_num)
            resp = self.session.post(self.base_url, data=dict(parse_qsl(payload)), timeout=15)
            if resp.status_code != 200:
                self.logger.warning(f"pagination POST failed: {resp.status_code}")
                return None

            new_hidden = self._scrape_hidden_fields(resp.text)
            if "__VIEWSTATE" not in new_hidden:
                self.logger.info("no __VIEWSTATE found, ending pagination")
                return None

            self.hidden_fields = new_hidden
            self.current_response = resp
            self.page_num += 1
            return resp.text

        except requests.exceptions.RequestException as re:
            self.logger.error(f"next_page HTTP error: {re}", exc_info=False)
            return None
        except Exception as e:
            self.logger.error(f"next_page failed: {e}", exc_info=True)
            return None

    def extract_data(self, page_content):
        # parse the HTML table (4th table) and extract links into a list of dicts
        self.logger.info("parsing Arizona HTML table into DataFrame")
        if not page_content:
            self.logger.error("no page_content provided to extract_data")
            return []

        try:
            tables = pd.read_html(StringIO(page_content))
            if len(tables) < 5:
                self.logger.error("expected at least 5 tables, found fewer")
                return []
            df = tables[4]

            soup = BeautifulSoup(page_content, "html.parser")
            tbl = soup.find("table", id="body_x_grid_grd")
            if not tbl:
                self.logger.error("results table not found in extract_data")
                return []

            rows = tbl.select("tbody > tr")
            links = []
            for tr in rows:
                a = tr.find_all("td", recursive=False)[0].find("a", href=True)
                href = a["href"] if a else None
                if href and not href.startswith("http"):
                    href = urljoin(self.base_url, href)
                links.append(href)

            df["Link"] = links
            self.current_df = df
            self.logger.info(f"found {len(df)} records (with Link column)")
            return df.to_dict("records")

        except ValueError as ve:
            self.logger.error(f"pd.read_html failed: {ve}", exc_info=False)
            return []
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            return []

    def scrape(self, **kwargs):
        # search -> first extract -> loop next_page -> dedupe check -> filter -> return
        self.logger.info("starting Arizona scrape")
        all_records = []
        try:
            page = self.search(**kwargs)
            if not page:
                self.logger.warning("search() returned no page; skipping extraction")
                return []

            all_records.extend(self.extract_data(page))
            self.previous_df = self.current_df

            while True:
                page = self.next_page()
                if not page:
                    break

                all_records.extend(self.extract_data(page))
                if self.current_df is not None and self.previous_df is not None:
                    if self.current_df.equals(self.previous_df):
                        self.logger.info("identical page detected, stopping pagination")
                        break
                self.previous_df = self.current_df

            df = pd.DataFrame(all_records)
            self.logger.info(f"records before filter: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"records after filter: {len(filtered)}")
            return filtered.to_dict("records")

        except Exception as e:
            self.logger.error(f"scrape failed: {e}", exc_info=True)
            return []
        finally:
            self.close()
