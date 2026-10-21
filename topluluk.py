#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Famous Music Studio — Topluluk Entegrasyonu (Madde 29)

Iki katman:
  1. TOPLULUK BILDIRIMI — yeni video/set yayinlandiginda Discord webhook +
     Telegram (kanal mesaji) + site abonelik listesine bildirim.
  2. TOPLULUK ABONELIGI — site'deki "Topluluğa katil" formu; e-posta toplar,
     disa aktarilabilir (CSV/JSON), re-engagement icin.

Tasarim kararlari:
  - Discord: WEBHOOK (token yok, kanal yonetimi gerekmez). Kurulum:
    Server > Settings > Integrations > Webhooks > New Webhook > URL kopyala.
  - Telegram: mevcut bot token + chat id (notify_config.json) veya yeni kanal.
  - PII: SADECE e-posta adresi toplanir (topluluk listesi icin gerekli).
    Ziyaretci analitiginden AYRI tutulur (Madde 28).
  - Cift kayit korumasi: ayni e-posta tekrar yazilmaz.
  - Topluluk listesi disa aktarim: `topluluk.py disa-aktar`

Kullanim:
    python topluluk.py bildir            # yeni icerik bildirimi (config'den)
    python topluluk.py bildir --baslik "..." --mesaj "..."
    python topluluk.py abone ekle --email a@b.com
    python topluluk.py liste
    python topluluk.py disa-aktar --bicim csv
    python topluluk.py durum
