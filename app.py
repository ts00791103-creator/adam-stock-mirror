import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="亞當理論 B3 Pro", layout="wide")
st.title("亞當理論 B3 Pro｜A 模式左右鏡像")
st.caption("完整鏡像｜三波同圖／獨立放大｜每波前 3 個內部轉折點")

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
    return df


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

    # 日K：隱藏週末及實際資料缺少的平日（假日／休市日）。
    # 只調整日期軸的顯示，布林軌道與亞當鏡像仍使用原始資料。
    if pd.DatetimeIndex(df.index).normalize().is_unique and len(df) > 1:
        observed = pd.DatetimeIndex(df.index).normalize()
        expected = pd.bdate_range(observed.min(), observed.max())
        missing_days = expected.difference(observed)
        daily_breaks = [dict(bounds=["sat", "mon"])]
        if len(missing_days):
            daily_breaks.append(dict(values=missing_days.strftime("%Y-%m-%d").tolist()))
        fig.update_xaxes(rangebreaks=daily_breaks)

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
        title=title,
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
            font=dict(size=11)
        ),
        margin=dict(
            l=35,
            r=35,
            t=85,
            b=135
        )
    )

    fig.update_xaxes(gridcolor="#353535" if dark else "#e5e7eb")
    fig.update_yaxes(gridcolor="#353535" if dark else "#e5e7eb")

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

market = st.selectbox(
    "選擇市場",
    list(MARKETS)
)

if MARKETS[market] is None:
    query = st.text_input(
        "股票代號或中文名稱（例如：2330、台積電、台達電）",
        "2308"
    ).strip()
    stock_list = load_tw_symbols()
    matches = [
        (code, name, ex) for code, name, ex in stock_list
        if query and (query.lower() in code.lower() or query.lower() in name.lower())
    ]
    if matches:
        choices = matches[:100]
        labels = [f"{code} {name}（{ex}）" for code, name, ex in choices]
        chosen = st.selectbox("選擇股票／ETF", range(len(choices)),
                              format_func=lambda i: labels[i])
        code, stock_name, exchange = choices[chosen]
        symbol = code + (".TW" if exchange == "上市" else ".TWO")
        st.caption(f"目前選擇：{code} {stock_name}｜{exchange}")
    elif query.isdigit():
        exchange = st.radio("查無名稱對照，請選擇交易市場", ["上市", "上櫃"],
                            horizontal=True)
        symbol = query + (".TW" if exchange == "上市" else ".TWO")
        st.caption("目前使用股票代號查詢；中文名稱資料可能暫時無法取得。")
    else:
        symbol = ""
        if query:
            st.warning("找不到符合的中文股票名稱。請輸入完整名稱或股票代號。")

elif MARKETS[market] == "TAIFEX_TX":
    symbol = "TX（官方期交所 CSV）"

    tx_files = st.file_uploader(
        "上傳期交所年度期貨 CSV（可一次選多個年份）",
        type=["csv"],
        accept_multiple_files=True
    )

    tx_session = st.radio(
        "台指期交易時段",
        ["日盤", "日盤＋夜盤"],
        horizontal=True
    )

    st.caption(
        "使用官方交易日期合併夜盤；"
        "本版依日盤成交量選擇主力月合約。"
    )

elif MARKETS[market] == "CUSTOM":
    symbol = st.text_input(
        "Yahoo Finance 商品代碼",
        ""
    ).strip().upper()

else:
    symbol = MARKETS[market]


c1, c2 = st.columns(2)

with c1:
    if market == "台指期 TX（官方 CSV）":
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
    ["K線", "線圖"],
    horizontal=True
)

chart_theme = st.radio(
    "圖表配色",
    ["券商深色", "原本淺色"],
    horizontal=True
)

show_bollinger = st.checkbox("顯示布林軌道（BOLL）", value=False)
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

st.info(
    "未來鏡像保留全部 K 棒；"
    "初始畫面只顯示所選根數。"
)


# ===== 開始分析 =====

if st.button(
    "開始亞當鏡像分析",
    type="primary"
):
    if not symbol:
        st.error("請輸入商品代碼")
        st.stop()

    try:
        if market == "台指期 TX（官方 CSV）":
            df, roll_dates = load_tx_csv(
                tx_files,
                tx_session
            )
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
            "此處為按日盤成交量挑選的"
            "主力連續合約，未回補換月價差。"
            "2025 年資料不代表 2026 年最新行情。"
        )

    names = (
        [selected]
        if mode == "單一波段"
        else list(WAVES)
    )

    waves = []

    for name in names:
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
            waves.append(result)

    if not waves:
        st.stop()

    st.caption(
        f"商品：{symbol}｜"
        f"最新資料："
        f"{fmt_time(df.index[-1], interval)}｜"
        f"收盤價："
        f"{float(df['Close'].iloc[-1]):,.2f}"
    )

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

            for date in roll_dates:
                fig.add_vline(
                    x=date,
                    line_dash="dot",
                    line_color="purple",
                    opacity=0.5
                )

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

        for date in roll_dates:
            fig.add_vline(
                x=date,
                line_dash="dot",
                line_color="purple",
                opacity=0.5
            )

        st.plotly_chart(
            fig,
            use_container_width=True,
            config=config,
            key="combined"
        )

    st.caption("亞當轉折點：點選或長按圖上的彩色圓點，可查看轉折日期與價位。")
    st.caption(
        "手機操作：預設左右拖曳移動K線；使用圖表工具列「＋／－」放大縮小。"
        "若畫面異常，點房屋圖示還原；放大鏡框選模式不適合手機觸控。"
    )

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
