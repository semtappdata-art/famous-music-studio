# -*- coding: utf-8 -*-
"""TikTok WEB PLANLAMA — TikTok Studio web + yerleşik "Planla" akışının KOD tarafı.

    python upload/tiktok_web.py plan-oner [--gun 10] [--json]
    python upload/tiktok_web.py paket --proje "Kader Ortakları" [--an ISO] [--json]
    python upload/tiktok_web.py isaretle --proje "Kader Ortakları" --an 2026-09-15T18:00:00+03:00 \
        [--studio-id ...] [--sha1 <paketteki aciklama_sha1>] [--kaynak claude]
    python upload/tiktok_web.py yayinlandi --proje "Kader Ortakları" [--kaynak cli]
    python upload/tiktok_web.py iptal --proje "Kader Ortakları" [--sebep "..."]
    python upload/tiktok_web.py durum [--json]

NEDEN VAR (kullanıcı kararı 2026-09-13): "TikTok'ta tüm işlemleri web'den yap. Makine
boşta beklemesin; saati platformun web takvimiyle ayarla." Claude, KULLANICI İSTEDİĞİNDE
Chrome'dan tiktok.com/tiktokstudio/upload'a dikey videoyu yükler, kitin açıklamasını ve
ayarlarını girer, "Planla" ile ileri bir an seçer; yayını TikTok kendisi yapar. Bu modül
tarayıcıya DOKUNMAZ: state modeli, kapılar, planlama hesabı, işaretleme ve görünürlük.
ToS: TikTok Şartları md. 5 otomatik betikle etkileşimi yasaklıyor — zamanlanmış tarayıcı
otomasyonu YOK; bu modülün hiçbir yolu tarayıcı açmaz.

MOD: `config.TIKTOK_AKIS` ("web_planla" varsayılan | "api_taslak" eski). Web modunda
`auto_process` yeni projeye API taslağı YÜKLEMEZ ve `_is_fully_done` TikTok anahtarını
şart koşmaz (TikTok işi bu modülün bekleyen listesinde — CLAUDE.md kalıp B).

STATE (proje state.json, atomik `state_io`): `tiktok_web` sözlüğü
  durum          planlandi | yayinlandi | iptal
  planlanan_an   ISO +03:00 (TikTok Studio "Planla" anı)
  yuklendi_at    işaretleme anı (ISO +03:00)
  studio_id      TikTok Studio gönderi kimliği (varsa)
  aciklama_sha1  girilen açıklamanın (kit metni) sha1'i
  kaynak         claude | cli | pano | telegram ...
  onaylandi_at / onay_kaynak   (yayinlandi olunca), iptal_at / iptal_sebebi
KURAL: planlanan an geçti diye hiçbir saatlik yol `yayinlandi` YAZMAZ — durum
"doğrulanmadı" görünür; onayı kullanıcı ("yayınladım <ad>" Telegram becerisi,
`elle_islem ekle --islem yayinladi`) ya da Claude (`yayinlandi` alt komutu) verir.
Onayda `tiktok_published_at` = planlanan an, `tiktok_published_kaynak` =
"TikTok Studio web (Planla <an>)" — MEVCUT `tiktok_publish_plan.isaretle_yayinlandi` ile.
Otomatik doğrulama YOK: uygulamanın scope'ları `user.info.basic,video.upload`
(`tiktok_auth.SCOPES`); `video.list` scope'u yok, istenmedi.

PLANLAMA KURALLARI (eşikler config'te; `_kural_ihlalleri` TEK yer):
  * aday: YouTube uzun video public (ya da public'e planlı); `tiktok_published_at` /
    etkin `tiktok_web` yok; `build_plan` hazir=True; API durumu PUBLISH_COMPLETE değil.
    Durumu hiç okunmamış / bayat / kit gönderilmiş eski API taslağı ADAY DEĞİL →
    "önce içerik kontrolü gerekli" (telefondan yayınlanmış olabilir: ÇİFT GÖNDERİ).
    Kit sırasındaki taslak da aday değil (kit onu bugün gönderecek).
  * an: golden-hour içinde (15 dk adım), YouTube public anından sonra, en az
    `TIKTOK_WEB_PLANLA_MIN_DAKIKA` ileride, en fazla `TIKTOK_WEB_PLANLA_MAX_GUN`;
    TikTok gönderileri arası ≥ `TIKTOK_KIT_ARALIK_SAAT`, TR günü başına
    `TIKTOK_KIT_GUNLUK_TAVAN`, kayan 7 günde `TIKTOK_KIT_HAFTALIK_TAVAN`;
    yeni yayın (türev takvimi T0 bantları) ±`TUREV_YENI_YAYIN_BANDI_SAAT`;
    türev takviminin yüzey olaylarıyla AYNI golden-hour penceresinde değil
    (TikTok platformlu kesin türev olayı TikTok gönderisi sayılır).
  * sayılan TikTok gönderileri: etkin web planları, güvenilir damgalı
    `tiktok_published_at` (API tespit damgası "PUBLISH_COMPLETE" SAYILMAZ — tespit anıdır,
    yayın anı değil), onaylanmamış kit gönderimleri, kit sırasının bir sonraki
    golden-hour rezervi.

ÜÇ SORU:
  1. Kim çağırıyor? Planlama/işaretleme: kullanıcı başlattığında Claude oturumu (CLI).
     Hatırlatma + özet satırı: `auto_process.main()` finally → `_tiktok_web_sirasi()` →
     `kontrol_hatirlatma(log)`. Okuyanlar: `weekly_report._tiktok_web_bolumu`,
     `tiktok_yayin_kiti` (kit kapısı), `tiktok_upload.notify_pending_publish`,
     `tiktok_yayin_dogrulama.adaylari_bul`, `tiktok_yayin_onayi`, `elle_islem`,
     pano/Hermes (`durum --json`).
  2. Hangi görev? Saatlik AutoProcess; yeni görev YOK; `_is_fully_done`'a EKLENMEDİ.
  3. Çalışmadığını nasıl anlarız? Her koşuda tek "  TikTok web:" log satırı;
     `tests/test_tiktok_web.py`.

YAZIM KORUMASI: `PYTEST_CURRENT_TEST` ortamında GERÇEK köklerin altındaki state'e
yazma REDDEDİLİR; hatırlatma gerçek köklerde bildirim GÖNDERMEZ.
"""

