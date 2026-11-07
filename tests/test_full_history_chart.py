"""The selected period must remain available while panning daily/weekly charts."""
import json
import unittest
import time
from unittest.mock import patch
import numpy as np
import pandas as pd
import mobile_chart


class FullHistoryChartTests(unittest.TestCase):
    def frame(self,n,freq="B"):
        close=100+np.arange(n)*.01
        return pd.DataFrame({"Open":close,"High":close+1,"Low":close-1,"Close":close,"Volume":1000000},
                            index=pd.date_range("2016-01-04",periods=n,freq=freq))

    def render(self,frame,**options):
        started=time.perf_counter()
        with patch.object(mobile_chart.components,"html") as output:
            mobile_chart.mobile_chart(frame,[],"最近60根","TEST",**options)
        html=output.call_args.args[0]
        self.render_metrics={"bars":len(frame),"full_history":bool(options.get("retain_history")),
                             "html_bytes":len(html.encode("utf-8")),"build_ms":round((time.perf_counter()-started)*1000,2)}
        return json.loads(html.split("const data=",1)[1].split(";\ndocument",1)[0])

    def test_full_daily_history_is_retained_with_the_same_latest_bars(self):
        data=self.frame(2500)
        original=data.copy(deep=True)
        legacy=self.render(data)
        full=self.render(data,retain_history=True)
        self.assertEqual(len(legacy["bars"]),300)
        self.assertEqual(len(full["bars"]),2500)
        self.assertEqual(full["bars"][-300:],legacy["bars"])
        self.assertEqual(full["bars"][0]["time"],int(data.index[0].timestamp()))
        pd.testing.assert_frame_equal(data,original)
        self.assertTrue(full["retainHistory"])
        self.assertEqual(full["count"],60)
        print("HISTORY_RENDER_METRICS="+json.dumps(self.render_metrics))

    def test_weekly_history_is_not_limited_to_300(self):
        frame=self.frame(520,"W-MON")
        full=self.render(frame,retain_history=True)
        self.assertEqual(len(full["bars"]),520)
        self.assertEqual(full["bars"][-1]["close"],float(frame.Close.iloc[-1]))

    def test_explicit_all_history_zoom_displays_all_loaded_bars(self):
        frame=self.frame(1250)
        with patch.object(mobile_chart.components,"html") as output:
            mobile_chart.mobile_chart(frame,[],"全部歷史與鏡像","TEST",retain_history=True)
        data=json.loads(output.call_args.args[0].split("const data=",1)[1].split(";\ndocument",1)[0])
        self.assertEqual(data["count"],1250)
        self.assertEqual(len(data["bars"]),1250)
