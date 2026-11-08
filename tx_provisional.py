"""Replay the provisional TX rule on ordered, closed 60-minute OHLC bars."""

def replay(bars):
    """Return frozen setups with their first close-based invalidation, if any."""
    pivots = {"high": None, "low": None}
    setups = []
    active = None
    for i, bar in enumerate(bars):
        if i >= 4:
            center = i - 2
            neighbors = (i - 4, i - 3, i - 1, i)
            previous_pivots = pivots.copy()
            for field, sign in (("high", 1), ("low", -1)):
                value = bars[center][field]
                if all(sign * value > sign * bars[j][field] for j in neighbors):
                    opposite = "low" if field == "high" else "high"
                    source = previous_pivots[opposite]
                    pivots[field] = dict(index=center, value=value, source=source, used=False)
        close = bar["close"]
        if active is not None:
            if active["sign"] * (close - active["level"]) <= 0:
                active["invalidated_at"] = i
                active = None
            continue
        if i == 0:
            continue
        previous = bars[i - 1]["close"]
        for field, sign in (("high", 1), ("low", -1)):
            pivot = pivots[field]
            if pivot is None or pivot["source"] is None or pivot["used"]:
                continue
            level = pivot["value"]
            if sign * (previous - level) <= 0 < sign * (close - level):
                source = pivot["source"]
                pivot["used"] = True
                active = dict(sign=sign, level=level, trigger_at=i,
                              source_start=source["index"], target=2 * close - source["value"],
                              invalidated_at=None)
                setups.append(active)
                break
    return setups
