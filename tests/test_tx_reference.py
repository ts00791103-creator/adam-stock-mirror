import ast
from pathlib import Path
import unittest
from tx_reference import enabled, example_references, validate_reference, export_csv


class TxReferenceTests(unittest.TestCase):
    def test_scope_excludes_stocks_index_and_production(self):
        self.assertTrue(enabled("台指期 TX（官方 CSV）"))
        for market in ("台灣股票／ETF", "台股加權指數", "自訂"):
            self.assertFalse(enabled(market))
        self.assertFalse(enabled("台指期 TX（官方 CSV）", True))

    def test_examples_are_unverified_and_not_mutated(self):
        records = example_references()
        self.assertEqual([r["target"] for r in records], [41216, 42839, 40719])
        self.assertTrue(all("待核對" in r["status"] for r in records))
        records[0]["target"] = 1
        self.assertEqual(example_references()[0]["target"], 41216)

    def test_user_cannot_self_certify_signal(self):
        row = example_references()[0]
        row["status"] = "有效"
        self.assertIn("待核對", validate_reference(row)["status"])

    def test_bad_prices_direction_period_and_link_rejected(self):
        for change in ({"target": float('nan')}, {"invalidation": float('inf')},
                       {"target": 0}, {"target": 99999}, {"period": "週K"},
                       {"source": "javascript:alert(1)"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_reference({**example_references()[0], **change})

    def test_export_preserves_source_period_and_uncertainty(self):
        value = export_csv(example_references())
        self.assertIn("60分K", value)
        self.assertIn("iCbMHLc3oUM", value)
        self.assertIn("待核對", value)

    def test_app_hook_has_market_and_production_guards(self):
        root = ast.parse(Path('app.py').read_text(encoding='utf-8'))
        hooks = [node for node in ast.walk(root) if isinstance(node, ast.If)
                 and any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                         and n.func.id == 'show_tx_reference' for s in node.body for n in ast.walk(s))]
        self.assertEqual(len(hooks), 1)
        self.assertIn('PRODUCTION_MODE', ast.unparse(hooks[0].test))
        self.assertIn('台指期 TX（官方 CSV）', ast.unparse(hooks[0].test))


if __name__ == '__main__':
    unittest.main()
