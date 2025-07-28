# san_diego.py
# url: https://sdbuynet.sandiegocounty.gov/page.aspx/en/rfp/request_browse_public

import logging
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from scraper.core.selenium_scraper import SeleniumScraper
from src.config import COUNTY_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords
from scraper.utils.date_utils import parse_date_generic
from scraper.core.errors import (
    SearchTimeoutError,
    ElementNotFoundError,
    DataExtractionError,
    PaginationError,
    ScraperError,
)

# a scraper for San Diego County open solicitations using Selenium
class SanDiegoScraper(SeleniumScraper):

    # modifies: self
    # effects: initializes with San Diego's RFP URL and configures the logger
    def __init__(self):
        base_url = COUNTY_RFP_URL_MAP["california"]["san diego"]
        super().__init__(base_url)
        self.logger = logging.getLogger(__name__)

    # modifies: self.driver
    # effects: navigates to the San Diego RFP portal, filters to Open status, and waits for the main table
    # modifies: self.driver
    # effects: navigates to the San Diego RFP portal, filters to Open status, and waits for the main table
    def search(self, **kwargs):
        try:
            self.logger.info("Navigating to San Diego RFP portal and applying Open filter")
            self.driver.get(self.base_url)
            # open status filter: click filter dropdown toggle
            filter_toggle = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "/html/body/form[1]/div[3]/div/main/div/div[2]/div[4]/div/div[1]/div/div/table/tbody/tr[1]/td[3]/div/div/div"
                ))
            )
            filter_toggle.click()
            # select 'Open' first item in dropdown
            open_item = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "/html/body/form[1]/div[3]/div/main/div/div[2]/div[4]/div/div[1]/div/div/table/tbody/tr[1]/td[3]/div/div/div/div[2]/ul/li[1]"
                ))
            )
            open_item.click()
            # wait for table to load after filtering
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.ID, "body_x_grid_grd"))
            )
            return True
        except TimeoutException as te:
            self.logger.error(f"Search timeout: {te}", exc_info=False)
            raise SearchTimeoutError("San Diego search timed out") from te
        except WebDriverException as we:
            self.logger.error(f"Search WebDriver error: {we}", exc_info=True)
            raise ScraperError("San Diego search WebDriver error") from we
        except Exception as e:
            self.logger.error(f"Search failed: {e}", exc_info=True)
            raise ScraperError("San Diego search failed") from e
        except TimeoutException as te:
            self.logger.error(f"Search timeout: {te}", exc_info=False)
            raise SearchTimeoutError("San Diego search timed out") from te
        except WebDriverException as we:
            self.logger.error(f"Search WebDriver error: {we}", exc_info=True)
            raise ScraperError("San Diego search WebDriver error") from we
        except Exception as e:
            self.logger.error(f"Search failed: {e}", exc_info=True)
            raise ScraperError("San Diego search failed") from e

    # requires: current page loaded in self.driver
    # effects: parses the table rows into raw solicitation record dicts
    def extract_data(self):
        try:
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            table = soup.find("table", id="body_x_grid_grd")
            if not table:
                self.logger.error("Results table not found")
                raise ElementNotFoundError("San Diego results table not found")
            tbody = table.find("tbody")
            rows = tbody.find_all("tr") if tbody else []

            records = []
            for idx, row in enumerate(rows):
                cols = row.find_all("td")
                if len(cols) < 9:
                    continue

                code = cols[1].get_text(strip=True)
                title = cols[2].get_text(strip=True)
                raw_end = cols[8].get_text(strip=True)
                end_date = parse_date_generic(raw_end)

                a = cols[0].find("a", href=True)
                href = a["href"] if a else None
                link = urljoin(self.base_url, href) if href else self.base_url

                records.append({
                    "code": code,
                    "title": title,
                    "end_date": end_date,
                    "link": link,
                })
            return records
        except (ElementNotFoundError, DataExtractionError):
            raise
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise DataExtractionError("San Diego extract_data failed") from e

    # modifies: self.driver
    # effects: clicks through paginated results until no next button; returns True if navigated
    def next_page(self):
        try:
            next_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "body_x_grid_PagerBtnNextPage"))
            )
        except TimeoutException:
            return False

        try:
            old_table = self.driver.find_element(By.ID, "body_x_grid_grd")
            next_btn.click()
            WebDriverWait(self.driver, 10).until(EC.staleness_of(old_table))
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "body_x_grid_grd"))
            )
            return True
        except WebDriverException as we:
            self.logger.error(f"next_page WebDriver error: {we}", exc_info=False)
            raise PaginationError("San Diego pagination failed") from we
        except Exception as e:
            self.logger.error(f"next_page failed: {e}", exc_info=True)
            raise ScraperError("San Diego next_page failed") from e

    # effects: orchestrates full scrape: search -> extract_data & next_page loop -> filter -> return
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for San Diego County")
        try:
            if not self.search(**kwargs):
                self.logger.warning("Search returned no results; aborting")
                raise ScraperError("San Diego scrape aborted due to search failure")

            all_records = []
            self.logger.info("Extracting page 1")
            all_records.extend(self.extract_data())
            page = 2

            while self.next_page():
                self.logger.info(f"Extracting page {page}")
                all_records.extend(self.extract_data())
                page += 1

            df = pd.DataFrame(all_records)
            self.logger.info(f"Total raw records before filtering: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total records after filtering: {len(filtered)}")
            return filtered.to_dict("records")

        except (SearchTimeoutError, ElementNotFoundError, DataExtractionError, PaginationError, ScraperError):
            raise
        except Exception as e:
            self.logger.error(f"San Diego scrape failed: {e}", exc_info=True)
            raise ScraperError("San Diego scrape failed") from e
