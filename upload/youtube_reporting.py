# -*- coding: utf-8 -*-
"""YouTube Reporting API — küçük resim GÖSTERİMİ ve TIKLANMA ORANI.

NEDEN AYRI BİR SERVİS (ve neden bu modül var):

`upload/youtube_analytics.py` izlenme süresini youtubeAnalytics v2'den
çekiyor. Ama küçük resim **gösterimi** ve **tıklanma oranı** o API'de HİÇ
YOK — metrik adı bile tanınmıyor: `olcum_temel_cizgi.json` dört ayrı ad
denedi (`impressions`, `impressionClickThroughRate`, `videoImpressions`,
`thumbnailImpressions`) ve dördü de HTTP 400 "Unknown identifier" döndü. Bu
bir izin sorunu DEĞİL: aynı token ile `views` / `estimatedMinutesWatched`
sorunsuz geliyor. Metrik, YouTube **Reporting** API'sinin (ayrı servis:
`youtubereporting` v1) `channel_reach_basic_a1` / `channel_reach_combined_a1`
raporlarında yaşıyor (`video_thumbnail_impressions`,
`video_thumbnail_impressions_ctr`).

NEDEN ZAMAN KRİTİK (bu modülün varlık sebebi):

Reporting API "sorgu" değil "toplu iş" modeli kullanıyor. Rapor üretimi bir
**job** oluşturulunca BAŞLIYOR ve YouTube geriye dönük olarak yalnızca
**job oluşturulmadan önceki 30 günü** dolduruyor. API'yi Cloud Console'dan
etkinleştirmek TEK BAŞINA bu sayacı BAŞLATMIYOR — job gerekiyor.
2026-09-11'de kanalın 40 kapağı birden değişti; "değişiklik öncesi" temel
çizgi tam da o 30 günlük pencerenin içinde ve her gecikme günü pencereden
bir gün siliyor (bkz. `buyume_kontrol_listesi.md`, B1 — son tarih
2026-10-11). Yani bu modülün ilk çalıştırılması geri alınamaz bir olaydır.

KİMLİK — `upload/token.json`'A DOKUNULMUYOR:

Reporting API `yt-analytics.readonly` istiyor; bu izin ZATEN
`upload/analytics_token.json`'da var, yani YENİ bir tarayıcı onayı
GEREKMİYOR. O token bilerek AYRI: `Credentials.from_authorized_user_file`
kayıtlı izinlerle istenenleri karşılaştırdığı için `upload/token.json`'a
`yt-analytics.readonly` eklemek o token'ı GEÇERSİZ KILAR ve SAATLİK YÜKLEME
HATTI DURUR (CLAUDE.md'deki açık uyarı). Bu modül token yolunu/izin listesini
`youtube_analytics`'ten İMPORT ediyor, KOPYALAMIYOR — `uyumluluk.KOKLER`
dersi: kopya, ikinci bir yerde elle güncellenmeyi bekleyen sessiz arızadır.

NEDEN SESSİZ GEÇİŞ YOK (youtube_analytics'ten FARKLI):

`youtube_analytics.get_service()` token yoksa `None` dönüp sessizce geçiyor;
orada doğru olan buydu, çünkü çağıranı otomasyonun içindeydi ve ölçüm için
hattı durdurmak kabul edilemezdi. BURADA tam tersi geçerli: bu iş ELLE ve
YILDA BİRKAÇ KEZ çalışıyor, penceresi kayınca telafisi YOK. Sessizce `{}`
dönen bir kurulum, kurulmadığını ancak veri istendiği gün — yani artık geç
olduğu gün — belli ederdi. Bu yüzden her hata `ReportingHatasi` ile
YÜKSELTİLİYOR; özellikle izin (scope) yetersizliği ve SERVICE_DISABLED,
"ne yapılacağı" cümlesiyle birlikte.

ÜÇ SORU (CLAUDE.md):
  1. Kim çağıracak? — ELLE operatör (aşağıdaki CLI) ve ölçüm randevusunda
     `olcum_temel_cizgi.py`. Tek seferlik kurulum + dönemsel indirme.
  2. Hangi zamanlayıcı görevinden? — HİÇBİRİ, BİLEREK. Bu saatlik yükleme
     hattının işi değil; `auto_process.main()`'in `finally` bloğuna bir de
     bunu koymak, kotası ve gecikmesi olan bir işi her koşuya bindirmek
     olurdu (CLAUDE.md kuralının (B) şıkkı: ayrı modül, ayrı tetik). Raporlar
     zaten günde bir üretiliyor, saatlik çağırmanın hiçbir faydası yok.
  3. Çalışmadığını nasıl anlarız? — Hiçbir dal sessizce boş dönmüyor:
     `durum()` job'ların ve son raporların varlığını yazdırıyor, hata
     yükseliyor. `tests/test_youtube_reporting.py` idempotentliği, tip
     tahmininin yasak olduğunu ve izin hatasının sessiz kalmadığını
     doğruluyor.

KULLANIM:
    python upload/youtube_reporting.py --tipler       # API'nin sunduğu tipler
    python upload/youtube_reporting.py --kur --kuru   # ne yapacağını yazdır
    python upload/youtube_reporting.py --kur          # job(ları) OLUŞTURUR
    python upload/youtube_reporting.py --durum        # job + son raporlar
    python upload/youtube_reporting.py --indir        # CSV'leri diske çeker
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

UPLOAD_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(UPLOAD_DIR)

# Log'a yazilan HER metin buradan geciyor (asagidaki `_log`). Bu bir GARANTI
# ifadesidir, dolayisiyla testi de var: modulde `print` cagrisi YOK, tek cikis
# `_log`. Gerekce: bir ag/HTTP hatasinin metni istek URL'ini tasiyabiliyor
# (bkz. gizli_maskele.py docstring'i, 2026-09-04 Instagram token sizintisi).
from gizli_maskele import maskele, maskele_istisna  # noqa: E402

# TEK kanonik kaynak: token yolu, client secrets ve izin listesi
# `youtube_analytics`te tanimli. Buraya KOPYALANMIYOR — kopya, o dosya
# degistiginde sessizce ayrisan ikinci bir gercek demek.
import youtube_analytics  # noqa: E402
from youtube_analytics import CLIENT_SECRETS_PATH, TOKEN_PATH  # noqa: E402,F401

# Reporting API bu izinlerden BIRINI kabul ediyor. Parasal olan (monetary)
# daha genis; kanalda para kazanma acik degil, bu yuzden istenen izin
# `yt-analytics.readonly` ve mevcut analytics_token.json'da ZATEN o var.
GEREKLI_SCOPELAR = (
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/yt-analytics-monetary.readonly",
)

# ISTENEN tipler — TAHMIN DEGIL, istek listesi. `kur()` bunlari once
# `mevcut_rapor_tipleri()` (yani API'nin KENDI listesi) ile karsilastiriyor ve
# listede olmayan bir tip icin job ACMIYOR. Sebep: rapor tipi adlari surum
# ekliyle geliyor (`..._a1`, `..._a2`) ve YouTube eskisini kullanimdan
# kaldirabiliyor; uydurulmus bir ada job acmak ya 400 verir ya da daha
# kotusu — bos ureten bir job birakir ve 30 gunluk pencere sessizce yanar.
ISTENEN_RAPOR_TIPLERI = (
    "channel_reach_basic_a1",
    "channel_reach_combined_a1",
)

# Job adi: Console'da/`--durum` ciktisinda kimin acdigi belli olsun diye.
JOB_ADI_ONEKI = "fms"

# Indirilen CSV'lerin yeri. Repo kokunde AYRI bir klasor: `projects/`,
# `dj_sets/`, `derlemeler/` icerik KOKLERI ve oraya dosya birakmak yayin
# kuyruguna sahte oge sokmak demek (bkz. tests/conftest.py, HEDEF_KOK notu).
INDIRME_DIZINI = os.path.join(REPO_DIR, "olcum_reporting")


class ReportingHatasi(RuntimeError):
    """Reporting API tarafindaki her arizanin TEK tipi.

    Ayri bir tip olmasinin sebebi cagiranin `HttpError` ile `FileNotFoundError`
    arasinda ayrim yapmak zorunda kalmamasi; mesaj her zaman "ne yapilacagini"
    da soyluyor.
    """


def _log(mesaj) -> None:
    """Tek cikis noktasi — maskeleyiciden GECER."""
    print(maskele(mesaj))


def _scope_dogrula(creds) -> None:
    """Token'in izni Reporting icin yetiyor mu — YETMIYORSA YUKSELTIR.

    NEDEN SESSIZ DEGIL: yetersiz izin, API'yi cagirinca 403 olarak geri
    doner ve o 403'un metni "insufficient permissions" gibi genel bir sey
    olur; operatorun oradan "yeni bir tarayici onayi gerekiyor" sonucunu
    cikarmasi beklenemez. Burada ONCEDEN, ag'a hic cikmadan ve ne
    yapilacagini yazarak duruyoruz.
    """
    sahip = set(getattr(creds, "scopes", None) or ())
    if sahip & set(GEREKLI_SCOPELAR):
        return
    raise ReportingHatasi(
        "analytics_token.json'un izinleri Reporting API icin YETMIYOR.\n"
        "  Token'da olan  : %s\n"
        "  Gereken (biri) : %s\n"
        "  YAPILACAK: python upload/youtube_analytics.py --auth  "
        "(tarayicida bir kereye mahsus onay; ayni izin listesi).\n"
        "  DIKKAT: upload/token.json'a bu izni EKLEME — o token'i gecersiz "
        "kilar ve SAATLIK YUKLEME HATTI DURUR (CLAUDE.md)."
        % (sorted(sahip) or "(hic izin kayitli degil)", GEREKLI_SCOPELAR[0]))


def kimlik():
    """`analytics_token.json`'dan kimlik doner; eksik/yetersizse YUKSELTIR."""
    if not os.path.isfile(TOKEN_PATH):
        raise ReportingHatasi(
            "analytics_token.json bulunamadi: %s\n"
            "  YAPILACAK: python upload/youtube_analytics.py --auth"
            % TOKEN_PATH)

    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    try:
        creds = Credentials.from_authorized_user_file(
            TOKEN_PATH, list(youtube_analytics.SCOPES))
    except Exception as e:
        raise ReportingHatasi(
            "analytics_token.json okunamadi (%s).\n"
            "  YAPILACAK: python upload/youtube_analytics.py --auth"
            % maskele_istisna(e))

    _scope_dogrula(creds)

    if not creds.valid:
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                raise ReportingHatasi(
                    "Token yenilenemedi (%s).\n"
                    "  YAPILACAK: python upload/youtube_analytics.py --auth"
                    % maskele_istisna(e))
            # Yazim `youtube_analytics._token_yaz` uzerinden: ATOMIK yazimin
            # DORDUNCU kopyasini burada acmiyoruz (state_io dersi).
            youtube_analytics._token_yaz(creds)
        else:
            raise ReportingHatasi(
                "Token gecersiz ve yenilenemiyor (refresh_token yok).\n"
                "  YAPILACAK: python upload/youtube_analytics.py --auth")
    return creds


