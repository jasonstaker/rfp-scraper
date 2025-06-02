# alabama.py

import logging
import time

from bs4 import BeautifulSoup
import pandas as pd

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from scraper.core.selenium_scraper import SeleniumScraper
from scraper.config.settings import STATE_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords


class AlabamaScraper(SeleniumScraper):
    def __init__(self):
        # configure headless Chrome with minimal logs
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_experimental_option(
            "excludeSwitches", ["enable-logging", "enable-automation"]
        )

        super().__init__(STATE_RFP_URL_MAP["alabama"], options=chrome_options)
        self.logger = logging.getLogger(__name__)

    def search(self, **kwargs):
        # navigate to Alabama STAARS Public Access and open the 'Open Solicitations' table
        self.logger.info("navigating to Alabama STAARS Public Access")
        try:
            self.driver.get(self.base_url)

            # click 'Public Access'
            pub_locator = (By.XPATH, '//*[@id="homelayout"]/td[1]/div/div[5]/div[3]/input')
            WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(pub_locator)).click()

            # wait for new tab, then switch
            WebDriverWait(self.driver, 10).until(lambda d: len(d.window_handles) > 1)
            new_handle = [h for h in self.driver.window_handles if h != self.driver.current_window_handle][0]
            self.driver.switch_to.window(new_handle)

            # switch into 'Display' frame
            WebDriverWait(self.driver, 15).until(
                EC.frame_to_be_available_and_switch_to_it((By.NAME, "Display"))
            )

            # click 'Open Solicitations'
            open_locator = (By.ID, "AMSBrowseOpenSolicit")
            WebDriverWait(self.driver, 15).until(EC.element_to_be_clickable(open_locator))
            self.driver.execute_script("arguments[0].click();", self.driver.find_element(*open_locator))

            # wait for the solicitations table to load
            table_locator = (By.XPATH, '//*[@id="PageContent"]/table[4]')
            WebDriverWait(self.driver, 20).until(EC.presence_of_element_located(table_locator))
            time.sleep(1)
            self.logger.info("solicitations table loaded")
            return self.driver.page_source

        except TimeoutException as te:
            self.logger.error(f"search timeout: {te}", exc_info=False)
            return None
        except NoSuchElementException as ne:
            self.logger.error(f"search missing element: {ne}", exc_info=False)
            return None
        except Exception as e:
            self.logger.error(f"search failed: {e}", exc_info=True)
            return None

    def extract_data(self, page_source):
        # parse the HTML table into a list of raw records
        self.logger.info("parsing solicitations table")
        if not page_source:
            self.logger.error("no page_source provided to extract_data")
            return []

        try:
            soup = BeautifulSoup(page_source, "html.parser")
            table = soup.find("table", attrs={"name": "tblT1SO_SRCH_QRY"})
            if not table:
                self.logger.error("table not found in extract_data")
                return []

            records = []
            rows = table.find_all("tr", class_=lambda c: c and "advgrid" in c.lower())
            for row in rows:
                cols = row.find_all("td", valign="top")
                if len(cols) < 4:
                    continue

                # extract 'Label' and 'Code'
                label_block = cols[0]
                text_items = [
                    td.get_text(strip=True)
                    for td in label_block.find_all("td", style=lambda s: s and "border-bottom" in s)
                ]
                label = text_items[0] if len(text_items) > 0 else ""
                code = text_items[1] if len(text_items) > 1 else ""

                # extract 'End date'
                end_text = ""
                end_td = cols[2].find("td", style=lambda s: s and "color:red" in s)
                if end_td:
                    end_text = end_td.get_text(strip=True)

                # placeholder link (state-level)
                link = STATE_RFP_URL_MAP["alabama"]

                records.append(
                    {
                        "Label": label,
                        "Code": code,
                        "End (UTC-7)": end_text,
                        "Keyword Hits": "",
                        "Link": link,
                    }
                )

            self.logger.info(f"parsed {len(records)} raw records")
            return records

        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            return []

    def scrape(self, **kwargs):
        # high-level orchestration: search → paginate → extract → filter → return
        self.logger.info("starting Alabama scrape")
        all_records = []
        try:
            page = self.search(**kwargs)
            if not page:
                self.logger.warning("search() returned no page; skipping extraction")
                return []

            # first-page extraction
            all_records.extend(self.extract_data(page))

            # pagination loop
            while True:
                try:
                    next_btn = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, '//*[@id="T1SO_SRCH_QRYnextpage"]'))
                    )
                    self.driver.execute_script("arguments[0].click();", next_btn)

                    # wait for the table to reload
                    WebDriverWait(self.driver, 20).until(
                        EC.presence_of_element_located((By.XPATH, '//*[@id="PageContent"]/table[4]'))
                    )
                    time.sleep(1)

                    # extract next-page data
                    all_records.extend(self.extract_data(self.driver.page_source))
                except TimeoutException:
                    self.logger.info("pagination timeout or no next button; ending pagination")
                    break
                except Exception:
                    self.logger.info("no more pages found or pagination ended")
                    break

            # filtering
            df = pd.DataFrame(all_records)
            self.logger.info(f"total records before filter: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"total records after filter: {len(filtered)}")
            return filtered.to_dict("records")

        except Exception as e:
            self.logger.error(f"scrape failed: {e}", exc_info=True)
            return []
        finally:
            self.close()