"""
import argparse
import datetime
import json
import os
import re
import sys
import urllib.error
import urllib.request

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)

import config  # noqa: E402

TZ = datetime.timezone(datetime.timedelta(hours=3))
VERI_KLASORU = os.path.join(REPO, config.TOPLULUK_VERI_KLASORU)
ABONE_DOSYASI = os.path.join(VERI_KLASORU, "topluluk_aboneleri.json")
BILDIRIM_DOSYASI = os.path.join(VERI_KLASORU, "bildirim_log.jsonl")
CONFIG_DOSYASI = os.path.join(REPO, "topluluk_config.json")

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")


# ------------------------------------------------------------------ yapilandirma
def _ayarlari() -> dict:
    """topluluk_config.json + config.py birlestirilmis ayarlar."""
    ayar = {
        "discord_webhook_url": getattr(config, "TOPLULUK_DISCORD_WEBHOOK", ""),
        "telegram_chat_id": "",
        "telegram_bot_token": "",
        "site_url": getattr(config, "SITE_URL", "https://famousmusicstudio.com"),
        "kanal_ad": "Famous Music Studio",
    }
    if os.path.isfile(CONFIG_DOSYASI):
        try:
            with open(CONFIG_DOSYASI, encoding="utf-8") as f:
                ek = json.load(f)
            if isinstance(ek, dict):
                for k, v in ek.items():
                    if v:
                        ayar[k] = v
        except (OSError, ValueError):
            pass
    # Telegram: mevcut notify yapilandirmasini devral
    if not ayar.get("telegram_chat_id"):
        try:
            import notify
            _, chat_id, _ = notify._telegram_ayari()
            ayar["telegram_chat_id"] = chat_id or ""
        except Exception:
            pass
    if not ayar.get("telegram_bot_token"):
        try:
            import notify
            token, _, _ = notify._telegram_ayari()
            ayar["telegram_bot_token"] = token or ""
        except Exception:
            pass
    # PLACEHOLDER TOKEN TESPITI: "123456789:AA..." gibi sahte token 404 doner
    # ve kullaniciyi karsihtir. Gercek token uzunlugu >= 30 karakter.
    token = ayar.get("telegram_bot_token") or ""
    if token and (len(token) < 30 or token.startswith("123456789:")):
        ayar["telegram_bot_token"] = ""
        ayar["telegram_token_placeholder"] = True
    return ayar


def _klasor_hazirla():
    os.makedirs(VERI_KLASORU, exist_ok=True)


# ------------------------------------------------------------------ abonelik
def abone_ekle(email: str, kaynak: str = "site", ek_veri: dict = None) -> dict:
    """E-posta topluluk listesine ekler. Cift kayit engellenir."""
    email = (email or "").strip().lower()
    if not _EMAIL_RE.match(email):
        return {"durum": "hata", "hata": "gecersiz e-posta", "email": email}
    _klasor_hazirla()
    mevcut = _aboneleri_oku()
    for a in mevcut:
        if a.get("email") == email:
            return {"durum": "zaten_kayitli", "email": email}
    kayit = {
        "email": email,
        "kaynak": kaynak,
        "zaman": datetime.datetime.now(TZ).isoformat(),
        "onay": False,
    }
    if ek_veri:
        kayit.update(ek_veri)
    mevcut.append(kayit)
    _aboneleri_yaz(mevcut)
    return {"durum": "eklendi", "email": email, "toplam": len(mevcut)}


def _aboneleri_oku() -> list:
    if not os.path.isfile(ABONE_DOSYASI):
        return []
    try:
        with open(ABONE_DOSYASI, encoding="utf-8") as f:
            v = json.load(f)
        return v if isinstance(v, list) else []
    except (OSError, ValueError):
        return []


def _aboneleri_yaz(liste: list):
    _klasor_hazirla()
    tmp = ABONE_DOSYASI + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(liste, f, ensure_ascii=False, indent=2)
    os.replace(tmp, ABONE_DOSYASI)


def abone_listesi() -> list:
    return _aboneleri_oku()


def disa_aktar(bicim: str = "csv") -> str:
    """Abone listesini disa aktarir (CSV veya JSON). Donus: dosya yolu."""
    _klasor_hazirla()
    liste = _aboneleri_oku()
    if bicim == "json":
        yol = os.path.join(VERI_KLASORU, "topluluk_aboneleri_export.json")
        with open(yol, "w", encoding="utf-8") as f:
            json.dump(liste, f, ensure_ascii=False, indent=2)
    else:
        yol = os.path.join(VERI_KLASORU, "topluluk_aboneleri_export.csv")
        with open(yol, "w", encoding="utf-8", newline="") as f:
            f.write("email,kaynak,zaman,onay\n")
            for a in liste:
                f.write('"%s","%s","%s","%s"\n' % (
                    a.get("email", ""), a.get("kaynak", ""),
                    a.get("zaman", ""), "evet" if a.get("onay") else "hayir"))
    return yol


# ------------------------------------------------------------------ bildirim
def _ntfy_gonder(topic: str, baslik: str, mesaj: str, link: str = "") -> bool:
    """ntfy'ye anlik bildirim gonderir (token gerektirmez, telefona push).

    DIKKAT: HTTP header'lar latin-1 ile kodlanir; Turkce karakter ve em-dash
    header'da PATLAR (UnicodeEncodeError). Bu yuzden baslik ASCII'ye cevrilir
    (gorunen metin degismez, sadece header temizlenir).
    """
    if not topic:
        return False
    import urllib.parse
    govde = mesaj + ("\n\n" + link if link else "")
    temiz_baslik = (baslik.replace("—", "-").replace("–", "-")
                    .encode("ascii", "replace").decode("ascii"))[:200]
    try:
        req = urllib.request.Request(
            "https://ntfy.sh/" + urllib.parse.quote(topic, safe=""),
            data=govde.encode("utf-8"),
            headers={
                "Title": temiz_baslik,
                "Content-Type": "text/plain; charset=utf-8",
                "Priority": "default",
                "Tags": "music,headphones",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            return 200 <= r.status < 300
    except (urllib.error.URLError, OSError, ValueError) as e:
        sys.stderr.write(f"[topluluk] ntfy HATA: {e}\n")
        return False


def _discord_gonder(webhook_url: str, baslik: str, mesaj: str) -> bool:
    if not webhook_url:
        return False
    govde = {
        "username": "Famous Music Studio",
        "embeds": [{
            "title": baslik[:256],
            "description": mesaj[:4000],
            "color": 15311540,  # #e94560
            "footer": {"text": "Famous Music Studio"},
            "timestamp": datetime.datetime.now(TZ).isoformat(),
        }],
    }
    try:
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(govde, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            return 200 <= r.status < 300
    except (urllib.error.URLError, OSError, ValueError) as e:
        sys.stderr.write(f"[topluluk] Discord HATA: {e}\n")
        return False


def _telegram_gonder(bot_token: str, chat_id: str, baslik: str, mesaj: str) -> bool:
    if not bot_token or not chat_id:
        return False
    metin = f"*{baslik}*\n\n{mesaj}"
    veri = urllib.parse.urlencode({
        "chat_id": chat_id, "text": metin[:4096], "parse_mode": "Markdown",
    }).encode("utf-8")
    try:
        with urllib.request.urlopen(
            urllib.request.Request(f"https://api.telegram.org/bot{bot_token}/sendMessage",
                                   data=veri), timeout=15
        ) as r:
            return 200 <= r.status < 300
    except (urllib.error.URLError, OSError, ValueError) as e:
        sys.stderr.write(f"[topluluk] Telegram HATA: {e}\n")
        return False


def _abonelere_bildir(baslik: str, mesaj: str, link: str = "") -> int:
    """Topluluk abonel listesine 'yeni icerik' mesaji gonderir (simdilik
    dosyaya yazilir; gercek gonderim icin ESP/Resend API eklenebilir)."""
    liste = _aboneleri_oku()
    _klasor_hazirla()
    with open(BILDIRIM_DOSYASI, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "zaman": datetime.datetime.now(TZ).isoformat(),
            "baslik": baslik,
            "mesaj": mesaj,
            "link": link,
            "alici_sayisi": len(liste),
        }, ensure_ascii=False) + "\n")
    return len(liste)


def bildir(baslik: str = None, mesaj: str = None, link: str = "") -> dict:
    """Yeni icerik bildirimi: Discord + Telegram + abone listesi."""
    ayar = _ayarlari()
    if baslik is None:
        baslik = getattr(config, "TOPLULUK_BILDIRIM_BASLIK", "Yeni Video")
    if mesaj is None:
        mesaj = getattr(config, "TOPLULUK_BILDIRIM_MESAJ", "Famous Music Studio'da yeni bir şey var.")

    sonuc = {"discord": False, "telegram": False, "abone_sayisi": 0}

    kanallar = getattr(config, "TOPLULUK_KANALLAR", ["discord", "telegram", "ntfy"])

    if "discord" in kanallar and ayar.get("discord_webhook_url"):
        sonuc["discord"] = _discord_gonder(ayar["discord_webhook_url"], baslik, mesaj)
    if "telegram" in kanallar and ayar.get("telegram_bot_token") and ayar.get("telegram_chat_id"):
        sonuc["telegram"] = _telegram_gonder(
            ayar["telegram_bot_token"], ayar["telegram_chat_id"], baslik, mesaj)
    elif "telegram" in kanallar and ayar.get("telegram_token_placeholder"):
        sys.stderr.write(
            "[topluluk] Telegram token'ı PLACEHOLDER — gercek bot token'ı "
            "upload/telegram_client_secrets.json'a yazilmali.\n")
    if "ntfy" in kanallar and getattr(config, "TOPLULUK_NTFY_ACIK", True):
        sonuc["ntfy"] = _ntfy_gonder(
            getattr(config, "TOPLULUK_NTFY_TOPIC", ""), baslik, mesaj, link)
    sonuc["abone_sayisi"] = _abonelere_bildir(baslik, mesaj, link)
    return sonuc


# ------------------------------------------------------------------ durum
def durum() -> dict:
    ayar = _ayarlari()
    liste = _aboneleri_oku()
    bildirimler = 0
    if os.path.isfile(BILDIRIM_DOSYASI):
        with open(BILDIRIM_DOSYASI, encoding="utf-8") as f:
            bildirimler = sum(1 for l in f if l.strip())
    return {
        "discord_yapilandirilmis": bool(ayar.get("discord_webhook_url")),
        "telegram_yapilandirilmis": bool(ayar.get("telegram_chat_id")),
        "ntfy_yapilandirilmis": bool(getattr(config, "TOPLULUK_NTFY_TOPIC", "")),
        "ntfy_topic": getattr(config, "TOPLULUK_NTFY_TOPIC", ""),
        "kanallar": list(getattr(config, "TOPLULUK_KANALLAR", [])),
        "abone_sayisi": len(liste),
        "onayli_abone": sum(1 for a in liste if a.get("onay")),
        "bildirim_sayisi": bildirimler,
        "veri_klasoru": VERI_KLASORU,
    }


def main():
    ap = argparse.ArgumentParser(description="Topluluk entegrasyonu — Famous Music Studio")
    alt = ap.add_subparsers(dest="komut", required=True)

    b = alt.add_parser("bildir", help="yeni içerik bildirimi")
    b.add_argument("--baslik", default=None)
    b.add_argument("--mesaj", default=None)
    b.add_argument("--link", default="")

    a = alt.add_parser("abone", help="abone ekle")
    a.add_argument("eylem", choices=["ekle", "liste", "onayla"])
    a.add_argument("--email", default=None)
    a.add_argument("--kaynak", default="site")

    d = alt.add_parser("disa-aktar", help="abone listesini dışa aktar")
    d.add_argument("--bicim", default="csv", choices=["csv", "json"])

    alt.add_parser("durum", help="yapılandırma ve veri durumu")

    args = ap.parse_args()

    if args.komut == "bildir":
        s = bildir(args.baslik, args.mesaj, args.link)
        print("Bildirim sonucu:")
        print(f"  Discord   : {'GONDERILDI' if s['discord'] else 'gonderilmedi (yapilandirilmis degil / hata)'}")
        print(f"  Telegram  : {'GONDERILDI' if s['telegram'] else 'gonderilmedi (yapilandirilmis degil / hata)'}")
        print(f"  Abone log : {s['abone_sayisi']} abone")
        return 0

    if args.komut == "abone":
        if args.eylem == "ekle":
            if not args.email:
                print("HATA: --email gerekli")
                return 2
            s = abone_ekle(args.email, args.kaynak)
            print(f"{s['durum']}: {s.get('email', '')}"
                  + (f" (toplam {s['toplam']})" if "toplam" in s else ""))
            return 0 if s["durum"] != "hata" else 2
        if args.eylem == "liste":
            liste = abone_listesi()
            print(f"Toplam {len(liste)} abone:")
            for x in liste:
                print(f"  {x.get('email')}  [{x.get('kaynak')}]  "
                      f"{'ONAYLI' if x.get('onay') else 'bekliyor'}")
            return 0
        if args.eylem == "onayla":
            if not args.email:
                print("HATA: --email gerekli")
                return 2
            liste = _aboneleri_oku()
            bulundu = False
            for x in liste:
                if x.get("email") == args.email.strip().lower():
                    x["onay"] = True
                    bulundu = True
            if bulundu:
                _aboneleri_yaz(liste)
                print(f"ONAYLANDI: {args.email}")
            else:
                print(f"BULUNAMADI: {args.email}")
            return 0 if bulundu else 1

    if args.komut == "disa-aktar":
        yol = disa_aktar(args.bicim)
        print(f"Disa aktarildi: {yol}")
        return 0

    if args.komut == "durum":
        s = durum()
        print("=== TOPLULUK DURUMU ===")
        print(f"Discord yapilandirilmis : {s['discord_yapilandirilmis']}")
        print(f"Telegram yapilandirilmis: {s['telegram_yapilandirilmis']}")
        print(f"Abone sayisi             : {s['abone_sayisi']} "
              f"(onayli: {s['onayli_abone']})")
        print(f"Bildirim sayisi          : {s['bildirim_sayisi']}")
        print(f"Veri klasoru             : {s['veri_klasoru']}")
        if not s["discord_yapilandirilmis"]:
            print()
            print("Discord kurulumu:")
            print("  1) Discord sunucunda: Settings > Integrations > Webhooks")
            print("  2) 'New Webhook' > isim ver > 'Copy Webhook URL'")
            print("  3) topluluk_config.json'a yaz:")
            print('     {"discord_webhook_url": "https://discord.com/api/webhooks/..."}')
        return 0

    return 2


if __name__ == "__main__":
    import urllib.parse  # noqa: E402
    sys.exit(main())
