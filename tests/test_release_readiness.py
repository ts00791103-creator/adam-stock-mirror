"""V1 release readiness regression guards; offline, no network."""
import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ReleaseReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "app.py").read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_critical_functions_exist(self):
        names = {n.name for n in self.tree.body if isinstance(n, ast.FunctionDef)}
        for name in ("get_data", "audit_ohlc_data", "raw_quote_summary",
                     "find_pivots", "mirror_wave", "wave_source_rows"):
            with self.subTest(name=name):
                self.assertIn(name, names)

    def test_data_quality_gate_precedes_wave_calculation(self):
        source = self.source
        gate = source.index("    quality_issues = audit_ohlc_data(df)")
        stop = source.index("        st.stop()", gate)
        wave = source.index("    waves = []", gate)
        self.assertLess(gate, stop)
        self.assertLess(stop, wave)

    def test_source_cards_and_caveat_precede_chart(self):
        source = self.source
        cards = source.index('    st.subheader("亞當鏡像｜歷史波段來源")')
        caveat = source.index('    st.caption("鏡像終點僅為歷史時間左右翻轉的情境結果，不是未來價格預測。")', cards)
        chart = source.index('    config = {', caveat)
        self.assertLess(cards, caveat)
        self.assertLess(caveat, chart)

    def test_live_smoke_is_nonblocking(self):
        workflow = (ROOT / ".github/workflows/v1-validation.yml").read_text(encoding="utf-8")
        self.assertIn("Run offline regression tests", workflow)
        self.assertIn("Optional live Taiwan quote smoke check (non-blocking)", workflow)
        self.assertIn("Optional live Taiwan Adam mirror projection check (non-blocking)", workflow)
        self.assertGreaterEqual(workflow.count("continue-on-error: true"), 2)

    def test_handoff_exists(self):
        self.assertTrue((ROOT / "ADAM_V1_HANDOFF.md").is_file())


if __name__ == "__main__":
    unittest.main()
