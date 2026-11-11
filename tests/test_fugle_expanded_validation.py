import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

from streamlit.testing.v1 import AppTest
import fugle_history_validation as v
import fugle_universe_validation as u


def payload(kind="all", day=v.END):
    return {"date": day, "type": "EQUITY", "exchange": "TPEx", "market": "OTC",
            **({"isHalted": True} if kind == "halted" else {}),
            "data": [{"symbol": "5276", "industry": "24", "name": "UNTRUSTED_SENTINEL"}] if kind == "all" else []}


def fixture():
    rows = [{"code": s, "listing_date": "2010-01-01", "quote_status": "valid_close", "volume_shares": 1000}
            for s in v.EXPANDED_SYMBOLS]
    rows[0].update(listing_date="2026-01-01", quote_status="missing_normal_session_close", volume_shares=200)
    rows[1].update(quote_status="absent", volume_shares=None, status_evidence={"SuspensionOfTrading": "Ｙ"})
    return {"as_of": v.END, "rows": rows}, {"denominator": {"count": 10}, "sampling": {"method": "test"}}


def universe_fetch(kind, key):
    return u.parse_universe(payload(kind), kind), {"http_status": 200, "parameters": u.parameters(kind)}


def history_fetch(symbol, start, end, key):
    return [], {"symbol": symbol, "parameters": v.request_parameters(symbol, start, end), "http_status": 200}


def baseline(symbol):
    return [], {"known_nontrading_date": "2026-10-23", "known_no_ohlc_dates": []}


