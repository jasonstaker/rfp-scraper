# california.py
# url: https://caleprocure.ca.gov/pages/Events-BS3/event-search.aspx

import logging
import time
from io import StringIO

from bs4 import BeautifulSoup
import pandas as pd

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from scraper.core.selenium_scraper import SeleniumScraper
from scraper.config.settings import BUSINESS_UNIT_DICT, STATE_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords


class CaliforniaScraper(SeleniumScraper):
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP["california"])
        self.logger = logging.getLogger(__name__)

    def search(self, **kwargs):
        # navigate to the California RFP page and wait for the 'datatable-ready' table
        self.logger.info("navigating to California RFP page")
        try:
            self.driver.get(self.base_url)
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="datatable-ready"]'))
            )
            time.sleep(2)  # give JS time to populate rows
            return self.driver.page_source
        except TimeoutException as te:
            self.logger.error(f"search timeout: {te}", exc_info=False)
            return None
        except NoSuchElementException as ne:
            self.logger.error(f"search missing element: {ne}", exc_info=False)
            return None
        except Exception as e:
            self.logger.error(f"search failed: {e}", exc_info=True)
            return None

    def extract_data(self, page_source):
        # parse the HTML table (#datatable-ready) into a list of dicts
        self.logger.info("parsing HTML table for California records")
        if not page_source:
            self.logger.error("no page_source provided to extract_data")
            return []

        try:
            soup = BeautifulSoup(page_source, "html.parser")
            table = soup.find("table", id="datatable-ready")
            if not table:
                self.logger.error("datatable-ready table not found")
                return []

            df = pd.read_html(StringIO(str(table)))[0]
            links = []
            for _, row in df.iterrows():
                department_name = row.iloc[3]  # department column
                event_id = row.iloc[1]         # event ID column
                bu = BUSINESS_UNIT_DICT.get(department_name)
                if bu:
                    url = f"https://caleprocure.ca.gov/event/{bu}/{event_id}"
                else:
                    url = None
                links.append(url)

            mapped = pd.DataFrame(
                {
                    "Label": df.iloc[:, 2],
                    "Code": df.iloc[:, 1],
                    "End (UTC-7)": df.iloc[:, 4],
                    "Type": "RFP",
                    "Keyword Hits": "",
                    "Link": links,
                }
            )
            mapped["Link"] = mapped["Link"].fillna(
                "https://caleprocure.ca.gov/pages/Events-BS3/event-search.aspx"
            )
            return mapped.to_dict("records")
        except ValueError as ve:
            self.logger.error(f"pd.read_html failed: {ve}", exc_info=False)
            return []
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            return []

    def scrape(self, **kwargs):
        # high-level orchestration: search → extract → filter → return
        self.logger.info("Starting scrape for California")
        try:
            html = self.search(**kwargs)
            if not html:
                self.logger.warning("Search returned no HTML; aborting scrape")
                return []

            self.logger.info("Processing data")
            records = self.extract_data(html)
            df = pd.DataFrame(records)
            self.logger.info("Applying filters")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Found {len(filtered)} records after filtering")
            return filtered.to_dict("records")
        except Exception as e:
            self.logger.error(f"Scrape failed: {e}", exc_info=True)
            # Raise so main.py can retry
            raise
