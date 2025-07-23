# maryland.py
# url: https://emma.maryland.gov/page.aspx/en/rfp/request_browse_public

import logging
import pandas as pd
from bs4 import BeautifulSoup

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
    PaginationError,
    ScraperError,
)

# a scraper for Maryland RFP data using Selenium
class MarylandScraper(SeleniumScraper):

    # modifies: self
    # effects: initializes scraper with Maryland RFP URL and configures logger
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP.get("maryland"))
        self.logger = logging.getLogger(__name__)


    # modifies: self.driver
    # effects: navigates to the Maryland portal and waits for the grid to load
    def search(self, **kwargs):
        self.logger.info("Navigating to Maryland RFP portal")
        try:
            self.driver.get(self.base_url)
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.ID, "body_x_grid_grd"))
            )
            return True

        except TimeoutException as te:
            self.logger.error(f"search timeout: {te}", exc_info=False)
            raise SearchTimeoutError("Maryland search timed out") from te

        except NoSuchElementException as ne:
            self.logger.error(f"search missing element: {ne}", exc_info=False)
            raise ElementNotFoundError("Maryland search element not found") from ne

        except WebDriverException as we:
            self.logger.error(f"search WebDriver error: {we}", exc_info=True)
            raise ScraperError("Maryland search WebDriver error") from we

        except Exception as e:
            self.logger.error(f"search failed: {e}", exc_info=True)
            raise ScraperError("Maryland search failed") from e


    # requires: current page loaded
    # effects: parses the grid rows into a list of standardized records
    def extract_data(self):
        try:
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            table = soup.find("table", id="body_x_grid_grd")
            if not table:
                self.logger.error("Grid table not found")
                raise ElementNotFoundError("Maryland results table not found")

            rows = table.find_all("tr", attrs={"data-object-type": "rfp"})
            records = []
            for row in rows:
                try:
                    cells = row.find_all("td")
                    code = cells[1].get_text(strip=True)
                    a_tag = cells[2].find("a", href=True)
                    title = a_tag.get_text(strip=True) if a_tag else ""
                    link = f"https://emma.maryland.gov/{a_tag['href']}" if a_tag else self.base_url
                    end_dt = cells[4].get_text(strip=True)
                    records.append({
                        "title": title,
                        "code": code,
                        "end_date": end_dt,
                        "link": link,
                    })
                except Exception as e:
                    self.logger.warning(f"Failed to parse row: {e}")
                    continue

            return records

        except ElementNotFoundError:
            raise

        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise DataExtractionError("Maryland extract_data failed") from e


    # modifies: self.driver
    # effects: clicks next page if available, returns True if click succeeded
    def next_page(self):
        try:
            next_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "body_x_grid_PagerBtnNextPage"))
            )
            if 'disabled' in next_btn.get_attribute('class'):
                return False
            next_btn.click()
            WebDriverWait(self.driver, 10).until(EC.staleness_of(
                self.driver.find_element(By.ID, "body_x_grid_grd")
            ))
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "body_x_grid_grd"))
            )
            return True

        except (TimeoutException, NoSuchElementException):
            return False

        except WebDriverException as we:
            self.logger.error(f"next_page WebDriver error: {we}", exc_info=False)
            raise PaginationError("Maryland pagination failed") from we

        except Exception as e:
            self.logger.error(f"next_page failed: {e}", exc_info=True)
            raise ScraperError("Maryland next_page failed") from e


    # effects: orchestrates search -> extract -> paginate -> filter -> return
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Maryland")
        try:
            if not self.search(**kwargs):
                raise ScraperError("Maryland search did not initialize")

            all_records = []
            
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
            self.logger.error(f"Maryland scrape failed: {e}", exc_info=True)
            raise ScraperError("Maryland scrape failed") from e
