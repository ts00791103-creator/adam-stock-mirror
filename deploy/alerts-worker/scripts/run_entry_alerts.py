"""Daily worker. Default dry run; sending requires explicit flags and configuration."""
import argparse
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import os
from pathlib import Path
import re
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import yfinance as yf
from entry_alerts import AlertSettings, evaluate_entry_alerts
from alert_delivery import AlertLedger, deliver_once
from telegram_setup import validate_bot


TZ = ZoneInfo("Asia/Taipei")


def load_configuration(path):
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    symbols = list(dict.fromkeys(config.get("symbols", [])))
    if not 1 <= len(symbols) <= 30 or any(not re.fullmatch(r"[0-9]{4,6}\.(TW|TWO)", s) for s in symbols):
        raise ValueError("追蹤名單需為1至30檔台股Yahoo代號")
    settings = AlertSettings(**config.get("settings", {}))
    settings.validate()
    rules = config.get("rules", ["箱底反彈", "箱頂突破"])
    if not rules or any(rule not in ("箱底反彈", "箱頂突破") for rule in rules):
        raise ValueError("請設定有效提醒條件")
    return config, symbols, settings, rules


def scan(symbols, settings, rules, now, download=yf.download, names=None):
    events, checked, failures = [], [], []
    day = now.date().isoformat()
    for symbol in symbols:
        try:
            data = download(symbol, period="1y", interval="1d", auto_adjust=False,
                            progress=False, threads=False, timeout=12)
            found = evaluate_entry_alerts(data, symbol, day, settings, rules)
            for event in found:
                event["名稱"] = (names or {}).get(symbol, "")
            events.extend(found)
            checked.append({"symbol": symbol, "date": day, "alerts": len(found)})
        except Exception:
            failures.append({"symbol": symbol, "reason": "行情非當日、品質異常或無法取得；未判定"})
    return {"events": events, "checked": checked, "failures": failures}


def commit_checkpoint(path):
    # Dedicated private deployment repository only, never run this against main/B3 of the app repo.
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    branch = os.environ.get("GITHUB_REF_NAME", "")
    if not repository or repository.lower() == "ts00791103-creator/adam-stock-mirror" or not branch:
        raise RuntimeError("提醒紀錄需部署於獨立專案；禁止寫入原網站專案")
    subprocess.run(["git", "add", "--", str(path)], check=True, stdout=subprocess.DEVNULL)
    changed = subprocess.run(["git", "diff", "--cached", "--quiet", "--", str(path)], check=False).returncode
    if changed == 1:
        subprocess.run(["git", "commit", "-m", "Persist alert delivery state", "--only", "--", str(path)],
                       check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["git", "push", "origin", "HEAD:refs/heads/"+branch], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif changed != 0:
        raise RuntimeError("無法確認提醒紀錄狀態，停止推播")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="alerts_config.json")
    parser.add_argument("--state", default="state/alerts.json")
    parser.add_argument("--send", action="store_true")
    parser.add_argument("--git-state", action="store_true")
    args = parser.parse_args(argv)
    config, symbols, settings, rules = load_configuration(args.config)
    now = datetime.now(TZ)
    if now.weekday() >= 5 or now.hour < 14:
        print("Outside weekday after-close window; nothing sent.")
        return 0
    if args.send and (config.get("enabled") is not True or os.environ.get("ALERTS_ENABLED") != "true"):
        raise ValueError("背景推播尚未明確啟用，停止發送")
    if args.send and (not os.environ.get("TELEGRAM_BOT_TOKEN") or not os.environ.get("TELEGRAM_CHAT_ID")):
        raise ValueError("缺少Telegram設定，停止發送")
    if args.send:
        validate_bot(os.environ["TELEGRAM_BOT_TOKEN"], config.get("expected_bot_username", ""))
    result = scan(symbols, settings, rules, now, names=config.get("names", {}))
    print(json.dumps({"checked": len(result["checked"]), "unconfirmed": len(result["failures"]),
                      "triggered": len(result["events"]), "sending": args.send}, ensure_ascii=False))
    Path("reports").mkdir(exist_ok=True)
    Path("reports/latest_scan.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if not args.send:
        return 0
    ledger = AlertLedger(args.state)
    checkpoint = (lambda: commit_checkpoint(args.state)) if args.git_state else (lambda: None)
    outcomes = deliver_once(result["events"], ledger, os.environ["TELEGRAM_BOT_TOKEN"],
                            os.environ["TELEGRAM_CHAT_ID"], checkpoint=checkpoint)
    print(json.dumps(outcomes, ensure_ascii=False))
    return 1 if any(item["status"] == "uncertain" for item in outcomes) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Do not print secrets or credential-bearing Git/Telegram request details.
        print("Reminder worker stopped safely; check configuration, source dates and state persistence.", file=sys.stderr)
        sys.exit(1)
