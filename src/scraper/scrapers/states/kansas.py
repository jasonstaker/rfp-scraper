# kansas.py
# url: https://supplier.sok.ks.gov/psc/sokfsprdsup/SUPPLIER/ERP/c/SCP_PUBLIC_MENU_FL.SCP_PUB_BID_CMP_FL.GBL

import logging

from bs4 import BeautifulSoup
import pandas as pd

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

from scraper.core.selenium_scraper import SeleniumScraper
from src.config import STATE_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords

from scraper.core.errors import (
    SearchTimeoutError,
    ElementNotFoundError,
    DataExtractionError,
    ScraperError,
)

# a scraper for Kansas RFP data using Selenium
class KansasScraper(SeleniumScraper):

    # modifies: self
    # effects: initializes the scraper with Kansas's RFP URL and sets up logging
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP["kansas"])
        self.logger = logging.getLogger(__name__)


    # modifies: self.driver
    # effects: navigates to the Kansas portal, waits for the bidding table to load, returns page source
    def search(self, **kwargs):
        self.logger.info("navigating to Kansas RFP portal")
        try:
            self.driver.get(self.base_url)
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_all_elements_located((
                    By.XPATH,
                    '/html/body/form/div[2]/div[4]/div[2]/div/div/div/div/div[2]/'
                    'div[2]/div[2]/div/div[2]/table'
                ))
            )
            return self.driver.page_source
        except TimeoutException as te:
            self.logger.error(f"search timeout: {te}", exc_info=False)
            raise SearchTimeoutError("Kansas search timed out") from te
        except NoSuchElementException as ne:
            self.logger.error(f"search missing element: {ne}", exc_info=False)
            raise ElementNotFoundError("Kansas search element not found") from ne
        except WebDriverException as we:
            self.logger.error(f"search WebDriver error: {we}", exc_info=True)
            raise ScraperError("Kansas search WebDriver error") from we
        except Exception as e:
            self.logger.error(f"search() failed: {e}", exc_info=True)
            raise ScraperError("Kansas search failed") from e


    # requires: page_source is a string of HTML
    # effects: parses the second "Bidding Event Information" table into record dicts
    def extract_data(self, page_source):
        self.logger.info("parsing Kansas bidding tables")
        if not page_source:
            self.logger.error("no page_source provided to extract_data")
            raise DataExtractionError("Empty page_source for Kansas extract_data")

        try:
            soup = BeautifulSoup(page_source, "html.parser")
            tables = soup.find_all("table", {"title": "Bidding Event Information"})
            if len(tables) < 2:
                self.logger.error(f"expected ≥2 tables, found {len(tables)}")
                raise ElementNotFoundError("Kansas bidding table not found")

            table = tables[1]
            rows = table.select("tr.ps_grid-row")
            if not rows:
                all_tr = table.find_all("tr")
                rows = all_tr[1:] if len(all_tr) > 1 else []
            if not rows:
                self.logger.error("no data rows found in the bidding table")
                raise DataExtractionError("Kansas no data rows in bidding table")

            records = []
            for row in rows:
                cols = row.find_all("td")
                if len(cols) < 6:
                    continue
                name = cols[0].get_text(strip=True)
                code = cols[2].get_text(strip=True)
                end_date = cols[5].get_text(strip=True)
                records.append({
                    "title": name,
                    "code": code,
                    "end_date": end_date,
                    "link": STATE_RFP_URL_MAP["kansas"],
                })

            return records
        except (ElementNotFoundError, DataExtractionError):
            raise
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise DataExtractionError("Kansas extract_data failed") from e


    # effects: orchestrates search -> extract_data -> filter; returns filtered records
    def scrape(self, **kwargs):
        self.logger.info("starting Kansas scrape")
        try:
            html = self.search(**kwargs)
            records = self.extract_data(html)
            df = pd.DataFrame(records)
            filtered = filter_by_keywords(df)
            self.logger.info(f"found {len(filtered)} records after filtering")
            return filtered.to_dict("records")
        except (SearchTimeoutError, ElementNotFoundError, DataExtractionError, ScraperError):
            raise
        except Exception as e:
            self.logger.error(f"scrape failed: {e}", exc_info=True)
            raise ScraperError("Kansas scrape failed") from e
