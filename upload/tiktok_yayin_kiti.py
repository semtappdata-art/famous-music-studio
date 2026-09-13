# -*- coding: utf-8 -*-
"""TikTok YAYIN KİTİ — taslağı telefondan EKSİKSİZ yayınlamak için Telegram mesajları.

    python upload/tiktok_yayin_kiti.py --project "projects/Kırık Zincir" --onizle

NEDEN VAR (2026-09-13): boru hattı TikTok'a yalnız TASLAK yüklüyor (inbox akışı,
`video.upload` izni). O akışta API açıklama, gizlilik, `is_aigc` ve duet/stitch
ALAMIYOR — hepsi Direct Post'a özgü. Yani yayının "donanımlı" olup olmadığı
tamamen kullanıcının telefonda ne yaptığına bağlı. Eski hatırlatma yalnız "taslak
bekliyor" diyordu; açıklama `tiktok_publish_plan.py`de, AI etiketi bir konsol
satırında, kapak bir state alanında, ayarlar hiçbir yerde değildi.

MESAJ DÜZENİ (her parça AYRI mesaj, `parse_mode` YOK — kopyalanan metinde tek
bir kaçırılmamış karakter gönderimi düşürmesin):
  1. Kapak fotoğrafı (`notify.send_photo`) + kısa açıklama (şarkı adı, kod).
     Galeriye tek dokunuşla kaydedilir; TikTok'ta "Kapağı düzenle → Yükle".
  2. YALNIZ açıklama + hashtag — başka karakter yok, kopyalamaya hazır
     (`social_text.build_tiktok_kit_caption`).
  3. Ayar kontrol listesi + önerilen saat aralığı + uyarılar.
  4. YALNIZ ilk yorum (YouTube bağlantısı; açıklamada dış link YOK).
  5. "Yayınladıysan yaz: yayınladım <başlık>" + kod — `tiktok_upload`
     hatırlatmasıyla AYNI kalıp; Hermes becerisi ve `tiktok_yayin_onayi.py`
     değişmedi.

KAPILAR (sırasıyla; hepsi fail-closed):
  * Önceki kit ONAYLANMADAN (`tiktok_published_at` yazılmadan) yenisi gitmez.
    NEDEN: bekleyen taslakların çoğu büyük olasılıkla zaten yayında; onaysız
    kitleri üst üste göndermek aynı şarkıyı ikinci kez yayınlatır. 48 saat sonra
    aynı kit için TEK hatırlatma, sonrası yalnız log. İstisna: bekleyen kitin
    taslağı API'de artık yoksa (`tiktok_status_denenmez`) sıra tıkanmaz — aksi
    hâlde silinmiş bir taslak kiti sonsuza kadar sessizce bekletirdi.
  * Koşu başına en fazla 1 (hatırlatma dahil).
  * Yalnız golden-hour içinde (`config.next_golden_publish_time`).
  * Tempo (`config.TIKTOK_KIT_*`, eşikler YALNIZ orada): iki kit arası en az
    36 saat, pencere başına 1, günde 1, son 7 günde 4.
  * Durum ön şartı: yalnız `tiktok_yayin_dogrulama`nın o taslak için
    `SEND_TO_USER_INBOX` OKUDUĞU, `tiktok_status_denenmez` ve
    `tiktok_published_at` olmayan taslak. Durum hiç okunmamışsa ya da okuma
    bayatsa (`TIKTOK_KIT_DURUM_TAZELIK_SAAT`) kit GİTMEZ — kullanıcı bu arada
    yayınlamış olabilir.
  * `build_plan()` `hazir=False` (ikiz/uyumluluk/`yayin_beklet`) → kit gitmez,
    engel operatöre BİR KEZ bildirilir (engel metninin sha1'i state'te; metin
    değişince bir kez daha). Engelli taslak arkadakileri TIKAMAZ: sıradaki
    uygun taslağa geçilir.

GİZLİLİK ÖNERİSİ "Herkes" — `build_plan`'daki `onerilen_gizlilik`
(SELF_ONLY) BURADA KULLANILMIYOR, bilerek: o kısıt denetlenmemiş bir API
istemcisinin DIRECT_POST'u içindir (TikTok denetimsiz istemcide SELF_ONLY
zorunlu kılıyor). Kullanıcı taslağı UYGULAMADAN elle yayınlıyor; orada böyle bir
kısıt yok. Plan alanı API/MCP yolu için anlamlı kalıyor; kitte ayrı ve açık bir
alan var (`onerilen_gizlilik_uygulama`).

STATE (projenin state.json'u, atomik `state_io`):
  * `tiktok_kit_gonderildi_at` + `tiktok_kit_kodu` — açıklama mesajı (2)
    BAŞARILIYSA yazılır. Kapak fotoğrafı başarısızsa log'a düşer, kit yine sayılır.
    Kod publish_id'den; proje yeniden yüklenirse eski kit kaydı yeni taslağı
    etkilemez.
  * `tiktok_kit_hatirlatildi_at` — tek hatırlatma.
  * `tiktok_kit_engel_bildirimi` — bildirilen engel metninin sha1'i.
  `tiktok_notified` bu kapılarda KULLANILMAZ (eski düz metin hatırlatmanın alanı).

ÜÇ SORU (CLAUDE.md):
  1. Kim çağırıyor? `auto_process.main()` `finally` → `_tiktok_yayin_dogrulama()`
     SONRASINDA `_tiktok_kit_sirasi()` → `kit_gonder_sirasi()`. Doğrulamadan
     sonra: aynı koşuda yayında bulunup işaretlenen taslağa kit gitmesin.
     `_is_fully_done()`'a EKLENMEDİ (seçenek B: kendi tempo tavanı olan süpürge).
  2. Hangi görev? Saatlik `auto_process.py`; yeni zamanlayıcı görevi yok.
  3. Çalışmadığını nasıl anlarız? Her koşuda TEK özet log satırı ("golden-hour
     dışında", "onay bekliyor", "kimse — durum bekleniyor" dahil); gönderim
     hataları ayrı satır. Telegram kurulu değilse `notify.uyar_bir_kez` satırı.

AĞ: bu modül HTTP istemcisi İÇE AKTARMAZ; gönderim yalnız `notify.send_photo`,
`notify.send_text`, `notify.send` üzerinden (yayın kanalı kapısı ve token maskesi
orada). Telegram'dan HİÇBİR ŞEY OKUMAZ — bot Hermes gateway'iyle paylaşılıyor.
"""

