# california.py
# url: https://caleprocure.ca.gov/pages/Events-BS3/event-search.aspx

import logging
from io import StringIO

from bs4 import BeautifulSoup
import pandas as pd

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from scraper.core.selenium_scraper import SeleniumScraper
from src.config import BUSINESS_UNIT_DICT, STATE_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords

from scraper.core.errors import (
    SearchTimeoutError,
    DataExtractionError,
    ScraperError,
    ElementNotFoundError,
)

# a scraper for California RFP data using Selenium
class CaliforniaScraper(SeleniumScraper):

    # modifies: self
    # effects: initializes the scraper with California's RFP url and sets up logging
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP["california"])
        self.logger = logging.getLogger(__name__)


    # modifies: self.driver
    # effects: navigates to the California RFP page, waits for the table to load, and returns page source
    def search(self, **kwargs):
        self.logger.info("navigating to California RFP page")
        try:
            self.driver.get(self.base_url)
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="datatable-ready"]'))
            )
            return self.driver.page_source
        except TimeoutException as te:
            self.logger.error(f"search timeout: {te}", exc_info=False)
            raise SearchTimeoutError("California search timed out") from te
        except NoSuchElementException as ne:
            self.logger.error(f"search missing element: {ne}", exc_info=False)
            raise ElementNotFoundError("California search element not found") from ne
        except Exception as e:
            self.logger.error(f"search failed: {e}", exc_info=True)
            raise ScraperError("California search failed") from e


    # requires: page_source is a string containing html page source
    # effects: parses the HTML table, constructs links, and returns a list of record dicts
    def extract_data(self, page_source):
        if not page_source:
            self.logger.error("no page_source provided to extract_data")
            raise DataExtractionError("California extract_data received empty page_source")

        try:
            soup = BeautifulSoup(page_source, "html.parser")
            table = soup.find("table", id="datatable-ready")
            if not table:
                self.logger.error("datatable-ready table not found")
                raise ElementNotFoundError("California results table not found in extract_data")

            df = pd.read_html(StringIO(str(table)))[0]
            links = []
            for _, row in df.iterrows():
                department_name = row.iloc[3]
                event_id = row.iloc[1]
                bu = BUSINESS_UNIT_DICT.get(department_name)
                url = f"https://caleprocure.ca.gov/event/{bu}/{event_id}" if bu else None
                links.append(url)

            mapped = pd.DataFrame({
                "title": df.iloc[:, 2],
                "code": df.iloc[:, 1],
                "end_date": df.iloc[:, 4],
                "link": links,
            })
            mapped["link"] = mapped["link"].fillna(self.base_url)
            return mapped.to_dict("records")
        except ValueError as ve:
            self.logger.error(f"pd.read_html failed: {ve}", exc_info=False)
            raise DataExtractionError("California extract_data HTML parsing failed") from ve
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise ScraperError("California extract_data failed") from e


    # effects: orchestrates search -> extract -> filter; returns filtered records
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for California")
        try:
            html = self.search(**kwargs)
            if not html:
                self.logger.warning("Search returned no HTML; aborting scrape")
                raise ScraperError("California scrape aborted due to empty HTML")

            self.logger.info("Processing data")
            records = self.extract_data(html)
            df = pd.DataFrame(records)
            self.logger.info("Applying filters")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Found {len(filtered)} records after filtering")
            return filtered.to_dict("records")
        except (SearchTimeoutError, ElementNotFoundError, DataExtractionError, ScraperError) as e:
            self.logger.error(f"Scrape failed: {e}", exc_info=True)
            raise
        except Exception as e:
            self.logger.error(f"Scrape failed: {e}", exc_info=True)
            raise ScraperError("California scrape failed") from e
