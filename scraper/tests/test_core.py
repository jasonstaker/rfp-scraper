import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import scraper.core.base_scraper as base_scraper
import scraper.core.requests_scraper as requests_scraper
import scraper.core.selenium_scraper as selenium_scraper


class DummyScraper(base_scraper.BaseScraper):
    def __init__(self, base_url):
        super().__init__(base_url)
        self.pages = ["page1", "page2"]
        self.page_index = 0
        self.closed = False

    def search(self, **kwargs):
        if self.page_index < len(self.pages):
            content = self.pages[self.page_index]
            self.page_index += 1
            return content
        return None

    def next_page(self):
        if self.page_index < len(self.pages):
            content = self.pages[self.page_index]
            self.page_index += 1
            return content
        return None

    def extract_data(self, page_content):
        return [f"{page_content}_data"]

    def close(self):
        self.closed = True


class TestBaseScraper(unittest.TestCase):
    def test_scrape_accumulates_data_and_calls_close(self):
        dummy = DummyScraper("http://example.com")
        results = dummy.scrape(param1="value1")
        expected = ["page1_data", "page2_data"]
        self.assertEqual(results, expected)
        self.assertTrue(dummy.closed)

    def test_scrape_handles_exception_and_still_calls_close(self):
        class BrokenScraper(base_scraper.BaseScraper):
            def __init__(self, base_url):
                super().__init__(base_url)
                self.closed = False

            def search(self, **kwargs):
                raise RuntimeError("search failure")

            def next_page(self):
                return None

            def extract_data(self, page_content):
                return []

            def close(self):
                self.closed = True

        broken = BrokenScraper("http://bad.example.com")
        results = broken.scrape()
        self.assertEqual(results, [])
        self.assertTrue(broken.closed)


class TestRequestsScraper(unittest.TestCase):
    def setUp(self):
        self.scraper = requests_scraper.RequestsScraper("http://example.com")

    def test_search_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            self.scraper.search()

    def test_next_page_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            self.scraper.next_page()

    def test_extract_data_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            self.scraper.extract_data("dummy")

    def test_close_closes_session(self):
        try:
            self.scraper.close()
        except Exception as e:
            self.fail(f"close() raised an exception: {e}")


class DummyDriver:
    def __init__(self):
        self.quit_called = False

    def quit(self):
        self.quit_called = True


class TestSeleniumScraper(unittest.TestCase):
    @patch("scraper.core.selenium_scraper.ChromeDriverManager")
    @patch("scraper.core.selenium_scraper.webdriver.Chrome")
    def setUp(self, mock_chrome, mock_chromedriver_manager):
        mock_manager_instance = MagicMock()
        mock_manager_instance.install.return_value = "/path/to/chromedriver"
        mock_chromedriver_manager.return_value = mock_manager_instance

        mock_chrome.return_value = DummyDriver()

        self.scraper = selenium_scraper.SeleniumScraper("http://example.com")

    def test_search_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            self.scraper.search()

    def test_next_page_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            self.scraper.next_page()

    def test_extract_data_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            self.scraper.extract_data("dummy")

    def test_close_quits_driver(self):
        driver = self.scraper.driver
        self.assertFalse(driver.quit_called)
        self.scraper.close()
        self.assertTrue(driver.quit_called)


if __name__ == "__main__":
    unittest.main()