import argparse
import hashlib
import os
import struct
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import notify
import state_io
import tiktok_publish_plan as TPP
import uyumluluk
from gizli_maskele import maskele
from social_text import (ai_beyani_modu, build_tiktok_kit_caption, resolve_language,
                         tiktok_kit_turu)
from tiktok_upload import _load_meta, yayin_kodu
from tiktok_web import _ts as _web_ts, web_aktif

_ZAMAN = "%Y-%m-%dT%H:%M:%S"
SAAT = 3600
DURUM_TASLAKTA = "SEND_TO_USER_INBOX"
# TikTok açıklama sınırı: 2200 karakter (uygulama UTF-16 birimiyle sayıyor).
ACIKLAMA_SINIRI = 2200
# Telegram sendPhoto: "The photo must be at most 10 MB in size" (notify.send_photo
# aynı sınırda istek atmıyor; burada kit hazırlanırken önceden uyarılıyor).
FOTO_MAX_BAYT = 10 * 1024 * 1024
ONERILEN_GIZLILIK_UYGULAMA = "Herkes"

# Koşu (süreç) başına en fazla bir kit/hatırlatma.
_KOSUDA_GONDERILDI = False


# --------------------------------------------------------------------------
# Zaman
# --------------------------------------------------------------------------

def _damga(ts: float) -> str:
    return time.strftime(_ZAMAN, time.localtime(ts))


def _ts(metin):
    try:
        return time.mktime(time.strptime(str(metin), _ZAMAN))
    except (TypeError, ValueError, OverflowError):
        return None


def _tr(ts: float) -> datetime:
    return datetime.fromtimestamp(ts, config.TR_TZ)


def _golden_icinde(ts: float) -> bool:
    return config.next_golden_publish_time(_tr(ts)) is None


def _pencere(ts: float):
    """(TR tarihi, başlangıç, bitiş) — golden-hour dışındaysa None."""
    an = _tr(ts)
    for bas, bit in config.GOLDEN_HOURS:
        if bas <= an.hour < bit:
            return (an.date().isoformat(), bas, bit)
    return None


def _onerilen_saat(ts: float) -> str:
    p = _pencere(ts)
    if p:
        return "şimdi — bu golden-hour penceresi %02d:00'a kadar (TR saati)" % p[2]
    sonraki = config.next_golden_publish_time(_tr(ts))
    if sonraki is not None:
        for bas, bit in config.GOLDEN_HOURS:
            if sonraki.hour == bas:
                return "%s %02d:00-%02d:00 (TR saati)" % (sonraki.strftime("%d.%m"), bas, bit)
    return "golden-hour: %s (TR saati)" % ", ".join(
        "%02d:00-%02d:00" % gh for gh in config.GOLDEN_HOURS)


