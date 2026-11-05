"""Post-breakout tracking for causal consolidation boxes (test branch only)."""
import pandas as pd

def track_latest_breakout(df, boxes, retest_pct=1.0):
    """Track the most recent broken box using closes AFTER its breakout bar."""
    if df is None or not boxes:
        return None
    closes = pd.to_numeric(df["Close"], errors="coerce")
    broken = next((b for b in reversed(boxes)
                   if b["status"] in ("上破", "下破") and b["end"] + 1 < len(df)), None)
    if broken is None:
        return None
    idx = broken["end"] + 1
    top, bottom = float(broken["top"]), float(broken["bottom"])
    direction = broken["status"]
    level = top if direction == "上破" else bottom
    height = top - bottom
    target = top + height if direction == "上破" else bottom - height
    latest = float(closes.iloc[-1])
    post = closes.iloc[idx:]
    # The first closing re-entry invalidates the original breakout, even if price exits again.
    inside = post.between(bottom, top, inclusive="both")
    reentered = bool(inside.any())
    reentry_date = df.index[idx + int(inside.to_numpy().argmax())] if reentered else None
    if reentered:
        status = "突破失敗／曾收回箱內"
    elif direction == "上破":
        status = "回測箱頂附近" if abs(latest - top) / top * 100 <= retest_pct else "向上突破後追蹤"
    else:
        status = "反彈測試箱底附近" if abs(latest - bottom) / bottom * 100 <= retest_pct else "向下跌破後追蹤"
    return {
        "direction": direction, "status": status,
        "breakout_date": pd.Timestamp(df.index[idx]).strftime("%Y-%m-%d"),
        "breakout_close": float(closes.iloc[idx]),
        "box_top": top, "box_bottom": bottom, "breakout_level": level,
        "target": target, "latest_close": latest,
        "reentered": reentered,
        "reentry_date": pd.Timestamp(reentry_date).strftime("%Y-%m-%d") if reentry_date is not None else None,
    }
