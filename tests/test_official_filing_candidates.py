import unittest
from unittest.mock import patch
import pandas as pd
from official_filing_candidates import fetch_official_filing_candidates, review_candidate_coverage


class OfficialCandidateTests(unittest.TestCase):
    def test_extracts_only_matching_stock_report(self):
        frame = pd.DataFrame([
            ["115/08/14 16:30", "2308", "台達電", "115年第2季財務報告書"],
            ["115/08/14 16:30", "2330", "台積電", "115年第2季財務報告書"],
            ["115/08/14 16:30", "2308", "台達電", "法說會"],
        ], columns=["公告日期時間", "證券代號", "證券名稱", "主旨"])
        class Response:
            text = "<table></table>"
            def raise_for_status(self):
                pass
        with patch("official_filing_candidates.requests.get", return_value=Response()), patch(
            "official_filing_candidates.pd.read_html", return_value=[frame]
        ):
            rows, error = fetch_official_filing_candidates("2308")
        self.assertIsNone(error)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["季度"], "2026Q2")

    def test_empty_javascript_page_fails_closed(self):
        with patch("official_filing_candidates.requests.get") as getter:
            getter.return_value.text = "<html>No server-side table</html>"
            getter.return_value.raise_for_status.return_value = None
            rows, error = fetch_official_filing_candidates("2308")
        self.assertEqual(rows, [])
        self.assertIsNotNone(error)

    def test_duplicate_reports_are_not_verified(self):
        rows = [{"季度": "2025Q4"}, {"季度": "2025Q4"}]
        review = review_candidate_coverage(rows, ["2025Q4", "2026Q1"])
        self.assertIn("多筆", review[0]["狀態"])
        self.assertEqual(review[1]["候選公告筆數"], 0)


if __name__ == "__main__":
    unittest.main()
