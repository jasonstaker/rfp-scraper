# colorado.py
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


class ColoradoScraper(SeleniumScraper):
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP["colorado"])
        self.logger = logging.getLogger(__name__)

    def search(self, **kwargs):
        # navigate to the Colorado RFP portal and click 'View Published Solicitations'
        self.logger.info("navigating to Colorado RFP portal")
        try:
            self.driver.get(self.base_url)

            button_locator = (
                By.XPATH,
                "//div[@data-qa='vss.page.VAXXX03153.carouselView.carousel.solicitations']",
            )
            WebDriverWait(self.driver, 20).until(
                EC.element_to_be_clickable(button_locator)
            ).click()
            self.logger.info("clicked 'View Published Solicitations'")

            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located(
                    (By.ID, "vsspageVVSSX10019gridView1group1cardGridgrid1")
                )
            )
            time.sleep(1)
            self.logger.info("solicitations table loaded")
            return True

        except TimeoutException as te:
            self.logger.error(f"search timeout: {te}", exc_info=False)
            return False
        except NoSuchElementException as ne:
            self.logger.error(f"search missing element: {ne}", exc_info=False)
            return False
        except WebDriverException as we:
            self.logger.error(f"search WebDriver error: {we}", exc_info=True)
            return False
        except Exception as e:
            self.logger.error(f"search() failed: {e}", exc_info=True)
            return False

    def extract_data(self, page_source):
        # parse the solicitations table into raw records
        if not page_source:
            self.logger.error("no page_source provided to extract_data")
            return []

        try:
            soup = BeautifulSoup(page_source, "html.parser")
            table = soup.find("table", id="vsspageVVSSX10019gridView1group1cardGridgrid1")
            if not table:
                self.logger.error("results table not found")
                return []

            tbody = table.find("tbody")
            if not tbody:
                self.logger.error("no <tbody> found in table")
                return []

            records = []
            for row in tbody.find_all("tr"):
                cols = row.find_all("td")
                if len(cols) < 5:
                    continue

                label = cols[1].get_text(strip=True)
                anchor = cols[3].find("a")
                if not anchor:
                    continue

                code = anchor.get_text(strip=True)
                link = STATE_RFP_URL_MAP["colorado"]

                date_span = cols[4].find("span")
                raw_date = date_span.get_text(strip=True) if date_span else ""

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
            return []

    def scrape(self, **kwargs):
        # high-level orchestration: search → extract/paginate → filter → return
        self.logger.info("Starting scrape for Colorado")
        all_records = []
        try:
            success = self.search(**kwargs)
            if not success:
                self.logger.warning("Search returned False; skipping scrape")
                return []

            page_num = 1
            while True:
                self.logger.info(f"Processing page {page_num}")
                page_source = None
                try:
                    page_source = self.driver.page_source
                except WebDriverException as we:
                    self.logger.error(f"failed to get page_source: {we}", exc_info=False)
                    break

                batch = self.extract_data(page_source)
                all_records.extend(batch)

                next_buttons = []
                try:
                    next_buttons = self.driver.find_elements(By.CLASS_NAME, "css-1yn6b58")
                except WebDriverException as we:
                    self.logger.error(f"failed to find next buttons: {we}", exc_info=False)
                    break

                next_btn = None
                for btn in next_buttons:
                    try:
                        if btn.is_displayed() and btn.is_enabled():
                            next_btn = btn
                            break
                    except WebDriverException:
                        continue

                if not next_btn:
                    self.logger.info("No clickable Next button. Terminating pagination")
                    break

                try:
                    first_row = self.driver.find_element(By.CSS_SELECTOR, "tr[id^='tableDataRow']")
                    old_row_id = first_row.get_attribute("id")
                except NoSuchElementException:
                    old_row_id = None

                try:
                    next_btn.click()
                except WebDriverException as we:
                    self.logger.error(f"failed to click next button: {we}", exc_info=False)
                    break

                page_num += 1

            self.logger.info("Completed parsing")
            df = pd.DataFrame(all_records)
            self.logger.info("Applying filters")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Found {len(filtered)} records after filtering")
            return filtered.to_dict("records")

        except Exception as e:
            self.logger.error(f"Scrape failed: {e}", exc_info=True)
            return []
        finally:
            self.logger.info("closing browser")
            self.close()