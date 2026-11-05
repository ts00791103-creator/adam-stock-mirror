"""Scenario disclosures must preserve the original projection values."""
import ast
from pathlib import Path
import unittest
import numpy as np


ROOT = Path(__file__).resolve().parents[1]


class ProjectionWarningsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "app.py").read_text(encoding="utf-8")
        tree = ast.parse(cls.source)
        nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                 and n.name == "projection_warnings"]
        scope = {"np": np}
        exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])),
                     "app.py", "exec"), scope)
        cls.warn = staticmethod(scope["projection_warnings"])

    def test_positive_prices_need_no_warning(self):
        self.assertEqual(self.warn([{"name": "短波", "projection": [100, 110]}]), [])
        self.assertEqual(self.warn([]), [])

    def test_negative_and_zero_prices_are_disclosed_without_clipping(self):
        prices = np.array([1130., 0., -420.])
        before = prices.copy()
        messages = self.warn([{"name": "中波", "projection": prices}])
        self.assertEqual(len(messages), 1)
        self.assertIn("中波", messages[0])
        self.assertIn("-420.00", messages[0])
        self.assertIn("不是可交易", messages[0])
        np.testing.assert_array_equal(prices, before)

    def test_nonfinite_prices_are_disclosed(self):
        messages = self.warn([{"name": "長波", "projection": [np.nan, np.inf]}])
        self.assertEqual(len(messages), 1)
        self.assertIn("非有限數值", messages[0])

    def test_each_affected_wave_is_named(self):
        messages = self.warn([{"name": "中波", "projection": [0.]},
                              {"name": "長波", "projection": [-995.5]}])
        self.assertEqual(len(messages), 2)
        self.assertIn("中波", messages[0])
        self.assertIn("長波", messages[1])

    def test_disclosure_precedes_sources_and_chart(self):
        self.assertLess(self.source.index("    for message in projection_warnings(waves):"),
                        self.source.index('    st.subheader("亞當鏡像｜歷史波段來源")'))


if __name__ == "__main__":
    unittest.main()