def get_service(creds=None):
    """`youtubereporting` v1 servisi. Analytics'ten AYRI bir servis adi."""
    from googleapiclient.discovery import build
    return build("youtubereporting", "v1", credentials=creds or kimlik())


def _cagir(istek, ne: str):
    """Bir API cagrisini calistirir; hatayi KONUSAN bir mesaja cevirir.

    SERVICE_DISABLED ozel olarak ayristiriliyor: bu, kodun degil Cloud
    Console'un isi ve mesaji "kod bozuk" gibi okunuyordu.
    """
    try:
        return istek.execute()
    except Exception as e:
        metin = maskele_istisna(e)
        if "SERVICE_DISABLED" in metin or "has not been used in project" in metin:
            raise ReportingHatasi(
                "YouTube Reporting API bu Cloud projesinde KAPALI (%s).\n"
                "  YAPILACAK: Console > APIs & Services > "
                "youtubereporting.googleapis.com > ETKINLESTIR "
                "(proje 1026223060773), sonra birkac dakika yayilma bekle.\n"
                "  Ham hata: %s" % (ne, metin[:400]))
        if "insufficientPermissions" in metin or "Insufficient Permission" in metin:
            raise ReportingHatasi(
                "Reporting API izni reddetti (%s). Token'in izni yetmiyor "
                "olabilir.\n  YAPILACAK: python upload/youtube_analytics.py "
                "--auth\n  Ham hata: %s" % (ne, metin[:400]))
        raise ReportingHatasi("%s basarisiz: %s" % (ne, metin[:600]))


