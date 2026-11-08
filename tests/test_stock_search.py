import unittest
from stock_search import search_stocks, preferred_stock_index


class StockSearchTests(unittest.TestCase):
    stocks = [("020020", "元大台股領航N", "上市"), ("020025", "統一亞洲半導體N", "上櫃"),
              ("2002", "中鋼", "上市"), ("2330", "台積電", "上市"),
              ("2308", "台達電", "上市"), ("6488", "環球晶", "上櫃")]

    def test_complete_code_outranks_substrings_and_stale_context(self):
        choices = search_stocks(self.stocks, "2002")
        self.assertEqual(choices[0][0], "2002")
        self.assertIn(self.stocks[0], choices)
        self.assertEqual(preferred_stock_index(choices, "2002", "020020.TW"), 0)

    def test_leading_zero_and_other_complete_codes(self):
        for code in ("020020", "2330", "2308", "6488"):
            self.assertEqual(search_stocks(self.stocks, code)[0][0], code)

    def test_names_partial_codes_and_empty(self):
        self.assertEqual(search_stocks(self.stocks, " 中鋼 ")[0][0], "2002")
        self.assertEqual([r[0] for r in search_stocks(self.stocks, "23")], ["2330", "2308"])
        self.assertEqual([r[0] for r in search_stocks(self.stocks, "台")], ["2330", "2308", "020020"])
        self.assertEqual(search_stocks(self.stocks, ""), [])
        self.assertEqual(search_stocks(self.stocks, "不存在"), [])

    def test_partial_query_retains_explicit_navigation_context(self):
        choices = search_stocks(self.stocks, "23")
        self.assertEqual(choices[preferred_stock_index(choices, "23", "2308.TW")][0], "2308")
