# colorado.py
# url: https://prd.co.cgiadvantage.com/PRDVSS1X1/Advantage4

import logging

from bs4 import BeautifulSoup
import pandas as pd

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

from scraper.core.selenium_scraper import SeleniumScraper
from scraper.utils.data_utils import filter_by_keywords
from src.config import STATE_RFP_URL_MAP

from scraper.core.errors import (
    SearchTimeoutError,
    ElementNotFoundError,
    DataExtractionError,
    PaginationError,
    ScraperError,
)

# a scraper for Colorado RFP data using Selenium
class ColoradoScraper(SeleniumScraper):

    # modifies: self
    # effects: initializes the scraper with Colorado's RFP url and sets up logging
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP["colorado"])
        self.logger = logging.getLogger(__name__)


    # effects: navigates to the Colorado RFP portal, clicks to display solicitations, and returns True if successful
    def search(self, **kwargs):
        self.logger.info("navigating to Colorado RFP portal")
        try:
            self.driver.get(self.base_url)
            locator = (
                By.XPATH,
                "//div[@data-qa='vss.page.VAXXX03153.carouselView.carousel.solicitations']",
            )
            WebDriverWait(self.driver, 20).until(EC.element_to_be_clickable(locator)).click()
            self.logger.info("clicked 'View Published Solicitations'")
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.ID, "vsspageVVSSX10019gridView1group1cardGridgrid1"))
            )
            self.logger.info("solicitations table loaded")
            return True

        except TimeoutException as te:
            self.logger.error(f"search timeout: {te}", exc_info=False)
            raise SearchTimeoutError("Colorado search timed out") from te

        except NoSuchElementException as ne:
            self.logger.error(f"search missing element: {ne}", exc_info=False)
            raise ElementNotFoundError("Colorado search element not found") from ne

        except WebDriverException as we:
            self.logger.error(f"search WebDriver error: {we}", exc_info=True)
            raise ScraperError("Colorado search WebDriver error") from we

        except Exception as e:
            self.logger.error(f"search() failed: {e}", exc_info=True)
            raise ScraperError("Colorado search failed") from e


    # requires: page_source is a string containing HTML page source
    # effects: parses the solicitations table from page_source and returns a list of raw record dicts
    def extract_data(self, page_source):
        if not page_source:
            self.logger.error("no page_source provided to extract_data")
            raise DataExtractionError("No page_source provided to Colorado extract_data")

        try:
            soup = BeautifulSoup(page_source, "html.parser")
            table = soup.find("table", id="vsspageVVSSX10019gridView1group1cardGridgrid1")
            if not table:
                self.logger.error("results table not found")
                raise ElementNotFoundError("Colorado results table not found")

            tbody = table.find("tbody")
            if not tbody:
                self.logger.error("no <tbody> found in table")
                raise ElementNotFoundError("Colorado results <tbody> not found")

            records = []
            for row in tbody.find_all("tr"):
                cols = row.find_all("td")
                if len(cols) < 5:
                    continue
                anchor = cols[3].find("a")
                if not anchor:
                    continue
                records.append({
                    "title": cols[1].get_text(strip=True),
                    "code": anchor.get_text(strip=True),
                    "end_date": cols[4].find("span").get_text(strip=True) if cols[4].find("span") else "",
                    "link": STATE_RFP_URL_MAP["colorado"],
                })
            return records

        except (ElementNotFoundError, DataExtractionError):
            raise

        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise DataExtractionError("Colorado extract_data failed") from e


    # effects: orchestrates search -> extract/paginate -> filter; returns filtered records or raises on failure
    def scrape(self, **kwargs):
        self.logger.info("starting Colorado scrape")
        all_records = []

        try:
            success = self.search(**kwargs)
            if not success:
                self.logger.warning("search() returned False; retryable failure")
                raise SearchTimeoutError("Colorado search() returned False")

            page_num = 1
            while True:
                self.logger.info(f"processing page {page_num}")
                try:
                    page_source = self.driver.page_source
                except WebDriverException as we:
                    self.logger.error(f"failed to get page_source: {we}", exc_info=False)
                    raise ScraperError(f"failed to get page_source: {we}") from we

                batch = self.extract_data(page_source)
                if page_num == 1 and not batch:
                    self.logger.error("extract_data returned no records on first page; retryable failure")
                    raise DataExtractionError("Colorado extract_data returned empty on first page")

                all_records.extend(batch)

                try:
                    next_buttons = self.driver.find_elements(By.CLASS_NAME, "css-1yn6b58")
                except WebDriverException as we:
                    self.logger.error(f"failed to find next buttons: {we}", exc_info=False)
                    raise PaginationError(f"failed to find next buttons: {we}") from we

                next_btn = None
                for btn in next_buttons:
                    try:
                        if btn.is_displayed() and btn.is_enabled():
                            next_btn = btn
                            break
                    except WebDriverException:
                        continue

                if not next_btn:
                    self.logger.info("no clickable 'Next' button; stopping pagination")
                    break

                try:
                    next_btn.click()
                except WebDriverException as we:
                    self.logger.error(f"failed to click next button: {we}", exc_info=False)
                    raise PaginationError(f"failed to click next button: {we}") from we

                page_num += 1

            self.logger.info("completed parsing")
            df = pd.DataFrame(all_records)
            self.logger.info("applying filters")
            filtered = filter_by_keywords(df)
            self.logger.info(f"found {len(filtered)} records after filtering")
            return filtered.to_dict("records")

        except (SearchTimeoutError, ElementNotFoundError, DataExtractionError, PaginationError, ScraperError):
            raise

        except Exception as e:
            self.logger.error(f"scrape failed: {e}", exc_info=True)
            raise ScraperError("Colorado scrape failed") from e
