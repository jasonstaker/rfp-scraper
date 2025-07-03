# selenium_scraper.py

import os
import subprocess

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from contextlib import redirect_stdout
from webdriver_manager.chrome import ChromeDriverManager
from .base_scraper import BaseScraper
from src.config import SELENIUM_HEADLESS

class SeleniumScraper(BaseScraper):
    def __init__(self, base_url):
        super().__init__(base_url)

        # tell ChromeDriver to dump its stdout/stderr to nul
        null_log = "nul"
        service = Service(
            executable_path=ChromeDriverManager().install(),
            log_path=null_log,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        # build ChromeOptions
        self.options = webdriver.ChromeOptions()
        if SELENIUM_HEADLESS:
            self.options.add_argument("--headless=new")
            self.options.add_argument("window-size=1920,1080")
            self.options.add_argument("--log-level=3")
            self.options.add_argument("--disable-gpu")
            self.options.add_argument("--no-sandbox")
            self.options.add_argument("--disable-dev-shm-usage")

        self.options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/115.0.0.0 Safari/537.36"
        )

        # launch Chrome via that Service
        with redirect_stdout(open(os.devnull, 'w')):
            self.driver = webdriver.Chrome(service=service, options=self.options)
        self.current_response = None

    def search(self, **kwargs):
        """Perform the search (e.g., fill forms, click buttons)."""
        raise NotImplementedError("Search must be implemented in subclass.")

    def next_page(self):
        """Navigate to the next page."""
        raise NotImplementedError("Next page must be implemented in subclass.")

    def extract_data(self, page_content):
        """Extract data from the page."""
        raise NotImplementedError("Extract data must be implemented in subclass.")

    def close(self):
        """Close the browser."""
        if hasattr(self, 'driver') and self.driver:
            self.driver.quit()