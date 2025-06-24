# north_dakota.py
# URL: https://apps.nd.gov/csd/spo/services/bidder/searchSolicitation.do

import logging
from datetime import datetime
from urllib.parse import quote

import pandas as pd
from bs4 import BeautifulSoup

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from scraper.core.selenium_scraper import SeleniumScraper
from scraper.utils.data_utils import filter_by_keywords
from scraper.config.settings import STATE_RFP_URL_MAP

class NorthDakotaScraper(SeleniumScraper):
    # effects: initialize with base URL and logger
    def __init__(self):
        super().__init__(STATE_RFP_URL_MAP["north dakota"] + "&")
        self.logger = logging.getLogger(__name__)

    # effects: navigate home, click 'Search All Solicitations', then go to daily URL
    def search(self, **kwargs):
        self.logger.info("Navigating to North Dakota solicitations")
        today = datetime.now().strftime("%m/%d/%Y")
        start = quote(today, safe="")
        stop = quote("12/31/2100", safe="")
        search_url = f"{self.base_url}searchDT.startDate={start}&searchDT.stopDate={stop}"

        self.driver.get(self.base_url.rstrip("&"))
        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Search All Solicitations"))
        ).click()
        self.logger.info(f"Loading search URL: {search_url}")
        self.driver.get(search_url)
        WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div[4]/div/section/div[3]/form/div/table'))
        )
        return True

    # effects: parse table into record list
    def extract_data(self):
        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        table = soup.find("table", summary="Results from Project Search")
        if not table:
            return []

        records = []
        for tr in table.find_all("tr")[1:]:
            cols = tr.find_all("td")
            if len(cols) < 4:
                continue
            date = cols[0].get_text(strip=True)
            code = cols[1].get_text(strip=True)
            title = cols[2].get_text(strip=True)
            records.append({
                "Label": title,
                "Code": code,
                "End (UTC-7)": date,
                "Keyword Hits": "",
                "Link": self.driver.current_url,
            })
        return records

    # effects: orchestrate search, extract, filter, return
    def scrape(self, **kwargs):
        self.logger.info("Starting North Dakota scrape")
        self.search(**kwargs)
        recs = self.extract_data()
        df = pd.DataFrame(recs)
        filtered = filter_by_keywords(df)
        return filtered.to_dict("records")