# west_virginia.py
# URL: https://prd311.wvoasis.gov/PRDVSS1X1ERP/Advantage4

import logging

from bs4 import BeautifulSoup
import pandas as pd

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

from scraper.core.selenium_scraper import SeleniumScraper
from scraper.utils.data_utils import filter_by_keywords
from scraper.config.settings import STATE_RFP_URL_MAP
from scraper.core.errors import (
    SearchTimeoutError,
    ElementNotFoundError,
    DataExtractionError,
    ScraperError,
)

# a scraper for West Virginia RFP data using Selenium
class WestVirginiaScraper(SeleniumScraper):

    # modifies: self
    # effects: initializes the scraper with West Virginia's RFP url and sets up logging
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP["west virginia"])
        self.logger = logging.getLogger(__name__)


    # effects: navigates to the West Virginia RFP portal, clicks 'view published solicitations', and waits for the table
    def search(self, **kwargs):
        self.logger.info("Navigating to West Virginia RFP portal")
        try:
            self.driver.get(self.base_url)
            button_locator = (
                By.XPATH,
                "/html/body/div[1]/as-main-app/adv-view-mgr/div[3]/main/div[1]/div[2]/div[2]/section[2]/adv-custom-carousel-page/div[4]/carousel-component4/div[1]/div[1]/div[2]/div[2]/div[4]/div",
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
            self.logger.error(f"Search timeout: {te}", exc_info=False)
            raise SearchTimeoutError("West Virginia search timed out") from te
        except NoSuchElementException as ne:
            self.logger.error(f"Search element not found: {ne}", exc_info=False)
            raise ElementNotFoundError("West Virginia search element not found") from ne
        except WebDriverException as we:
            self.logger.error(f"Search WebDriver error: {we}", exc_info=True)
            raise ScraperError("West Virginia search WebDriver error") from we
        except Exception as e:
            self.logger.error(f"Search failed: {e}", exc_info=True)
            raise ScraperError("West Virginia search failed") from e


    # requires: page_source is a string containing html
    # effects: parses the solicitations table and returns a list of raw records
    def extract_data(self):
        page_source = self.driver.page_source
        if not page_source:
            self.logger.error("No page_source provided to extract_data")
            raise DataExtractionError("West Virginia missing page source")

        try:
            soup = BeautifulSoup(page_source, "html.parser")
            table = soup.find("table", id="vsspageVVSSX10019gridView1group1cardGridgrid1")
            if not table:
                self.logger.error("Results table not found")
                raise ElementNotFoundError("West Virginia results table not found")

            tbody = table.find("tbody")
            if not tbody:
                self.logger.error("No <tbody> found in table")
                raise ElementNotFoundError("West Virginia table body not found")

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
                link = STATE_RFP_URL_MAP["west virginia"]

                date_span = cols[4].find("span")
                raw_date = date_span.get_text(strip=True) if date_span else ""
                end_date = raw_date

                records.append({
                    "title": title,
                    "code": code,
                    "end_date": end_date,
                    "link": link,
                })

            return records

        except (ElementNotFoundError, DataExtractionError):
            raise
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise DataExtractionError("West Virginia extract_data failed") from e


    # effects: orchestrates the scraping process: search -> extract -> paginate -> filter
    def scrape(self, **kwargs):
        self.logger.info("Starting West Virginia scrape")
        try:
            if not self.search(**kwargs):
                self.logger.warning("Search returned False; aborting")
                raise ScraperError("West Virginia scrape aborted due to failed search")

            page_num = 1
            all_records = []

            while True:
                self.logger.info(f"Processing page {page_num}")
                batch = self.extract_data()
                if page_num == 1 and not batch:
                    self.logger.error("No records found on first page; aborting")
                    raise DataExtractionError("West Virginia extract_data returned empty on first page")
                all_records.extend(batch)

                try:
                    next_buttons = self.driver.find_elements(By.CLASS_NAME, "css-1yn6b58")
                except WebDriverException as we:
                    self.logger.error(f"Failed to locate next buttons: {we}", exc_info=False)
                    break

                next_btn = None
                for btn in next_buttons:
                    if btn.is_displayed() and btn.is_enabled():
                        next_btn = btn
                        break

                if not next_btn:
                    self.logger.info("No clickable 'Next' button; ending pagination")
                    break

                try:
                    next_btn.click()
                except WebDriverException as we:
                    self.logger.error(f"Failed to click next button: {we}", exc_info=False)
                    raise ScraperError("West Virginia next_page click failed") from we

                page_num += 1

            df = pd.DataFrame(all_records)
            self.logger.info("Applying filters")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Found {len(filtered)} records after filtering")
            return filtered.to_dict("records")

        except (SearchTimeoutError, ElementNotFoundError, DataExtractionError, ScraperError):
            raise
        except Exception as e:
            self.logger.error(f"West Virginia scrape failed: {e}", exc_info=True)
            raise ScraperError("West Virginia scrape failed") from e
