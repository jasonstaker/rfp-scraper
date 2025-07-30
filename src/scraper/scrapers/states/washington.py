# washington.py
# url: https://pr-webs-vendor.des.wa.gov/BidCalendar.aspx

import logging
from urllib.parse import urljoin

import pandas as pd
from bs4 import BeautifulSoup
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

# a scraper for Washington RFP data using Selenium
class WashingtonScraper(SeleniumScraper):

    # modifies: self
    # effects: initializes scraper with Washington RFP URL and configures logger
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP.get("washington"))
        self.logger = logging.getLogger(__name__)


    # modifies: self.driver
    # effects: navigates to the Washington portal, clicks search button, and waits for results table
    def search(self, **kwargs):
        self.logger.info("Navigating to Washington RFP portal")
        try:
            self.driver.get(self.base_url)
            WebDriverWait(self.driver, 20).until(
                EC.element_to_be_clickable((By.ID, "ImageButton1"))
            ).click()
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.ID, "DataGrid1"))
            )
            return True
        except TimeoutException as te:
            self.logger.error(f"Search timeout: {te}", exc_info=False)
            raise SearchTimeoutError("Washington search timed out") from te
        except WebDriverException as we:
            self.logger.error(f"Search WebDriver error: {we}", exc_info=True)
            raise ScraperError("Washington search WebDriver error") from we
        except Exception as e:
            self.logger.error(f"Search failed: {e}", exc_info=True)
            raise ScraperError("Washington search failed") from e


    # requires: current page loaded
    # effects: parses the DataGrid1 table and returns list of standardized records
    def extract_data(self):
        try:
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            table = soup.find("table", id="DataGrid1")
            if not table:
                self.logger.error("DataGrid1 table not found")
                raise ElementNotFoundError("Washington results table not found")

            records = []
            for tr in table.find_all("tr"):
                td = tr.find("td")
                nested = td.find("table") if td else None
                if not nested:
                    continue
                rows = nested.find_all("tr")
                if len(rows) < 2:
                    continue

                # first row: date, title/link, code embed in span
                cols1 = rows[0].find_all("td")
                date = cols1[0].get_text(strip=True)
                title_cell = cols1[1]
                a = title_cell.find("a", href=True)
                title = a.get_text(strip=True) if a else ""
                link = urljoin(self.base_url, a["href"]) if a else self.base_url

                ref_span = title_cell.find("span", class_="text-small")
                code = ""
                if ref_span:
                    text = ref_span.get_text(strip=True)
                    if "Ref #" in text:
                        code = text.split("Ref #:")[-1].strip()

                records.append({
                    "title": title,
                    "code": code,
                    "end_date": date,
                    "link": link,
                })

            return records
        except ElementNotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise DataExtractionError("Washington extract_data failed") from e


    # requires: current page loaded and page number
    # modifies: self.driver
    # effects: clicks the link for next page if available, waits for table to reload
    def next_page(self, current_page: int) -> bool:
        next_page_num = current_page + 1
        xpath_tr = "/html/body/form/table/tbody/tr[2]/td/table/tbody/tr[4]/td/table/tbody/tr[27]"
        try:
            pager_row = self.driver.find_element(By.XPATH, xpath_tr)
            pager_link = pager_row.find_element(By.LINK_TEXT, str(next_page_num))
        except (NoSuchElementException, TimeoutException):
            return False

        try:
            old_table = self.driver.find_element(By.ID, "DataGrid1")
            pager_link.click()
            WebDriverWait(self.driver, 10).until(EC.staleness_of(old_table))
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "DataGrid1"))
            )
            return True
        except WebDriverException as we:
            self.logger.error(f"next_page WebDriver error: {we}", exc_info=False)
            raise PaginationError("Washington pagination failed") from we
        except Exception as e:
            self.logger.error(f"next_page failed: {e}", exc_info=True)
            raise ScraperError("Washington next_page failed") from e


    # effects: orchestrates search -> extract -> paginate -> filter -> return
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Washington")
        try:
            if not self.search(**kwargs):
                self.logger.warning("Search returned no results; aborting")
                raise ScraperError("Washington scrape aborted due to empty search")

            all_records = []
            page = 1
            while True:
                self.logger.info(f"Extracting page {page}")
                batch = self.extract_data()
                if page == 1 and not batch:
                    self.logger.error("No records found on first page; aborting")
                    raise DataExtractionError("Washington extract_data returned empty on first page")
                all_records.extend(batch)

                if not self.next_page(page):
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
            self.logger.error(f"Washington scrape failed: {e}", exc_info=True)
            raise ScraperError("Washington scrape failed") from e
