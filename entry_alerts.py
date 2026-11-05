"""Causal, user-configurable daily observation rules; never place orders."""
from dataclasses import dataclass, asdict
import hashlib
import json
import numpy as np
import pandas as pd
from box_theory import detect_boxes
from quote_quality import invalid_price_rows


class EntryDataError(ValueError):
    """Controlled explanation containing public OHLC evidence only."""
    def __init__(self, records):
        super().__init__("行情品質異常，未產生提醒")
        self.records = records


@dataclass(frozen=True)
class AlertSettings:
    box_window: int = 20
    box_width_pct: float = 20.
    near_bottom_pct: float = 3.
    rebound_pct: float = .5
    breakout_buffer_pct: float = .5
    breakout_max_pct: float = 5.
    volume_ratio: float = 1.5
    min_average_lots: float = 1000.

    def validate(self):
        if not 10 <= self.box_window <= 60:
            raise ValueError("箱型觀察根數需介於10至60")
        values = asdict(self)
        if not all(np.isfinite(float(v)) and float(v) >= 0 for v in values.values()):
            raise ValueError("提醒參數需為有限非負數")
        if not 0 < self.box_width_pct <= 25 or not 0 < self.near_bottom_pct <= 20:
            raise ValueError("箱型振幅或距箱底門檻超出範圍")
        if not 0 <= self.breakout_buffer_pct < self.breakout_max_pct <= 20:
            raise ValueError("突破確認幅度需小於最大追蹤幅度，且上限不超過20%")


def evaluate_entry_alerts(frame, symbol, as_of, settings=None, rules=("箱底反彈", "箱頂突破")):
    settings = settings or AlertSettings()
    settings.validate()
    if any(rule not in ("箱底反彈", "箱頂突破") for rule in rules):
        raise ValueError("未知提醒條件")
    data = frame.copy(deep=True)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    required = ["Open", "High", "Low", "Close", "Volume"]
    if any(col not in data for col in required) or len(data) < max(21, settings.box_window+1):
        raise ValueError("行情欄位或歷史根數不足")
    index = pd.to_datetime(data.index)
    if index.tz is not None:
        index = index.tz_convert("Asia/Taipei").tz_localize(None)
    data.index = index
    if not data.index.is_monotonic_increasing or data.index.has_duplicates:
        raise ValueError("行情時間重複或未排序")
    if str(data.index[-1].date()) != str(as_of):
        raise ValueError("行情不是指定日期，未產生提醒")
    data[required] = data[required].apply(pd.to_numeric, errors="coerce")
    bad_prices = invalid_price_rows(data)
    if bad_prices:
        raise EntryDataError(bad_prices)
    if not np.isfinite(data.Volume.to_numpy(dtype=float)).all() or (data.Volume < 0).any():
        raise ValueError("行情品質異常，未產生提醒")
    # The box and volume baseline must exist BEFORE the signal candle.
    prior = data.iloc[:-1]
    boxes = detect_boxes(prior, window=settings.box_window, max_width_pct=settings.box_width_pct, max_boxes=5)
    box = next((b for b in reversed(boxes) if b["status"] == "整理中" and b["end"] == len(prior)-1), None)
    if box is None:
        return []
    average = float(prior.Volume.tail(20).mean())
    if average <= 0 or average/1000 < settings.min_average_lots:
        return []
    last = data.iloc[-1]
    close, previous = float(last.Close), float(prior.Close.iloc[-1])
    top, bottom = float(box["top"]), float(box["bottom"])
    ratio = float(last.Volume)/average
    triggered = []
    if ("箱底反彈" in rules and bottom <= previous <= bottom*(1+settings.near_bottom_pct/100)
            and bottom <= close <= top and close >= previous*(1+settings.rebound_pct/100)
            and close > float(last.Open)):
        triggered.append(("箱底反彈", f"前收盤距既有箱底{(previous/bottom-1)*100:.2f}%，本日上漲{(close/previous-1)*100:.2f}%且收高於開盤"))
    if ("箱頂突破" in rules and top*(1+settings.breakout_buffer_pct/100) <= close <= top*(1+settings.breakout_max_pct/100)
            and ratio >= settings.volume_ratio):
        triggered.append(("箱頂突破", f"收盤高於既有箱頂{(close/top-1)*100:.2f}%，成交量為前20日均量{ratio:.2f}倍"))
    events = []
    config = {"settings": asdict(settings), "rules": sorted(set(rules)), "version": "ENTRY-1"}
    config_id = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()[:12]
    for rule, reason in triggered:
        event_id = hashlib.sha256(f"{symbol}|{as_of}|{rule}|{config_id}".encode()).hexdigest()[:24]
        events.append({"提醒編號": event_id, "股票": symbol, "條件": rule, "行情日期": str(as_of),
                       "觀察價": round(close, 4), "既有箱底": round(bottom, 4), "既有箱頂": round(top, 4),
                       "相對成交量": round(ratio, 2), "前20日均量（張）": round(average/1000, 2),
                       "觸發原因": reason, "參數版本": config_id})
    return events


def telegram_text(event):
    label = event["股票"] + (" " + event["名稱"] if event.get("名稱") else "")
    return (f"亞當鏡像｜進場觀察提醒\n{label}｜{event['條件']}\n"
            f"行情日期：{event['行情日期']}（收盤日K）\n觀察價：{event['觀察價']:,.2f}\n"
            f"既有箱底／箱頂：{event['既有箱底']:,.2f}／{event['既有箱頂']:,.2f}\n"
            f"原因：{event['觸發原因']}\n編號：{event['提醒編號']}\n"
            "條件到達提醒，不代表保證上漲；非自動下單。")

