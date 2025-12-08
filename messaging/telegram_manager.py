import os
import json
import time
import requests
from pathlib import Path

class TelegramManager:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if not self.token or not self.chat_id:
            raise RuntimeError("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")

        self.api_url = f"https://api.telegram.org/bot{self.token}"

    # ----------------------------
    # Send message with 3 buttons
    # ----------------------------
    def send_bugfix_message(self, text: str):
        r = requests.post(f"{self.api_url}/sendMessage", data={
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": json.dumps({
                "inline_keyboard": [
                    [
                        {"text": "🔁 Rerun", "callback_data": "rerun"},
                        {"text": "🛠 Fix & Rerun", "callback_data": "fix_and_rerun"},
                        {"text": "⛔ Terminate", "callback_data": "terminate"}
                    ]
                ]
            })
        })

        if not r.ok:
            raise RuntimeError(f"Telegram error: {r.text}")

    # ----------------------------
    # Wait for user clicking a button
    # ----------------------------
    def wait_for_user_response(self):
        res = requests.get(f"{self.api_url}/getUpdates")
        updates = res.json().get("result", [])
        last_update_id = updates[-1]["update_id"] + 1 if updates else None
        while True:
            res = requests.get(
                f"{self.api_url}/getUpdates",
                params={"offset": last_update_id, "timeout": 10}
            )

            if not res.ok:
                time.sleep(1)
                continue

            updates = res.json().get("result", [])
            for update in updates:
                last_update_id = update["update_id"] + 1

                if "callback_query" in update:
                    cb = update["callback_query"]
                    action = cb["data"]

                    # Stop animation in Telegram UI
                    requests.post(f"{self.api_url}/answerCallbackQuery", data={
                        "callback_query_id": cb["id"]
                    })

                    return action

            time.sleep(0.5)

    # ----------------------------
    # Combine send + wait
    # ----------------------------
    def notify_and_wait(self, text: str) -> str:
        self.send_bugfix_message(text)
        return self.wait_for_user_response()