import argparse
import datetime
import hashlib
import json
import os
import sys
import time
import unicodedata

_UPLOAD = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(_UPLOAD)
for _yol in (_UPLOAD, REPO):
    if _yol not in sys.path:
        sys.path.insert(0, _yol)

import config
import state_io
import uyumluluk

# NOT: tiktok_publish_plan / tiktok_yayin_kiti / turev_takvimi / elle_islem / notify
# fonksiyon İÇİNDE import ediliyor. NEDEN: kit, tiktok_upload ve doğrulama bu modülün
# `web_aktif`ini modül düzeyinde içe aktarıyor; tepede ağır import döngü kurardı.

TR = config.TR_TZ
SAAT = 3600
GUN_SN = 24 * SAAT
SURUM = 1
ALAN = "tiktok_web"
DURUMLAR = ("planlandi", "yayinlandi", "iptal")
AKTIF_DURUMLAR = ("planlandi", "yayinlandi")
ADIM_DAKIKA = 15
DURUM_TASLAKTA = "SEND_TO_USER_INBOX"
DURUM_YAYINDA = "PUBLISH_COMPLETE"
GERCEK_KOKLER = tuple(uyumluluk.KOKLER)
DURUM_DOSYASI = os.path.join(REPO, "upload", "saglik_durum.json")
HATIRLATMA_GUN_DAMGASI = "tiktok_web_kontrol_gun"
WEB_KAYNAK_BICIMI = "TikTok Studio web (Planla %s)"


class TiktokWebHatasi(Exception):
    """İşaretleme/doğrulama reddi — hiçbir şey yazılmadı."""


# --------------------------------------------------------------------------
# Mod ve kayıt yardımcıları (ucuz; başka modüller modül düzeyinde kullanır)
# --------------------------------------------------------------------------

def web_modu() -> bool:
    return config.tiktok_web_modu() if hasattr(config, "tiktok_web_modu") else True


def web_kaydi(st):
    v = (st or {}).get(ALAN)
    return v if isinstance(v, dict) else None


def web_aktif(st) -> bool:
    """Projede etkin bir web kaydı var mı (planlandi/yayinlandi).

    FAIL-CLOSED: alan var ama bozuksa (sözlük değil / tanınmayan durum) ETKİN sayılır —
    kit ve API taslağı "belki web'de planlı" bir projeye gitmesin. Yalnız `iptal` etkin değil."""
    v = (st or {}).get(ALAN)
    if v in (None, "", {}):
        return False
    if isinstance(v, dict) and v.get("durum") == "iptal":
        return False
    return True


def _dt(ts):
    return datetime.datetime.fromtimestamp(ts, TR)


def _iso(ts):
    return _dt(ts).replace(microsecond=0).isoformat()


def _yerel_damga(ts):
    """`tiktok_published_at` biçimi (TR yerel, ofsetsiz) — tiktok_upload ile aynı."""
    return _dt(ts).strftime("%Y-%m-%dT%H:%M:%S")


