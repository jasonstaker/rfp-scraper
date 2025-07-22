# kansas.py
# url: https://supplier.sok.ks.gov/psc/sokfsprdsup/SUPPLIER/ERP/c/SCP_PUBLIC_MENU_FL.SCP_PUB_BID_CMP_FL.GBL

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

# a scraper for Kansas RFP data using Selenium
class KansasScraper(SeleniumScraper):
    # modifies: self
    # effects: initializes the scraper with Kansas’s RFP URL and sets up logging
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP["kansas"])
        self.logger = logging.getLogger(__name__)

    # modifies: self.driver (through selenium operations)
    # effects: navigates to the Kansas portal, waits for the 2nd table titled "Bidding Event Information", returns page source
    def search(self, **kwargs):
        self.logger.info("navigating to Kansas RFP portal")
        try:
            self.driver.get(self.base_url)
            # wait for both tables to be present
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_all_elements_located((
                    By.XPATH,
                    '/html/body/form/div[2]/div[4]/div[2]/div/div/div/div/div[2]/'
                    'div[2]/div[2]/div/div[2]/table'
                ))
            )
            return self.driver.page_source
        except (TimeoutException, NoSuchElementException, WebDriverException) as e:
            self.logger.error(f"search failed: {e}", exc_info=True)
            raise

    # requires: page_source is a string of HTML
    # effects: parses the second "Bidding Event Information" table into record dicts
    def extract_data(self, page_source):
        self.logger.info("parsing Kansas bidding tables")
        if not page_source:
            self.logger.error("no page_source provided to extract_data")
            raise ValueError("empty page_source")

        soup = BeautifulSoup(page_source, "html.parser")
        tables = soup.find_all("table", {"title": "Bidding Event Information"})
        if len(tables) < 2:
            self.logger.error(f"expected ≥2 tables, found {len(tables)}")
            raise RuntimeError("bidding table not found")

        table = tables[1]  # second table

        # find rows with the grid-row class (or fallback)
        rows = table.select("tr.ps_grid-row")
        if not rows:
            all_tr = table.find_all("tr")
            rows = all_tr[1:] if len(all_tr) > 1 else []
        if not rows:
            self.logger.error("no data rows found in the bidding table")
            raise RuntimeError("no data rows")

        records = []
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 6:
                continue

            name     = cols[0].get_text(strip=True)
            code     = cols[2].get_text(strip=True)
            end_date = cols[5].get_text(strip=True)

            records.append({
                "title": name,
                "code": code,
                "end_date": end_date,
                "link": STATE_RFP_URL_MAP["kansas"],
            })

        return records

    # effects: orchestrates search -> extract_data -> DataFrame -> filter; returns filtered records
    def scrape(self, **kwargs):
        self.logger.info("starting Kansas scrape")
        try:
            html    = self.search(**kwargs)
            records = self.extract_data(html)

            df       = pd.DataFrame(records)
            filtered = filter_by_keywords(df)
            self.logger.info(f"found {len(filtered)} records after filtering")
            return filtered.to_dict("records")

        except Exception as e:
            self.logger.error(f"scrape failed: {e}", exc_info=True)
            raise
