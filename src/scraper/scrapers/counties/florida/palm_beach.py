# palm_beach.py
# url: https://pbcvssp.pbc.gov/vssprd/Advantage4

import logging
import time

from bs4 import BeautifulSoup
import pandas as pd

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

from scraper.core.selenium_scraper import SeleniumScraper
from scraper.utils.data_utils import filter_by_keywords
from src.config import COUNTY_RFP_URL_MAP

from scraper.core.errors import (
    SearchTimeoutError,
    ElementNotFoundError,
    DataExtractionError,
    PaginationError,
    ScraperError,
)

# a scraper for Palm Beach RFP data using Selenium
class PalmBeachScraper(SeleniumScraper):

    # modifies: self
    # effects: initializes the scraper with Palm Beach's RFP url and sets up logging
    def __init__(self):
        super().__init__(COUNTY_RFP_URL_MAP["florida"]["palm beach"])
        self.logger = logging.getLogger(__name__)


    # effects: navigates to Palm Beach portal, navigates carousel, clicks solicitations, returns True if successful
    def search(self, **kwargs):
        self.logger.info("Navigating to Palm Beach RFP portal")
        try:
            self.driver.get(self.base_url)
            next_carousel = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.XPATH,
                    "/html/body/div[1]/as-main-app/adv-view-mgr/div[3]/main/"
                    "div[1]/div[2]/div[2]/section[2]/adv-custom-carousel-page/"
                    "div[4]/carousel-component4/div[1]/div[1]/div[3]/a"
                ))
            )
            next_carousel.click()
            self.logger.info("Clicked initial carousel Next arrow")

            button_locator = (
                By.XPATH,
                "//div[@data-qa='vss.page.VAXXX03153.carouselView.carousel.solicitations']",
            )
            WebDriverWait(self.driver, 20).until(
                EC.element_to_be_clickable(button_locator)
            ).click()
            self.logger.info("Clicked 'View Published Solicitations'")

            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located(
                    (By.ID, "vsspageVVSSX10019gridView1group1cardGridgrid1")
                )
            )
            self.logger.info("Solicitations table loaded")
            return True

        except TimeoutException as te:
            self.logger.error(f"search timeout: {te}", exc_info=False)
            raise SearchTimeoutError("Palm Beach search timed out") from te
        except NoSuchElementException as ne:
            self.logger.error(f"search missing element: {ne}", exc_info=False)
            raise ElementNotFoundError("Palm Beach search element not found") from ne
        except WebDriverException as we:
            self.logger.error(f"search WebDriver error: {we}", exc_info=True)
            raise ScraperError("Palm Beach search WebDriver error") from we
        except Exception as e:
            self.logger.error(f"search failed: {e}", exc_info=True)
            raise ScraperError("Palm Beach search failed") from e


    # requires: page_source is a string containing html
    # effects: parses the solicitations table into standardized record dicts
    def extract_data(self, page_source):
        if not page_source:
            self.logger.error("No page_source provided to extract_data")
            raise DataExtractionError("Empty page_source for Palm Beach extract_data")

        try:
            soup = BeautifulSoup(page_source, "html.parser")
            table = soup.find("table", id="vsspageVVSSX10019gridView1group1cardGridgrid1")
            if not table:
                self.logger.error("Results table not found")
                raise ElementNotFoundError("Palm Beach results table not found")

            tbody = table.find("tbody")
            if not tbody:
                self.logger.error("No <tbody> found in table")
                raise ElementNotFoundError("Palm Beach results <tbody> not found")

            records = []
            for row in tbody.find_all("tr"):
                cols = row.find_all("td")
                if len(cols) < 5:
                    continue

                title = cols[1].get_text(strip=True)
                anchor = cols[3].find("a")
                if not anchor:
                    continue
                code = anchor.get_text(strip=True)
                link = COUNTY_RFP_URL_MAP["florida"]["palm beach"]

                date_span = cols[4].find("span")
                raw_date = date_span.get_text(strip=True) if date_span else ""
                records.append({
                    "title": title,
                    "code": code,
                    "end_date": raw_date,
                    "link": link,
                })

            return records
        except (ElementNotFoundError, DataExtractionError):
            raise
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise DataExtractionError("Palm Beach extract_data failed") from e


    # modifies: self.driver
    # effects: orchestrates search->extract->paginate->filter; returns filtered records or raises
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Palm Beach")
        try:
            if not self.search(**kwargs):
                raise ScraperError("Palm Beach search did not initialize")

            all_records = []
            page_num = 1
            while True:
                self.logger.info(f"Processing page {page_num}")
                page_source = self.driver.page_source
                batch = self.extract_data(page_source)
                if page_num == 1 and not batch:
                    self.logger.error("No records on first page; retryable failure")
                    raise DataExtractionError("Palm Beach extract_data returned empty on first page")
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
                    self.logger.info("No clickable 'Next' button; stopping pagination")
                    break

                try:
                    next_btn.click()
                except WebDriverException as we:
                    self.logger.error(f"failed to click next button: {we}", exc_info=False)
                    raise PaginationError(f"failed to click next button: {we}") from we

                page_num += 1
                time.sleep(1)

            df = pd.DataFrame(all_records)
            self.logger.info(f"Total raw records before filtering: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total records after filtering: {len(filtered)}")
            return filtered.to_dict("records")
        except (SearchTimeoutError, ElementNotFoundError, DataExtractionError, PaginationError, ScraperError):
            raise
        except Exception as e:
            self.logger.error(f"Palm Beach scrape failed: {e}", exc_info=True)
            raise ScraperError("Palm Beach scrape failed") from e
