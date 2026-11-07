"""Test the exact staged production UI before moving the production branch."""
from pathlib import Path
from unittest.mock import patch
from concurrent.futures import Future
import test_production_entry as entry
from streamlit.testing.v1 import AppTest

ROOT=Path(__file__).resolve().parents[1]


class ProductionFinancialReleaseTests(entry.ProductionEntryTests):
    def make_app(self):
        return AppTest.from_file(str(ROOT/"production_financial_preview.py"),default_timeout=45)

    def test_financial_option_and_independent_completed_book_render(self):
        growth,book=Future(),Future()
        growth.set_result(({"error":"缺少連續八季"},[]))
        book.set_result(({"value":123.45,"quarter":"2026Q2","field":"fixture",
             "published_snapshot":"fixture","source":"fixture","age_days":100,
             "provider":"Yahoo Finance 替代來源，未經官方交叉核實",
             "common_equity":123450.,"ordinary_shares":1000.},None))
        job={"symbol":"2308.TW","retrieved_at":"fixture","futures":{"growth":growth,"book":book}}
        with patch("urllib.request.urlopen",side_effect=OSError("offline")), \
             patch("financial_jobs.start_job",return_value=(job,None)) as start:
            app=self.make_app().run()
            self.assertEqual(len(app.exception),0)
            self.assertTrue(app.checkbox(key="auto_financial_alternative").value)
            app.button(key="auto_fundamentals_load").click().run()
            self.assertEqual(len(app.exception),0)
            start.assert_called_once()
            self.assertIn("123.45",[m.value for m in app.metric])
            self.assertTrue(any("替代來源" in w.value for w in app.warning))
