import ast
import copy
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

from streamlit.testing.v1 import AppTest
import fugle_history_validation as v


PAGE = 'from fugle_history_preview import show_fugle_history_preview\nshow_fugle_history_preview()'


def payload(symbol='5474', day=v.START):
    return {'symbol': symbol, 'exchange': 'TPEx', 'market': 'OTC', 'type': 'EQUITY',
            'timeframe': 'D', 'sort': 'asc', 'data': [
                {'date': day, 'open': 10, 'high': 12, 'low': 9, 'close': 11, 'volume': 1500}]}


def sample_fetch(symbol, start, end, key):
    rows, _ = v.load_baseline(symbol)
    parsed = [{'Date': r['Date'], **{f: r[f] for f in v.FIELDS},
               'Volume': int(r['Volume_shares_scaled']), 'valid_ohlc': v.valid_ohlc(r)}
              for r in rows if start <= r['Date'] <= end]
    return parsed, {'http_status': 200, 'rows': len(parsed), 'parameters': v.request_parameters(symbol, start, end)}


class HistoryValidationTests(unittest.TestCase):
    def test_segments_cover_each_day_once_and_under_one_year(self):
        days = []
        self.assertEqual(len(v.chunks()), 2)
        for start, end in v.chunks():
            first, last = date.fromisoformat(start), date.fromisoformat(end)
            self.assertLess((last-first).days, 365)
            days.extend((first + timedelta(days=i)).isoformat() for i in range((last-first).days+1))
        self.assertEqual(len(days), 366)
        self.assertEqual(len(set(days)), len(days))
        self.assertEqual((days[0], days[-1]), (v.START, v.END))
        with self.assertRaises(v.ValidationError):
            v.request_parameters('2330', *v.chunks()[0])
        with self.assertRaises(v.ValidationError):
            v.request_parameters('5474', v.START, v.END)

    def test_baseline_integrity_and_missing_dates(self):
        for code, expected in [('5474', 242), ('6708', 235), ('9962', 242)]:
            rows, evidence = v.load_baseline(code)
            self.assertEqual(len(rows), 242)
            self.assertEqual(sum(v.valid_ohlc(r) for r in rows), expected)
            self.assertNotIn('2026-10-23', {r['Date'] for r in rows})
            self.assertEqual(len(evidence['known_no_ohlc_dates']), 7 if code == '6708' else 0)

    def test_payload_strict_identity_basis_date_and_order(self):
        args = ('5474', *v.chunks()[0])
        self.assertEqual(len(v.parse_payload(payload(), *args)), 1)
        cases = []
        for key, value in [('symbol', '9962'), ('exchange', 'TWSE'), ('timeframe', '1'),
                           ('market', 'ESB'), ('type', 'INDEX'), ('adjusted', True),
                           ('adjusted', 'false'), ('sort', 'desc'), ('data', [])]:
            p = payload(); p[key] = value; cases.append(p)
        for day in ['2025-11-11T00:00:00+08:00', '2025-11-10', '2026-02-30']:
            p = payload(); p['data'][0]['date'] = day; cases.append(p)
        p = payload(); p['data'] *= 2; cases.append(p)
        p = payload(day='2025-11-12'); p['data'].append(payload()['data'][0]); cases.append(p)
        for p in cases:
            with self.subTest(p=p), self.assertRaises(v.ValidationError):
                v.parse_payload(p, *args)

    def test_invalid_values_never_silently_fill(self):
        args = ('5474', *v.chunks()[0])
        for field, val in [('volume', float('nan')), ('volume', -1), ('volume', 0.5),
                           ('open', float('inf')), ('open', True), ('close', '11')]:
            p = payload(); p['data'][0][field] = val
            with self.subTest(field=field,val=val), self.assertRaises(v.ValidationError):
                v.parse_payload(p, *args)
        p = payload(); del p['data'][0]['open']
        with self.assertRaises(v.ValidationError): v.parse_payload(p, *args)
        for val in [None, 0, 99]:
            p = payload(); p['data'][0]['close'] = val
            self.assertFalse(v.parse_payload(p, *args)[0]['valid_ohlc'])

    def test_transport_secret_only_in_header_and_evidence_allowlist(self):
        p = payload(); p['unexpected'] = 'DO_NOT_ECHO'
        raw = json.dumps(p).encode()
        response = MagicMock(); response.__enter__.return_value = response
        response.read.return_value = raw; response.status = 200
        opener = MagicMock(); opener.open.return_value = response
        with patch.object(v, 'build_opener', return_value=opener):
            rows, evidence = v.fetch_segment('5474', *v.chunks()[0], 'SECRET_SENTINEL')
        request = opener.open.call_args.args[0]
        self.assertEqual(request.get_header('X-api-key'), 'SECRET_SENTINEL')
        self.assertNotIn('SECRET_SENTINEL', request.full_url)
        self.assertEqual(urlsplit(request.full_url).hostname, 'api.fugle.tw')
        self.assertEqual(parse_qs(urlsplit(request.full_url).query)['adjusted'], ['false'])
        self.assertEqual(evidence['response_sha256'], hashlib.sha256(raw).hexdigest())
        self.assertNotIn('DO_NOT_ECHO', json.dumps([rows,evidence]))
        self.assertNotIn('SECRET_SENTINEL', json.dumps([rows,evidence]))
        with self.assertRaises(v.ValidationError):
            v.NoRedirect().redirect_request(None,None,302,'',None,'https://example.com')

    def test_bounded_run_missing_days_and_no_secret_in_report(self):
        fetcher = MagicMock(side_effect=sample_fetch)
        result = v.run_validation('SECRET_SENTINEL', fetcher=fetcher, sleeper=lambda _: None)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(fetcher.call_count, 6)
        self.assertEqual(len(result['samples']), 3)
        self.assertNotIn('SECRET_SENTINEL', json.dumps(result,allow_nan=False))
        sample = result['samples'][1]
        self.assertEqual(sample['summary']['shared_valid_dates'], 235)
        self.assertEqual(len(sample['summary']['official_no_ohlc_dates']), 7)
        self.assertEqual(sample['summary']['price_fields_compared'], 940)
        self.assertFalse(sample['summary']['closure_2026_10_23_fugle_present'])
        missing = [r for r in sample['daily_comparison'] if r['Date'] == '2025-11-20'][0]
        self.assertIsNone(missing['Fugle_Close'])
        self.assertIsNone(missing['TPEx_Close'])

    def test_price_volume_and_extra_dates_are_distinguished(self):
        official, evidence = v.load_baseline('5474')
        row = {'Date': v.START, **{f: official[0][f] for f in v.FIELDS},
               'Volume': int(official[0]['Volume_shares_scaled']) + 1234}
        row['Close'] -= .01
        extra = {'Date': '2026-10-23', 'Open': 10, 'High': 10, 'Low': 10, 'Close': 10, 'Volume': 0}
        original = copy.deepcopy(official)
        result = v.compare_rows('5474', [row,extra], official, evidence)
        self.assertEqual(result['summary']['price_mismatch_fields'], 1)
        self.assertEqual(result['summary']['volume_differing_dates'], 1)
        self.assertEqual(result['summary']['volume_difference_max'], 1234)
        self.assertEqual(result['summary']['fugle_extra_dates'], ['2026-10-23'])
        self.assertEqual(official, original)
        with self.assertRaises(v.ValidationError):
            v.compare_rows('5474', [row,row], official, evidence)

    def test_first_failure_stops_without_retry_or_exception_disclosure(self):
        for error in [HTTPError('https://private/SECRET_SENTINEL', code, 'SECRET_SENTINEL', {}, None)
                      for code in [401,403,429,404,500]] + [OSError('SECRET_SENTINEL')]:
            fetcher = MagicMock(side_effect=error)
            result = v.run_validation('SECRET_SENTINEL', fetcher=fetcher, sleeper=lambda _: None)
            self.assertEqual(fetcher.call_count, 1)
            self.assertEqual(result['status'], 'stopped')
            self.assertEqual(result['requests'][0]['status'], 'failed')
            self.assertNotIn('SECRET_SENTINEL', json.dumps(result))
        fetcher = MagicMock()
        self.assertEqual(v.run_validation('', fetcher=fetcher)['status'], 'blocked')
        fetcher.assert_not_called()


