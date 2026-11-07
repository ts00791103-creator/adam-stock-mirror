"""Opt-in Telegram transport and durable, fail-closed de-duplication."""
import json
from pathlib import Path
from urllib.request import Request, urlopen
from entry_alerts import telegram_text


class AlertLedger:
    """Single worker only; deploy workflow uses concurrency to serialize runs."""
    def __init__(self, path):
        self.path = Path(path)
        self.records = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
        if not isinstance(self.records, dict):
            raise ValueError("提醒紀錄格式損壞，停止推播以免重複")

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.records, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.path)

    def claim(self, event):
        event_id = event["提醒編號"]
        if event_id in self.records:
            return False
        self.records[event_id] = {"status": "pending", "event": event}
        self.save()
        return True

    def mark(self, event_id, status):
        if status not in ("sent", "uncertain"):
            raise ValueError("不支援的推播狀態")
        self.records[event_id]["status"] = status
        self.save()


def send_telegram(event, token, chat_id):
    if not token or not chat_id:
        raise ValueError("尚未完成Telegram設定")
    # Never include token-bearing URLs or transport exception details in logs.
    request = Request("https://api.telegram.org/bot" + token + "/sendMessage",
                      data=json.dumps({"chat_id": chat_id, "text": telegram_text(event)}).encode(),
                      headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.load(response)
        if not payload.get("ok"):
            raise ValueError("Telegram未確認送達")
        return True
    except Exception:
        raise RuntimeError("Telegram送達狀態未確認；未自動重送，請至紀錄核對") from None


def deliver_once(events, ledger, token, chat_id, *, checkpoint=lambda: None, transport=None):
    """Persist claim before POST; ambiguous failures never auto-retry."""
    results = []
    for event in events:
        if not ledger.claim(event):
            results.append({"提醒編號": event["提醒編號"], "status": "duplicate_skipped"})
            continue
        # If durable persistence fails, do NOT send anything.
        checkpoint()
        try:
            (transport or send_telegram)(event, token, chat_id)
        except Exception:
            ledger.mark(event["提醒編號"], "uncertain")
            checkpoint()
            results.append({"提醒編號": event["提醒編號"], "status": "uncertain"})
        else:
            ledger.mark(event["提醒編號"], "sent")
            checkpoint()
            results.append({"提醒編號": event["提醒編號"], "status": "sent"})
    return results

