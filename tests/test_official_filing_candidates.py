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

    def test_mops_query_form_not_misclassified_as_filing(self):
        from official_filing_candidates import probe_mops_financial_announcement
        class Response:
            status_code = 200
            url = "https://mopsov.twse.com.tw/mops/web/ajax_t163sb01"
            headers = {"Content-Type": "text/html"}
            text = "<html><table><tr><td>財務報告公告查詢</td></tr></table></html>"
            def raise_for_status(self):
                pass
        with patch("official_filing_candidates.requests.post", return_value=Response()):
            result = probe_mops_financial_announcement("2308", 2026, 3)
        self.assertEqual(result["status"], "query_form_only")
        self.assertFalse(result["response_has_requested_stock"])

    def test_session_probe_reuses_client_and_never_verifies_date(self):
        from official_filing_candidates import probe_session_backed_filing_query
        from unittest.mock import Mock
        def fake_response(body):
            response = Mock()
            response.text = body
            response.raise_for_status.return_value = None
            return response
        client = Mock()
        client.get.return_value = fake_response("<html><script></script></html>")
        client.post.return_value = fake_response("<html><table><tr><td>查詢介面</td></tr></table></html>")
        result = probe_session_backed_filing_query("2308", 2026, 3, session=client)
        self.assertEqual(result["status"], "session_diagnostic_only")
        self.assertFalse(result["same_response"])
        self.assertTrue(result["ajax_result"]["has_table"])
        self.assertFalse(result["ajax_result"]["has_stock_code"])
        self.assertEqual(client.get.call_count, 1)
        self.assertEqual(client.post.call_count, 1)
        self.assertNotIn("公告日期", result)

    def test_three_quarter_identical_responses_stay_unverified(self):
        from official_filing_candidates import compare_filing_quarters
        def probe(stock_code, year, quarter, timeout=12):
            return {"status": "session_diagnostic_only",
                    "ajax_result": {"chars": 2517, "has_table": False,
                                    "has_stock_code": False, "sha256_prefix": "same123"}}
        result = compare_filing_quarters("2308", probe=probe)
        self.assertEqual(len(result["rows"]), 3)
        self.assertTrue(result["all_ajax_responses_identical"])
        self.assertEqual(result["verified_filing_dates"], 0)
        self.assertEqual([r["季度"] for r in result["rows"]],
                         ["2026Q3", "2025Q4", "2024Q4"])

    def test_three_quarter_probe_error_is_isolated(self):
        from official_filing_candidates import compare_filing_quarters
        def probe(stock_code, year, quarter, timeout=12):
            if year == 2025:
                raise RuntimeError("network")
            return {"status": "session_diagnostic_only",
                    "ajax_result": {"sha256_prefix": str(year)}}
        result = compare_filing_quarters("2308", probe=probe)
        self.assertFalse(result["all_ajax_responses_identical"])
        self.assertEqual(result["rows"][1]["查詢狀態"], "probe_error")
        self.assertEqual(result["verified_filing_dates"], 0)

    def test_duplicate_reports_are_not_verified(self):
        rows = [{"季度": "2025Q4"}, {"季度": "2025Q4"}]
        review = review_candidate_coverage(rows, ["2025Q4", "2026Q1"])
        self.assertIn("多筆", review[0]["狀態"])
        self.assertEqual(review[1]["候選公告筆數"], 0)


if __name__ == "__main__":
    unittest.main()
