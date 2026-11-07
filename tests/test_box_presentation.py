"""Regression cases for current versus historical box presentation."""
import json
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from box_presentation import box_layers, chart_box_payload, add_plotly_boxes


def frame(n=90):
    return pd.DataFrame({"Open": np.full(n,100.), "High":np.full(n,101.),
                         "Low":np.full(n,99.), "Close":np.full(n,100.),
                         "Volume":np.full(n,100000.)},
                        index=pd.date_range("2025-01-01",periods=n,freq="B"))


class BoxPresentationTests(unittest.TestCase):
    def test_default_never_displays_broken_history_as_active(self):
        df=frame()
        df.iloc[-1]=[96,97,94,95,100000]
        layers, overview=box_layers(df)
        self.assertEqual(layers, [])
        self.assertTrue(all(item["active"] is None for item in overview))
        historical,_=box_layers(df,history=True)
        self.assertTrue(historical)
        self.assertTrue(all(not b["active"] and b["status"]=="下破" for b in historical))
        self.assertTrue(all(b["break_index"]==len(df)-1 for b in historical))

    def test_current_box_has_known_formation_and_no_future_break(self):
        df=frame()
        layers,overview=box_layers(df)
        self.assertEqual(len(layers),1)  # coincident ranges are drawn just once
        self.assertIn("小區間",layers[0]["label"])
        self.assertIn("大區間",layers[0]["label"])
        for item in overview:
            b=item["active"]
            self.assertIsNotNone(b)
            self.assertEqual(b["end"],89)
            self.assertLessEqual(b["start"]+item["window"]-1,b["end"])
        self.assertNotEqual(overview[0]["color"],overview[1]["color"])

    def test_insufficient_large_window_does_not_invent_box(self):
        _,overview=box_layers(frame(20))
        self.assertIsNotNone(overview[0]["active"])
        self.assertIsNone(overview[1]["active"])
        self.assertEqual(box_layers(frame(2))[0],[])

    def test_intraday_wick_is_not_a_close_break(self):
        df=frame()
        df.loc[df.index[-1],"Low"]=90.
        layers,_=box_layers(df)
        self.assertTrue(layers)
        self.assertTrue(all(b["active"] for b in layers))

    def test_boundaries_freeze_before_later_break(self):
        prefix=frame(70)
        b=box_layers(prefix)[1][0]["active"]
        later=frame(71)
        later.iloc[-1]=[104,106,103,105,100000]
        old=box_layers(later,history=True)[1][0]["history"][0]
        self.assertEqual((b["top"],b["bottom"]),(old["top"],old["bottom"]))
        self.assertEqual(old["status"],"上破")

    def test_payload_and_plotly_identify_status_without_price_label_stack(self):
        df=frame()
        payload,_=chart_box_payload(df)
        self.assertEqual(payload[0]["formed_date"],str(df.index[9].date()))
        fig=add_plotly_boxes(go.Figure(),df)
        self.assertEqual(len(fig.data),2*len(payload))
        self.assertFalse(fig.layout.annotations)
        self.assertTrue(all("目前整理中" in t.name for t in fig.data if t.showlegend is not False))

    def test_next_box_requires_full_window_after_break(self):
        from box_theory import detect_boxes
        df=frame(20)
        df.iloc[10:]=[96,97,94,95,100000]
        just_broke=detect_boxes(df.iloc[:11],window=10,max_width_pct=20)
        self.assertEqual(len(just_broke),1)
        self.assertEqual(just_broke[-1]["status"],"下破")
        not_ready=detect_boxes(df.iloc[:19],window=10,max_width_pct=20)
        self.assertEqual(len(not_ready),1)
        ready=detect_boxes(df,window=10,max_width_pct=20)
        self.assertEqual(len(ready),2)
        self.assertEqual(ready[-1]["start"],10)
        self.assertEqual(ready[-1]["status"],"整理中")
        self.assertEqual(ready[-1]["bottom"],94)

    def test_invalid_horizon_order(self):
        with self.assertRaises(ValueError):
            box_layers(frame(),short_window=60,large_window=60)

    def test_mobile_enhanced_history_and_mirror_style(self):
        import mobile_chart
        df=frame()
        wave={"name":"長波","color":"#ef4444","projection":[100.,99.],
              "times":pd.date_range(df.index[-1],periods=2,freq="B"),
              "recent":df,"start":0,"end":1,"segment":[100.,100.]}
        with patch.object(mobile_chart.components,"html") as render:
            mobile_chart.mobile_chart(df,[wave],"最近60根","TEST",auto_boxes=True,
                                      box_options=dict(short_window=10,large_window=60))
        html=render.call_args.args[0]
        payload=json.loads(html.split("const data=",1)[1].split(";\ndocument",1)[0])
        self.assertTrue(payload["enhancedBoxes"])
        self.assertTrue(all(b["active"] for b in payload["boxes"]))
        self.assertEqual([l["style"] for l in payload["lines"] if l.get("mirrorWave")],[2])
        self.assertIn("stroke-dasharray",html)
        with patch.object(mobile_chart.components,"html") as render:
            mobile_chart.mobile_chart(df,[],"最近60根","TEST",auto_boxes=True)
        payload=json.loads(render.call_args.args[0].split("const data=",1)[1].split(";\ndocument",1)[0])
        self.assertFalse(payload["enhancedBoxes"])  # production-compatible default


if __name__=="__main__":
    unittest.main()
