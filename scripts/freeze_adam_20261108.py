"""One-off pre-open snapshot of exact production mirror engine; never sends alerts."""
import ast
import csv
import hashlib
import io
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import yfinance as yf

VERSION = '8b6cefc70a84a856b793f29df2553f0e00a248b6'
CUTOFF = pd.Timestamp('2026-11-06')
DEADLINE = datetime(2026, 11, 9, 9, tzinfo=ZoneInfo('Asia/Taipei'))
COHORT = [('2887', '台新新光金', 37.349998474121094, 44.79999923706055),
          ('2002', '中鋼', 18.049999237060547, 19.950000762939453),
          ('2834', '臺企銀', 16.850000381469727, 18.799999237060547)]
ROOT = Path(__file__).resolve().parents[1]
PROD = ROOT / 'production-source'
OUT = ROOT / 'forecast-output'
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(PROD))


def now():
    value = datetime.now(ZoneInfo('Asia/Taipei'))
    if value >= DEADLINE:
        raise RuntimeError('Past pre-open deadline; no ex-ante baseline may be created')
    return value.isoformat()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def write_json(name, value):
    data = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()
    with (OUT / name).open('xb') as f:
        f.write(data)
    return digest(data)


def engine():
    tree = ast.parse((PROD / 'app.py').read_text(encoding='utf-8'))
    names = {'audit_ohlc_data', 'raw_quote_summary', 'get_data', 'get_analysis_data',
             'find_pivots', 'future_index', 'internal_turns', 'mirror_wave'}
    selected = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in {'WAVES', 'COLORS'} for t in node.targets):
            selected.append(node)
        if isinstance(node, ast.FunctionDef) and node.name in names:
            node.decorator_list = []
            selected.append(node)
    if len([n for n in selected if isinstance(n, ast.FunctionDef)]) != len(names):
        raise RuntimeError('Production engine extraction incomplete')
    raw_download = yf.download

    def capture(symbol, **kwargs):
        frame = raw_download(symbol, **kwargs)
        frame.to_csv(OUT / f'{symbol}_{kwargs["interval"]}_download-original.csv')
        return frame

    scope = {'np': np, 'pd': pd, 'yf': SimpleNamespace(download=capture)}
    exec(compile(ast.Module(body=selected, type_ignores=[]), 'production-engine', 'exec'), scope)
    assert scope['WAVES'] == {'短波': (3, 100), '中波': (7, 260), '長波': (14, 650)}
    return scope


def official(code):
    url = f'https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY?date=20261101&stockNo={code}&response=json'
    with urlopen(Request(url, headers={'User-Agent': 'AdamResearch/1.0'}), timeout=25) as response:
        raw = response.read()
    (OUT / f'{code}_official-month.json').write_bytes(raw)
    value = json.loads(raw)
    if value.get('stat') != 'OK' or code not in value.get('title', ''):
        raise ValueError('Official month identity/status mismatch')
    fields = value['fields']
    expected = ['日期', '成交股數', '成交金額', '開盤價', '最高價', '最低價', '收盤價']
    if fields[:7] != expected:
        raise ValueError('Official schema changed')
    dates = []
    rows = {}
    for row in value['data']:
        year, month, day = map(int, row[0].split('/'))
        date = pd.Timestamp(year=year+1911, month=month, day=day)
        if date in rows:
            raise ValueError('Duplicate official date')
        dates.append(date)
        rows[date] = row
    if max(dates) != CUTOFF:
        raise ValueError(f'Latest official date not cutoff: {max(dates)}')
    values = [float(str(x).replace(',', '')) for x in rows[CUTOFF][3:7]]
    return dict(zip(['Open', 'High', 'Low', 'Close'], values)), {'url': url, 'sha256': digest(raw), 'latest_date': str(CUTOFF.date())}


def mirror_record(result, frame, interval, settings):
    if result is None:
        return {'status': '無法預測', 'reason': '轉折數不足', 'settings': settings}
    segment = result['segment']
    projection = result['projection']
    latest = float(frame.Close.iloc[-1])
    expected = latest + segment[::-1] - segment[-1]
    if not np.isfinite(projection).all() or not np.allclose(projection, expected, rtol=0, atol=1e-9):
        raise ValueError('Projection formula verification failed')
    times = result['times']
    if len(times) != len(projection) or not times.is_monotonic_increasing or len(projection) < 2:
        raise ValueError('Projection time/length verification failed')
    recent = result['recent']
    source_dates = recent.index[result['start']:result['end']+1]
    complete = len(frame) >= settings[1]
    finite_positive = bool((projection > 0).all())
    first = float(projection[1])
    delta = (first/latest-1)*100
    return {'status': '可核對情境' if complete and finite_positive else '無法預測',
        'reason': None if complete and finite_positive else ('觀察根數不足' if not complete else '存在非正投影'),
        'settings': {'pivot_span': settings[0], 'lookback_requested': settings[1], 'lookback_actual': len(recent)},
        'source_start': str(source_dates[0]), 'source_end': str(source_dates[-1]),
        'source_closes': [float(x) for x in segment], 'source_dates': [str(x) for x in source_dates],
        'anchor_date_label': str(frame.index[-1]), 'anchor_close': latest,
        'path': [{'date_label': str(t), 'price': float(p)} for t,p in zip(times, projection)],
        'first_future_price': first,
        'first_future_direction': '上' if delta > .5 else '下' if delta < -.5 else '盤整',
        'close_tolerance_abs': latest*.01,
        'first_point_due': '下一實際交易日（預期2026-11-09）' if interval == '1d' else '下一完整週K，11/09未到期',
        'terminal': {'date_label': str(times[-1]), 'price': float(projection[-1]), 'due_after_future_bars': len(projection)-1},
        'high': {'date_label': str(times[int(np.argmax(projection))]), 'price': float(np.max(projection))},
        'low': {'date_label': str(times[int(np.argmin(projection))]), 'price': float(np.min(projection))},
        'limitations': ['日期為正式版示意刻度，非完整交易日曆', '歷史情境不是已驗證未來預測或勝率',
                        '資料品質通過不代表歷史交易日／公司行動已全部認證', '未到期整段不以一天判成敗']}


