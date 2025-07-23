# montana.py
# url: https://bids.sciquest.com/apps/Router/PublicEvent?CustomerOrg=StateOfMontana

import logging
import time

from bs4 import BeautifulSoup
import pandas as pd

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
    StaleElementReferenceException,
)

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

# a scraper for Montana RFP data using Selenium
class MontanaScraper(SeleniumScraper):

    # modifies: self
    # effects: initializes the scraper with Montana’s portal URL and sets up logging
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP.get("montana"))
        self.logger = logging.getLogger(__name__)


    # modifies: self.driver
    # effects: navigates to the Montana portal, waits for the main table to appear or raises
    def search(self, **kwargs):
        self.logger.info("Navigating to Montana RFP portal")
        try:
            self.driver.get(self.base_url)
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "/html/body/div[1]/div/div/div/div[2]/form/div[4]/div[2]/div/table",
                ))
            )
            return True

        except TimeoutException as te:
            self.logger.error(f"search timeout: {te}", exc_info=False)
            raise SearchTimeoutError("Montana search timed out") from te
        except NoSuchElementException as ne:
            self.logger.error(f"search missing element: {ne}", exc_info=False)
            raise ElementNotFoundError("Montana search element not found") from ne
        except WebDriverException as we:
            self.logger.error(f"search WebDriver error: {we}", exc_info=True)
            raise ScraperError("Montana search WebDriver error") from we
        except Exception as e:
            self.logger.error(f"search failed: {e}", exc_info=True)
            raise ScraperError("Montana search failed") from e


    # requires: page_source is HTML string
    # effects: parses the results table into record dicts or raises
    def extract_data(self, page_source):
        self.logger.info("Parsing Montana RFP table")
        if not page_source:
            self.logger.error("Empty page_source provided to extract_data")
            raise DataExtractionError("Montana empty page_source")

        try:
            soup = BeautifulSoup(page_source, "html.parser")
            tables = soup.find_all("table", attrs={"aria-label": "Search Results"})
            if not tables:
                tables = soup.find_all("table", attrs={"aria-title": "Search Results"})
            if not tables:
                self.logger.error("No Search Results table found")
                raise ElementNotFoundError("Montana results table not found")

            table = tables[0]
            body = table.find("tbody") or table
            rows = body.find_all("tr")
            if not rows:
                self.logger.error("No rows found in Search Results table")
                raise DataExtractionError("Montana no data rows found")

            records = []
            for row in rows:
                cols = row.find_all("td")
                if len(cols) < 2:
                    continue

                details_td = cols[1]
                link_a = details_td.select_one("a.btn.btn-link")
                if not link_a:
                    continue
                title = link_a.get_text(strip=True)
                link = link_a.get("href")

                def _find_value(suffix, strip_tz=False):
                    for dr in details_td.select("div.phx.table-row-layout"):
                        id_div = dr.find("div", id=lambda i: i and suffix in i)
                        if id_div:
                            content = dr.select_one("div.phx.data-row-content")
                            if content:
                                text = content.get_text(strip=True)
                                return text.rsplit(" ", 1)[0] if strip_tz else text
                    return ""

                end_date = _find_value("LABEL_CLOSE", strip_tz=True)
                code = _find_value("LABEL_NUMBER")
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
            raise DataExtractionError("Montana extract_data failed") from e


    # effects: orchestrates search->extract->pagination->filter; returns filtered records or raises
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Montana")
        try:
            if not self.search(**kwargs):
                raise ScraperError("Montana search did not initialize")

            all_records = []
            while True:
                page_source = self.driver.page_source
                batch = self.extract_data(page_source)
                all_records.extend(batch)

                try:
                    next_btn = self.driver.find_element(By.XPATH, "//button[@aria-label='Next page']")
                except NoSuchElementException:
                    break
                if next_btn.get_attribute("disabled"):
                    break

                try:
                    next_btn.click()
                    WebDriverWait(self.driver, 20).until(EC.staleness_of(next_btn))
                except (WebDriverException, StaleElementReferenceException) as pe:
                    self.logger.error(f"pagination click failed: {pe}", exc_info=False)
                    raise PaginationError("Montana pagination failed") from pe

                time.sleep(1)

            df = pd.DataFrame(all_records)
            self.logger.info(f"Total raw records before filtering: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total records after filtering: {len(filtered)}")
            return filtered.to_dict("records")

        except (SearchTimeoutError, ElementNotFoundError, DataExtractionError, PaginationError, ScraperError):
            raise
        except Exception as e:
            self.logger.error(f"Montana scrape failed: {e}", exc_info=True)
            raise ScraperError("Montana scrape failed") from e