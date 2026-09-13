# -*- coding: utf-8 -*-
"""Yayın sonrası TÜREV TAKVİMİ — Aşama 1: salt plan + görünürlük (2026-09-13).

Kaynak: `yayin_sonrasi_takvim_plani.md` (§1 türler, §2 kurallar, §3 veri modeli,
§6 Aşama 1). BU AŞAMADA HİÇBİR ŞEY YAYINLANMAZ ve render edilmez. Modül yalnız:
  * her projenin `state.json`'ına `turev_plani` listesini yazar (`plan_uret`,
    `state_io` ile, yalnız EKSİK kayıtları ekler, mevcutları ezmez),
  * tüm katalog için çakışma çözümlü bir takvim TÜRETİR (`takvim`, salt okuma),
  * elle yapılacak türevler için bayrakla açılan TEK günlük Telegram
    hatırlatması gönderir (`hatirlatma_sirasi`, `config.TUREV_HATIRLATMA_AKTIF`,
    varsayılan KAPALI).

KURALLAR (kullanıcı kararları 2026-09-13, sayıların hepsi `config.TUREV_*`):
  * Türevler 52 saatlik yeni yayın tabanına SAYILMAZ; türev state anahtarları
    `auto_process.UPLOAD_TIMESTAMP_KEYS` / `YENI_YAYIN_*` demetlerine GİRMEZ
    (kayıt içi alanlar; `tests/test_turev_takvimi.py` ast ile kilitli).
  * Günde en fazla 1 yüzey türevi, yalnız golden-hour; YouTube'a video yükleyen
    türev kayan 7 günde 1 (DJ kesit damgası `youtube_clip_uploaded_at` ortak
    sayaç); yeni yayın anının ±24 saatinde türev yok; aynı projenin iki yüzey
    türevi arası ≥48 saat; pencere T0 + 21 gün.
  * Yeni şarkı yayınları ÖNCELİKLİ: bant olarak okunur, türev yalnız İLERİ kayar,
    `en_gec`'i aşarsa takvimde "iptal_cakisma" görünür (state'e YAZILMAZ).
  * `yayin_beklet` / `kopya_notu` / telif işareti / Content ID engeli / gerçek
    gizliliği public olmayan proje -> türevlerin HEPSİ durur. `kesit_beklet`
    yalnız `dj_kesit` türünü durdurur.
  * Şarkı için YouTube ikinci kesiti `TUREV_SARKI_YOUTUBE_KESIT_KAPI`'dan önce
    hiç planlanmaz; DJ kulisi `TUREV_DJ_KULIS_ONAYLI` ister.
  * "Yüzey" olmayan türler (Studio işleri, D+7 kararı, derleme adaylığı) yeni bir
    kamuya açık gönderi değildir: tavanlara ve bantlara SAYILMAZ, yalnız tarihlenir.

ÜÇ SORU:
  1. Kim çağırıyor? `auto_process.main()` `finally` -> `_turev_takvimi()` ->
     `sirasi(log)` (plan + hatırlatma + tek özet satırı). Okuyanlar:
     `weekly_report._turev_bolumu` (günlük rapor "Bugün/yarın türev"),
     `elle_islem._state_yansit` (yayinladi -> `elle_yayin_eslestir`), pano ve
     sesli asistan için `python turev_takvimi.py takvim --json`.
  2. Hangi zamanlayıcı görevinden? Saatlik AutoProcess. Yeni görev YOK.
     `_is_fully_done`'a EKLENMEDİ (Kalıp B süpürge).
  3. Çalışmadığını nasıl anlarız? Her koşuda tek "  Türev takvimi: ..." log
     satırı; satır yoksa kanca çağrılmıyor. Testler: tests/test_turev_takvimi.py.

YAZIM KORUMASI: `PYTEST_CURRENT_TEST` ortamında GERÇEK köklerin (uyumluluk.KOKLER)
altındaki bir state'e yazma REDDEDİLİR (`elle_islem` deseni).

CLI (varsayılan KURU):
    python turev_takvimi.py plan --proje "Sabah Senin" [--uygula] [--json]
    python turev_takvimi.py takvim --gun 7 [--json]
    python turev_takvimi.py sirada [--json]
    python turev_takvimi.py iptal TRV-sabah-senin-kulis [--sebep "..."]
    python turev_takvimi.py plan --kanal soz_defteri --hedef 2026-09-15T20:30:00+03:00 \
        --baslik "Söz Defteri #1 — Sabah Senin" [--ilgili-proje "Sabah Senin"] [--uygula]

KANAL GENELİ İNSAN EMEĞİ GÖNDERİLERİ (TikTok LIVE planı, kullanıcı kararı 2026-09-13):
  "Söz Defteri" / "Kulis" (TikTok, elle) projeye bağlı DEĞİL -> `kanal_takvimi.json`
  (repo kökü, `config.TUREV_KANAL_TAKVIMI`). Kurallar: TR takvim haftasında en fazla
  `TUREV_INSAN_EMEGI_HAFTALIK_TAVAN`; şarkı kesiti tavanlarına (TIKTOK_KIT_*,
  TUREV_GUNLUK_TAVAN) SAYILMAZ; şarkı kesitiyle (türev kesiti, TikTok web planı/yayını/
  kiti) AYNI GÜN yok; yeni yayın ±24 sa yok; golden-hour; aynı gün ikinci insan emeği yok.
  Kesit ÖNCELİKLİ: gönderi en fazla `TUREV_INSAN_EMEGI_KAYMA_GUN` gün ileri kayar.
  Takvimde `olaylar`a DEĞİL `kanal_gonderileri`ne girer: tiktok_web ve hatırlatma yalnız
  `olaylar`ı okur, yani kesit tavanını yemez ve Telegram hatırlatması gitmez.
"""

import argparse
import datetime
import json
import os
import sys
import time
import unicodedata

_KOK = os.path.dirname(os.path.abspath(__file__))
if _KOK not in sys.path:
    sys.path.insert(0, _KOK)
if os.path.join(_KOK, "upload") not in sys.path:
    sys.path.append(os.path.join(_KOK, "upload"))

import config                                             # noqa: E402
import state_io                                           # noqa: E402
import uyumluluk                                          # noqa: E402

TR = config.TR_TZ
SAAT = 3600
GUN_SN = 24 * SAAT
SURUM = 1

DURUMLAR = ("planlandi", "hazirlandi", "onay_bekliyor", "yayinlandi", "iptal")
_ACIK_DURUMLAR = ("planlandi", "hazirlandi")
_RISK_SIRASI = {"dusuk": 0, "dusuk_orta": 1, "orta": 2}

# Yazım koruması: import anındaki GERÇEK kökler (testler uyumluluk.KOKLER'i
# sonradan tmp'ye çekse bile bu demet gerçek klasörleri gösterir).
GERCEK_KOKLER = tuple(uyumluluk.KOKLER)

# DJ koşusu state'e yazarken plan/hatırlatma o kökte yazmaz (iki süreç, iki kilit).
DJ_KILIT_YOLU = os.path.join(_KOK, ".dj_famous_process.lock")
DJ_KILIT_TAZE_SN = 4 * SAAT

# Yeni yayın tabanı: tahmini yeni şarkı anı için. Tek doğruluk kaynağı
# `auto_process.MIN_YAYIN_ARALIGI_SN`; auto_process ağır bir import olduğu için
# yalnız zaten yüklüyse oradan okunur (saatlik koşuda her zaman yüklü).
_YENI_YAYIN_TABANI_VARSAYILAN = 52 * SAAT


class TurevHatasi(ValueError):
    """Doğrulama / yazma reddi — mesaj kullanıcıya olduğu gibi gösterilir."""


# --------------------------------------------------------------------------
# Tür tanımları
# --------------------------------------------------------------------------
# gun/saat: hedef = T0 tarihinden `gun` gün sonra `saat`:00 (TR); saat None ise
# T0 + 1 saat. en_gec_gun: o günün 22:00'si (T0 + TUREV_PENCERE_GUN ile kırpılır).
# yuzey: yeni bir kamuya açık gönderi mi (tavan ve bantlara sayılır mı).

def _tur(tur, ad, platform, gun, saat, en_gec_gun, risk, yuzey=True, elle=True,
         youtube_video=False, kosul=None, dosyalar=(), aciklama=""):
    return {"tur": tur, "ad": ad, "platform": platform, "gun": gun, "saat": saat,
            "en_gec_gun": en_gec_gun, "risk": risk, "yuzey": yuzey, "elle": elle,
            "youtube_video": youtube_video, "kosul": kosul, "dosyalar": list(dosyalar),
            "aciklama": aciklama}


_D7 = "d7_karar=ac"

