# idaho.py
# url: https://sms-idaho-prd.tam.inforgov.com/fsm/SupplyManagementSupplier/list/SourcingEvent.XiOpenForBid?navigation=SourcingEvent%5BByCompany%5D%28_niu_,_niu_%29.OpenEventsNav&csk.SupplierGroup=LUMA

import logging

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
    ScraperError,
)

# a scraper for Idaho RFP data using Selenium
class IdahoScraper(SeleniumScraper):

    # modifies: self
    # effects: initializes the scraper with Idaho's RFP url and sets up logging
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP["idaho"])
        self.logger = logging.getLogger(__name__)


    # modifies: self.driver (through selenium operations)
    # effects: navigates to the Idaho RFP portal, pages through all results, and returns list of page_source strings
    def search(self, **kwargs):
        self.logger.info("navigating to Idaho RFP portal")
        table_xpath = (
            "/html/body/lm-app/soho-module-nav-container/div/div/"
            "lm-list/div[1]/div/div[1]/div/div[2]/lm-list-content/"
            "lm-list-grid/div/div[1]/div[1]/div/div[1]/table"
        )
        next_button_xpath = (
            "/html/body/lm-app/soho-module-nav-container/div/div[1]/lm-list/"
            "div[1]/div/div[1]/div/div[2]/lm-list-content/lm-list-grid/div/"
            "div[1]/div[2]/ul/li[3]"
        )
        all_html = []

        try:
            self.driver.get(self.base_url)
            while True:
                # wait for table and rows
                WebDriverWait(self.driver, 30).until(
                    EC.presence_of_element_located((By.XPATH, table_xpath))
                )
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, table_xpath + "/tbody/tr[@role='row']"))
                )
                all_html.append(self.driver.page_source)

                # find next button and check if disabled
                next_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, next_button_xpath))
                )
                class_attr = next_button.get_attribute("class")
                if "pager-next is-disabled" in class_attr:
                    self.logger.info("Last page reached, stopping pagination")
                    break

                self.logger.info("Clicking next page")
                next_button.click()
            return all_html

        except TimeoutException as te:
            self.logger.error(f"search timeout: {te}", exc_info=False)
            raise SearchTimeoutError("Idaho search timed out") from te

        except NoSuchElementException as ne:
            self.logger.error(f"search missing element: {ne}", exc_info=False)
            raise ElementNotFoundError("Idaho search element not found") from ne

        except WebDriverException as we:
            self.logger.error(f"search WebDriver error: {we}", exc_info=True)
            raise ScraperError("Idaho search WebDriver error") from we

        except Exception as e:
            self.logger.error(f"search() failed: {e}", exc_info=True)
            raise ScraperError("Idaho search failed") from e


    # requires: page_source is a string containing html page source
    # effects: parses the solicitations table from page_source and returns a list of raw record dicts
    def extract_data(self, page_source):
        if not page_source:
            self.logger.error("no page_source provided to extract_data")
            raise DataExtractionError("Empty page_source for Idaho extract_data")

        try:
            soup = BeautifulSoup(page_source, "html.parser")
            table = soup.find("table", class_="datagrid extra-small-rowheight")
            if not table:
                self.logger.error("results table not found")
                raise ElementNotFoundError("Idaho results table not found")

            tbody = table.find("tbody")
            if not tbody:
                self.logger.error("no <tbody> found in table")
                raise ElementNotFoundError("Idaho results <tbody> not found")

            records = []
            for row in tbody.find_all("tr", role="row"):
                cols = row.find_all("td")
                if len(cols) < 7:
                    continue

                card_spans = cols[0].find_all("span", class_="lm-card-field")
                if len(card_spans) < 2:
                    continue
                title = card_spans[0].get_text(strip=True)
                code = card_spans[1].get_text(strip=True)
                raw_date = cols[5].get_text(strip=True)
                link = STATE_RFP_URL_MAP["idaho"]

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
            raise DataExtractionError("Idaho extract_data failed") from e


    # modifies: self.driver (through selenium operations)
    # effects: orchestrates the scraping process: search -> extract_data -> filter; returns filtered records
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Idaho")
        try:
            html_list = self.search(**kwargs)
            if not html_list:
                self.logger.warning("Search returned no HTML; aborting Idaho scrape")
                raise ScraperError("Idaho scrape aborted due to empty search")

            all_records = []
            for html in html_list:
                all_records.extend(self.extract_data(html))

            df = pd.DataFrame(all_records)
            self.logger.info("Applying filters")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Found {len(filtered)} records after filtering")
            return filtered.to_dict("records")

        except (SearchTimeoutError, ElementNotFoundError, DataExtractionError, ScraperError):
            raise

        except Exception as e:
            self.logger.error(f"Idaho scrape failed: {e}", exc_info=True)
            raise ScraperError("Idaho scrape failed") from e
