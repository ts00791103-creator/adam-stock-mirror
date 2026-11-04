import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title='亞當理論｜完整波段鏡像 B2', layout='wide')
st.title('亞當理論｜完整波段鏡像分析 B2 版')
st.caption('歷史波段左右翻轉：短、中、長波分別推演｜僅供情境參考，並非價格預測')

@st.cache_data(ttl=1800)
def load_prices(symbol, period):
    data = yf.download(symbol, period=period, auto_adjust=True, progress=False, threads=False)
    if data.empty:
        return pd.Series(dtype=float)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    if 'Close' not in data.columns:
        return pd.Series(dtype=float)
    return data['Close'].dropna().astype(float)


def turning_points(prices, threshold):
    """以百分比反轉門檻確認高低轉折；最後未確認的一段不當作完整波段。"""
    values = prices.to_numpy(dtype=float)
    if len(values) < 3:
        return []
    extreme = 0
    direction = 0
    points = []
    for i in range(1, len(values)):
        if direction == 0:
            change = values[i] / values[extreme] - 1
            if change >= threshold:
                points.append((extreme, '低'))
                direction = 1
                extreme = i
            elif change <= -threshold:
                points.append((extreme, '高'))
                direction = -1
                extreme = i
            elif values[i] > values[extreme] and values[i] >= values[0]:
                extreme = i
            elif values[i] < values[extreme] and values[i] <= values[0]:
                extreme = i
        elif direction == 1:
            if values[i] >= values[extreme]:
                extreme = i
            elif values[i] <= values[extreme] * (1 - threshold):
                points.append((extreme, '高'))
                direction = -1
                extreme = i
        else:
            if values[i] <= values[extreme]:
                extreme = i
            elif values[i] >= values[extreme] * (1 + threshold):
                points.append((extreme, '低'))
                direction = 1
                extreme = i
    return points


def mirror_segment(prices, turns, max_days):
    """選最後兩個已確認轉折構成完整歷史波段，時間倒序後以現價銜接。"""
    if len(turns) < 2:
        return None
    end = turns[-1][0]
    start = turns[-2][0]
    if end <= start:
        return None
    segment = prices.iloc[start:end + 1].to_numpy(dtype=float)
    if len(segment) < 3 or len(segment) > max_days:
        return None
    # 左右翻轉：最新的歷史端先出現，接著倒序走回歷史起點。
    reversed_path = segment[::-1]
    # 比例縮放，使鏡像起點與最新收盤價一致；避免使用絕對價差造成負價。
    current = float(prices.iloc[-1])
    forecast = current * (reversed_path / reversed_path[0])
    return start, end, forecast

code = st.text_input('輸入台股代號', value='2308').strip()
market = st.selectbox('股票市場', ['上市', '上櫃'])
period = st.selectbox('歷史資料長度', ['5y', '10y', '2y', '1y'], index=0)
threshold = st.slider('轉折敏感度（%）', min_value=3, max_value=20, value=5)
settings = {'短波': (threshold, 90), '中波': (min(threshold * 2, 35), 260), '長波': (min(threshold * 3, 50), 700)}

if st.button('開始完整波段分析', type='primary'):
    if not code.isdigit():
        st.error('請輸入數字股票代號，例如 2308。')
        st.stop()
    ticker = code + ('.TW' if market == '上市' else '.TWO')
    with st.spinner('正在取得歷史股價並分析...'):
        try:
            prices = load_prices(ticker, period)
        except Exception as exc:
            st.error(f'資料下載失敗：{exc}')
            st.stop()
    if len(prices) < 30:
        st.error('歷史資料不足，請確認代號、市場或資料來源。')
        st.stop()

    latest_date = pd.Timestamp(prices.index[-1]).date()
    st.success(f'{ticker}｜最新資料日：{latest_date}｜調整後收盤價：{prices.iloc[-1]:,.2f} 元')
    st.info('圖中的虛線是歷史波段「時間左右翻轉」後，以最新收盤價比例銜接的情境路徑，不代表未來必然如此。')
    tabs = st.tabs(['短波', '中波', '長波'])
    for tab, (name, (pct, limit)) in zip(tabs, settings.items()):
        with tab:
            turns = turning_points(prices, pct / 100)
            result = mirror_segment(prices, turns, limit)
            if result is None:
                st.warning(f'{name}：尚未找到符合條件的完整波段。可調低敏感度或加長歷史期間。')
                continue
            start, end, path = result
            dates = pd.bdate_range(start=pd.Timestamp(prices.index[-1]) + pd.offsets.BDay(1), periods=len(path))
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=prices.index, y=prices.values, name='歷史調整後收盤價', line=dict(color='#2563eb')))
            fig.add_trace(go.Scatter(x=[prices.index[-1]] + list(dates), y=[prices.iloc[-1]] + list(path),
                                     name='左右翻轉鏡像（情境）', line=dict(color='#dc2626', dash='dash', width=3)))
            for idx, kind in turns:
                fig.add_trace(go.Scatter(x=[prices.index[idx]], y=[prices.iloc[idx]], mode='markers',
                                         marker=dict(size=7, color='#16a34a' if kind == '低' else '#f59e0b'),
                                         name=f'確認{kind}點', showlegend=False))
            fig.update_layout(title=f'{name}｜轉折門檻 {pct}%｜鏡像 {len(path)} 個交易日',
                              xaxis_title='日期（未來以工作日近似，未扣除台股休市日）',
                              yaxis_title='價格（元）', hovermode='x unified', height=520)
            st.plotly_chart(fig, use_container_width=True)
            st.write(f'**歷史參考完整波段：** {pd.Timestamp(prices.index[start]).date()} ～ {pd.Timestamp(prices.index[end]).date()}')
            st.write(f'**鏡像最高參考價：** {np.max(path):,.2f} 元　｜　**鏡像最低參考價：** {np.min(path):,.2f} 元')
            st.write(f'**鏡像終點參考價：** {path[-1]:,.2f} 元　｜　**推演長度：** {len(path)} 個交易日')
            st.caption('高低點是鏡像情境價位，不是經過驗證的支撐壓力或買賣訊號。')
            output = pd.DataFrame({'參考日期（工作日）': dates.date.astype(str), '鏡像情境價格': np.round(path, 2)})
            st.download_button(f'下載{name}鏡像數據 CSV', data=output.to_csv(index=False).encode('utf-8-sig'),
                               file_name=f'{ticker}_{name}_B2.csv', mime='text/csv', key=f'download_{name}')
