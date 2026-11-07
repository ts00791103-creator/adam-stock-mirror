"""Private deployment setup. Token is read from environment and never printed."""
import argparse
import json
import os
from pathlib import Path
import re
from urllib.request import Request, urlopen


def api_call(token, method, payload=None):
    request = Request("https://api.telegram.org/bot" + token + "/" + method,
                      data=json.dumps(payload or {}).encode(),
                      headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=10) as response:
            result = json.load(response)
        if not result.get("ok"):
            raise ValueError("request rejected")
        return result["result"]
    except Exception:
        raise RuntimeError("Telegram設定查證未完成，請核對金鑰、機器人與配對訊息") from None


def validate_bot(token, expected_username):
    if not token or not expected_username:
        raise ValueError("尚未設定機器人")
    actual = api_call(token, "getMe")
    if actual.get("username", "").lower() != expected_username.lstrip("@").lower():
        raise ValueError("Token對應的機器人與設定帳號不同，停止連接")


def find_private_recipient(token, code):
    if not re.fullmatch(r"[A-Za-z0-9_-]{8,64}", code or ""):
        raise ValueError("配對碼需8至64個英數字元、底線或連字號")
    updates = api_call(token, "getUpdates", {"timeout": 0, "limit": 100})
    chats = set()
    for update in updates:
        message = update.get("message") or {}
        chat = message.get("chat") or {}
        if chat.get("type") == "private" and message.get("text") == "/start " + code:
            chats.add(str(chat["id"]))
    if len(chats) != 1:
        raise ValueError("未找到唯一配對：請在自己的機器人傳送指定配對碼，不自動選擇其他聊天")
    return chats.pop()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("check-bot", "find-chat", "test-message"))
    args = parser.parse_args()
    config = json.loads(Path("alerts_config.json").read_text(encoding="utf-8"))
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    validate_bot(token, config.get("expected_bot_username", ""))
    if args.mode == "check-bot":
        print("機器人帳號已確認，尚未發送訊息。")
    elif args.mode == "find-chat":
        recipient = find_private_recipient(token, os.environ.get("TELEGRAM_SETUP_CODE", ""))
        print("將以下值存入此私有專案的TELEGRAM_CHAT_ID Secret：")
        print(recipient)
    else:
        chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
        if not chat_id:
            raise ValueError("尚未設定收件人")
        api_call(token, "sendMessage", {"chat_id": chat_id,
                 "text": "亞當鏡像：Telegram連線測試成功。這是測試訊息，不是進場觀察提醒；自動排程是否啟用請看後台設定。"})
        print("Telegram已接受測試訊息，請由本人確認手機收到。")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("設定尚未完成；未顯示金鑰或私人聊天內容。")
        raise SystemExit(1)
