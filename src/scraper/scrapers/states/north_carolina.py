# north_carolina.py
# url: https://evp.nc.gov/solicitations/

import logging
from urllib.parse import urljoin

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
    PaginationError,
    ScraperError,
)

# a scraper for North Carolina RFP data using Selenium
class NorthCarolinaScraper(SeleniumScraper):

    # modifies: self
    # effects: initializes scraper with North Carolina RFP URL and configures logger
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP.get("north carolina"))
        self.logger = logging.getLogger(__name__)


    # modifies: self.driver
    # effects: navigates to the North Carolina portal and waits for initial table rows to load
    def search(self, **kwargs):
        self.logger.info("Navigating to North Carolina RFP portal")
        try:
            self.driver.get(self.base_url)
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    "table.table-striped.table-fluid tbody tr"
                ))
            )
            return True
        except TimeoutException as te:
            self.logger.error(f"Search timeout: {te}", exc_info=False)
            raise SearchTimeoutError("North Carolina search timed out") from te
        except NoSuchElementException as ne:
            self.logger.error(f"Search element not found: {ne}", exc_info=False)
            raise ElementNotFoundError("North Carolina search element not found") from ne
        except WebDriverException as we:
            self.logger.error(f"Search WebDriver error: {we}", exc_info=True)
            raise ScraperError("North Carolina search WebDriver error") from we
        except Exception as e:
            self.logger.error(f"Search failed: {e}", exc_info=True)
            raise ScraperError("North Carolina search failed") from e


    # requires: current page loaded in self.driver
    # effects: parses the solicitations table and returns list of raw records
    def extract_data(self):
        try:
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            table = soup.find("table", class_="table table-striped table-fluid")
            if not table:
                self.logger.error("Solicitations table not found")
                raise ElementNotFoundError("North Carolina solicitations table not found")

            tbody = table.find("tbody")
            if not tbody:
                self.logger.error("<tbody> not found in table")
                raise ElementNotFoundError("North Carolina table body not found")

            records = []
            for row in tbody.find_all("tr", attrs={"data-entity": "evp_solicitation"}):
                cols = row.find_all("td")
                if len(cols) < 7:
                    continue

                a = cols[0].find("a", href=True)
                code = a.get_text(strip=True) if a else ""
                link = urljoin(self.base_url, a["href"]) if a else self.base_url

                title = cols[1].get_text(strip=True)

                time_tag = cols[3].find("time")
                end_date = time_tag.get_text(strip=True) if time_tag else cols[3].get_text(strip=True)

                records.append({
                    "title": title,
                    "code": code,
                    "end_date": end_date,
                    "link": link,
                })

            return records
        except ElementNotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise DataExtractionError("North Carolina extract_data failed") from e


    # modifies: self.driver
    # effects: clicks next page if available, returns True if click succeeded
    def next_page(self):
        try:
            next_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR,
                    "a.entity-pager-next-link:not([aria-disabled='true'])"
                ))
            )
        except TimeoutException:
            return False

        try:
            old_tbody = self.driver.find_element(By.CSS_SELECTOR, "table.table-striped.table-fluid tbody")
            next_btn.click()
            WebDriverWait(self.driver, 10).until(EC.staleness_of(old_tbody))
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.table-striped.table-fluid tbody tr"))
            )
            return True
        except WebDriverException as we:
            self.logger.error(f"next_page WebDriver error: {we}", exc_info=False)
            raise PaginationError("North Carolina pagination failed") from we
        except Exception as e:
            self.logger.error(f"next_page failed: {e}", exc_info=True)
            raise ScraperError("North Carolina next_page failed") from e


    # effects: orchestrates full scrape: search -> extract_data & paginate -> filter -> return
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for North Carolina")
        try:
            if not self.search(**kwargs):
                self.logger.warning("Search did not initialize correctly; aborting")
                raise ScraperError("North Carolina scrape aborted due to empty search")

            all_records = []
            page = 1
            while True:
                self.logger.info(f"Extracting page {page}")
                batch = self.extract_data()
                if page == 1 and not batch:
                    self.logger.error("No records found on first page; aborting")
                    raise DataExtractionError("North Carolina extract_data returned empty on first page")
                all_records.extend(batch)

                if not self.next_page():
                    self.logger.info("No more pages to process; ending pagination")
                    break
                page += 1

            df = pd.DataFrame(all_records)
            self.logger.info(f"Total raw records before filtering: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total records after filtering: {len(filtered)}")
            return filtered.to_dict("records")

        except (SearchTimeoutError, ElementNotFoundError, DataExtractionError, PaginationError, ScraperError):
            raise
        except Exception as e:
            self.logger.error(f"scrape failed: {e}", exc_info=True)
            raise ScraperError("North Carolina scrape failed") from e
