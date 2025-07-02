# requests_scraper.py
import requests
from .base_scraper import BaseScraper

class RequestsScraper(BaseScraper):
    def __init__(self, base_url):
        super().__init__(base_url)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": base_url
        })
        self.current_response = None

    def search(self, **kwargs):
        """Start the search with given parameters."""
        raise NotImplementedError("Search must be implemented in subclass.")

    def next_page(self):
        """Handle pagination."""
        raise NotImplementedError("Next page must be implemented in subclass.")

    def extract_data(self, page_content):
        """Extract data from the page."""
        raise NotImplementedError("Extract data must be implemented in subclass.")

    def close(self):
        """Close the session."""
        self.session.close()