# --------------------------------------------------------------------------
# Kit içeriği
# --------------------------------------------------------------------------

def _ad(proje: str, meta: dict = None) -> str:
    if meta is None:
        try:
            meta = _load_meta(proje)
        except Exception:                                    # noqa: BLE001
            meta = {}
    return meta.get("title") or os.path.basename(os.path.abspath(proje))


def _resim_boyutu(yol: str):
    """(genişlik, yükseklik) — PNG/JPEG başlığından; okunamazsa None.

    PIL bu makinede kurulu değil ve yalnız iki sayı için bağımlılık eklemeye
    değmez: PNG'de IHDR, JPEG'de ilk SOF işareti."""
    try:
        with open(yol, "rb") as f:
            bas = f.read(24)
            if bas[:8] == b"\x89PNG\r\n\x1a\n" and bas[12:16] == b"IHDR":
                return struct.unpack(">II", bas[16:24])
            if bas[:2] != b"\xff\xd8":
                return None
            f.seek(2)
            while True:
                isaret = f.read(2)
                if len(isaret) < 2 or isaret[0] != 0xFF:
                    return None
                kod = isaret[1]
                uzunluk = struct.unpack(">H", f.read(2))[0]
                if kod in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                           0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    veri = f.read(5)
                    h, w = struct.unpack(">HH", veri[1:5])
                    return w, h
                f.seek(uzunluk - 2, 1)
    except (OSError, struct.error, IndexError):
        return None


def _ayarlar(ai_mod: str) -> list:
    """Telefonda elle uygulanacak ayarlar: [(ad, değer)].

    ADLAR: Türkçe arayüzde resmî kaynakla doğrulanan TEK ad "Yapay zekayla
    üretilen içerik" (TikTok destek sayfası; + → Daha fazla seçenek altında).
    Diğerlerinin Türkçe adı DOĞRULANMADI — İngilizce arayüzdeki karşılığı
    parantezde, kullanıcı hangisini görürse onu bulabilsin.

    AI satırı `config.TIKTOK_AI_BEYANI`'ndan üretiliyor (koda sabit değil):
    politika araştırması sürüyor; "aciklama" modunda beyan açıklamaya giriyor.
    """
    if "etiket" in ai_mod:
        ai_deger = ("AÇIK — Daha fazla seçenek (More options) içinde; yayından "
                    "sonra kaldırılamaz")
    else:
        # Varsayılan (kullanıcı kararı 2026-09-13).
        ai_deger = ("KAPALI — beyan açıklamada; TikTok kuralları açıklamada yazılı "
                    "beyanı kabul ediyor")
    return [
        ("Kapak", "Kapağı düzenle (Edit cover) → Yükle (Upload) → 1. mesajdaki "
                  "fotoğraf (önce galeriye kaydet)"),
        ("Açıklama", "2. mesajı olduğu gibi yapıştır — düzenleme, kısaltma"),
        ("Kimler izleyebilir (Who can watch)", "Herkes (Everyone)"),
        ("Yorumlara izin ver (Allow comments)", "AÇIK"),
        ("Düet (Duet)", "AÇIK"),
        ("Stitch", "AÇIK"),
        ("Yapay zekayla üretilen içerik", ai_deger),
        ("İçerik açıklaması / marka içeriği (Disclose post content / Branded "
         "content)", "KAPALI"),
        ("Konum (Location)", "ekleme"),
        ("Yüksek kaliteli yükleme (Upload HD)", "AÇIK"),
        ("Ses / müzik ekleme (Add sound)", "EKLEME — videoda şarkının kendisi çalıyor"),
    ]


