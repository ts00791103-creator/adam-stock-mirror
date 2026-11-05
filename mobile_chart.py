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
    volume_unit = "口" if str(title).upper().find("TX") >= 0 and "台指" in str(title) else "張"
    volumes = []
    if "Volume" in plot_df.columns:
        for t, row in plot_df.iterrows():
            v = pd.to_numeric(row["Volume"], errors="coerce")
            if pd.notna(v) and float(v) >= 0:
                volumes.append({"time": int(pd.Timestamp(t).timestamp()), "value": float(v) / (1000 if volume_unit == "張" else 1),
                                "color": "#ef4444" if float(row["Close"]) >= float(row["Open"]) else "#22c55e"})
    volume_ma5 = _points(plot_df.index, pd.to_numeric(df["Volume"], errors="coerce").rolling(5).mean().reindex(plot_df.index) / (1000 if volume_unit == "張" else 1)) if "Volume" in df else []
    volume_ma20 = _points(plot_df.index, pd.to_numeric(df["Volume"], errors="coerce").rolling(20).mean().reindex(plot_df.index) / (1000 if volume_unit == "張" else 1)) if "Volume" in df else []
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
    rectangles = []
    visible_start = pd.Timestamp(plot_df.index[0]).timestamp()
    visible_end = pd.Timestamp(plot_df.index[-1]).timestamp()
    for box in boxes:
        start_ts = int(pd.Timestamp(df.index[box["start"]]).timestamp())
        end_ts = int(pd.Timestamp(df.index[box["end"]]).timestamp())
        if end_ts < visible_start or start_ts > visible_end:
            continue
        rectangles.append({"start": max(start_ts, int(visible_start)),
                           "end": min(end_ts, int(visible_end)),
                           "top": box["top"], "bottom": box["bottom"],
                           "status": box["status"]})
    # Lightweight Charts requires monotonically increasing unique timestamps.
    for line in series:
        unique = {p["time"]: p for p in line["points"]}
        line["points"] = sorted(unique.values(), key=lambda p: p["time"])
    bars = sorted({b["time"]: b for b in bars}.values(), key=lambda b: b["time"])
    payload = json.dumps({"rendererVersion": "VOL-OHLC-1", "bars": bars, "lines": series, "boxes": rectangles, "volumes": volumes, "volumeMA5": volume_ma5, "volumeMA20": volume_ma20, "volumeUnit": volume_unit,
                          "count": view_count, "dark": dark,
                          "title": title, "viewportKey": viewport_key}, ensure_ascii=False).replace("</", "<\\/")
    html = """<!doctype html><html lang="zh-Hant"><head><meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<style>html,body{margin:0;padding:0;overflow:hidden;background:BG;color:FG;font-family:-apple-system,BlinkMacSystemFont,'Noto Sans TC',sans-serif}
#heading{padding:8px 10px;font-size:14px;font-weight:600}#ohlc{padding:4px 10px;font-size:12px;min-height:20px;font-variant-numeric:tabular-nums}#chart-wrap{position:relative;width:100%;height:480px}#chart{width:100%;height:480px;touch-action:pan-y}#box-overlay{position:absolute;inset:0;width:100%;height:480px;pointer-events:none;z-index:2}
#hint{font-size:12px;opacity:.8;padding:6px 10px}#error{color:#ff7777;padding:12px}</style></head>
<body><div id="heading"></div><div id="renderer-status" style="padding:4px 10px;font-size:12px;color:#65d6a5">手機圖表版本 VOL-OHLC-1｜箱型＋量能</div><div id="ohlc">移動十字游標查看開高低收及成交量｜成交量資料：Yahoo Finance（台股單位：張）</div><div id="chart-wrap"><div id="chart"></div><svg id="box-overlay" aria-hidden="true"></svg></div><div id="hint">雙指縮放｜單指左右拖曳｜點選 K 棒查看價格</div><div id="error"></div>
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
 const volume=chart.addHistogramSeries({priceScaleId:'volume',priceFormat:{type:'volume'},priceLineVisible:false,lastValueVisible:false});
 volume.setData(data.volumes);
 chart.priceScale('volume').applyOptions({scaleMargins:{top:0.76,bottom:0.01},visible:false});
 chart.priceScale('right').applyOptions({scaleMargins:{top:0.04,bottom:0.28}});
 for(const [points,color] of [[data.volumeMA5,'#ffca28'],[data.volumeMA20,'#42a5f5']]){
   if(!points.length)continue;
   const ma=chart.addLineSeries({priceScaleId:'volume',color,lineWidth:1,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false});
   ma.setData(points);
 }
 const byTime=new Map(data.bars.map((b,i)=>[b.time,{...b,volume:data.volumes.find(v=>v.time===b.time)?.value,prev:i?data.bars[i-1].close:null}]));
 const fmt=v=>Number.isFinite(v)?v.toLocaleString('zh-TW',{maximumFractionDigits:2}):'—';
 const showBar=b=>{
   if(!b)return;
   const pct=b.prev?((b.close/b.prev-1)*100):null;
   document.getElementById('ohlc').textContent=
     new Date(b.time*1000).toLocaleDateString('zh-TW',{timeZone:'Asia/Taipei'})+
     '  開 '+fmt(b.open)+'  高 '+fmt(b.high)+'  低 '+fmt(b.low)+
     '  收 '+fmt(b.close)+'  漲跌 '+(pct===null?'—':pct.toFixed(2)+'%')+
     '  量 '+fmt(b.volume)+' '+data.volumeUnit;
 };
 showBar(data.bars[data.bars.length-1]);
 chart.subscribeCrosshairMove(param=>{
   if(!param.time)return;
   showBar(byTime.get(typeof param.time==='number'?param.time:null));
 });
 for(const line of data.lines){
  if(!line.points.length)continue;
  const l=chart.addLineSeries({color:line.color,lineWidth:line.style===2?3:(line.style===1?1:2),
   lineStyle:line.style===2?LightweightCharts.LineStyle.Dashed:(line.style===1?LightweightCharts.LineStyle.Dotted:LightweightCharts.LineStyle.Solid),
   title:line.name||'',priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false});
  l.setData(line.points);
 }
 // Draw translucent rectangles on a pointer-transparent SVG; never intercept chart gestures.
 const overlay=document.getElementById('box-overlay');
 const svgNS='http://www.w3.org/2000/svg';
 let boxFrame=0;
 function drawBoxRectangles(){
   boxFrame=0;
   overlay.replaceChildren();
   const width=document.getElementById('chart').clientWidth;
   overlay.setAttribute('viewBox','0 0 '+width+' 480');
   if(!data.boxes || !data.boxes.length)return;
   for(const b of data.boxes){
     const x1=chart.timeScale().timeToCoordinate(b.start);
     const x2=chart.timeScale().timeToCoordinate(b.end);
     const y1=candle.priceToCoordinate(b.top);
     const y2=candle.priceToCoordinate(b.bottom);
     if([x1,x2,y1,y2].some(v=>v===null || !Number.isFinite(v)))continue;
     const left=Math.min(x1,x2),top=Math.min(y1,y2);
     const rect=document.createElementNS(svgNS,'rect');
     rect.setAttribute('x',left);rect.setAttribute('y',top);
     rect.setAttribute('width',Math.max(1,Math.abs(x2-x1)));
     rect.setAttribute('height',Math.max(1,Math.abs(y2-y1)));
     rect.setAttribute('fill',b.status==='整理中'?'rgba(53,160,245,0.13)':'rgba(53,160,245,0.09)');
     rect.setAttribute('stroke','#52a9ff');
     rect.setAttribute('stroke-width','1');
     overlay.appendChild(rect);
   }
 }
 function queueBoxDraw(){
   if(!boxFrame)boxFrame=requestAnimationFrame(drawBoxRectangles);
 }
 chart.timeScale().subscribeVisibleLogicalRangeChange(queueBoxDraw);
 const chartElement=document.getElementById('chart');
 chartElement.addEventListener('wheel',queueBoxDraw,{passive:true});
 chartElement.addEventListener('pointermove',queueBoxDraw,{passive:true});
 chartElement.addEventListener('touchmove',queueBoxDraw,{passive:true});
 queueBoxDraw();
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
 const resize=new ResizeObserver(()=>{chart.applyOptions({width:document.getElementById('chart').clientWidth});queueBoxDraw();});
 resize.observe(document.getElementById('chart'));
}
</script></body></html>"""
    html = html.replace("BG", "#101010" if dark else "#ffffff").replace(
        "FG", "#ffffff" if dark else "#222222").replace("PAYLOAD", payload)
    components.html(html, height=585, scrolling=False)
