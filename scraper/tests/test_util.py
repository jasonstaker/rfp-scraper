import os
import sys
import unittest

import pandas as pd

from scraper.utils.data_utils import filter_by_keywords
from scraper.utils.date_utils import parse_date
from scraper.utils.text_utils import clean_text


class TestDataUtils(unittest.TestCase):
    def setUp(self):
        with open('keywords.txt', "r", encoding="utf-8") as f:
            self.keywords = [line.strip().lower() for line in f if line.strip()]

        if len(self.keywords) < 2:
            self.skipTest("Need at least two keywords in KEYWORD_FILE to make this test meaningful.")

    def test_filter_by_keywords_with_real_file(self):
        kw1, kw2 = self.keywords[0], self.keywords[1]

        rows = {
            "Label": [
                f"{kw1}",
                f"{kw1} {kw1}",
                f"{kw1} {kw1} {kw2}",
                "completely unrelated text"
            ]
        }
        df = pd.DataFrame(rows)

        filtered = filter_by_keywords(df)
        self.assertNotIn("completely unrelated text", filtered["Label"].tolist())
        self.assertIn("Keyword Hits", filtered.columns)
        self.assertEqual(filtered["Keyword Hits"].tolist(), [3, 2, 1])
        self.assertEqual(
            filtered["Label"].tolist(),
            [f"{kw1} {kw1} {kw2}", f"{kw1} {kw1}", f"{kw1}"]
        )


class TestDateUtils(unittest.TestCase):
    def test_parse_date_valid(self):
        date_str = "12/31/2020"
        iso = parse_date(date_str)
        self.assertEqual(iso, "2020-12-31")

    def test_parse_date_invalid_format(self):
        date_str = "2020-12-31"
        result = parse_date(date_str)
        self.assertEqual(result, date_str)

    def test_parse_date_none(self):
        result = parse_date(None)
        self.assertIsNone(result)


class TestTextUtils(unittest.TestCase):
    def test_clean_text_normal(self):
        text = "  This   is   a   test  "
        cleaned = clean_text(text)
        self.assertEqual(cleaned, "This is a test")

    def test_clean_text_empty_string(self):
        text = ""
        cleaned = clean_text(text)
        self.assertEqual(cleaned, "")

    def test_clean_text_none(self):
        result = clean_text(None)
        self.assertEqual(result, "")


if __name__ == "__main__":
    unittest.main()
