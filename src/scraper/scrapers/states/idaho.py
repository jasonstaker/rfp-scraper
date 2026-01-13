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

        table_css = "table.datagrid.extra-small-rowheight"
        row_css = "table.datagrid.extra-small-rowheight tbody tr.datagrid-row"
        next_btn_css = "#XiOpenForBid_pager-btn-next"

        all_html = []

        try:
            self.driver.get(self.base_url)

            while True:
                WebDriverWait(self.driver, 45).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, table_css))
                )
                WebDriverWait(self.driver, 45).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, row_css))
                )

                all_html.append(self.driver.page_source)

                next_btn = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, next_btn_css))
                )

                next_li = next_btn.find_element(By.XPATH, "./ancestor::li[1]")
                next_li_class = next_li.get_attribute("class") or ""
                if "is-disabled" in next_li_class:
                    self.logger.info("Last page reached (pager-next is-disabled), stopping pagination")
                    break

                def first_row_signature(drv):
                    r = drv.find_element(By.CSS_SELECTOR, row_css)
                    spans = r.find_elements(By.CSS_SELECTOR, "td.lm-datagrid-card-container span.lm-card-field")
                    title = spans[0].text.strip() if len(spans) > 0 else ""
                    event = spans[1].text.strip() if len(spans) > 1 else ""
                    close_date = r.find_elements(By.CSS_SELECTOR, "td:nth-child(6) .datagrid-cell-wrapper")
                    close = close_date[0].text.strip() if close_date else ""
                    return f"{title}||{event}||{close}"

                before_sig = first_row_signature(self.driver)

                self.logger.info("Clicking next page")
                self.driver.execute_script("arguments[0].click();", next_btn)

                try:
                    WebDriverWait(self.driver, 45).until(lambda d: first_row_signature(d) != before_sig)
                except TimeoutException:
                    self.logger.info("Next click did not advance (signature unchanged). Stopping pagination.")
                    break


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
