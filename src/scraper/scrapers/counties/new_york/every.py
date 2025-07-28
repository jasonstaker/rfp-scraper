# every.py
# url: https://a0333-passportpublic.nyc.gov/rfx.html

import logging
import os
import glob
import time
import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from scraper.core.selenium_scraper import SeleniumScraper
from src.config import COUNTY_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords
from scraper.core.errors import (
    SearchTimeoutError,
    DataExtractionError,
    ScraperError,
)

# a scraper for all New York counties via the Excel download portal
class EveryNYScraper(SeleniumScraper):

    # modifies: self
    # effects: initializes scraper with All Counties URL and configures logger & download path
    def __init__(self):
        url = COUNTY_RFP_URL_MAP["new york"]["every"]
        super().__init__(url)
        self.logger = logging.getLogger(__name__)
        # ensure temp download directory
        self.download_dir = os.path.join(os.path.dirname(__file__), "temp")
        os.makedirs(self.download_dir, exist_ok=True)
        # configure Selenium to download to temp directory
        self._set_download_directory(self.download_dir)


    # effects: set Chrome download directory
    def _set_download_directory(self, path):
        self.driver.command_executor._commands["send_command"] = (
            "POST", "/session/$sessionId/chromium/send_command"
        )
        params = {
            'cmd': 'Page.setDownloadBehavior',
            'params': {'behavior': 'allow', 'downloadPath': path}
        }
        self.driver.execute("send_command", params)


    # modifies: self.driver
    # effects: navigates to portal and clicks "Download Data" button, waits for file
    def search(self, **kwargs):
        self.logger.info("Navigating to All Counties portal and initiating download")
        try:
            self.driver.get(self.base_url)
            # wait for button
            btn = WebDriverWait(self.driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/div[3]/div[1]/button"))
            )
            btn.click()
            timeout = time.time() + 30
            while time.time() < timeout:
                files = glob.glob(os.path.join(self.download_dir, "*.xlsx"))
                if files:
                    self.latest_file = max(files, key=os.path.getctime)
                    return self.latest_file
                time.sleep(1)
            raise TimeoutException("Excel download did not appear in time")
        except TimeoutException as te:
            self.logger.error(f"Download timeout: {te}", exc_info=False)
            raise SearchTimeoutError("All Counties download timed out") from te
        except WebDriverException as we:
            self.logger.error(f"search WebDriver error: {we}", exc_info=True)
            raise ScraperError("All Counties search WebDriver error") from we
        except Exception as e:
            self.logger.error(f"search failed: {e}", exc_info=True)
            raise ScraperError("All Counties search failed") from e


    # requires: path to downloaded file
    # effects: reads Excel, returns list of record dicts
    def extract_data(self, filepath):
        self.logger.info(f"Parsing downloaded Excel: {filepath}")
        try:
            df = pd.read_excel(filepath, header=None)

            df.columns = df.iloc[1].astype(str).str.strip()
            df = df.drop(index=[0, 1]).reset_index(drop=True)

            df = df.rename(columns={
                'RFP-ID': 'code',
                'Procurement Name': 'title',
                'Due Date': 'end_date',
            })
            df = df[['code', 'title', 'end_date']]

            df['link'] = 'https://a0333-passportpublic.nyc.gov/rfx.html'

            records = df.to_dict('records')
            return records
        except Exception as e:
            self.logger.error(f"extract_data failed: {e}", exc_info=True)
            raise DataExtractionError("All Counties extract_data failed") from e


    # effects: orchestrates download -> extract_data -> filter -> return
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for All New York Counties")
        try:
            filepath = self.search(**kwargs)
            raw = self.extract_data(filepath)
            df = pd.DataFrame(raw)
            self.logger.info(f"Total raw records before filtering: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total records after filtering: {len(filtered)}")
            return filtered.to_dict('records')
        except (SearchTimeoutError, DataExtractionError) as e:
            self.logger.error(f"All Counties scrape failed: {e}", exc_info=True)
            raise
        except Exception as e:
            self.logger.error(f"All Counties scrape unexpected error: {e}", exc_info=True)
            raise ScraperError("All Counties scrape failed") from e