def mevcut_rapor_tipleri(servis) -> dict:
    """API'nin GERCEKTEN sundugu rapor tipleri: {id: {ad, kullanimdan_kaldirildi}}.

    Bu fonksiyon olmadan `kur()` calistirilamaz — tip adi TAHMIN EDILMEZ.
    """
    tipler = {}
    sayfa = None
    while True:
        y = _cagir(servis.reportTypes().list(pageToken=sayfa, includeSystemManaged=True),
                   "reportTypes().list")
        for t in y.get("reportTypes", []) or []:
            tid = t.get("id")
            if not tid:
                continue
            tipler[tid] = {
                "ad": t.get("name") or tid,
                # `deprecateTime` doluysa YouTube o tipi kaldiracak; yeni job
                # acmak icin kotu aday, ama VAR olan bir tip — silmiyoruz,
                # isaretliyoruz ki `kur()` gerekcesini yazabilsin.
                "kullanimdan_kaldirildi": bool(t.get("deprecateTime")),
                "kaldirma_zamani": t.get("deprecateTime"),
            }
        sayfa = y.get("nextPageToken")
        if not sayfa:
            break
    return tipler


def joblari_listele(servis) -> list:
    """Kanalda TANIMLI tum reporting job'lari (sayfalanmis)."""
    joblar = []
    sayfa = None
    while True:
        y = _cagir(servis.jobs().list(pageToken=sayfa, includeSystemManaged=True),
                   "jobs().list")
        joblar.extend(y.get("jobs", []) or [])
        sayfa = y.get("nextPageToken")
        if not sayfa:
            break
    return joblar


