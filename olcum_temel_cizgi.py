# -*- coding: utf-8 -*-
"""Kanal ölçüm penceresi — SALT OKUMA çekim + karşılaştırma aracı.

===========================================================================
NE ZAMAN ÇALIŞTIRILACAK:  **2026-10-09**  (ve sonra 2026-10-23 … 2026-11-06)
===========================================================================

    python olcum_temel_cizgi.py --dry-run      # önce bunu: hiç API çağırmaz
    python olcum_temel_cizgi.py --cek          # gerçek ölçüm -> olcum_2026-10-09.json
    python olcum_temel_cizgi.py --karsilastir  # temel çizgi ile farkı raporlar

NEYLE KARŞILAŞTIRILACAK: repo kökündeki `olcum_temel_cizgi.json` — 2026-09-11'de
alınmış TEMEL ÇİZGİ. Bu script onun ÜSTÜNE HİÇBİR KOŞULDA YAZMAZ (bkz.
`_cikti_yolu` içindeki muhafız); her çekim tarihli ayrı bir dosyaya gider.

NEDEN BU ÖLÇÜM KAYBEDİLEMEZ (bu dosyanın var olma sebebi):
    2026-09-11'de kanalın **40 kapağının tamamı** değiştirildi (başlık puntosu 2x,
    logo kontrastı artırıldı) ve AYNI GÜN video açılışları da değişti. Bu iki
    değişikliğin işe yarayıp yaramadığının **tek kanıtı**, temel çizgiyle bu
    ölçümün karşılaştırılması. Ölçüm yapılmazsa 11 Eylül'de yapılan işin tamamı
    ölçülemez hâle gelir — "iyileşti mi" sorusu bir daha asla cevaplanamaz.

    Bu aracın kendisi de tam bu yüzden repoda: ölçümü üreten scriptler
    (`temel_cizgi.py` + `zenginlestir.py`) 2026-09-11'de scratchpad'de kalmıştı.
    Scratchpad oturuma özeldir ve silinir — yani bir ay sonraki randevu, o gün
    var olmayacak bir araca bağlanmıştı. Bu deponun EN SIK hatası (yazıldı ama
    hiçbir yerden çağrılmıyor / çalışacağı an mevcut olmuyor) geleceğe kurulmuş
    hâliydi. Bu dosya o bağı kalıcı hâle getiriyor.

BİRİNCİL METRİK: `audienceWatchRatio`'nun **%2 ve %3** noktaları.
    Temel çizgi (7 gerçek uzun video ortalaması): **%2 ≈ 0,837 · %3 ≈ 0,715**
    `Küllerimden Geç` ORTALAMAYA KATILMIYOR: `Yeniden Doğacağım` ile aynı ses,
    aynı sözler, aynı md5 — kopya. (Tam da bu kopya çift gürültü tabanını
    veriyor: %3 noktasında 0,679 vs 0,891, yani **21,2 puan fark, içerik farkı
    sıfır**. Bu ölçekte 20 puanın altındaki tek-video farkları hiçbir şey
    anlatmıyor; karşılaştırma modunun sonunda bu uyarı tekrar basılıyor.)

ELLE YAPILACAK TEK EK ADIM (API'den ALINAMIYOR): tıklanma oranı. YouTube
    Analytics API v2 `impressions` / `impressionClickThroughRate` metriklerini
    TANIMIYOR (HTTP 400 "Unknown identifier" — izin sorunu değil, metrik API'nin
    sözlüğünde yok). Studio > Analizler > Erişim ekranında tarih aralığını ÖNCE
    2026-08-14..2026-09-10, SONRA 2026-09-12..2026-10-09 seçip "Gösterimler" ve
    "Gösterimlerin tıklanma oranı" sütunlarını CSV dışa aktar. Video ÖMRÜ BOYUNCA
    (lifetime) değerini KULLANMA — yeni kapak eski dönemi de kirletir.

KOTA VE GÜVENLİK: salt okuma. Hiçbir yükleme, hiçbir bildirim, hiçbir state.json
    yazımı yok. Analytics API, Data API'den AYRI kotada — ama yine de `--cek`
    tek koşuda ~40 sorgu yapıyor; gereksiz tekrar çalıştırma. `--dry-run` hiç
    ağa çıkmaz ve hiçbir dosya yazmaz, önce onunla doğrula.

`upload/analytics_token.json` gerekiyor (ayrı token — NEDEN ayrı olduğu
    `upload/youtube_analytics.py` docstring'inde: yükleme token'ına
    `yt-analytics.readonly` eklemek o token'ı geçersiz kılar ve SAATLİK YÜKLEME
    HATTINI DURDURUR). Token yoksa: `python upload/youtube_analytics.py --auth`.
"""

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "upload"))

