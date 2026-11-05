import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest


SOURCE = "from live_quote import show_personal_quote\nshow_personal_quote('台灣股票／ETF','2330.TW',production=True)"


class LiveQuotePanelTests(unittest.TestCase):
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
