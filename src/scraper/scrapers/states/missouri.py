# missouri.py
# url: https://ewqg.fa.us8.oraclecloud.com/fscmUI/redwood/negotiation-abstracts/view/abstractlisting?prcBuId=300000005255687

import logging
import time
import re
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, WebDriverException

import pytz
import pandas as pd

from scraper.core.selenium_scraper import SeleniumScraper
from scraper.utils.data_utils import filter_by_keywords
from scraper.config.settings import STATE_RFP_URL_MAP

from scraper.core.errors import (
    SearchTimeoutError,
    ElementNotFoundError,
    DataExtractionError,
    PaginationError,
    ScraperError,
)

# a scraper for Missouri RFP data using Selenium
class MissouriScraper(SeleniumScraper):

    # modifies: self
    # effects: initializes the scraper with Missouri’s negotiation abstracts URL and configures logging
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP.get("missouri"))
        self.logger = logging.getLogger(__name__)


    # modifies: self.driver
    # effects: navigates to the Missouri page and waits up to 20s for the UL container to appear
    def search(self, **kwargs):
        if not self.base_url or not self.base_url.startswith("http"):
            self.logger.error("Invalid base_url for Missouri scraper")
            raise ScraperError("Missouri base_url invalid")

        self.driver.get(self.base_url)
        deadline = time.time() + 20
        while time.time() < deadline:
            try:
                self.driver.find_element(By.ID, "ui-id-2")
                return True
            except NoSuchElementException:
                time.sleep(1)

        self.logger.error("Could not find <ul id='ui-id-2'> on Missouri page")
        raise SearchTimeoutError("Missouri search timed out waiting for list")


    # requires: UL is present in DOM
    # modifies: self.driver
    # effects: scrolls the window twice until the page height stabilizes to trigger lazy loading
    def _ensure_all_loaded(self):
        try:
            last_height = 0
            for pass_num in range(2):
                self.logger.info(f"Scroll pass {pass_num+1}/2 to load items")
                while True:
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)
                    new_height = self.driver.execute_script("return document.body.scrollHeight;")
                    if new_height == last_height:
                        break
                    last_height = new_height
                time.sleep(1)
        except WebDriverException as we:
            self.logger.error(f"_ensure_all_loaded failed: {we}", exc_info=False)
            raise PaginationError("Missouri lazy-load scroll failed") from we


    # requires: items are fully loaded in the UL
    # effects: parses each <li> into a record dict and returns a DataFrame or raises
    def extract_data(self):
        try:
            self._ensure_all_loaded()
            ul = self.driver.find_element(By.ID, "ui-id-2")
            items = ul.find_elements(By.TAG_NAME, "li")
            self.logger.info(f"Found {len(items)} items in Missouri list")

            pacific = pytz.timezone("US/Pacific")
            records = []
            for li in items:
                try:
                    span = li.find_element(By.CSS_SELECTOR, "oj-highlight-text span")
                    raw = span.text.strip()
                    head, _, title = raw.partition(": ")
                    title = title or raw

                    code = None
                    try:
                        colon_index = raw.index(":")
                        before_colon = raw[:colon_index]
                        last_paren_index = before_colon.rindex(')')
                        code = before_colon[last_paren_index + 1:].strip()
                    except ValueError:
                        pass

                    end_str = ""
                    try:
                        dt_elem = li.find_element(
                            By.CSS_SELECTOR,
                            "oj-input-date-time[id$='CloseDate'] .oj-text-field-readonly"
                        )
                        raw_dt = dt_elem.text.strip()
                        dt = datetime.strptime(raw_dt, "%m/%d/%Y %I:%M %p")
                        dt = pacific.localize(dt)
                        end_str = dt.strftime("%Y-%m-%d %H:%M:%S %Z")
                    except Exception:
                        end_str = ""

                    link = self.base_url
                    records.append({
                        "title": title,
                        "code": code,
                        "end_date": end_str,
                        "link": link,
                    })
                except Exception as e:
                    snippet = li.get_attribute("outerHTML")[:200].replace("\n", " ")
                    self.logger.warning(f"Skipping LI due to {e!r}. Snippet: {snippet}…")
                    continue

            return pd.DataFrame(records)
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise DataExtractionError("Missouri extract_data failed") from e


    # effects: orchestrates search -> extract_data -> filter_by_keywords; returns list of filtered records or raises
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Missouri")
        try:
            if not self.search(**kwargs):
                raise ScraperError("Missouri search did not initialize")
            df = self.extract_data()
            self.logger.info(f"Total raw records before filtering: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total records after filtering: {len(filtered)}")
            return filtered.to_dict("records")
        except (SearchTimeoutError, DataExtractionError, PaginationError, ScraperError):
            raise
        except Exception as e:
            self.logger.error(f"Missouri scrape failed: {e}", exc_info=True)
            raise ScraperError("Missouri scrape failed") from e