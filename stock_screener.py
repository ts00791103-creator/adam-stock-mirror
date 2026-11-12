"""Watchlist screening using historical daily bars, with explicit data failures."""
import re
import numpy as np
import pandas as pd
from box_theory import detect_boxes


def resolve_watchlist(text, stock_list, limit=30):
    lookup = {}
    for code, name, exchange in stock_list:
        lookup.setdefault(code, []).append((code, name, exchange))
        lookup.setdefault(name, []).append((code, name, exchange))
    items, errors, seen = [], [], set()
    tokens = [x for x in re.split(r"[\s,，、;；]+", text.strip()) if x]
    for token in tokens:
        match = re.fullmatch(r"(\d{4,6})\.(TW|TWO)", token.upper())
        if match:
            code, suffix = match.groups()
            exchange = "上市" if suffix == "TW" else "上櫃"
            candidates = [r for r in lookup.get(code, []) if r[2] == exchange]
            item = candidates[0] if candidates else (code, code, exchange)
        else:
            candidates = list(dict.fromkeys(lookup.get(token, [])))
            if len(candidates) != 1:
                errors.append({"輸入": token, "原因": "名稱或代號無法確認，請用完整名稱或代號.TW／.TWO"})
                continue
            item = candidates[0]
        symbol = item[0] + (".TW" if item[2] == "上市" else ".TWO")
        if symbol not in seen:
            seen.add(symbol)
            items.append((symbol, item[0], item[1], item[2]))
    if len(items) > limit:
        raise ValueError(f"最多 {limit} 檔；目前 {len(items)} 檔，請縮減名單後重試。")
    return items, errors


def screen_frame(frame, *, min_price=0, max_price=100000, min_lots=0,
                 mode="不限箱型", near_pct=5, window=20, width_pct=20):
    df = frame.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    required = ["Open", "High", "Low", "Close", "Volume"]
    if any(c not in df for c in required):
        raise ValueError("缺少價格或成交量欄位")
    df = df.sort_index()
    df = df[~df.index.duplicated(keep="last")]
    if len(df) < max(21, window):
        raise ValueError("日K不足，至少需要21根及完整箱型觀察根數")
    values = df[required].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(values.to_numpy(dtype=float)).all():
        raise ValueError("行情含缺值或無效數字")
    if (values[["Open", "High", "Low", "Close"]] <= 0).any().any() or (values.Volume < 0).any():
        raise ValueError("行情含無效價格或成交量")
    if ((values.High < values[["Open", "Low", "Close"]].max(axis=1)) |
            (values.Low > values[["Open", "High", "Close"]].min(axis=1))).any():
        raise ValueError("K線高低價不一致")
    df[required] = values
    close = float(df.Close.iloc[-1])
    avg_lots = float(df.Volume.tail(20).mean() / 1000)
    previous_volume = float(df.Volume.iloc[-21:-1].mean())
    ratio = float(df.Volume.iloc[-1] / previous_volume) if previous_volume > 0 else None
    boxes = detect_boxes(df, window=window, max_width_pct=width_pct, max_boxes=5)
    active = next((b for b in reversed(boxes) if b["status"] == "整理中" and b["end"] == len(df)-1), None)
    bottom = float(active["bottom"]) if active else None
    top = float(active["top"]) if active else None
    distance = (close / bottom - 1) * 100 if active else None
    if mode == "突破後收弱（試驗）":
        prior = df.iloc[:-1]
        prior_boxes = detect_boxes(prior, window=window, max_width_pct=width_pct, max_boxes=5)
        prior_box = next((box for box in reversed(prior_boxes)
                          if box["status"] == "整理中" and box["end"] == len(prior)-1), None)
        last = df.iloc[-1]
        day_range = float(last.High - last.Low)
        close_position = (close - float(last.Low)) / day_range if day_range > 0 else None
        matched = bool(prior_box and close_position is not None
                       and float(last.High) > prior_box["top"]
                       and prior_box["bottom"] <= close <= prior_box["top"]
                       and close_position <= 0.25
                       and min_price <= close <= max_price and avg_lots >= min_lots)
        return {"符合": matched, "資料日期": str(pd.Timestamp(df.index[-1]).date()),
                "收盤": close, "20日均量（張）": round(avg_lots, 2),
                "當日量／前20日均量": round(ratio, 2) if ratio is not None else None,
                "前日箱底": prior_box["bottom"] if prior_box else None,
                "前日箱頂": prior_box["top"] if prior_box else None,
                "日內收盤位置（%）": round(close_position * 100, 2) if close_position is not None else None,
                "箱型狀態": "突破後收弱（試驗）" if matched else "未觸發"}
    if mode not in ("不限箱型", "箱內整理", "接近箱底"):
        raise ValueError("不支援的箱型條件")
    matched = min_price <= close <= max_price and avg_lots >= min_lots
    if mode != "不限箱型":
        matched = matched and active is not None
    if mode == "接近箱底":
        matched = matched and distance is not None and 0 <= distance <= near_pct
    return {"符合": bool(matched), "資料日期": str(pd.Timestamp(df.index[-1]).date()),
            "收盤": close, "20日均量（張）": round(avg_lots, 2),
            "當日量／前20日均量": round(ratio, 2) if ratio is not None else None,
            "箱型狀態": "箱內整理" if active else "無有效整理箱型",
            "箱底": bottom, "箱頂": top,
            "距箱底（%）": round(distance, 2) if distance is not None else None}