def build_kit(proje: str) -> dict:
    """Kitin tamamı tek sözlükte — HİÇBİR ŞEY GÖNDERMEZ.

    `build_plan()` ÇAĞRILIYOR (mantık kopyalanmadı): politika kapısı, ikiz kapısı,
    ilk yorum ve kapak oradan. Açıklama TikTok'a özel
    (`social_text.build_tiktok_kit_caption`); plandaki `caption` diğer yolların
    arşiv metni olarak aynen kalıyor.
    """
    plan = TPP.build_plan(proje)
    meta = _load_meta(proje)
    durum = TPP._durum_oku(proje)
    ai_mod, ai_gecerli = ai_beyani_modu()
    aciklama = build_tiktok_kit_caption(meta, ai_beyani=ai_mod)

    uyarilar = [maskele(u) for u in (plan.get("uyumluluk_uyarilari") or [])]
    if not ai_gecerli:
        uyarilar.append("config.TIKTOK_AI_BEYANI tanınmıyor (%r) — fail-closed: AI "
                        "etiketi AÇIK + açıklamada beyan birlikte" % config.TIKTOK_AI_BEYANI)
    kapak = plan.get("kapak")
    if not kapak:
        uyarilar.append("kapak dosyası yok — TikTok'ta özel kapak yüklenemeyecek")
    else:
        boyut = _resim_boyutu(kapak)
        if boyut is None:
            uyarilar.append("kapak boyutu okunamadı (%s)" % os.path.basename(kapak))
        elif abs(boyut[0] * 16 - boyut[1] * 9) > 0.01 * boyut[1] * 9:
            uyarilar.append("kapak 9:16 değil (%dx%d) — TikTok kırpar; dikey kapak "
                            "(cover_vertical) üret" % boyut)
        try:
            if os.path.getsize(kapak) > FOTO_MAX_BAYT:
                uyarilar.append("kapak 10 MB'tan büyük — Telegram fotoğrafı reddeder")
        except OSError:
            pass
    if len(aciklama.encode("utf-16-le")) // 2 > ACIKLAMA_SINIRI:
        uyarilar.append("açıklama %d karakter sınırını aşıyor" % ACIKLAMA_SINIRI)

    return {
        "proje": proje,
        "ad": _ad(proje, meta),
        "baslik": plan.get("baslik") or _ad(proje, meta),
        "kod": yayin_kodu(durum.get("tiktok_publish_id")),
        "tur": tiktok_kit_turu(meta),
        "dil": resolve_language(meta),
        "hazir": bool(plan.get("hazir")),
        "engel": plan.get("engel"),
        "aciklama": aciklama,
        "ilk_yorum": plan.get("ilk_yorum"),
        "kapak": kapak,
        "onerilen_gizlilik_uygulama": ONERILEN_GIZLILIK_UYGULAMA,
        # Yalnız bilgi: API/MCP DIRECT_POST yolunun önerisi (bkz. modül docstring).
        "api_onerilen_gizlilik": plan.get("onerilen_gizlilik"),
        "ai_beyani": ai_mod,
        "ayarlar": _ayarlar(ai_mod),
        "uyarilar": uyarilar,
    }


def _onay_satirlari(baslik: str, kod: str) -> str:
    # `tiktok_upload.notify_pending_publish` ile AYNI kalıp — Hermes becerisi
    # bu satırı `tiktok_yayin_onayi.py`ye olduğu gibi veriyor.
    return ("Yayınladıysan bu sohbete yaz: yayınladım %s\n"
            "(kod: %s — ad yerine 'yayınladım %s' de olur)" % (baslik, kod, kod))


def kit_mesajlari(kit: dict, simdi: float = None) -> list:
    """Gönderim sırasıyla mesajlar: [{"anahtar", "metin", "yol"}]."""
    t = time.time() if simdi is None else simdi
    baslik = kit["baslik"]
    kod = kit["kod"] or "kod yok"
    mesajlar = []
    if kit["kapak"]:
        mesajlar.append({
            "anahtar": "kapak", "yol": kit["kapak"],
            "metin": ("TikTok yayın kiti: %s (%s)\nKapak — galeriye kaydet; TikTok'ta "
                      "Kapağı düzenle → Yükle." % (baslik, kod))})
    mesajlar.append({"anahtar": "aciklama", "yol": None, "metin": kit["aciklama"]})

    satirlar = ["TikTok ayarları — %s (%s)" % (baslik, kod),
                "Taslağı aç: Gelen kutusu / Taslaklar → bu video", ""]
    satirlar += ["• %s → %s" % (ad, deger) for ad, deger in kit["ayarlar"]]
    satirlar += ["", "Önerilen saat: %s" % _onerilen_saat(t)]
    if kit["ilk_yorum"]:
        satirlar.append("Yayından sonra: sonraki mesajdaki ilk yorumu ekle.")
    else:
        satirlar.append("İlk yorum yok (YouTube bağlantısı kayıtlı değil).")
    for u in kit["uyarilar"]:
        satirlar.append("UYARI: %s" % u)
    mesajlar.append({"anahtar": "ayarlar", "yol": None, "metin": "\n".join(satirlar)})

    if kit["ilk_yorum"]:
        mesajlar.append({"anahtar": "ilk_yorum", "yol": None, "metin": kit["ilk_yorum"]})
    mesajlar.append({"anahtar": "onay", "yol": None,
                     "metin": _onay_satirlari(baslik, kod)})
    return mesajlar


