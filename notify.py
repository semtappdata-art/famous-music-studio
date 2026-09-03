"""ntfy.sh üzerinden telefona push bildirimi gönderen küçük yardımcı.

Kurulum (kullanıcı tarafında, elle, bir kere):
  1. Telefona "ntfy" uygulamasını kur (App Store / Play Store).
  2. Rastgele, tahmin edilmesi zor bir konu (topic) adı seç (ör.
     "fms-bildirim-x7q2") ve uygulamada o konuya abone ol — ntfy.sh'de hesap
     gerekmiyor, konu adı tek başına "gizlilik" sağlıyor (herkese açık ama
     bilinmeyen bir kanal).
  3. Repo kökünde notify_config.json oluştur (gitignored — bkz. .gitignore):
         {"ntfy_topic": "senin-sectigin-konu-adi"}

notify_config.json yoksa send() sessizce False döner — otomasyon bildirim
olmadan da normal çalışmaya devam eder, sadece hatırlatma gönderilmez.
"""

import json
import os

import requests

_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notify_config.json")


def _topic() -> str | None:
    if not os.path.isfile(_CONFIG_PATH):
        return None
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f).get("ntfy_topic")
    except (OSError, json.JSONDecodeError):
        return None


def send(title: str, message: str) -> bool:
    """title SADECE ASCII olmalı — ntfy'nin Title header'ı requests'te latin-1
    ile kodlanıyor, Türkçe karakterlerin bir kısmı (ı, İ, ş, ğ) latin-1 dışında
    kalıp UnicodeEncodeError'a yol açar. message (body) tam UTF-8 destekli,
    Türkçe metin oraya yazılmalı."""
    topic = _topic()
    if not topic:
        return False
    try:
        resp = requests.post(
            f"https://ntfy.sh/{topic}",
            data=message.encode("utf-8"),
            headers={"Title": title, "Priority": "default"},
            timeout=(5, 10),
        )
        resp.raise_for_status()
        return True
    except Exception:
        return False
