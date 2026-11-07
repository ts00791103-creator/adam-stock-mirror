import unittest
from datetime import date
import pandas as pd
from auto_fundamentals import eps_growth, parse_book_value, fetch_book_value, fetch_fundamentals, stock_code


def quarters():
    return [{"quarter": str(p), "quarter_eps": 2.0 if p.year == 2025 else 1.0,
             "ytd_consistent": True, "source": "https://mopsov.twse.com.tw"}
            for p in pd.period_range('2024Q1', '2025Q4', freq='Q')]


class FinancialTests(unittest.TestCase):
    def test_growth_uses_eight_consecutive_quarters(self):
        r = eps_growth(quarters(), as_of='2026-01-01')
        self.assertEqual(r['recent_ttm'], 8)
        self.assertEqual(r['prior_ttm'], 4)
        self.assertEqual(r['growth_pct'], 100)

    def test_gap_not_filled_or_replaced_by_older_quarter(self):
        rows = quarters(); rows.pop(3)
        rows.insert(0, dict(rows[0], quarter='2023Q4'))
        self.assertIsNone(eps_growth(rows, as_of='2026-01-01')['growth_pct'])

    def test_inconsistent_ytd_and_nonfinite_rejected(self):
        for field, value in [('ytd_consistent', False), ('quarter_eps', float('nan'))]:
            rows = quarters(); rows[-1][field] = value
            self.assertIsNone(eps_growth(rows, as_of='2026-01-01')['growth_pct'])

    def test_loss_denominator_and_recent_loss(self):
        for index in (0, 7):
            rows = quarters(); rows[index]['quarter_eps'] = -20
            self.assertIsNone(eps_growth(rows, as_of='2026-01-01')['growth_pct'])

    def test_duplicate_and_future(self):
        rows = quarters()
        with self.assertRaises(ValueError): eps_growth(rows + [rows[0]], as_of='2026-01-01')
        rows.append(dict(rows[-1], quarter='2026Q1', quarter_eps=1000))
        self.assertEqual(eps_growth(rows, as_of='2026-01-01')['quarter'], '2025Q4')

    def test_book_value_is_official_per_share_not_total_equity(self):
        row = {'公司代號':'2449', '年度':'114', '季別':'3', '每股參考淨值':'39.91',
               '權益總計':'99999999', '股本':'1000'}
        r = parse_book_value([row], '2449', 'official', as_of='2026-01-01')
        self.assertEqual(r['value'], 39.91)
        self.assertEqual(r['quarter'], '2025Q3')
        self.assertIsNone(parse_book_value([row], '3413', 'official', as_of='2026-01-01'))
        row['每股參考淨值']='--'
        self.assertIsNone(parse_book_value([row], '2449', 'official', as_of='2026-01-01'))

    def test_conflicting_book_value_not_silently_selected(self):
        row = {'公司代號':'2449','年度':'114','季別':'3','每股參考淨值':'10'}
        with self.assertRaises(ValueError):
            parse_book_value([row,dict(row, 每股參考淨值='11')], '2449','official',as_of='2026-01-01')

    def test_tpex_endpoint(self):
        urls=[]
        class Response:
            def raise_for_status(self): pass
            def json(self): return [{'公司代號':'3413','年度':'114','季別':'3','每股淨值':'100'}]
        def get(url, **kwargs): urls.append(url); return Response()
        result, error = fetch_book_value('3413.TWO', getter=get)
        self.assertIsNone(error); self.assertEqual(result['value'],100)
        self.assertIn('mopsfin_t187ap07_O_ci', urls[0])

    def test_partial_failure_keeps_independent_metric(self):
        def history(*args, **kwargs): return [], [{'quarter':'2025Q4','reason':'missing'}]
        result,error=fetch_fundamentals('2449.TW', history_fetcher=history,
            book_fetcher=lambda _: ({'value':10},None))
        self.assertIsNone(error); self.assertEqual(result['book']['value'],10)
        self.assertIn('error',result['growth'])

    def test_other_markets_not_allowed(self):
        for symbol in ['AAPL','BTC-USD','2330','2330.TW;echo','0050.TW']:
            with self.assertRaises(ValueError): stock_code(symbol)


class AutoPanelTests(unittest.TestCase):
    def test_load_button_renders_metrics_and_never_leaks_across_symbols(self):
        from streamlit.testing.v1 import AppTest
        code = '''
import streamlit as st
import auto_fundamentals as af
symbol = st.text_input("symbol", value="2449.TW")
def fixture(symbol):
    return {"symbol":symbol,"retrieved_at":"2026-11-07T00:00:00+00:00",
        "growth":{"recent_ttm":8,"prior_ttm":4,"growth_pct":100,"quarter":"2026Q2","quarter_end":"2026-06-30","age_days":130},
        "book":{"value":39.91,"quarter":"2026Q2","field":"每股參考淨值","published_snapshot":"1151107","source":"official","age_days":130},
        "book_error":None,"history_failures":[]}, None
af.fetch_fundamentals = fixture
af.render_auto_fundamentals(st.sidebar, symbol, "台灣股票／ETF")
'''
        app = AppTest.from_string(code).run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.metric), 0)
        app.button(key="auto_fundamentals_load").click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual([m.value for m in app.metric], ['8.00','100.00','39.91'])
        app.text_input[0].set_value('3413.TW').run()
        self.assertEqual(len(app.metric), 0)
        app.text_input[0].set_value('0050.TW').run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.button), 0)


if __name__ == '__main__': unittest.main()
