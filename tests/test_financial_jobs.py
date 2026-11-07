import unittest
from concurrent.futures import Future
from threading import Event
from unittest.mock import patch
import pandas as pd
import financial_jobs as jobs
from auto_fundamentals import fetch_alternative_book_value


class FinancialJobTests(unittest.TestCase):
    def test_pending_eps_does_not_hide_completed_book(self):
        growth, book = Future(), Future()
        book.set_result(({'value': 100}, None))
        job = {'symbol':'2330.TW','retrieved_at':'now','futures':{'growth':growth,'book':book}}
        r = jobs.poll_job(job)
        self.assertEqual(r['book']['value'], 100)
        self.assertEqual(r['pending'], ['growth'])
        growth.set_result(({'growth_pct': 50}, []))
        # Result survives arbitrary polling; no completed result is discarded.
        for _ in range(3):
            r = jobs.poll_job(job)
            self.assertEqual(r['growth']['growth_pct'], 50)
            self.assertEqual(r['pending'], [])

    def test_one_source_failure_preserves_other(self):
        growth, book = Future(), Future()
        growth.set_exception(OSError('offline'))
        book.set_result(({'value': 10}, None))
        r = jobs.poll_job({'symbol':'2330.TW','retrieved_at':'now','futures':{'growth':growth,'book':book}})
        self.assertIn('error', r['growth']); self.assertEqual(r['book']['value'],10)

    def test_repeated_start_reuses_pending_job(self):
        release = Event()
        def growth(symbol): release.wait(3); return {}, []
        def book(symbol, alternative): release.wait(3); return None, 'missing'
        with patch.dict(jobs._jobs, {}, clear=True):
            try:
                first,_=jobs.start_job('2330.TW',growth_loader=growth,book_loader=book)
                second,_=jobs.start_job('2330.TW',growth_loader=growth,book_loader=book)
                self.assertIs(first,second)
            finally:
                release.set()
                for f in first['futures'].values(): f.result(timeout=5)

    def test_fallback_requires_same_date_common_equity_and_shares(self):
        class Ticker:
            def get_info(self): return {'financialCurrency':'TWD'}
            quarterly_balance_sheet=pd.DataFrame({pd.Timestamp('2026-06-30'):[2000,100],
                                                 pd.Timestamp('2026-09-30'):[3000,float('nan')]},
                       index=['Common Stock Equity','Ordinary Shares Number'])
        value,error=fetch_alternative_book_value('2330.TW',Ticker())
        self.assertIsNone(error); self.assertEqual(value['value'],20)
        self.assertEqual(value['quarter'],'2026Q2')
        self.assertIn('未經官方',value['provider'])
        Ticker.get_info=lambda self: {'financialCurrency':'USD'}
        value,error=fetch_alternative_book_value('2330.TW',Ticker())
        self.assertIsNone(value); self.assertIn('TWD',error)


if __name__ == '__main__': unittest.main()