TUR_TANIMLARI = {
    "projects": [
        _tur("studio_isleri", "Yayın sonrası Studio işleri", "youtube", 0, None, 1, "dusuk",
             yuzey=False, dosyalar=("cover.png", "cover_vertical.png"),
             aciklama="Shorts -> ilgili video, sabitlenmiş yorum, kapak doğrulaması"),
        _tur("topluluk_soz_anket", "Topluluk gönderisi (söz + anket)", "youtube", 1, 12, 5,
             "dusuk", dosyalar=("cover.png",),
             aciklama="Temiz Sözler'den bir beyit + 2-3 seçenekli anket, Studio'da"),
        _tur("carousel_soz_kartlari", "Instagram Carousel (söz kartları)", "instagram", 4, 18,
             10, "dusuk_orta", dosyalar=("output/turev/carousel_*.png",),
             aciklama="4-6 söz kartı; caption'da AI beyan satırı"),
        _tur("kulis", "Kulis gönderisi (nasıl yapıldı)", "youtube", 7, 18, 14, "dusuk",
             aciklama="Söz yazım sürecinden 3-5 madde; metni düzeltip öyle yayınla"),
        _tur("d7_karar", "D+7 karar noktası", "rapor", 7, 12, 9, "dusuk", yuzey=False,
             elle=False, aciklama="Koşullu türevler açılsın mı (izlenme medyanı)"),
        _tur("derleme_adayligi", "Derleme adaylığı notu", "rapor", None, 12, 21, "dusuk",
             yuzey=False, elle=False, aciklama="Ayın 3. Pazartesi'si derleme havuzu"),
        _tur("tg_bs_hatirlatma", "Telegram + Bluesky hatırlatma", "telegram", 9, 12, 16,
             "dusuk_orta", elle=False, kosul=_D7,
             aciklama="Metin + YouTube linki (günlük tavan 1'e dahil)"),
        _tur("tiktok_ikinci_kesit", "TikTok ikinci kesit", "tiktok", 11, 18, 21, "orta",
             kosul=_D7, dosyalar=("output/turev_kesit_9x16.mp4",),
             aciklama="İkinci en enerjili 45 sn (TikTok kit tavanlarına dahil)"),
        _tur("sarki_youtube_kesit", "YouTube ikinci kesit (Shorts)", "youtube_shorts", 10, 18,
             21, "orta", elle=False, youtube_video=True,
             aciklama="Yalnız kapı tarihinden sonra ve bayrakla"),
    ],
    "dj_sets": [
        _tur("studio_isleri", "Studio işleri (bölümler)", "youtube", 0, None, 7, "dusuk",
             yuzey=False, aciklama="Açıklamaya bölümler; telif aralığı bölüm adına yazılmaz"),
        _tur("topluluk_set_anlari", "Topluluk gönderisi (setin 3 anı + anket)", "youtube", 2,
             18, 7, "dusuk", dosyalar=("cover.png",),
             aciklama="Kesit dakika damgaları + 'hangisi?' anketi"),
        _tur("kulis", "Kulis gönderisi (DJ Famous onaylı)", "youtube", 7, 18, 14, "dusuk",
             aciklama="Gerçek kişi: ayrı onay (config.TUREV_DJ_KULIS_ONAYLI)"),
        _tur("d7_karar", "D+7 karar noktası", "rapor", 7, 12, 9, "dusuk", yuzey=False,
             elle=False, aciklama="Kesit seçimi: izlenme tepe anı"),
        _tur("dj_kesit", "DJ kesiti (YouTube Shorts)", "youtube_shorts", 10, 18, 21, "orta",
             elle=False, youtube_video=True, dosyalar=("output/clip_*.mp4",),
             aciklama="dj_clips süpürgesi yayınlar (bu aşamada bağımsız)"),
        _tur("tiktok_ikinci_kesit", "TikTok kesit", "tiktok", 14, 18, 21, "orta", kosul=_D7,
             aciklama="Aynı kesit dosyası TikTok'a (koşullu)"),
    ],
}

# Kanal geneli İNSAN EMEĞİ gönderileri. Proje `kulis` türü (YouTube Posts) AYNEN kalır;
# TikTok yüzeyi kanal türü olarak burada (projeye bağlanırsa her yeni şarkı bir gönderi
# doğurur — kaçınılan şablon desen).
KANAL_TUR_TANIMLARI = {
    "soz_defteri": {"ad": "Söz Defteri", "platform": "tiktok",
                    "aciklama": "Eller + defter + kendi sesin: eski dize -> neden değişti -> "
                                "yeni dize (30-45 sn, yüz yok)"},
    "kulis": {"ad": "Kulis", "platform": "tiktok",
              "aciklama": "Ekran kaydı + eller + kendi sesin: bir seçim sürecinin hikâyesi"},
    # YouTube TOPLULUK sürümleri (özgünlük planı Aşama 1, iş #4). Topluluk gönderisi için API
    # YOK -> elle, Studio'dan. `tavan_disi`: haftalık insan emeği tavanına ve "aynı gün ikinci
    # insan emeği" kuralına SAYILMAZ (aynı içeriğin ikinci yüzeyi, yeni bir gönderi değil).
    # Bağlı TikTok kaydının (`kaynak_id`, türü `kaynak_tur`) ÇÖZÜLMÜŞ anından en az
    # `config.TUREV_TOPLULUK_TIKTOK_SONRASI_SAAT` sonra; golden-hour ve yeni yayın bandı AYNEN
    # (Topluluk da kamuya açık bir yüzey); TikTok şarkı kesiti aynı gün kuralı uygulanmaz.
    "soz_defteri_topluluk": {"ad": "Söz Defteri (YouTube Topluluk)", "platform": "youtube_topluluk",
                             "kaynak_tur": "soz_defteri", "tavan_disi": True,
                             "aciklama": "TikTok Söz Defteri'nin Topluluk sürümü: metin + defter "
                                         "fotoğrafı + isteğe bağlı anket (elle, Studio)"},
    "kulis_topluluk": {"ad": "Kulis (YouTube Topluluk)", "platform": "youtube_topluluk",
                       "kaynak_tur": "kulis", "tavan_disi": True,
                       "aciklama": "TikTok Kulis'in Topluluk sürümü: metin + ekran görüntüsü + "
                                   "isteğe bağlı anket (elle, Studio)"},
}


def _topluluk_saat():
    return float(getattr(config, "TUREV_TOPLULUK_TIKTOK_SONRASI_SAAT", 24))


def _tavan_disi(k):
    """Kayıt tavan dışı (Topluluk) mı — tanımdan; kayıttaki alan tek başına yetmez."""
    return bool(KANAL_TUR_TANIMLARI.get((k or {}).get("tur"), {}).get("tavan_disi"))
# İnsan emeği gönderisiyle AYNI GÜNE düşemeyen şarkı kesiti türev türleri.
SARKI_KESIT_TURLERI = ("tiktok_ikinci_kesit", "dj_kesit", "sarki_youtube_kesit")
KANAL_TAKVIMI_YOLU = os.path.join(_KOK, getattr(config, "TUREV_KANAL_TAKVIMI",
                                                "kanal_takvimi.json"))
GERCEK_KANAL_TAKVIMI_YOLU = KANAL_TAKVIMI_YOLU


# --------------------------------------------------------------------------
# Zaman
# --------------------------------------------------------------------------

def _dt(ts):
    return datetime.datetime.fromtimestamp(ts, TR)


def _iso(ts):
    return _dt(ts).replace(microsecond=0).isoformat()


