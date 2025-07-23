# illinois.py
# URL: https://www.bidbuy.illinois.gov/bso/view/search/external/advancedSearchBid.xhtml?openBids=true

import logging
import pandas as pd
from bs4 import BeautifulSoup

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

from scraper.core.selenium_scraper import SeleniumScraper
from scraper.config.settings import STATE_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords
from scraper.utils.date_utils import parse_date_generic

from scraper.core.errors import (
    SearchTimeoutError,
    ElementNotFoundError,
    DataExtractionError,
    PaginationError,
    ScraperError,
)

# a scraper for Illinois RFP data using Selenium
class IllinoisScraper(SeleniumScraper):

    # modifies: self
    # effects: initializes scraper with Illinois's RFP URL and configures the logger
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP["illinois"])
        self.logger = logging.getLogger(__name__)


    # modifies: self.driver
    # effects: navigates to the Illinois RFP portal and waits for the results table to load
    def search(self, **kwargs):
        self.logger.info("Navigating to Illinois RFP portal")
        try:
            self.driver.get(self.base_url)
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.ID, "bidSearchResultsForm:bidResultId_data"))
            )
            return True
        except TimeoutException as te:
            self.logger.error(f"Search timeout: {te}", exc_info=False)
            raise SearchTimeoutError("Illinois search timed out") from te
        except NoSuchElementException as ne:
            self.logger.error(f"Search missing element: {ne}", exc_info=False)
            raise ElementNotFoundError("Illinois search element not found") from ne
        except Exception as e:
            self.logger.error(f"Search failed: {e}", exc_info=True)
            raise ScraperError("Illinois search failed") from e


    # requires: current page loaded in self.driver
    # effects: parses page_source to extract raw solicitation records and returns list of dicts
    def extract_data(self):
        try:
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            table_body = soup.find("tbody", id="bidSearchResultsForm:bidResultId_data")
            if not table_body:
                self.logger.error("results tbody not found")
                raise ElementNotFoundError("Illinois results tbody not found")
            rows = table_body.find_all("tr")

            records = []
            for row in rows:
                cols = row.find_all("td")
                if len(cols) < 8:
                    continue

                a = cols[0].find("a")
                code = a.text.strip() if a else ""
                link = a.get("href") if a else None
                full_link = f"https://www.bidbuy.illinois.gov{link}" if link else self.base_url

                title = cols[6].get_text(strip=True).removeprefix("Description")
                raw_date = cols[7].get_text(strip=True).removeprefix("Bid Opening Date")
                end_date = parse_date_generic(raw_date)

                records.append({
                    "title": title,
                    "code": code,
                    "end_date": end_date,
                    "link": full_link,
                })

            return records
        except (ElementNotFoundError, DataExtractionError):
            raise
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise DataExtractionError("Illinois extract_data failed") from e


    # modifies: self.driver
    # effects: clicks through paginated results until end; returns True when next page available, else False
    def next_page(self):
        try:
            next_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "(//a[contains(@class,'ui-paginator-next') and not(contains(@class,'ui-state-disabled'))])[1]"
                ))
            )
        except TimeoutException:
            return False
        try:
            old_table = self.driver.find_element(By.ID, "bidSearchResultsForm:bidResultId_data")
            next_btn.click()
            WebDriverWait(self.driver, 10).until(EC.staleness_of(old_table))
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "bidSearchResultsForm:bidResultId_data"))
            )
            return True
        except WebDriverException as we:
            self.logger.error(f"next_page WebDriver error: {we}", exc_info=False)
            raise PaginationError("Illinois pagination failed") from we
        except Exception as e:
            self.logger.error(f"next_page failed: {e}", exc_info=True)
            raise ScraperError("Illinois next_page failed") from e


    # effects: orchestrates full scrape: search -> loop extract_data & next_page -> filter and return records
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Illinois")
        try:
            if not self.search(**kwargs):
                self.logger.warning("Search returned no results; aborting")
                raise ScraperError("Illinois scrape aborted due to empty search")

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
            self.logger.error(f"Illinois scrape failed: {e}", exc_info=True)
            raise ScraperError("Illinois scrape failed") from e
