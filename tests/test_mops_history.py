"""Regression tests for MOPS EPS header and TTM safeguards.
Run: python -m unittest discover -s tests -p 'test_mops_history.py'
"""
import unittest
from unittest.mock import patch
import pandas as pd
import mops_history


class TestMopsHistory(unittest.TestCase):
    def test_2023_q3_multilevel_header(self):
        columns = pd.MultiIndex.from_tuples([
            ("民國112年第3季", "單位：新台幣仟元", "會計項目", "Unnamed"),
            ("民國112年第3季", "單位：新台幣仟元", "112年第3季", "金額"),
            ("民國112年第3季", "單位：新台幣仟元", "112年第3季", "%"),
            ("民國112年第3季", "單位：新台幣仟元", "111年第3季", "金額"),
            ("民國112年第3季", "單位：新台幣仟元", "111年第3季", "%"),
            ("民國112年第3季", "單位：新台幣仟元", "112年01月01日至112年09月30日", "金額"),
            ("民國112年第3季", "單位：新台幣仟元", "112年01月01日至112年09月30日", "%"),
            ("民國112年第3季", "單位：新台幣仟元", "111年01月01日至111年09月30日", "金額"),
        ])
        frame = pd.DataFrame([["基本每股盈餘", 3.6, None, 4.26, None, 9.4, None, 9.53]], columns=columns)
        class Response:
            text = "mock"
            def raise_for_status(self):
                return None
        with patch.object(mops_history.requests, "post", return_value=Response()), patch.object(mops_history.pd, "read_html", return_value=[frame]):
            result, error = mops_history.fetch_mops_quarter("2308", 2023, 3)
        self.assertIsNone(error)
        self.assertTrue(result["column_verified"])
        self.assertEqual(result["verified_eps"], {"quarter_eps": 3.6, "cumulative_eps": 9.4})
        self.assertFalse(result["filing_date_verified"])

    def test_q1_single_eps_header(self):
        columns = pd.MultiIndex.from_tuples([
            ("民國114年第1季", "會計項目", "Unnamed"),
            ("民國114年第1季", "114年第1季", "金額"),
            ("民國114年第1季", "113年第1季", "金額"),
        ])
        frame = pd.DataFrame([["基本每股盈餘", 2.5, 2.0]], columns=columns)
        class Response:
            text = "mock"
            def raise_for_status(self):
                pass
        with patch.object(mops_history.requests, "post", return_value=Response()), patch.object(mops_history.pd, "read_html", return_value=[frame]):
            result, error = mops_history.fetch_mops_quarter("2308", 2025, 1)
        self.assertIsNone(error)
        self.assertTrue(result["column_verified"])
        self.assertEqual(result["verified_eps"], {"quarter_eps": 2.5, "cumulative_eps": 2.5})

    def test_ttm_complete_four_quarters(self):
        def fake(symbol, year, quarter):
            return {"column_verified": True, "verified_eps": {
                "quarter_eps": 2.0, "cumulative_eps": float(quarter * 2),
            }, "source": "mock"}, None
        with patch.object(mops_history, "fetch_mops_quarter", side_effect=fake):
            rows, failures = mops_history.fetch_mops_eps_history("2308", years=1, end_period="2025Q4")
        self.assertEqual(len(rows), 4)
        self.assertEqual(failures, [])
        self.assertEqual(rows[-1]["ttm_eps"], 8.0)
        self.assertTrue(all(x["filing_date"] is None for x in rows))

    def test_ttm_requires_four_consecutive_quarters(self):
        def fake(symbol, year, quarter):
            period = pd.Period(year=year, quarter=quarter, freq="Q")
            if str(period) == "2025Q2":
                return None, "missing"
            return {"column_verified": True, "verified_eps": {
                "quarter_eps": 1.0, "cumulative_eps": float(quarter),
            }, "source": "mock"}, None
        with patch.object(mops_history, "fetch_mops_quarter", side_effect=fake):
            rows, failures = mops_history.fetch_mops_eps_history("2308", years=1, end_period="2025Q4")
        self.assertEqual(len(rows), 3)
        self.assertTrue(any(x["quarter"] == "2025Q2" for x in failures))
        self.assertTrue(all(x["ttm_eps"] is None for x in rows))
        self.assertTrue(all(x["filing_date"] is None for x in rows))

if __name__ == "__main__":
    unittest.main()
