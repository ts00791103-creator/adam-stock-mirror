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
                 boll_period=20, boll_std=2.0, chart_theme="券商深色", indicators=None, auto_boxes=False, box_window=20, box_width=12.0):
    """Render mobile-friendly pinch zoom; no effect on Adam calculations."""
    indicators = set(indicators if indicators is not None else (["BOLL"] if show_bollinger else []))
    show_bollinger = "BOLL" in indicators
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
    boxes = detect_boxes(df, box_window, box_width) if auto_boxes else []
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
    for kind, periods in (("MA", (5, 10, 20, 60, 120, 240)), ("EMA", (5, 10, 20, 60))):
        if kind not in indicators:
            continue
        palette = ["#f5c542", "#00bcd4", "#ef6c9a", "#9c80ff", "#66bb6a", "#ff8a65"]
        for period, color in zip(periods, palette):
            values = (close.rolling(period, min_periods=period).mean()
                      if kind == "MA" else close.ewm(span=period, adjust=False, min_periods=period).mean())
            series.append({"name": f"{kind}{period}", "color": color,
                           "points": _points(plot_df.index, values.reindex(plot_df.index))})
    panels = []
    if "VOL" in indicators:
        panels.append({"name": "成交量 VOL", "type": "histogram",
                       "lines": [{"name": "成交量", "color": "#729bc2",
                                  "points": _points(plot_df.index, df["Volume"].reindex(plot_df.index).fillna(0))}]})
    if "KD" in indicators:
        low = df["Low"].rolling(9, min_periods=9).min()
        high = df["High"].rolling(9, min_periods=9).max()
        rsv = ((close-low)/(high-low).replace(0, float("nan"))*100).fillna(50)
        k = rsv.ewm(alpha=1/3, adjust=False).mean()
        d = k.ewm(alpha=1/3, adjust=False).mean()
        panels.append({"name": "KD (9,3,3)", "lines": [
            {"name": "K", "color": "#f5c542", "points": _points(plot_df.index, k.reindex(plot_df.index))},
            {"name": "D", "color": "#00bcd4", "points": _points(plot_df.index, d.reindex(plot_df.index))}]})
    if "MACD" in indicators:
        dif = close.ewm(span=12, adjust=False).mean()-close.ewm(span=26, adjust=False).mean()
        signal = dif.ewm(span=9, adjust=False).mean()
        panels.append({"name": "MACD (12,26,9)", "lines": [
            {"name": "DIF", "color": "#f5c542", "points": _points(plot_df.index, dif.reindex(plot_df.index))},
            {"name": "訊號", "color": "#00bcd4", "points": _points(plot_df.index, signal.reindex(plot_df.index))},
            {"name": "柱狀體", "color": "#a88bff", "type": "histogram",
             "points": _points(plot_df.index, (dif-signal).reindex(plot_df.index))}]})
    if "RSI" in indicators:
        delta = close.diff()
        gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False, min_periods=14).mean()
        loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False, min_periods=14).mean()
        rsi = 100 - 100/(1+gain/loss.replace(0, float("nan")))
        panels.append({"name": "RSI (14)", "lines": [
            {"name": "RSI", "color": "#f5c542", "points": _points(plot_df.index, rsi.reindex(plot_df.index))}]})
    for wave in waves:
        series.append({"name": wave["name"] + "歷史波段",
                       "color": wave["color"],
                       "points": _points(wave["recent"].index[wave["start"]:wave["end"]+1],
                                         wave["segment"]), "style": 0})
        series.append({"name": wave["name"] + "左右鏡像",
                       "color": wave["color"],
                       "points": _points(wave["times"], wave["projection"]),
                       "style": 2})
    # Lightweight Charts requires monotonically increasing unique timestamps.
    for line in series:
        unique = {p["time"]: p for p in line["points"]}
        line["points"] = sorted(unique.values(), key=lambda p: p["time"])
    bars = sorted({b["time"]: b for b in bars}.values(), key=lambda b: b["time"])
    payload = json.dumps({"bars": bars, "lines": series,
                          "count": view_count, "dark": dark,
                          "title": title, "panels": panels, "boxes": boxes}, ensure_ascii=False).replace("</", "<\\/")
    html = """<!doctype html><html lang="zh-Hant"><head><meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<style>html,body{margin:0;padding:0;overflow:hidden;background:BG;color:FG;font-family:-apple-system,BlinkMacSystemFont,'Noto Sans TC',sans-serif}
#chart-wrap{position:relative}#box-overlay{position:absolute;inset:0;pointer-events:none;width:100%;height:100%}#heading{padding:8px 10px;font-size:14px;font-weight:600}#chart{width:100%;height:480px;touch-action:pan-y}
#panels .panel{height:175px;width:100%}#panels .panel-title{padding:5px 10px;font-size:12px}#hint{font-size:12px;opacity:.8;padding:6px 10px}#error{color:#ff7777;padding:12px}</style></head>
<body><div id="heading"></div><div id="chart-wrap"><div id="chart"></div><canvas id="box-overlay"></canvas></div><div id="panels"></div><div id="hint">雙指縮放｜單指左右拖曳｜點選 K 棒查看價格</div><div id="error"></div>
<script src="https://unpkg.com/lightweight-charts@4.2.3/dist/lightweight-charts.standalone.production.js"></script>
<script>
const data=PAYLOAD;
document.getElementById('heading').textContent=data.title;
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
  const l=chart.addLineSeries({color:line.color,lineWidth:line.style===2?3:2,
   lineStyle:line.style===2?LightweightCharts.LineStyle.Dashed:LightweightCharts.LineStyle.Solid,
   title:line.name,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false});
  l.setData(line.points);
 }
 if(data.bars.length){
  const count=Math.min(data.count,data.bars.length);
  chart.timeScale().setVisibleLogicalRange({from:Math.max(0,data.bars.length-count),
   to:data.bars.length+Math.min(5,Math.max(1,Math.floor(count/4)))});
 }
 for(const panel of data.panels){
  const holder=document.createElement('div');
  const label=document.createElement('div');label.className='panel-title';label.textContent=panel.name;
  const el=document.createElement('div');el.className='panel';
  holder.appendChild(label);holder.appendChild(el);document.getElementById('panels').appendChild(holder);
  const pc=LightweightCharts.createChart(el,{
   width:el.clientWidth,height:175,
   layout:{background:{type:'solid',color:dark?'#101010':'#ffffff'},textColor:dark?'#eeeeee':'#333333'},
   grid:{vertLines:{color:dark?'#242424':'#eeeeee'},horzLines:{color:dark?'#353535':'#eeeeee'}},
   timeScale:{timeVisible:true,secondsVisible:false},handleScale:{pinch:true},
   handleScroll:{horzTouchDrag:true,vertTouchDrag:false}
  });
  for(const line of panel.lines){
   if(!line.points.length)continue;
   const ps=line.type==='histogram'?pc.addHistogramSeries({color:line.color,priceFormat:{type:'volume'}}):
     pc.addLineSeries({color:line.color,lineWidth:2,title:line.name,priceLineVisible:false});
   ps.setData(line.points);
  }
  if(data.bars.length){const count=Math.min(data.count,data.bars.length);
   pc.timeScale().setVisibleLogicalRange({from:Math.max(0,data.bars.length-count),to:data.bars.length+5});}
  new ResizeObserver(()=>pc.applyOptions({width:el.clientWidth})).observe(el);
 }
 const overlay=document.getElementById('box-overlay');
 function drawBoxes(){
  if(!data.boxes.length)return;
  const w=overlay.clientWidth,h=overlay.clientHeight,dpr=window.devicePixelRatio||1;
  overlay.width=Math.round(w*dpr);overlay.height=Math.round(h*dpr);
  const ctx=overlay.getContext('2d');ctx.scale(dpr,dpr);
  for(const b of data.boxes){
   const x1=chart.timeScale().timeToCoordinate(b.start);
   const x2=chart.timeScale().timeToCoordinate(b.end);
   const y1=candle.priceToCoordinate(b.top),y2=candle.priceToCoordinate(b.bottom);
   if([x1,x2,y1,y2].some(v=>v===null||!Number.isFinite(v)))continue;
   const left=Math.min(x1,x2),top=Math.min(y1,y2),width=Math.abs(x2-x1)+5,height=Math.abs(y2-y1);
   ctx.fillStyle='rgba(80,150,230,0.10)';ctx.fillRect(left,top,width,height);
   ctx.strokeStyle='rgba(95,170,250,0.85)';ctx.lineWidth=1.5;ctx.strokeRect(left,top,width,height);
   ctx.setLineDash([4,4]);ctx.beginPath();ctx.moveTo(left,(y1+y2)/2);ctx.lineTo(left+width,(y1+y2)/2);ctx.stroke();ctx.setLineDash([]);
   ctx.font='11px sans-serif';ctx.fillStyle=dark?'#d1e6ff':'#18508a';
   ctx.fillText('箱 '+b.top+' / '+b.bottom+' '+b.breakout,left+3,Math.max(12,top-4));
  }
 }
 chart.timeScale().subscribeVisibleTimeRangeChange(drawBoxes);
 chart.timeScale().subscribeVisibleLogicalRangeChange(drawBoxes);
 requestAnimationFrame(drawBoxes);
 const resize=new ResizeObserver(()=>{drawBoxes();});
 resize.observe(document.getElementById('chart'));
 const resize=new ResizeObserver(()=>chart.applyOptions({width:document.getElementById('chart').clientWidth}));
 resize.observe(document.getElementById('chart'));
}
</script></body></html>"""
    html = html.replace("BG", "#101010" if dark else "#ffffff").replace(
        "FG", "#ffffff" if dark else "#222222").replace("PAYLOAD", payload)
    components.html(html, height=555 + 198 * len(panels), scrolling=False)
