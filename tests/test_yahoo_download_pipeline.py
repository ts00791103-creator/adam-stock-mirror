"""Yahoo download integration tests: mock network, run actual get_data function."""
import ast
from pathlib import Path
import types
import unittest
from unittest.mock import Mock
import numpy as np
import pandas as pd


def load_pipeline(download):
    source = ast.parse((Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8"))
    names = {"raw_quote_summary", "get_data", "audit_ohlc_data"}
    selected = [node for node in source.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert len(selected) == 3
    for node in selected:
        node.decorator_list = []
    scope = {"pd": pd, "np": np, "yf": types.SimpleNamespace(download=download)}
    exec(compile(ast.fix_missing_locations(ast.Module(body=selected, type_ignores=[])), "app.py", "exec"), scope)
    return scope


def bars(index, close):
    return pd.DataFrame({"Open": close, "High": np.asarray(close) + 1,
                         "Low": np.asarray(close) - 1, "Close": close,
                         "Volume": [100] * len(close)}, index=pd.DatetimeIndex(index))


class YahooDownloadPipelineTests(unittest.TestCase):
    def test_unsorted_duplicate_missing_close_survive_as_notes(self):
        original = bars(["2026-11-04", "2026-11-03", "2026-11-03", "2026-11-05"],
                        [103., 100., 101., np.nan])
        download = Mock(return_value=original)
        scope = load_pipeline(download)
        cleaned = scope["get_data"]("2330.TW", "1y", "1d")
        self.assertEqual(cleaned["Close"].tolist(), [101., 103.])
        self.assertTrue(cleaned.index.is_monotonic_increasing)
        self.assertFalse(cleaned.index.has_duplicates)
        notes = cleaned.attrs["raw_quote_notes"]
        self.assertEqual(len(notes), 3)
        self.assertEqual(scope["audit_ohlc_data"](cleaned), [])
        download.assert_called_once_with("2330.TW", period="1y", interval="1d",
                                         auto_adjust=False, progress=False, threads=False)

    def test_yahoo_multiindex_is_flattened(self):
        original = bars(["2026-11-03", "2026-11-04"], [100., 101.])
        original.columns = pd.MultiIndex.from_product([original.columns, ["2330.TW"]])
        scope = load_pipeline(Mock(return_value=original))
        cleaned = scope["get_data"]("2330.TW", "1y", "1d")
        self.assertIn("Close", cleaned.columns)
        self.assertEqual(cleaned["Close"].tolist(), [100., 101.])

    def test_ten_minute_bars_do_not_merge_across_sessions(self):
        times = ["2026-11-03 13:25", "2026-11-04 09:00", "2026-11-04 09:05",
                 "2026-11-04 09:10"]
        original = bars(times, [100., 110., 111., 112.])
        scope = load_pipeline(Mock(return_value=original))
        cleaned = scope["get_data"]("2330.TW", "5d", "10m")
        self.assertEqual(len(cleaned), 3)
        self.assertEqual(cleaned["Close"].tolist(), [100., 111., 112.])
        self.assertEqual(cleaned["Volume"].tolist(), [100, 200, 100])

    def test_infinite_price_remains_visible_to_quality_gate(self):
        original = bars(["2026-11-03", "2026-11-04"], [100., np.inf])
        scope = load_pipeline(Mock(return_value=original))
        cleaned = scope["get_data"]("2330.TW", "1y", "1d")
        self.assertTrue(any("缺漏" in x for x in cleaned.attrs["raw_quote_notes"]))
        self.assertTrue(any("缺漏" in x for x in scope["audit_ohlc_data"](cleaned)))

    def test_empty_download_does_not_crash(self):
        scope = load_pipeline(Mock(return_value=pd.DataFrame()))
        self.assertTrue(scope["get_data"]("2330.TW", "1y", "1d").empty)


if __name__ == "__main__":
    unittest.main()
