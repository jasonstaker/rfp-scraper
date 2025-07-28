# gwinnett.py
# url: https://www.gwinnettcounty.com/BidOpportunity

import logging
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

from scraper.core.selenium_scraper import SeleniumScraper
from src.config import COUNTY_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords
from scraper.utils.date_utils import parse_date_generic
from scraper.core.errors import (
    SearchTimeoutError,
    ElementNotFoundError,
    DataExtractionError,
    ScraperError,
)

# a scraper for Gwinnett County solicitations using Selenium
class GwinnettScraper(SeleniumScraper):


    # modifies: self
    # effects: initializes scraper with Gwinnett County bid URL and configures the logger
    def __init__(self):
        super().__init__(COUNTY_RFP_URL_MAP["georgia"]["gwinnett"])
        self.logger = logging.getLogger(__name__)


    # modifies: self.driver
    # effects: navigates to the Gwinnett bid portal and waits for the list to load
    def search(self, **kwargs):
        self.logger.info("Navigating to Gwinnett County bid portal")
        try:
            self.driver.get(self.base_url)
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "li.list-group-item-flex"))
            )
            return True
        except TimeoutException as te:
            self.logger.error(f"Search timeout: {te}", exc_info=False)
            raise SearchTimeoutError("Gwinnett search timed out") from te
        except WebDriverException as we:
            self.logger.error(f"Search WebDriver error: {we}", exc_info=True)
            raise ScraperError("Gwinnett search WebDriver error") from we
        except Exception as e:
            self.logger.error(f"Search failed: {e}", exc_info=True)
            raise ScraperError("Gwinnett search failed") from e


    # requires: current page loaded in self.driver
    # effects: parses li.list-group-item-flex items into raw solicitation records and returns list of dicts
    def extract_data(self):
        try:
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            items = soup.select("li.list-group-item-flex")
            if not items:
                self.logger.error("No bid items found")
                raise ElementNotFoundError("Gwinnett bid items not found")

            records = []
            for item in items:
                try:
                    a_tag = item.select_one("div.autofit-col.autofit-col-expand p strong a")
                    code = a_tag.text.strip() if a_tag else ""
                    href = a_tag["href"] if a_tag and a_tag.has_attr("href") else None
                    link = urljoin(self.base_url, href) if href else self.base_url

                    p_tags = item.select("div.autofit-col.autofit-col-expand p")
                    title = p_tags[1].text.strip() if len(p_tags) > 1 else ""

                    raw_date = ""
                    for p in p_tags:
                        text = p.text.strip()
                        if text.startswith("Opening Date"):
                            raw_date = text.split(":", 1)[1].strip()
                            break
                    end_date = parse_date_generic(raw_date)

                    records.append({
                        "code": code,
                        "title": title,
                        "end_date": end_date,
                        "link": link,
                    })
                except Exception as row_e:
                    self.logger.error(f"Error parsing item: {row_e}", exc_info=False)
                    continue

            return records
        except (ElementNotFoundError, DataExtractionError):
            raise
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise DataExtractionError("Gwinnett extract_data failed") from e

    # effects: orchestrates search -> extract_data -> filter; returns filtered records
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Gwinnett County")
        try:
            if not self.search(**kwargs):
                self.logger.warning("Search returned no results; aborting")
                raise ScraperError("Gwinnett scrape aborted due to search failure")

            raw = self.extract_data()
            df = pd.DataFrame(raw)
            self.logger.info(f"Total raw records before filtering: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total records after filtering: {len(filtered)}")
            return filtered.to_dict("records")

        except (SearchTimeoutError, ElementNotFoundError, DataExtractionError, ScraperError):
            raise
        except Exception as e:
            self.logger.error(f"Gwinnett scrape failed: {e}", exc_info=True)
            raise ScraperError("Gwinnett scrape failed") from e
