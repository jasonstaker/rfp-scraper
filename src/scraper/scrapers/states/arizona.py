# arizona.py
# url: https://app.az.gov/page.aspx/en/rfp/request_browse_public

import logging
from io import StringIO
from urllib.parse import parse_qsl, urlencode, urljoin

import pandas as pd
from bs4 import BeautifulSoup
import requests

from scraper.core.requests_scraper import RequestsScraper
from scraper.config.settings import FALLBACK_CSRF, STATE_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords
from scraper.utils.date_utils import parse_date_generic

from scraper.core.errors import (
    SearchTimeoutError,
    DataExtractionError,
    ScraperError,
)

# a scraper for Arizona RFP data using Requests
class ArizonaScraper(RequestsScraper):

    # modifies: self
    # effects: initializes the scraper with Arizona's RFP url and state variables
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP["arizona"])
        self.logger = logging.getLogger(__name__)
        self.hidden_fields = {}
        self.previous_df = None
        self.current_df = None
        self.page_num = 2
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                           " AppleWebKit/537.36 (KHTML, like Gecko)"
                           " Chrome/126.0.0.0 Safari/537.36",
            "Referer": self.base_url,
            "Content-Type": "application/x-www-form-urlencoded"
        })


    # requires: html_text is a string containing html content
    # effects: returns dict of hidden field names and values
    def _scrape_hidden_fields(self, html_text):
        try:
            soup = BeautifulSoup(html_text, "html.parser")
            return {
                inp["name"]: inp.get("value", "")
                for inp in soup.find_all("input", type="hidden")
                if inp.get("name")
            }
        except Exception as e:
            self.logger.error(f"_scrape_hidden_fields failed: {e}", exc_info=True)
            raise DataExtractionError("Failed to scrape hidden fields") from e


    # requires: self.hidden_fields is a dict
    # effects: builds and returns form data for initial search POST
    def _build_search_payload(self):
        data = {**self.hidden_fields}
        data.update({
            # ...payload fields...
            "CSRFToken": self.hidden_fields.get("CSRFToken", FALLBACK_CSRF),
        })
        return urlencode(data, safe=":/|%")


    # requires: page_num is an integer ≥ 2
    # effects: builds and returns form data for pagination POST
    def _build_pagination_payload(self, page_num):
        focus = page_num - 1
        prev_index = page_num - 2
        data = {
            # ...pagination fields...
            "CSRFToken": self.hidden_fields.get("CSRFToken", FALLBACK_CSRF),
        }
        return urlencode(data, safe=":/|%")


    # modifies: self.hidden_fields, self.current_response, self.page_num
    # effects: performs the initial search and returns first page HTML
    def search(self, **kwargs):
        try:
            resp = self.session.get(self.base_url, timeout=15)
            if resp.status_code != 200:
                self.logger.error(f"GET failed: {resp.status_code}")
                raise SearchTimeoutError("Arizona initial GET failed")
            self.hidden_fields = self._scrape_hidden_fields(resp.text)
            payload = self._build_search_payload()
            resp = self.session.post(self.base_url, data=dict(parse_qsl(payload)), timeout=15)
            if resp.status_code != 200:
                self.logger.error(f"POST failed: {resp.status_code}")
                raise SearchTimeoutError("Arizona initial POST failed")
            self.hidden_fields = self._scrape_hidden_fields(resp.text)
            self.current_response = resp
            self.page_num = 2
            return resp.text
        except requests.exceptions.RequestException as re:
            self.logger.error(f"search HTTP error: {re}", exc_info=False)
            raise ScraperError("Arizona search HTTP error") from re
        except Exception as e:
            self.logger.error(f"search failed: {e}", exc_info=True)
            raise ScraperError("Arizona search failed") from e


    # requires: self.current_response is set
    # modifies: self.hidden_fields, self.current_response, self.page_num
    # effects: fetches and returns next page HTML or raises DataExtractionError if done
    def next_page(self):
        if not getattr(self, "current_response", None):
            raise DataExtractionError("No current response for pagination")
        try:
            payload = self._build_pagination_payload(self.page_num)
            resp = self.session.post(self.base_url, data=dict(parse_qsl(payload)), timeout=15)
            if resp.status_code != 200:
                self.logger.warning(f"pagination POST failed: {resp.status_code}")
                raise SearchTimeoutError("Arizona pagination POST failed")
            new_hidden = self._scrape_hidden_fields(resp.text)
            if "__VIEWSTATE" not in new_hidden:
                self.logger.info("no __VIEWSTATE found, ending pagination")
                raise DataExtractionError("End of pagination")
            self.hidden_fields = new_hidden
            self.current_response = resp
            self.page_num += 1
            return resp.text
        except requests.exceptions.RequestException as re:
            self.logger.error(f"next_page HTTP error: {re}", exc_info=False)
            raise ScraperError("Arizona next_page HTTP error") from re
        except DataExtractionError:
            raise
        except Exception as e:
            self.logger.error(f"next_page failed: {e}", exc_info=True)
            raise ScraperError("Arizona next_page failed") from e


    # requires: page_content is a string containing html
    # modifies: self.current_df
    # effects: parses HTML table and returns list of RFP record dicts
    def extract_data(self, page_content):
        if not page_content:
            self.logger.error("no page_content provided to extract_data")
            raise DataExtractionError("Empty page_content for Arizona extract_data")
        try:
            tables = pd.read_html(StringIO(page_content))
            if len(tables) < 5:
                self.logger.error("expected at least 5 tables, found fewer")
                raise DataExtractionError("Insufficient tables in Arizona extract_data")
            df = tables[4]

            soup = BeautifulSoup(page_content, "html.parser")
            tbl = soup.find("table", id="body_x_grid_grd")
            if not tbl:
                self.logger.error("results table not found in extract_data")
                raise DataExtractionError("Arizona results table not found")
            rows = tbl.select("tbody > tr")
            links = []
            for tr in rows:
                a = tr.find_all("td", recursive=False)[0].find("a", href=True)
                href = a["href"] if a else None
                if href and not href.startswith("http"):
                    href = urljoin(self.base_url, href)
                links.append(href)
            df["link"] = links

            df = df.rename(columns={'Label': 'title', 'Code': 'code', 'End (UTC-7)': 'end_date'})
            df['end_date'] = df['end_date'].apply(lambda x: parse_date_generic(x) if pd.notna(x) else x)
            df = df[['title', 'code', 'end_date', 'link']]

            self.current_df = df
            return df.to_dict("records")
        except ValueError as ve:
            self.logger.error(f"pd.read_html failed: {ve}", exc_info=False)
            raise DataExtractionError("Arizona extract_data HTML parse failed") from ve
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise ScraperError("Arizona extract_data failed") from e


    # modifies: self.hidden_fields, self.current_response, self.page_num, self.previous_df, self.current_df
    # effects: orchestrates search->extract->paginate->filter; returns filtered records
    def scrape(self, **kwargs):
        self.logger.info("starting Arizona scrape")
        all_records = []

        try:
            page = self.search(**kwargs)
        except ScraperError as e:
            self.logger.warning(f"search failed: {e}")
            return []

        if not page:
            self.logger.warning("search() returned no page; aborting Arizona scrape")
            return []

        try:
            all_records.extend(self.extract_data(page))
        except (DataExtractionError, ScraperError) as e:
            self.logger.warning(f"extract_data failed on first page: {e}")
        self.previous_df = self.current_df

        while True:
            try:
                page = self.next_page()
            except ScraperError as e:
                self.logger.warning(f"next_page failed: {e}")
                break
            if not page:
                break
            try:
                all_records.extend(self.extract_data(page))
            except (DataExtractionError, ScraperError) as e:
                self.logger.warning(f"extract_data failed on page {self.page_num - 1}: {e}")

            if self.current_df is not None and self.previous_df is not None and self.current_df.equals(self.previous_df):
                self.logger.info("identical page detected, stopping pagination")
                break
            self.previous_df = self.current_df

        df = pd.DataFrame(all_records)
        self.logger.info(f"total records before filter: {len(df)}")
        filtered = filter_by_keywords(df)
        self.logger.info(f"total records after filter: {len(filtered)}")
        return filtered.to_dict("records")