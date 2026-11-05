"""Optional live 5-year TW daily-bar Adam mirror verification.

Loads the exact production pivot/mirror functions via AST to avoid Streamlit UI.
Does not claim mirror projections predict future prices.
"""
import ast
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import yfinance as yf


def load_mirror_engine():
    source = ast.parse((Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8"))
    required = {"find_pivots", "future_index", "internal_turns", "mirror_wave"}
    functions = [n for n in source.body if isinstance(n, ast.FunctionDef) and n.name in required]
    if {n.name for n in functions} != required:
        raise RuntimeError("找不到完整亞當鏡像函式")
    scope = {
        "np": np, "pd": pd,
        "WAVES": {"短波": (3, 100), "中波": (7, 260), "長波": (14, 650)},
        "COLORS": {"短波": "#16a34a", "中波": "#ea580c", "長波": "#dc2626"},
    }
    exec(compile(ast.fix_missing_locations(ast.Module(body=functions, type_ignores=[])),
                 "app.py", "exec"), scope)
    return scope["mirror_wave"], scope["WAVES"]


def validate_projection(result, latest):
    segment = np.asarray(result["segment"], dtype=float)
    projection = np.asarray(result["projection"], dtype=float)
    expected = latest + segment[::-1] - segment[-1]
    if len(projection) != len(segment) or len(result["times"]) != len(projection):
        raise AssertionError("鏡像長度或日期長度不一致")
    if not np.allclose(projection, expected, atol=1e-8, rtol=1e-10):
        raise AssertionError("鏡像不符合歷史時間左右反轉公式")
    if not np.isclose(projection[0], latest):
        raise AssertionError("鏡像起點未錨定最新收盤價")
    if not result["times"].is_monotonic_increasing:
        raise AssertionError("鏡像日期未遞增")
    if not np.isfinite(projection).all():
        raise AssertionError("鏡像存在非有限數值")


def main():
    mirror, settings = load_mirror_engine()
    failed = False
    for symbol in ("2330.TW", "2308.TW"):
        try:
            df = yf.download(symbol, period="5y", interval="1d",
                             auto_adjust=False, progress=False, threads=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if df.empty or "Close" not in df:
                raise ValueError("無有效日K")
            df = df.dropna(subset=["Close"]).sort_index()
            if len(df) < settings["長波"][1]:
                raise ValueError(f"日K僅 {len(df)} 根，長波需要 {settings['長波'][1]} 根")
            latest = float(df["Close"].iloc[-1])
            print(f"{symbol}: {len(df)} 根日K，最後日期 {pd.Timestamp(df.index[-1]).date()}，最新收盤 {latest:.2f}")
            for name in settings:
                result = mirror(df, name, 3.0, "1d")
                if result is None:
                    print(f"NO_PIVOTS {symbol} {name}: 最近波段轉折不足，未產生鏡像")
                    continue
                validate_projection(result, latest)
                print(f"PASS {symbol} {name}: 歷史段 {len(result['segment'])} 根，鏡像起點 {result['projection'][0]:.2f}，終點 {result['projection'][-1]:.2f}")
        except Exception as exc:
            failed = True
            print(f"FAIL {symbol}: {type(exc).__name__}: {exc}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