class HistoryPageTests(unittest.TestCase):
    def test_unconfigured_and_locked_page_never_fetch(self):
        with patch('fugle_history_preview._secret', return_value=''), patch('fugle_history_preview.run_validation') as run:
            app = AppTest.from_string(PAGE).run()
            self.assertEqual(len(app.text_input), 0)
            run.assert_not_called()
        with patch('fugle_history_preview._secret', side_effect=lambda k:'SECRET_SENTINEL' if k=='FUGLE_API_KEY' else '密碼'), \
             patch('fugle_history_preview.run_validation') as run:
            app = AppTest.from_string(PAGE).run()
            self.assertEqual([b.key for b in app.button], ["fugle_history_back"])
            app.text_input[0].set_value('wrong').run()
            self.assertEqual([b.key for b in app.button], ["fugle_history_back"])
            run.assert_not_called()
            self.assertEqual(len(app.exception), 0)

    def test_unlock_run_rerun_cooldown_lock_and_failed_result(self):
        report = v.run_validation('mock', fetcher=sample_fetch, sleeper=lambda _:None)
        with patch('fugle_history_preview._secret', side_effect=lambda k:'SECRET_SENTINEL' if k=='FUGLE_API_KEY' else '密碼'), \
             patch('fugle_history_preview.run_validation', return_value=report) as run:
            app = AppTest.from_string(PAGE).run()
            app.text_input[0].set_value('密碼').run()
            run.assert_not_called()
            next(b for b in app.button if b.key=='fugle_history_run').click().run()
            self.assertEqual(run.call_count, 1)
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(len(app.success), 1)
            app.run(); self.assertEqual(run.call_count, 1)
            next(b for b in app.button if b.key=='fugle_history_run').click().run()
            self.assertEqual(run.call_count, 1)
            app.text_input[0].set_value('wrong').run()
            self.assertEqual(len(app.dataframe), 0)
            self.assertNotIn('fugle_history_validation_result', app.session_state)
            app.text_input[0].set_value('密碼').run()
            next(b for b in app.button if b.key=='fugle_history_lock').click().run()
            self.assertEqual(app.text_input[0].value, '')
            self.assertEqual([b.key for b in app.button], ["fugle_history_back"])
            self.assertEqual(len(app.exception), 0)

    def test_real_entry_route_and_return_stay_in_session(self):
        with patch('fugle_history_preview._secret', return_value=''), \
             patch('fugle_history_preview.run_validation') as run, \
             patch('urllib.request.urlopen', side_effect=OSError('offline')):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=30)
            app.query_params['view'] = 'fugle-history'
            app.run()
            self.assertEqual(len(app.exception), 0)
            self.assertTrue(any('受保護測試頁' in h.value for h in app.subheader))
            self.assertFalse(any(b.key == 'screen_run' for b in app.button))
            app.button(key='fugle_history_back').click().run()
            self.assertEqual(len(app.exception), 0)
            self.assertNotIn('view', app.query_params)
            app.button(key='open_fugle_history').click().run()
            self.assertEqual(app.query_params['view'], 'fugle-history')
            self.assertEqual(len(app.exception), 0)
            run.assert_not_called()

    def test_page_route_is_guarded_by_production_flag(self):
        tree = ast.parse(Path('app.py').read_text())
        found = []
        for node in tree.body:
            if isinstance(node, ast.If) and ast.unparse(node.test) == 'not PRODUCTION_MODE':
                if 'show_fugle_history_preview' in ast.unparse(node): found.append(node)
        self.assertEqual(len(found), 1)
        self.assertIn('st.stop()', ast.unparse(found[0]))
        self.assertIn('"PRODUCTION_MODE": True', Path('production_app.py').read_text())


if __name__ == '__main__': unittest.main()