def _ts(deger):
    """ISO metni (Z'li, ofsetli ya da ofsetsiz TR yerel) -> epoch; bozuksa None."""
    if not isinstance(deger, str) or not deger.strip():
        return None
    try:
        an = datetime.datetime.fromisoformat(deger.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if an.tzinfo is None:
        an = an.replace(tzinfo=TR)
    return an.timestamp()


def _gun_saat(tarih, saat):
    return datetime.datetime(tarih.year, tarih.month, tarih.day, saat, tzinfo=TR).timestamp()


def _pencereler(bas_ts):
    """bas_ts'nin gününden itibaren (pencere_bas, pencere_bit) üreteci."""
    gun = _dt(bas_ts).date()
    while True:
        for b, s in config.GOLDEN_HOURS:
            yield _gun_saat(gun, b), _gun_saat(gun, s)
        gun += datetime.timedelta(days=1)


def _golden_icinde(ts):
    saat = _dt(ts).hour
    return any(b <= saat < s for b, s in config.GOLDEN_HOURS)


def _ilk_golden_an(ts):
    for wb, ws in _pencereler(ts):
        if ws > ts:
            return max(ts, wb)


def _pencere_of(ts):
    for b, s in config.GOLDEN_HOURS:
        if b <= _dt(ts).hour < s:
            return _gun_saat(_dt(ts).date(), b), _gun_saat(_dt(ts).date(), s)
    return None


def _yeni_yayin_tabani():
    ap = sys.modules.get("auto_process")
    return float(getattr(ap, "MIN_YAYIN_ARALIGI_SN", _YENI_YAYIN_TABANI_VARSAYILAN))


# --------------------------------------------------------------------------
# State / klasör
# --------------------------------------------------------------------------

def _kok_adi(proje):
    return os.path.basename(os.path.dirname(os.path.normpath(os.path.abspath(proje))))


def _ad(proje):
    return unicodedata.normalize("NFC", os.path.basename(os.path.normpath(proje)))


def _json_oku(yol):
    """dict ya da None (dosya yok -> {}; bozuk -> None)."""
    if not os.path.exists(yol):
        return {}
    try:
        with open(yol, "r", encoding="utf-8") as f:
            veri = json.load(f)
    except (OSError, ValueError):
        return None
    return veri if isinstance(veri, dict) else None


def _durum_oku(proje):
    return _json_oku(os.path.join(proje, "state.json"))


def _meta_oku(proje):
    return _json_oku(os.path.join(proje, "meta.json")) or {}


def _klasorler(klasorler=None):
    return list(uyumluluk.proje_klasorleri() if klasorler is None else klasorler)


def _testte_gercek_yol(yol):
    if not os.environ.get("PYTEST_CURRENT_TEST"):
        return False
    y = os.path.normcase(os.path.abspath(yol))
    for kok in GERCEK_KOKLER:
        k = os.path.normcase(os.path.abspath(kok))
        if y == k or y.startswith(k + os.sep):
            return True
    return False


def _dj_kilidi_taze(simdi):
    try:
        return simdi - os.path.getmtime(DJ_KILIT_YOLU) < DJ_KILIT_TAZE_SN
    except OSError:
        return False


def _yazim_kapisi(proje, simdi):
    if _testte_gercek_yol(proje):
        raise TurevHatasi("test sırasında GERÇEK state'e yazma reddedildi: %s" % proje)
    if _kok_adi(proje) == "dj_sets" and _dj_kilidi_taze(simdi):
        raise TurevHatasi("DJ koşusu sürüyor (kilit taze) — dj_sets state'ine yazılmadı")


def _kayit_guncelle(proje, kayit_id, degistir, simdi=None):
    """state.json'da tek bir türev kaydını değiştirir (oku -> değiştir -> atomik yaz)."""
    t = time.time() if simdi is None else simdi
    _yazim_kapisi(proje, t)
    st = _durum_oku(proje)
    if st is None:
        raise TurevHatasi("state.json okunamadı: %s" % proje)
    plan = st.get("turev_plani")
    if not isinstance(plan, list):
        raise TurevHatasi("turev_plani yok ya da bozuk: %s" % proje)
    for k in plan:
        if isinstance(k, dict) and k.get("id") == kayit_id:
            degistir(k)
            k["guncellendi_at"] = _iso(t)
            state_io.durum_yaz(proje, st)
            return k
    raise TurevHatasi("kayıt bulunamadı: %s" % kayit_id)


# --------------------------------------------------------------------------
# T0, engeller
# --------------------------------------------------------------------------

def t0_bul(st):
    """Uzun formatın public anı: `youtube_publish_at`, yoksa `youtube_uploaded_at`."""
    if not (st or {}).get("youtube_video_id"):
        return None
    for anahtar in ("youtube_publish_at", "youtube_uploaded_at"):
        t = _ts(st.get(anahtar))
        if t is not None:
            return t
    return None


def _dolu(deger):
    return deger not in (None, "", [], {}, False)


def engel_sebebi(st, meta=None, tur=None):
    """Türevleri DURDURAN engel (metin) ya da None. FAIL-CLOSED: dolu her değer engel."""
    st = st or {}
    b = st.get(uyumluluk.BEKLETME_ALANI)
    if _dolu(b):
        sebep = b.get("sebep") if isinstance(b, dict) else b
        return "yayın bekletiliyor (yayin_beklet: %s)" % str(sebep or "sebep yok")[:80]
    if _dolu(st.get("kopya_notu")) or _dolu((meta or {}).get("kopya_notu")):
        return "kopya_notu"
    for alan in ("telif_araliklari", "telif_eser"):
        if _dolu(st.get(alan)):
            return "telif işareti (%s)" % alan
    if _dolu(st.get("dj_tarama_engelli")):
        return "Content ID engeli"
    gercek = st.get("youtube_privacy_gercek")
    if gercek and gercek != "public":
        return "YouTube gerçek gizlilik %s" % gercek
    if tur == "dj_kesit":
        alan = getattr(config, "DJ_KESIT_BEKLETME_ALANI", "kesit_beklet")
        if _dolu(st.get(alan)):
            return "kesit bekletiliyor (%s)" % alan
    return None


# --------------------------------------------------------------------------
# Plan
# --------------------------------------------------------------------------

_TR_KATLA = str.maketrans({"ı": "i", "İ": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g",
                           "ü": "u", "Ü": "u", "ö": "o", "Ö": "o", "ç": "c", "Ç": "c"})


def _slug(ad):
    s = unicodedata.normalize("NFC", ad).translate(_TR_KATLA).lower()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    parca = "".join(c if c.isalnum() else "-" for c in s)
    return "-".join(p for p in parca.split("-") if p) or "proje"


def _ucuncu_pazartesi_sonrasi(ts):
    """ts gününe eşit ya da sonraki ilk 'ayın 3. Pazartesi'si' (12:00 TR)."""
    gun = _dt(ts).date()
    yil, ay = gun.year, gun.month
    for _ in range(3):
        ilk = datetime.date(yil, ay, 1)
        pzt = ilk + datetime.timedelta(days=(7 - ilk.weekday()) % 7)
        ucuncu = pzt + datetime.timedelta(days=14)
        if ucuncu >= gun:
            return _gun_saat(ucuncu, 12)
        ay, yil = (1, yil + 1) if ay == 12 else (ay + 1, yil)
    return None


def _tur_acik(tanim, kok, hedef):
    if tanim["tur"] == "kulis" and kok == "dj_sets":
        return bool(getattr(config, "TUREV_DJ_KULIS_ONAYLI", False))
    if tanim["tur"] == "sarki_youtube_kesit":
        if not getattr(config, "TUREV_SARKI_YOUTUBE_KESIT_AKTIF", False):
            return False
        try:
            kapi = datetime.date.fromisoformat(str(config.TUREV_SARKI_YOUTUBE_KESIT_KAPI))
        except (AttributeError, ValueError):
            return False                                  # okunamayan kapı = kapalı
        return _dt(hedef).date() >= kapi
    return True


def _kayit_uret(ad, kok, tanim, t0, simdi):
    t0_gun = _dt(t0).date()
    pencere_sonu = _gun_saat(t0_gun + datetime.timedelta(days=int(config.TUREV_PENCERE_GUN)), 22)
    if tanim["tur"] == "derleme_adayligi":
        hedef = _ucuncu_pazartesi_sonrasi(t0 + 7 * GUN_SN)
        if hedef is None:
            return None
    elif tanim["saat"] is None:
        hedef = t0 + SAAT
    else:
        hedef = _gun_saat(t0_gun + datetime.timedelta(days=tanim["gun"]), tanim["saat"])
    en_gec = min(_gun_saat(t0_gun + datetime.timedelta(days=tanim["en_gec_gun"]), 22),
                 pencere_sonu)
    # Hedefi GEÇMİŞ tür eklenmez: geriye dönük telafi dalgası yok (plan §5b). Yeni
    # render edilen projede hedeflerin hepsi gelecekte olduğu için etkisiz; eski
    # projelere elle plan üretilirken kaçırılmış türevler takvimi doldurmasın.
    if hedef < simdi or hedef > en_gec or not _tur_acik(tanim, kok, hedef):
        return None
    bagimlilik = ["youtube_public", "!yayin_beklet", "!kopya_notu", "!telif_isareti"]
    iptal = ["kopya_notu", "telif_isareti", "en_gec_asildi"]
    if tanim["tur"] == "dj_kesit":
        bagimlilik.append("!" + getattr(config, "DJ_KESIT_BEKLETME_ALANI", "kesit_beklet"))
    if tanim["kosul"]:
        bagimlilik.append(tanim["kosul"])
        iptal.append("d7_karar=iptal")
    return {
        "id": "TRV-%s-%s" % (_slug(ad), tanim["tur"]),
        "tur": tanim["tur"],
        "tur_adi": tanim["ad"],
        "platform": tanim["platform"],
        "yuzey": tanim["yuzey"],
        "elle": tanim["elle"],
        "youtube_video": tanim["youtube_video"],
        "t0": _iso(t0),
        "hedef_an": _iso(hedef),
        "en_erken": _iso(hedef),
        "en_gec": _iso(en_gec),
        "durum": "planlandi",
        "dosyalar": list(tanim["dosyalar"]),
        "bagimliliklar": bagimlilik,
        "iptal_kosulu": iptal,
        "kosul": tanim["kosul"],
        "risk": tanim["risk"],
        "tempo_sayilir": False,
        "yayin": None,
        "iptal_sebebi": None,
        "hatirlatildi_at": None,
        "olusturuldu_at": _iso(simdi),
        "guncellendi_at": _iso(simdi),
    }


def plan_uret(proje, simdi=None, uygula=False):
    """Projenin türev planını üretir. DETERMİNİSTİK (aynı state + simdi -> aynı plan).

    Varsayılan KURU. `uygula=True` yalnız EKSİK id'leri ekler; mevcut kayıtlara
    (iptal edilmiş olanlar dahil) dokunmaz. Döner: {proje, ad, kok, t0, eklenecek,
    mevcut, sebep, yazildi}."""
    t = time.time() if simdi is None else simdi
    ad, kok = _ad(proje), _kok_adi(proje)
    sonuc = {"proje": proje, "ad": ad, "kok": kok, "t0": None, "eklenecek": [],
             "mevcut": 0, "sebep": "", "yazildi": False}
    st = _durum_oku(proje)
    if st is None:
        sonuc["sebep"] = "state.json okunamadı (fail-closed)"
        return sonuc
    if kok not in TUR_TANIMLARI:
        sonuc["sebep"] = "bu kök (%s) için türev tanımı yok" % kok
        return sonuc
    t0 = t0_bul(st)
    if t0 is None:
        sonuc["sebep"] = "T0 yok (YouTube uzun format yayını kayıtlı değil)"
        return sonuc
    sonuc["t0"] = _iso(t0)
    if t > _gun_saat(_dt(t0).date() + datetime.timedelta(days=int(config.TUREV_PENCERE_GUN)), 22):
        sonuc["sebep"] = "türev penceresi kapandı (T0 + %s gün)" % config.TUREV_PENCERE_GUN
        return sonuc
    if kok == "dj_sets" and getattr(config, "DJ_ON_TARAMA", True) and not st.get("dj_tarama_temiz"):
        sonuc["sebep"] = "Content ID taraması temiz değil (dj_tarama_temiz yok)"
        return sonuc
    engel = engel_sebebi(st, _meta_oku(proje))
    if engel:
        sonuc["sebep"] = "engel: %s — plan üretilmedi" % engel
        return sonuc
    mevcut = st.get("turev_plani")
    if mevcut is not None and not isinstance(mevcut, list):
        sonuc["sebep"] = "turev_plani bozuk (liste değil) — dokunulmadı"
        return sonuc
    mevcut_idler = {k.get("id") for k in (mevcut or []) if isinstance(k, dict)}
    sonuc["mevcut"] = len(mevcut_idler)
    for tanim in TUR_TANIMLARI[kok]:
        kayit = _kayit_uret(ad, kok, tanim, t0, t)
        if kayit and kayit["id"] not in mevcut_idler:
            sonuc["eklenecek"].append(kayit)
    sonuc["eklenecek"].sort(key=lambda k: (k["hedef_an"], k["id"]))
    sonuc["sebep"] = "%d kayıt eklenecek" % len(sonuc["eklenecek"])
    if not uygula or not sonuc["eklenecek"]:
        return sonuc

    _yazim_kapisi(proje, t)
    st = _durum_oku(proje)                               # yazmadan hemen önce TAZE oku
    if st is None or (st.get("turev_plani") is not None
                      and not isinstance(st.get("turev_plani"), list)):
        raise TurevHatasi("state yazımdan önce okunamadı/bozuk: %s" % proje)
    liste = st.setdefault("turev_plani", [])
    idler = {k.get("id") for k in liste if isinstance(k, dict)}
    eklenen = [k for k in sonuc["eklenecek"] if k["id"] not in idler]
    liste.extend(eklenen)
    st["turev_plani_surumu"] = SURUM
    state_io.durum_yaz(proje, st)
    sonuc["eklenecek"] = eklenen
    sonuc["yazildi"] = bool(eklenen)
    return sonuc


# --------------------------------------------------------------------------
# Takvim
# --------------------------------------------------------------------------

def _katalog(klasorler):
    """[(yol, ad, kok, st, meta)] — okunamayan state atlanır (sayılır)."""
    sonuc, okunamayan = [], 0
    for p in klasorler:
        st = _durum_oku(p)
        if st is None:
            okunamayan += 1
            continue
        sonuc.append((p, _ad(p), _kok_adi(p), st, _meta_oku(p)))
    return sonuc, okunamayan


def _ses_var(proje):
    try:
        return any(f.lower().startswith("audio.") for f in os.listdir(proje))
    except OSError:
        return False


def yeni_yayin_anlari(katalog, simdi):
    """[(an, proje_adı, tahmini)] — bilinen T0'lar + sesi hazır bekleyen şarkıların
    tahmini public anı (son yeni şarkı + taban, sonraki golden-hour; tek tek +taban)."""
    bantlar, son = [], None
    for p, ad, kok, st, meta in katalog:
        t0 = t0_bul(st)
        if t0 is None:
            continue
        bantlar.append((t0, ad, False))
        if kok == "projects":
            son = t0 if son is None else max(son, t0)
    taban = _yeni_yayin_tabani()
    bekleyen = [(ad, p) for p, ad, kok, st, meta in katalog
                if kok == "projects" and not st.get("youtube_video_id")
                and not _dolu(st.get(uyumluluk.BEKLETME_ALANI)) and _ses_var(p)]
    t = max(simdi, son + taban) if son is not None else simdi
    for ad, _p in sorted(bekleyen):
        t = _ilk_golden_an(t)
        bantlar.append((t, ad, True))
        t += taban
    return bantlar


def _kayitlar(katalog):
    """[(yol, ad, kok, st, meta, kayit)] geçerli olanlar + bozuk sayısı."""
    iyi, bozuk = [], 0
    for p, ad, kok, st, meta in katalog:
        plan = st.get("turev_plani")
        if plan is None:
            continue
        if not isinstance(plan, list):
            bozuk += 1
            continue
        for k in plan:
            if (not isinstance(k, dict) or k.get("durum") not in DURUMLAR or not k.get("id")
                    or _ts(k.get("hedef_an")) is None or _ts(k.get("en_gec")) is None):
                bozuk += 1
                continue
            iyi.append((p, ad, kok, st, meta, k))
    return iyi, bozuk


def _olay(p, ad, kok, k, an, etkin, engel=None):
    hedef = _ts(k.get("hedef_an"))
    return {
        "id": k["id"], "proje": ad, "proje_yolu": p, "kok": kok,
        "tur": k.get("tur"), "tur_adi": k.get("tur_adi") or k.get("tur"),
        "platform": k.get("platform"), "yuzey": bool(k.get("yuzey")),
        "elle": bool(k.get("elle")), "youtube_video": bool(k.get("youtube_video")),
        "kosul": k.get("kosul"), "risk": k.get("risk"), "durum": k.get("durum"),
        "etkin": etkin, "an": _iso(an), "hedef_an": k.get("hedef_an"),
        "en_gec": k.get("en_gec"), "t0": k.get("t0"), "engel": engel,
        "kaydirma_saat": round((an - hedef) / SAAT, 1) if hedef is not None else None,
        "hatirlatildi_at": k.get("hatirlatildi_at"),
    }


def _cakisma(aday, kayit, proje, dolu, bantlar):
    """Yüzey türevi `aday` anına konabilir mi? Engel metni ya da None."""
    gun = _dt(aday).date()
    if sum(1 for d in dolu if d[2] and _dt(d[0]).date() == gun) >= int(config.TUREV_GUNLUK_TAVAN):
        return "günlük tavan"
    bant = float(config.TUREV_YENI_YAYIN_BANDI_SAAT) * SAAT
    if any(abs(aday - b[0]) < bant for b in bantlar):
        return "yeni yayın bandı"
    ara = float(config.TUREV_AYNI_SARKI_ARA_SAAT) * SAAT
    if any(d[1] == proje and d[2] and abs(aday - d[0]) < ara for d in dolu):
        return "aynı şarkı aralığı"
    if kayit.get("youtube_video"):
        yakin = sum(1 for d in dolu if d[3] and abs(aday - d[0]) < 7 * GUN_SN)
        if yakin >= int(config.TUREV_YOUTUBE_VIDEO_HAFTALIK_TAVAN):
            return "haftalık YouTube video tavanı"
    return None


def _tiktok_kesit_anlari(st):
    """Projenin TikTok şarkı kesiti anları (state, salt okuma): etkin web planı
    (`tiktok_web.planlanan_an`), `tiktok_published_at`, gönderilmiş kit."""
    anlar = []
    w = st.get("tiktok_web")
    if isinstance(w, dict) and w.get("durum") in ("planlandi", "yayinlandi"):
        anlar.append(_ts(w.get("planlanan_an")))
    anlar.append(_ts(st.get("tiktok_published_at")))
    anlar.append(_ts(st.get("tiktok_kit_gonderildi_at")))
    return [a for a in anlar if a is not None]


def _hafta_bas(ts):
    gun = _dt(ts).date()
    return gun - datetime.timedelta(days=gun.weekday())


def _kanal_yolu(yol=None):
    return KANAL_TAKVIMI_YOLU if yol is None else yol


def _kanal_testte_gercek(yol):
    return bool(os.environ.get("PYTEST_CURRENT_TEST")) and (
        os.path.normcase(os.path.abspath(yol))
        == os.path.normcase(os.path.abspath(GERCEK_KANAL_TAKVIMI_YOLU)))


def kanal_kayitlari(yol=None):
    """([geçerli kayıtlar], bozuk sayısı, okunamadı_mı). Dosya yok -> ([], 0, False).

    Test sırasında GERÇEK dosya OKUNMAZ: canlı takvim test sonuçlarına sızmasın."""
    yol = _kanal_yolu(yol)
    if _kanal_testte_gercek(yol):
        return [], 0, False
    veri = _json_oku(yol)
    if veri is None or not isinstance(veri.get("gonderiler", []), list):
        return [], 0, True
    iyi, bozuk = [], 0
    for k in veri.get("gonderiler", []):
        if (not isinstance(k, dict) or not k.get("id") or k.get("durum") not in DURUMLAR
                or k.get("tur") not in KANAL_TUR_TANIMLARI
                or _ts(k.get("hedef_an")) is None or _ts(k.get("en_gec")) is None):
            bozuk += 1
            continue
        iyi.append(k)
    return iyi, bozuk, False


def _kanal_olay(k, an, etkin, engel=None):
    hedef = _ts(k.get("hedef_an"))
    return {
        "id": k["id"], "proje": "Kanal", "proje_yolu": None, "kok": "kanal",
        "tur": k["tur"], "tur_adi": k.get("baslik") or k.get("tur_adi") or k["tur"],
        "platform": k.get("platform"), "yuzey": True, "elle": True, "youtube_video": False,
        "insan_emegi": True, "sarki_kesiti_tavanina_sayilir": False,
        "ilgili_proje": k.get("ilgili_proje"), "paket": k.get("paket"),
        "kosul": None, "risk": k.get("risk"), "durum": k.get("durum"),
        "etkin": etkin, "an": _iso(an), "hedef_an": k.get("hedef_an"),
        "en_gec": k.get("en_gec"), "t0": None, "engel": engel,
        "kaydirma_saat": round((an - hedef) / SAAT, 1) if hedef is not None else None,
        "hatirlatildi_at": k.get("hatirlatildi_at"),
        "kaynak_id": k.get("kaynak_id"), "tavan_disi": _tavan_disi(k),
    }


def _kanal_cakisma(aday, kesitler, insan, bantlar):
    """İnsan emeği gönderisi `aday` anına konabilir mi? Engel metni ya da None.

    `TUREV_GUNLUK_TAVAN` ve TikTok kesit tavanlarına BİLEREK bakılmaz (tavan dışı)."""
    gun = _dt(aday).date()
    if any(_dt(k).date() == gun for k in kesitler):
        return "şarkı kesitiyle aynı gün"
    bant = float(config.TUREV_YENI_YAYIN_BANDI_SAAT) * SAAT
    if any(abs(aday - b[0]) < bant for b in bantlar):
        return "yeni yayın bandı"
    if any(_dt(i).date() == gun for i in insan):
        return "aynı gün ikinci insan emeği gönderisi"
    hafta = _hafta_bas(aday)
    if sum(1 for i in insan if _hafta_bas(i) == hafta) >= int(
            config.TUREV_INSAN_EMEGI_HAFTALIK_TAVAN):
        return "haftalık insan emeği tavanı"
    return None


def _kanal_takvimi(t, bit, bantlar, kesitler, yol=None):
    """(olaylar, düşenler, bozuk, okunamadı) — kanal geneli insan emeği gönderileri."""
    kayitlar, bozuk, okunamadi = kanal_kayitlari(yol)
    olaylar, dusen, insan, adaylar = [], [], [], []
    cozulen = {}            # kayıt id -> çözülmüş an; None = iptal/düştü (Topluluk kaynağı)
    topluluk = [k for k in kayitlar if _tavan_disi(k)]
    for k in kayitlar:
        if _tavan_disi(k):
            continue
        durum = k["durum"]
        if durum == "iptal":
            cozulen[k["id"]] = None
            continue
        if durum in ("yayinlandi", "onay_bekliyor"):
            an = ((_ts((k.get("yayin") or {}).get("an")) if durum == "yayinlandi" else None)
                  or _ts(k["hedef_an"]))
            insan.append(an)
            cozulen[k["id"]] = an
            if t - GUN_SN <= an < bit:
                olaylar.append(_kanal_olay(k, an, durum))
            continue
        hedef, en_gec = _ts(k["hedef_an"]), _ts(k["en_gec"])
        if en_gec < t:
            cozulen[k["id"]] = None
            if hedef < bit:
                dusen.append(_kanal_olay(k, hedef, "suresi_doldu"))
            continue
        adaylar.append((hedef, k["id"], k, en_gec))
    for hedef, _kid, k, en_gec in sorted(adaylar, key=lambda a: (a[0], a[1])):
        an = _kanal_yerlestir(max(hedef, t), en_gec, kesitler, insan, bantlar)
        cozulen[k["id"]] = an
        if an is None:
            if hedef < bit:
                dusen.append(_kanal_olay(k, hedef, "iptal_cakisma"))
            continue
        insan.append(an)
        if an < bit:
            olaylar.append(_kanal_olay(k, an, "planli"))
    # TOPLULUK (tavan dışı): TikTok kayıtları çözüldükten SONRA — kaynak kayarsa bu da kayar.
    # `insan` listesine GİRMEZ ve ona bakmaz (haftalık / aynı gün insan emeği kuralı dışı).
    for k in sorted(topluluk, key=lambda x: (_ts(x["hedef_an"]), x["id"])):
        durum = k["durum"]
        if durum == "iptal":
            continue
        if durum in ("yayinlandi", "onay_bekliyor"):
            an = ((_ts((k.get("yayin") or {}).get("an")) if durum == "yayinlandi" else None)
                  or _ts(k["hedef_an"]))
            if t - GUN_SN <= an < bit:
                olaylar.append(_kanal_olay(k, an, durum))
            continue
        hedef, en_gec = _ts(k["hedef_an"]), _ts(k["en_gec"])
        kaynak_an = cozulen.get(k.get("kaynak_id"))
        if kaynak_an is None:
            if hedef < bit:
                dusen.append(_kanal_olay(k, hedef, "kaynak_dustu",
                                         "bağlı TikTok kaydı yok/iptal/düştü: %s"
                                         % k.get("kaynak_id")))
            continue
        if en_gec < t:
            if hedef < bit:
                dusen.append(_kanal_olay(k, hedef, "suresi_doldu"))
            continue
        bas = max(hedef, t, kaynak_an + _topluluk_saat() * SAAT)
        # Şarkı KESİTİ aynı gün kuralı BİLEREK uygulanmaz: o kural TikTok akışında insan emeği
        # gönderisiyle şarkı kesitinin aynı güne düşmemesi için; Topluluk YouTube'da ayrı yüzey.
        # Canlı takvimde (2026-09-13) uygulansaydı 17-18 Eyl TikTok kesitleri Söz Defteri
        # Topluluk'u tamamen düşürüyordu. Yeni yayın bandı ve golden-hour AYNEN.
        an = _kanal_yerlestir(bas, en_gec, [], [], bantlar)
        if an is None:
            if hedef < bit:
                dusen.append(_kanal_olay(k, hedef, "iptal_cakisma"))
            continue
        if an < bit:
            olaylar.append(_kanal_olay(k, an, "planli"))
    return olaylar, dusen, bozuk, okunamadi


def _kanal_yerlestir(bas, en_gec, kesitler, insan, bantlar):
    """`bas`tan itibaren çakışmasız ilk golden-hour anı ya da None (en_gec aşıldı)."""
    for wb, ws in _pencereler(bas):
        if ws <= bas:
            continue
        aday = max(bas, wb)
        if aday > en_gec:
            break
        if _kanal_cakisma(aday, kesitler, insan, bantlar):
            continue
        return aday
    return None


def _kanal_en_gec(hedef):
    gun = _dt(hedef).date()
    son = gun + datetime.timedelta(days=int(config.TUREV_INSAN_EMEGI_KAYMA_GUN))
    pazar = _hafta_bas(hedef) + datetime.timedelta(days=6)
    return _gun_saat(min(son, pazar), 22)


def _kanal_yaz(yol, degistir, simdi):
    """Kanal takvimini oku -> değiştir -> atomik yaz. Testte GERÇEK dosyaya yazma reddedilir."""
    if _kanal_testte_gercek(yol):
        raise TurevHatasi("test sırasında GERÇEK kanal takvimine yazma reddedildi: %s" % yol)
    veri = _json_oku(yol)                                  # yazmadan hemen önce TAZE oku
    if veri is None or not isinstance(veri.get("gonderiler", []), list):
        raise TurevHatasi("kanal takvimi okunamadı/bozuk: %s" % yol)
    veri.setdefault("aciklama", "Kanal geneli insan emeği gönderileri (turev_takvimi.py "
                                "plan --kanal). Elle düzenleme yerine CLI kullan.")
    veri["surum"] = SURUM
    liste = veri.setdefault("gonderiler", [])
    degistir(liste)
    gecici = yol + ".tmp"
    with open(gecici, "w", encoding="utf-8") as f:
        f.write(json.dumps(veri, ensure_ascii=False, indent=2) + "\n")
    os.replace(gecici, yol)


def kanal_plan(tur, hedef, baslik, ilgili_proje=None, paket=None, simdi=None, uygula=False,
               yol=None, kaynak_id=None):
    """Kanal geneli insan emeği gönderisi kaydı. Varsayılan KURU.

    Yazım anı kuralları: tür tanımlı; hedef gelecekte ve golden-hour içinde; aynı TR
    haftasında iptal olmayan kayıt < `TUREV_INSAN_EMEGI_HAFTALIK_TAVAN`; aynı gün ikinci
    kayıt yok. Kesit / yeni yayın çakışması DİNAMİK: `takvim` her okumada çözer.
    Aynı id varsa hiçbir şey yazılmaz (mevcut ezilmez)."""
    t = time.time() if simdi is None else simdi
    yol = _kanal_yolu(yol)
    if tur not in KANAL_TUR_TANIMLARI:
        raise TurevHatasi("tanımsız kanal türü: %r (geçerli: %s)"
                          % (tur, ", ".join(sorted(KANAL_TUR_TANIMLARI))))
    h = hedef if isinstance(hedef, (int, float)) else _ts(hedef)
    if h is None:
        raise TurevHatasi("hedef an okunamadı: %r" % (hedef,))
    if h < t:
        raise TurevHatasi("hedef an geçmişte: %s" % _iso(h))
    if not _golden_icinde(h):
        raise TurevHatasi("hedef an golden-hour dışında: %s" % _iso(h))
    if not (baslik or "").strip():
        raise TurevHatasi("--baslik boş olamaz")
    tanim = KANAL_TUR_TANIMLARI[tur]
    tavan_disi = bool(tanim.get("tavan_disi"))
    if kaynak_id and not tavan_disi:
        raise TurevHatasi("--kaynak-id yalnız Topluluk türlerinde geçerli (%s değil)" % tur)
    kayit = {
        "id": "KNL-%s-%s" % (_dt(h).date().isoformat(), tur),
        "tur": tur, "tur_adi": tanim["ad"], "baslik": baslik.strip(),
        "platform": tanim["platform"], "kanal_geneli": True, "insan_emegi": True,
        "sarki_kesiti_tavanina_sayilir": False, "elle": True,
        "ilgili_proje": ilgili_proje, "paket": paket, "aciklama": tanim["aciklama"],
        "hedef_an": _iso(h), "en_erken": _iso(h), "en_gec": _iso(_kanal_en_gec(h)),
        "durum": "planlandi", "risk": "dusuk", "tempo_sayilir": False, "yayin": None,
        "iptal_sebebi": None, "hatirlatildi_at": None,
        "olusturuldu_at": _iso(t), "guncellendi_at": _iso(t),
    }
    if tavan_disi:
        # Hafta sonuna kırpılmaz (haftalık tavan dışı); kaynak kayarsa bu da kayabilsin.
        son = _dt(h).date() + datetime.timedelta(days=int(config.TUREV_INSAN_EMEGI_KAYMA_GUN))
        kayit.update(kaynak_id=kaynak_id, kaynak_tur=tanim["kaynak_tur"], tavan_disi=True,
                     en_gec=_iso(_gun_saat(son, 22)))
    sonuc = {"yol": yol, "kayit": kayit, "sebep": "", "yazildi": False}
    kayitlar, _bozuk, okunamadi = kanal_kayitlari(yol)
    if okunamadi:
        raise TurevHatasi("kanal takvimi okunamadı/bozuk (fail-closed): %s" % yol)
    if tavan_disi:
        kaynak = next((k for k in kayitlar if k["id"] == kaynak_id), None) if kaynak_id else None
        if kaynak is None or kaynak.get("durum") == "iptal":
            raise TurevHatasi("Topluluk kaydı için geçerli bir --kaynak-id (TikTok %s kaydı) "
                              "gerekli: %r" % (tanim["kaynak_tur"], kaynak_id))
        if kaynak.get("tur") != tanim["kaynak_tur"]:
            raise TurevHatasi("kaynak kaydın türü %r, beklenen %r: %s" % (
                kaynak.get("tur"), tanim["kaynak_tur"], kaynak_id))
        kaynak_an = ((_ts((kaynak.get("yayin") or {}).get("an"))
                      if kaynak.get("durum") == "yayinlandi" else None)
                     or _ts(kaynak["hedef_an"]))
        if h < kaynak_an + _topluluk_saat() * SAAT:
            raise TurevHatasi("Topluluk sürümü TikTok kaydından (%s) en az %g sa sonra olmalı"
                              % (_iso(kaynak_an), _topluluk_saat()))
    if any(k["id"] == kayit["id"] for k in kayitlar):
        sonuc["sebep"] = "zaten var: %s (dokunulmadı)" % kayit["id"]
        return sonuc
    if tavan_disi:
        sonuc["sebep"] = "1 kayıt eklenecek (Topluluk, tavan dışı)"
        if uygula:
            _kanal_yaz(yol, lambda liste: liste.append(kayit), t)
            sonuc["yazildi"] = True
        return sonuc
    etkin = [k for k in kayitlar if k["durum"] != "iptal" and not _tavan_disi(k)]
    if any(_dt(_ts(k["hedef_an"])).date() == _dt(h).date() for k in etkin):
        raise TurevHatasi("aynı gün ikinci insan emeği gönderisi olamaz (%s)" % _dt(h).date())
    ayni_hafta = [k for k in etkin if _hafta_bas(_ts(k["hedef_an"])) == _hafta_bas(h)]
    if len(ayni_hafta) >= int(config.TUREV_INSAN_EMEGI_HAFTALIK_TAVAN):
        raise TurevHatasi("haftalık insan emeği tavanı dolu (%d/%s): %s" % (
            len(ayni_hafta), config.TUREV_INSAN_EMEGI_HAFTALIK_TAVAN,
            ", ".join(k["id"] for k in ayni_hafta)))
    sonuc["sebep"] = "1 kayıt eklenecek"
    if not uygula:
        return sonuc
    _kanal_yaz(yol, lambda liste: liste.append(kayit), t)
    sonuc["yazildi"] = True
    return sonuc


def _kanal_iptal(kayit_id, sebep, simdi=None, yol=None):
    t = time.time() if simdi is None else simdi

    def degistir(liste):
        for k in liste:
            if isinstance(k, dict) and k.get("id") == kayit_id:
                if k.get("durum") == "yayinlandi":
                    raise TurevHatasi("yayınlanmış kayıt iptal edilemez: %s" % kayit_id)
                k.update(durum="iptal", iptal_sebebi=sebep, guncellendi_at=_iso(t))
                return
        raise TurevHatasi("kayıt bulunamadı: %s" % kayit_id)

    _kanal_yaz(_kanal_yolu(yol), degistir, t)
    return {"id": kayit_id, "proje": "Kanal", "durum": "iptal"}


def takvim(gun=7, simdi=None, klasorler=None, kanal_yolu=None):
    """Tüm katalog için çakışma çözümlü türev takvimi (SALT OKUMA, state yazmaz).

    JSON biçimi (pano / sesli asistan): bkz. `python turev_takvimi.py takvim --json`."""
    t = time.time() if simdi is None else simdi
    bit = t + float(gun) * GUN_SN
    katalog, okunamayan = _katalog(_klasorler(klasorler))
    bantlar = yeni_yayin_anlari(katalog, t)
    kayitlar, bozuk = _kayitlar(katalog)

    olaylar, durdurulan, dusen = [], [], []
    # dolu: (an, proje_yolu, yuzey, youtube_video)
    dolu = []
    kesitler = []                  # şarkı kesiti anları: insan emeği gönderisi o güne düşmez
    for p, ad, kok, st, meta in katalog:
        klip = _ts(st.get("youtube_clip_uploaded_at"))
        if klip is not None:
            dolu.append((klip, p, True, True))
            kesitler.append(klip)
        kesitler.extend(_tiktok_kesit_anlari(st))
    adaylar = []
    for p, ad, kok, st, meta, k in kayitlar:
        durum = k["durum"]
        if durum == "iptal":
            continue
        if durum == "yayinlandi":
            an = _ts((k.get("yayin") or {}).get("an")) or _ts(k["hedef_an"])
            dolu.append((an, p, bool(k.get("yuzey")), bool(k.get("youtube_video"))))
            if k.get("tur") in SARKI_KESIT_TURLERI:
                kesitler.append(an)
            if t - GUN_SN <= an < bit:
                olaylar.append(_olay(p, ad, kok, k, an, "yayinlandi"))
            continue
        if durum == "onay_bekliyor":
            an = _ts(k.get("hatirlatildi_at")) or _ts(k["hedef_an"])
            dolu.append((an, p, bool(k.get("yuzey")), bool(k.get("youtube_video"))))
            if k.get("tur") in SARKI_KESIT_TURLERI:
                kesitler.append(an)
            olaylar.append(_olay(p, ad, kok, k, an, "onay_bekliyor"))
            continue
        hedef, en_gec = _ts(k["hedef_an"]), _ts(k["en_gec"])
        engel = engel_sebebi(st, meta, k.get("tur"))
        if engel:
            if hedef < bit:
                durdurulan.append(_olay(p, ad, kok, k, max(hedef, t), "durdu", engel))
            continue
        if en_gec < t:
            if hedef < bit:
                dusen.append(_olay(p, ad, kok, k, hedef, "suresi_doldu"))
            continue
        adaylar.append((p, ad, kok, k, hedef, en_gec))

    adaylar.sort(key=lambda a: (a[3].get("kosul") is not None, a[4],
                                _RISK_SIRASI.get(a[3].get("risk"), 9),
                                -(_ts(a[3].get("t0")) or 0), a[3]["id"]))
    for p, ad, kok, k, hedef, en_gec in adaylar:
        bas = max(hedef, t)
        an = None
        for wb, ws in _pencereler(bas):
            if ws <= bas:
                continue
            aday = max(bas, wb)
            if aday > en_gec:
                break
            if k.get("yuzey") and _cakisma(aday, k, p, dolu, bantlar):
                continue
            an = aday
            break
        if an is None:
            if hedef < bit:
                dusen.append(_olay(p, ad, kok, k, hedef, "iptal_cakisma"))
            continue
        dolu.append((an, p, bool(k.get("yuzey")), bool(k.get("youtube_video"))))
        if k.get("tur") in SARKI_KESIT_TURLERI:
            kesitler.append(an)
        if an < bit:
            olaylar.append(_olay(p, ad, kok, k, an, "kosullu" if k.get("kosul") else "planli"))

    kanal, kanal_dusen, kanal_bozuk, kanal_okunamadi = _kanal_takvimi(
        t, bit, bantlar, kesitler, kanal_yolu)
    sirala = lambda x: (x["an"], x["id"])                 # noqa: E731
    return {
        "surum": SURUM,
        "uretildi_at": _iso(t),
        "aralik": {"bas": _iso(t), "bit": _iso(bit), "gun": gun},
        "olaylar": sorted(olaylar, key=sirala),
        # İnsan emeği (kanal geneli): kesit tavanı DIŞI, bu yüzden `olaylar`dan AYRI.
        "kanal_gonderileri": sorted(kanal, key=sirala),
        "durdurulanlar": sorted(durdurulan, key=sirala),
        "dusenler": sorted(dusen + kanal_dusen, key=sirala),
        "yeni_yayinlar": [{"proje": ad, "an": _iso(an), "tahmini": tah}
                          for an, ad, tah in sorted(bantlar)
                          if t - GUN_SN <= an < bit + GUN_SN],
        "kurallar": {
            "gunluk_tavan": config.TUREV_GUNLUK_TAVAN,
            "youtube_video_haftalik_tavan": config.TUREV_YOUTUBE_VIDEO_HAFTALIK_TAVAN,
            "yeni_yayin_bandi_saat": config.TUREV_YENI_YAYIN_BANDI_SAAT,
            "ayni_sarki_ara_saat": config.TUREV_AYNI_SARKI_ARA_SAAT,
            "pencere_gun": config.TUREV_PENCERE_GUN,
            "golden_hours": [list(g) for g in config.GOLDEN_HOURS],
            "hatirlatma_aktif": bool(getattr(config, "TUREV_HATIRLATMA_AKTIF", False)),
            "insan_emegi_haftalik_tavan": config.TUREV_INSAN_EMEGI_HAFTALIK_TAVAN,
            "topluluk_tiktok_sonrasi_saat": _topluluk_saat(),
        },
        "atlanan_kayitlar": bozuk + kanal_bozuk,
        "kanal_takvimi_okunamadi": kanal_okunamadi,
        "okunamayan_projeler": okunamayan,
    }


def sirada_ne(simdi=None, klasorler=None):
    """Sıradaki (en erken) planlı / koşullu / onay bekleyen türev olayı ya da None."""
    tk = takvim(gun=config.TUREV_PENCERE_GUN, simdi=simdi, klasorler=klasorler)
    adaylar = sorted([o for o in tk["olaylar"] + tk.get("kanal_gonderileri", [])
                      if o["etkin"] in ("planli", "kosullu", "onay_bekliyor")],
                     key=lambda x: (x["an"], x["id"]))
    return adaylar[0] if adaylar else None


_GUN_ADLARI = ("Pzt", "Sal", "Çar", "Prş", "Cum", "Cmt", "Paz")


def _olay_satiri(o, simdi=None):
    an = datetime.datetime.fromisoformat(o["an"])
    if simdi is not None:
        fark = (an.date() - _dt(simdi).date()).days
        gun = {0: "Bugün", 1: "Yarın"}.get(fark, "%s %s" % (an.strftime("%d.%m"),
                                                          _GUN_ADLARI[an.weekday()]))
    else:
        gun = "%s %s" % (an.strftime("%d.%m"), _GUN_ADLARI[an.weekday()])
    ek = []
    if o["elle"]:
        ek.append("senin işin")
    if o.get("insan_emegi"):
        ek.append("insan emeği, kesit tavanı dışı")
    if o["etkin"] == "kosullu":
        ek.append("koşullu")
    if o["etkin"] == "onay_bekliyor":
        ek.append("onay bekliyor")
    return "%s %s · %s · %s (%s)%s" % (gun, an.strftime("%H:%M"), o["proje"], o["tur_adi"],
                                      o["platform"], (" — " + ", ".join(ek)) if ek else "")


def bugun_yarin_satirlari(simdi=None, klasorler=None, tavan=4):
    """Günlük rapor için "bugün/yarın" türev satırları (boşsa [])."""
    t = time.time() if simdi is None else simdi
    tk = takvim(gun=2, simdi=t, klasorler=klasorler)
    gunler = {_dt(t).date(), _dt(t).date() + datetime.timedelta(days=1)}
    secilen = sorted([o for o in tk["olaylar"] + tk.get("kanal_gonderileri", [])
                      if o["etkin"] in ("planli", "kosullu", "onay_bekliyor")
                      and datetime.datetime.fromisoformat(o["an"]).date() in gunler],
                     key=lambda x: (x["an"], x["id"]))
    satirlar = ["  " + _olay_satiri(o, t) for o in secilen[:tavan]]
    if len(secilen) > tavan:
        satirlar.append("  +%d daha" % (len(secilen) - tavan))
    return satirlar


# --------------------------------------------------------------------------
# Hatırlatma (bayrakla; varsayılan KAPALI)
# --------------------------------------------------------------------------

def _hatirlatma_metni(o):
    tanim = next((x for x in TUR_TANIMLARI.get(o["kok"], []) if x["tur"] == o["tur"]), {})
    platform = {"youtube": "youtube", "instagram": "instagram", "tiktok": "tiktok"}.get(
        o["platform"], o["platform"])
    return "\n".join([
        "Türev hatırlatması — senin işin",
        "%s: %s" % (o["proje"], o["tur_adi"]),
        "Ne: %s" % (tanim.get("aciklama") or "-"),
        "Son gün: %s" % o["en_gec"][:10],
        "Yaptıktan sonra kaydet: python elle_islem.py ekle --platform %s --proje \"%s\" "
        "--islem yayinladi --ayrinti \"...\"" % (platform, o["proje"]),
        "Kod: %s" % o["id"],
    ])


def hatirlatma_sirasi(log=print, simdi=None, klasorler=None, gonder=None):
    """Elle türev için EN FAZLA bir Telegram hatırlatması (operatör DM'i, `notify.send_text`).

    Kapılar sırasıyla: ana şalter (kapalıysa state OKUNMAZ/YAZILMAZ, tek log satırı),
    golden-hour, önceki hatırlatma yanıtlanmadı mı (herhangi bir `onay_bekliyor`),
    günlük tavan, bu pencerede planlı elle türev, `uyumluluk.kontrol(..., "yukleme")`
    (fail-closed). Gönderim başarılıysa kayıt `onay_bekliyor` + `hatirlatildi_at`."""
    sonuc = {"gonderilen": None, "sebep": ""}
    if not getattr(config, "TUREV_HATIRLATMA_AKTIF", False):
        sonuc["sebep"] = "kapalı (config)"
        log("  Türev hatırlatma: kapalı (config.TUREV_HATIRLATMA_AKTIF=False)")
        return sonuc
    t = time.time() if simdi is None else simdi
    if not _golden_icinde(t):
        sonuc["sebep"] = "golden-hour dışında"
        return sonuc
    klasorler = _klasorler(klasorler)
    katalog, _ = _katalog(klasorler)
    kayitlar, _ = _kayitlar(katalog)
    bekleyen = [k for *_x, k in kayitlar if k["durum"] == "onay_bekliyor"]
    if bekleyen:
        sonuc["sebep"] = "önceki hatırlatma yanıtlanmadı (%s)" % bekleyen[0]["id"]
        return sonuc
    bugun = _dt(t).date()
    gunluk = sum(1 for *_x, k in kayitlar
                 if _ts(k.get("hatirlatildi_at")) is not None
                 and _dt(_ts(k["hatirlatildi_at"])).date() == bugun)
    if gunluk >= int(config.TUREV_HATIRLATMA_GUNLUK_TAVAN):
        sonuc["sebep"] = "bugün hatırlatma zaten gitti (günlük tavan)"
        return sonuc
    pencere = _pencere_of(t)
    tk = takvim(gun=1, simdi=t, klasorler=klasorler)
    adaylar = [o for o in tk["olaylar"] if o["elle"] and o["etkin"] == "planli"
               and pencere[0] <= _ts(o["an"]) < pencere[1]]
    if not adaylar:
        sonuc["sebep"] = "bu pencerede elle türev yok"
        return sonuc
    for o in adaylar:
        try:
            hatalar, _u = uyumluluk.kontrol(o["proje_yolu"], "yukleme")
        except Exception as e:                            # noqa: BLE001
            hatalar = ["uyumluluk kapısı çöktü (%s)" % type(e).__name__]
        if hatalar:
            sonuc["sebep"] = "uyumluluk: %s" % "; ".join(hatalar)[:120]
            log("  Türev hatırlatma: '%s' uyumluluk nedeniyle atlandı — %s"
                % (o["proje"], sonuc["sebep"]))
            continue
        if gonder is None:
            import notify
            gonder = notify.send_text
        try:
            tamam = bool(gonder(_hatirlatma_metni(o)))
        except Exception as e:                            # noqa: BLE001
            log("  Türev hatırlatma: gönderim HATA (%s)" % type(e).__name__)
            tamam = False
        if not tamam:
            sonuc["sebep"] = "gönderilemedi"
            return sonuc
        _kayit_guncelle(o["proje_yolu"], o["id"], lambda k: k.update(
            durum="onay_bekliyor", hatirlatildi_at=_iso(t)), simdi=t)
        sonuc.update(gonderilen=o["id"], sebep="gönderildi")
        log("  Türev hatırlatma: '%s' %s gönderildi (%s)" % (o["proje"], o["tur_adi"], o["id"]))
        return sonuc
    return sonuc


# --------------------------------------------------------------------------
# Elle yayın eşleşmesi (elle_islem kancası)
# --------------------------------------------------------------------------

_ELLE_PLATFORM = {"bluesky": "telegram"}


def elle_yayin_eslestir(proje, platform, zaman, kayit_id, simdi=None):
    """`elle_islem ekle --islem yayinladi` -> (state_etkisi, mesaj).

    Eşleşme: proje + platform + `TUREV_ELLE_ESLESME_SAAT` içindeki `planlandi` /
    `onay_bekliyor` kayıt (referans: hedef_an ya da hatirlatildi_at). Tek aday ->
    `yayinlandi`; birden fazla -> hiçbiri işaretlenmez, mesajda raporlanır."""
    st = _durum_oku(proje)
    plan = (st or {}).get("turev_plani")
    zt = _ts(zaman)
    if not isinstance(plan, list) or zt is None:
        return None, ""
    hedef_platform = _ELLE_PLATFORM.get(platform, platform)
    pencere = float(config.TUREV_ELLE_ESLESME_SAAT) * SAAT
    adaylar = []
    for k in plan:
        if (not isinstance(k, dict) or k.get("platform") != hedef_platform
                or k.get("durum") not in ("planlandi", "onay_bekliyor")):
            continue
        refs = [_ts(k.get("hedef_an")), _ts(k.get("hatirlatildi_at"))]
        if any(r is not None and abs(r - zt) <= pencere for r in refs):
            adaylar.append(k)
    if not adaylar:
        return None, ""
    if len(adaylar) > 1:
        return None, ("türev: %d aday kayıt (%s) — hiçbiri işaretlenmedi, doğru kaydı elle seç"
                      % (len(adaylar), ", ".join(k["id"] for k in adaylar)))
    kid = adaylar[0]["id"]
    _kayit_guncelle(proje, kid, lambda k: k.update(
        durum="yayinlandi", yayin={"an": _iso(zt), "kimlik": None, "kaynak": "elle:%s" % kayit_id}),
        simdi=simdi)
    return "turev_plani:%s yayinlandi" % kid, "türev %s yayınlandı işaretlendi" % kid


def iptal(kayit_id, sebep="elle iptal (CLI)", klasorler=None, simdi=None):
    """Bir türev kaydını `iptal` yapar (yayınlanmış kayıt iptal edilemez).
    `KNL-` kimlikleri kanal takviminde aranır."""
    if str(kayit_id).startswith("KNL-"):
        return _kanal_iptal(kayit_id, sebep, simdi=simdi)
    for p in _klasorler(klasorler):
        st = _durum_oku(p) or {}
        for k in st.get("turev_plani") or []:
            if isinstance(k, dict) and k.get("id") == kayit_id:
                if k.get("durum") == "yayinlandi":
                    raise TurevHatasi("yayınlanmış kayıt iptal edilemez: %s" % kayit_id)
                _kayit_guncelle(p, kayit_id, lambda x: x.update(
                    durum="iptal", iptal_sebebi=sebep), simdi=simdi)
                return {"id": kayit_id, "proje": _ad(p), "durum": "iptal"}
    raise TurevHatasi("kayıt bulunamadı: %s" % kayit_id)


# --------------------------------------------------------------------------
# Saatlik süpürge
# --------------------------------------------------------------------------

def sirasi(log=print, simdi=None, klasorler=None, gonder=None):
    """Saatlik koşu kancası: (1) T0'ı yeni projelere plan, (2) hatırlatma, (3) TEK özet satırı.

    Hiçbir hata yukarı çıkmaz. YAYIN YOK (Aşama 1)."""
    t = time.time() if simdi is None else simdi
    klasorler = _klasorler(klasorler)
    plan_proje = plan_kayit = hata = 0
    dj_kilitli = _dj_kilidi_taze(t)
    esik = float(config.TUREV_PLAN_T0_SAAT) * SAAT
    for p in klasorler:
        if plan_proje >= int(config.TUREV_KOSU_BASINA_PLAN):
            break
        kok = _kok_adi(p)
        if kok not in TUR_TANIMLARI or (kok == "dj_sets" and dj_kilitli):
            continue
        st = _durum_oku(p)
        if not st or "turev_plani" in st:
            continue
        t0 = t0_bul(st)
        if t0 is None or t0 < t - esik:
            continue
        try:
            r = plan_uret(p, simdi=t, uygula=True)
        except Exception as e:                            # noqa: BLE001
            hata += 1
            log("  Türev takvimi: '%s' planı yazılamadı (%s)" % (_ad(p), str(e)[:120]))
            continue
        if r["yazildi"]:
            plan_proje += 1
            plan_kayit += len(r["eklenecek"])
    try:
        h = hatirlatma_sirasi(log, simdi=t, klasorler=klasorler, gonder=gonder)
        hat = h.get("sebep") or "-"
    except Exception as e:                                # noqa: BLE001
        hat = "HATA (%s)" % type(e).__name__
    try:
        bugun = len(bugun_yarin_satirlari(simdi=t, klasorler=klasorler, tavan=99))
        bugun_metin = "%d" % bugun
    except Exception as e:                                # noqa: BLE001
        bugun_metin = "hesaplanamadı (%s)" % type(e).__name__
    log("  Türev takvimi: plan %d proje (+%d kayıt)%s, bugün/yarın %s türev, hatırlatma: %s"
        % (plan_proje, plan_kayit, (", %d HATA" % hata) if hata else "", bugun_metin, hat))
    return {"plan_proje": plan_proje, "plan_kayit": plan_kayit, "hata": hata}


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _cikti_utf8():
    """cp1254 konsolda Türkçe/emoji çökmesin (tiktok_publish_plan._cikti_utf8 deseni)."""
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        except Exception:                                 # noqa: BLE001
            pass
    for akis in (sys.stdout, sys.stderr):
        try:
            akis.reconfigure(encoding="utf-8", errors="replace")
        except Exception:                                 # noqa: BLE001
            pass


def _proje_bul(deger):
    if os.path.isdir(deger):
        return deger
    ad = unicodedata.normalize("NFC", os.path.basename(os.path.normpath(deger)))
    for p in uyumluluk.proje_klasorleri():
        if _ad(p) == ad:
            return p
    raise TurevHatasi("proje bulunamadı: %r" % deger)


def _simdi_arg(deger):
    if not deger:
        return None
    t = _ts(deger)
    if t is None:
        raise TurevHatasi("--simdi okunamadı: %r" % deger)
    return t


def _kok_klasorleri(kokler):
    return None if not kokler else list(uyumluluk.proje_klasorleri(tuple(kokler)))


def _json_bas(veri):
    print(json.dumps(veri, ensure_ascii=False, indent=2))


def main(argv=None):
    _cikti_utf8()
    ap = argparse.ArgumentParser(description="Yayın sonrası türev takvimi (Aşama 1, yayın YOK).")
    alt = ap.add_subparsers(dest="komut", required=True)
    pl = alt.add_parser("plan", help="bir projenin türev planı (varsayılan KURU)")
    pl.add_argument("--proje", default=None)
    pl.add_argument("--kanal", default=None, metavar="TUR",
                    help="kanal geneli insan emeği gönderisi: soz_defteri | kulis | "
                         "soz_defteri_topluluk | kulis_topluluk")
    pl.add_argument("--kaynak-id", default=None,
                    help="--kanal *_topluluk ile: bağlı TikTok kaydının id'si (KNL-...)")
    pl.add_argument("--hedef", default=None, help="--kanal ile: ISO an (TR), golden-hour içinde")
    pl.add_argument("--baslik", default=None, help="--kanal ile: gönderi başlığı")
    pl.add_argument("--ilgili-proje", default=None, help="--kanal ile: konu şarkısı (bilgi)")
    pl.add_argument("--paket", default=None, help="--kanal ile: içerik paketi yolu")
    pl.add_argument("--kanal-yolu", default=None, help=argparse.SUPPRESS)
    pl.add_argument("--uygula", action="store_true", help="state.json'a YAZ")
    pl.add_argument("--json", action="store_true")
    pl.add_argument("--simdi", default=None, help=argparse.SUPPRESS)
    tk = alt.add_parser("takvim", help="katalog takvimi (salt okuma)")
    tk.add_argument("--gun", type=float, default=7)
    tk.add_argument("--json", action="store_true")
    tk.add_argument("--kok", action="append", default=None, help=argparse.SUPPRESS)
    tk.add_argument("--simdi", default=None, help=argparse.SUPPRESS)
    tk.add_argument("--kanal-yolu", default=None, help=argparse.SUPPRESS)
    sn = alt.add_parser("sirada", help="sıradaki türev")
    sn.add_argument("--json", action="store_true")
    sn.add_argument("--kok", action="append", default=None, help=argparse.SUPPRESS)
    sn.add_argument("--simdi", default=None, help=argparse.SUPPRESS)
    ip = alt.add_parser("iptal", help="bir türev kaydını iptal et (YAZAR)")
    ip.add_argument("id")
    ip.add_argument("--sebep", default="elle iptal (CLI)")
    ip.add_argument("--kok", action="append", default=None, help=argparse.SUPPRESS)
    args = ap.parse_args(argv)

    try:
        if args.komut == "plan" and args.kanal:
            r = kanal_plan(args.kanal, args.hedef, args.baslik, ilgili_proje=args.ilgili_proje,
                           paket=args.paket, simdi=_simdi_arg(args.simdi), uygula=args.uygula,
                           yol=args.kanal_yolu, kaynak_id=args.kaynak_id)
            if args.json:
                _json_bas(r)
                return 0
            k = r["kayit"]
            print("KANAL PLANI %s" % ("UYGULANDI" if args.uygula else "KURU (hiçbir şey yazılmadı)"))
            print("Dosya: %s" % r["yol"])
            print("Sonuç: %s%s" % (r["sebep"], " · YAZILDI" if r["yazildi"] else ""))
            print("  %s  %s [%s] elle, insan emeği (kesit tavanı dışı)  %s" % (
                k["hedef_an"][:16].replace("T", " "), k["baslik"], k["platform"], k["id"]))
            return 0
        if args.komut == "plan":
            if not args.proje:
                print("HATA: --proje ya da --kanal gerekli")
                return 2
            r = plan_uret(_proje_bul(args.proje), simdi=_simdi_arg(args.simdi), uygula=args.uygula)
            if args.json:
                _json_bas(r)
                return 0
            print("PLAN %s" % ("UYGULANDI" if args.uygula else "KURU (hiçbir şey yazılmadı)"))
            print("Proje: %s (%s) · T0: %s" % (r["ad"], r["kok"], r["t0"] or "-"))
            print("Sonuç: %s · mevcut kayıt: %d%s" % (r["sebep"], r["mevcut"],
                                                   " · YAZILDI" if r["yazildi"] else ""))
            for k in r["eklenecek"]:
                print("  %s  %-40s [%s] %s%s  %s" % (
                    k["hedef_an"][:16].replace("T", " "), k["tur_adi"], k["platform"],
                    "elle" if k["elle"] else "otomatik", " koşullu" if k["kosul"] else "",
                    k["id"]))
            return 0
        if args.komut == "takvim":
            veri = takvim(gun=args.gun, simdi=_simdi_arg(args.simdi),
                          klasorler=_kok_klasorleri(args.kok), kanal_yolu=args.kanal_yolu)
            if args.json:
                _json_bas(veri)
                return 0
            t = _ts(veri["uretildi_at"])
            print("TÜREV TAKVİMİ %s → %s" % (veri["aralik"]["bas"][:16], veri["aralik"]["bit"][:16]))
            print("Yeni yayınlar: %s" % (", ".join(
                "%s %s%s" % (y["proje"], y["an"][:16].replace("T", " "),
                             " (tahmini)" if y["tahmini"] else "")
                for y in veri["yeni_yayinlar"]) or "-"))
            print("Olaylar (%d):" % len(veri["olaylar"]))
            for o in veri["olaylar"]:
                print("  " + _olay_satiri(o, t))
            if veri["kanal_gonderileri"]:
                print("Kanal gönderileri — insan emeği, kesit tavanı dışı (%d):"
                      % len(veri["kanal_gonderileri"]))
                for o in veri["kanal_gonderileri"]:
                    print("  " + _olay_satiri(o, t))
            if veri["kanal_takvimi_okunamadi"]:
                print("UYARI: kanal takvimi okunamadı (bozuk JSON?)")
            if veri["durdurulanlar"]:
                print("Durdurulan (%d):" % len(veri["durdurulanlar"]))
                for o in veri["durdurulanlar"]:
                    print("  %s · %s — %s" % (o["proje"], o["tur_adi"], o["engel"]))
            if veri["dusenler"]:
                print("Düşen (%d, state'e yazılmadı):" % len(veri["dusenler"]))
                for o in veri["dusenler"]:
                    print("  %s · %s — %s" % (o["proje"], o["tur_adi"], o["etkin"]))
            if veri["atlanan_kayitlar"]:
                print("UYARI: %d bozuk türev kaydı atlandı" % veri["atlanan_kayitlar"])
            return 0
        if args.komut == "sirada":
            o = sirada_ne(simdi=_simdi_arg(args.simdi), klasorler=_kok_klasorleri(args.kok))
            if args.json:
                _json_bas(o)
            else:
                print(_olay_satiri(o) if o else "Sırada türev yok.")
            return 0
        if args.komut == "iptal":
            _json_bas(iptal(args.id, sebep=args.sebep, klasorler=_kok_klasorleri(args.kok)))
            return 0
    except TurevHatasi as e:
        print("HATA: %s" % e)
        return 2
    return 2


if __name__ == "__main__":
    sys.exit(main())