def _ts(deger):
    """ISO (Z'li / ofsetli / ofsetsiz=TR) -> epoch; bozuksa None."""
    if not isinstance(deger, str) or not deger.strip():
        return None
    try:
        an = datetime.datetime.fromisoformat(deger.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if an.tzinfo is None:
        an = an.replace(tzinfo=TR)
    return an.timestamp()


def _golden_icinde(ts):
    s = _dt(ts).hour
    return any(b <= s < e for b, e in config.GOLDEN_HOURS)


def _pencere(ts):
    an = _dt(ts)
    for b, e in config.GOLDEN_HOURS:
        if b <= an.hour < e:
            return (an.date().isoformat(), b)
    return None


def _max_gun():
    return float(getattr(config, "TIKTOK_WEB_PLANLA_MAX_GUN", 10))


def _min_dakika():
    return float(getattr(config, "TIKTOK_WEB_PLANLA_MIN_DAKIKA", 60))


def sha1(metin: str) -> str:
    return hashlib.sha1(str(metin).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# Katalog
# --------------------------------------------------------------------------

def _ad(proje):
    return unicodedata.normalize("NFC", os.path.basename(os.path.normpath(proje)))


def _durum_oku(proje):
    yol = os.path.join(proje, "state.json")
    if not os.path.isfile(yol):
        return {}
    try:
        with open(yol, "r", encoding="utf-8") as f:
            v = json.load(f)
    except (OSError, ValueError):
        return None
    return v if isinstance(v, dict) else None


def _klasorler(klasorler=None):
    return list(uyumluluk.proje_klasorleri() if klasorler is None else klasorler)


def _katalog(klasorler=None):
    """[(yol, ad, st)] ve okunamayan ad listesi."""
    iyi, bozuk = [], []
    for p in _klasorler(klasorler):
        st = _durum_oku(p)
        if st is None:
            bozuk.append(_ad(p))
            continue
        iyi.append((p, _ad(p), st))
    return iyi, bozuk


def proje_bul(deger, klasorler=None):
    """Klasör adı (NFC, büyük/küçük harf duyarsız) ya da yol -> proje yolu."""
    if not deger or not str(deger).strip():
        raise TiktokWebHatasi("proje adı boş")
    hedef = unicodedata.normalize("NFC", str(deger).strip())
    adaylar = _klasorler(klasorler)
    if os.path.isdir(hedef):
        mutlak = os.path.normcase(os.path.abspath(hedef))
        for p in adaylar:
            if os.path.normcase(os.path.abspath(p)) == mutlak:
                return p
    bulunan = [p for p in adaylar if _ad(p) == hedef]
    if not bulunan:
        bulunan = [p for p in adaylar if _ad(p).casefold() == hedef.casefold()]
    if len(bulunan) == 1:
        return bulunan[0]
    if not bulunan:
        raise TiktokWebHatasi("proje bulunamadı: %r" % deger)
    raise TiktokWebHatasi("belirsiz proje adı: %r (%d eşleşme)" % (deger, len(bulunan)))


def _testte_gercek_yol(yol):
    if not os.environ.get("PYTEST_CURRENT_TEST"):
        return False
    y = os.path.normcase(os.path.abspath(yol))
    for kok in GERCEK_KOKLER:
        k = os.path.normcase(os.path.abspath(kok))
        if y == k or y.startswith(k + os.sep):
            return True
    return False


def _yazim_kapisi(proje):
    if _testte_gercek_yol(proje):
        raise TiktokWebHatasi("test sırasında GERÇEK state'e yazma reddedildi: %s" % proje)


# --------------------------------------------------------------------------
# Aday sınıflandırması
# --------------------------------------------------------------------------

def _youtube_yayinda(st):
    if not st.get("youtube_video_id"):
        return False
    gercek = st.get("youtube_privacy_gercek")
    if gercek:
        return gercek == "public"
    return st.get("youtube_privacy") == "public"


def aday_degerlendir(proje, st=None, simdi=None, kit_adayi=None):
    """("aday"|"kontrol"|"degil", sebep). build_plan'ı yalnız ucuz elemelerden sonra çağırır."""
    import tiktok_publish_plan as TPP
    import turev_takvimi as TT

    t = time.time() if simdi is None else simdi
    st = _durum_oku(proje) if st is None else st
    if st is None:
        return "degil", "state.json okunamadı"
    if web_aktif(st):
        k = web_kaydi(st) or {}
        return "degil", "web kaydı var (%s %s)" % (k.get("durum", "bozuk"),
                                                   k.get("planlanan_an", ""))
    if st.get("tiktok_published_at"):
        return "degil", "TikTok'ta yayınlandı işaretli (%s)" % st["tiktok_published_at"]
    if not _youtube_yayinda(st):
        return "degil", "YouTube uzun video public değil"
    if TT.t0_bul(st) is None:
        return "degil", "YouTube public anı bilinmiyor"
    durum = st.get("tiktok_publish_status")
    if st.get("tiktok_publish_id") and durum == DURUM_YAYINDA:
        return "degil", "API durumu PUBLISH_COMPLETE (TikTok'ta yayında)"
    try:
        plan = TPP.build_plan(proje)
    except Exception as e:                                   # noqa: BLE001
        plan = {"hazir": False, "engel": "plan hesaplanamadı (%s)" % type(e).__name__}
    if not plan.get("hazir"):
        return "degil", "hazir=False: %s" % str(plan.get("engel") or "sebep bilinmiyor")[:160]
    if st.get("tiktok_publish_id") and not st.get("tiktok_status_denenmez"):
        if st.get("tiktok_kit_gonderildi_at"):
            return "kontrol", ("eski API taslağına kit gönderildi (%s) — telefondan "
                               "yayınlanmış olabilir" % st["tiktok_kit_gonderildi_at"])
        if kit_adayi and os.path.normcase(os.path.abspath(kit_adayi)) == \
                os.path.normcase(os.path.abspath(proje)):
            return "kontrol", "kit sırasında (eski API taslağı, kit bu golden-hour'da gidecek)"
        if not durum:
            return "kontrol", ("eski API taslağının durumu hiç okunmadı — telefondan "
                               "yayınlanmış olabilir")
        if durum != DURUM_TASLAKTA:
            return "kontrol", "eski API taslağı durumu %s" % durum
        tazelik = float(getattr(config, "TIKTOK_KIT_DURUM_TAZELIK_SAAT", 72)) * SAAT
        okundu = _ts(st.get("tiktok_status_checked_at"))
        if okundu is None or t - okundu > tazelik:
            return "kontrol", "eski API taslağının durum okuması bayat"
    return "aday", "uygun"


# --------------------------------------------------------------------------
# Dolu anlar ve kurallar
# --------------------------------------------------------------------------

def _gonderi_anlari(katalog, haric=None):
    """[(ts, ad, tur)] — sayılan TikTok gönderileri (proje başına en fazla bir)."""
    haric_n = os.path.normcase(os.path.abspath(haric)) if haric else None
    anlar = []
    for p, ad, st in katalog:
        if haric_n and os.path.normcase(os.path.abspath(p)) == haric_n:
            continue
        w = web_kaydi(st)
        if w and w.get("durum") in AKTIF_DURUMLAR:
            ts = _ts(w.get("planlanan_an"))
            if ts is not None:
                anlar.append((ts, ad, "web planı"))
                continue
        yayin = st.get("tiktok_published_at")
        if yayin and "PUBLISH_COMPLETE" not in str(st.get("tiktok_published_kaynak") or ""):
            ts = _ts(yayin)
            if ts is not None:
                anlar.append((ts, ad, "yayın"))
                continue
        kit = _ts(st.get("tiktok_kit_gonderildi_at"))
        if kit is not None:
            anlar.append((kit, ad, "kit"))
    return anlar


def _kit_rezervi(katalog, simdi, klasorler=None):
    """(ts, ad, "kit sırası") ya da None — kit bir sonraki uygun golden-hour'da gidecekse."""
    if not getattr(config, "TIKTOK_KIT_AKTIF", False):
        return None, None
    try:
        import tiktok_yayin_kiti as K
        durumlar = [(p, st) for p, _, st in katalog]
        if any(K._onay_bekliyor(st) for _, st in durumlar):
            return None, None
        secim = K.siradaki_kit_adayi([p for p, _, _ in katalog], simdi)
        aday = secim.get("aday")
        if not aday:
            return None, None
        for ts in _grid(simdi, simdi + _max_gun() * GUN_SN):
            if K._tempo_engeli(durumlar, ts) is None:
                return (ts, _ad(aday), "kit sırası"), aday
    except Exception:                                        # noqa: BLE001
        return None, None
    return None, None


def _grid(bas, bit):
    """[bas, bit] içindeki golden-hour anları, 15 dk adımla, artan sırada."""
    gun = _dt(bas).date()
    son = _dt(bit).date()
    while gun <= son:
        for b, e in config.GOLDEN_HOURS:
            for dk in range(b * 60, e * 60, ADIM_DAKIKA):
                ts = datetime.datetime(gun.year, gun.month, gun.day, dk // 60, dk % 60,
                                       tzinfo=TR).timestamp()
                if bas <= ts <= bit:
                    yield ts
        gun += datetime.timedelta(days=1)


def _baglam(simdi, klasorler=None, katalog=None):
    """Kural bağlamı: katalog, yeni yayın bantları, türev olayları, kit rezervi."""
    import turev_takvimi as TT
    if katalog is None:
        katalog, _ = _katalog(klasorler)
    try:
        tt_katalog, _ = TT._katalog([p for p, _, _ in katalog])
        bantlar = [(an, ad) for an, ad, _ in TT.yeni_yayin_anlari(tt_katalog, simdi)]
    except Exception:                                        # noqa: BLE001
        bantlar = None                                       # fail-closed: aşağıda engel
    try:
        olaylar = TT.takvim(gun=_max_gun() + 2, simdi=simdi,
                            klasorler=[p for p, _, _ in katalog])["olaylar"]
    except Exception:                                        # noqa: BLE001
        olaylar = None
    rezerv, kit_adayi = _kit_rezervi(katalog, simdi, klasorler)
    return {"katalog": katalog, "bantlar": bantlar, "turev": olaylar,
            "kit_rezervi": rezerv, "kit_adayi": kit_adayi}


def _kural_ihlalleri(an, proje, st, baglam, simdi, ek_anlar=(), min_dakika=None):
    """Kurala uymayan her şeyin listesi (boş = uygun). TEK kural yeri."""
    import turev_takvimi as TT

    ihlal = []
    lead = (_min_dakika() if min_dakika is None else min_dakika) * 60
    if an <= simdi + lead:
        ihlal.append("an çok yakın/geçmiş (en az %d dk ileride olmalı)" % (lead // 60))
    if an > simdi + _max_gun() * GUN_SN:
        ihlal.append("TikTok Studio planlama sınırı: en fazla %g gün ileri" % _max_gun())
    if not _golden_icinde(an):
        ihlal.append("golden-hour dışında (%s)" % ", ".join(
            "%02d-%02d" % g for g in config.GOLDEN_HOURS))
    t0 = TT.t0_bul(st)
    if t0 is None:
        ihlal.append("YouTube public anı bilinmiyor")
    elif an <= t0:
        ihlal.append("YouTube public anından (%s) önce" % _iso(t0))
    if baglam["bantlar"] is None:
        ihlal.append("yeni yayın bantları hesaplanamadı (fail-closed)")
    else:
        bant = float(getattr(config, "TUREV_YENI_YAYIN_BANDI_SAAT", 24)) * SAAT
        for b, bad in baglam["bantlar"]:
            if abs(an - b) < bant:
                ihlal.append("yeni yayın ±%d sa (%s %s)" % (bant // SAAT, bad, _iso(b)))
                break
    gonderiler = [(ts, ad, tur) for ts, ad, tur in
                  _gonderi_anlari(baglam["katalog"], haric=proje)]
    if baglam["kit_rezervi"] and baglam["kit_adayi"] and \
            os.path.normcase(os.path.abspath(baglam["kit_adayi"])) != \
            os.path.normcase(os.path.abspath(proje)):
        gonderiler.append(baglam["kit_rezervi"])
    gonderiler.extend(ek_anlar)
    if baglam["turev"] is None:
        ihlal.append("türev takvimi hesaplanamadı (fail-closed)")
    else:
        pen = _pencere(an)
        for o in baglam["turev"]:
            if not o.get("yuzey") or o.get("etkin") not in (
                    "planli", "kosullu", "onay_bekliyor", "yayinlandi"):
                continue
            ots = _ts(o.get("an"))
            if ots is None:
                continue
            if pen is not None and _pencere(ots) == pen:
                ihlal.append("türev çakışması (%s %s, %s)" % (o.get("proje"), o.get("tur"),
                                                             o.get("an")))
                break
        for o in baglam["turev"]:
            ots = _ts(o.get("an"))
            if (o.get("yuzey") and o.get("platform") == "tiktok" and ots is not None
                    and o.get("etkin") in ("planli", "onay_bekliyor", "yayinlandi")):
                gonderiler.append((ots, o.get("proje"), "türev"))
    aralik = float(config.TIKTOK_KIT_ARALIK_SAAT) * SAAT
    for ts, ad, tur in sorted(gonderiler):
        if abs(an - ts) < aralik:
            ihlal.append("iki TikTok gönderisi arası en az %g sa (%s: %s %s)"
                         % (aralik / SAAT, tur, ad, _iso(ts)))
            break
    gun = _dt(an).date()
    ayni_gun = sum(1 for ts, _, _ in gonderiler if _dt(ts).date() == gun)
    if ayni_gun >= int(config.TIKTOK_KIT_GUNLUK_TAVAN):
        ihlal.append("günlük tavan dolu (%d/%d)" % (ayni_gun, config.TIKTOK_KIT_GUNLUK_TAVAN))
    tavan = int(config.TIKTOK_KIT_HAFTALIK_TAVAN)
    anlar = sorted([ts for ts, _, _ in gonderiler] + [an])
    j = anlar.index(an)
    for i in range(max(0, j - tavan), j + 1):
        if i + tavan < len(anlar) and anlar[i + tavan] - anlar[i] < 7 * GUN_SN:
            ihlal.append("haftalık tavan dolu (kayan 7 günde en fazla %d)" % tavan)
            break
    return ihlal


def ilk_uygun_an(proje, st, baglam, simdi, gun=None, ek_anlar=()):
    gun = _max_gun() if gun is None else min(float(gun), _max_gun())
    for ts in _grid(simdi, simdi + gun * GUN_SN):
        if not _kural_ihlalleri(ts, proje, st, baglam, simdi, ek_anlar):
            return ts
    return None


# --------------------------------------------------------------------------
# Paket (tarayıcı ajanının girdiği her şey)
# --------------------------------------------------------------------------

def web_ayarlari(ai_mod, kapak=None, an=None):
    """TikTok Studio web formundaki alan adlarıyla (2026-09-13 pilotunda görülen)."""
    if "etiket" in str(ai_mod):
        ai = "AÇIK"
    else:
        ai = "KAPALI — beyan açıklamada (config.TIKTOK_AI_BEYANI=aciklama)"
    return [
        {"alan": "Açıklama", "deger": "paketteki `aciklama` metnini olduğu gibi yapıştır"},
        {"alan": "Kapak yükleyin", "deger": kapak or "kapak yok — varsayılan kareyi bırak"},
        {"alan": "Kimler görebilir", "deger": "Herkes"},
        {"alan": "Yorum", "deger": "AÇIK"},
        {"alan": "İçeriği yeniden kullanma", "deger": "AÇIK (düet + stitch tek kutu)"},
        {"alan": "AI ile oluşturulmuş içerik", "deger": ai},
        {"alan": "Gönderi içeriğini açıklayın", "deger": "KAPALI"},
        {"alan": "HD yükleme", "deger": "AÇIK"},
        {"alan": "Planla", "deger": _iso(an) if an is not None else "önerilen an yok"},
    ]


def paket(proje, an=None, simdi=None, baglam=None, klasorler=None):
    """Tek projenin tarayıcı paketi — HİÇBİR ŞEY YAZMAZ, GÖNDERMEZ.

    Metin `tiktok_yayin_kiti.build_kit`'ten (kopya değil; AI beyanı kitteki mod).
    `an` verilmezse kurallara uyan ilk an hesaplanır (yalnız KAYITLI planlara göre)."""
    import tiktok_publish_plan as TPP
    import tiktok_yayin_kiti as K

    t = time.time() if simdi is None else simdi
    st = _durum_oku(proje) or {}
    if baglam is None:
        baglam = _baglam(t, klasorler)
    sinif, sebep = aday_degerlendir(proje, st, t, baglam["kit_adayi"])
    kit = K.build_kit(proje)
    if an is None and sinif == "aday":
        an = ilk_uygun_an(proje, st, baglam, t)
    video = os.path.abspath(os.path.join(proje, "output", TPP.VIDEO_ADI))
    kapak = os.path.abspath(kit["kapak"]) if kit.get("kapak") else None
    ozet = sha1(kit["aciklama"])
    ad = _ad(proje)
    return {
        "surum": SURUM,
        "proje": ad,
        "proje_yolu": os.path.abspath(proje),
        "baslik": kit["baslik"],
        "aday": sinif == "aday",
        "sinif": sinif,
        "sebep": sebep,
        "onerilen_an": _iso(an) if an is not None else None,
        "video": video,
        "video_var": os.path.isfile(video),
        "video_bayt": os.path.getsize(video) if os.path.isfile(video) else 0,
        "kapak": kapak,
        "aciklama": kit["aciklama"],
        "aciklama_sha1": ozet,
        "aciklama_karakter": len(kit["aciklama"].encode("utf-16-le")) // 2,
        "ai_beyani": kit["ai_beyani"],
        "ayarlar": web_ayarlari(kit["ai_beyani"], kapak, an),
        "ilk_yorum": kit["ilk_yorum"],
        "hazir": kit["hazir"],
        "engel": kit["engel"],
        "uyarilar": list(kit["uyarilar"]),
        "isaretle_komutu": ('python upload/tiktok_web.py isaretle --proje "%s" --an %s --sha1 %s'
                            % (ad, _iso(an) if an is not None else "<ISO>", ozet)),
    }


def plan_oner(gun=10, simdi=None, klasorler=None):
    """Deterministik öneri listesi — HİÇBİR ŞEY YAZMAZ."""
    import turev_takvimi as TT

    t = time.time() if simdi is None else simdi
    gun = min(float(gun), _max_gun())
    katalog, bozuk = _katalog(klasorler)
    baglam = _baglam(t, katalog=katalog)
    adaylar, kontrol, degil = [], [], []
    for p, ad, st in katalog:
        sinif, sebep = aday_degerlendir(p, st, t, baglam["kit_adayi"])
        if sinif == "aday":
            adaylar.append((TT.t0_bul(st) or 0, ad, p, st))
        elif sinif == "kontrol":
            kontrol.append({"proje": ad, "sebep": sebep})
        else:
            degil.append({"proje": ad, "sebep": sebep})
    adaylar.sort(key=lambda x: (x[0], x[1]))
    oneriler, sigmayan, ek = [], [], []
    for _, ad, p, st in adaylar:
        an = ilk_uygun_an(p, st, baglam, t, gun, ek_anlar=ek)
        if an is None:
            sigmayan.append({"proje": ad, "sebep": "önümüzdeki %g günde kurala uyan an yok" % gun})
            continue
        ek.append((an, ad, "öneri"))
        oneriler.append(paket(p, an=an, simdi=t, baglam=baglam))
    return {
        "surum": SURUM,
        "uretildi_at": _iso(t),
        "akis": getattr(config, "TIKTOK_AKIS", None),
        "gun": gun,
        "oneriler": oneriler,
        "sigmayan": sigmayan,
        "icerik_kontrolu_gerekli": kontrol,
        "aday_degil": degil,
        "kit_rezervi": ({"proje": baglam["kit_rezervi"][1], "an": _iso(baglam["kit_rezervi"][0])}
                        if baglam["kit_rezervi"] else None),
        "okunamayan": bozuk,
        "kurallar": _kurallar(),
    }


def _kurallar():
    return {
        "golden_hours": [list(g) for g in config.GOLDEN_HOURS],
        "adim_dakika": ADIM_DAKIKA,
        "aralik_saat": config.TIKTOK_KIT_ARALIK_SAAT,
        "gunluk_tavan": config.TIKTOK_KIT_GUNLUK_TAVAN,
        "haftalik_tavan": config.TIKTOK_KIT_HAFTALIK_TAVAN,
        "yeni_yayin_bandi_saat": getattr(config, "TUREV_YENI_YAYIN_BANDI_SAAT", 24),
        "max_gun": _max_gun(),
        "min_dakika": _min_dakika(),
    }


# --------------------------------------------------------------------------
# İşaretleme
# --------------------------------------------------------------------------

def planlandi_isaretle(proje, an, studio_id=None, kaynak="claude", simdi=None, sha1_beklenen=None,
                       klasorler=None, defter_yol=None):
    """Doğrular, `tiktok_web.durum=planlandi` yazar, deftere satır ekler. Red -> TiktokWebHatasi."""
    import elle_islem
    import tiktok_publish_plan as TPP
    import tiktok_yayin_kiti as K

    t = time.time() if simdi is None else simdi
    if kaynak not in elle_islem.KAYNAKLAR:
        raise TiktokWebHatasi("geçersiz kaynak: %r — geçerli: %s"
                              % (kaynak, ", ".join(elle_islem.KAYNAKLAR)))
    an_ts = _ts(an) if isinstance(an, str) else (float(an) if an is not None else None)
    if an_ts is None:
        raise TiktokWebHatasi("an okunamadı: %r (ISO, ör. 2026-09-15T18:00:00+03:00)" % (an,))
    _yazim_kapisi(proje)
    try:
        st = TPP._durum_oku_kesin(proje)
    except TPP.IsaretlemeHatasi as e:
        raise TiktokWebHatasi(str(e))
    baglam = _baglam(t, klasorler)
    sinif, sebep = aday_degerlendir(proje, st, t, baglam["kit_adayi"])
    if sinif != "aday":
        raise TiktokWebHatasi("REDDEDİLDİ: '%s' aday değil — %s" % (_ad(proje), sebep))
    kit = K.build_kit(proje)
    ozet = sha1(kit["aciklama"])
    if sha1_beklenen and sha1_beklenen != ozet:
        raise TiktokWebHatasi("REDDEDİLDİ: açıklama değişmiş (sha1 %s != güncel %s) — paketi "
                              "yeniden al ve metni düzelt" % (sha1_beklenen, ozet))
    ihlal = _kural_ihlalleri(an_ts, proje, st, baglam, t, min_dakika=0)
    if ihlal:
        raise TiktokWebHatasi("REDDEDİLDİ: %s kurala uymuyor — %s" % (_iso(an_ts), "; ".join(ihlal)))
    kayit = {"durum": "planlandi", "planlanan_an": _iso(an_ts), "yuklendi_at": _iso(t),
             "studio_id": studio_id or None, "aciklama_sha1": ozet, "kaynak": kaynak,
             "surum": SURUM}
    st[ALAN] = kayit
    state_io.durum_yaz(proje, st)
    defter = ""
    try:
        sonuc = elle_islem.ekle(
            "tiktok", "planladi",
            "TikTok Studio web: '%s' yüklendi, Planla %s" % (kit["baslik"], _iso(an_ts)),
            proje=_ad(proje), zaman=_iso(t), kaynak=kaynak, kanit=studio_id or None,
            yol=defter_yol, state_yansit=False, state_etkisi="tiktok_web.planlandi",
            proje_klasorleri=klasorler, simdi=t)
        defter = sonuc.get("mesaj", "")
    except Exception as e:                                   # noqa: BLE001
        defter = "UYARI: deftere yazılamadı (%s: %s)" % (type(e).__name__, str(e)[:150])
    return {"durum": "planlandi", "proje": _ad(proje), "kayit": kayit, "defter": defter}


def yayinlandi_isaretle(proje, kaynak, simdi=None):
    """Planlanan an GEÇMİŞ web kaydını yayınlandı yapar (+ tiktok_published_at). (yazildi, mesaj)."""
    import tiktok_publish_plan as TPP

    t = time.time() if simdi is None else simdi
    _yazim_kapisi(proje)
    try:
        st = TPP._durum_oku_kesin(proje)
    except TPP.IsaretlemeHatasi as e:
        raise TiktokWebHatasi(str(e))
    k = web_kaydi(st)
    if not k or k.get("durum") not in AKTIF_DURUMLAR:
        raise TiktokWebHatasi("'%s' için web planı yok" % _ad(proje))
    if k.get("durum") == "yayinlandi":
        return False, "'%s' ZATEN yayınlandı işaretli (%s)" % (_ad(proje), k.get("onaylandi_at"))
    an_ts = _ts(k.get("planlanan_an"))
    if an_ts is None:
        raise TiktokWebHatasi("'%s' planlanan_an bozuk: %r" % (_ad(proje), k.get("planlanan_an")))
    if an_ts > t:
        raise TiktokWebHatasi("'%s' planlanan an (%s) henüz gelmedi — yayınlanmış olamaz"
                              % (_ad(proje), _iso(an_ts)))
    if not st.get("tiktok_published_at"):
        plan = TPP.build_plan(proje)
        if not plan.get("hazir"):
            raise TiktokWebHatasi("REDDEDİLDİ: '%s' plana göre yayınlanmamalıydı — %s. TikTok "
                                  "Studio'da planı iptal et ya da bilinçli yol: "
                                  "tiktok_publish_plan.py --yayinlandi-hepsi"
                                  % (_ad(proje), plan.get("engel") or "sebep bilinmiyor"))
        try:
            TPP.isaretle_yayinlandi(proje, zaman=_yerel_damga(an_ts),
                                    kaynak=WEB_KAYNAK_BICIMI % _iso(an_ts))
        except TPP.IsaretlemeHatasi as e:
            raise TiktokWebHatasi(str(e))
    st = TPP._durum_oku_kesin(proje)
    k = dict(web_kaydi(st) or k)
    k.update(durum="yayinlandi", onaylandi_at=_iso(t), onay_kaynak=str(kaynak))
    st[ALAN] = k
    state_io.durum_yaz(proje, st)
    return True, "'%s' TikTok'ta yayınlandı işaretlendi (Planla %s)" % (_ad(proje), _iso(an_ts))


def iptal(proje, sebep="elle iptal (CLI)", simdi=None):
    t = time.time() if simdi is None else simdi
    _yazim_kapisi(proje)
    import tiktok_publish_plan as TPP
    try:
        st = TPP._durum_oku_kesin(proje)
    except TPP.IsaretlemeHatasi as e:
        raise TiktokWebHatasi(str(e))
    k = web_kaydi(st)
    if not k:
        raise TiktokWebHatasi("'%s' için web kaydı yok" % _ad(proje))
    if k.get("durum") == "yayinlandi":
        raise TiktokWebHatasi("yayınlanmış web kaydı iptal edilemez: %s" % _ad(proje))
    k = dict(k)
    k.update(durum="iptal", iptal_at=_iso(t), iptal_sebebi=str(sebep))
    st[ALAN] = k
    state_io.durum_yaz(proje, st)
    return {"durum": "iptal", "proje": _ad(proje), "kayit": k}


# --------------------------------------------------------------------------
# Görünürlük
# --------------------------------------------------------------------------

def durum(simdi=None, klasorler=None):
    """Pano/Hermes sözleşmesi (`durum --json`) — yalnız state okur, hesap yok."""
    t = time.time() if simdi is None else simdi
    katalog, bozuk = _katalog(klasorler)
    planli, yayinlandi, iptaller, bozuk_kayit = [], [], [], []
    for p, ad, st in katalog:
        if ALAN not in st:
            continue
        k = web_kaydi(st)
        if k is None or k.get("durum") not in DURUMLAR:
            bozuk_kayit.append(ad)
            continue
        an = _ts(k.get("planlanan_an"))
        gecti = an is not None and an <= t
        satir = {
            "proje": ad, "proje_yolu": os.path.abspath(p), "durum": k.get("durum"),
            "planlanan_an": k.get("planlanan_an"), "yuklendi_at": k.get("yuklendi_at"),
            "studio_id": k.get("studio_id"), "aciklama_sha1": k.get("aciklama_sha1"),
            "kaynak": k.get("kaynak"), "an_gecti": gecti,
            "dogrulanmadi": (k.get("durum") == "planlandi" and gecti
                             and not st.get("tiktok_published_at")),
            "tiktok_published_at": st.get("tiktok_published_at"),
            "onaylandi_at": k.get("onaylandi_at"),
        }
        {"planlandi": planli, "yayinlandi": yayinlandi, "iptal": iptaller}[k["durum"]].append(satir)
    sirala = lambda x: (str(x["planlanan_an"]), x["proje"])    # noqa: E731
    planli.sort(key=sirala)
    yayinlandi.sort(key=sirala)
    iptaller.sort(key=sirala)
    return {
        "surum": SURUM,
        "uretildi_at": _iso(t),
        "akis": getattr(config, "TIKTOK_AKIS", None),
        "web_modu": web_modu(),
        "planli": planli,
        "yayinlandi": yayinlandi,
        "iptal": iptaller,
        "dogrulanmadi": [s["proje"] for s in planli if s["dogrulanmadi"]],
        "bozuk_kayit": bozuk_kayit,
        "okunamayan": bozuk,
    }


def rapor_satirlari(simdi=None, klasorler=None):
    """Günlük rapor: "TikTok planlı: <proje> <an>" satırları; boşsa []."""
    d = durum(simdi, klasorler)
    satirlar = []
    for s in d["planli"]:
        an = _ts(s["planlanan_an"])
        metin = _dt(an).strftime("%d.%m %H:%M") if an is not None else str(s["planlanan_an"])
        ek = " (an geçti, doğrulanmadı)" if s["dogrulanmadi"] else ""
        satirlar.append("TikTok planlı: %s %s%s" % (s["proje"], metin, ek))
    return satirlar


def _gun_damgasi_oku():
    try:
        with open(DURUM_DOSYASI, "r", encoding="utf-8") as f:
            v = json.load(f)
        return v if isinstance(v, dict) else {}
    except (OSError, ValueError):
        return {}


def _gun_damgasi_yaz(gun):
    d = _gun_damgasi_oku()
    d[HATIRLATMA_GUN_DAMGASI] = gun
    try:
        state_io._atomik_yaz(DURUM_DOSYASI, d)
    except OSError:
        pass


def kontrol_hatirlatma(log=print, simdi=None, klasorler=None, gonder=None):
    """Planlanan anı geçmiş, doğrulanmamış web kaydı için GÜNDE EN FAZLA 1 kısa mesaj.

    Hiçbir hata yukarı çıkmaz; her koşuda tek "  TikTok web:" özet satırı."""
    sonuc = {"gonderilen": None, "sebep": ""}
    t = time.time() if simdi is None else simdi
    try:
        d = durum(t, klasorler)
    except Exception as e:                                   # noqa: BLE001
        log("  TikTok web: durum okunamadı (%s)" % type(e).__name__)
        sonuc["sebep"] = "durum okunamadı"
        return sonuc
    bekleyen = [s for s in d["planli"] if s["dogrulanmadi"]]
    gelecek = [s for s in d["planli"] if not s["an_gecti"]]
    ozet = "%s modu; %d planlı, %d doğrulanmadı" % (
        "web_planla" if d["web_modu"] else "api_taslak", len(d["planli"]), len(bekleyen))
    if gelecek:
        ozet += "; sıradaki: %s %s" % (gelecek[0]["proje"], gelecek[0]["planlanan_an"])
    if d["bozuk_kayit"]:
        ozet += "; BOZUK kayıt: %s" % ", ".join(d["bozuk_kayit"])
    if not bekleyen:
        sonuc["sebep"] = "doğrulanmayan yok"
        log("  TikTok web: %s" % ozet)
        return sonuc
    if not getattr(config, "TIKTOK_WEB_KONTROL_HATIRLATMA", True):
        sonuc["sebep"] = "hatırlatma kapalı (config)"
    elif not _golden_icinde(t):
        sonuc["sebep"] = "golden-hour dışında"
    else:
        bugun = _dt(t).date().isoformat()
        if _gun_damgasi_oku().get(HATIRLATMA_GUN_DAMGASI) == bugun:
            sonuc["sebep"] = "bugün zaten hatırlatıldı"
        elif gonder is None and klasorler is None and os.environ.get("PYTEST_CURRENT_TEST"):
            sonuc["sebep"] = "test ortamı — gerçek bildirim yok"
        else:
            ilk = bekleyen[0]["proje"]
            mesaj = "TikTok'ta çıktı mı? %s\nÇıktıysa bu sohbete yaz: yayınladım %s" % (ilk, ilk)
            if len(bekleyen) > 1:
                mesaj += "\n(+%d planlı gönderi daha doğrulanmadı)" % (len(bekleyen) - 1)
            if gonder is None:
                import notify
                gonder = notify.send
            try:
                ok = gonder("TikTok kontrolü", mesaj) is True
            except Exception:                                # noqa: BLE001
                ok = False
            if ok:
                _gun_damgasi_yaz(bugun)
                sonuc["gonderilen"] = ilk
                sonuc["sebep"] = "hatırlatma gönderildi"
            else:
                sonuc["sebep"] = "hatırlatma gönderilemedi"
    log("  TikTok web: %s; hatırlatma: %s" % (ozet, sonuc["sebep"]))
    return sonuc


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _json_bas(veri):
    print(json.dumps(veri, ensure_ascii=False, indent=2))


def main(argv=None):
    import tiktok_publish_plan as TPP
    TPP._cikti_utf8()
    ap = argparse.ArgumentParser(description="TikTok Studio web planlama yardımcıları "
                                             "(tarayıcı AÇMAZ).")
    alt = ap.add_subparsers(dest="komut", required=True)
    a = alt.add_parser("plan-oner", help="Deterministik öneri listesi (KURU, yazmaz)")
    a.add_argument("--gun", type=float, default=10)
    a.add_argument("--json", action="store_true")
    a = alt.add_parser("paket", help="Tek projenin tarayıcı paketi (yazmaz)")
    a.add_argument("--proje", required=True)
    a.add_argument("--an", default=None)
    a.add_argument("--json", action="store_true")
    a = alt.add_parser("isaretle", help="Web'de planlandı: doğrula + state + defter")
    a.add_argument("--proje", required=True)
    a.add_argument("--an", required=True)
    a.add_argument("--studio-id", default=None)
    a.add_argument("--sha1", default=None)
    a.add_argument("--kaynak", default="claude")
    a = alt.add_parser("yayinlandi", help="Planlanan anı geçmiş kaydı onayla")
    a.add_argument("--proje", required=True)
    a.add_argument("--kaynak", default="cli")
    a = alt.add_parser("iptal", help="Web planını iptal et (TikTok Studio'da da iptal et)")
    a.add_argument("--proje", required=True)
    a.add_argument("--sebep", default="elle iptal (CLI)")
    a = alt.add_parser("durum", help="Pano/Hermes özeti")
    a.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    try:
        if args.komut == "plan-oner":
            sonuc = plan_oner(gun=args.gun)
            if args.json:
                _json_bas(sonuc)
            else:
                print("TikTok web planı önerisi (%s, %g gün) — KURU" % (sonuc["uretildi_at"],
                                                                     sonuc["gun"]))
                for o in sonuc["oneriler"]:
                    print("  %s  %s  (sha1 %s)" % (o["onerilen_an"], o["proje"],
                                                   o["aciklama_sha1"][:10]))
                for s in sonuc["sigmayan"]:
                    print("  sığmayan: %s — %s" % (s["proje"], s["sebep"]))
                if sonuc["kit_rezervi"]:
                    print("  kit rezervi: %s %s" % (sonuc["kit_rezervi"]["proje"],
                                                    sonuc["kit_rezervi"]["an"]))
                print("Önce içerik kontrolü gerekli:")
                for s in sonuc["icerik_kontrolu_gerekli"]:
                    print("  %s — %s" % (s["proje"], s["sebep"]))
            return 0
        if args.komut == "paket":
            p = proje_bul(args.proje)
            an = None
            if args.an:
                an = _ts(args.an)
                if an is None:
                    raise TiktokWebHatasi("an okunamadı: %r" % args.an)
            sonuc = paket(p, an=an)
            if args.json:
                _json_bas(sonuc)
            else:
                print("%s — aday: %s (%s); önerilen an: %s" % (
                    sonuc["proje"], sonuc["aday"], sonuc["sebep"], sonuc["onerilen_an"]))
                print("video: %s\nkapak: %s\nsha1: %s" % (sonuc["video"], sonuc["kapak"],
                                                         sonuc["aciklama_sha1"]))
                print("--- açıklama ---\n%s\n--- ayarlar ---" % sonuc["aciklama"])
                for s in sonuc["ayarlar"]:
                    print("  %s → %s" % (s["alan"], s["deger"]))
            return 0
        if args.komut == "isaretle":
            sonuc = planlandi_isaretle(proje_bul(args.proje), args.an, studio_id=args.studio_id,
                                       kaynak=args.kaynak, sha1_beklenen=args.sha1)
            print("TAMAM: '%s' planlandı — %s. %s" % (sonuc["proje"],
                                                      sonuc["kayit"]["planlanan_an"],
                                                      sonuc["defter"]))
            return 0
        if args.komut == "yayinlandi":
            yazildi, mesaj = yayinlandi_isaretle(proje_bul(args.proje), kaynak=args.kaynak)
            print(("TAMAM: " if yazildi else "") + mesaj)
            return 0
        if args.komut == "iptal":
            sonuc = iptal(proje_bul(args.proje), sebep=args.sebep)
            print("TAMAM: '%s' web planı iptal edildi (TikTok Studio'da da iptal et)"
                  % sonuc["proje"])
            return 0
        if args.komut == "durum":
            sonuc = durum()
            if args.json:
                _json_bas(sonuc)
            else:
                for s in rapor_satirlari() or ["TikTok planlı gönderi yok"]:
                    print(s)
            return 0
    except TiktokWebHatasi as e:
        print(str(e))
        return 2
    return 2


if __name__ == "__main__":
    sys.exit(main())