# Windows konsolu cp1252 — Türkçe karakterler yazdırılırken çökmesin.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

# Kök listesi TEK kanonik kaynaktan (uyumluluk.KOKLER, mutlak yollar). Kendi
# kopyasını tutmak, dördüncü bir kök açıldığında elle güncellenmesi gereken
# yerlerden biri olmak demek — `derlemeler/` eklendiğinde tam bu sınıf hata
# oluşmuştu. Muhafız: tests/test_kok_listesi_muhafizi.py
from uyumluluk import KOKLER  # noqa: E402

TEMEL_CIZGI_PATH = os.path.join(BASE_DIR, "olcum_temel_cizgi.json")

# --- temel çizgi sabitleri (devir belgesi §3.1 / §4.1) -----------------------
KUCUK_RESIM_DEGISIKLIGI = "2026-09-11"
OLCUM_RANDEVUSU = "2026-10-09"
# Kopya çift: aynı ses/söz/md5 iki ayrı video olarak yüklendi. Ortalamaya
# katılırsa hem temel çizgiyi hem yeni ölçümü yukarı çeker ve karşılaştırmayı
# bozar — devir belgesinde de "kopya, sayma" diye işaretli.
KOPYA_PROJELER = ("Küllerimden Geç",)
TEMEL_TUTMA_ORTALAMASI = {"0.02": 0.837, "0.03": 0.715}
GURULTU_TABANI_PUAN = 21.2  # aynı dosyanın iki kopyası arasındaki %3 farkı

# Temel çizgideki metrik dizeleri BİREBİR korunuyor: sütun kümesi değişirse
# karşılaştırma sessizce yanlış olur (eksik metrik "0" gibi okunur).
METRIKLER = ("views,estimatedMinutesWatched,averageViewDuration,"
             "averageViewPercentage,subscribersGained,subscribersLost,"
             "likes,comments,shares")
# zenginlestir.py'nin kullandığı kısa küme (subscribersLost YOK, sıra farklı).
# Aynen bırakıldı — temel çizgideki `icerik_tipi_*` / `ulke_28gun` bölümleri bu
# kümeyle üretildi.
METRIKLER_KISA = ("views,estimatedMinutesWatched,averageViewDuration,"
                  "averageViewPercentage,subscribersGained,likes,shares,comments")

# Temel çizgide bulunan 14 veri bölümü (meta alanlar hariç). Karşılaştırma modu
# bu listeyi bir kontrol listesi gibi kullanıyor: yeni ölçümde eksik/hatalı olan
# bölüm SESSİZCE atlanmasın, raporda "EKSİK" diye görünsün.
BOLUMLER = (
    "gosterim_ctr_durumu", "kanal_28gun", "kanal_7gun",
    "trafik_kaynaklari_28gun", "video_meta", "pencere_28gun", "pencere_7gun",
    "icerik_tipi_28gun", "icerik_tipi_7gun", "gunluk_kanal_28gun",
    "ulke_28gun", "arama_terimleri_28gun", "kart_ve_playlist_28gun",
    "kitle_tutma_28gun",
)

_SORGULAR = []   # --dry-run raporu için: yapılacak sorguların dökümü


# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------
def _json_oku(yol):
    with open(yol, "r", encoding="utf-8") as f:
        return json.load(f)


def _video_haritasi():
    """{video_id: {kok, proje, tip, ...}} — state.json'lardan, AĞA ÇIKMADAN.

    Uzun format VE Shorts birlikte: temel çizgi ikisini de içeriyor ve
    `icerik_tipi_*` karşılaştırması ancak ikisi de varken anlamlı.
    """
    harita = {}
    for kok in KOKLER:
        if not os.path.isdir(kok):
            continue
        kok_adi = os.path.basename(kok)
        for ad in sorted(os.listdir(kok)):
            sp = os.path.join(kok, ad, "state.json")
            if not os.path.isfile(sp):
                continue
            try:
                st = _json_oku(sp)
            except (OSError, ValueError):
                continue      # yarım/bozuk state.json ölçümü durdurmasın
            for vid_key, tip, up_key, pub_key, priv_key, izl_key in (
                ("youtube_video_id", "uzun", "youtube_uploaded_at",
                 "youtube_publish_at", "youtube_privacy", "youtube_views"),
                ("youtube_shorts_video_id", "shorts", "youtube_shorts_uploaded_at",
                 "youtube_shorts_publish_at", "youtube_shorts_privacy",
                 "youtube_shorts_views"),
            ):
                v = st.get(vid_key)
                if v:
                    harita[v] = {
                        "kok": kok_adi, "proje": ad, "tip": tip,
                        "yuklendi": st.get(up_key),
                        "publishAt": st.get(pub_key),
                        "gorunurluk": st.get(priv_key),
                        "state_izlenme": st.get(izl_key),
                        "playlist": st.get("youtube_playlist_id"),
                    }
    return harita


