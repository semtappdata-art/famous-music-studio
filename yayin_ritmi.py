# -*- coding: utf-8 -*-
"""Kanal geneli YAYIN RİTMİ kuralları — tek yardımcı modül (ozgunluk_plani.md §2d, Aşama 1).

Onaylanan karar 4 (2026-09-13):
  R1  DJ seti / derleme ile şarkı arasında ORTAK 48 saat (`YAYIN_RITMI_SET_SARKI_ARA_SAAT`).
      Şarkı ↔ şarkı tabanı DEĞİŞMEDİ: `auto_process.MIN_YAYIN_ARALIGI_SN` (52 sa).
  R3a YouTube Shorts, uzun formatın PUBLIC anından 24 saat sonra
      (`YAYIN_RITMI_SHORTS_GECIKME_SAAT`, ana şalter `YAYIN_RITMI_SHORTS_GECIKMELI`).
  R3b Bir şarkı aynı TR takvim gününde en fazla 2 platformda
      (`YAYIN_RITMI_SARKI_GUNLUK_PLATFORM_TAVANI`). Geri doldurmalar, TikTok web planı,
      Instagram drain ve Telegram/Bluesky DAHİL.
  R2  (yalnız ÖLÇÜLÜR, bu aşamada kapı değil) aynı platformda iki farklı şarkının
      gönderisi arasında `YAYIN_RITMI_PLATFORM_MIN_ARA_SAAT`'ten kısa aralık. TikTok'ta
      zaten kapı var: `upload/tiktok_web._kural_ihlalleri` (`TIKTOK_KIT_ARALIK_SAAT`).

NEDEN TEK MODÜL: kurallar beş ayrı hatta (auto_process, dj_famous_process, iki geri
doldurma, Instagram drain, TikTok web planı) uygulanıyor. Her birinde ayrı sayaç
yazmak "unutulacak liste" olurdu; hepsi buradaki fonksiyonlara "şimdi olur mu" diye
sorar. Modül SALT OKUR: state yazmaz, ağa çıkmaz, config'e yazmaz.

Sayılar config'te; burada yalnız `getattr` varsayılanı var (config henüz güncellenmemiş
bir checkout'ta import zinciri kırılmasın). Shorts gecikmesinin varsayılanı KAPALI —
şalter config'te bilerek açılır (canlı yüklemelerin eski akışla bitmesi için).

ÜÇ SORU (CLAUDE.md):
  1. Kim çağırır: `auto_process._auto_pace_count` (R1 set tarafı),
     `auto_process._shorts_gecikmeli_supurge` + `process_project` Shorts dalı (R3a),
     `auto_process._ek_platformlari_isle` (Facebook), `dj_famous_process.process_set`
     (R1 + R3a), `upload/ek_platform_backfill.backfill`, `upload/facebook_backfill.backfill`,
     `upload/instagram_upload.try_publish_pending`, `upload/tiktok_web._kural_ihlalleri`
     (R3b); `ozgunluk_skoru` (ihlal sayımı).
  2. Hangi görevden: saatlik `auto_process.py` (finally süpürgeleri) ve haftalık
     `dj_famous_process.py`. Yeni görev yok.
  3. Çalışmadığını nasıl anlarız: her engel çağıranın log'una SEBEP metniyle düşer
     ("ritim: ..."); `python yayin_ritmi.py --json` son 7 günün ihlallerini listeler;
     koruma testleri `tests/test_yayin_ritmi.py` (5 Eylül fikstürü dahil).
"""

import argparse
import datetime
import json
import os
import sys
import time

import config

_KOK = os.path.dirname(os.path.abspath(__file__))
SAAT = 3600.0
GUN_SN = 24 * SAAT
TR = getattr(config, "TR_TZ", datetime.timezone(datetime.timedelta(hours=3)))

PLATFORMLAR = ("youtube", "youtube_shorts", "tiktok", "instagram", "facebook",
               "telegram", "bluesky")
# Ana katalog kökü; diğer TÜM kökler (uyumluluk.KOK_ADLARI: dj_sets, derlemeler ve
# ileride eklenecekler) "set" sayılır — kök listesi burada KOPYALANMIYOR.
SARKI_KOKU = "projects"
_SARKI_TABANI_VARSAYILAN_SN = 52 * SAAT


# --------------------------------------------------------------------------
# Ayarlar (config'ten; varsayılanlar yalnız import güvenliği için)
# --------------------------------------------------------------------------

def set_sarki_ara_sn() -> float:
    return float(getattr(config, "YAYIN_RITMI_SET_SARKI_ARA_SAAT", 48)) * SAAT


