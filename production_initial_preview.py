PRODUCTION_MODE = True
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from mobile_chart import mobile_chart, RENDERER_VERSION
from live_quote import show_personal_quote
from live_candle import show_live_candle

PRODUCTION_MODE = bool(globals().get("PRODUCTION_MODE", False))
st.set_page_config(page_title="亞當鏡像分析 V1.0" if PRODUCTION_MODE else "亞當鏡像分析 V1.0 候選版", layout="wide")
from studio_layout import apply_studio_layout
apply_studio_layout(st, production=PRODUCTION_MODE)
st.title("亞當鏡像分析 V1.0" if PRODUCTION_MODE else "亞當鏡像股票分析")
st.caption("A 模式左右鏡像｜短、中、長三波｜歷史路徑情境分析")
if PRODUCTION_MODE:
    st.caption("V1.0.6｜初選個股直接開圖・大小箱型・自動財報")
st.info("鏡像右側為歷史路徑反向排列的情境示意，並非即時行情或未來價格預測；未來日期為示意刻度，未完整排除台股休市日及盤中休市時段。")

MARKETS = {
    "台灣股票／ETF": None,
    "台指期 TX（官方 CSV）": "TAIFEX_TX",
    "那斯達克期貨 NQ（MNQ 參考）": "NQ=F",
    "黃金期貨 GC（MGC 參考）": "GC=F",
    "原油期貨 CL": "CL=F",
    "標普期貨 ES（MES 參考）": "ES=F",
    "比特幣 BTC": "BTC-USD",
    "其他商品（自訂 Yahoo 代碼）": "CUSTOM",
}

INTERVALS = {
    "1分K": "1m",
    "5分K": "5m",
    "10分K": "10m",
    "15分K": "15m",
    "30分K": "30m",
    "60分K": "60m",
    "日K": "1d",
    "週K": "1wk",
    "月K": "1mo",
}

PERIODS = {
    "1m": ["1d", "5d", "7d"],
    "10m": ["5d", "1mo", "60d"],
    "30m": ["5d", "1mo", "60d"],
    "5m": ["5d", "1mo", "60d"],
    "15m": ["5d", "1mo", "60d"],
    "60m": ["5d", "1mo", "3mo", "6mo", "2y"],
    "1d": ["6mo", "1y", "2y", "5y", "10y"],
    "1wk": ["1y", "2y", "5y", "10y"],
    "1mo": ["2y", "5y", "10y", "max"],
}

WAVES = {
    "短波": (3, 100),
    "中波": (7, 260),
    "長波": (14, 650),
}

COLORS = {
    "短波": "#16a34a",
    "中波": "#ea580c",
    "長波": "#dc2626",
}

ZOOMS = [
    "最近5根",
    "最近10根",
    "最近15根",
    "最近30根",
    "最近60根",
    "最近120根",
    "最近250根",
    "全部歷史與鏡像",
]


def audit_ohlc_data(df):
    """回報行情資料品質；不自行猜測或修補價格。"""
    issues = []
    if df.empty:
        return issues
    if not df.index.is_monotonic_increasing:
        issues.append("時間順序未由舊到新")
    if df.index.has_duplicates:
        issues.append("存在重複時間")
    columns = ("Open", "High", "Low", "Close")
    missing = [col for col in columns if col not in df.columns]
    if missing:
        issues.append("缺少 OHLC 欄位：" + "、".join(missing))
        return issues
    prices = df.loc[:, list(columns)].apply(pd.to_numeric, errors="coerce")
    invalid = ~np.isfinite(prices.to_numpy(dtype=float))
    if invalid.any():
        issues.append(f"存在 {int(invalid.any(axis=1).sum())} 根價格缺漏或非有限數值 K 線")
    nonpositive = (prices <= 0).any(axis=1)
    if nonpositive.any():
        issues.append(f"存在 {int(nonpositive.sum())} 根非正數價格 K 線")
    bad_high = prices["High"] < prices[["Open", "Low", "Close"]].max(axis=1)
    bad_low = prices["Low"] > prices[["Open", "High", "Close"]].min(axis=1)
    if (bad_high | bad_low).any():
        issues.append(f"存在 {int((bad_high | bad_low).sum())} 根高低價關係異常 K 線")
    return issues


def raw_quote_summary(df):
    """下載原始資料的整理前品質摘要；僅作揭露，不修補行情。"""
    if df.empty:
        return []
    notes = []
    if "Close" in df.columns:
        close = pd.to_numeric(df["Close"], errors="coerce")
        missing = int((~np.isfinite(close.to_numpy(dtype=float))).sum())
        if missing:
            notes.append(f"原始資料有 {missing} 根收盤價缺漏或非有限數值")
    duplicates = int(df.index.duplicated(keep="last").sum())
    if duplicates:
        notes.append(f"原始資料有 {duplicates} 筆重複時間，保留最後一筆")
    if not df.index.is_monotonic_increasing:
        notes.append("原始資料時間未排序，已由舊到新整理")
    return notes


@st.cache_data(ttl=900)
def get_data(symbol, period, interval):
    source_interval = "5m" if interval == "10m" else interval
    df = yf.download(
        symbol,
        period=period,
        interval=source_interval,
        auto_adjust=False,
        progress=False,
        threads=False
    )

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    if df.empty:
        return df

    raw_notes = raw_quote_summary(df)
    df = df.dropna(subset=["Close"]).sort_index().copy()
    df.index = pd.to_datetime(df.index)

    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)

    df = df[~df.index.duplicated(keep="last")]
    if interval == "10m":
        # 以每個交易日首根5分K為起點，避免跨日混合。
        # 遇到盤中長時間休市亦重新開始合成。
        gaps = df.index.to_series().diff().gt(pd.Timedelta(minutes=10))
        sessions = (df.index.to_series().dt.normalize().ne(
            df.index.to_series().dt.normalize().shift()) | gaps).cumsum()
        parts = []
        for _, group in df.groupby(sessions):
            bars = group.resample("10min", origin=group.index[0], label="left", closed="left").agg({
                "Open": "first", "High": "max", "Low": "min",
                "Close": "last", "Volume": "sum"
            })
            bars = bars.dropna(subset=["Open", "High", "Low", "Close"])
            parts.append(bars)
        df = pd.concat(parts).sort_index() if parts else df.iloc[0:0]
    df.attrs["raw_quote_notes"] = raw_notes
    return df



@st.cache_data(ttl=1800, show_spinner=False)
def fetch_tx_latest():
    """期交所 OpenAPI 僅提供最近交易日快照，並非歷史查詢 API。"""
    import json
    from urllib.request import Request, urlopen
    url = "https://openapi.taifex.com.tw/v1/DailyMarketReportFut"
    req = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    with urlopen(req, timeout=15) as response:
        rows = json.load(response)
    if not isinstance(rows, list):
        raise ValueError("期交所 API 未回傳行情清單")
    data = pd.DataFrame(rows)
    required = ["Date", "Contract", "ContractMonth(Week)", "TradingSession",
                "Open", "High", "Low", "Last", "Volume"]
    missing = [col for col in required if col not in data.columns]
    if missing:
        raise ValueError("期交所 API 欄位異動：" + ", ".join(missing))
    data = data.loc[data["Contract"].astype(str).str.strip() == "TX"].copy()
    data["月份"] = data["ContractMonth(Week)"].astype(str).str.strip()
    data = data.loc[data["月份"].str.fullmatch(r"20\d{4}")].copy()
    data["日期"] = pd.to_datetime(data["Date"].astype(str), format="%Y%m%d", errors="coerce")
    data["交易時段"] = data["TradingSession"].astype(str).str.strip()
    for src, dst in [("Open", "Open"), ("High", "High"),
                     ("Low", "Low"), ("Last", "Close"), ("Volume", "成交量數字")]:
        data[dst] = pd.to_numeric(data[src].astype(str).str.replace(",", "", regex=False),
                                  errors="coerce")
    data = data.dropna(subset=["日期", "Open", "High", "Low", "Close"])
    if data.empty:
        raise ValueError("最近交易日沒有可用的 TX 行情")
    return data


def tx_latest_bar(session_mode):
    data = fetch_tx_latest()
    regular = data.loc[data["交易時段"] == "一般"].copy()
    if regular.empty:
        raise ValueError("官方 API 尚未提供最近交易日 TX 日盤資料")
    chosen = regular.sort_values(["日期", "成交量數字", "月份"],
                                 ascending=[True, False, True]).drop_duplicates("日期")
    bars = []
    for _, day in chosen.iterrows():
        same = data.loc[(data["日期"] == day["日期"]) &
                        (data["月份"] == day["月份"])].copy()
        if session_mode == "日盤":
            same = same.loc[same["交易時段"] == "一般"]
        if same.empty:
            continue
        night = same.loc[same["交易時段"] == "盤後"]
        last = night.iloc[-1] if not night.empty else day
        bars.append({"Date": day["日期"], "Open": day["Open"],
                     "High": same["High"].max(), "Low": same["Low"].min(),
                     "Close": last["Close"], "月份": day["月份"]})
    if not bars:
        raise ValueError("最近交易日 TX 行情無法合併")
    return pd.DataFrame(bars).set_index("Date").sort_index()


def merge_tx_history(history, latest):
    """相同日期以最新官方資料為準，換月日重新計算。"""
    if history is None or history.empty:
        merged = latest.copy()
    else:
        merged = pd.concat([history, latest]).sort_index()
        merged = merged.loc[~merged.index.duplicated(keep="last")]
    roll = merged["月份"].ne(merged["月份"].shift())
    roll.iloc[0] = False
    return merged, merged.index[roll].tolist()


