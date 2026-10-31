"""WhatsApp notifications through the CallMeBot API (free, no business account).

Setup for each collector's phone (once):
  1. add +34 644 52 74 88 to the contacts
  2. send "I allow callmebot to send me messages" on WhatsApp
  3. you receive an API key
Then set   WHATSAPP_RECIPIENTS="22901XXXXXXXX:apikey1,22901YYYYYYYY:apikey2"

Without configuration the notifier only logs the message (demo mode).
"""
import logging
import os
from urllib.parse import quote

import requests

log = logging.getLogger("notifier")
API = "https://api.callmebot.com/whatsapp.php?phone={phone}&text={text}&apikey={key}"


class WhatsAppNotifier:
    def __init__(self, recipients: str | None = None):
        raw = recipients if recipients is not None else os.environ.get("WHATSAPP_RECIPIENTS", "")
        self.recipients = [tuple(r.split(":", 1)) for r in raw.split(",") if ":" in r]
        self.sent: list[str] = []          # kept for tests / dashboard

    @property
    def configured(self) -> bool:
        return bool(self.recipients)

    def send(self, text: str) -> str:
        self.sent.append(text)
        if not self.configured:
            log.warning("[WhatsApp demo] %s", text)
            return "demo"
        ok = True
        for phone, key in self.recipients:
            try:
                r = requests.get(API.format(phone=phone, text=quote(text), key=key), timeout=10)
                ok &= r.status_code == 200
            except requests.RequestException as e:
                log.error("WhatsApp to %s failed: %s", phone, e)
                ok = False
        return "sent" if ok else "error"
