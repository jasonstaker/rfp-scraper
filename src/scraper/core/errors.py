# errors.py

class ScraperError(Exception):
    """Base class for all scraper errors."""

class SearchTimeoutError(ScraperError):
    """Timed out waiting for the page to load or element to appear."""

class ElementNotFoundError(ScraperError):
    """Expected element was not found in the DOM."""

class DataExtractionError(ScraperError):
    """Got malformed or missing data when parsing the page."""

class PaginationError(ScraperError):
    """Failed to paginate through all pages."""