def load_tx_csv(uploaded_files, session_mode):
    """
    讀取期交所年度期貨 CSV。
    僅保留 TX 單式月合約。
    每日依日盤成交量選擇主力合約。
    """
    import io

    chunks = []

    for uploaded in uploaded_files:
        content = uploaded.getvalue()
        table = None

        for encoding in ("big5", "cp950", "utf-8-sig"):
            try:
                candidate = pd.read_csv(
                    io.BytesIO(content),
                    encoding=encoding,
                    index_col=False,
                    low_memory=False
                )

                required = {
                    "交易日期",
                    "契約",
                    "到期月份(週別)",
                    "交易時段",
                }

                if required.issubset(candidate.columns):
                    table = candidate
                    break

            except (UnicodeDecodeError, UnicodeError):
                continue

        if table is None:
            raise ValueError(
                f"無法讀取 {uploaded.name}；"
                "請上傳期交所年度期貨 CSV。"
            )

        chunks.append(table)

    if not chunks:
        raise ValueError("請先上傳期交所 CSV。")

    data = pd.concat(chunks, ignore_index=True)

    data = data.loc[
        data["契約"].astype(str).str.strip() == "TX"
    ].copy()

    data["月份"] = (
        data["到期月份(週別)"].astype(str).str.strip()
    )

    # 排除價差組合、週契約等非單式月合約
    data = data.loc[
        data["月份"].str.fullmatch(r"20\d{4}")
    ].copy()

    data["日期"] = pd.to_datetime(
        data["交易日期"],
        errors="coerce"
    )

    data["交易時段"] = (
        data["交易時段"].astype(str).str.strip()
    )

    data = data.loc[
        data["交易時段"].isin(["一般", "盤後"])
    ].copy()

    for source, target in [
        ("開盤價", "Open"),
        ("最高價", "High"),
        ("最低價", "Low"),
        ("收盤價", "Close"),
    ]:
        data[target] = pd.to_numeric(
            data[source].astype(str).str.replace(
                ",", "", regex=False
            ),
            errors="coerce"
        )

    data = data.dropna(
        subset=["日期", "Open", "High", "Low", "Close"]
    )

    data["成交量數字"] = pd.to_numeric(
        data["成交量"].astype(str).str.replace(
            ",", "", regex=False
        ),
        errors="coerce"
    ).fillna(0)

    regular = data.loc[
        data["交易時段"] == "一般"
    ].copy()

    if regular.empty:
        raise ValueError("CSV 中沒有 TX 日盤行情。")

    # 依當日日盤成交量選擇主力月份
    chosen = (
        regular.sort_values(
            ["日期", "成交量數字", "月份"],
            ascending=[True, False, True]
        )
        .drop_duplicates("日期", keep="first")[
            ["日期", "月份"]
        ]
    )

    selected = data.merge(
        chosen,
        on=["日期", "月份"],
        how="inner"
    )

    if session_mode == "日盤":
        selected = selected.loc[
            selected["交易時段"] == "一般"
        ].copy()

    bars = []

    for date, group in selected.groupby(
        "日期", sort=True
    ):
        day = group.loc[
            group["交易時段"] == "一般"
        ]

        night = group.loc[
            group["交易時段"] == "盤後"
        ]

        if day.empty:
            continue

        first = day.iloc[0]

        if (
            session_mode == "日盤＋夜盤"
            and not night.empty
        ):
            last = night.iloc[-1]
        else:
            last = first

        bars.append({
            "Date": date,
            "Open": first["Open"],
            "High": group["High"].max(),
            "Low": group["Low"].min(),
            "Close": last["Close"],
            "月份": first["月份"],
        })

    if not bars:
        raise ValueError("沒有可用的 TX 日 K 資料。")

    frame = (
        pd.DataFrame(bars)
        .set_index("Date")
        .sort_index()
    )

    frame = frame.loc[
        ~frame.index.duplicated(keep="last")
    ]

    roll = frame["月份"].ne(
        frame["月份"].shift()
    )

    roll.iloc[0] = False

    roll_dates = frame.index[roll].tolist()

    return frame, roll_dates


def find_pivots(values, span, min_change):
    x = np.asarray(values, dtype=float)

    if len(x) < 2 * span + 3:
        return []

    candidates = []

    for i in range(span, len(x) - span):
        window = x[i-span:i+span+1]

        if x[i] >= np.max(window):
            candidates.append((i, "高"))

        elif x[i] <= np.min(window):
            candidates.append((i, "低"))

    pivots = []

    for i, kind in candidates:
        if not pivots:
            pivots.append((i, kind))
            continue

        j, prev_kind = pivots[-1]

        if kind == prev_kind:
            if (
                (kind == "高" and x[i] >= x[j])
                or
                (kind == "低" and x[i] <= x[j])
            ):
                pivots[-1] = (i, kind)

        elif (
            abs(x[i] - x[j])
            / max(abs(x[j]), 1e-9)
            >= min_change
        ):
            pivots.append((i, kind))

    return pivots


def future_index(last_date, count, interval):
    t = pd.Timestamp(last_date)

    if count <= 0:
        return pd.DatetimeIndex([])

    if interval == "1d":
        return pd.bdate_range(
            t + pd.offsets.BDay(1),
            periods=count
        )

    if interval == "1wk":
        return pd.date_range(
            t + pd.Timedelta(days=7),
            periods=count,
            freq="7D"
        )

    if interval == "1mo":
        return pd.date_range(
            t + pd.offsets.MonthBegin(1),
            periods=count,
            freq="MS"
        )

    delta = {
        "1m": pd.Timedelta(minutes=1),
        "5m": pd.Timedelta(minutes=5),
        "10m": pd.Timedelta(minutes=10),
        "15m": pd.Timedelta(minutes=15),
        "30m": pd.Timedelta(minutes=30),
        "60m": pd.Timedelta(hours=1),
    }[interval]

    return pd.DatetimeIndex([
        t + delta * i
        for i in range(1, count + 1)
    ])


def fmt_time(value, interval):
    if interval in ("1m", "5m", "10m", "15m", "30m", "60m"):
        fmt = "%Y-%m-%d %H:%M"
    else:
        fmt = "%Y-%m-%d"

    return pd.Timestamp(value).strftime(fmt)


def internal_turns(
    prices,
    span,
    threshold,
    limit=3
):
    pivots = find_pivots(
        prices,
        span,
        threshold / 100.0
    )

    return [
        (i, kind)
        for i, kind in pivots
        if 0 < i < len(prices) - 1
    ][:limit]


def mirror_wave(df, name, threshold, interval):
    span, lookback = WAVES[name]

    recent = df.tail(lookback)
    close = recent["Close"].to_numpy(dtype=float)

    pivots = find_pivots(
        close,
        span,
        threshold / 100.0
    )

    if len(pivots) < 2:
        return None

    start = pivots[-2][0]
    end = pivots[-1][0]

    segment = close[start:end+1]

    if len(segment) < 2:
        return None

    # A 模式：左右翻轉時間順序，不上下翻轉
    reversed_segment = segment[::-1]

    latest = float(df["Close"].iloc[-1])

    projection = (
        latest
        + reversed_segment
        - reversed_segment[0]
    )

    times = pd.DatetimeIndex(
        [df.index[-1]]
    ).append(
        future_index(
            df.index[-1],
            len(projection)-1,
            interval
        )
    )

    return {
        "name": name,
        "color": COLORS[name],
        "recent": recent,
        "start": start,
        "end": end,
        "segment": segment,
        "times": times,
        "projection": projection,
        "high_i": int(np.argmax(projection)),
        "low_i": int(np.argmin(projection)),
        "turns": internal_turns(
            projection,
            max(1, min(span, 4)),
            threshold
        ),
        "latest": latest,
    }


def wave_source_rows(waves, interval):
    """建立鏡像來源摘要，辨識不同波段共用同一歷史區間。"""
    rows = []
    seen = {}
    for wave in waves:
        recent = wave["recent"]
        start = int(wave["start"])
        end = int(wave["end"])
        start_date = fmt_time(recent.index[start], interval)
        end_date = fmt_time(recent.index[end], interval)
        key = (pd.Timestamp(recent.index[start]), pd.Timestamp(recent.index[end]))
        same_as = "、".join(seen.get(key, [])) or "無"
        seen.setdefault(key, []).append(wave["name"])
        rows.append({
            "波段": wave["name"],
            "歷史起日": start_date,
            "歷史迄日": end_date,
            "歷史起價": round(float(wave["segment"][0]), 2),
            "歷史迄價": round(float(wave["segment"][-1]), 2),
            "鏡像終點": round(float(wave["projection"][-1]), 2),
            "與其他波段相同來源": same_as,
        })
    return rows


def projection_warnings(waves):
    """Disclose non-tradable scenario prices without changing mirror math."""
    warnings = []
    for wave in waves:
        prices = np.asarray(wave["projection"], dtype=float)
        if not np.isfinite(prices).all():
            warnings.append(f"{wave['name']}鏡像包含非有限數值，請勿作為價格參考。")
        finite = prices[np.isfinite(prices)]
        if len(finite) and (finite <= 0).any():
            warnings.append(
                f"{wave['name']}鏡像包含零或負數價位（最低 {float(finite.min()):,.2f}）。"
                "這是歷史價差平移的數學情境，不是可交易的股價或目標價；原始鏡像數值未裁切。"
            )
    return warnings