class Cekici:
    """Analytics sorgularını çalıştırır. `kuru=True` ise HİÇ ağa çıkmaz."""

    def __init__(self, kuru=False):
        self.kuru = kuru
        self.servis = None
        if not kuru:
            from youtube_analytics import get_service
            self.servis = get_service()
            if self.servis is None:
                raise SystemExit(
                    "upload/analytics_token.json yok ya da geçersiz.\n"
                    "Önce: python upload/youtube_analytics.py --auth")

    def q(self, etiket, **kw):
        """Tek sorgu -> satır listesi. Hata sözlük olarak KAYDEDİLİR, yutulmaz.

        NEDEN hatayı kaydediyoruz: temel çizgide `arama_terimleri_28gun` tam da
        böyle bir hatayla boş kaldı. Hatanın metnini dosyaya yazmak, bir ay
        sonra "veri mi yoktu, sorgu mu patladı" sorusunu cevaplıyor.
        """
        _SORGULAR.append((etiket, kw.get("dimensions", "-"),
                          kw.get("metrics", "-")[:60]))
        if self.kuru:
            return {"_dry_run": etiket}
        try:
            r = self.servis.reports().query(ids="channel==MINE", **kw).execute()
        except Exception as e:                      # noqa: BLE001 — API her tür hatayı atabiliyor
            msg = str(e)
            i = msg.find('returned "')
            return {"hata": msg[i + 10:i + 300] if i > 0 else msg[:300]}
        kolonlar = [c["name"] for c in r.get("columnHeaders", [])]
        return [dict(zip(kolonlar, satir)) for satir in (r.get("rows", []) or [])]


def _tek(sonuc, varsayilan=None):
    """Tek satırlık sorgu sonucunu sözlüğe indirger (hata sözlüğünü korur)."""
    if isinstance(sonuc, list):
        return sonuc[0] if sonuc else (varsayilan if varsayilan is not None else {})
    return sonuc