def _job_bul(joblar, rapor_tipi: str):
    """Verilen rapor tipi icin ZATEN duran job (yoksa None).

    IDEMPOTENTLIK BURADA: ayni tip icin ikinci bir job acmak, ayni veriyi iki
    kez uretmek ve `--durum` ciktisinda hangisinin dogru oldugunu belirsiz
    birakmak demek. API ikinci job'i REDDETMIYOR, sessizce kabul ediyor.
    """
    for j in joblar:
        if j.get("reportTypeId") == rapor_tipi:
            return j
    return None


def job_olustur(servis, rapor_tipi: str, joblar=None, kuru: bool = False):
    """Tek bir tip icin job; VARSA yenisini ACMAZ.

    Doner: (job_sozlugu_veya_None, yeni_mi)
    """
    if joblar is None:
        joblar = joblari_listele(servis)
    var = _job_bul(joblar, rapor_tipi)
    if var is not None:
        return var, False
    if kuru:
        return None, True          # kuru kosuda hicbir sey OLUSTURULMAZ
    yeni = _cagir(
        servis.jobs().create(body={
            "reportTypeId": rapor_tipi,
            "name": "%s_%s" % (JOB_ADI_ONEKI, rapor_tipi),
        }),
        "jobs().create(%s)" % rapor_tipi)
    return yeni, True


def kur(istenen=ISTENEN_RAPOR_TIPLERI, kuru: bool = False, servis=None) -> dict:
    """Istenen rapor tipleri icin job'lari IDEMPOTENT kurar.

    SIRA BILINCLI: once `reportTypes().list` (API'nin kendi sozlugu), sonra
    `jobs().list` (zaten duranlar), EN SON `jobs().create`. Ilk adim atlanirsa
    uydurma bir tip adina job acilabilir; ikincisi atlanirsa her kosuda yeni
    bir kopya job birikir.
    """
    if servis is None:
        servis = get_service()

    tipler = mevcut_rapor_tipleri(servis)
    if not tipler:
        raise ReportingHatasi(
            "reportTypes().list BOS dondu. Bu normal degil — job acmadan "
            "duruluyor (bos listeye guvenip tip adi TAHMIN ETMEK, 30 gunluk "
            "geriye doldurma penceresini bos bir job'a harcamak olurdu).")

    joblar = joblari_listele(servis)
    sonuc = {
        "kuru": kuru,
        "mevcut_tip_sayisi": len(tipler),
        "joblar": {},
        "atlanan": {},
    }

    for tip in istenen:
        bilgi = tipler.get(tip)
        if bilgi is None:
            sonuc["atlanan"][tip] = "API bu rapor tipini SUNMUYOR"
            _log("  ATLANDI %s: API'nin listesinde YOK (tip adi tahmin "
                 "edilmiyor). Mevcut 'reach' tipleri: %s"
                 % (tip, ", ".join(sorted(t for t in tipler if "reach" in t))
                    or "(yok)"))
            continue
        if bilgi["kullanimdan_kaldirildi"]:
            sonuc["atlanan"][tip] = ("kullanimdan kaldiriliyor (%s)"
                                     % bilgi["kaldirma_zamani"])
            _log("  ATLANDI %s: YouTube bu tipi kaldiriyor (%s)."
                 % (tip, bilgi["kaldirma_zamani"]))
            continue

        job, yeni = job_olustur(servis, tip, joblar=joblar, kuru=kuru)
        if job is not None:
            joblar.append(job)     # ayni kosuda ikinci kez acilmasin
        sonuc["joblar"][tip] = {
            "id": (job or {}).get("id"),
            "ad": (job or {}).get("name"),
            "olusturuldu": (job or {}).get("createTime"),
            "yeni": yeni,
        }
        if yeni and kuru:
            _log("  KURU: %s icin job OLUSTURULACAKTI (simdi olusturulmadi)." % tip)
        elif yeni:
            _log("  OLUSTURULDU %s -> job id %s" % (tip, (job or {}).get("id")))
        else:
            _log("  ZATEN VAR  %s -> job id %s (ikincisi ACILMADI)"
                 % (tip, (job or {}).get("id")))

    if not sonuc["joblar"] and not kuru:
        raise ReportingHatasi(
            "Hicbir job kurulamadi. Atlananlar: %s"
            % json.dumps(sonuc["atlanan"], ensure_ascii=False))
    return sonuc


