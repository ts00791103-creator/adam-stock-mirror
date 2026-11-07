import unittest
from chip_sources import parse_institution, parse_margin


class ChipSourceTests(unittest.TestCase):
    def test_twse_institution_shares_and_negative_net(self):
        fields=["證券代號","外陸資買賣超股數(不含外資自營商)","投信買賣超股數","自營商買賣超股數","三大法人買賣超股數"]
        body={"date":"20261106","stat":"OK","fields":fields,"data":[["2330","-3,000","1,000","500","-1,500"],["00632R","0","0","0","0"]]}
        result=parse_institution(body,"上市","2026-11-06","fixture")
        self.assertEqual(result["2330"]["net"],-1500.)
        self.assertNotIn("00632R",result)
        with self.assertRaises(ValueError): parse_institution(body,"上市","2026-11-05","fixture")

    def test_tpex_exact_published_keys_and_dates(self):
        row={"Date":"1151106","SecuritiesCompanyCode":"3163",
             "Foreign Investors include Mainland Area Investors (Foreign Dealers excluded)-Difference":"1000",
             "SecuritiesInvestmentTrustCompanies-Difference":"0","Dealers-Difference":"-100","TotalDifference":"900"}
        result=parse_institution([row],"上櫃","2026-11-06","fixture")
        self.assertEqual(result["3163"]["net"],900.)
        row["TotalDifference"]="100"
        with self.assertRaises(ValueError): parse_institution([row],"上櫃","2026-11-06","fixture")

    def test_margin_date_and_lot_fields(self):
        body={"date":"20261106","tables":[{"fields":["代號","名稱","前資餘額(張)","資買","資餘額"],
                    "data":[["3163","波若威","7,580","0","5,893"]]}]}
        result=parse_margin(body,"上櫃","2026-11-06","fixture")
        self.assertEqual(result["3163"]["balance"]-result["3163"]["previous"],-1687.)
        with self.assertRaises(ValueError): parse_margin(body,"上櫃","2026-11-05","fixture")
        with self.assertRaises(ValueError): parse_margin([{"balance":100}],"上市","2026-11-06","fixture")

    def test_twse_repeated_fields_require_financing_group(self):
        table={"fields":["股票代號","股票名稱","前日餘額","今日餘額","前日餘額","今日餘額"],
               "data":[["2330","台積電","100","80","500","900"]]}
        body={"date":"20261106","tables":[table]}
        with self.assertRaises(ValueError): parse_margin(body,"上市","2026-11-06","fixture")
        table["groups"]=[{"title":"融資","span":2},{"title":"融券","span":2}]
        self.assertEqual(parse_margin(body,"上市","2026-11-06","fixture")["2330"]["balance"],80.)


if __name__=="__main__": unittest.main()