# ---------------------------------------------------------------------------
# ÇEKİM — temel çizgideki 14 bölümün AYNISI
# ---------------------------------------------------------------------------
def cek(kuru=False, bugun=None):
    bugun = bugun or date.today()
    son = bugun.isoformat()
    c = Cekici(kuru=kuru)
    harita = _video_haritasi()

    def bas(gun):
        return (bugun - timedelta(days=gun)).isoformat()

    def kanal(gun):
        return _tek(c.q("kanal_%dgun" % gun, startDate=bas(gun), endDate=son,
                        metrics=METRIKLER))

    def pencere(gun):
        """Video bazında metrikler. 200'lük öbekler: filtre uzunluğu sınırlı."""
        out = {}
        idler = list(harita)
        for i in range(0, len(idler), 200):
            obek = idler[i:i + 200]
            r = c.q("pencere_%dgun[%d]" % (gun, i // 200), startDate=bas(gun),
                    endDate=son, metrics=METRIKLER, dimensions="video",
                    filters="video==%s" % ",".join(obek), maxResults=200)
            if isinstance(r, dict):
                out["_hata"] = r.get("hata", r)
                continue
            for d in r:
                d = dict(d)
                out[d.pop("video")] = d
        return {"baslangic": bas(gun), "bitis": son, "gun": gun, "video": out}

    def trafik(gun):
        out = {}
        for dim in ("insightTrafficSourceType", "deviceType", "subscribedStatus"):
            out[dim] = c.q("trafik/%s" % dim, startDate=bas(gun), endDate=son,
                           metrics="views,estimatedMinutesWatched",
                           dimensions=dim, sort="-views")
        return out

    sonuc = {
        "alindi": datetime.now().isoformat(timespec="seconds"),
        "olcum_turu": "takip",       # temel çizgide bu alan yok; onu ayırt eder
        "not": ("Takip ölçümü. Karşılaştırma tabanı: olcum_temel_cizgi.json "
                "(2026-09-11, kapak+açılış değişikliğinden ÖNCEKİ dönem). "
                "Birincil metrik: audienceWatchRatio %%2 ve %%3 noktaları."),
        "kucuk_resim_degisikligi_tarihi": KUCUK_RESIM_DEGISIKLIGI,
        "gosterim_ctr_durumu": None,
        "kanal_28gun": kanal(28),
        "kanal_7gun": kanal(7),
        "trafik_kaynaklari_28gun": trafik(28),
        "video_meta": harita,
        "pencere_28gun": pencere(28),
        "pencere_7gun": pencere(7),
    }

    for gun in (28, 7):
        sonuc["icerik_tipi_%dgun" % gun] = c.q(
            "icerik_tipi_%dgun" % gun, startDate=bas(gun), endDate=son,
            metrics=METRIKLER_KISA, dimensions="creatorContentType")

    sonuc["gunluk_kanal_28gun"] = c.q(
        "gunluk_kanal_28gun", startDate=bas(28), endDate=son,
        metrics="views,estimatedMinutesWatched,subscribersGained,likes",
        dimensions="day")
    sonuc["ulke_28gun"] = c.q("ulke_28gun", startDate=bas(28), endDate=son,
                              metrics=METRIKLER_KISA, dimensions="country")
    # maxResults BİLEREK YOK: temel çizgide bu sorgu `maxResults=30` yüzünden
    # HTTP hatasıyla boş döndü (FIELD_UNKNOWN_VALUE / max-results). Bölüm aynı
    # bölüm, sadece patlayan parametre çıkarıldı — 2026-10-09'da veri gelsin.
    sonuc["arama_terimleri_28gun"] = c.q(
        "arama_terimleri_28gun", startDate=bas(28), endDate=son, metrics="views",
        dimensions="insightTrafficSourceDetail",
        filters="insightTrafficSourceType==YT_SEARCH", sort="-views")

    sonuc["kart_ve_playlist_28gun"] = {}
    for m in ("cardImpressions", "cardClicks", "annotationImpressions",
              "annotationClicks", "videosAddedToPlaylists", "playlistStarts",
              "viewsPerPlaylistStart", "averageTimeInPlaylist"):
        r = c.q("kart/%s" % m, startDate=bas(28), endDate=son, metrics=m)
        sonuc["kart_ve_playlist_28gun"][m] = r[0][m] if isinstance(r, list) and r else r

    sonuc["kitle_tutma_28gun"] = _kitle_tutma(c, harita, sonuc["pencere_28gun"],
                                              bas(28), son, kuru)
    sonuc["gosterim_ctr_durumu"] = _gosterim_ctr(c, bas(28), son)
    sonuc["veri_gecikmesi_notu"] = (
        "YouTube Analytics günlük verisi 2-3 gün gecikmeli işliyor: bu çekimin "
        "son DOLU günü bugünden 2-3 gün öncesi. 28 günlük pencere "
        "%s ile başlıyor, yani kapak değişikliğinden (%s) SONRAKİ dönemi "
        "kapsaması için ölçüm en erken %s'da alınmalı."
        % (bas(28), KUCUK_RESIM_DEGISIKLIGI, OLCUM_RANDEVUSU))
    return sonuc


def _kitle_tutma(c, harita, pencere28, baslangic, son, kuru):
    """BİRİNCİL METRİK: en çok izlenen 8 uzun videonun tutma eğrisi.

    audienceType==ORGANIC: reklam/keşfet dışı organik izleyici. Temel çizgi de
    böyle alındı; filtreyi değiştirmek karşılaştırmayı geçersiz kılar.
    """
    p28 = pencere28.get("video", {})
    uz = sorted([(v, p28.get(v, {}).get("views", 0) or 0)
                 for v, m in harita.items() if m["tip"] == "uzun"],
                key=lambda x: -x[1])[:8]
    if kuru and not any(n for _, n in uz):
        # --dry-run'da izlenme verisi yok (sorgu çalışmadı), sıralama anlamsız.
        # Sorgu SAYISI gerçekçi kalsın diye ilk 8 uzun video alınıyor.
        uz = [(v, 0) for v, m in harita.items() if m["tip"] == "uzun"][:8]

    tut = {}
    for vid, _ in uz:
        r = c.q("kitle_tutma/%s" % vid, startDate=baslangic, endDate=son,
                metrics="audienceWatchRatio", dimensions="elapsedVideoTimeRatio",
                filters="video==%s;audienceType==ORGANIC" % vid)
        if not (isinstance(r, list) and r):
            continue
        tut[vid] = {
            "proje": harita[vid]["proje"],
            # egri: ilk %10, yüzde yüzde (asıl sızıntı ilk saniyelerde)
            "egri": {str(round(x["elapsedVideoTimeRatio"], 2)):
                     round(x["audienceWatchRatio"], 3) for x in r
                     if abs((x["elapsedVideoTimeRatio"] * 100) % 1) < 1e-6
                     and x["elapsedVideoTimeRatio"] <= 0.10},
            # onluk: tüm video, onda birlik adımlarla
            "onluk": {str(round(x["elapsedVideoTimeRatio"], 2)):
                      round(x["audienceWatchRatio"], 3) for x in r
                      if abs((x["elapsedVideoTimeRatio"] * 100) % 10) < 1e-6},
        }
    return tut


def _gosterim_ctr(c, baslangic, son):
    """Gösterim/CTR metriklerini DENER ve sonucu kayda geçirir.

    NEDEN her seferinde tekrar deniyoruz: bugün API bu metrikleri tanımıyor,
    ama tanımaya başlarsa bunu ancak deneyerek öğreniriz. Dört metriğin dördü
    de HTTP 400 dönüyor; maliyeti ihmal edilebilir.
    """
    deneme = {}
    for m in ("impressions", "impressionClickThroughRate", "videoImpressions",
              "thumbnailImpressions"):
        r = c.q("ctr_denemesi/%s" % m, startDate=baslangic, endDate=son, metrics=m)
        deneme[m] = "OK" if isinstance(r, list) else str(r.get("hata", r))[:120]
    return {
        "cekilebildi_mi": all(v == "OK" for v in deneme.values()),
        "denenen_metrikler": deneme,
        "aciklama": ("YouTube Analytics API v2 'impressions' ve "
                     "'impressionClickThroughRate' metriklerini TANIMIYOR -> "
                     "HTTP 400 'Unknown identifier'. İzin/scope sorunu DEĞİL "
                     "(aynı token ile views/estimatedMinutesWatched sorunsuz "
                     "geliyor); metrik API'nin sözlüğünde hiç yok."),
        "ne_yapmali": ("Tıklanma oranı yalnızca YouTube Studio > Analizler > "
                       "Erişim ekranından, TARİH ARALIĞI seçilerek okunur. "
                       "Karşılaştırma için: 2026-08-14..2026-09-10 (öncesi) ve "
                       "2026-09-12..%s (sonrası). Video ÖMRÜ BOYUNCA değerini "
                       "KULLANMA — yeni kapak eski dönemi de kirletir."
                       % OLCUM_RANDEVUSU),
    }


# ---------------------------------------------------------------------------
# ÇIKTI — temel çizginin üstüne YAZMAYAN yazıcı
# ---------------------------------------------------------------------------
def _cikti_yolu(istenen=None, bugun=None):
    yol = istenen or os.path.join(
        BASE_DIR, "olcum_%s.json" % (bugun or date.today()).isoformat())
    yol = os.path.abspath(yol)
    # MUHAFIZ: temel çizgi kaybedilemez. Bir yazım hedefi olarak bile kabul
    # edilmiyor — `--cikti` ile elle verilse bile burada duruyor.
    if yol == os.path.abspath(TEMEL_CIZGI_PATH):
        raise SystemExit(
            "REDDEDİLDİ: olcum_temel_cizgi.json TEMEL ÇİZGİ, üstüne yazılamaz.\n"
            "Ölçümler tarihli dosyalara yazılır (olcum_YYYY-AA-GG.json).")
    return yol


def yaz(sonuc, istenen=None, zorla=False, bugun=None):
    yol = _cikti_yolu(istenen, bugun)
    if os.path.exists(yol) and not zorla:
        raise SystemExit("Zaten var: %s  (üstüne yazmak için --zorla)" % yol)
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(sonuc, f, ensure_ascii=False, indent=2)
    return yol


def _son_olcum_yolu():
    """En yeni tarihli ölçüm dosyası (temel çizgi HARİÇ)."""
    adaylar = sorted(a for a in os.listdir(BASE_DIR)
                     if a.startswith("olcum_") and a.endswith(".json")
                     and a != os.path.basename(TEMEL_CIZGI_PATH))
    return os.path.join(BASE_DIR, adaylar[-1]) if adaylar else None


# ---------------------------------------------------------------------------
# KARŞILAŞTIRMA
# ---------------------------------------------------------------------------
def _tutma_noktalari(veri, nokta):
    """{proje: oran} — kopya video ORTALAMAYA katılmadan işaretlenir."""
    out = {}
    for vid, b in (veri.get("kitle_tutma_28gun") or {}).items():
        egri = b.get("egri") or {}
        if nokta in egri:
            out[b.get("proje", vid)] = egri[nokta]
    return out


def _ortalama(degerler):
    degerler = [d for d in degerler if isinstance(d, (int, float))]
    return round(sum(degerler) / len(degerler), 3) if degerler else None


def karsilastir(eski, yeni):
    """İki ölçümü karşılaştırır, sözlük döner (yazdırma `_bas_karsilastirma`)."""
    rapor = {"eski_alindi": eski.get("alindi"), "yeni_alindi": yeni.get("alindi"),
             "bolum_durumu": {}, "birincil": {}, "ikincil": {},
             "icerik_tipi": {}, "kart_ve_playlist": {}, "trafik": {}}

    # 1) 14 bölümün ikisinde de var olup olmadığı — sessiz eksik OLMASIN
    for b in BOLUMLER:
        def _durum(d):
            v = d.get(b)
            if v is None:
                return "YOK"
            if isinstance(v, dict) and ("hata" in v or "_hata" in v):
                return "HATA"
            if hasattr(v, "__len__") and len(v) == 0:
                return "BOŞ"
            return "var"
        rapor["bolum_durumu"][b] = (_durum(eski), _durum(yeni))

    # 2) BİRİNCİL: audienceWatchRatio %2 ve %3
    for nokta in ("0.02", "0.03"):
        e, y = _tutma_noktalari(eski, nokta), _tutma_noktalari(yeni, nokta)
        ortak = sorted(set(e) & set(y))
        gercek = [p for p in ortak if p not in KOPYA_PROJELER]
        eo, yo = _ortalama([e[p] for p in gercek]), _ortalama([y[p] for p in gercek])
        rapor["birincil"][nokta] = {
            "temel_belge_ortalamasi": TEMEL_TUTMA_ORTALAMASI[nokta],
            "eski_ortalama": eo, "yeni_ortalama": yo,
            "fark_puan": round((yo - eo) * 100, 1) if (eo is not None and yo is not None) else None,
            "video_sayisi": len(gercek),
            "haric_tutulan": [p for p in ortak if p in KOPYA_PROJELER],
            "yalnizca_eskide": sorted(set(e) - set(y)),
            "yalnizca_yenide": sorted(set(y) - set(e)),
            "video_bazinda": {p: {"eski": e[p], "yeni": y[p],
                                  "fark_puan": round((y[p] - e[p]) * 100, 1)}
                              for p in ortak},
        }

    # 3) İKİNCİL: kanal geneli
    for pencere in ("kanal_28gun", "kanal_7gun"):
        e, y = eski.get(pencere) or {}, yeni.get(pencere) or {}
        rapor["ikincil"][pencere] = {
            m: {"eski": e.get(m), "yeni": y.get(m),
                "fark": (round(y[m] - e[m], 2)
                         if isinstance(e.get(m), (int, float))
                         and isinstance(y.get(m), (int, float)) else None)}
            for m in ("views", "estimatedMinutesWatched", "averageViewDuration",
                      "averageViewPercentage", "subscribersGained", "likes",
                      "comments", "shares")}

    # 4) İçerik tipi (uzun vs Shorts) — "Shorts değer mi" sorusu buradan
    def _tip_haritasi(d, anahtar):
        return {r.get("creatorContentType"): r for r in (d.get(anahtar) or [])
                if isinstance(r, dict)}
    for anahtar in ("icerik_tipi_28gun", "icerik_tipi_7gun"):
        e, y = _tip_haritasi(eski, anahtar), _tip_haritasi(yeni, anahtar)
        rapor["icerik_tipi"][anahtar] = {
            tip: {m: {"eski": e.get(tip, {}).get(m), "yeni": y.get(tip, {}).get(m)}
                  for m in ("views", "estimatedMinutesWatched",
                            "averageViewPercentage", "subscribersGained")}
            for tip in sorted(set(e) | set(y))}

    # 5) Kart/playlist ve trafik kaynakları
    e, y = eski.get("kart_ve_playlist_28gun") or {}, yeni.get("kart_ve_playlist_28gun") or {}
    rapor["kart_ve_playlist"] = {m: {"eski": e.get(m), "yeni": y.get(m)}
                                 for m in sorted(set(e) | set(y))}

    def _trafik(d):
        kaynak = (d.get("trafik_kaynaklari_28gun") or {}).get("insightTrafficSourceType")
        return {r["insightTrafficSourceType"]: r.get("views")
                for r in kaynak} if isinstance(kaynak, list) else {}
    e, y = _trafik(eski), _trafik(yeni)
    rapor["trafik"] = {k: {"eski": e.get(k), "yeni": y.get(k)}
                       for k in sorted(set(e) | set(y))}
    return rapor


def _bas_karsilastirma(r, eski_yol, yeni_yol):
    print("=" * 72)
    print("ÖLÇÜM KARŞILAŞTIRMASI")
    print("  temel/eski : %s  (%s)" % (os.path.basename(eski_yol), r["eski_alindi"]))
    print("  yeni       : %s  (%s)" % (os.path.basename(yeni_yol), r["yeni_alindi"]))
    print("=" * 72)

    print("\n[1] BİRİNCİL METRİK — audienceWatchRatio %2 ve %3")
    for nokta in ("0.02", "0.03"):
        b = r["birincil"][nokta]
        print("\n  %%%s noktası  (belgedeki temel ortalama: %s)"
              % (nokta.split(".")[1].lstrip("0") or "0", b["temel_belge_ortalamasi"]))
        print("    eski ort: %s | yeni ort: %s | FARK: %s puan  (n=%d video)"
              % (b["eski_ortalama"], b["yeni_ortalama"],
                 ("%+.1f" % b["fark_puan"]) if b["fark_puan"] is not None else "?",
                 b["video_sayisi"]))
        if b["haric_tutulan"]:
            print("    ortalamaya katılmayan (kopya): %s" % ", ".join(b["haric_tutulan"]))
        for p, d in sorted(b["video_bazinda"].items(), key=lambda x: -x[1]["fark_puan"]):
            isaret = "  (kopya)" if p in KOPYA_PROJELER else ""
            print("      %-26s %5.3f -> %5.3f   %+5.1f puan%s"
                  % (p[:26], d["eski"], d["yeni"], d["fark_puan"], isaret))
        if b["yalnizca_eskide"]:
            print("    yalnızca eski ölçümde: %s" % ", ".join(b["yalnizca_eskide"]))
        if b["yalnizca_yenide"]:
            print("    yalnızca yeni ölçümde: %s" % ", ".join(b["yalnizca_yenide"]))

    print("\n[2] İKİNCİL — kanal geneli")
    for pencere, veri in r["ikincil"].items():
        print("  %s" % pencere)
        for m, d in veri.items():
            print("    %-26s %10s -> %10s   %s"
                  % (m, d["eski"], d["yeni"],
                     ("%+g" % d["fark"]) if d["fark"] is not None else "-"))

    print("\n[3] İÇERİK TİPİ (uzun format vs Shorts)")
    for anahtar, tipler in r["icerik_tipi"].items():
        print("  %s" % anahtar)
        for tip, metrikler in tipler.items():
            ozet = " | ".join("%s %s->%s" % (m, d["eski"], d["yeni"])
                              for m, d in metrikler.items())
            print("    %-16s %s" % (tip, ozet))

    print("\n[4] TRAFİK KAYNAKLARI (izlenme)")
    for k, d in r["trafik"].items():
        print("    %-28s %8s -> %8s" % (k, d["eski"], d["yeni"]))

    print("\n[5] KART / PLAYLIST")
    for m, d in r["kart_ve_playlist"].items():
        print("    %-28s %8s -> %8s" % (m, d["eski"], d["yeni"]))

    print("\n[6] 14 BÖLÜMÜN DURUMU (eski -> yeni)")
    for b, (e, y) in r["bolum_durumu"].items():
        uyari = "   <-- DİKKAT" if y != "var" else ""
        print("    %-26s %-5s -> %-5s%s" % (b, e, y, uyari))

    print("\n" + "-" * 72)
    print("GÜRÜLTÜ TABANI — sonucu yorumlamadan ÖNCE oku:")
    print("  Aynı ses/söz/md5'e sahip iki video (Yeniden Doğacağım / Küllerimden")
    print("  Geç) arasında %%3 noktasında %.1f puan fark ölçüldü — içerik farkı" % GURULTU_TABANI_PUAN)
    print("  SIFIRKEN. Bu ölçekte TEK video farkları anlamsız; yalnızca 7 videonun")
    print("  ORTALAMASINDAKİ yön anlamlı, o da ancak birkaç ölçüm üst üste aynı")
    print("  yönü gösterirse. Kapak ve açılış AYNI GÜN değişti; iyileşme olsa")
    print("  bile hangisinin yaptığı AYRILAMAZ.")
    print("-" * 72)


# ---------------------------------------------------------------------------
def _bas_dry_run(sonuc, cikti_yolu):
    print("=" * 72)
    print("DRY-RUN — hiçbir API çağrısı yapılmadı, hiçbir dosya yazılmadı")
    print("=" * 72)
    harita = sonuc["video_meta"]
    uzun = sum(1 for m in harita.values() if m["tip"] == "uzun")
    print("  video haritası : %d video (%d uzun + %d Shorts), %d proje klasöründen"
          % (len(harita), uzun, len(harita) - uzun,
             len({m["proje"] for m in harita.values()})))
    print("  yazılacak dosya: %s" % cikti_yolu)
    print("  karşılaştırma  : %s" % TEMEL_CIZGI_PATH)
    print("  üretilecek bölüm sayısı: %d"
          % len([b for b in BOLUMLER if b in sonuc]))
    eksik = [b for b in BOLUMLER if b not in sonuc]
    print("  eksik bölüm    : %s" % (", ".join(eksik) if eksik else "yok"))
    print("\n  YAPILACAK SORGULAR (%d adet, hepsi SALT OKUMA):" % len(_SORGULAR))
    for etiket, dim, met in _SORGULAR:
        print("    %-24s dim=%-24s metrics=%s" % (etiket[:24], dim, met))
    print("\n  Gerçek ölçüm için: python olcum_temel_cizgi.py --cek")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Kanal ölçüm penceresi (salt okuma). Randevu: %s"
                    % OLCUM_RANDEVUSU,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Temel çizgi (olcum_temel_cizgi.json) HİÇBİR KOŞULDA ÜSTÜNE YAZILMAZ.")
    ap.add_argument("--cek", action="store_true",
                    help="Gerçek ölçüm: 14 bölümü çeker, tarihli dosyaya yazar")
    ap.add_argument("--dry-run", action="store_true",
                    help="Hiç ağa çıkmaz, hiç yazmaz: ne yapılacağını gösterir")
    ap.add_argument("--karsilastir", nargs="*", metavar="DOSYA",
                    help="İki ölçümü karşılaştırır "
                         "(argümansız: temel çizgi <-> en yeni ölçüm)")
    ap.add_argument("--cikti", metavar="YOL", help="Çekim çıktısının yolu")
    ap.add_argument("--zorla", action="store_true",
                    help="Aynı tarihli çıktı dosyası varsa üstüne yaz")
    ap.add_argument("--json", action="store_true",
                    help="Karşılaştırmayı ham JSON olarak yazdır")
    args = ap.parse_args(argv)

    if args.karsilastir is not None:
        yollar = list(args.karsilastir)
        if len(yollar) == 0:
            son = _son_olcum_yolu()
            if son is None:
                raise SystemExit(
                    "Karşılaştırılacak ikinci ölçüm yok. Önce: "
                    "python olcum_temel_cizgi.py --cek")
            yollar = [TEMEL_CIZGI_PATH, son]
        elif len(yollar) == 1:
            yollar = [TEMEL_CIZGI_PATH] + yollar
        elif len(yollar) > 2:
            raise SystemExit("--karsilastir en fazla iki dosya alır.")
        eski_yol, yeni_yol = (os.path.abspath(y) for y in yollar)
        r = karsilastir(_json_oku(eski_yol), _json_oku(yeni_yol))
        if args.json:
            print(json.dumps(r, ensure_ascii=False, indent=2))
        else:
            _bas_karsilastirma(r, eski_yol, yeni_yol)
        return 0

    if args.dry_run:
        sonuc = cek(kuru=True)
        _bas_dry_run(sonuc, _cikti_yolu(args.cikti))
        return 0

    if args.cek:
        sonuc = cek(kuru=False)
        yol = yaz(sonuc, args.cikti, args.zorla)
        print("yazıldı: %s" % yol)
        print("video sayısı: %d | 28g veri gelen: %d"
              % (len(sonuc["video_meta"]), len(sonuc["pencere_28gun"]["video"])))
        print("kanal 28g: %s" % json.dumps(sonuc["kanal_28gun"], ensure_ascii=False))
        print("\nŞimdi: python olcum_temel_cizgi.py --karsilastir")
        return 0

    ap.print_help()
    print("\nDurum:")
    print("  temel çizgi : %s"
          % ("var" if os.path.isfile(TEMEL_CIZGI_PATH) else "YOK!"))
    son = _son_olcum_yolu()
    print("  son ölçüm   : %s" % (os.path.basename(son) if son else "henüz yok"))
    print("  randevu     : %s (bugün: %s)" % (OLCUM_RANDEVUSU, date.today()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