def shorts_gecikme_sn() -> float:
    return float(getattr(config, "YAYIN_RITMI_SHORTS_GECIKME_SAAT", 24)) * SAAT


def shorts_gecikmeli_mi() -> bool:
    """R3a ana şalteri. Varsayılan KAPALI: config açıkça True demeden eski akış sürer."""
    return bool(getattr(config, "YAYIN_RITMI_SHORTS_GECIKMELI", False))


def sarki_gunluk_platform_tavani() -> int:
    return int(getattr(config, "YAYIN_RITMI_SARKI_GUNLUK_PLATFORM_TAVANI", 2))


def platform_min_ara_sn() -> float:
    return float(getattr(config, "YAYIN_RITMI_PLATFORM_MIN_ARA_SAAT", 6)) * SAAT


def sarki_tabani_sn() -> float:
    """Şarkı ↔ şarkı tabanı: auto_process yüklüyse ORADAN (tek kaynak), değilse 52 sa.
    auto_process ağır bir import; bu modül onu kendisi yüklemez (turev_takvimi deseni)."""
    ap = sys.modules.get("auto_process")
    return float(getattr(ap, "MIN_YAYIN_ARALIGI_SN", _SARKI_TABANI_VARSAYILAN_SN))


# --------------------------------------------------------------------------
# Damga okuma
# --------------------------------------------------------------------------