class ExpandedTests(unittest.TestCase):
    def test_frozen_evidence_and_official_null_rows(self):
        official, manifest = u.load_universe()
        self.assertEqual(len(official["rows"]),897)
        self.assertEqual(set(manifest["baseline_files"]),set(v.EXPANDED_SYMBOLS))
        self.assertEqual(manifest["denominator"]["issuer_quote_intersection_count"],895)
        self.assertEqual(manifest["denominator"]["missing_close_present_quote_count"],23)
        self.assertEqual(manifest["denominator"]["new_listing_count"],45)
        self.assertEqual(manifest["denominator"]["official_suspended_codes"],["4534","4804"])
        missing_total = 0
        for symbol in v.EXPANDED_SYMBOLS:
            rows, evidence = v.load_baseline(symbol)
            missing = [r for r in rows if not v.valid_ohlc(r)]
            missing_total += len(missing)
            self.assertEqual(sorted(r["Date"] for r in missing), sorted(evidence["known_no_ohlc_dates"]))
            self.assertGreater(len(rows),200)
            same = [{"Date":r["Date"], **{f:r[f] for f in v.FIELDS},"Volume":int(r["Volume_shares_scaled"])}
                    for r in rows if v.valid_ohlc(r)]
            result = v.compare_rows(symbol,same,rows,evidence)
            self.assertEqual(result["summary"]["official_no_ohlc_dates"], sorted(r["Date"] for r in missing))
            self.assertEqual(result["summary"]["price_mismatch_fields"],0)
            self.assertEqual(result["summary"]["official_valid_dates_without_fugle_valid_ohlc"],[])
            self.assertEqual(result["summary"]["fugle_extra_dates"],[])
            self.assertTrue(set(r["Date"] for r in missing).issubset(r["Date"] for r in result["daily_comparison"]))
        self.assertGreater(missing_total,0)

    def test_official_universe_integrity_dates_denominator_and_classification(self):
        rows = [{"code": str(i), "reference_date": v.END,
                 "classification": "ordinary_equity_candidate_by_official_issuer_code", "listing_date": "2010-01-01"}
                for i in range(1000, 1897)]
        for i, symbol in enumerate(v.EXPANDED_SYMBOLS): rows[i]["code"] = symbol
        # Ensure fixture remains unique when an allowed sample overlaps generated codes.
        used = set()
        for row in rows:
            if row["code"] in used: row["code"] = str(9000 + len(used))
            used.add(row["code"])
        official = {"as_of":v.END, "rows":rows}
        with tempfile.TemporaryDirectory() as folder, patch.object(u, "BASELINE", Path(folder)):
            def save(value, count=897, status="complete", corrupt=False):
                raw = json.dumps(value).encode()
                (Path(folder)/"universe.json").write_bytes(raw)
                (Path(folder)/"manifest.json").write_text(json.dumps({"status":status, "as_of":v.END,
                    "universe_sha256": "bad" if corrupt else hashlib.sha256(raw).hexdigest(), "denominator":{"count":count}}))
            save(official); self.assertEqual(len(u.load_universe()[0]["rows"]),897)
            cases = []
            x=copy.deepcopy(official); x["as_of"]="2026-11-10"; cases.append(x)
            x=copy.deepcopy(official); x["rows"][1]=x["rows"][0]; cases.append(x)
            x=copy.deepcopy(official); x["rows"][0]["reference_date"]="2026-11-10"; cases.append(x)
            x=copy.deepcopy(official); x["rows"][0]["classification"]="ETF"; cases.append(x)
            x=copy.deepcopy(official); x["rows"][0]["listing_date"]="bad"; cases.append(x)
            for x in cases:
                save(x)
                with self.assertRaises(v.ValidationError): u.load_universe()
            for kwargs in ({"count":896}, {"status":"collecting"}, {"corrupt":True}):
                save(official,**kwargs)
                with self.assertRaises(v.ValidationError): u.load_universe()

    def test_allowlist_and_caps(self):
        self.assertEqual(len(v.EXPANDED_SYMBOLS), 10)
        self.assertFalse(set(v.EXPANDED_SYMBOLS) & set(v.SYMBOLS))
        for s in v.EXPANDED_SYMBOLS:
            for start, end in v.chunks():
                self.assertEqual(v.request_parameters(s, start, end)["adjusted"], "false")
        for kind in [None, "normal", "all&date=2026-11-11"]:
            with self.assertRaises(v.ValidationError): u.parameters(kind)
        self.assertEqual(u.parameters("all"), {"type":"EQUITY", "exchange":"TPEx", "market":"OTC"})
        self.assertEqual(u.parameters("halted")["isHalted"], "true")

    def test_parser_rejects_malformed_duplicate_and_hidden_filters(self):
        cases = []
        for key, value in [("date", None), ("date", "2026-02-30"), ("date", "2026-11-11T00:00"),
                           ("market", "ESB"), ("exchange", "TWSE"), ("type", "INDEX"),
                           ("data", []), ("isNormal", True), ("isNormal", False), ("isHalted", True)]:
            p = payload(); p[key] = value; cases.append(p)
        p = payload(); p["data"] *= 2; cases.append(p)
        p = payload(); p["data"][0]["symbol"] = "../../secret"; cases.append(p)
        for p in cases:
            with self.subTest(p=p), self.assertRaises(v.ValidationError): u.parse_universe(p, "all")
        self.assertEqual(u.parse_universe(payload("halted"), "halted")["rows"], [])
        with self.assertRaises(v.ValidationError): u.parse_universe(payload(), "halted")

    def test_dates_denominator_extras_and_statuses(self):
        official, manifest = fixture()
        all_result = u.parse_universe(payload(), "all")
        all_result["rows"].append({"symbol": "00679B", "industry": "00"})
        halted = {"date": v.END, "rows": [{"symbol": "4153", "industry": "24"}]}
        result = u.compare_universes(official, all_result, halted, manifest)
        self.assertEqual(result["official_denominator"], 10)
        self.assertEqual(result["observed_official_intersection_count"], 2)
        self.assertEqual(result["fugle_extra_symbols"], ["00679B"])
        self.assertEqual(len(result["official_missing_from_fugle"]), 8)
        classes = {r["symbol"]: r for r in result["official_symbol_classes"]}
        self.assertTrue(classes["5276"]["new_listing_in_window"])
        self.assertFalse(classes["5276"]["official_no_trade"])
        self.assertFalse(classes["5276"]["official_suspended"])
        self.assertTrue(classes["4153"]["official_suspended"])
        all_result["date"] = halted["date"] = "2026-11-12"
        result = u.compare_universes(official, all_result, halted, manifest)
        self.assertTrue(result["dated_universe_mismatch"])
        self.assertIsNone(result["same_date_observed_listing_coverage_percent"])
        self.assertFalse(result["point_in_time_roster_equivalence_proven"])
        halted["date"] = v.END
        with self.assertRaises(v.ValidationError): u.compare_universes(official, all_result, halted, manifest)

    def test_transport_bound_and_sanitized(self):
        raw = json.dumps(payload()).encode()
        response = MagicMock(); response.__enter__.return_value = response
        response.read.return_value = raw; response.status = 200
        opener = MagicMock(); opener.open.return_value = response
        with patch.object(u, "build_opener", return_value=opener):
            rows, evidence = u.fetch_universe("all", "SECRET_SENTINEL")
        req = opener.open.call_args.args[0]
        self.assertEqual(req.get_header("X-api-key"), "SECRET_SENTINEL")
        self.assertEqual(parse_qs(urlsplit(req.full_url).query), {"type":["EQUITY"],"exchange":["TPEx"],"market":["OTC"]})
        self.assertEqual(opener.open.call_args.kwargs["timeout"], 20)
        self.assertEqual(response.read.call_args.args, (4_000_001,))
        for secret in ("SECRET_SENTINEL", "UNTRUSTED_SENTINEL"):
            self.assertNotIn(secret, json.dumps([rows,evidence]))
        response.read.return_value = b"x" * 4_000_001
        with patch.object(u, "build_opener", return_value=opener), self.assertRaises(v.ValidationError):
            u.fetch_universe("all", "SECRET_SENTINEL")

    @patch.object(u, "load_universe", side_effect=fixture)
    @patch.object(v, "load_baseline", side_effect=baseline)
    def test_run_exact22_serial_and_different_date_continues_history(self, *mocks):
        uf, hf, sleep = MagicMock(side_effect=universe_fetch), MagicMock(side_effect=history_fetch), MagicMock()
        result = u.run_expanded_validation("SECRET_SENTINEL", hf, uf, sleep)
        self.assertEqual(result["status"], "completed")
        self.assertEqual((uf.call_count, hf.call_count, sleep.call_count), (2,20,21))
        self.assertEqual(result["actual_http_attempts"], 22)
        self.assertEqual(len(result["samples"]), 10)
        self.assertTrue(all(c.args[0] >= 1 for c in sleep.call_args_list))
        self.assertNotIn("SECRET_SENTINEL", json.dumps(result, allow_nan=False))
        def other_day(kind, key):
            return u.parse_universe(payload(kind, "2026-11-12"),kind), {"http_status":200}
        result = u.run_expanded_validation("key", history_fetch, other_day, lambda _:None)
        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["universe"]["dated_universe_mismatch"])

    def test_preflight_missing_key_and_source_failure_make_no_calls(self):
        hf, uf = MagicMock(), MagicMock()
        self.assertEqual(u.run_expanded_validation("", hf, uf)["status"], "blocked")
        with patch.object(u, "load_universe", side_effect=OSError("SECRET_SENTINEL")):
            result = u.run_expanded_validation("key", hf, uf)
        self.assertEqual(result["actual_http_attempts"], 0)
        self.assertNotIn("SECRET_SENTINEL", json.dumps(result))
        hf.assert_not_called(); uf.assert_not_called()

    @patch.object(u, "load_universe", side_effect=fixture)
    @patch.object(v, "load_baseline", side_effect=baseline)
    def test_stop_no_retry_no_error_text(self, *mocks):
        for exc in [OSError("SECRET_SENTINEL"), v.ValidationError("SECRET_SENTINEL"),
                    HTTPError("https://SECRET_SENTINEL", 429, "SECRET_SENTINEL", {}, None)]:
            uf, hf = MagicMock(side_effect=exc), MagicMock()
            result = u.run_expanded_validation("key", hf, uf, lambda _:None)
            self.assertEqual(result["actual_http_attempts"], 1)
            self.assertEqual(result["status"], "stopped")
            self.assertNotIn("SECRET_SENTINEL", json.dumps(result))
            uf.assert_called_once(); hf.assert_not_called()
        hf = MagicMock(side_effect=OSError("SECRET_SENTINEL"))
        result = u.run_expanded_validation("key", hf, universe_fetch, lambda _:None)
        self.assertEqual(result["actual_http_attempts"],3)
        self.assertEqual(result["requests"][-1]["symbol"],"5276")
        self.assertEqual(result["requests"][-1]["from"],v.START)
        self.assertNotIn("SECRET_SENTINEL",json.dumps(result))
        hf.assert_called_once()

    def test_unauthorized_and_shared_cooldown(self):
        page = "from fugle_history_preview import show_fugle_history_preview\nshow_fugle_history_preview()"
        with patch.object(u,"load_universe",side_effect=fixture), patch.object(v,"load_baseline",side_effect=baseline):
            report = u.run_expanded_validation("mock",history_fetch,universe_fetch,lambda _:None)
        with patch("fugle_history_preview._secret", side_effect=lambda k: "key" if k=="FUGLE_API_KEY" else "pass"), \
             patch("fugle_history_preview.run_validation") as original, \
             patch("fugle_history_preview.run_expanded_validation", return_value=report) as expanded:
            app = AppTest.from_string(page).run()
            app.text_input[0].set_value("wrong").run()
            self.assertNotIn("fugle_history_expanded_run", [b.key for b in app.button])
            expanded.assert_not_called(); original.assert_not_called()
            app.text_input[0].set_value("pass").run()
            app.button(key="fugle_history_expanded_run").click().run()
            self.assertEqual(expanded.call_count, 1)
            self.assertEqual(len(app.success),1)
            app.run()
            app.button(key="fugle_history_run").click().run()
            original.assert_not_called()
            self.assertEqual(expanded.call_count, 1)
            self.assertEqual(len(app.exception), 0)
            app.button(key="fugle_history_lock").click().run()
            self.assertNotIn("fugle_history_validation_result", app.session_state)


if __name__ == "__main__": unittest.main()
