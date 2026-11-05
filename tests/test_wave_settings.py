import unittest
from streamlit.testing.v1 import AppTest
from wave_settings import wave_windows


class WaveSettingsTests(unittest.TestCase):
    def test_daily_weekly_windows_preserve_pivot_spans(self):
        self.assertEqual(list(wave_windows("1d").values()), [(3,100),(7,260),(14,650)])
        self.assertEqual(list(wave_windows("1wk").values()), [(3,26),(7,78),(14,156)])

    def test_invalid_order_and_insufficient_windows_cannot_be_used(self):
        for values in ((100,78,156), (7,15,28), (7,15,5001), (7,15,29.5)):
            with self.assertRaises(ValueError):
                wave_windows("1wk", values)

    def test_custom_windows_stay_separate_when_switching_interval(self):
        app = AppTest.from_string('''
import streamlit as st
from wave_settings import show_wave_settings
interval=st.selectbox("測試週期", ["1d", "1wk"])
st.session_state["actual_waves"]=show_wave_settings(interval)
st.write("可進行分析")
''').run()
        app.checkbox[0].check().run()
        app.number_input[0].set_value(90).run()
        self.assertEqual(app.session_state["actual_waves"]["短波"], (3,90))
        app.selectbox[0].set_value("1wk").run()
        self.assertFalse(app.checkbox[0].value)
        self.assertEqual(app.session_state["actual_waves"]["短波"], (3,26))
        app.checkbox[0].check().run()
        app.number_input[0].set_value(100).run()
        self.assertTrue(any("依序增加" in e.value for e in app.error))
        self.assertFalse(any("可進行分析" in m.value for m in app.markdown))
        self.assertEqual(len(app.exception),0)

