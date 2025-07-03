# virginia.py
# url: https://mvendor.cgieva.com/Vendor/public/AllOpportunities.jsp

import logging
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd
from bs4 import BeautifulSoup

from scraper.core.selenium_scraper import SeleniumScraper
from scraper.config.settings import STATE_RFP_URL_MAP
from scraper.utils.data_utils import filter_by_keywords
from scraper.utils.date_utils import parse_date_generic

# a scraper for Virginia RFP data using Selenium
class VirginiaScraper(SeleniumScraper):
    # requires: STATE_RFP_URL_MAP['virginia'] = search page URL
    # modifies: self
    # effects: initializes scraper with Virginia all opportunities URL and detail link base
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP['virginia'])
        self.details_url = (
            'https://mvendor.cgieva.com/Vendor/public/IVDetails.jsp?'
            'PageTitle=SO%20Details'
        )
        self.logger = logging.getLogger(__name__)

    # modifies: self.driver
    # effects: load the 'Open' opportunities, then scroll to load all cards
    def search(self, **kwargs):
        try:
            self.logger.info("Navigating to Virginia portal and filtering Open opportunities")
            self.driver.get(self.base_url)
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, '/html/body/div[3]/div/div[2]/div/ul/li[1]/div/ul/li[1]'))
            )
            li = self.driver.find_element(By.XPATH, '/html/body/div[3]/div/div[2]/div/ul/li[1]/div/ul/li[1]')
            li.click()
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'li.fetch-by-cursor'))
            )
            self.driver.execute_script("window.scrollBy(0, window.innerHeight);")
            time.sleep(0.5)
            self.driver.execute_script("window.scrollBy(0, -100);")
            time.sleep(0.5)
            count = 1;
            while True:
                try:
                    count += 1
                    sentinel = self.driver.find_element(By.CSS_SELECTOR, 'li.fetch-by-cursor')
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", sentinel)
                    time.sleep(0.2)
                    if(count >= 120): 
                        break
                except NoSuchElementException:
                    self.logger.info("All items loaded; sentinel gone.")
                    break
            return True
        except TimeoutException as e:
            self.logger.error(f"search() timeout: {e}", exc_info=True)
            raise

    # requires: page_source contains all opportunity cards loaded
    # effects: parse the first <li> container of cards into a list of records
    def extract_data(self):
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        ul = soup.select_one('div:nth-of-type(3) > div > div:nth-of-type(3) > div > ul')
        if not ul:
            self.logger.error("Opportunities list not found")
            return []
        
        first_li = next(
            (li for li in ul.find_all('li', recursive=False)
             if 'fetch-by-cursor' not in (li.get('class') or [])),
            None
        )
        if not first_li:
            self.logger.error("No card container <li> found")
            return []

        records = []
        for card in first_li.find_all('div', class_='card text-center'):
            try:
                title = card.select_one('h5.card-title').get_text(strip=True)
                code_text = card.select_one('h6.card-title').get_text(strip=True)
                parts = code_text.split()
                if len(parts) < 2:
                    continue
                bid_code = parts[0]
                lot_round = parts[1]
                bid_no, round_no = (lot_round.split('-') if '-' in lot_round else (lot_round, '1'))
                
                link = (
                    f"{self.details_url}&rfp_id_lot={bid_no}"
                    f"&rfp_id_round={round_no}"
                )
                closing_p = card.find('p', string=lambda t: t and 'Closing On:' in t)
                end_str = ''
                if closing_p:
                    raw = closing_p.get_text(strip=True).replace('Closing On:', '').strip()
                    end_str = parse_date_generic(raw)
                records.append({
                    'title':       title,
                    'code':        code_text,
                    'end_date': end_str,
                    'link':        link,
                })
            except Exception as e:
                self.logger.error(f"Error parsing card: {e}", exc_info=True)
                continue
        return records

    # requires: search() and extract_data() methods
    # effects: orchestrates full scrape, returning filtered records
    def scrape(self, **kwargs):
        self.logger.info("Starting scrape for Virginia")
        try:
            self.search(**kwargs)
            recs = self.extract_data()
            df = pd.DataFrame(recs)
            self.logger.info(f"Total raw records: {len(df)}")
            filtered = filter_by_keywords(df)
            self.logger.info(f"Total after filtering: {len(filtered)}")
            return filtered.to_dict('records')
        except Exception as e:
            self.logger.error(f"Virginia scrape failed: {e}", exc_info=True)
            raise
