"""Bounded system-only verification; never fabricates stock signals."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from alert_delivery import AlertLedger, deliver_once
from telegram_setup import validate_bot, api_call
from scripts.run_entry_alerts import commit_checkpoint

EVENT_ID = "system:scheduler-check:2026-11-06:v1"
DEADLINE = datetime(2026, 11, 6, 0, 0, tzinfo=timezone.utc)


def system_transport(event, token, chat_id):
    api_call(token, "sendMessage", {"chat_id": chat_id, "text":
        "亞當鏡像｜自動排程驗證\n這是系統連線測試，不是股票進場訊號。\n"
        "背景排程已自動啟動；下一次驗證將確認不會重複發送。"})
    return True


def main():
    if datetime.now(timezone.utc) >= DEADLINE:
        print("Verification window expired; nothing sent.")
        return 0
    if os.environ.get("GITHUB_EVENT_NAME") != "schedule":
        raise ValueError("Only an actual schedule event can verify scheduling")
    if os.environ.get("ALERTS_ENABLED") != "true":
        raise ValueError("Background notifications disabled")
    token, chat_id = os.environ.get("TELEGRAM_BOT_TOKEN", ""), os.environ.get("TELEGRAM_CHAT_ID", "")
    config = json.loads(Path("alerts_config.json").read_text(encoding="utf-8"))
    if not config.get("enabled") or not token or not chat_id:
        raise ValueError("Configuration incomplete")
    validate_bot(token, config.get("expected_bot_username", ""))
    ledger = AlertLedger("state/scheduler_verification.json")
    before = ledger.records.get(EVENT_ID, {}).get("status")
    results = deliver_once([{"提醒編號": EVENT_ID, "用途": "系統排程驗證，非股票訊號"}], ledger,
                           token, chat_id, checkpoint=lambda: commit_checkpoint(ledger.path),
                           transport=system_transport)
    result = results[0]["status"]
    if result == "duplicate_skipped" and before != "sent":
        raise RuntimeError("Previous delivery was not confirmed; not retrying")
    Path("reports").mkdir(exist_ok=True)
    report = {"event": "schedule", "utc": datetime.now(timezone.utc).isoformat(),
              "result": result, "prior_status": before, "stock_signals": False}
    Path("reports/scheduler_verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))
    return 1 if result == "uncertain" else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        print("System verification stopped safely; no credential details displayed.", file=sys.stderr)
        sys.exit(1)
