# new_hampshire.py
# url: https://das.nh.gov/purchasing/contracting-opportunities

import logging
from bs4 import BeautifulSoup
import pandas as pd

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from scraper.core.selenium_scraper import SeleniumScraper
from scraper.config.settings import STATE_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords

# a scraper for New Hampshire RFP data using Selenium
class NewHampshireScraper(SeleniumScraper):
    # modifies: self
    # effects: initializes scraper with New Hampshire's RFP URL and configures the logger
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP["new hampshire"])
        self.logger = logging.getLogger(__name__)

    # modifies: self.driver
    # effects: navigates to the New Hampshire RFP portal and waits for the bids table to load
    def search(self, **kwargs):
        self.logger.info("Navigating to New Hampshire RFP portal")
        try:
            self.driver.get(self.base_url)
            # Wait for the bids table to be present
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((
                    By.ID,
                    "ctl00_ContentPlaceHolder_GridViewBids"
                ))
            )
            self.logger.info("Bids table loaded")
            return True
        except Exception as e:
            self.logger.error(f"Search failed: {e}", exc_info=True)
            raise

    # requires: page_source in self.driver
    # effects: parses bids table, extracting description, code, end date, and link
    def extract_data(self):
        self.logger.info("Parsing HTML table for New Hampshire records")
        try:
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            table = soup.find("table", id="ctl00_ContentPlaceHolder_GridViewBids")
            if not table:
                self.logger.error("Bids table not found")
                raise RuntimeError("Table not found")

            tbody = table.find("tbody") or table
            records = []
            for row in tbody.find_all("tr")[1:]:
                cols = row.find_all("td")
                if len(cols) < 5:
                    continue

                desc_span = cols[0].find("span")
                label = desc_span.get_text(strip=True) if desc_span else cols[0].get_text(strip=True)

                bid_anchor = cols[1].find("a")
                code = bid_anchor.get_text(strip=True) if bid_anchor else ""
                link = bid_anchor["href"] if bid_anchor and bid_anchor.has_attr("href") else None

                end_date = cols[4].get_text(strip=True)

                records.append({
                    "Label": label,
                    "Code": code,
                    "End (UTC-7)": end_date,
                    "Type": "RFP",
                    "Keyword Hits": "",
                    "Link": link or self.base_url,
                })

            return records
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise

    # effects: orchestrates full scrape: search -> extract_data -> filter -> return records
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for New Hampshire")
        try:
            if not self.search(**kwargs):
                raise RuntimeError("Search returned False")

            raw = self.extract_data()
            df = pd.DataFrame(raw)
            self.logger.info(f"Total raw records: {len(df)}")

            filtered = filter_by_keywords(df)
            self.logger.info(f"Total records after filtering: {len(filtered)}")
            return filtered.to_dict("records")
        except Exception as e:
            self.logger.error(f"New Hampshire scrape failed: {e}", exc_info=True)
            raise
