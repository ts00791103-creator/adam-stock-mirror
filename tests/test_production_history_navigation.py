"""Run production navigation and quality safeguards with full retained history."""
from pathlib import Path
from streamlit.testing.v1 import AppTest
import test_initial_navigation as original

ROOT=Path(__file__).resolve().parents[1]


class ProductionHistoryNavigationTests(original.InitialNavigationTests):
    def make_app(self):
        app=AppTest.from_file(str(ROOT/"production_history_preview.py"),default_timeout=45)
        app.session_state["market_scan"]=original.seed()
        return app.run()

    def test_exact_staged_production_app(self):
        actual=(ROOT/"production_history_preview.py").read_text(encoding="utf-8")
        expected=(ROOT/"release-preview/v1.0.7/app.py").read_text(encoding="utf-8")
        self.assertEqual(actual,"PRODUCTION_MODE = True\n"+expected)
