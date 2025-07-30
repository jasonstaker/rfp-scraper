# fresno.py
# url: https://www.fresnocountyca.gov/Departments/General-Services-Department/Purchasing-Services/Bid-Opportunities

import logging
from bs4 import BeautifulSoup
import pandas as pd

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

from scraper.core.selenium_scraper import SeleniumScraper
from scraper.utils.data_utils import filter_by_keywords
from src.config import COUNTY_RFP_URL_MAP
from scraper.core.errors import (
    SearchTimeoutError,
    ElementNotFoundError,
    ScraperError,
)

# a scraper for Fresno County RFP data using Selenium
class FresnoScraper(SeleniumScraper):

    # modifies: self
    # effects: initializes scraper with Fresno County URL and logger
    def __init__(self):
        super().__init__(COUNTY_RFP_URL_MAP["california"]["fresno"])
        self.logger = logging.getLogger(__name__)


    # effects: navigates to Fresno portal, parses DataFrame, returns cleaned records
    def search(self, **kwargs):
        self.logger.info("Navigating to Fresno RFP portal")
        try:
            self.driver.get(self.base_url)
            WebDriverWait(self.driver, 20).until(
                EC.frame_to_be_available_and_switch_to_it(
                    (By.XPATH, "/html/body/form/div[4]/div[2]/div/div/div[1]/div/div[3]/div/div/div/div/p[3]/iframe")
                )
            )
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "/html/body/div/table"))
            )
            table_elem = self.driver.find_element(By.XPATH, "/html/body/div/table")
            table_html = table_elem.get_attribute("outerHTML")

            df = pd.read_html(table_html)[0]

            df[['code', 'title_raw']] = df['Title'].str.split(' - ', n=1, expand=True)

            df['title'] = df['title_raw'].str.split('\t', n=1).str[0]

            records = []
            for _, row in df.iterrows():
                records.append({
                    'code': row['code'],
                    'title': row['title'],
                    'end_date': row['End Date'],
                    'link': self.base_url,
                })

            return records

        except TimeoutException as te:
            self.logger.error(f"search timeout: {te}", exc_info=False)
            raise SearchTimeoutError("Fresno search timed out") from te
        except NoSuchElementException as ne:
            self.logger.error(f"search missing element: {ne}", exc_info=False)
            raise ElementNotFoundError("Fresno search element not found") from ne
        except WebDriverException as we:
            self.logger.error(f"search WebDriver error: {we}", exc_info=True)
            raise ScraperError("Fresno search WebDriver error") from we
        except Exception as e:
            self.logger.error(f"search failed: {e}", exc_info=True)
            raise ScraperError("Fresno search failed") from e


    # requires: not used
    # effects: placeholder to satisfy interface
    def extract_data(self, page_source=None):
        raise NotImplementedError


    # effects: orchestrates search -> filter; returns records or raises ScraperError
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Fresno County")
        try:
            records = self.search(**kwargs)
            df = pd.DataFrame(records)
            filtered = filter_by_keywords(df)
            return filtered.to_dict('records')
        except (SearchTimeoutError, ElementNotFoundError, ScraperError) as err:
            raise
        except Exception as e:
            self.logger.error(f"Fresno scrape failed: {e}", exc_info=True)
            raise ScraperError("Fresno scrape failed") from e