"""Chart history is capped globally, including independently detected horizons."""
import unittest
from unittest.mock import patch
import pandas as pd
from box_presentation import box_layers


class LatestFiveBoxTests(unittest.TestCase):
    def candidates(self,ends,window):
        return [{"start":end-window+1,"end":end,"top":100+window,"bottom":90,
                 "mid":95+window/2,"status":"整理中" if end==119 else "下破"} for end in ends]

    def test_two_horizons_show_only_the_latest_five_boxes_in_total(self):
        short=self.candidates([19,39,59,79,99],3)
        large=self.candidates([29,49,69,89,119],5)
        frame=pd.DataFrame(index=pd.bdate_range("2026-01-01",periods=120))
        with patch("box_presentation.detect_boxes",side_effect=[short,large]):
            layers,_=box_layers(frame,short_window=3,large_window=5,history=True)
        self.assertEqual([b["end"] for b in layers],[69,79,89,99,119])
        self.assertEqual(len(layers),5)
        self.assertTrue(layers[-1]["active"])
        self.assertFalse(any(b["end"]<69 for b in layers))

    def test_default_still_draws_only_current_valid_boxes(self):
        short=self.candidates([19,39,59,79,99],3)
        large=self.candidates([29,49,69,89,119],5)
        frame=pd.DataFrame(index=pd.bdate_range("2026-01-01",periods=120))
        with patch("box_presentation.detect_boxes",side_effect=[short,large]):
            layers,_=box_layers(frame,short_window=3,large_window=5,history=False)
        self.assertEqual(len(layers),1)
        self.assertTrue(layers[0]["active"])