def main():
    created = now()
    scope = engine()
    protocol = (ROOT / 'docs/evidence/forecast-20261108/PROTOCOL.txt').read_bytes()
    baseline = {'created_at_taipei': created, 'cutoff': '2026-11-06', 'expected_next_session': '2026-11-09',
        'production_commit': VERSION, 'production_app_sha256': digest((PROD/'app.py').read_bytes()),
        'protocol_sha256': digest(protocol), 'threshold_pct': 3, 'period': '10y',
        'scope': '固定20檔複選的3檔觀察；未掃描其餘1943檔，不依鏡像終點排名',
        'no_schedule_created_or_changed': True, 'stocks': []}
    for code, name, bottom, top in COHORT:
        item = {'code': code, 'symbol': code+'.TW', 'name': name,
                'frozen_screen_box': {'bottom': bottom, 'top': top, 'window': 20, 'max_width_pct': 20,
                                     'invalidation': '下一交易日官方收盤嚴格低於凍結箱底；不刪除鏡像評分'},
                'intervals': {}}
        try:
            quote, evidence = official(code)
            item['official_ohlc'] = quote
            item['official_evidence'] = evidence
            for interval in ('1d', '1wk'):
                try:
                    frame = scope['get_analysis_data'](code+'.TW', '10y', interval)
                    if frame.empty or frame.index.max() > CUTOFF:
                        raise ValueError('Empty or post-cutoff bars')
                    if interval == '1d' and frame.index[-1] != CUTOFF:
                        raise ValueError('Daily data stale')
                    if interval == '1wk' and not (CUTOFF - pd.Timedelta(days=6) <= frame.index[-1] <= CUTOFF):
                        raise ValueError('Weekly data stale')
                    if abs(float(frame.Close.iloc[-1])-quote['Close']) > .005:
                        raise ValueError('Latest close differs from official cutoff')
                    if interval == '1d' and any(abs(float(frame[k].iloc[-1])-quote[k]) > .005 for k in ('Open','High','Low','Close')):
                        raise ValueError('Latest daily OHLC differs from official cutoff')
                    if frame.attrs.get('official_close_verification'):
                        write_json(f'{code}_official-close-verification.json', frame.attrs['official_close_verification'])
                    frame.to_csv(OUT / f'{code}_{interval}_analysis.csv')
                    # Never truncate the full request to make invalid OHLC pass.
                    issues = scope['audit_ohlc_data'](frame)
                    if issues:
                        raise ValueError('; '.join(issues))
                    info = {'status': '價格品質通過', 'rows': len(frame), 'first_date_label': str(frame.index[0]),
                            'last_date_label': str(frame.index[-1]), 'waves': {}}
                    for wave, settings in scope['WAVES'].items():
                        info['waves'][wave] = mirror_record(scope['mirror_wave'](frame, wave, 3, interval), frame, interval, settings)
                    sources = [(k,v.get('source_start'),v.get('source_end')) for k,v in info['waves'].items()]
                    info['shared_source_groups'] = [[a[0], b[0]] for i,a in enumerate(sources) for b in sources[i+1:]
                                                   if a[1] and a[1:] == b[1:]]
                    item['intervals'][interval] = info
                except Exception as exc:
                    item['intervals'][interval] = {'status': '無法預測', 'reason': str(exc)}
        except Exception as exc:
            item['status'] = '無法預測'
            item['reason'] = str(exc)
        baseline['stocks'].append(item)
        time.sleep(3)
    baseline['sealed_at_taipei'] = now()
    baseline['counts'] = {'stocks': len(baseline['stocks']), 'daily_available': sum(
        x['intervals'].get('1d', {}).get('status') == '價格品質通過' for x in baseline['stocks'])}
    baseline_hash = write_json('baseline-20261108.json', baseline)
    rows = []
    for stock in baseline['stocks']:
        for interval, result in stock['intervals'].items():
            for name, wave in result.get('waves', {}).items():
                rows.append({'code': stock['code'], 'name': stock['name'], 'interval': interval, 'wave': name,
                    'status': wave['status'], 'anchor': wave.get('anchor_close'), 'next_price': wave.get('first_future_price'),
                    'direction': wave.get('first_future_direction'), 'tolerance': wave.get('close_tolerance_abs'),
                    'due': wave.get('first_point_due'), 'reason': wave.get('reason')})
    with (OUT/'baseline-20261108.csv').open('x', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ['status'])
        writer.writeheader(); writer.writerows(rows)
    write_json('SHA256-manifest.json', {p.name:digest(p.read_bytes()) for p in sorted(OUT.iterdir()) if p.is_file()})
    print(json.dumps({'created':created, 'sealed':baseline['sealed_at_taipei'], 'counts':baseline['counts'], 'baseline_sha256':baseline_hash},ensure_ascii=False))


if __name__ == '__main__':
    main()
