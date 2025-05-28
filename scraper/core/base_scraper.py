# base_scraper.py
from abc import ABC, abstractmethod
import logging

class BaseScraper(ABC):
    def __init__(self, base_url):
        self.base_url = base_url
        self.logger = logging.getLogger(__name__)

    @abstractmethod
    def search(self, **kwargs):
        """Perform the initial search and return the first page of content."""
        pass

    @abstractmethod
    def next_page(self):
        """Get the next page of results or None if no more pages exist."""
        pass

    @abstractmethod
    def extract_data(self, page_content):
        """Extract data (e.g., RFPs) from the current page."""
        pass

    @abstractmethod
    def close(self):
        """Clean up resources (e.g., close browser or session)."""
        pass

    def scrape(self, **kwargs):
        """Run the full scraping process: search, paginate, extract."""
        try:
            response = self.search(**kwargs)
            results = []
            while response:
                data = self.extract_data(response)
                results.extend(data)
                response = self.next_page()
            return results
        except Exception as e:
            self.logger.error(f"Scraping failed: {e}")
            return []
        finally:
            self.close()