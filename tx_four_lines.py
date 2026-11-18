"""Point-in-time four-line observations for a fixed-contract TAIFEX replay."""
import csv
from pathlib import Path


def read_replay_bars():
    """Read the verified TX 202611 bars, keyed by local bar closing time."""
    with Path(__file__).with_name("tx_four_lines_202611.csv").open(encoding="utf-8", newline="") as source:
        return [
            {**row, **{key: int(row[key]) for key in ("open", "high", "low", "close", "trades", "minutes")}}
            for row in csv.DictReader(source)
        ]


def reaction(bar, inner, outer, direction):
    if outer is None:
        return "outer_missing"
    close = bar["close"]
    if direction * (close - outer) > 0:
        return "close_outside"
    extreme = bar["high" if direction == 1 else "low"]
    if direction * (extreme - outer) > 0:
        return "wick_return"
    if direction * (extreme - inner) >= 0:
        return "touch"
    return "no_touch"


def outer(history, inner, side):
    field = "high" if side == 1 else "low"
    for i in range(len(history)-3, 1, -1):
        pivot = history[i][field]
        if side*(pivot-inner)>0 and all(side*(pivot-b[field])>0 for b in history[i-2:i]+history[i+1:i+3]):
            return pivot, history[i]["time"]
    return None, None

def classify(bar, inner, edge, side, previous):
    if not bar["trades"]:
        return "missing_bar", 0
    if edge is not None and bar["close"] == edge:
        return "touch", 0
    event = reaction(bar, inner, edge, side)
    return event, previous+1 if event == "close_outside" else 0

def replay(data):
    history = []
    formation = []
    zone = None
    streak = {1:0,-1:0}
    rows = []
    for bar in data:
        row = dict(bar)
        for side, label in ((1,"upper"),(-1,"lower")):
            state = "no_confirmed_box"
            if not bar["trades"]:
                state = "missing_bar"
            elif zone:
                inner, edge, pivot_time = zone[side]
                state, streak[side] = classify(bar,inner,edge,side,streak[side])
                row.update({label+"_inner":inner,label+"_outer":edge,label+"_pivot":pivot_time,
                            label+"_one":streak[side]==1,label+"_two":streak[side]==2})
            row[label+"_event"] = state
        rows.append(row)
        if not bar["trades"]:
            history, formation, zone = [], [], None
            streak = {1:0,-1:0}
            continue
        # Once the inner box breaks, keep its four-line reference until a new box forms.
        if not formation and zone and zone[-1][0] <= bar["close"] <= zone[1][0] and not zone["broken"]:
            history.append(bar)
            continue
        if zone:
            zone["broken"] = True
        formation.append(bar)
        history.append(bar)
        if len(formation) == 20:
            hi,lo = max(b["high"] for b in formation),min(b["low"] for b in formation)
            if (hi-lo)/lo <= .20:
                zone = {side:(inner,*outer(history[:-20],inner,side))
                        for side,inner in ((1,hi),(-1,lo))}
                zone["broken"] = False
                streak = {1:0,-1:0}
                formation = []
            else:
                formation.pop(0)
    return rows