def raporlari_listele(servis, job_id: str, gun: int = 45) -> list:
    """Bir job'in URETTIGI raporlar (en yeni once).

    `gun`: `createdAfter` filtresi. Varsayilan 45, cunku geriye doldurma
    penceresi 30 gun ve raporlar gunlerce sonra da uretilebiliyor.
    """
    sinir = (datetime.now(timezone.utc) - timedelta(days=gun)).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    raporlar = []
    sayfa = None
    while True:
        y = _cagir(
            servis.jobs().reports().list(
                jobId=job_id, createdAfter=sinir, pageToken=sayfa),
            "jobs().reports().list(%s)" % job_id)
        raporlar.extend(y.get("reports", []) or [])
        sayfa = y.get("nextPageToken")
        if not sayfa:
            break
    raporlar.sort(key=lambda r: r.get("startTime") or "", reverse=True)
    return raporlar


def rapor_indir(servis, rapor: dict, hedef_dizin: str = None) -> str:
    """Tek bir raporu diske yazar; yazilan dosyanin yolunu doner.

    ATOMIK DEGIL ama gerek de yok: dosya adi rapor id'sini tasiyor ve VARSA
    yeniden indirilmiyor — yarim kalan bir indirme bir sonraki kosuda ayni
    adla bastan yazilir.
    """
    import io
    from googleapiclient.http import MediaIoBaseDownload

    hedef_dizin = hedef_dizin or INDIRME_DIZINI
    os.makedirs(hedef_dizin, exist_ok=True)
    ad = "%s_%s.csv" % ((rapor.get("startTime") or "bilinmiyor")[:10],
                        rapor.get("id") or "rapor")
    yol = os.path.join(hedef_dizin, ad)

    url = rapor.get("downloadUrl")
    if not url:
        raise ReportingHatasi(
            "Raporda downloadUrl yok: %s" % json.dumps(rapor, ensure_ascii=False)[:300])

    # Resmi ornekteki yontem: media().download() istegi kurulup uri'si
    # raporun downloadUrl'iyle DEGISTIRILIYOR (resourceName tek basina
    # yetmiyor, API imzali bir URL veriyor).
    istek = servis.media().download(resourceName="")
    istek.uri = url
    with io.FileIO(yol, mode="wb") as f:
        indirici = MediaIoBaseDownload(f, istek, chunksize=-1)
        bitti = False
        while not bitti:
            try:
                _, bitti = indirici.next_chunk()
            except Exception as e:
                raise ReportingHatasi(
                    "Rapor indirilemedi (%s): %s"
                    % (rapor.get("id"), maskele_istisna(e)))
    return yol


