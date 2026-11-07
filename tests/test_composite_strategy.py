import unittest
import pandas as pd
from composite_strategy import price_factors, combine_factors, rank_rows, margin_decliners


class CompositeStrategyTests(unittest.TestCase):
    def frame(self):
        data=pd.DataFrame({"Open":100., "High":120., "Low":100., "Close":110., "Volume":1000000.},
                          index=pd.bdate_range("2026-09-01", periods=21))
        data.iloc[-1,data.columns.get_loc("Volume")]=3000000.
        return data

    def item(self, frame):
        return {"代號":"2330","名稱":"測試","市場":"上市","Yahoo代號":"2330.TW",
                "官方行情日期":str(frame.index[-1].date()),"官方收盤":110.,
                "官方當日成交量（張）":3000.}

    def chip(self,day):
        return {"date":day,"foreign":-300000.,"trust":600000.,"dealer":0.,"net":300000.,"source":"fixture"}

    def test_formula_excludes_signal_from_average_and_includes_twenty_lows(self):
        d=self.frame()
        d.iloc[0,d.columns.get_loc("Low")]=50.
        result=price_factors(d,str(d.index[-1].date()))
        self.assertAlmostEqual(result["近低反彈%"],10.)
        self.assertEqual(result["量比"],3.)

    def test_share_units_reconcile_net_and_margin_periods(self):
        d=self.frame(); item=self.item(d); day=item["官方行情日期"]
        row=combine_factors(item,d,self.chip(day),
             {"date":day,"balance":100.,"previous":120.,"source":"fixture"},
             {"date":str(d.index[-6].date()),"balance":150.})
        self.assertEqual(row["法人占比%"],10.)
        self.assertEqual(row["法人合計（張）"],300.)
        self.assertEqual(row["融資日增減（張）"],-20.)
        self.assertEqual(row["融資5日增減（張）"],-50.)

    def test_missing_chips_or_bad_dates_do_not_become_zero(self):
        d=self.frame(); i=self.item(d)
        for chip in (None,self.chip("2000-01-01")):
            with self.assertRaises(ValueError): combine_factors(i,d,chip)
        with self.assertRaises(ValueError): price_factors(d,"2000-01-01")
        self.assertIsNone(combine_factors(i,d,self.chip(i["官方行情日期"]))["融資日增減（張）"])

    def test_components_and_different_source_volumes_are_checked(self):
        d=self.frame(); i=self.item(d); c=self.chip(i["官方行情日期"]); c["net"]=0.
        with self.assertRaises(ValueError): combine_factors(i,d,c)
        i["官方當日成交量（張）"]=3.
        with self.assertRaises(ValueError): combine_factors(i,d,self.chip(i["官方行情日期"]))

    def rows(self):
        return [{"Yahoo代號":str(i)+".TW","資料日期":"2026-11-06",
                 "近低反彈%":float(i),"量比":float(4-i),"法人占比%":float(i-2)}
                 for i in range(1,4)]

    def test_percentile_then_weights_with_stable_ties(self):
        rows=rank_rows(self.rows())
        self.assertTrue(all(abs(r["綜合分"]-50)<1e-8 for r in rows))
        self.assertEqual([r["Yahoo代號"] for r in rows],["1.TW","2.TW","3.TW"])
        self.assertEqual(rank_rows(self.rows(),(0,100,0))[0]["Yahoo代號"],"1.TW")

    def test_equal_values_and_single_security_get_neutral_percentiles(self):
        rows=self.rows()
        for row in rows:
            row.update({"近低反彈%":1.,"量比":1.,"法人占比%":0.})
        self.assertTrue(all(r["綜合分"]==50. for r in rank_rows(rows)))
        self.assertEqual(rank_rows(rows[:1])[0]["綜合分"],50.)

    def test_bad_weights_and_incomplete_cross_sections_are_rejected(self):
        with self.assertRaises(ValueError): rank_rows(self.rows(),(40,50,30))
        rows=self.rows(); rows[0]["法人占比%"]=None
        with self.assertRaises(ValueError): rank_rows(rows)
        rows=self.rows(); rows[0]["資料日期"]="2000-01-01"
        with self.assertRaises(ValueError): rank_rows(rows)
        rows=self.rows(); rows[0]["Yahoo代號"]=rows[1]["Yahoo代號"]
        with self.assertRaises(ValueError): rank_rows(rows)

    def test_margin_decline_is_optional_and_uses_negative_change(self):
        rows=[{"Yahoo代號":"A","融資日增減（張）":None},
              {"Yahoo代號":"B","融資日增減（張）":-10.},
              {"Yahoo代號":"C","融資日增減（張）":0.}]
        self.assertEqual([r["Yahoo代號"] for r in margin_decliners(rows)],["B"])
        self.assertEqual(margin_decliners(rows,5),[])


if __name__=="__main__": unittest.main()
