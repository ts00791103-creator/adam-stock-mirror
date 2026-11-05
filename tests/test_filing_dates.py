import unittest
from unittest.mock import patch
from datetime import date
from filing_dates import inspect_filing_date as check


class FilingDateTests(unittest.TestCase):
    def test_valid_official_url_is_not_verified(self):
        with patch("filing_dates.date") as clock:
            clock.today.return_value = date(2026, 11, 5)
            self.assertIn("仍待核實", check("2308", "2025Q4", "2026-03-01",
                                        "https://mops.twse.com.tw/example", "2308"))

    def test_quarter_end_is_not_disclosure(self):
        self.assertIn("不得早於", check("2308", "2025Q4", "2025-12-31",
                                    "https://mops.twse.com.tw/", "2308"))

    def test_non_official_url_is_rejected(self):
        self.assertIn("官方來源", check("2308", "2025Q4", "2026-03-01",
                                    "https://example.com", "2308"))

    def test_wrong_stock_code_is_rejected(self):
        self.assertIn("不符", check("2330", "2025Q4", "2026-03-01",
                                "https://mops.twse.com.tw/", "2308"))

    def test_invalid_date_is_rejected(self):
        self.assertIn("格式錯誤", check("2308", "2025Q4", "not-a-date",
                                    "https://mops.twse.com.tw/", "2308"))


if __name__ == "__main__":
    unittest.main()