def ts_oku(deger):
    """ISO damga → epoch saniye. Saat dilimsiz damga YEREL saattir (state'in
    `%Y-%m-%dT%H:%M:%S` biçimi); "...Z" ve "+03:00" desteklenir. Okunamazsa None."""
    if not isinstance(deger, str) or not deger.strip():
        return None
    try:
        an = datetime.datetime.fromisoformat(deger.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if an.tzinfo is None:
        try:
            return time.mktime(an.timetuple())
        except (OverflowError, ValueError):
            return None
    return an.timestamp()


def tr_gun(ts):
    return datetime.datetime.fromtimestamp(ts, TR).date()


def _iso(ts):
    return datetime.datetime.fromtimestamp(ts, TR).isoformat(timespec="minutes")


def uzun_yayin_ani(st):
    """Uzun formatın izleyiciye çıktığı an = max(yükleme, publish_at).

    `auto_process._son_yeni_yayin_ani` ile AYNI tanım (tempo dışı public anı SAYILMAZ)."""
    st = st or {}
    if not st.get("youtube_video_id"):
        return None
    adaylar = [ts_oku(st.get("youtube_uploaded_at")), ts_oku(st.get("youtube_publish_at"))]
    adaylar = [a for a in adaylar if a is not None]
    return max(adaylar) if adaylar else None


def platform_anlari(st) -> dict:
    """{platform: [ts, ...]} — bir şarkının kamuya açık (ya da zamanlanmış) gönderi anları.

    Kaynaklar bilinçli: YouTube/Shorts için public anı (publish_at yoksa yükleme);
    TikTok için web planı ve elle/Telegram onayı (`PUBLISH_COMPLETE` API TESPİT anı
    gerçek yayın anı DEĞİL, CLAUDE.md (e) — sayılmaz); Facebook için zamanlanan an."""
    st = st or {}
    anlar = {p: [] for p in PLATFORMLAR}

    def ekle(platform, deger):
        ts = ts_oku(deger)
        if ts is not None:
            anlar[platform].append(ts)

    if st.get("youtube_video_id"):
        ekle("youtube", st.get("youtube_publish_at") or st.get("youtube_uploaded_at"))
        ekle("youtube", st.get("youtube_public_ani_tempo_disi"))
    if st.get("youtube_shorts_video_id"):
        ekle("youtube_shorts", st.get("youtube_shorts_publish_at")
             or st.get("youtube_shorts_uploaded_at"))
    web = st.get("tiktok_web")
    if isinstance(web, dict) and web.get("durum") in ("planlandi", "yayinlandi"):
        ekle("tiktok", web.get("yayinlandi_at") if web.get("durum") == "yayinlandi"
             and web.get("yayinlandi_at") else web.get("planlanan_an"))
    elif st.get("tiktok_published_at") and "PUBLISH_COMPLETE" not in str(
            st.get("tiktok_published_kaynak") or ""):
        ekle("tiktok", st.get("tiktok_published_at"))
    ekle("instagram", st.get("instagram_uploaded_at") if st.get("instagram_media_id") else None)
    if st.get("facebook_reels_id") or st.get("facebook_video_id"):
        ekle("facebook", st.get("facebook_scheduled_for") or st.get("facebook_uploaded_at"))
    ekle("telegram", st.get("telegram_uploaded_at"))
    ekle("telegram", st.get("telegram_shorts_uploaded_at"))
    ekle("bluesky", st.get("bluesky_uploaded_at"))
    return {p: sorted(v) for p, v in anlar.items() if v}


def gun_platformlari(st, an, haric=None) -> set:
    gun = tr_gun(an)
    return {p for p, liste in platform_anlari(st).items()
            if p != haric and any(tr_gun(ts) == gun for ts in liste)}


# --------------------------------------------------------------------------
# Kapılar
# --------------------------------------------------------------------------

def platform_gun_izni(st, platform, an=None):
    """(izin, sebep) — R3b. `an` gönderinin izleyiciye çıkacağı an (varsayılan şimdi).

    Aynı platformun aynı gündeki ikinci kaydı (ör. Telegram Shorts) yeni platform
    SAYILMAZ. Tavan <= 0 kuralı kapatır."""
    tavan = sarki_gunluk_platform_tavani()
    if tavan <= 0:
        return True, ""
    an = time.time() if an is None else an
    diger = gun_platformlari(st, an, haric=platform)
    if len(diger) >= tavan:
        return False, ("ritim: şarkı %s günü zaten %d platformda (%s) — günlük tavan %d"
                       % (tr_gun(an).isoformat(), len(diger), ", ".join(sorted(diger)), tavan))
    return True, ""


def shorts_zamani(st, simdi=None):
    """(hazir, kalan_sn, sebep) — R3a. Şalter kapalıysa her zaman hazır."""
    if not shorts_gecikmeli_mi():
        return True, 0.0, ""
    st = st or {}
    simdi = time.time() if simdi is None else simdi
    t0 = uzun_yayin_ani(st)
    if t0 is None:
        return False, None, "ritim: uzun formatın yayın anı bilinmiyor — Shorts bekliyor"
    kalan = t0 + shorts_gecikme_sn() - simdi
    if kalan > 0:
        return False, kalan, ("ritim: Shorts uzun formattan %g sa sonra (%s), %.1f sa kaldı"
                              % (shorts_gecikme_sn() / SAAT, _iso(t0 + shorts_gecikme_sn()),
                                 kalan / SAAT))
    return True, 0.0, ""


def kok_turu(proje) -> str:
    kok = os.path.basename(os.path.dirname(os.path.abspath(proje)))
    return "sarki" if kok == SARKI_KOKU else "set"


def _klasorler(klasorler=None):
    """Katalog klasörleri. Test sırasında GERÇEK kökler OKUNMAZ (turev_takvimi /
    kanal_kayitlari deseni): canlı state'ler test sonuçlarına sızmasın — testler
    `uyumluluk.KOKLER`i tmp'ye çeker ya da `klasorler` verir."""
    if klasorler is not None:
        return list(klasorler)
    import uyumluluk
    if os.environ.get("PYTEST_CURRENT_TEST"):
        gercek = {os.path.normcase(os.path.abspath(os.path.join(_KOK, k)))
                  for k in uyumluluk.KOK_ADLARI}
        if any(os.path.normcase(os.path.abspath(k)) in gercek for k in uyumluluk.KOKLER):
            return []
    return list(uyumluluk.proje_klasorleri())


def _durum_oku(proje):
    yol = os.path.join(proje, "state.json")
    if not os.path.isfile(yol):
        return {}
    try:
        with open(yol, "r", encoding="utf-8") as f:
            v = json.load(f)
        return v if isinstance(v, dict) else None
    except (OSError, ValueError):
        return None


def kanal_tabani(proje, simdi=None, klasorler=None, tur=None):
    """(izin, kalan_sn, sebep) — R1, kanal geneli yeni yayın tabanı (set/derleme tarafı).

    tur "set": başka HERHANGİ bir projenin (şarkı, set, derleme) uzun yayınından 48 sa.
    tur "sarki": yalnız set/derleme uzun yayınından 48 sa (şarkı ↔ şarkı 52 sa tabanı
    auto_process'te, burada tekrar SAYILMAZ). Gelecekteki (zamanlanmış) yayın anı da
    sayılır. Okunamayan state atlanır (tempo kuralı, geri alınamaz bir yayın kapısı değil;
    telif/kopya kapısı `uyumluluk`'ta fail-closed kalır)."""
    simdi = time.time() if simdi is None else simdi
    tur = tur or kok_turu(proje)
    ara = set_sarki_ara_sn()
    ben = os.path.normcase(os.path.abspath(proje))
    en_kalan, engel = 0.0, None
    for p in _klasorler(klasorler):
        if os.path.normcase(os.path.abspath(p)) == ben:
            continue
        if tur == "sarki" and kok_turu(p) != "set":
            continue
        st = _durum_oku(p)
        if not st:
            continue
        t = uzun_yayin_ani(st)
        if t is None:
            continue
        kalan = t + ara - simdi
        if kalan > en_kalan:
            en_kalan, engel = kalan, (os.path.basename(os.path.normpath(p)), t)
    if engel is None:
        return True, 0.0, ""
    return False, en_kalan, ("ritim: set/derleme ↔ şarkı ortak tabanı %g sa (son: %s %s), "
                             "%.1f sa kaldı" % (ara / SAAT, engel[0], _iso(engel[1]),
                                                en_kalan / SAAT))


# --------------------------------------------------------------------------
# Olay listesi, ihlal taraması ve aday değerlendirme (skor + fikstür)
# --------------------------------------------------------------------------

def olay(ts, proje, platform, tur="sarki"):
    return {"ts": float(ts), "proje": proje, "platform": platform, "tur": tur}


def olaylar(klasorler=None) -> list:
    """Tüm katalogun gönderi olayları (zamana göre sıralı)."""
    liste = []
    for p in _klasorler(klasorler):
        st = _durum_oku(p)
        if not st:
            continue
        ad = os.path.basename(os.path.normpath(p))
        for platform, anlar in platform_anlari(st).items():
            for ts in anlar:
                liste.append(olay(ts, ad, platform, kok_turu(p)))
    return sorted(liste, key=lambda o: (o["ts"], o["proje"], o["platform"]))


def aday_ihlalleri(gecmis, aday) -> list:
    """Kabul edilmiş `gecmis` olaylarına `aday` eklenirse KAPI kurallarından hangileri
    çiğnenir (boş = kabul). R2 burada YOK (bu aşamada kapı değil) — TikTok'un kendi
    aralık kapısı hariç, çünkü o zaten canlıda (`tiktok_web._kural_ihlalleri`)."""
    ihlal = []
    t, proje, platform = aday["ts"], aday["proje"], aday["platform"]
    if platform != "youtube" and not any(
            o["proje"] == proje and o["platform"] == "youtube" and o["ts"] <= t for o in gecmis):
        # Ön koşul (bugünkü hatlarda zaten var: Instagram/Facebook ana hatta YouTube'dan
        # sonra, geri doldurmalar public anı kapısıyla, TikTok web planı T0 sonrası).
        ihlal.append("ön koşul: uzun format henüz yayında değil")
    if platform == "youtube":
        for o in gecmis:
            if o["platform"] != "youtube" or o["proje"] == proje:
                continue
            if aday["tur"] == "sarki" and o["tur"] == "sarki":
                ara, kural = sarki_tabani_sn(), "R1 şarkı tabanı"
            else:
                ara, kural = set_sarki_ara_sn(), "R1 set/şarkı tabanı"
            if abs(t - o["ts"]) < ara:
                ihlal.append("%s (%s, %.1f sa)" % (kural, o["proje"], abs(t - o["ts"]) / SAAT))
                break
    if platform == "youtube_shorts" and shorts_gecikmeli_mi():
        uzun = [o["ts"] for o in gecmis if o["proje"] == proje and o["platform"] == "youtube"]
        if not uzun:
            ihlal.append("R3a Shorts uzun formattan önce")
        elif t < min(uzun) + shorts_gecikme_sn():
            ihlal.append("R3a Shorts uzun formattan %g sa geçmeden" % (shorts_gecikme_sn() / SAAT))
    tavan = sarki_gunluk_platform_tavani()
    if tavan > 0:
        gun = tr_gun(t)
        diger = {o["platform"] for o in gecmis if o["proje"] == proje
                 and o["platform"] != platform and tr_gun(o["ts"]) == gun}
        if len(diger) >= tavan:
            ihlal.append("R3b şarkı aynı gün %d platformda" % len(diger))
    if platform == "tiktok":
        aralik = float(getattr(config, "TIKTOK_KIT_ARALIK_SAAT", 36)) * SAAT
        if any(o["platform"] == "tiktok" and abs(t - o["ts"]) < aralik for o in gecmis):
            ihlal.append("TikTok iki gönderi arası %g sa" % (aralik / SAAT))
    return ihlal


def ihlaller(liste, bas=None, bit=None) -> list:
    """Gerçekleşmiş olaylarda kural ihlalleri (ölçüm). Her ihlal ikinci olayın anına
    yazılır; [bas, bit) aralığı verilirse yalnız o aralıktakiler döner.

    Sayılanlar: R1 (şarkı↔şarkı 52 sa, set↔her şey 48 sa), R2 (aynı platform, farklı
    şarkı, < min ara), R3a (Shorts < uzun + 24 sa; şalter kapalıyken de ÖLÇÜLÜR —
    ölçüm, kapının açık olup olmamasından bağımsız), R3b (şarkı günü > tavan platform)."""
    sonuc = []
    liste = sorted(liste, key=lambda o: o["ts"])
    uzunlar = [o for o in liste if o["platform"] == "youtube"]
    for i, o in enumerate(uzunlar):
        for onceki in uzunlar[:i]:
            if onceki["proje"] == o["proje"]:
                continue
            ara = (sarki_tabani_sn() if o["tur"] == "sarki" and onceki["tur"] == "sarki"
                   else set_sarki_ara_sn())
            if o["ts"] - onceki["ts"] < ara:
                sonuc.append({"kural": "R1", "ts": o["ts"], "proje": o["proje"],
                              "aciklama": "%s ← %s %.1f sa" % (o["proje"], onceki["proje"],
                                                              (o["ts"] - onceki["ts"]) / SAAT)})
                break
    min_ara = platform_min_ara_sn()
    for platform in PLATFORMLAR:
        pl = [o for o in liste if o["platform"] == platform]
        for i in range(1, len(pl)):
            if pl[i]["proje"] != pl[i - 1]["proje"] and pl[i]["ts"] - pl[i - 1]["ts"] < min_ara:
                sonuc.append({"kural": "R2", "ts": pl[i]["ts"], "proje": pl[i]["proje"],
                              "aciklama": "%s: %s ← %s %.0f dk" % (
                                  platform, pl[i]["proje"], pl[i - 1]["proje"],
                                  (pl[i]["ts"] - pl[i - 1]["ts"]) / 60)})
    for o in liste:
        if o["platform"] != "youtube_shorts":
            continue
        uzun = [u["ts"] for u in uzunlar if u["proje"] == o["proje"]]
        if uzun and o["ts"] - min(uzun) < shorts_gecikme_sn():
            sonuc.append({"kural": "R3a", "ts": o["ts"], "proje": o["proje"],
                          "aciklama": "Shorts uzun formattan %.1f sa sonra"
                                      % ((o["ts"] - min(uzun)) / SAAT)})
    tavan = sarki_gunluk_platform_tavani()
    if tavan > 0:
        gunler = {}
        for o in liste:
            gunler.setdefault((o["proje"], tr_gun(o["ts"])), []).append(o)
        for (proje, gun), ol in sorted(gunler.items(), key=lambda kv: min(x["ts"] for x in kv[1])):
            platformlar = sorted({x["platform"] for x in ol})
            if len(platformlar) > tavan:
                sonuc.append({"kural": "R3b", "ts": max(x["ts"] for x in ol), "proje": proje,
                              "aciklama": "%s %s: %d platform (%s)" % (
                                  proje, gun.isoformat(), len(platformlar),
                                  ", ".join(platformlar))})
    if bas is not None:
        sonuc = [s for s in sonuc if s["ts"] >= bas]
    if bit is not None:
        sonuc = [s for s in sonuc if s["ts"] < bit]
    return sorted(sonuc, key=lambda s: s["ts"])


def main(argv=None):
    ap = argparse.ArgumentParser(description="Yayın ritmi ihlalleri (salt okur).")
    ap.add_argument("--gun", type=float, default=7.0)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    simdi = time.time()
    liste = ihlaller(olaylar(), bas=simdi - args.gun * GUN_SN, bit=simdi + 1)
    veri = {"gun": args.gun, "ihlal_sayisi": len(liste),
            "ihlaller": [dict(s, an=_iso(s["ts"])) for s in liste]}
    if args.json:
        sys.stdout.buffer.write((json.dumps(veri, ensure_ascii=False, indent=2) + "\n")
                                .encode("utf-8"))
    else:
        for s in veri["ihlaller"]:
            print("%s %s %s" % (s["an"], s["kural"], s["aciklama"]))
        print("toplam: %d ihlal (son %g gün)" % (len(liste), args.gun))
    return 0


if __name__ == "__main__":
    sys.exit(main())
