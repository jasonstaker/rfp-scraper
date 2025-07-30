# miami_dade.py
# url: https://supplier.miamidade.gov/psc/EXTSUPP_1/SUPPLIER/ERP/c/SCP_PUBLIC_MENU_FL.SCP_PUB_BID_CMP_FL.GBL

import logging

from bs4 import BeautifulSoup
import pandas as pd

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

from scraper.core.selenium_scraper import SeleniumScraper
from src.config import COUNTY_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords

from scraper.core.errors import (
    SearchTimeoutError,
    ElementNotFoundError,
    DataExtractionError,
    ScraperError,
)

# a scraper for Miami Dade RFP data using Selenium
class MiamiDadeScraper(SeleniumScraper):

    # modifies: self
    # effects: initializes the scraper with Miami Dade's RFP URL and sets up logging
    def __init__(self):
        super().__init__(COUNTY_RFP_URL_MAP["florida"]["miami dade"])
        self.logger = logging.getLogger(__name__)


    # modifies: self.driver
    # effects: navigates twice to the Miami Dade portal URL in the same browser window, waits for the bidding table to load, returns page source
    def search(self, **kwargs):
        self.logger.info("Navigating to Miami Dade RFP portal")
        try:
            self.driver.get(self.base_url)
            self.driver.get(self.base_url)

            WebDriverWait(self.driver, 20).until(
                EC.presence_of_all_elements_located((
                    By.XPATH,
                    '/html/body/form/div[2]/div[4]/div[2]/div/div/div/div/div/div[2]/div[2]/div/div[2]/table'
                ))
            )
            return self.driver.page_source
        except TimeoutException as te:
            self.logger.error(f"search timeout: {te}", exc_info=False)
            raise SearchTimeoutError("Miami Dade search timed out") from te
        except NoSuchElementException as ne:
            self.logger.error(f"search missing element: {ne}", exc_info=False)
            raise ElementNotFoundError("Miami Dade search element not found") from ne
        except WebDriverException as we:
            self.logger.error(f"search WebDriver error: {we}", exc_info=True)
            raise ScraperError("Miami Dade search WebDriver error") from we
        except Exception as e:
            self.logger.error(f"search() failed: {e}", exc_info=True)
            raise ScraperError("Miami Dade search failed") from e


    # requires: page_source is a string of HTML
    # effects: parses the second "Bidding Event Information" table into record dicts
    def extract_data(self, page_source):
        self.logger.info("Parsing Miami Dade bidding tables")
        if not page_source:
            self.logger.error("No page_source provided to extract_data")
            raise DataExtractionError("Empty page_source for Miami Dade extract_data")

        try:
            soup = BeautifulSoup(page_source, "html.parser")
            tables = soup.find_all("table", {"title": "Bidding Event Information"})
            if len(tables) < 2:
                self.logger.error(f"Expected ≥2 tables, found {len(tables)}")
                raise ElementNotFoundError("Miami Dade bidding table not found")

            table = tables[1]
            rows = table.select("tr.ps_grid-row")
            if not rows:
                all_tr = table.find_all("tr")
                rows = all_tr[1:] if len(all_tr) > 1 else []
            if not rows:
                self.logger.error("No data rows found in the bidding table")
                raise DataExtractionError("Miami Dade no data rows in bidding table")

            records = []
            for row in rows:
                cols = row.find_all("td")
                if len(cols) < 6:
                    continue
                title = cols[0].get_text(strip=True)
                code = cols[2].get_text(strip=True)
                end_date = cols[7].get_text(strip=True)
                records.append({
                    "title": title,
                    "code": code,
                    "end_date": end_date,
                    "link": COUNTY_RFP_URL_MAP["florida"]["miami dade"],
                })

            return records
        except (ElementNotFoundError, DataExtractionError):
            raise
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise DataExtractionError("Miami Dade extract_data failed") from e


    # effects: orchestrates search -> extract_data -> filter; returns filtered records
    def scrape(self, **kwargs):
        self.logger.info("Starting Miami Dade scrape")
        try:
            html = self.search(**kwargs)
            records = self.extract_data(html)
            df = pd.DataFrame(records)
            self.logger.info(f"Total raw records before filtering: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Found {len(filtered)} records after filtering")
            return filtered.to_dict("records")
        except (SearchTimeoutError, ElementNotFoundError, DataExtractionError, ScraperError):
            raise
        except Exception as e:
            self.logger.error(f"scrape failed: {e}", exc_info=True)
            raise ScraperError("Miami Dade scrape failed") from e
