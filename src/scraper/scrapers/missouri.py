# missouri.py
# URL: https://ewqg.fa.us8.oraclecloud.com/fscmUI/redwood/negotiation-abstracts/view/abstractlisting?prcBuId=300000005255687

import logging
import time
import re
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

import pytz
import pandas as pd

from scraper.core.selenium_scraper import SeleniumScraper
from scraper.config.settings import STATE_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords

# a scraper class for Missouri bid opportunities using Selenium
class MissouriScraper(SeleniumScraper):

    # requires: nothing
    # modifies: self
    # effects: initializes the scraper with Missouri’s negotiation abstracts URL and configures logging
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP.get("missouri"))
        self.logger = logging.getLogger(__name__)

    # requires: nothing
    # modifies: self.driver
    # effects: navigates to the Missouri page and waits up to 20s for the UL container to appear
    def search(self, **kwargs):
        if not self.base_url.startswith("http"):
            self.logger.error("Invalid base_url for Missouri scraper")
            return False

        self.driver.get(self.base_url)
        deadline = time.time() + 20
        while time.time() < deadline:
            try:
                self.driver.find_element(By.ID, "ui-id-2")
                return True
            except NoSuchElementException:
                time.sleep(1)

        self.logger.error("Could not find <ul id='ui-id-2'> on Missouri page")
        return False

    # requires: UL is present in DOM
    # modifies: self.driver
    # effects: scrolls the window twice until the page height stabilizes to trigger lazy loading
    def _ensure_all_loaded(self):
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

    # requires: items are fully loaded in the UL
    # modifies: nothing
    # effects: parses each <li> into a record dict and returns a DataFrame
    def extract_data(self):
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
                label = title or raw

                m = re.search(r"\b[A-Z][A-Z ]*-FY\d{2}-\d{4}-SL\b", head)
                code = m.group(0) if m else ""

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
                    "Label": label,
                    "Code": code,
                    "End (UTC-7)": end_str,
                    "Keyword Hits": "",
                    "Link": link,
                })

            except Exception as e:
                snippet = li.get_attribute("outerHTML")[:200].replace("\n", " ")
                self.logger.warning(f"Skipping LI due to {e!r}. Snippet: {snippet}…")
                continue

        return pd.DataFrame(records)

    # requires: nothing
    # modifies: nothing
    # effects: orchestrates search → extract_data → filter_by_keywords; returns list of filtered records
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Missouri")
        try:
            if not self.search(**kwargs):
                self.logger.error("Search failed; aborting Missouri scrape")
                return
            df = self.extract_data()
            self.logger.info(f"Total raw records before filtering: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total records after filtering: {len(filtered)}")
            return filtered.to_dict("records")

        except Exception as e:
            self.logger.error(f"Missouri scrape failed: {e}", exc_info=True)
            raise
