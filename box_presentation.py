"""Presentation of independently detected bar-window boxes; no trading-rule changes."""
from box_theory import detect_boxes

PALETTE = ("#22d3ee", "#f59e0b")


def box_layers(df, short_window=10, large_window=60, max_width_pct=20.0, history=False):
    if not 3 <= short_window < large_window <= 2500:
        raise ValueError("箱型根數需符合 3 ≤ 小區間 < 大區間 ≤ 2500")
    layers, overview = [], []
    for rank, (name, window) in enumerate((("小區間", short_window), ("大區間", large_window))):
        boxes = detect_boxes(df, window, max_width_pct, max_boxes=5)
        active = next((b for b in reversed(boxes)
                       if b["status"] == "整理中" and b["end"] == len(df)-1), None)
        overview.append({"name": name, "window": window, "active": active,
                         "history": boxes, "color": PALETTE[rank]})
        selected = boxes[-3:] if history else ([active] if active else [])
        for box in selected:
            confirmed = box["start"] + window - 1
            # A box is knowable only once its formation window is complete.
            if confirmed > box["end"]:
                continue
            current = box is active
            layers.append({**box, "name": name, "window": window,
                           "confirmed": confirmed, "active": current,
                           "break_index": box["end"]+1 if box["status"] != "整理中" else None,
                           "color": PALETTE[rank],
                           "label": f'{name} {window}根｜{"目前整理中" if current else "歷史"+box["status"]}'})
    # Coincident boundaries convey one shared range, not two independent confirmations.
    merged = []
    for layer in layers:
        same = next((b for b in merged if b["start"] == layer["start"]
                     and b["end"] == layer["end"] and b["top"] == layer["top"]
                     and b["bottom"] == layer["bottom"] and b["active"] == layer["active"]), None)
        if same:
            same["label"] += "／" + layer["label"]
        else:
            merged.append(layer)
    return merged, overview


def chart_box_payload(df, **options):
    layers, overview = box_layers(df, **options)
    result = []
    for box in layers:
        result.append({**box, "start": int(df.index[box["start"]].timestamp()),
                       "end": int(df.index[box["end"]].timestamp()),
                       "formed_date": str(df.index[box["confirmed"]].date())})
    return result, overview


def add_plotly_boxes(fig, df, **options):
    layers, _ = box_layers(df, **options)
    for b in layers:
        color = b["color"] if b["active"] else "#94a3b8"
        x0, x1 = df.index[b["start"]], df.index[b["end"]]
        fig.add_shape(type="rect", x0=x0, x1=x1, y0=b["bottom"], y1=b["top"],
                      line=dict(color=color, width=2 if b["active"] else 1,
                                dash="solid" if b["active"] else "dash"),
                      fillcolor=color, opacity=.12 if b["active"] else .04, layer="below")
        fig.add_scatter(x=[x0,x1], y=[b["mid"],b["mid"]], mode="lines",
                        line=dict(color=color,width=1,dash="dot"),
                        opacity=.6 if b["active"] else .25,showlegend=False,hoverinfo="skip")
        # One legend/hover item per box; no stack of permanent price labels.
        fig.add_scatter(x=[x0,x1,x1,x0,x0],
                        y=[b["bottom"],b["bottom"],b["top"],b["top"],b["bottom"]],
                        mode="lines", name=b["label"],
                        line=dict(color=color, width=2 if b["active"] else 1,
                                  dash="solid" if b["active"] else "dash"),
                        opacity=1 if b["active"] else .45,
                        hovertemplate=b["label"]+"<br>形成："+str(df.index[b["confirmed"]].date())+
                        f'<br>上緣 {b["top"]:,.2f}／下緣 {b["bottom"]:,.2f}<extra></extra>')
    return fig


def show_box_overview(df, interval_name="", **options):
    import pandas as pd
    import streamlit as st
    _, overview = box_layers(df, **options)
    st.subheader("大小區間箱型｜目前有效狀態")
    rows = []
    for item in overview:
        b = item["active"]
        rows.append({"區間": f'{item["name"]} {item["window"]}根 {interval_name}',
                     "狀態": "目前箱內整理" if b else "沒有目前有效箱型",
                     "形成日": str(df.index[b["start"]+item["window"]-1].date()) if b else "—",
                     "上緣": round(b["top"],2) if b else None,
                     "下緣": round(b["bottom"],2) if b else None})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.caption("青色＝小區間；橙色＝大區間。同一K線週期的不同觀察根數，並非多週期共振。"
               "箱頂／底在形成時固定；收盤越界即上破／下破。突破當根起須重新累積完整觀察根數，才形成新箱。盤中K線狀態仍可能變動。"
               "歷史框不代表目前有效支撐；跌破後轉壓力仍須另行確認回測。")

    if options.get("history"):
        with st.expander("大小區間歷史箱型｜形成與突破紀錄", expanded=False):
            history_rows = []
            for item in overview:
                for b in item["history"][-3:]:
                    break_i = b["end"]+1 if b["status"] != "整理中" else None
                    history_rows.append({
                        "區間": f'{item["name"]} {item["window"]}根',
                        "形成日": str(df.index[b["start"]+item["window"]-1].date()),
                        "狀態": b["status"], "上緣": b["top"], "下緣": b["bottom"],
                        "突破日": str(df.index[break_i].date()) if break_i is not None else "—"})
            if history_rows:
                st.dataframe(pd.DataFrame(history_rows),use_container_width=True,hide_index=True)
            else:
                st.info("沒有符合目前參數的歷史箱型。")