# --------------------------------------------------------------------------
# Sıra ve kapılar
# --------------------------------------------------------------------------

def _kit_kodu_guncel(d: dict) -> bool:
    kod = yayin_kodu(d.get("tiktok_publish_id"))
    return bool(kod) and d.get("tiktok_kit_kodu") == kod


def _onay_bekliyor(d: dict) -> bool:
    # Web'de planlanan (tiktok_web.py) taslağın kiti artık onay BEKLEMEZ: gönderiyi
    # TikTok Studio yayınlayacak; sıra tıkanmaz, 48 sa hatırlatması da gitmez.
    return (bool(d.get("tiktok_kit_gonderildi_at")) and _kit_kodu_guncel(d)
            and not d.get("tiktok_published_at") and not d.get("tiktok_status_denenmez")
            and not web_aktif(d))


def siradaki_kit_adayi(projeler, simdi: float) -> dict:
    """Sıradaki kit adayı — GÖNDERMEZ, YAZMAZ (build_plan salt okunur).

    Döner: {"aday": proje|None, "engelliler": [(proje, ad, engel)], "sebep": str,
    "durum_yok": [...], "bayat": [...], "baska_durum": [(ad, durum)]}.
    Uygun taslaklar en eski yüklemeden başlayarak `build_plan`'dan geçirilir;
    ilk `hazir=True` aday olur, öncekiler engelli listesine yazılır (arkadakini
    tıkamaz). Tempo kapıları burada DEĞİL, `kit_gonder_sirasi`nda.
    """
    tazelik = float(config.TIKTOK_KIT_DURUM_TAZELIK_SAAT) * SAAT
    sonuc = {"aday": None, "engelliler": [], "sebep": "", "durum_yok": [],
             "bayat": [], "baska_durum": []}
    uygun = []
    for proje in projeler:
        d = TPP._durum_oku(proje)
        if (not d.get("tiktok_publish_id") or d.get("tiktok_published_at")
                or d.get("tiktok_status_denenmez") or web_aktif(d)):
            continue                                  # web planlı (tiktok_web.py): kit YOK
        if d.get("tiktok_kit_gonderildi_at") and _kit_kodu_guncel(d):
            continue                                  # bu taslağın kiti zaten gitti
        ad = _ad(proje)
        durum = d.get("tiktok_publish_status")
        if not durum:
            sonuc["durum_yok"].append(ad)
            continue
        if durum != DURUM_TASLAKTA:
            sonuc["baska_durum"].append((ad, str(durum)))
            continue
        okundu = _ts(d.get("tiktok_status_checked_at"))
        if okundu is None or simdi - okundu > tazelik:
            sonuc["bayat"].append(ad)
            continue
        uygun.append((str(d.get("tiktok_uploaded_at") or ""), ad, proje, d))
    uygun.sort(key=lambda x: (x[0], x[1]))

    for _, ad, proje, d in uygun:
        try:
            plan = TPP.build_plan(proje)
        except Exception as e:                               # noqa: BLE001
            plan = {"hazir": False, "engel": "plan hesaplanamadı (%s)" % type(e).__name__}
        if plan.get("hazir"):
            sonuc["aday"] = proje
            sonuc["sebep"] = "sıradaki: %s (%s)" % (ad, yayin_kodu(d.get("tiktok_publish_id")))
            return sonuc
        sonuc["engelliler"].append((proje, ad, str(plan.get("engel") or "sebep bilinmiyor")))

    parcalar = []
    if sonuc["durum_yok"]:
        parcalar.append("durum bekleniyor (%d taslakta API durumu hiç okunmadı)"
                        % len(sonuc["durum_yok"]))
    if sonuc["bayat"]:
        parcalar.append("durum bayat (%d taslak, %s saatten eski okuma)"
                        % (len(sonuc["bayat"]), config.TIKTOK_KIT_DURUM_TAZELIK_SAAT))
    if sonuc["engelliler"]:
        parcalar.append("plan engeli: %s" % ", ".join(a for _, a, _ in sonuc["engelliler"]))
    if sonuc["baska_durum"]:
        parcalar.append("başka durum: %s" % ", ".join(
            "%s=%s" % x for x in sonuc["baska_durum"]))
    sonuc["sebep"] = "kimse — " + ("; ".join(parcalar) if parcalar
                                   else "bekleyen taslak yok")
    return sonuc


