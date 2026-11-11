import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest


SOURCE = "from live_quote import show_personal_quote\nshow_personal_quote('台灣股票／ETF','2330.TW',production=True)"


class LiveQuotePanelTests(unittest.TestCase):
    def test_full_width_rows_preserve_complete_quote_values(self):
        source = """
import streamlit as st
from studio_layout import apply_studio_layout
from live_quote import _render_quote_metrics
apply_studio_layout(st)
with st.sidebar:
    _render_quote_metrics(1295, 20, 20 / 1275 * 100)
st.metric("Unrelated metric", "123.00")
"""
        app = AppTest.from_string(source).run()
        rows = app.sidebar.get("metric")
        self.assertEqual([row.label for row in rows], ["最新成交價", "漲跌", "漲跌幅"])
        self.assertEqual([row.value for row in rows], ["1,295.00", "+20.00", "+1.57%"])
        self.assertEqual(len(app.sidebar.get("column")), 0)
        css = next(item.value for item in app.markdown if ".st-key-live_quote_metrics" in item.value)
        self.assertIn("white-space:nowrap!important", css)
        self.assertEqual(len(app.exception), 0)

    def test_negative_zero_and_missing_change_keep_original_format(self):
        for previous, expected in [(1300, ["1,295.00", "-5.00", "-0.38%"]),
                                   (1295, ["1,295.00", "+0.00", "+0.00%"]),
                                   (None, ["1,295.00", "—", "—"])]:
            with self.subTest(previous=previous), \
                 patch('live_quote._fetch_quote', return_value={'lastTrade': {'price': 1295},
                                                               'previousClose': previous}):
                app = AppTest.from_string("from live_quote import _render_quote\n_render_quote('2330','test')").run()
                self.assertEqual([row.value for row in app.metric], expected)
                self.assertEqual(len(app.exception), 0)

    def test_auto_refresh_toggle_and_repeated_manual_query(self):
        with patch('live_quote._secret', return_value='pw'), \
             patch('live_quote._fetch_quote', return_value={'lastTrade': {'price': 1295}, 'previousClose': 1275}) as fetch:
            app = AppTest.from_string(SOURCE).run()
            app.text_input[0].set_value('pw').run()
            app.checkbox(key='live_quote_enabled').check().run()
            self.assertEqual(fetch.call_count, 1)
            self.assertEqual([row.value for row in app.metric], ['1,295.00', '+20.00', '+1.57%'])
            app.checkbox(key='live_quote_enabled').uncheck().run()
            self.assertEqual(fetch.call_count, 1)
            self.assertEqual(len(app.metric), 0)
            for expected_count in (2, 3):
                app.button(key='live_quote_refresh').click().run()
                self.assertEqual(fetch.call_count, expected_count)
                self.assertEqual(len(app.metric), 3)
            app.text_input[0].set_value('wrong').run()
            self.assertEqual(fetch.call_count, 3)
            self.assertEqual(len(app.metric), 0)
            self.assertEqual(len(app.exception), 0)

    def test_missing_setup_does_not_request_data(self):
        with patch('live_quote._secret', return_value=''), patch('live_quote._fetch_quote') as fetch:
            app = AppTest.from_string(SOURCE).run()
            fetch.assert_not_called()
            self.assertTrue(any('設定 FUGLE_API_KEY' in i.value for i in app.info))
            self.assertEqual(len(app.exception), 0)

    def test_password_gate_single_request_and_invalid_data(self):
        with patch('live_quote._secret', side_effect=lambda key: 'key' if key == 'FUGLE_API_KEY' else 'pw'), \
             patch('live_quote._fetch_quote', return_value={'lastTrade': {'price': 123}, 'previousClose': 120}) as fetch:
            app = AppTest.from_string(SOURCE).run()
            app.text_input[0].set_value('wrong').run()
            fetch.assert_not_called()
            app.text_input[0].set_value('pw').run()
            fetch.assert_not_called()
            next(b for b in app.button if b.key == 'live_quote_refresh').click().run()
            self.assertEqual(fetch.call_count, 1)
            self.assertEqual(app.metric[0].value, '123.00')
            self.assertTrue(any('尚無成交時間' in c.value for c in app.caption))
            fetch.return_value = {'lastTrade': {'price': float('nan')}}
            next(b for b in app.button if b.key == 'live_quote_refresh').click().run()
            self.assertEqual(len(app.metric), 0)
            self.assertTrue(any('無效成交價' in w.value for w in app.warning))
            self.assertEqual(len(app.exception), 0)

    def test_connection_failure_clears_price(self):
        with patch('live_quote._secret', return_value='pw'), \
             patch('live_quote._fetch_quote', side_effect=OSError('offline')):
            app = AppTest.from_string(SOURCE).run()
            app.text_input[0].set_value('pw').run()
            next(b for b in app.button if b.key == 'live_quote_refresh').click().run()
            self.assertEqual(len(app.metric), 0)
            self.assertTrue(any('連線失敗' in w.value for w in app.warning))
            self.assertEqual(len(app.exception), 0)
