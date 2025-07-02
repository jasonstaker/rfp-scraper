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
from scraper.config.settings import STATE_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords

# a scraper for Idaho RFP data using Selenium
class IdahoScraper(SeleniumScraper):
    # modifies: self
    # effects: initializes the scraper with idaho's rfp url and sets up logging
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP["idaho"])
        self.logger = logging.getLogger(__name__)

    # modifies: self.driver (through selenium operations)
    # effects: navigates to the idaho rfp portal, waits for the table to load; returns page source if successful, otherwise None
    def search(self, **kwargs):
        self.logger.info("navigating to Idaho RFP portal")
        try:
            self.driver.get(self.base_url)

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

            while True:
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, table_xpath))
                )
                all_html.append(self.driver.page_source)

                # check the class of the "next" button
                next_button = self.driver.find_element(By.XPATH, next_button_xpath)
                class_attr = next_button.get_attribute("class")
                if "pager-next is-disabled" in class_attr:
                    self.logger.info("Last page reached, stopping pagination")
                    break

                self.logger.info("Clicking next page")
                next_button.click()

            return all_html

        except TimeoutException as te:
            self.logger.error(f"search timeout: {te}", exc_info=False)
            raise
        except NoSuchElementException as ne:
            self.logger.error(f"search missing element: {ne}", exc_info=False)
            raise
        except WebDriverException as we:
            self.logger.error(f"search WebDriver error: {we}", exc_info=True)
            raise
        except Exception as e:
            self.logger.error(f"search() failed: {e}", exc_info=True)
            raise


    # requires: page_source is a string containing html page source
    # effects: parses the solicitations table from page_source and returns a list of raw records
    def extract_data(self, page_source):
        if not page_source:
            self.logger.error("no page_source provided to extract_data")
            raise

        try:
            soup = BeautifulSoup(page_source, "html.parser")
            table = soup.find("table", class_="datagrid extra-small-rowheight")
            if not table:
                self.logger.error("results table not found")
                raise

            tbody = table.find("tbody")
            if not tbody:
                self.logger.error("no <tbody> found in table")
                raise

            records = []
            for row in tbody.find_all("tr", role="row"):
                cols = row.find_all("td")
                if len(cols) < 7:
                    continue

                card_spans = cols[0].find_all("span", class_="lm-card-field")
                if len(card_spans) < 2:
                    continue
                label = card_spans[0].get_text(strip=True)
                code = card_spans[1].get_text(strip=True)

                raw_date = cols[5].get_text(strip=True)

                link = STATE_RFP_URL_MAP["idaho"]

                records.append(
                    {
                        "Label": label,
                        "Code": code,
                        "End (UTC-7)": raw_date,
                        "Keyword Hits": "",
                        "Link": link,
                    }
                )

            return records

        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise

    # modifies: self.driver (through selenium operations)
    # effects: orchestrates the scraping process: search -> extract_data; returns filtered records, raises exception on failure
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Idaho")
        try:
            html_list = self.search(**kwargs)
            if not html_list:
                self.logger.warning("Search returned no HTML; skipping extraction")
                raise

            all_records = []
            for html in html_list:
                records = self.extract_data(html)
                all_records.extend(records)

            df = pd.DataFrame(all_records)
            self.logger.info("Applying filters")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Found {len(filtered)} records after filtering")
            return filtered.to_dict("records")

        except Exception as e:
            self.logger.error(f"Idaho scrape failed: {e}", exc_info=True)
            raise

