"""Mobile financial chart renderer (TradingView Lightweight Charts v4)."""
import json
import math
import pandas as pd
import streamlit.components.v1 as components
from box_theory import detect_boxes


def _points(index, values):
    result = []
    for timestamp, value in zip(index, values):
        try:
            price = float(value)
            if math.isfinite(price):
                result.append({"time": int(pd.Timestamp(timestamp).timestamp()), "value": price})
        except (TypeError, ValueError, OverflowError):
            pass
    return result


def mobile_chart(df, waves, zoom, title, show_bollinger=False,
                 boll_period=20, boll_std=2.0, chart_theme="券商深色", viewport_key=None, ma_periods=None, ema_periods=None, auto_boxes=False, box_window=20, box_width=12.0):
    """Render mobile-friendly pinch zoom; no effect on Adam calculations."""
    dark = chart_theme == "券商深色"
    if zoom == "全部歷史與鏡像":
        view_count = min(len(df), 120)
    else:
        try:
            view_count = int(zoom.replace("最近", "").replace("根", ""))
        except ValueError:
            view_count = 60
    plot_df = df.tail(min(len(df), max(300, view_count + 40)))
    bars = []
    for t, row in plot_df.iterrows():
        bars.append({
            "time": int(pd.Timestamp(t).timestamp()),
            "open": float(row["Open"]), "high": float(row["High"]),
            "low": float(row["Low"]), "close": float(row["Close"])
        })
    series = []
    if show_bollinger and len(df) >= boll_period:
        mid = df["Close"].rolling(boll_period, min_periods=boll_period).mean()
        dev = df["Close"].rolling(boll_period, min_periods=boll_period).std(ddof=0)
        for name, values, color in [
            ("布林上軌", mid + boll_std * dev, "#ffff00" if dark else "#d97706"),
            ("布林中軌", mid, "#00d9f5" if dark else "#2563eb"),
            ("布林下軌", mid - boll_std * dev, "#d000ff" if dark else "#9333ea")
        ]:
            series.append({"name": name, "color": color,
                           "points": _points(plot_df.index, values.reindex(plot_df.index))})
    close = df["Close"].astype(float)
    for kind, periods in (("MA", ma_periods or []), ("EMA", ema_periods or [])):
        for period in periods:
            if kind == "MA":
                values = close.rolling(period, min_periods=period).mean()
            else:
                values = close.ewm(span=period, adjust=False, min_periods=period).mean()
            palette = {5:"#ffca28",10:"#29b6f6",20:"#ab47bc",60:"#66bb6a",120:"#ef5350",240:"#b0bec5"}
            series.append({"name":f"{kind}{period}", "color":palette.get(period,"#ffffff"),
                           "points":_points(plot_df.index,values.reindex(plot_df.index))})
    for wave in waves:
        series.append({"name": wave["name"] + "歷史波段",
                       "color": wave["color"],
                       "points": _points(wave["recent"].index[wave["start"]:wave["end"]+1],
                                         wave["segment"]), "style": 0})
        series.append({"name": wave["name"] + "左右鏡像",
                       "color": wave["color"],
                       "points": _points(wave["times"], wave["projection"]),
                       "style": 2})
    for wave in waves:
        previous = wave.get("previous_mirror")
        if previous:
            series.append({
                "name": wave["name"] + "上一版鏡像",
                "color": wave["color"],
                "points": _points(previous["times"], previous["projection"]),
                "style": 1
            })
    boxes = detect_boxes(df, box_window, box_width) if auto_boxes else []
    for n, box in enumerate(boxes, 1):
        indexes = df.index[box["start"]:box["end"]+1]
        if len(indexes) < 2:
            continue
        for label, value, color in [
            ("箱頂", box["top"], "#52a9ff"),
            ("箱底", box["bottom"], "#52a9ff"),
            ("箱中線", box["mid"], "#7e98b6")
        ]:
            series.append({"name": "",
                           "color": color,
                           "points": _points([indexes[0], indexes[-1]], [value, value]),
                           "style": 1 if label == "箱中線" else 0})
    # Lightweight Charts requires monotonically increasing unique timestamps.
    for line in series:
        unique = {p["time"]: p for p in line["points"]}
        line["points"] = sorted(unique.values(), key=lambda p: p["time"])
    bars = sorted({b["time"]: b for b in bars}.values(), key=lambda b: b["time"])
    payload = json.dumps({"rendererVersion": "BOX-1125C", "bars": bars, "lines": series,
                          "count": view_count, "dark": dark,
                          "title": title, "viewportKey": viewport_key}, ensure_ascii=False).replace("</", "<\\/")
    html = """<!doctype html><html lang="zh-Hant"><head><meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<style>html,body{margin:0;padding:0;overflow:hidden;background:BG;color:FG;font-family:-apple-system,BlinkMacSystemFont,'Noto Sans TC',sans-serif}
#heading{padding:8px 10px;font-size:14px;font-weight:600}#chart{width:100%;height:480px;touch-action:pan-y}
#hint{font-size:12px;opacity:.8;padding:6px 10px}#error{color:#ff7777;padding:12px}</style></head>
<body><div id="heading"></div><div id="renderer-status" style="padding:4px 10px;font-size:12px;color:#65d6a5">手機圖表版本 BOX-1125D｜箱型標籤關閉</div><div id="chart"></div><div id="hint">雙指縮放｜單指左右拖曳｜點選 K 棒查看價格</div><div id="error"></div>
<script src="https://unpkg.com/lightweight-charts@4.2.3/dist/lightweight-charts.standalone.production.js"></script>
<script>
const data=PAYLOAD;
document.getElementById('heading').textContent=data.title+'｜'+data.rendererVersion;
if(!window.LightweightCharts){document.getElementById('error').textContent='圖表元件載入失敗，請檢查網路或切回原本圖表。';}
else {
 const dark=data.dark;
 const chart=LightweightCharts.createChart(document.getElementById('chart'),{
  width:document.getElementById('chart').clientWidth,height:480,
  layout:{background:{type:'solid',color:dark?'#101010':'#ffffff'},textColor:dark?'#eeeeee':'#333333'},
  grid:{vertLines:{color:dark?'#242424':'#eeeeee'},horzLines:{color:dark?'#353535':'#eeeeee'}},
  timeScale:{timeVisible:true,secondsVisible:false,rightOffset:5,barSpacing:9,
    fixLeftEdge:false,lockVisibleTimeRangeOnResize:true},
  rightPriceScale:{borderColor:dark?'#555555':'#cccccc'},
  handleScroll:{mouseWheel:true,pressedMouseMove:true,horzTouchDrag:true,vertTouchDrag:false},
  handleScale:{mouseWheel:true,pinch:true,axisPressedMouseMove:false},
  crosshair:{mode:LightweightCharts.CrosshairMode.Normal}
 });
 const candle=chart.addCandlestickSeries({
  upColor:dark?'#ff2020':'#26a69a',downColor:dark?'#00e000':'#ef5350',
  borderUpColor:dark?'#ff2020':'#26a69a',borderDownColor:dark?'#00e000':'#ef5350',
  wickUpColor:dark?'#ff2020':'#26a69a',wickDownColor:dark?'#00e000':'#ef5350'
 });
 candle.setData(data.bars);
 for(const line of data.lines){
  if(!line.points.length)continue;
  const l=chart.addLineSeries({color:line.color,lineWidth:line.style===2?3:(line.style===1?1:2),
   lineStyle:line.style===2?LightweightCharts.LineStyle.Dashed:(line.style===1?LightweightCharts.LineStyle.Dotted:LightweightCharts.LineStyle.Solid),
   title:line.name||'',priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false});
  l.setData(line.points);
 }
 // Remember the visible logical range between Streamlit fragment redraws.
 // Never use the timestamp range: a new candle should not shift the user's view.
 let storageKey=data.viewportKey?'b3pro-viewport-'+data.viewportKey:null;
 let saved=null;
 try { if(storageKey) saved=JSON.parse(sessionStorage.getItem(storageKey)||'null'); } catch(e) {}
 if(saved && Number.isFinite(saved.from) && Number.isFinite(saved.to) && saved.to>saved.from){
   try { chart.timeScale().setVisibleLogicalRange(saved); } catch(e) { saved=null; }
 }
 if(!saved && data.bars.length){
   const count=Math.min(data.count,data.bars.length);
   chart.timeScale().setVisibleLogicalRange({from:Math.max(0,data.bars.length-count),
    to:data.bars.length+Math.min(5,Math.max(1,Math.floor(count/4)))});
 }
 let persistTimer=null;
 chart.timeScale().subscribeVisibleLogicalRangeChange(range=>{
   if(!storageKey || !range || !Number.isFinite(range.from) || !Number.isFinite(range.to))return;
   clearTimeout(persistTimer);
   persistTimer=setTimeout(()=>{
     try {sessionStorage.setItem(storageKey,JSON.stringify({from:range.from,to:range.to}));}catch(e){}
   },150);
 });
 const resize=new ResizeObserver(()=>chart.applyOptions({width:document.getElementById('chart').clientWidth}));
 resize.observe(document.getElementById('chart'));
}
</script></body></html>"""
    html = html.replace("BG", "#101010" if dark else "#ffffff").replace(
        "FG", "#ffffff" if dark else "#222222").replace("PAYLOAD", payload)
    components.html(html, height=555, scrolling=False)