def indir(servis=None, gun: int = 45, hedef_dizin: str = None) -> dict:
    """Kurulu TUM job'larin son raporlarini indirir. {job_id: [yol, ...]}"""
    if servis is None:
        servis = get_service()
    hedef_dizin = hedef_dizin or INDIRME_DIZINI
    sonuc = {}
    joblar = joblari_listele(servis)
    if not joblar:
        raise ReportingHatasi(
            "Hic reporting job YOK — indirilecek rapor da yok.\n"
            "  YAPILACAK: python upload/youtube_reporting.py --kur")
    for j in joblar:
        jid = j.get("id")
        raporlar = raporlari_listele(servis, jid, gun=gun)
        if not raporlar:
            _log("  %s (%s): henuz rapor URETILMEDI. Job yeni olusturulduysa "
                 "ilk dosyalar ~24-48 saat icinde gelir; geriye donuk 30 gun "
                 "de o zaman dolar." % (jid, j.get("reportTypeId")))
            sonuc[jid] = []
            continue
        yollar = []
        for r in raporlar:
            yollar.append(rapor_indir(servis, r, hedef_dizin))
        _log("  %s (%s): %d rapor indirildi -> %s"
             % (jid, j.get("reportTypeId"), len(yollar), hedef_dizin))
        sonuc[jid] = yollar
    return sonuc


def durum(servis=None, gun: int = 45) -> dict:
    """Job'lar + her birinin son rapor tarihi. Hicbir sey OLUSTURMAZ/INDIRMEZ."""
    if servis is None:
        servis = get_service()
    joblar = joblari_listele(servis)
    d = {"job_sayisi": len(joblar), "joblar": []}
    for j in joblar:
        raporlar = raporlari_listele(servis, j.get("id"), gun=gun)
        d["joblar"].append({
            "id": j.get("id"),
            "ad": j.get("name"),
            "rapor_tipi": j.get("reportTypeId"),
            "olusturuldu": j.get("createTime"),
            "rapor_sayisi": len(raporlar),
            "en_yeni_rapor": (raporlar[0].get("startTime") if raporlar else None),
        })
    return d


def main():
    ap = argparse.ArgumentParser(
        description="YouTube Reporting API — job kurulumu ve rapor indirme.")
    ap.add_argument("--tipler", action="store_true",
                    help="API'nin sundugu rapor tiplerini yazdir (hicbir sey olusturmaz)")
    ap.add_argument("--kur", action="store_true",
                    help="Istenen rapor tipleri icin job'lari IDEMPOTENT kur")
    ap.add_argument("--kuru", action="store_true",
                    help="--kur ile: ne yapilacagini yazdir, OLUSTURMA")
    ap.add_argument("--durum", action="store_true",
                    help="Kurulu job'lar ve son raporlari")
    ap.add_argument("--indir", action="store_true",
                    help="Uretilmis raporlari %s altina indir" % INDIRME_DIZINI)
    ap.add_argument("--gun", type=int, default=45,
                    help="Rapor listeleme penceresi (varsayilan 45 gun)")
    ap.add_argument("--json", action="store_true", help="Ham JSON yazdir")
    args = ap.parse_args()

    if not (args.tipler or args.kur or args.durum or args.indir):
        ap.print_help()
        return 0

    try:
        servis = get_service()

        if args.tipler:
            tipler = mevcut_rapor_tipleri(servis)
            if args.json:
                _log(json.dumps(tipler, ensure_ascii=False, indent=2))
            else:
                _log("API %d rapor tipi sunuyor. 'reach' iceren tipler:" % len(tipler))
                for tid in sorted(t for t in tipler if "reach" in t):
                    _log("  %-34s %s%s" % (
                        tid, tipler[tid]["ad"],
                        "  [KULLANIMDAN KALDIRILIYOR]"
                        if tipler[tid]["kullanimdan_kaldirildi"] else ""))

        if args.kur:
            _log("Job kurulumu (%s):" % ("KURU KOSU" if args.kuru else "GERCEK"))
            s = kur(kuru=args.kuru, servis=servis)
            if args.json:
                _log(json.dumps(s, ensure_ascii=False, indent=2))

        if args.durum:
            d = durum(servis, gun=args.gun)
            if args.json:
                _log(json.dumps(d, ensure_ascii=False, indent=2))
            else:
                _log("Kurulu job: %d" % d["job_sayisi"])
                for j in d["joblar"]:
                    _log("  %-24s %-34s rapor=%d  en_yeni=%s"
                         % (j["id"], j["rapor_tipi"], j["rapor_sayisi"],
                            j["en_yeni_rapor"]))

        if args.indir:
            _log("Raporlar indiriliyor -> %s" % INDIRME_DIZINI)
            indir(servis, gun=args.gun)
        return 0
    except ReportingHatasi as e:
        # SESSIZ KALMA: hata metni "ne yapilacagini" da tasiyor, ve cikis
        # kodu 1 — bir sarmalayici/zamanlayici bunu ayirt edebilsin diye.
        _log("HATA: %s" % e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