def make_figure(
    df,
    waves,
    chart_type,
    zoom,
    title,
    show_bollinger=False,
    boll_period=20,
    boll_std=2.0,
    chart_theme="券商深色"
):
    # 只減少瀏覽器繪製的歷史 K 棒，鏡像仍依完整資料計算。
    if zoom == "全部歷史與鏡像":
        plot_df = df
    else:
        try:
            visible_count = int(zoom.replace("最近", "").replace("根", ""))
        except (ValueError, AttributeError):
            visible_count = 120
        plot_df = df.tail(max(visible_count, 300) + 20)

    fig = go.Figure()
    dark = chart_theme == "券商深色"

    if chart_type == "K線":
        fig.add_trace(go.Candlestick(
            x=plot_df.index,
            open=plot_df["Open"],
            high=plot_df["High"],
            low=plot_df["Low"],
            close=plot_df["Close"],
            name="歷史K線",
            increasing=dict(line=dict(color="#ff2020"), fillcolor="#ff2020") if dark else dict(),
            decreasing=dict(line=dict(color="#00e000"), fillcolor="#00e000") if dark else dict()
        ))
    else:
        fig.add_trace(go.Scatter(
            x=plot_df.index,
            y=plot_df["Close"],
            mode="lines",
            name="歷史收盤線",
            line=dict(
                color="#64748b",
                width=2
            )
        ))

    # 布林軌道僅使用實際歷史收盤價，不將鏡像預測納入計算。
    boll_values = None
    if show_bollinger and len(df) >= boll_period:
        middle = df["Close"].rolling(window=boll_period, min_periods=boll_period).mean()
        deviation = df["Close"].rolling(window=boll_period, min_periods=boll_period).std(ddof=0)
        upper = middle + boll_std * deviation
        lower = middle - boll_std * deviation
        boll_values = (upper, middle, lower)
        for label, series, color, dash in [
            ("布林上軌", upper, "#ffff00" if dark else "#d97706", "solid"),
            ("布林中軌", middle, "#00d9f5" if dark else "#2563eb", "solid" if dark else "dash"),
            ("布林下軌", lower, "#d000ff" if dark else "#9333ea", "solid")
        ]:
            fig.add_trace(go.Scatter(
                x=plot_df.index, y=series.reindex(plot_df.index),
                mode="lines", name=label,
                line=dict(color=color, width=1.8, dash=dash),
                hovertemplate="%{y:,.2f}<extra>" + label + "</extra>"
            ))

    for w in waves:
        r = w["recent"]
        s = w["start"]
        e = w["end"]

        fig.add_trace(go.Scatter(
            x=r.index[s:e+1],
            y=w["segment"],
            mode="lines",
            name=f"{w['name']}歷史完整波段",
            line=dict(
                color=w["color"],
                width=2
            ),
            opacity=0.65
        ))

        if w.get("previous_mirror"):
            old = w["previous_mirror"]
            fig.add_trace(go.Scatter(
                x=old["times"], y=old["projection"],
                mode="lines", name=f"{w['name']}上一版鏡像",
                line=dict(color=w["color"], width=1.5, dash="dot"),
                opacity=0.42
            ))

        fig.add_trace(go.Scatter(
            x=w["times"],
            y=w["projection"],
            mode="lines",
            name=f"{w['name']}完整左右鏡像",
            line=dict(
                color=w["color"],
                width=3,
                dash="dash"
            )
        ))

        for number, (i, kind) in enumerate(
            w["turns"],
            start=1
        ):
            fig.add_trace(go.Scatter(
                x=[w["times"][i]],
                y=[float(w["projection"][i])],
                mode="markers",
                text=[
                    f"{w['name']}轉{number} "
                    f"{kind} "
                    f"{w['projection'][i]:,.2f}"
                ],
                marker=dict(
                    color=w["color"],
                    size=9
                ),
                showlegend=False,
                hovertemplate="%{text}<extra></extra>"
            ))

    # 日K 保留連續日期軸，避免 Plotly rangebreaks 導致布林軌道斷線。
    # 後續可改用交易日序號軸，同時實現無空白與連續曲線。
    # 台股分K：移除非交易時段與週末，避免手機圖表出現大片空白。
    # 僅套用在符合台股日盤時間的資料，避免影響美股期貨與 BTC。
    is_intraday = (
        len(df) > 1
        and pd.Timestamp(df.index[-1]).normalize() != pd.Timestamp(df.index[0]).normalize()
        and (df.index.to_series().diff().dropna().median() < pd.Timedelta(hours=8))
    )
    if is_intraday:
        market_hours = df.index.hour * 60 + df.index.minute
        day_session_ratio = ((market_hours >= 9 * 60) & (market_hours <= 13 * 60 + 35)).mean()
        if day_session_ratio > 0.95:
            fig.update_xaxes(rangebreaks=[
                dict(bounds=["sat", "mon"]),
                dict(bounds=[13.6, 9], pattern="hour")
            ])

    fig.update_layout(
        template="plotly_dark" if dark else "plotly_white",
        paper_bgcolor="#101010" if dark else "#ffffff",
        plot_bgcolor="#101010" if dark else "#ffffff",
        font=dict(color="#eeeeee" if dark else "#252a34"),
        title=dict(text=title, font=dict(color="#ffffff" if dark else "#252a34", size=17)),
        modebar=dict(bgcolor="rgba(16,16,16,0.95)" if dark else "rgba(255,255,255,0.9)", color="#f5f5f5" if dark else "#52525b", activecolor="#38bdf8" if dark else "#2563eb"),
        height=700,
        hovermode="x unified",
        dragmode="pan",
        xaxis_rangeslider_visible=False,
        xaxis_title="日期／時間",
        yaxis_title="價格",
        legend=dict(
            orientation="h",
            x=0,
            xanchor="left",
            y=-0.22,
            yanchor="top",
            font=dict(size=12, color="#f5f5f5" if dark else "#252a34"),
            bgcolor="rgba(16,16,16,0)" if dark else "rgba(255,255,255,0)"
        ),
        margin=dict(
            l=35,
            r=35,
            t=85,
            b=135
        )
    )

    fig.update_xaxes(gridcolor="#353535" if dark else "#e5e7eb", tickfont=dict(color="#e5e7eb" if dark else "#52525b"), title_font=dict(color="#e5e7eb" if dark else "#52525b"))
    fig.update_yaxes(gridcolor="#353535" if dark else "#e5e7eb", tickfont=dict(color="#e5e7eb" if dark else "#52525b"), title_font=dict(color="#e5e7eb" if dark else "#52525b"))

    if zoom != "全部歷史與鏡像":
        n = int(
            zoom.replace("最近", "").replace("根", "")
        )

        left = df.index[
            max(0, len(df)-n)
        ]

        # 手機初始視窗保留少量未來K棒，完整鏡像仍可拖曳查看。
        future_bars = min(5, max(1, n // 4))
        right = max(
            [df.index[-1]]
            +
            [
                w["times"][
                    min(future_bars, len(w["times"])-1)
                ]
                for w in waves
            ]
        )

        fig.update_xaxes(
            range=[left, right]
        )

        visible = df.loc[
            df.index >= left
        ]

        values = []

        if not visible.empty:
            values.extend([
                float(visible["Low"].min()),
                float(visible["High"].max())
            ])

        for w in waves:
            for t, price in zip(
                w["times"],
                w["projection"]
            ):
                if (
                    left <= t <= right
                    and np.isfinite(price)
                ):
                    values.append(float(price))

        if boll_values is not None:
            for series in (boll_values[0], boll_values[2]):
                shown = series.loc[(series.index >= left) & (series.index <= df.index[-1])].dropna()
                if not shown.empty:
                    values.extend([float(shown.min()), float(shown.max())])

        if values:
            lo = min(values)
            hi = max(values)

            pad = max(
                (hi-lo)*0.08,
                abs(hi)*0.005,
                0.01
            )

            fig.update_yaxes(
                range=[lo-pad, hi+pad]
            )

    return fig



# ===== 台股中文名稱查詢（官方公開資料；失敗時保留代號輸入）=====
@st.cache_data(ttl=86400, show_spinner=False)
def load_tw_symbols():
    import json
    from urllib.request import Request, urlopen

    sources = [
        ("上市", "https://openapi.twse.com.tw/v1/opendata/t187ap03_L", "公司代號", "公司名稱"),
        ("上櫃", "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O", "公司代號", "公司名稱"),
        ("上市", "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL", "Code", "Name"),
        ("上櫃", "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes", "SecuritiesCompanyCode", "CompanyName"),
    ]
    found = {}
    for exchange_name, url, code_key, name_key in sources:
        try:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
            with urlopen(req, timeout=8) as resp:
                rows = json.load(resp)
            if not isinstance(rows, list):
                continue
            for row in rows:
                code = str(row.get(code_key, "")).strip()
                name = str(row.get(name_key, "")).strip()
                if code.isdigit() and 4 <= len(code) <= 6 and name:
                    found[(code, exchange_name)] = name
        except Exception:
            continue
    # 常用股票備援，官方來源暫時無法存取時仍可搜尋
    backup = {
        "2330": ("台積電", "上市"), "2308": ("台達電", "上市"),
        "2317": ("鴻海", "上市"), "2454": ("聯發科", "上市"),
        "2618": ("長榮航", "上市"), "3481": ("群創", "上市"),
        "00878": ("國泰永續高股息", "上市"),
    }
    for code, (name, exchange_name) in backup.items():
        found.setdefault((code, exchange_name), name)
    return [(code, name, exchange_name) for (code, exchange_name), name in sorted(found.items())]


# ===== 操作介面 =====
from initial_navigation import consume_initial, back_to_initial, scroll_chart_top
initial_request=consume_initial(st.session_state)
initial_chart=bool(st.session_state.get("initial_chart_open"))
if initial_chart:
    st.button("← 返回初選股票",key="initial_chart_back",on_click=back_to_initial)
chart_heading_slot=st.empty()
if initial_chart:
    st.markdown('<style>.st-key-initial_results_panel{display:none}</style>',unsafe_allow_html=True)
if st.session_state.get("initial_chart_jump"):
    scroll_chart_top(st.session_state.pop("initial_chart_jump"))
with st.container(key="initial_results_panel"):
    if not PRODUCTION_MODE:
        from entry_alerts_ui import show_entry_alerts
        show_entry_alerts(load_tw_symbols())
    
    if PRODUCTION_MODE:
        st.subheader("尋找股票")
        st.caption("全台股選股與自選名單在這裡；查詢單一股票，請展開左上角側欄輸入代號或中文名稱。")
    from full_market_ui import show_full_market
    show_full_market(production=PRODUCTION_MODE)
    
    from screener_ui import show_screener
    show_screener(load_tw_symbols(), production=PRODUCTION_MODE)

if "adam_stock_query" not in st.session_state:
    st.session_state["adam_stock_query"] = "2308"

from contextlib import nullcontext
with st.sidebar:
    market = st.selectbox(
        "選擇市場",
        ["台灣股票／ETF"] if PRODUCTION_MODE else list(MARKETS)
    )

    if MARKETS[market] is None:
        query = st.text_input(
            "股票代號或中文名稱（例如：2330、台積電、台達電）",
            key="adam_stock_query"
        ).strip()
        stock_list = load_tw_symbols()
        matches = [
            (code, name, ex) for code, name, ex in stock_list
            if query and (query.lower() in code.lower() or query.lower() in name.lower())
        ]
        if matches:
            choices = matches[:100]
            labels = [f"{code} {name}（{ex}）" for code, name, ex in choices]
            requested=st.session_state.get("initial_chart_context",{}).get("symbol","")
            chosen_index=next((i for i,r in enumerate(choices)
                               if r[0]+(".TW" if r[2]=="上市" else ".TWO")==requested),0)
            chosen = st.selectbox("選擇股票／ETF", range(len(choices)),index=chosen_index,
                                  format_func=lambda i: labels[i])
            code, stock_name, exchange = choices[chosen]
            symbol = code + (".TW" if exchange == "上市" else ".TWO")
            st.caption(f"目前選擇：{code} {stock_name}｜{exchange}")
        elif query.isdigit():
            exchange = st.radio("查無名稱對照，請選擇交易市場", ["上市", "上櫃"],
                                index=1 if st.session_state.get("initial_chart_context",{}).get("symbol")==query+".TWO" else 0,
                                horizontal=True)
            symbol = query + (".TW" if exchange == "上市" else ".TWO")
            st.caption("目前使用股票代號查詢；中文名稱資料可能暫時無法取得。")
        else:
            symbol = ""
            if query:
                st.warning("找不到符合的中文股票名稱。請輸入完整名稱或股票代號。")

    elif MARKETS[market] == "TAIFEX_TX":
        symbol = "TX（官方期交所 CSV）"

        tx_source = st.radio(
            "台指期資料來源",
            ["官方 API 自動取得最新交易日", "官方 CSV 歷史資料"],
            horizontal=True
        )
        tx_files = st.file_uploader(
            "選用：上傳期交所年度 CSV 補足歷史（可多選）",
            type=["csv"],
            accept_multiple_files=True
        )

        tx_session = st.radio(
            "台指期交易時段",
            ["日盤", "日盤＋夜盤"],
            horizontal=True
        )

        st.caption(
            "官方 API 自動讀取最近交易日，並非即時報價；"
            "如需長期短中長波分析，請上傳歷史 CSV 補齊。"
            "依日盤成交量選主力月；夜盤依官方交易日期合併。"
        )

    elif MARKETS[market] == "CUSTOM":
        symbol = st.text_input(
            "Yahoo Finance 商品代碼",
            ""
        ).strip().upper()

    else:
        symbol = MARKETS[market]



    if initial_chart and symbol:
        context=st.session_state.get("initial_chart_context",{})
        if context and symbol.split(".")[0]==context["symbol"].split(".")[0]:
            symbol=context["symbol"]
        with chart_heading_slot.container():
            st.subheader("個股線圖｜"+symbol)
            if context:
                st.caption(f'{context["name"]}｜初選行情日期：{context["date"]}；本頁依所選期間重新讀取歷史行情。')
                st.info("這是初選個股，尚未驗證20日均量與箱型；開圖不代表符合進場條件。")

    c1, c2 = st.columns(2)

    with c1:
        if PRODUCTION_MODE:
            interval_name = st.selectbox("K線週期", ["日K", "週K"])
        elif market == "台指期 TX（官方 CSV）":
            interval_name = st.selectbox(
                "K線週期",
                ["日K"]
            )
        else:
            interval_name = st.selectbox(
                "K線週期",
                list(INTERVALS),
                index=6
            )

    with c2:
        interval = INTERVALS[interval_name]

        if market == "台指期 TX（官方 CSV）":
            period = st.selectbox(
                "歷史資料長度",
                ["上傳檔案全部日期"]
            )
        else:
            options = PERIODS[interval]

            period = st.selectbox(
                "歷史資料長度",
                options,
                index=len(options)-1
            )


    if not PRODUCTION_MODE:
        from wave_settings import show_wave_settings
        WAVES = show_wave_settings(interval)

    mode = st.radio(
        "顯示模式",
        [
            "三波同圖",
            "單一波段",
            "三波各自獨立放大"
        ],
        horizontal=True
    )

    selected = st.radio(
        "單一波段選擇",
        list(WAVES),
        horizontal=True,
        disabled=(mode != "單一波段")
    )

    chart_type = st.radio(
        "圖表模式",
        ["K線"] if PRODUCTION_MODE else ["K線", "線圖"],
        horizontal=True
    )

    mobile_engine = True if PRODUCTION_MODE else st.checkbox("測試手機雙指縮放圖表（新版）", value=True, key="b3_mobile_engine_box1125", help="測試版預設開啟；取消勾選可回原本 Plotly 圖表。")

    chart_theme = st.radio(
        "圖表配色",
        ["券商深色", "原本淺色"],
        horizontal=True
    )

    show_bollinger = st.checkbox("顯示布林軌道（BOLL）", value=True)
    ma_periods = [] if PRODUCTION_MODE else st.multiselect("測試 MA 均線（可複選）", [5,10,20,60,120,240], default=[])
    ema_periods = [] if PRODUCTION_MODE else st.multiselect("測試 EMA 均線（可複選）", [5,10,20,60,120,240], default=[])
    st.caption(("正式版本 V1.0｜圖表：" if PRODUCTION_MODE else "候選版本 V1.0｜圖表：") + (RENDERER_VERSION if mobile_engine else "Plotly")
               + "｜箱型不顯示價格標籤")

    auto_boxes = st.checkbox("自動箱型（箱頂／箱底／中線）" if PRODUCTION_MODE else "測試自動箱型（箱頂／箱底／中線）", value=True, key="b3_box_default_on_10_20")
    box_window = st.slider("箱型觀察根數", 10, 60, 10, disabled=not auto_boxes, key="b3_box_window_default_10")
    box_width = st.slider("箱型最大振幅（%）", 3.0, 25.0, 20.0, 0.5, disabled=not auto_boxes, key="b3_box_width_default_20")
    large_box_window = st.selectbox("大區間箱型觀察根數（同一K線週期）",
                                   [n for n in [60, 120, 250] if n > box_window],
                                   disabled=not auto_boxes, key="large_box_window")
    box_history = st.checkbox("顯示歷史箱型（已突破淡色虛線）", value=False,
                              disabled=not auto_boxes, key="box_history")
    box_options = dict(short_window=box_window, large_window=large_box_window,
                       max_width_pct=box_width, history=box_history)
    st.caption("圖上預設只保留目前整理箱型：青色小區間、橙色大區間。大小以K棒根數區分。")

    boll_period = st.number_input("布林均線週期", min_value=5, max_value=120, value=20, step=1, disabled=not show_bollinger)
    boll_std = st.number_input("標準差倍數", min_value=0.5, max_value=4.0, value=2.0, step=0.5, disabled=not show_bollinger)

    threshold = st.slider(
        "最小反轉幅度（%）",
        1, 20, 3
    )

    zoom = st.selectbox(
        "三波同圖／單波初始放大範圍",
        ZOOMS,
        index=4
    )

    individual_zoom = {
        "短波": "最近30根",
        "中波": "最近60根",
        "長波": "最近60根"
    }

    if mode == "三波各自獨立放大":
        z1, z2, z3 = st.columns(3)

        with z1:
            individual_zoom["短波"] = st.selectbox(
                "短波放大",
                ZOOMS,
                index=3
            )

        with z2:
            individual_zoom["中波"] = st.selectbox(
                "中波放大",
                ZOOMS,
                index=4
            )

        with z3:
            individual_zoom["長波"] = st.selectbox(
                "長波放大",
                ZOOMS,
                index=4
            )

    show_personal_quote(market, symbol, production=PRODUCTION_MODE)

    st.info(
        "未來鏡像保留全部 K 棒；"
        "初始畫面只顯示所選根數。"
    )


    # ===== 開始分析 =====

    @st.cache_data(ttl=21600, show_spinner=False)
    def fetch_auto_eps(ticker_symbol):
        """Yahoo trailingEps is historical TTM, not an analyst forecast."""
        try:
            info = yf.Ticker(ticker_symbol).info
            value = pd.to_numeric(info.get("trailingEps"), errors="coerce")
            if pd.notna(value) and float(value) > 0:
                return float(value), "Yahoo Finance trailingEps（近四季歷史 EPS）"
        except Exception:
            pass
        return None, "Yahoo Finance 無有效 EPS"

    # 估價：自動 EPS 或手動輸入，倍數為可調示例。
    valuation_enabled = False
    if not PRODUCTION_MODE:
        with st.expander("🧮 便宜價／合理價／昂貴價估算（測試版）", expanded=False):
            valuation_enabled = st.checkbox("啟用估價", value=False, key="b3_valuation_enabled_v1")
            valuation_mode = st.radio("估價模式", ["參考價值投資分區（可調參數）", "自訂本益比"], horizontal=True, key="b3_valuation_mode_v1")
            eps_source_mode = st.radio("EPS 取得方式", ["自動抓取近四季 EPS", "手動輸入 EPS"], horizontal=True, key="b3_eps_source_v2")
            if eps_source_mode == "自動抓取近四季 EPS":
                if valuation_enabled and market == "台灣股票／ETF" and symbol:
                    eps_value, eps_period = fetch_auto_eps(symbol)
                    if eps_value is None:
                        eps_value = 0.0
                        st.warning("目前抓不到有效的近四季 EPS，請切換手動輸入。")
                    else:
                        st.success(f"已取得近四季 EPS：{eps_value:,.2f} 元｜來源：{eps_period}")
                else:
                    eps_value, eps_period = 0.0, "不支援此商品自動 EPS"
                    if valuation_enabled:
                        st.info("此商品不支援自動 EPS，請改選手動輸入。")
            else:
                eps_value = st.number_input("年度 EPS（元）", min_value=0.0, value=0.0, step=0.5, key="b3_eps_manual_v2")
                eps_period = st.text_input("EPS 年度／資料依據", value="", placeholder="例如：2027 年預估／公司法說", key="b3_eps_period_manual_v2")
            if valuation_enabled and market == "台灣股票／ETF":
                st.markdown("##### 🏛️ 證交所官方最新 EPS（資料核對）")
                if st.button("查詢證交所最新財報 EPS", key="b3_twse_eps_check_v1"):
                    from twse_eps import fetch_twse_latest_eps
                    with st.spinner("查詢證交所官方財報中…"):
                        official_eps, official_error = fetch_twse_latest_eps(symbol)
                    if official_eps:
                        st.success(f"官方欄位：{official_eps['field']}｜EPS：{official_eps['eps']:.2f} 元")
                        st.caption(f"來源：{official_eps['source']}｜期間資訊：{official_eps['period']}")
                        st.warning(official_eps["note"])
                    else:
                        st.warning(official_error)
                st.caption("這是官方最新財報查詢，不是完整歷史 EPS；尚未取得逐季公告日，不會把這筆資料混入歷史 PE 或直接當成 TTM。")
            st.caption("🧩 MOPS 診斷版本：2026-11-05 v2｜多欄 EPS 候選值")
            with st.expander("🧪 MOPS 歷史季報連線測試（不納入估價）", expanded=False):
                st.caption("先測試單一季度的歷史財報讀取。由於尚未核對原始申報日期與欄位，任何抓到的 EPS 都不會進入歷史 PE。")
                test_year = st.number_input("測試西元年度", min_value=2018, max_value=2026, value=2024, step=1, key="b3_mops_year_v1")
                test_quarter = st.selectbox("測試季度", [1,2,3,4], index=2, key="b3_mops_quarter_v1")
                if st.button("測試讀取 MOPS 歷史季報", key="b3_mops_probe_v1"):
                    import importlib
                    import mops_history
                    importlib.invalidate_caches()
                    mops_history = importlib.reload(mops_history)
                    st.caption(f"實際解析模組：{getattr(mops_history, '__file__', '未知')}｜多欄解析：{'eps_row_count' in mops_history.fetch_mops_quarter.__code__.co_consts.__str__()}")
                    with st.spinner("讀取官方歷史季報…"):
                        result, error = mops_history.fetch_mops_quarter(symbol, int(test_year), int(test_quarter))
                    if result:
                        st.write(f"季度末：{result['quarter_end']}｜找到 {result['eps_row_count']} 列基本 EPS 候選資料")
                        eps_diagnostic_rows = [
                            {"表格": item["table"], "列": item["row"],
                             "欄": value["column"], "欄位名稱": item["label"],
                             "EPS 候選數值": value["value"]}
                            for item in result["eps_rows"] for value in item["values"]
                        ]
                        st.dataframe(pd.DataFrame(eps_diagnostic_rows), use_container_width=True, hide_index=True)
                        if result.get("column_verified"):
                            verified_eps = result["verified_eps"]
                            st.success(f"已核對財報表頭｜本季基本 EPS：{verified_eps['quarter_eps']:.2f} 元｜年初至今累計基本 EPS：{verified_eps['cumulative_eps']:.2f} 元")
                            st.caption("已核對期間欄位，但尚未核對實際申報日期；不納入歷史估價。")
                        else:
                            st.warning("未能唯一核對本季及累計 EPS 欄位；保留候選數值，不納入估價。")
                        with st.expander("🔎 EPS 數值與原始表頭逐欄對照（除錯）", expanded=True):
                            diagnostic_rows = result.get("eps_header_diagnostics", [])
                            if diagnostic_rows:
                                st.dataframe(pd.DataFrame([
                                    {"表格": x["table"], "欄": x["column"], "EPS": x["value"],
                                     "完整表頭": " / ".join(x["header_levels"]),
                                     "包含金額": x["contains_amount"],
                                     "包含百分比": x["contains_percent"]}
                                    for x in diagnostic_rows
                                ]), use_container_width=True, hide_index=True)
                            else:
                                st.info("目前沒有可供對照的表頭資料。")
                        with st.expander("查看 MOPS 原始表頭（辨識本季／累計欄位）", expanded=False):
                            for table_no, header in result.get("headers", {}).items():
                                st.write(f"原始表格 {table_no}｜欄名：", header["columns"])
                                st.dataframe(pd.DataFrame(header["top_rows"]), use_container_width=True, hide_index=True)
                        st.caption("本階段只展示原始表頭，未經確認不會自動指定累計 EPS 或計算估價。")
                        st.warning("這些數字可能包含本期、去年同期及累計 EPS；尚未核對表頭及公告日，不會納入估價。")
                    else:
                        st.warning(error)
            with st.expander("📚 MOPS 近五年 EPS 與 TTM 自動整理（測試版）", expanded=False):
                st.caption("依序讀取最多 20 季官方財報；首次可能需要較長時間。只顯示可核對期間欄位的 EPS，尚未取得實際公告日，絕不混入歷史 PE。官方連線若失敗，可能顯示缺漏。")
                history_years = st.selectbox("抓取年數", [1, 2, 3, 4, 5], index=4, key="b3_mops_history_years")
                @st.cache_data(ttl=86400, show_spinner=False)
                def cached_mops_quarter_success(stock_symbol, year, quarter, parser_version="annual-header-v4"):
                    from mops_history import fetch_mops_quarter
                    import time
                    last_error = None
                    for attempt in range(3):
                        result, error = fetch_mops_quarter(stock_symbol, year, quarter, timeout=12)
                        if not error and result and result.get("column_verified"):
                            return result, None
                        last_error = error or "EPS 欄位無法唯一核對"
                        if last_error != "MOPS 歷史財報服務無法讀取或格式已變更":
                            break
                        if attempt < 2:
                            time.sleep(1.5 * (attempt + 1))
                    # Do not cache transient failures as if they were valid financial data.
                    raise RuntimeError(last_error or "官方資料讀取失敗")
                def cached_mops_quarter(stock_symbol, year, quarter):
                    try:
                        return cached_mops_quarter_success(stock_symbol, year, quarter)
                    except RuntimeError as exc:
                        return None, str(exc)
                    except Exception:
                        return None, "MOPS 讀取暫時失敗，可稍後重試"
                if st.button("自動抓取官方歷史 EPS", key="b3_mops_history_fetch"):
                    from mops_history import fetch_mops_eps_history
                    progress_bar = st.progress(0, text="準備讀取官方季度財報…")
                    def report_progress(completed, total, quarter):
                        progress_bar.progress(completed / total, text=f"已查詢 {completed}/{total} 季｜{quarter}")
                    with st.spinner("逐季核對 MOPS 財報；已讀取季度會保留快取…"):
                        try:
                            history_rows, history_failures = fetch_mops_eps_history(
                                symbol, years=int(history_years),
                                fetcher=cached_mops_quarter, progress=report_progress)
                            st.session_state["b3_mops_history_result"] = (symbol, history_years, history_rows, history_failures)
                        except Exception as exc:
                            st.error(f"歷史資料讀取失敗：{type(exc).__name__}")
                saved_history = st.session_state.get("b3_mops_history_result")
                if saved_history and saved_history[0] == symbol and saved_history[1] == history_years:
                    _, _, history_rows, history_failures = saved_history
                    st.write(f"已核對 {len(history_rows)} 季；缺漏或異常 {len(history_failures)} 筆")
                    if history_rows:
                        history_table = pd.DataFrame([{
                            "季度": x["quarter"], "單季 EPS": x["quarter_eps"],
                            "當年累計 EPS": x["cumulative_eps"], "TTM EPS": x["ttm_eps"],
                            "累計核對": "通過" if x["ytd_consistent"] is True else ("待核" if x["ytd_consistent"] is None else "異常"),
                            "TTM 狀態": x["ttm_status"],
                            "公告日期": "尚未核實"
                        } for x in history_rows])
                        st.dataframe(history_table, use_container_width=True, hide_index=True)
                        st.download_button("下載 EPS 檢查結果 CSV", history_table.to_csv(index=False).encode("utf-8-sig"),
                                           file_name=f"{str(symbol).split('.')[0]}_mops_eps_review.csv",
                                           mime="text/csv", key="b3_mops_history_csv")
                        st.warning("TTM 為四個連續且欄位已核對的季度 EPS 加總，僅供核對；財報公告日尚未確認，不能用於歷史估價。")
                        with st.expander("📅 下一階段：官方公告日逐季核實", expanded=False):
                            st.caption("證交所財務報告書資訊揭露頁可查公告日期時間；法定截止日、董事會預定日與財報期間結束日，都不能當成實際公告日。")
                            st.markdown("[開啟證交所資訊揭露／財務報告書](https://www.twse.com.tw/IIH2/zh/market/information.html)")
                            st.info("目前尚未取得可逐季對應、可驗證來源的 20 筆公告日期，歷史 PE 回測維持鎖定。")
                            with st.expander("🔬 MOPS 財報公告接口診斷（不會改動估價）", expanded=False):
                                st.caption("以最新已取得的季度為測試目標，僅檢查官方介接是否回傳可解析的表格；不會把財報期間當作公告日。")
                                st.markdown("[官方公開資訊觀測站－財務報告公告](https://mops.twse.com.tw/mops/#/web/t163sb01)")
                                if st.button("交叉測試 2026Q3／2025Q4／2024Q4", key="b3_mops_cross_quarter"):
                                    from official_filing_candidates import compare_filing_quarters
                                    with st.spinner("正在逐季比較官方查詢回應（最多三次查詢）…"):
                                        st.session_state["b3_mops_cross_quarter_result"] = (
                                            str(symbol).split(".")[0],
                                            compare_filing_quarters(str(symbol).split(".")[0])
                                        )
                                cross_saved = st.session_state.get("b3_mops_cross_quarter_result")
                                if cross_saved and cross_saved[0] == str(symbol).split(".")[0]:
                                    cross_result = cross_saved[1]
                                    cross_df = pd.DataFrame(cross_result["rows"])
                                    priority_cols = ["季度", "符合條件候選表格數", "表格判讀",
                                                     "包含股票代號", "包含表格", "查詢狀態"]
                                    ordered_cols = [c for c in priority_cols if c in cross_df.columns]
                                    ordered_cols += [c for c in cross_df.columns if c not in ordered_cols]
                                    st.dataframe(cross_df[ordered_cols], hide_index=True, use_container_width=True)
                                    for _, cross_row in cross_df.iterrows():
                                        status = cross_row.get("表格判讀")
                                        count = cross_row.get("符合條件候選表格數")
                                        st.write(f"**{cross_row['季度']}**｜候選表格：{count if pd.notna(count) else '未取得'}｜判讀：{status or '未取得'}")
                                    if "表格判讀" in cross_df and all(
                                        x == "no_matching_filing_table" for x in cross_df["表格判讀"]
                                    ):
                                        st.warning("三個季度都未找到符合條件的公告表格，建議停止使用目前接口。")
                                        stock_code = str(symbol).split(".")[0]
                                        st.markdown(
                                            f"[改查證交所 {stock_code} 單一公司財務報告書資訊揭露]"
                                            f"(https://www.twse.com.tw/IIH2/zh/company/information.html?code={stock_code})"
                                        )
                                    st.write("三季回應完全相同：", cross_result["all_ajax_responses_identical"])
                                    st.info(cross_result["conclusion"])
                                    st.caption("僅比較官方查詢回應；無法因此認定公告日期或解除歷史 PE 鎖定。")
                                if st.button("同一工作階段核對財報公告查詢", key="b3_mops_session_probe"):
                                    from official_filing_candidates import probe_session_backed_filing_query
                                    latest_period = pd.Period(history_rows[-1]["quarter"], freq="Q")
                                    with st.spinner("正在比對官方查詢頁與資料回應…"):
                                        session_result = probe_session_backed_filing_query(
                                            str(symbol).split(".")[0], latest_period.year, latest_period.quarter)
                                    st.session_state["b3_mops_session_probe_result"] = (
                                        str(symbol).split(".")[0], str(latest_period), session_result)
                                session_saved = st.session_state.get("b3_mops_session_probe_result")
                                if session_saved and session_saved[0] == str(symbol).split(".")[0]:
                                    st.write("同工作階段測試季度：", session_saved[1])
                                    st.json(session_saved[2])
                                    st.caption("本項僅比較請求與回應，不能據此認定公告日期。")
                                if st.button("測試新發現的 MOPS 表單提交路徑", key="b3_mops_discovered_form_probe"):
                                    from official_filing_candidates import probe_discovered_mops_form
                                    latest_period = pd.Period(history_rows[-1]["quarter"], freq="Q")
                                    with st.spinner("正在測試表單提交路徑…"):
                                        discovered_result = probe_discovered_mops_form(
                                            str(symbol).split(".")[0], latest_period.year, latest_period.quarter)
                                    st.session_state["b3_mops_discovered_form_result"] = (
                                        str(symbol).split(".")[0], str(latest_period), discovered_result)
                                discovered_saved = st.session_state.get("b3_mops_discovered_form_result")
                                if discovered_saved and discovered_saved[0] == str(symbol).split(".")[0]:
                                    st.write("新路徑測試季度：", discovered_saved[1])
                                    st.json(discovered_saved[2])
                                    st.caption("僅測試表單路徑是否能回傳資料，不會解鎖歷史 PE。")
                                if st.button("檢查 MOPS 財報公告接口", key="b3_mops_announcement_probe"):
                                    import importlib
                                    import official_filing_candidates as filing_module
                                    filing_module = importlib.reload(filing_module)
                                    latest_period = pd.Period(history_rows[-1]["quarter"], freq="Q")
                                    if not hasattr(filing_module, "probe_mops_financial_announcement"):
                                        probe_result = {"status": "module_version_mismatch",
                                                        "message": "部署中的官方公告模組版本不一致；請重新啟動 Streamlit App",
                                                        "module_path": str(getattr(filing_module, "__file__", "unknown"))}
                                    else:
                                        with st.spinner("正在檢查官方接口…"):
                                            probe_result = filing_module.probe_mops_financial_announcement(
                                                str(symbol).split(".")[0], latest_period.year, latest_period.quarter)
                                    st.session_state["b3_mops_announcement_probe_result"] = (
                                        str(symbol).split(".")[0], str(latest_period), probe_result)
                                probe_saved = st.session_state.get("b3_mops_announcement_probe_result")
                                if probe_saved and probe_saved[0] == str(symbol).split(".")[0]:
                                    st.write("測試季度：", probe_saved[1])
                                    probe_data = probe_saved[2]
                                    status = probe_data.get("status", "unknown")
                                    if status == "query_form_only":
                                        st.error("目前取得的是查詢介面，不是台達電的財報公告結果。請勿用此資料計算歷史 PE。")
                                    elif status == "tables_unverified":
                                        st.warning("取得表格，但公告日期尚未核實。")
                                    elif status == "javascript_shell":
                                        st.warning("官方回傳 JavaScript 頁面，尚未取得公告資料。")
                                    if "input_field_names" in probe_data or "form_targets" in probe_data:
                                        st.markdown("**官方查詢表單結構（診斷用途）**")
                                        st.write("欄位名稱：", ", ".join(probe_data.get("input_field_names", [])) or "無")
                                        st.write("提交目標：", probe_data.get("form_targets", []))
                                        st.write("安全查詢預設值：", probe_data.get("safe_form_defaults", {}))
                                        st.caption("RID、SKEY 等可能涉及工作階段的值一律遮蔽；這些欄位不是財報公告日期。")
                                    if probe_data.get("table_profiles"):
                                        profiles = pd.DataFrame(probe_data["table_profiles"])
                                        profiles = profiles.rename(columns={
                                            "index": "表格編號", "rows": "列數", "columns": "欄數",
                                            "has_stock_code": "包含股票代號",
                                            "has_filing_keyword": "財報關鍵字",
                                            "has_date_keyword": "日期關鍵字",
                                            "has_roc_date_pattern": "民國日期格式",
                                            "header_labels": "原始欄名",
                                            "looks_like_result_table": "疑似公告結果",
                                            "likely_ui_table": "疑似查詢介面",
                                        })
                                        st.dataframe(profiles, use_container_width=True, hide_index=True)
                                        st.caption("勾選表示偵測到關鍵字，並不代表公告日已經核實。")
                                        with st.expander("查看原始診斷 JSON"):
                                            st.json(probe_data)
                                    else:
                                        st.json(probe_data)
                                    st.warning("此處僅測試接口與表格結構；尚未驗證公告日，歷史 PE 不會解鎖。")
                            if st.button("自動查詢證交所財報公告候選紀錄", key="b3_official_filing_fetch"):
                                from official_filing_candidates import fetch_official_filing_candidates, review_candidate_coverage
                                with st.spinner("正在檢查證交所單一公司資訊揭露頁…"):
                                    candidates, candidate_error = fetch_official_filing_candidates(str(symbol).split(".")[0])
                                st.session_state["b3_official_filing_candidates"] = (
                                    str(symbol).split(".")[0], candidates, candidate_error)
                            official_saved = st.session_state.get("b3_official_filing_candidates")
                            if official_saved and official_saved[0] == str(symbol).split(".")[0]:
                                from official_filing_candidates import review_candidate_coverage
                                _, candidates, candidate_error = official_saved
                                if candidate_error:
                                    st.warning(candidate_error)
                                if candidates:
                                    st.write(f"找到 {len(candidates)} 筆公告候選紀錄（非已核實公告日）")
                                    st.dataframe(pd.DataFrame(candidates), use_container_width=True, hide_index=True)
                                from official_filing_candidates import summarize_filing_coverage
                                periods_to_check = [x["quarter"] for x in history_rows]
                                summary = summarize_filing_coverage(candidates, periods_to_check)
                                st.write(
                                    f"**公告候選涵蓋率：{summary['quarters_with_candidates']}/{summary['requested_quarters']} 季 "
                                    f"({summary['candidate_coverage_percent']}%)**"
                                )
                                st.caption(
                                    f"缺漏 {summary['quarters_missing_candidates']} 季；"
                                    f"多筆候選 {summary['quarters_with_multiple_candidates']} 季；"
                                    "已核實首次申報日期 0 季（歷史 PE 維持鎖定）。"
                                )
                                if summary["missing_quarters"]:
                                    st.write("**尚無公告候選的季度：**", "、".join(summary["missing_quarters"]))
                                coverage = review_candidate_coverage(candidates, periods_to_check)
                                st.dataframe(pd.DataFrame(coverage), use_container_width=True, hide_index=True)
                                st.caption("缺漏、重複、補正公告都不會自動填入歷史 PE；必須核對首次有效申報與原始紀錄。")
                            filing_template = pd.DataFrame([{
                                "股票代號": str(symbol).split(".")[0],
                                "季度": x["quarter"],
                                "公告日期": "",
                                "官方來源網址": "",
                            } for x in history_rows])
                            st.download_button("下載公告日核對範本 CSV",
                                               filing_template.to_csv(index=False).encode("utf-8-sig"),
                                               file_name=f"{str(symbol).split('.')[0]}_filing_dates_template.csv",
                                               mime="text/csv", key="b3_filing_date_template")
                            filing_upload = st.file_uploader("上傳已核實公告日 CSV（僅作核對，不會自動啟用估價）",
                                                             type=["csv"], key="b3_filing_dates_upload")
                            if filing_upload is not None:
                                try:
                                    date_table = pd.read_csv(filing_upload, dtype=str).fillna("")
                                    required = {"股票代號", "季度", "公告日期", "官方來源網址"}
                                    if not required.issubset(date_table.columns):
                                        st.error("CSV 缺少必要欄位，請使用下載範本。")
                                    else:
                                        from filing_dates import inspect_filing_date
                                        matched = []
                                        valid_periods = {x["quarter"] for x in history_rows}
                                        for _, date_row in date_table.iterrows():
                                            quarter = str(date_row["季度"]).strip()
                                            code = str(date_row["股票代號"]).strip()
                                            date_str = str(date_row["公告日期"]).strip()
                                            source_url = str(date_row["官方來源網址"]).strip()
                                            status = inspect_filing_date(
                                                code, quarter, date_str, source_url,
                                                str(symbol).split(".")[0])
                                            if quarter not in valid_periods:
                                                status = "季度不在目前核對範圍"
                                            matched.append({"季度": quarter, "公告日期": date_str,
                                                            "官方來源網址": source_url, "狀態": status})
                                        st.dataframe(pd.DataFrame(matched), use_container_width=True, hide_index=True)
                                        st.warning("上傳資料僅供逐季人工查證；網址存在不代表已查證，尚不會進入歷史 PE。")
                                except Exception as exc:
                                    st.error(f"公告日 CSV 讀取失敗：{type(exc).__name__}")

                    if history_failures:
                        with st.expander("查看讀取失敗／資料異常季度"):
                            st.dataframe(pd.DataFrame(history_failures), use_container_width=True, hide_index=True)
                            st.caption("精準診斷：選一個失敗季度，檢查 MOPS 原始 EPS 表頭；不會修改任何估價資料。")
                            failed_periods = [x["quarter"] for x in history_failures
                                              if x.get("reason") == "EPS 欄位無法唯一核對"]
                            if failed_periods:
                                inspect_period = st.selectbox("診斷季度", failed_periods,
                                                              key="b3_eps_inspect_period")
                                if st.button("檢查這一季的 EPS 原始表頭", key="b3_eps_inspect_button"):
                                    import json
                                    from mops_history import fetch_mops_quarter
                                    period_to_check = pd.Period(inspect_period, freq="Q")
                                    with st.spinner("正在讀取官方原始表頭…"):
                                        diagnostic, diagnostic_error = fetch_mops_quarter(
                                            symbol, period_to_check.year, period_to_check.quarter, timeout=12)
                                    if diagnostic_error:
                                        st.error(diagnostic_error)
                                    elif diagnostic:
                                        st.write("基本 EPS 資料列：", diagnostic.get("eps_row_count", 0))
                                        st.write("欄位是否唯一核對：", diagnostic.get("column_verified", False))
                                        details = diagnostic.get("eps_header_diagnostics", [])
                                        if details:
                                            st.dataframe(pd.DataFrame([{
                                                "表格": d["table"], "欄位": d["column"],
                                                "EPS": d["value"],
                                                "期間表頭": d["period_text"],
                                                "原始層級": " / ".join(d["header_levels"]),
                                            } for d in details]), use_container_width=True, hide_index=True)
                                        st.download_button(
                                            "下載這季診斷 JSON",
                                            json.dumps({
                                                "quarter": inspect_period,
                                                "eps_rows": diagnostic.get("eps_rows", []),
                                                "eps_header_diagnostics": details,
                                            }, ensure_ascii=False, indent=2).encode("utf-8"),
                                            file_name=f"{str(symbol).split('.')[0]}_{inspect_period}_eps_diagnostic.json",
                                            mime="application/json",
                                            key="b3_eps_diagnostic_download")
            filing_format = st.radio("匯入 EPS 格式", ["單季 EPS", "年初至今累計 EPS（自動換算單季）"], horizontal=True, key="b3_eps_csv_format_v1")
            filing_upload = st.file_uploader("選用：匯入歷史季度 EPS CSV（含實際公告日）", type=["csv"], key="b3_filing_eps_csv_v1", help="單季格式欄位：symbol,quarter_end,announced_on,eps；累計格式欄位：symbol,quarter_end,announced_on,cumulative_eps。兩者都必須提供真實公告日。")
            st.caption("匯入資料僅用於本次試算，須自行核對公開資訊觀測站的公告日期與單季 EPS；尚未自動串接官方歷史財報。")
            auto_pe_result = None
            auto_pe_enabled = st.checkbox("自動歷史本益比分位數（20%／50%／80%）", value=True, key="b3_auto_pe_v3")
            if valuation_enabled and auto_pe_enabled and eps_value > 0 and market == "台灣股票／ETF":
                try:
                    if filing_upload is not None:
                        from filing_eps import parse_quarterly_eps_csv, parse_cumulative_eps_csv, historical_pe_from_filings
                        parser = parse_cumulative_eps_csv if filing_format.startswith("年初") else parse_quarterly_eps_csv
                        filing_data, pe_error = parser(filing_upload.getvalue(), symbol)
                        if filing_data is not None:
                            auto_pe_result, pe_error = historical_pe_from_filings(symbol, filing_data, years=3)
                    else:
                        if str(symbol).endswith(".TW"):
                            from twse_pe import official_twse_pe
                            @st.cache_data(ttl=86400, show_spinner=False)
                            def cached_twse_pe(stock_symbol):
                                return official_twse_pe(stock_symbol, years=3)
                            auto_pe_result, pe_error = cached_twse_pe(symbol)
                        else:
                            from valuation_engine import historical_pe_bands
                            auto_pe_result, pe_error = historical_pe_bands(symbol, years=3)
                except Exception:
                    pe_error = "財務資料或股價來源暫時不可用"
                if auto_pe_result:
                    st.success(("公告日 CSV 歷史 PE：" if filing_upload is not None else "證交所官方歷史 PE：" if str(symbol).endswith(".TW") else "Yahoo 歷史 PE：") + "／".join(f"{p:.1f} 倍" for p in auto_pe_result["pes"]))
                    st.caption(f"樣本 {auto_pe_result['samples']} 日｜{auto_pe_result['start']}～{auto_pe_result['end']}｜{auto_pe_result['method']}")
                    if auto_pe_result.get("warnings"):
                        st.warning("估價可信度提醒：" + "；".join(auto_pe_result["warnings"]))
                    st.caption(f"季 EPS {auto_pe_result['eps_quarters']} 季（{auto_pe_result.get('eps_first', '未知')}～{auto_pe_result.get('eps_last', '未知')}）｜有效樣本跨度 {auto_pe_result.get('coverage_days', 0)} 天；資料不足時歷史分位數可能偏誤。")
                else:
                    st.warning(f"歷史 PE 無法計算：{pe_error}。自動估價已暫停，不會改用固定倍數；如需自行試算，請取消勾選自動歷史 PE。")
            growth_reference = None
            if valuation_enabled and market == "台灣股票／ETF" and symbol:
                from valuation_engine import eps_growth_reference
                growth_reference, growth_error = eps_growth_reference(symbol)
                if growth_reference:
                    st.caption(f"📊 財報參考：近四季 EPS 年增率 {growth_reference['growth_pct']:+.1f}%｜最新季末 {growth_reference['quarter_end']}｜{growth_reference['source']}（不是未來預測）")
                else:
                    st.caption(f"📊 無法取得 EPS 成長參考：{growth_error}")
            forecast_enabled = st.checkbox("加入未來 EPS 成長情境（非分析師預測）", value=False, key="b3_growth_on_v1")
            forecast_growth = st.number_input("假設下一年度 EPS 成長率（%）", min_value=-80.0, max_value=150.0, value=float(round(max(-80, min(150, growth_reference["growth_pct"])), 1)) if growth_reference else 10.0, step=5.0, key="b3_growth_pct_v3") if forecast_enabled else 0.0
            forecast_discount = st.number_input("未來估價安全折扣（%）", min_value=0.0, max_value=60.0, value=20.0, step=5.0, key="b3_growth_discount_v1") if forecast_enabled else 0.0
            if auto_pe_enabled:
                st.caption("下方手動 PE 只在取消勾選自動模式後使用，不會作為自動模式的備援。")
            v1, v2, v3 = st.columns(3)
            cheap_pe = v1.number_input("便宜 PE", min_value=1.0, max_value=200.0, value=12.0, step=0.5, key="b3_cheap_pe_v1")
            fair_pe = v2.number_input("合理 PE", min_value=1.0, max_value=200.0, value=16.0, step=0.5, key="b3_fair_pe_v1")
            expensive_pe = v3.number_input("昂貴 PE", min_value=1.0, max_value=200.0, value=20.0, step=0.5, key="b3_expensive_pe_v1")
            st.caption("自動模式僅使用歷史 PE 分位數；資料不足時不顯示估價。取消勾選自動模式才使用下方手動 PE。這不是孫慶龍本人發布的公式或估價。")

    sr_show = st.checkbox("顯示關鍵壓力與支撐點", value=True, key="sr_show")
    sr_window = st.selectbox("支撐壓力觀察根數", [60, 120, 250], index=1, key="sr_lookback", disabled=not sr_show)

    vp_show = st.checkbox("顯示成交量集中區（估算）", value=True, key="vp_show")
    with st.expander("成交量分布估算設定"):
        vp_window = st.selectbox("分布觀察根數（不含訊號K線）", [20, 60, 120, 250], index=1, key="vp_window")
        vp_bins = st.selectbox("價位格數", [20, 40, 80], index=1, key="vp_bins")
        vp_area = st.slider("價值區涵蓋量（%）", 50, 95, 70, key="vp_area")
        vp_buffer = st.number_input("價值區突破確認幅度（%）", min_value=0., max_value=5., value=.5, step=.1, key="vp_buffer")
        vp_ratio = st.number_input("價值區突破最低量比", min_value=1., max_value=5., value=1.5, step=.1, key="vp_ratio")
        st.caption("使用K線高低價均分成交量；非逐筆價量、未分日夜盤。")

# Keep the analysis control before the periodically refreshed financial fragment.
# Its sidebar subtree must not own or clear the following analysis button.
analysis_requested = st.sidebar.button(
    "開始亞當鏡像分析",
    type="primary", use_container_width=True
)
from auto_fundamentals import render_auto_fundamentals
render_auto_fundamentals(st.sidebar, symbol, market)

if analysis_requested or initial_chart:
    if not symbol:
        st.error("請輸入商品代碼")
        st.stop()

    try:
        if market == "台指期 TX（官方 CSV）":
            history = None
            if tx_files:
                history, _ = load_tx_csv(tx_files, tx_session)
            if tx_source == "官方 API 自動取得最新交易日":
                try:
                    latest = tx_latest_bar(tx_session)
                    df, roll_dates = merge_tx_history(history, latest)
                except Exception as api_error:
                    if history is None:
                        raise ValueError(f"官方 API 取得失敗：{api_error}；可改用 CSV 模式") from api_error
                    st.warning(f"官方 API 暫時無法取得，改用已上傳 CSV：{api_error}")
                    df, roll_dates = merge_tx_history(history, pd.DataFrame())
            else:
                if history is None:
                    raise ValueError("CSV 模式請先上傳期交所歷史資料")
                df, roll_dates = merge_tx_history(history, pd.DataFrame())
        else:
            df = get_data(
                symbol,
                period,
                interval
            )
            roll_dates = []

    except Exception as exc:
        st.error(
            f"資料下載失敗：{exc}"
        )
        st.stop()

    if df.empty:
        st.error("查無資料")
        st.stop()

    for note in df.attrs.get("raw_quote_notes", []):
        st.warning("原始行情資料提醒：" + note)

    quality_issues = audit_ohlc_data(df)
    if quality_issues:
        st.error("行情資料品質異常，已停止鏡像分析：" + "；".join(quality_issues))
        from quote_quality import invalid_price_rows
        invalid_rows = invalid_price_rows(df)
        if invalid_rows:
            st.caption("異常行情明細（最多列20根）：以下保留資料來源數值，未推測哪一個價格正確。")
            st.dataframe(pd.DataFrame(invalid_rows), hide_index=True)
        st.info("可將「歷史資料長度」縮短後重新分析，或稍後重試。縮短期間可能無法涵蓋完整中、長波，請保留資料不足提示；系統不會自動刪除異常K線或改寫價格。")
        st.stop()

    if roll_dates:
        dates_text = "、".join(
            pd.Timestamp(x).strftime("%Y-%m-%d")
            for x in roll_dates[-12:]
        )

        st.info(
            f"主力合約切換 {len(roll_dates)} 次："
            + dates_text
        )

    if market == "台指期 TX（官方 CSV）":
        st.warning(
            "官方 API 僅提供最近交易日，不能直接回補 2026 全年歷史。"
            "目前是未回補換月價差的主力連續合約；"
            "只有一根 K 棒時無法計算亞當波段。"
        )

    names = (
        [selected]
        if mode == "單一波段"
        else list(WAVES)
    )

    # 每個商品／週期／反轉門檻獨立記錄已確認的鏡像轉折。
    # Streamlit session_state 僅在目前瀏覽器工作階段保留前一版，
    # 不聲稱能跨裝置或重新啟動後永久保存。
    if "adam_mirror_history" not in st.session_state:
        st.session_state.adam_mirror_history = {}
    mirror_key = (market, symbol, interval, period, float(threshold))
    mirror_history = st.session_state.adam_mirror_history.setdefault(mirror_key, {})

    waves = []

    for name in names:
        required_bars = WAVES[name][1]
        available_bars = len(df)
        if available_bars < required_bars:
            st.warning(
                f"⚠️ {name}歷史資料不足：目前 {available_bars} 根／"
                f"參考設定 {required_bars} 根。"
                "鏡像若能計算，僅代表有限資料下的暫定結果，"
                "不可視為完整波段；建議選擇更長歷史期間。"
            )
        result = mirror_wave(
            df,
            name,
            threshold,
            interval
        )

        if result is None:
            st.warning(
                f"{name}轉折點不足，"
                "請增加歷史資料或降低反轉幅度。"
            )
        else:
            previous = mirror_history.get(name)
            signature = (
                str(result["recent"].index[result["start"]]),
                str(result["recent"].index[result["end"]]),
                len(result["segment"])
            )
            if previous is not None and previous["signature"] != signature:
                result["previous_mirror"] = previous["snapshot"]
                result["mirror_changed"] = True
            else:
                result["mirror_changed"] = False
                if previous is not None and "previous" in previous:
                    result["previous_mirror"] = previous["previous"]
            snapshot = {
                "times": list(result["times"]),
                "projection": [float(v) for v in result["projection"]],
                "updated_at": str(df.index[-1])
            }
            mirror_history[name] = {
                "signature": signature,
                "snapshot": snapshot,
                **({"previous": result["previous_mirror"]}
                   if "previous_mirror" in result else {})
            }
            waves.append(result)

    if not waves:
        st.stop()

    for w in waves:
        if w.get("mirror_changed"):
            st.info(f"{w['name']}偵測到新的已確認轉折：鏡像已更新，並保留上一版（本次瀏覽器工作階段）。")

    st.caption(
        f"商品：{symbol}｜"
        f"最新資料："
        f"{fmt_time(df.index[-1], interval)}｜"
        f"收盤價："
        f"{float(df['Close'].iloc[-1]):,.2f}"
    )

    for message in projection_warnings(waves):
        st.warning(message)

    with st.expander("歷史波段來源與鏡像說明",expanded=False) if initial_chart else nullcontext():
        st.subheader("亞當鏡像｜歷史波段來源")
        source_rows = wave_source_rows(waves, interval)
        # 手機優先：每波段各一張直向摘要，不必橫向捲動寬表格。
        for source in source_rows:
            with st.container(border=True):
                st.markdown(
                    f"**{source['波段']}**｜鏡像情境終點 "
                    f"**{source['鏡像終點']:,.2f}**"
                )
                st.caption(
                    f"歷史來源：{source['歷史起日']} → {source['歷史迄日']}"
                )
                st.caption(
                    f"歷史價格：{source['歷史起價']:,.2f} → "
                    f"{source['歷史迄價']:,.2f}"
                )
                if source["與其他波段相同來源"] != "無":
                    st.warning(
                        f"與{source['與其他波段相同來源']}共用同一歷史區間，"
                        "不是獨立鏡像訊號。"
                    )
        with st.expander("查看完整波段來源表"):
            st.dataframe(source_rows, use_container_width=True, hide_index=True)
        st.caption("鏡像終點僅為歷史時間左右翻轉的情境結果，不是未來價格預測。")

    config = {
        "scrollZoom": True,
        "displayModeBar": True,
        "displaylogo": False,
        "responsive": True,
        "modeBarButtonsToAdd": ["zoom2d", "pan2d", "zoomIn2d", "zoomOut2d", "autoScale2d", "resetScale2d"]
    }

    if mode == "三波各自獨立放大":
        for w in waves:
            st.subheader(
                f"{w['name']}｜獨立放大"
            )

            fig = make_figure(
                df,
                [w],
                chart_type,
                individual_zoom[w["name"]],
                f"{symbol}｜{w['name']} A模式完整鏡像",
                show_bollinger, boll_period, boll_std, chart_theme
            )

            if auto_boxes:
                from box_presentation import add_plotly_boxes
                add_plotly_boxes(fig, df, **box_options)

            for date in roll_dates:
                fig.add_vline(
                    x=date,
                    line_dash="dot",
                    line_color="purple",
                    opacity=0.5
                )

            if mobile_engine:
                mobile_chart(
                    df, [w], individual_zoom[w["name"]],
                    f"{symbol}｜{w['name']} A模式完整鏡像",
                    show_bollinger, boll_period, boll_std, chart_theme,
                    ma_periods=ma_periods, ema_periods=ema_periods,
                    auto_boxes=auto_boxes, box_window=box_window, box_width=box_width, box_options=box_options
                )
            else:
                st.plotly_chart(
                    fig,
                    use_container_width=True,
                    config=config,
                    key=f"wave_{w['name']}"
                )

    else:
        fig = make_figure(
            df,
            waves,
            chart_type,
            zoom,
            f"{symbol}｜{mode}｜A模式完整鏡像",
            show_bollinger, boll_period, boll_std
        )

        if auto_boxes:
            from box_presentation import add_plotly_boxes
            add_plotly_boxes(fig, df, **box_options)

        for date in roll_dates:
            fig.add_vline(
                x=date,
                line_dash="dot",
                line_color="purple",
                opacity=0.5
            )

        if mobile_engine:
            mobile_chart(
                df, waves, zoom, f"{symbol}｜{mode}｜A模式完整鏡像",
                show_bollinger, boll_period, boll_std, chart_theme,
                ma_periods=ma_periods, ema_periods=ema_periods,
                auto_boxes=auto_boxes, box_window=box_window, box_width=box_width, box_options=box_options
            )
        else:
            st.plotly_chart(
                fig,
                use_container_width=True,
                config=config,
                key="combined"
            )

    if vp_show:
        from volume_profile_estimate import show_volume_profile
        show_volume_profile(df, symbol, interval, vp_window, vp_bins, vp_area, vp_buffer, vp_ratio)

    if sr_show:
        from support_resistance import show_key_levels
        show_key_levels(df, symbol, interval, sr_window, production=PRODUCTION_MODE)


    if auto_boxes:
        from box_presentation import show_box_overview
        show_box_overview(df, interval_name, **box_options)
        st.caption(f"以下突破目標與歷史追蹤使用小區間 {box_window}根。")
        from box_theory import detect_boxes
        detected = detect_boxes(df, window=box_window, max_width_pct=box_width, max_boxes=5)
        st.subheader("自動箱型突破目標分析" if PRODUCTION_MODE else "自動箱型突破目標分析（測試版）")
        if detected:
            rows = []
            for n, box in enumerate(detected, 1):
                top, bottom = float(box["top"]), float(box["bottom"])
                height = top - bottom
                rows.append({
                    "箱型": f"箱{n}",
                    "開始": df.index[box["start"]].strftime("%Y-%m-%d"),
                    "結束": df.index[box["end"]].strftime("%Y-%m-%d"),
                    "狀態": box["status"],
                    "箱頂壓力": round(top, 2),
                    "箱底支撐": round(bottom, 2),
                    "箱型高度": round(height, 2),
                    "上突破目標": round(top + height, 2),
                    "下跌破目標": round(bottom - height, 2),
                })
            # An active box must contain the most recent candle and remain unbroken.
            active = next((b for b in reversed(detected)
                           if b["status"] == "整理中" and b["end"] == len(df) - 1), None)
            st.markdown("#### 最新有效箱型")
            if active is not None:
                top = float(active["top"])
                bottom = float(active["bottom"])
                height = top - bottom
                st.success(
                    f"目前仍在箱內整理｜支撐 {bottom:,.2f}｜壓力 {top:,.2f}｜"
                    f"上破量測 {top + height:,.2f}｜下破量測 {bottom - height:,.2f}"
                )
                st.caption("最新收盤仍在箱內；上、下目標須等待收盤有效突破後再作參考。")
            else:
                latest = detected[-1]
                st.info(
                    f"目前沒有仍有效的整理箱型。最近一個歷史箱型："
                    f"{latest['status']}（{df.index[latest['end']].strftime('%Y-%m-%d')} 結束）。"
                    "歷史箱型價位不直接視為當前有效支撐或壓力；轉換角色需確認回測。"
                )
            st.markdown("#### 最近一次箱型突破後追蹤" if PRODUCTION_MODE else "#### 最近一次箱型突破後追蹤（測試版）")
            from box_tracking import track_latest_breakout
            tracked = track_latest_breakout(df, detected)
            if tracked is None:
                st.caption("目前沒有可追蹤的已突破箱型。")
            else:
                st.write(
                    f"**{tracked['status']}**｜方向：{tracked['direction']}｜"
                    f"突破日：{tracked['breakout_date']}｜突破收盤：{tracked['breakout_close']:,.2f}"
                )
                c1, c2, c3 = st.columns(3)
                c1.metric("突破參考價", f"{tracked['breakout_level']:,.2f}")
                c2.metric("最新收盤", f"{tracked['latest_close']:,.2f}")
                c3.metric("等幅目標（推估）", f"{tracked['target']:,.2f}")
                if tracked["reentered"]:
                    st.warning(
                        f"已在 {tracked['reentry_date']} 首次收回原箱內；"
                        "原突破訊號視為失效，目標價不可當作有效交易訊號。"
                    )
                else:
                    st.caption(
                        "以收盤價判斷是否重新進入箱內；距突破價 1% 內提示回測／反彈測試。"
                        "未確認成交量、盤中觸價或多日站穩，請勿視為保證有效突破。"
                    )
            st.markdown("#### 歷史箱型紀錄（非目前有效價位）")
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            st.caption("目標價為箱型等幅量測推估，並非保證達到；突破狀態以收盤價判斷。")
        else:
            st.info("目前參數下沒有符合條件的整理箱型，可調整觀察根數或最大振幅。")

    if valuation_enabled:
        st.subheader("🧮 股票估價參考（測試版）")
        if eps_value <= 0:
            st.info("目前沒有有效 EPS，請切換手動輸入或確認資料來源。")
        elif auto_pe_enabled and auto_pe_result is None:
            st.warning("歷史 PE 資料不足或暫時無法取得：本次不顯示歷史估值與未來情境價格。請稍後重試，或取消自動模式後自行輸入 PE 試算。")
        elif not auto_pe_enabled and not (cheap_pe < fair_pe < expensive_pe):
            st.warning("本益比需符合：便宜 PE ＜ 合理 PE ＜ 昂貴 PE。")
        else:
            effective_pes = auto_pe_result["pes"] if auto_pe_enabled else (cheap_pe, fair_pe, expensive_pe)
            cheap_price, fair_price, expensive_price = [eps_value * pe for pe in effective_pes]
            latest_price = float(df["Close"].iloc[-1])
            official_pe_mode = bool(auto_pe_enabled and filing_upload is None and str(symbol).endswith(".TW"))
            quality_ok = bool(auto_pe_enabled and auto_pe_result and auto_pe_result["samples"] >= 250
                              and auto_pe_result.get("coverage_days", 0) >= 365
                              and (official_pe_mode or auto_pe_result.get("eps_quarters", 0) >= 12)
                              and not auto_pe_result.get("warnings"))
            p1, p2, p3 = st.columns(3)
            p1.metric(("🟢 歷史估值下緣（試算）" if auto_pe_enabled else "🟢 手動 PE 下緣（試算）") if not quality_ok else "🟢 便宜價（參考）", f"{cheap_price:,.2f}")
            p2.metric(("🟡 歷史估值中位（試算）" if auto_pe_enabled else "🟡 手動 PE 中位（試算）") if not quality_ok else "🟡 合理價（參考）", f"{fair_price:,.2f}")
            p3.metric(("🔴 歷史估值上緣（試算）" if auto_pe_enabled else "🔴 手動 PE 上緣（試算）") if not quality_ok else "🔴 昂貴價（參考）", f"{expensive_price:,.2f}")
            st.info("估值可信度：" + ("手動情境（不提供買進訊號）" if not auto_pe_enabled else "中（樣本門檻通過；仍需核對財報公告日）" if quality_ok else "低／未驗證（不提供買進訊號）"))
            category = ("便宜區" if latest_price <= cheap_price else
                        "合理偏低區" if latest_price < fair_price else
                        "合理偏高區" if latest_price < expensive_price else "昂貴區")
            st.write(f"最新資料收盤價：{latest_price:,.2f}｜隱含 PE：{latest_price / eps_value:.2f} 倍｜估價區間：**{category if quality_ok else '未判定（低可信度）'}**")
            if auto_pe_result and (latest_price / eps_value < effective_pes[0] * 0.8 or latest_price / eps_value > effective_pes[2] * 1.2):
                st.warning("目前隱含 PE 與歷史區間差距超過 20%；可能是獲利或市場評價結構改變，請勿直接把便宜價視為安全買點。")
            from valuation_engine import valuation_quality, conservative_entry
            quality, quality_reasons = valuation_quality(auto_pe_result if auto_pe_enabled else None, latest_price / eps_value, growth_reference)
            st.markdown(f"#### 🛡️ 估值資料可信度：{quality}")
            st.caption("依歷史樣本數、資料跨度、季 EPS、PE 分布與現價偏離程度評級；不代表預測準確率。")
            if quality_reasons:
                st.warning("評級原因：" + "；".join(quality_reasons))
            safety_price = conservative_entry(eps_value, auto_pe_result, margin_pct=25) if quality_ok else None
            if safety_price is not None:
                st.metric("🛡️ 保守觀察進場參考價（非買進建議）", f"{safety_price:,.2f}")
                st.caption("以歷史低檔 PE（20% 分位）與歷史中位 PE 再打 75 折，取較低者 × 近四季 EPS。此價格仍可能高於現價，不能據此判定低估。")
            else:
                st.info("缺乏可靠歷史 PE，暫不顯示保守進場參考價。")
            try:
                valuation_date = str(pd.Timestamp(df.index[-1]).date())
            except Exception:
                valuation_date = "日期未知"
            st.caption(f"📅 股價資料日期：{valuation_date}｜價格：歷史 K 線資料｜EPS：Yahoo Finance 或手動輸入｜歷史 PE：{auto_pe_result['method'] if auto_pe_result else '未取得'}；非即時報價。")
            if not quality_ok:
                st.warning("歷史 EPS 樣本不足或估價未驗證：數字僅供試算，不提供安全進場價。")
            if forecast_enabled:
                if not auto_pe_enabled:
                    st.info("以下未來 EPS 情境使用自行設定的手動 PE，並非歷史 PE 模型。")
                future_eps = eps_value * (1 + forecast_growth / 100)
                st.markdown("#### 📈 下一年度 EPS 情境估價（自行假設，非市場共識預測）")
                st.write(f"假設成長率 {forecast_growth:+.1f}%｜情境 EPS {future_eps:,.2f} 元｜安全折扣 {forecast_discount:.0f}%")
                if future_eps > 0:
                    future_prices = [future_eps * pe * (1 - forecast_discount / 100) for pe in effective_pes]
                    c1, c2, c3 = st.columns(3)
                    c1.metric("🟢 情境便宜價", f"{future_prices[0]:,.2f}")
                    c2.metric("🟡 情境合理價", f"{future_prices[1]:,.2f}")
                    c3.metric("🔴 情境昂貴價", f"{future_prices[2]:,.2f}")
                    gap = abs(future_prices[1] - fair_price) / fair_price * 100 if fair_price else 0
                    if gap > 30:
                        st.warning(f"歷史合理價與未來情境合理價差距 {gap:.1f}%，估價不確定性高。")
                else:
                    st.warning("情境 EPS 不可小於或等於零。")

            st.caption(f"估價依據：EPS {eps_value:,.2f} × PE {effective_pes[0]:.1f}／{effective_pes[1]:.1f}／{effective_pes[2]:.1f}；"
                       f"EPS 期間／來源：{eps_period or '未填寫'}。"
                       "自動 EPS 為近四季歷史值、非未來預估；PE 模式明確分開，不會自動回退固定倍數；非即時報價、非保證價位，亦非孫慶龍本人發布的估價。")

    if not PRODUCTION_MODE:
        show_live_candle(
            market, symbol, interval, df, waves,
            zoom if mode != "三波各自獨立放大" else "最近60根",
            show_bollinger, boll_period, boll_std, chart_theme
        )

    if mobile_engine:
        st.caption(
            "圖表操作：電腦滾輪放大縮小、按住左右拖曳；手機雙指縮放、單指左右拖曳。"
            "上下拖曳可調整價格顯示範圍（手機待實機驗收）；電腦雙擊右側價格軸可還原。"
            "點選圖表上方的波段標籤，可切換該波鏡像顯示。"
        )
    else:
        st.caption("亞當轉折點：點選或長按圖上的彩色圓點，可查看轉折日期與價位。")
        st.caption("圖表操作：使用工具列「＋／－」放大縮小、房屋圖示還原；放大鏡框選模式不適合手機觸控。")

    rows = []
    turn_rows = []

    for w in waves:
        p = w["projection"]
        t = w["times"]
        r = w["recent"]

        hi = w["high_i"]
        lo = w["low_i"]

        rows.append({
            "波段": w["name"],
            "最新收盤": round(w["latest"], 2),
            "鏡像最高價": round(float(p[hi]), 2),
            "最高價日期": fmt_time(t[hi], interval),
            "鏡像最低價": round(float(p[lo]), 2),
            "最低價日期": fmt_time(t[lo], interval),
            "鏡像終點價": round(float(p[-1]), 2),
            "終點日期": fmt_time(t[-1], interval),
            "鏡像K棒數": len(p),
            "歷史波段起日": fmt_time(
                r.index[w["start"]],
                interval
            ),
            "歷史波段迄日": fmt_time(
                r.index[w["end"]],
                interval
            ),
        })

        for number, (i, kind) in enumerate(
            w["turns"],
            start=1
        ):
            turn_rows.append({
                "波段": w["name"],
                "轉折順序": number,
                "轉折類型": kind,
                "參考日期": fmt_time(
                    t[i],
                    interval
                ),
                "參考價位": round(
                    float(p[i]),
                    2
                ),
                "距鏡像起點K棒": i,
            })

    st.subheader(
        "短、中、長波｜整段最高、最低與終點"
    )

    summary = pd.DataFrame(rows)

    st.dataframe(
        summary,
        use_container_width=True,
        hide_index=True
    )

    st.download_button(
        "下載鏡像價位 CSV",
        summary.to_csv(
            index=False
        ).encode("utf-8-sig"),
        "adam_wave_summary.csv",
        "text/csv"
    )

    st.subheader(
        "短、中、長波｜前 3 個內部轉折點"
    )

    if turn_rows:
        turns = pd.DataFrame(turn_rows)

        st.dataframe(
            turns,
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "下載內部轉折點 CSV",
            turns.to_csv(
                index=False
            ).encode("utf-8-sig"),
            "adam_internal_turns.csv",
            "text/csv"
        )
    else:
        st.info(
            "目前選定的完整波段"
            "沒有足夠的內部轉折點。"
        )

    st.warning(
        "左右鏡像僅為歷史價格路徑的情境推演，"
        "並非未來價格保證。"
        "日期僅為估算，未完整處理休市日、"
        "分K交易時段與期貨換月。"
    )