def _tempo_engeli(durumlar, t: float):
    """Tempo kapısı; engel varsa sebep metni, yoksa None. Eşikler config'ten.

    WEB PLANLARI (tiktok_web.py, 2026-09-13) da TikTok gönderisidir: etkin bir web
    planının anına `TIKTOK_KIT_ARALIK_SAAT`ten yakın ya da aynı TR gününde kit gitmez."""
    aralik_web = float(config.TIKTOK_KIT_ARALIK_SAAT) * SAAT
    for _, d in durumlar:
        w = d.get("tiktok_web") if web_aktif(d) else None
        an = _web_ts(w.get("planlanan_an")) if isinstance(w, dict) else None
        if an is None:
            continue
        if abs(t - an) < aralik_web or _tr(an).date() == _tr(t).date():
            return ("TikTok web planı %s — kit ile arası en az %s saat ve aynı gün değil"
                    % (_damga(an), config.TIKTOK_KIT_ARALIK_SAAT))
    gonderimler = sorted(g for g in (_ts(d.get("tiktok_kit_gonderildi_at"))
                                     for _, d in durumlar)
                         if g is not None and g <= t)
    if not gonderimler:
        return None
    son = gonderimler[-1]
    aralik = float(config.TIKTOK_KIT_ARALIK_SAAT) * SAAT
    if t - son < aralik:
        return ("son kit %s — iki kit arası en az %s saat (kalan ~%.1f sa)"
                % (_damga(son), config.TIKTOK_KIT_ARALIK_SAAT, (aralik - (t - son)) / SAAT))
    p = _pencere(t)
    if p is not None and _pencere(son) == p:
        return "bu golden-hour penceresinde zaten bir kit gitti (%s)" % _damga(son)
    bugun = _tr(t).date()
    gunluk = sum(1 for g in gonderimler if _tr(g).date() == bugun)
    if gunluk >= config.TIKTOK_KIT_GUNLUK_TAVAN:
        return "günlük tavan dolu (%d/%d)" % (gunluk, config.TIKTOK_KIT_GUNLUK_TAVAN)
    haftalik = sum(1 for g in gonderimler if t - g < 7 * 24 * SAAT)
    if haftalik >= config.TIKTOK_KIT_HAFTALIK_TAVAN:
        return "haftalık tavan dolu (%d/%d, son 7 gün)" % (
            haftalik, config.TIKTOK_KIT_HAFTALIK_TAVAN)
    return None


def _yaz(proje: str, pid, degistir, log) -> bool:
    """state.json'u yazımdan HEMEN önce taze okuyup `degistir` uygular.
    Okunamıyorsa YAZMAZ; publish_id bu arada değiştiyse eski taslağın kaydı yeni
    kayda yazılmaz (`tiktok_yayin_dogrulama._guncelle` ile aynı desen)."""
    try:
        durum = TPP._durum_oku_kesin(proje)
        if str(durum.get("tiktok_publish_id")) != str(pid):
            return False
        degistir(durum)
        state_io.durum_yaz(proje, durum)
        return True
    except (TPP.IsaretlemeHatasi, OSError) as e:
        log("  TikTok kit: '%s' state yazılamadı — %s" % (_ad(proje), maskele(str(e))[:200]))
        return False


def _guvenli(fn, log, *args) -> bool:
    try:
        return fn(*args) is True
    except Exception as e:                                   # noqa: BLE001
        log("  TikTok kit: gönderim istisnası (%s)" % type(e).__name__)
        return False


def _engelleri_bildir(engelliler, gonder, log, sonuc) -> None:
    yeni = []
    for proje, ad, engel in engelliler:
        metin = " ".join(maskele(engel).split())[:300]
        ozet = hashlib.sha1(metin.encode("utf-8")).hexdigest()
        if TPP._durum_oku(proje).get("tiktok_kit_engel_bildirimi") == ozet:
            continue
        yeni.append((proje, ad, metin, ozet))
    if not yeni:
        return
    mesaj = ("Bu taslaklara TikTok yayın kiti GÖNDERİLMEDİ — plan engeli var, "
             "yayınlama:\n" + "\n".join("- %s: %s" % (ad, metin) for _, ad, metin, _ in yeni)
             + "\nEngel kalkınca kit sıraya kendiliğinden girer.")
    if not _guvenli(gonder, log, "TikTok kit engeli", mesaj):
        log("  TikTok kit: engel bildirimi gitmedi (%s) — sonraki koşu yeniden dener"
            % ", ".join(ad for _, ad, _, _ in yeni))
        return
    for proje, ad, _, ozet in yeni:
        pid = TPP._durum_oku(proje).get("tiktok_publish_id")
        _yaz(proje, pid, lambda d, o=ozet: d.__setitem__("tiktok_kit_engel_bildirimi", o), log)
        sonuc["engel_bildirilen"].append(ad)


