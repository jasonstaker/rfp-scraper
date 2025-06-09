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

# a scraper class for california rfp data using selenium
class CaliforniaScraper(SeleniumScraper):
    # requires: nothing
    # modifies: self
    # effects: initializes the scraper with california's rfp url and sets up logging
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP["california"])
        self.logger = logging.getLogger(__name__)

    # requires: nothing
    # modifies: self.driver (through selenium operations)
    # effects: navigates to the california rfp page, waits for the table to load, and returns the page source if successful, otherwise none
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
            raise
        except NoSuchElementException as ne:
            self.logger.error(f"search missing element: {ne}", exc_info=False)
            raise
        except Exception as e:
            self.logger.error(f"search failed: {e}", exc_info=True)
            raise

    # requires: page_source is a string containing html page source
    # modifies: nothing
    # effects: parses the html table from page_source, constructs links, and returns a list of records
    def extract_data(self, page_source):
        self.logger.info("parsing HTML table for California records")
        if not page_source:
            self.logger.error("no page_source provided to extract_data")
            raise

        try:
            soup = BeautifulSoup(page_source, "html.parser")
            table = soup.find("table", id="datatable-ready")
            if not table:
                self.logger.error("datatable-ready table not found")
                raise

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
            raise
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise

    # requires: nothing
    # modifies: self.driver (through selenium operations)
    # effects: orchestrates the scraping process: search → extract → filter; returns filtered records, raises exception on failure
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for California")
        try:
            html = self.search(**kwargs)
            if not html:
                self.logger.warning("Search returned no HTML; aborting scrape")
                raise

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