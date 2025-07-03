# michigan.py
# url: https://prd.co.cgiadvantage.com/PRDVSS1X1/Advantage4

import logging
import time

from bs4 import BeautifulSoup
import pandas as pd

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

from scraper.core.selenium_scraper import SeleniumScraper
from scraper.utils.data_utils import filter_by_keywords
from scraper.config.settings import STATE_RFP_URL_MAP

# a scraper for Michigan RFP data using Selenium
class MichiganScraper(SeleniumScraper):
    # modifies: self
    # effects: initializes the scraper with Michigan's RFP url and sets up logging
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP["michigan"])
        self.logger = logging.getLogger(__name__)

    # effects: navigates to the Michigan RFP portal, clicks 'View Published Solicitations', and waits for the table to load
    def search(self, **kwargs):
        self.logger.info("Navigating to Michigan RFP portal")
        try:
            self.driver.get(self.base_url)
            
            next_carousel = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.XPATH,
                    "/html/body/div[1]/as-main-app/adv-view-mgr/div[3]/main/"
                    "div[1]/div[2]/div[2]/section[2]/adv-custom-carousel-page/"
                    "div[4]/carousel-component4/div[1]/div[1]/div[3]/a"
                ))
            )
            next_carousel.click()
            self.logger.info("Clicked initial carousel Next arrow")
            
            button_locator = (
                By.XPATH,
                "//div[@data-qa='vss.page.VAXXX03153.carouselView.carousel.solicitations']",
            )
            WebDriverWait(self.driver, 20).until(
                EC.element_to_be_clickable(button_locator)
            ).click()
            self.logger.info("Clicked 'View Published Solicitations'")

            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located(
                    (By.ID, "vsspageVVSSX10019gridView1group1cardGridgrid1")
                )
            )
            self.logger.info("Solicitations table loaded")
            return True

        except (TimeoutException, NoSuchElementException, WebDriverException) as e:
            self.logger.error(f"Search failed: {e}", exc_info=True)
            raise

    # requires: page_source is a string containing html page source
    # effects: parses the solicitations table and returns a list of standardized records
    def extract_data(self, page_source):
        if not page_source:
            self.logger.error("No page_source provided to extract_data")
            raise RuntimeError("Empty page_source")

        try:
            soup = BeautifulSoup(page_source, "html.parser")
            table = soup.find("table", id="vsspageVVSSX10019gridView1group1cardGridgrid1")
            if not table:
                self.logger.error("Results table not found")
                raise RuntimeError("Table missing")

            tbody = table.find("tbody")
            if not tbody:
                self.logger.error("No <tbody> found in table")
                raise RuntimeError("Missing tbody")

            records = []
            for row in tbody.find_all("tr"):
                cols = row.find_all("td")
                if len(cols) < 5:
                    continue

                # Column 2: title
                title = cols[1].get_text(strip=True)
                # Column 4: Code and link
                anchor = cols[3].find("a")
                if not anchor:
                    continue
                code = anchor.get_text(strip=True)
                link = STATE_RFP_URL_MAP["michigan"]

                # Column 5: End date
                date_span = cols[4].find("span")
                raw_date = date_span.get_text(strip=True) if date_span else ""

                records.append({
                    "title": title,
                    "code": code,
                    "end_date": raw_date,
                    "link": link,
                })

            return records

        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise

    # effects: orchestrates search -> extract_data -> pagination -> filter -> return
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Michigan")
        all_records = []
        try:
            if not self.search(**kwargs):
                raise RuntimeError("Search() failed")

            page_num = 1
            while True:
                self.logger.info(f"Processing page {page_num}")
                page_source = self.driver.page_source
                batch = self.extract_data(page_source)
                if page_num == 1 and not batch:
                    raise RuntimeError("No records on first page")

                all_records.extend(batch)

                # find next pagination button
                next_buttons = self.driver.find_elements(By.CLASS_NAME, "css-1yn6b58")
                next_btn = next_buttons[0] if next_buttons and next_buttons[0].is_enabled() else None
                if not next_btn:
                    break

                next_btn.click()
                page_num += 1
                time.sleep(1)  # allow table to refresh

            df = pd.DataFrame(all_records)
            self.logger.info(f"Total raw records before filtering: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total records after filtering: {len(filtered)}")
            return filtered.to_dict("records")

        except Exception as e:
            self.logger.error(f"Michigan scrape failed: {e}", exc_info=True)
            raise