def kit_gonder_sirasi(log=print, simdi: float = None, projeler=None,
                      gonder_foto=None, gonder_metin=None, gonder=None) -> dict:
    """Kapılardan geçen EN FAZLA bir kiti (ya da tek hatırlatmayı) gönderir.

    Hiçbir hata yukarı çıkmaz; her koşuda tek özet log satırı bırakır.
    """
    global _KOSUDA_GONDERILDI
    sonuc = {"gonderilen": None, "hatirlatilan": None, "engel_bildirilen": [], "sebep": ""}
    # 0. ANA ŞALTER (config.TIKTOK_KIT_AKTIF) — hatırlatma ve engel bildirimi DAHİL
    # her şeyin önünde: kapalıyken hiçbir gönderici çağrılmaz, state OKUNMAZ/YAZILMAZ,
    # yalnız tek log satırı (sessiz kalmasın — ÜÇ SORU #3).
    if not getattr(config, "TIKTOK_KIT_AKTIF", False):
        sonuc["sebep"] = "kit kapalı (config)"
        log("  TikTok kit: kit kapalı (config)")
        return sonuc
    t = time.time() if simdi is None else simdi
    foto = gonder_foto or notify.send_photo
    metin = gonder_metin or notify.send_text
    gonder = gonder or notify.send
    # list(): proje_klasorleri() bir ÜRETEÇ — iki kez gezildiği için (durumlar +
    # aday seçimi) listeye çevrilmezse ikinci gezinti BOŞ kalır ve kit "bekleyen
    # taslak yok" diye sessizce hiç gitmez (testte yakalandı).
    projeler = list(uyumluluk.proje_klasorleri() if projeler is None else projeler)

    durumlar = [(p, TPP._durum_oku(p)) for p in projeler]

    # 1. Önceki kit onay bekliyor mu?
    bekleyen = sorted(((p, d) for p, d in durumlar if _onay_bekliyor(d)),
                      key=lambda x: str(x[1].get("tiktok_kit_gonderildi_at")))
    if bekleyen:
        proje, d = bekleyen[0]
        ad = _ad(proje)
        gitti = _ts(d.get("tiktok_kit_gonderildi_at"))
        yas = (t - gitti) / SAAT if gitti is not None else 0.0
        if (not d.get("tiktok_kit_hatirlatildi_at") and gitti is not None
                and yas >= float(config.TIKTOK_KIT_HATIRLATMA_SAAT)
                and _golden_icinde(t) and not _KOSUDA_GONDERILDI):
            kod = yayin_kodu(d.get("tiktok_publish_id"))
            mesaj = ("'%s' için %d saat önce TikTok yayın kiti gönderildi, onay gelmedi.\n"
                     "%s\nYayınlamadıysan taslak TikTok gelen kutusunda, kit mesajları "
                     "yukarıda. Bu TEK hatırlatma — sıradaki kit bu onayı bekliyor."
                     % (ad, int(yas), _onay_satirlari(ad, kod)))
            if _guvenli(gonder, log, "TikTok yayın kiti hatırlatma", mesaj):
                _KOSUDA_GONDERILDI = True
                _yaz(proje, d.get("tiktok_publish_id"),
                     lambda x: x.__setitem__("tiktok_kit_hatirlatildi_at", _damga(t)), log)
                sonuc["hatirlatilan"] = ad
                sonuc["sebep"] = "hatırlatma gönderildi"
                log("  TikTok kit: '%s' için tek hatırlatma gönderildi (%d saattir onay yok)"
                    % (ad, int(yas)))
                return sonuc
            log("  TikTok kit: '%s' hatırlatması gönderilemedi — sonraki koşu yeniden dener" % ad)
        sonuc["sebep"] = "onay bekleniyor"
        log("  TikTok kit: önceki kit onay bekliyor — '%s' (gönderim %s, %d saat%s); yeni kit "
            "gönderilmedi" % (ad, d.get("tiktok_kit_gonderildi_at"), int(yas),
                              ", hatırlatıldı" if d.get("tiktok_kit_hatirlatildi_at") else ""))
        return sonuc

    # 2. Koşu başına bir.
    if _KOSUDA_GONDERILDI:
        sonuc["sebep"] = "bu koşuda zaten gönderildi"
        log("  TikTok kit: bu koşuda zaten bir kit/hatırlatma gitti")
        return sonuc

    # 3. Golden-hour.
    if not _golden_icinde(t):
        sonuc["sebep"] = "golden-hour dışında"
        log("  TikTok kit: golden-hour dışında — kit yok")
        return sonuc

    # 4. Tempo.
    engel = _tempo_engeli(durumlar, t)
    if engel:
        sonuc["sebep"] = engel
        log("  TikTok kit: tempo — %s" % engel)
        return sonuc

    # 5. Aday.
    secim = siradaki_kit_adayi(projeler, t)
    _engelleri_bildir(secim["engelliler"], gonder, log, sonuc)
    if not secim["aday"]:
        sonuc["sebep"] = secim["sebep"]
        log("  TikTok kit: %s" % secim["sebep"])
        return sonuc

    proje = secim["aday"]
    try:
        kit = build_kit(proje)
    except Exception as e:                                   # noqa: BLE001
        sonuc["sebep"] = "kit hazırlanamadı"
        log("  TikTok kit: '%s' kiti hazırlanamadı (%s)" % (_ad(proje), type(e).__name__))
        return sonuc
    if not kit["hazir"]:
        sonuc["sebep"] = "plan engeli (son kontrol)"
        log("  TikTok kit: '%s' son kontrolde engellendi — %s"
            % (kit["baslik"], maskele(str(kit["engel"]))[:200]))
        return sonuc

    baslik = kit["baslik"]
    pid = TPP._durum_oku(proje).get("tiktok_publish_id")
    if not kit["kapak"]:
        log("  TikTok kit: '%s' kapak dosyası yok — fotoğraf mesajı atlandı" % baslik)
    for m in kit_mesajlari(kit, t):
        if m["anahtar"] == "kapak":
            if not _guvenli(foto, log, m["yol"], m["metin"]):
                log("  TikTok kit: '%s' kapak fotoğrafı GÖNDERİLEMEDİ (%s) — kit yine sayılıyor"
                    % (baslik, os.path.basename(m["yol"])))
            continue
        tamam = _guvenli(metin, log, m["metin"])
        if m["anahtar"] == "aciklama":
            if not tamam:
                sonuc["sebep"] = "açıklama gönderilemedi"
                log("  TikTok kit: '%s' açıklama mesajı gönderilemedi — kit SAYILMADI, "
                    "sonraki uygun koşu yeniden dener" % baslik)
                return sonuc
            _KOSUDA_GONDERILDI = True
            kod = kit["kod"]

            def _kaydet(d, kod=kod):
                d["tiktok_kit_gonderildi_at"] = _damga(t)
                d["tiktok_kit_kodu"] = kod
                d.pop("tiktok_kit_hatirlatildi_at", None)
            _yaz(proje, pid, _kaydet, log)
            sonuc["gonderilen"] = baslik
        elif not tamam:
            log("  TikTok kit: '%s' %s mesajı gönderilemedi — kit sayıldı"
                % (baslik, m["anahtar"]))
    sonuc["sebep"] = "kit gönderildi"
    log("  TikTok kit: '%s' (%s) gönderildi — onay bekleniyor ('yayınladım %s')"
        % (baslik, kit["kod"], baslik))
    return sonuc


# --------------------------------------------------------------------------
# CLI — yalnız önizleme
# --------------------------------------------------------------------------

def main(argv=None) -> int:
    TPP._cikti_utf8()
    ap = argparse.ArgumentParser(
        description="TikTok yayın kitini önizler (HİÇBİR ŞEY GÖNDERMEZ, state yazmaz).")
    ap.add_argument("--project", required=True, help="Proje klasörü")
    ap.add_argument("--onizle", action="store_true", required=True,
                    help="Kit mesajlarını sırasıyla bas (tek desteklenen mod)")
    args = ap.parse_args(argv)

    kit = build_kit(args.project)
    mesajlar = kit_mesajlari(kit)
    print("Proje : %s (%s) — tür: %s, kod: %s" % (kit["ad"], kit["proje"], kit["tur"], kit["kod"]))
    print("Hazır : %s%s" % (kit["hazir"], "" if kit["hazir"] else "  <- " + str(kit["engel"])))
    print("Gizlilik önerisi (uygulama): %s | API/MCP yolu: %s | AI beyanı: %s"
          % (kit["onerilen_gizlilik_uygulama"], kit["api_onerilen_gizlilik"], kit["ai_beyani"]))
    for i, m in enumerate(mesajlar, 1):
        print("")
        baslik = "=== [%d/%d] %s" % (i, len(mesajlar), m["anahtar"])
        if m["yol"]:
            baslik += " — fotoğraf: %s" % m["yol"]
        print(baslik + " ===")
        print(m["metin"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
