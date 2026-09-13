# -*- coding: utf-8 -*-
"""YouTube Data API kota DEFTERİ — her çağrı `youtube_kota_defteri.jsonl`'a.

NEDEN VAR (2026-09-13): ortak 10.000 birimlik havuz gece bitti ve harcamanın
nereye gittiği HİÇBİR yere yazılmamıştı — tek kayıtlı iz `ai_beyani_onar.log`'daki
~2.142 birimdi. Bedeli: Sabah Senin'in kapak (`thumbnails.set`) ve playlist
adımları 403 aldı. Elle çalıştırılan betikler (ve ajanların `python -c` ile
yaptığı okumalar) hiçbir log'a düşmediği için "kim harcadı" sorusunun cevabı
yoktu.

MERKEZİ YAKALAMA — neden `requestBuilder`
-----------------------------------------
Depodaki TÜM Data API istemcileri tek bir yerden doğuyor:
`upload/youtube_auth.get_authenticated_service()` -> `build("youtube", "v3")`.
`build()` resmî bir `requestBuilder` parametresi alıyor; buraya verilen
`KotaliHttpRequest` (bir `googleapiclient.http.HttpRequest` alt sınıfı) her
isteğin `methodId`'sini ("youtube.videos.list") biliyor. Böylece:
  * çağrı noktalarının HİÇBİRİNE dokunulmuyor (40+ `.execute()`),
  * yarın eklenecek çağrı da kendiliğinden kapsanıyor ("unutulacak liste" yok),
  * `list_next()` isteği `copy.copy` ile türettiği için sayfalar da sayılıyor,
  * devam ettirilebilir yükleme (`next_chunk`) YALNIZ tamamlandığında BİR kez
    sayılıyor (`execute()` resumable isteklerde `next_chunk`'ı çağırdığı için
    çift sayım ayrıca engelleniyor).
`HttpRequest.execute`'u monkeypatch'lemek (global) Analytics/Reporting
istemcilerini de (AYRI kota) sayardı; `http` sarmalayıcısı ise metod adını
URL'den tahmin etmek zorunda kalırdı. Kapsam dışı: bu depo DIŞINDAN aynı
Google Cloud projesini kullanan istemciler (Studio, başka makine) — defter
onları GÖREMEZ; `ozet` bu yüzden "en az" harcamayı gösterir.

DEFTER HATASI ÇAĞRIYI ASLA DÜŞÜRMEZ: `kaydet()` her istisnayı yutar ve False
döner (stderr'e süreç başına bir uyarı). Koruma YALNIZ toplu ELLE betiklerde
(`ai_beyani_onar.py`, `set_privacy.py`); saatlik hat hiçbir koşulda
engellenmez, sadece `auto_process.log`'a `saglik_satiri()` düşer.

STUDIO BEKLEYEN İŞLERİ (2026-09-13, aynı gün) — `youtube_studio_bekleyenler.json`
------------------------------------------------------------------------------
`quotaExceeded` alan ve kodda KENDİLİĞİNDEN yeniden deneme yolu OLMAYAN adımlar
kalıcı bir listeye yazılır; Pasifik günü başına EN FAZLA bir Telegram mesajı
(`notify.send`) operatöre "Studio'dan elle tamamlanabilir" der. Koddan
doğrulanan ayrım (`studio_isi_turu`):
  * `thumbnails.set` -> YAZILIR ("kapak"). `youtube_upload.upload_video` /
    `upload_short` / `upload_clip` kapak hatasını yalnız `print` ediyor; state'e
    video kimliği yazıldığı için adım bir daha hiç denenmiyor.
  * `videos.update` + ELLE kaynak -> YAZILIR ("gizlilik" part=status, aksi hâlde
    "video_update"). `set_privacy.py`, `youtube_upload.py --description-only`
    ve ajanların tek seferlik betikleri kendini tekrar etmez.
    İSTİSNA `elle:ai_beyani_onar`: ilerleme dosyasıyla kaldığı yerden devam eder.
  * `videos.update` + saatlik hat -> YAZILMAZ: görünürlük planı
    (`auto_process._youtube_gorunurluk_planlarini_uygula`, plan silinmez) ve
    `dj_tarama_kontrol.yayina_ac` (`dj_tarama_bekliyor` açık kalır) bir sonraki
    koşuda yeniden dener.
  * `playlistItems.insert` -> YAZILMAZ: `youtube_playlists.sync_project`/`ekle`
    `process_project` içinde proje pending kaldıkça HER koşuda yeniden
    çağrılıyor. (Sınır: proje `_is_fully_done`'dan geçip pending'den düşerse
    tekrar YOK — o durumda Studio'dan bakmak gerekir; bugün bu türe yazan yol yok.)
  * `captions.*` -> YAZILMAZ: `_check_youtube_captions` süpürgesi yeniden dener.
Kapanış: `studio_bekleyen_tamamla(id, kaynak)` / CLI `studio-tamamla <id>`.
Saatlik hat, kota SIFIRLANDIKTAN sonra bekleyen kapak işlerini günde EN FAZLA
`KAPAK_TELAFI_GUNLUK` tane API ile de dener (`kapak_telafisi`, golden-hour
kısıtı yok, her denemeden önce `yeterli_mi(50)`); başarılıysa kaydı kapatır.

ÜÇ SORU (CLAUDE.md):
  1. Kim çağırıyor? — `youtube_auth.get_authenticated_service()` (kayıt +
     Studio işi), `auto_process.main()` finally'sinin son try'ı (`kosu_sonu`:
     kapak telafisi, Studio bildirimi, kota satırı), `ai_beyani_onar.main()` /
     `set_privacy.main()` (`toplu_izin`).
  2. Hangi zamanlayıcı görevinden? — saatlik `auto_process.py`; haftalık
     `dj_famous_process.py` kayıt tarafından kapsanıyor.
  3. Çalışmadığını nasıl anlarız? — her koşuda log'da "YouTube kota: ..."
     satırı (bekleyen Studio işi varsa sayısıyla); defter okunamıyorsa satırda
     yazar. Koruma: `tests/test_youtube_kota.py`.

Kullanım:
    python upload/youtube_kota.py ozet [--json]
    python upload/youtube_kota.py son [--adet 20]
    python upload/youtube_kota.py studio-bekleyenler [--json] [--tumu]
    python upload/youtube_kota.py studio-tamamla SB-xxxxxxxxxx [--kaynak claude]
"""

import argparse
import hashlib
import json
import os
import sys
import threading
from datetime import date, datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

UPLOAD_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(UPLOAD_DIR)

# Adı `DURUM_DOSYASI` BİLİNÇLİ: `tests/conftest.py` bu addaki her repo-içi yolu
# testlerde geçici klasöre çekiyor — defter bir ÖLÇÜM KAYNAĞI (toplu betiklerin
# eşiği ona bakıyor), bir test artığı üretimdeki eşiği kaydırmamalı.
DURUM_DOSYASI = os.path.join(REPO, "youtube_kota_defteri.jsonl")
ORTAM_DEGISKENI = "YOUTUBE_KOTA_DEFTERI"

GUNLUK_HAVUZ = 10000
INSERT_GUNLUK_CAGRI = 100
TOPLU_ESIK_ORANI = 0.60
SAKLAMA_GUN = 30
VARSAYILAN_YAYIN_REZERVI = 950   # config.YOUTUBE_KOTA_YAYIN_REZERVI yoksa

# Resmî maliyet tablosu — TEK sabit.
# Kaynak: https://developers.google.com/youtube/v3/determine_quota_cost
# (sayfanın "Last updated" tarihi 2026-09-04 UTC; 2026-09-13'te okundu).
# `videos.insert` ve `search.list` ORTAK havuzdan yemez: kendi kovaları var
# (günde 100 çağrı, çağrı başına 1).
MALIYETLER = {
    "videos.list": 1,
    "videos.update": 50,
    "videos.delete": 50,
    "thumbnails.set": 50,
    "playlistItems.list": 1,
    "playlistItems.insert": 50,
    "playlists.list": 1,
    "playlists.insert": 50,
    "channels.list": 1,
    "commentThreads.list": 1,
    "commentThreads.insert": 50,
    "comments.insert": 50,
    "captions.list": 50,
    "captions.insert": 400,
    "captions.update": 450,
}
AYRI_KOVALAR = {"videos.insert": "insert", "search.list": "search"}
# Tabloda OLMAYANLAR — tahmin, kayıtta `tahmin: true` olarak işaretlenir.
TAHMINI_MALIYETLER = {"captions.download": 200}

# Resmî: "Every API request, even if invalid, will cost at least one quota
# point." Başarısız çağrının TAM maliyeti belgelenmemiş -> alt sınır 1, tahmin.
# `quotaExceeded` (havuz zaten bitmişken) özelinde puan düşülüp düşülmediği
# DOĞRULANAMADI — bilinmiyor.
BASARISIZ_CAGRI_BIRIMI = 1

ZAMANLANMIS_BETIKLER = ("auto_process", "dj_famous_process", "watch_projects")

# Studio bekleyen işleri
STUDIO_ORTAM_DEGISKENI = "YOUTUBE_STUDIO_BEKLEYENLER"
STUDIO_DOSYA_ADI = "youtube_studio_bekleyenler.json"
STUDIO_IS_TURLERI = ("kapak", "playlist", "gizlilik", "video_update")
KENDINI_DENEYEN_ELLE_KAYNAKLAR = ("elle:ai_beyani_onar",)
KAPAK_TELAFI_GUNLUK = 3
KAPAK_BIRIMI = MALIYETLER["thumbnails.set"]
ELLE_ISLEM_ESLEMESI = {"kapak": "kapak_degistirdi", "playlist": "oynatma_listesi",
                       "gizlilik": "gizlilik_degistirdi", "video_update": "duzenledi"}

_KILIT = threading.RLock()
_DONDURULEN = set()
_UYARILDI = set()
UTC = timezone.utc


# ---------------------------------------------------------------------------
# Maliyet
# ---------------------------------------------------------------------------

def metod_adi(method_id) -> str:
    """'youtube.videos.list' -> 'videos.list'."""
    ad = str(method_id or "bilinmiyor")
    return ad[len("youtube."):] if ad.startswith("youtube.") else ad


def maliyet(metod):
    """(ortak_havuz_birimi, tahmin_mi, kova). Kova: 'ortak' | 'insert' | 'search'."""
    m = metod_adi(metod)
    if m in AYRI_KOVALAR:
        return 0, False, AYRI_KOVALAR[m]
    if m in MALIYETLER:
        return MALIYETLER[m], False, "ortak"
    if m in TAHMINI_MALIYETLER:
        return TAHMINI_MALIYETLER[m], True, "ortak"
    return (1 if m.endswith(".list") else 50), True, "ortak"


def _repo_yolda():
    if REPO not in sys.path:
        sys.path.append(REPO)


def yayin_rezervi() -> int:
    try:
        _repo_yolda()
        import config
        return int(getattr(config, "YOUTUBE_KOTA_YAYIN_REZERVI", VARSAYILAN_YAYIN_REZERVI))
    except Exception:                                   # noqa: BLE001
        return VARSAYILAN_YAYIN_REZERVI


# ---------------------------------------------------------------------------
# Pasifik günü — sabit saat YOK
# ---------------------------------------------------------------------------

def _pasifik_tz():
    """`zoneinfo` America/Los_Angeles. Windows'ta `tzdata` paketi yoksa None
    (bu üretim makinesinde 2026-09-13 itibarıyla YOK) -> `_yedek_ofset`."""
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo("America/Los_Angeles")
    except Exception:                                   # noqa: BLE001
        return None


def _pazar(yil, ay, en_erken_gun):
    g = date(yil, ay, en_erken_gun)
    return g + timedelta(days=(6 - g.weekday()) % 7)


def _yedek_ofset(an_utc) -> timedelta:
    """ABD kuralı (2007'den beri): yaz saati Mart'ın 2. pazarı 02:00 PST
    (10:00 UTC) — Kasım'ın 1. pazarı 02:00 PDT (09:00 UTC). `zoneinfo` ile
    eşitliği test ediliyor (tzdata olan ortamda)."""
    an_utc = an_utc.astimezone(UTC)
    y = an_utc.year
    bas = datetime.combine(_pazar(y, 3, 8), datetime.min.time(), UTC) + timedelta(hours=10)
    bit = datetime.combine(_pazar(y, 11, 1), datetime.min.time(), UTC) + timedelta(hours=9)
    return timedelta(hours=-7) if bas <= an_utc < bit else timedelta(hours=-8)


def _simdi(simdi=None) -> datetime:
    if simdi is None:
        return datetime.now(UTC)
    return simdi if simdi.tzinfo else simdi.replace(tzinfo=UTC)


def _pasifik(an) -> datetime:
    an = _simdi(an)
    tz = _pasifik_tz()
    if tz is not None:
        return an.astimezone(tz)
    return an.astimezone(timezone(_yedek_ofset(an)))


def pasifik_gunu(simdi=None) -> date:
    return _pasifik(simdi).date()


def sifirlanma_ani(simdi=None) -> datetime:
    """Bir sonraki Pasifik gece yarısı (UTC)."""
    yarin = pasifik_gunu(simdi) + timedelta(days=1)
    tz = _pasifik_tz()
    if tz is not None:
        return datetime(yarin.year, yarin.month, yarin.day, tzinfo=tz).astimezone(UTC)
    for saat in (-7, -8):
        aday = datetime(yarin.year, yarin.month, yarin.day, tzinfo=UTC) - timedelta(hours=saat)
        if _yedek_ofset(aday) == timedelta(hours=saat):
            return aday
    return datetime(yarin.year, yarin.month, yarin.day, tzinfo=UTC) + timedelta(hours=8)


def _tr_saati(an) -> datetime:
    """TR yerel saati: zoneinfo varsa Europe/Istanbul, yoksa UTC+3 (Türkiye
    2016'dan beri yaz saati uygulamıyor)."""
    try:
        from zoneinfo import ZoneInfo
        return an.astimezone(ZoneInfo("Europe/Istanbul"))
    except Exception:                                   # noqa: BLE001
        return an.astimezone(timezone(timedelta(hours=3)))


def _saat_eki(saat: int) -> str:
    """'10:00'da', '11:00'de', '13:00'te' — tam saatin okunuşuna göre."""
    ekler = {0: "da", 1: "de", 2: "de", 3: "te", 4: "te", 5: "te", 6: "da",
             7: "de", 8: "de", 9: "da"}
    if saat % 10 == 0:
        return {0: "da", 10: "da", 20: "de"}[saat]
    return ekler[saat % 10]


def _sure_metni(saniye) -> str:
    saniye = max(0, int(saniye))
    sa, dk = saniye // 3600, (saniye % 3600) // 60
    return "%d sa %d dk" % (sa, dk) if sa else "%d dk" % dk


# ---------------------------------------------------------------------------
# Defter
# ---------------------------------------------------------------------------

def defter_yolu(yol=None) -> str:
    """Açık yol > `YOUTUBE_KOTA_DEFTERI` > repo kökündeki gerçek defter.

    TEST KORUMASI (2026-09-13, üretimde yakalandı): `conftest.py`'nin
    `DURUM_DOSYASI` yönlendirmesi yalnız fixture anında YÜKLÜ modüllere
    uygulanıyor; bu modül çoğu testte `youtube_auth` içinden GEÇ yükleniyor.
    İlk gün başka bir test paketi gerçek deftere `elle:pytest` satırları
    yazdı (sahte `videos.insert` "tamam" dahil) — ölçümü kirletir, bir
    `thumbnails.set` 403'ü gerçek Studio listesine iş, sonraki saatlik koşuda
    gerçek Telegram mesajı demekti. `elle_islem._testte_gercek_defter` ile aynı
    desen: pytest içinde gerçek yol ASLA dönmez (Studio dosyası defterin
    yanında durduğu için o da kapsanır)."""
    if yol:
        return yol
    ortam = os.environ.get(ORTAM_DEGISKENI)
    if ortam:
        return ortam
    if os.environ.get("PYTEST_CURRENT_TEST") and (
            os.path.normcase(os.path.abspath(DURUM_DOSYASI))
            == os.path.normcase(os.path.join(REPO, "youtube_kota_defteri.jsonl"))):
        import tempfile
        klasor = os.path.join(tempfile.gettempdir(), "youtube_kota_pytest_%d" % os.getpid())
        try:
            os.makedirs(klasor, exist_ok=True)
        except OSError:
            pass
        return os.path.join(klasor, "youtube_kota_defteri.jsonl")
    return DURUM_DOSYASI


def _uyar_bir_kez(anahtar, mesaj):
    if anahtar in _UYARILDI:
        return
    _UYARILDI.add(anahtar)
    try:
        if sys.stderr is not None:                      # pythonw.exe: None
            sys.stderr.write("youtube_kota: %s\n" % mesaj)
    except Exception:                                   # noqa: BLE001
        pass


def _ts_oku(kayit):
    try:
        t = datetime.fromisoformat(str(kayit["ts"]))
        return t if t.tzinfo else t.replace(tzinfo=UTC)
    except Exception:                                   # noqa: BLE001
        return None


def _dondur(yol, simdi):
    """30 günden eski satırları at. Süreç başına dosya başına EN FAZLA bir kez,
    ve yalnız ilk satır gerçekten eskiyse (ucuz yol). Atomik: tmp + os.replace."""
    if yol in _DONDURULEN:
        return
    _DONDURULEN.add(yol)
    try:
        with open(yol, encoding="utf-8", errors="replace") as f:
            ilk = f.readline()
        try:
            ilk_ts = _ts_oku(json.loads(ilk))
        except ValueError:
            ilk_ts = None
        sinir = simdi - timedelta(days=SAKLAMA_GUN)
        if ilk_ts is not None and ilk_ts >= sinir:
            return
        with open(yol, encoding="utf-8", errors="replace") as f:
            satirlar = f.readlines()
        kalan = []
        for s in satirlar:
            try:
                t = _ts_oku(json.loads(s))
            except ValueError:
                continue
            if t is not None and t >= sinir:
                kalan.append(s if s.endswith("\n") else s + "\n")
        gecici = yol + ".tmp"
        with open(gecici, "w", encoding="utf-8", newline="") as f:
            f.writelines(kalan)
            f.flush()
            os.fsync(f.fileno())
        os.replace(gecici, yol)
    except FileNotFoundError:
        pass
    except Exception as e:                              # noqa: BLE001
        _uyar_bir_kez("dondur", "defter döndürülemedi: %s" % e)


def kaydet(metod, adet=1, basarili=True, kaynak="auto_process", proje=None,
           yol=None, hata=None, hedef=None, simdi=None) -> bool:
    """Bir API çağrısını deftere EKLER. Hiçbir koşulda istisna fırlatmaz."""
    try:
        an = _simdi(simdi)
        m = metod_adi(metod)
        birim, tahmin, kova = maliyet(m)
        adet = max(1, int(adet))
        if not basarili:
            ortak, tahmin = BASARISIZ_CAGRI_BIRIMI * adet, True
            insert = 0
        else:
            ortak = birim * adet
            insert = adet if kova == "insert" else 0
        kayit = {
            "ts": an.isoformat(timespec="seconds"),
            "pt_gun": pasifik_gunu(an).isoformat(),
            "metod": m,
            "adet": adet,
            "birim": ortak,
            "insert": insert,
            "kova": kova,
            "basarili": bool(basarili),
            "tahmin": bool(tahmin),
            "kaynak": kaynak,
            "proje": proje,
            "hedef": hedef,
            "hata": hata,
        }
        veri = (json.dumps(kayit, ensure_ascii=False) + "\n").encode("utf-8")
        hedef_yol = defter_yolu(yol)
        with _KILIT:
            _dondur(hedef_yol, an)
            # Tek os.write + O_APPEND: satır bölünmeden dosya sonuna eklenir.
            bayrak = os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_BINARY", 0)
            fd = os.open(hedef_yol, bayrak, 0o644)
            try:
                os.write(fd, veri)
            finally:
                os.close(fd)
        return True
    except Exception as e:                              # noqa: BLE001
        _uyar_bir_kez("kaydet", "deftere yazılamadı (çağrı etkilenmedi): %s" % e)
        return False


def kayitlar(yol=None):
    """Defterdeki geçerli kayıtlar (bozuk satır atlanır). Okunamazsa istisna."""
    sonuc = []
    with open(defter_yolu(yol), encoding="utf-8", errors="replace") as f:
        for s in f:
            try:
                k = json.loads(s)
            except ValueError:
                continue
            if isinstance(k, dict) and _ts_oku(k) is not None:
                sonuc.append(k)
    return sonuc


def _bugunkuler(yol=None, simdi=None):
    gun = pasifik_gunu(simdi)
    try:
        tum = kayitlar(yol)
        okundu = True
    except FileNotFoundError:
        tum, okundu = [], True
    except Exception:                                   # noqa: BLE001
        tum, okundu = [], False
    return [k for k in tum if pasifik_gunu(_ts_oku(k)) == gun], okundu


def bugunku_harcama(yol=None, simdi=None) -> dict:
    bugun, okundu = _bugunkuler(yol, simdi)
    return {
        "pasifik_gunu": pasifik_gunu(simdi).isoformat(),
        "ortak": sum(int(k.get("birim") or 0) for k in bugun),
        "insert": sum(int(k.get("insert") or 0) for k in bugun),
        "cagri": sum(int(k.get("adet") or 1) for k in bugun),
        "basarisiz": sum(int(k.get("adet") or 1) for k in bugun if not k.get("basarili", True)),
        "tahmin_iceren": any(k.get("tahmin") for k in bugun),
        "defter_okunabildi": okundu,
    }


def kalan(yol=None, simdi=None) -> int:
    return max(0, GUNLUK_HAVUZ - bugunku_harcama(yol, simdi)["ortak"])


def yeterli_mi(birim, yol=None, simdi=None) -> bool:
    return kalan(yol, simdi) >= int(birim)


# ---------------------------------------------------------------------------
# Koruma: YALNIZ toplu elle betikler
# ---------------------------------------------------------------------------

def toplu_izin(birim_basina, istenen, gunluk_sinir=None, zorla=False,
               yol=None, simdi=None) -> dict:
    """Toplu ELLE bir işin bugün kaç öğe yapabileceği.

    Üst sınır: bugünkü harcama + iş <= havuzun %60'ı (`--zorla` bu sınırı
    kaldırır) VE her durumda <= havuz - yayın rezervi (saatlik hattın yeni
    yayını için ayrılmış pay; `--zorla` bunu AŞAMAZ).
    `durdu=True` -> betik hiç API çağrısı yapmadan çıkmalı.
    `gunluk_sinir` verilirse iş, sığan kadarıyla (en fazla N) YAPILIR.
    """
    harcanan = bugunku_harcama(yol, simdi)["ortak"]
    rezerv = yayin_rezervi()
    esik = int(GUNLUK_HAVUZ * TOPLU_ESIK_ORANI)
    rezerv_tavani = GUNLUK_HAVUZ - rezerv
    ust = rezerv_tavani if zorla else min(esik, rezerv_tavani)
    birim_basina = max(0, int(birim_basina))
    istenen = max(0, int(istenen))
    sigan = istenen if birim_basina == 0 else max(0, (ust - harcanan) // birim_basina)
    izin = min(istenen, sigan)
    if gunluk_sinir is not None:
        izin = min(izin, max(0, int(gunluk_sinir)))
    tahmini = istenen * birim_basina
    asiyor = harcanan + tahmini > ust
    durdu = (asiyor and gunluk_sinir is None) or (istenen > 0 and izin == 0)
    ayrinti = ("bugün harcanan %d, bu iş ~%d birim (%d x %d), sınır %d "
               "(%s; yayın rezervi %d)" % (
                   harcanan, tahmini, istenen, birim_basina, ust,
                   "--zorla: yalnız rezerv" if zorla else "havuzun %%%d'ı" % int(TOPLU_ESIK_ORANI * 100),
                   rezerv))
    if durdu:
        mesaj = ("KOTA KORUMASI: Bugün en fazla %d öğe; kalanlar yarın. %s. "
                 "Devam için --gunluk-sinir %d (ya da eşiği aşmak için --zorla)."
                 % (izin, ayrinti, izin))
    elif izin < istenen:
        mesaj = "KOTA KORUMASI: Bugün en fazla %d öğe; kalanlar yarın. %s." % (izin, ayrinti)
    else:
        mesaj = "Kota kontrolü: tamam — %s." % ayrinti
    return {"izin": izin, "istenen": istenen, "harcanan": harcanan,
            "tahmini": tahmini, "ust": ust, "rezerv": rezerv,
            "durdu": durdu, "mesaj": mesaj}


# ---------------------------------------------------------------------------
# Studio bekleyen işleri
# ---------------------------------------------------------------------------

def studio_dosya_yolu(yol=None) -> str:
    """Varsayılan: defterin YANI (repo kökü). Defter testte geçici klasöre
    çekildiğinde (ortam değişkeni ya da conftest) bu dosya da oraya gider."""
    return (yol or os.environ.get(STUDIO_ORTAM_DEGISKENI)
            or os.path.join(os.path.dirname(os.path.abspath(defter_yolu())), STUDIO_DOSYA_ADI))


def _studio_oku(yol=None) -> dict:
    try:
        with open(studio_dosya_yolu(yol), encoding="utf-8") as f:
            veri = json.load(f)
        if not isinstance(veri, dict) or not isinstance(veri.get("isler"), list):
            raise ValueError("beklenmeyen biçim")
        return veri
    except FileNotFoundError:
        return {"surum": 1, "isler": []}
    except ValueError as e:
        _uyar_bir_kez("studio-bozuk", "Studio bekleyenler dosyası okunamadı: %s" % e)
        return {"surum": 1, "isler": []}


def _studio_yaz(veri, yol=None) -> None:
    """Atomik (`state_io._atomik_yaz` — yeni yazıcı YOK, CLAUDE.md)."""
    _repo_yolda()
    import state_io
    state_io._atomik_yaz(studio_dosya_yolu(yol), veri)


def studio_bekleyen_ekle(proje, video_id, is_turu, ayrinti, proje_yol=None,
                         dikey=None, kaynak=None, yol=None, simdi=None):
    """Studio'dan elle tamamlanabilecek bir işi kaydeder. Aynı (tür, video)
    zaten BEKLİYORSA yeni kayıt açılmaz; yalnız `son_gorulme` tazelenir.
    Döner: (id, yeni_mi)."""
    if is_turu not in STUDIO_IS_TURLERI:
        raise ValueError("geçersiz iş türü: %r (%s)" % (is_turu, ", ".join(STUDIO_IS_TURLERI)))
    an = _simdi(simdi)
    gun = pasifik_gunu(an).isoformat()
    with _KILIT:
        veri = _studio_oku(yol)
        for i in veri["isler"]:
            if (i.get("durum") == "bekliyor" and i.get("is_turu") == is_turu
                    and i.get("video_id") == video_id):
                i["son_gorulme_utc"] = an.isoformat(timespec="seconds")
                i["son_gorulme_pt_gun"] = gun
                i["gorulme"] = int(i.get("gorulme") or 1) + 1
                if ayrinti:
                    i["ayrinti"] = ayrinti
                _studio_yaz(veri, yol)
                return i["id"], False
        kimlik = "SB-" + hashlib.sha1(("%s|%s|%s" % (
            is_turu, video_id, an.isoformat())).encode("utf-8")).hexdigest()[:10]
        veri["isler"].append({
            "id": kimlik, "durum": "bekliyor", "is_turu": is_turu,
            "proje": proje, "proje_yol": proje_yol, "video_id": video_id,
            "dikey": dikey, "ayrinti": ayrinti, "kaynak": kaynak,
            "eklendi_utc": an.isoformat(timespec="seconds"), "eklendi_pt_gun": gun,
            "son_gorulme_utc": an.isoformat(timespec="seconds"), "son_gorulme_pt_gun": gun,
            "gorulme": 1,
        })
        _studio_yaz(veri, yol)
        return kimlik, True


def studio_bekleyenler(yol=None, tumu=False) -> list:
    isler = _studio_oku(yol)["isler"]
    return list(isler) if tumu else [i for i in isler if i.get("durum") == "bekliyor"]


def studio_bekleyen_tamamla(kimlik, kaynak, yol=None, simdi=None) -> bool:
    an = _simdi(simdi)
    with _KILIT:
        veri = _studio_oku(yol)
        for i in veri["isler"]:
            if i.get("id") == kimlik and i.get("durum") == "bekliyor":
                i["durum"] = "tamamlandi"
                i["tamamlandi_utc"] = an.isoformat(timespec="seconds")
                i["tamamlayan"] = kaynak
                _studio_yaz(veri, yol)
                return True
    return False


def _studio_guncelle(yol, alan, deger) -> None:
    with _KILIT:
        veri = _studio_oku(yol)
        veri[alan] = deger
        _studio_yaz(veri, yol)


def studio_isi_turu(metod, kaynak, parca=None):
    """quotaExceeded alan çağrı Studio işi mi? Gerekçe: modül docstring'i."""
    m = metod_adi(metod)
    if m == "thumbnails.set":
        return "kapak"
    if m == "videos.update":
        kaynak = str(kaynak or "")
        if not kaynak.startswith("elle:") or kaynak in KENDINI_DENEYEN_ELLE_KAYNAKLAR:
            return None
        return "gizlilik" if "status" in str(parca or "").split(",") else "video_update"
    return None


def _proje_bul(video_id):
    """(proje adı, klasör, dikey) — üç içerik kökündeki state.json'lardan."""
    try:
        _repo_yolda()
        import uyumluluk
        for klasor in uyumluluk.proje_klasorleri():
            try:
                with open(os.path.join(klasor, "state.json"), encoding="utf-8") as f:
                    st = json.load(f)
            except (OSError, ValueError):
                continue
            for anahtar, dikey in (("youtube_video_id", False),
                                   ("youtube_shorts_video_id", True),
                                   ("youtube_clip_video_id", True)):
                if isinstance(st, dict) and st.get(anahtar) == video_id:
                    return os.path.basename(klasor), klasor, dikey
    except Exception:                                   # noqa: BLE001
        pass
    return None, None, None


def _studio_isi_kaydet(istek) -> None:
    kaynak = kaynak_tespit()
    m = metod_adi(istek.methodId)
    parca = (parse_qs(urlparse(istek.uri).query).get("part") or [""])[0]
    tur = studio_isi_turu(m, kaynak, parca)
    if not tur:
        return
    govde = {}
    if tur != "kapak" and isinstance(istek.body, (str, bytes)):
        try:
            govde = json.loads(istek.body)
        except ValueError:
            govde = {}
    video_id = _hedef(istek.uri) or (govde.get("id") if isinstance(govde, dict) else None)
    if not video_id:
        return
    proje, proje_yol, dikey = _proje_bul(video_id)
    if tur == "kapak":
        ayrinti = {True: "Shorts kapağı", False: "uzun format kapağı"}.get(dikey, "kapak")
    elif tur == "gizlilik":
        ayrinti = "gizlilik → %s" % ((govde.get("status") or {}).get("privacyStatus") or "?")
    else:
        ayrinti = "videos.update (part=%s)" % parca
    studio_bekleyen_ekle(proje, video_id, tur, ayrinti, proje_yol=proje_yol,
                         dikey=dikey, kaynak=kaynak)


def _is_satiri(i) -> str:
    return "%s — %s: %s [%s]" % (i.get("proje") or i.get("video_id"), i.get("is_turu"),
                                 i.get("ayrinti") or "", i.get("id"))


def studio_bildirim_metni(bekleyen, simdi=None) -> str:
    an = _simdi(simdi)
    sifir = _tr_saati(sifirlanma_ani(an))
    return ("YouTube kotası bitti. Studio'dan tamamlanabilecek %d iş:\n%s\n"
            "Tamamlatmak için Claude Code oturumunda 'Studio işlerini Chrome'dan "
            "tamamla' yaz. Kota TR %s'%s sıfırlanır; kapak işleri yükleme adımında "
            "kendiliğinden yeniden denenmez (saatlik hat sıfırlanmadan sonra günde "
            "en fazla %d kapağı API ile dener)." % (
                len(bekleyen), "\n".join("• " + _is_satiri(i) for i in bekleyen),
                sifir.strftime("%H:%M"), _saat_eki(sifir.hour), KAPAK_TELAFI_GUNLUK))


def studio_bildirimi(simdi=None, yol=None, gonder=None):
    """Pasifik günü başına EN FAZLA bir mesaj; yalnız BUGÜN kotaya takılmış
    (son_gorulme bugün) bir iş varsa. Tekrar önleme: sha1(gün + iş kimlikleri).
    Gönderim başarısızsa damga YAZILMAZ (sonraki koşu yeniden dener).
    Döner: 'gonderildi' | 'gonderilemedi' | None."""
    an = _simdi(simdi)
    gun = pasifik_gunu(an).isoformat()
    veri = _studio_oku(yol)
    bekleyen = [i for i in veri["isler"] if i.get("durum") == "bekliyor"]
    if not any(i.get("son_gorulme_pt_gun") == gun for i in bekleyen):
        return None
    damga = veri.get("bildirim") or {}
    ozet_sha = hashlib.sha1(("%s|%s" % (gun, ",".join(sorted(i["id"] for i in bekleyen))))
                            .encode("utf-8")).hexdigest()
    if damga.get("pt_gun") == gun or damga.get("sha1") == ozet_sha:
        return None
    metin = studio_bildirim_metni(bekleyen, an)
    if gonder is None:
        _repo_yolda()
        import notify
        tamam = notify.send("YouTube Studio işleri bekliyor", metin)
    else:
        tamam = gonder("YouTube Studio işleri bekliyor", metin)
    if not tamam:
        return "gonderilemedi"
    _studio_guncelle(yol, "bildirim", {"pt_gun": gun, "sha1": ozet_sha,
                                       "gonderildi_utc": an.isoformat(timespec="seconds"),
                                       "is_sayisi": len(bekleyen)})
    return "gonderildi"


def _varsayilan_kapak_yukle(servis, video_id, proje_yol, vertical=False):
    import youtube_upload as yu
    kapak = (yu._find_cover_vertical if vertical else yu._find_cover)(proje_yol)
    if not kapak:
        # upload_thumbnail kapak yoksa SESSİZCE döner; iş yanlışlıkla kapanmasın.
        raise RuntimeError("kapak dosyası bulunamadı: %s" % proje_yol)
    yu.upload_thumbnail(servis, video_id, proje_yol, vertical=vertical)


def kapak_telafisi(simdi=None, yol=None, servis=None, yukle=None, log=print) -> dict:
    """Kota SIFIRLANDIKTAN sonra (işin son görüldüğü Pasifik günü < bugün)
    bekleyen kapak işlerini API ile dener. Günde EN FAZLA KAPAK_TELAFI_GUNLUK
    DENEME (başarı değil — kota güvenliği); her denemeden önce yeterli_mi(50).
    Golden-hour kısıtı YOK (kapak yayın değil). Başarılıysa kayıt kapanır."""
    an = _simdi(simdi)
    gun = pasifik_gunu(an).isoformat()
    sonuc = {"denenen": 0, "tamamlanan": 0, "aday": 0, "sebep": None}
    veri = _studio_oku(yol)
    adaylar = [i for i in veri["isler"]
               if i.get("durum") == "bekliyor" and i.get("is_turu") == "kapak"
               and i.get("proje_yol") and i.get("video_id")
               and (i.get("son_gorulme_pt_gun") or i.get("eklendi_pt_gun") or gun) < gun]
    sonuc["aday"] = len(adaylar)
    if not adaylar:
        sonuc["sebep"] = "aday yok"
        return sonuc
    telafi = veri.get("telafi") or {}
    yapilan = int(telafi.get("adet") or 0) if telafi.get("pt_gun") == gun else 0
    for is_ in adaylar:
        if yapilan >= KAPAK_TELAFI_GUNLUK:
            sonuc["sebep"] = "günlük sınır (%d)" % KAPAK_TELAFI_GUNLUK
            break
        if not yeterli_mi(KAPAK_BIRIMI, simdi=an):
            sonuc["sebep"] = "kota yetersiz"
            break
        yapilan += 1
        _studio_guncelle(yol, "telafi", {"pt_gun": gun, "adet": yapilan})
        sonuc["denenen"] += 1
        etiket = "%s — %s" % (is_.get("proje") or "?", is_["video_id"])
        try:
            if servis is None:
                from youtube_auth import get_authenticated_service
                servis = get_authenticated_service()
            (yukle or _varsayilan_kapak_yukle)(servis, is_["video_id"], is_["proje_yol"],
                                               vertical=bool(is_.get("dikey")))
        except Exception as e:                          # noqa: BLE001
            log("  Kapak telafisi HATA (%s): %s" % (etiket, str(e)[:200]))
            if "quotaexceeded" in str(e).lower():
                sonuc["sebep"] = "quotaExceeded"
                break
            continue
        studio_bekleyen_tamamla(is_["id"], "auto_process:api", yol=yol, simdi=an)
        sonuc["tamamlanan"] += 1
        log("  Kapak telafisi: tamam (%s) — Studio işi %s kapandı" % (etiket, is_["id"]))
    return sonuc


def kosu_sonu(log=print, simdi=None) -> None:
    """`auto_process.main()` finally'sinin son adımı. ASLA istisna fırlatmaz.
    Sıra: kapak telafisi -> Studio bildirimi (kapananlar mesaja girmesin) ->
    kota satırı (telafinin harcamasını da göstersin)."""
    def _yaz(metin):
        try:
            log(metin)
        except Exception:                               # noqa: BLE001
            pass

    try:
        s = kapak_telafisi(simdi=simdi, log=_yaz)
        if s.get("aday") and not s.get("denenen"):
            _yaz("  Kapak telafisi bekliyor: %d aday (%s)" % (s["aday"], s.get("sebep")))
    except Exception as e:                              # noqa: BLE001
        _yaz("  YouTube kapak telafisi HATA: %s" % e)
    try:
        b = studio_bildirimi(simdi=simdi)
        if b:
            _yaz("  YouTube Studio bekleyen işleri bildirimi: %s" % b)
    except Exception as e:                              # noqa: BLE001
        _yaz("  YouTube Studio bildirimi HATA: %s" % e)
    _yaz(saglik_satiri(simdi=simdi))


# ---------------------------------------------------------------------------
# Görünürlük
# ---------------------------------------------------------------------------

def saglik_satiri(yol=None, simdi=None) -> str:
    """Tek satır. `auto_process.main()` finally'si ve (ileride) saglik_kontrol."""
    try:
        an = _simdi(simdi)
        h = bugunku_harcama(yol, an)
        kalan_birim = max(0, GUNLUK_HAVUZ - h["ortak"])
        satir = "YouTube kota: bugün %d/%d (insert %d/%d), sıfırlanma %s sonra" % (
            h["ortak"], GUNLUK_HAVUZ, h["insert"], INSERT_GUNLUK_CAGRI,
            _sure_metni((sifirlanma_ani(an) - an).total_seconds()))
        rezerv = yayin_rezervi()
        if not h["defter_okunabildi"]:
            satir += " — UYARI: defter okunamadı (%s)" % defter_yolu(yol)
        if kalan_birim < rezerv:
            satir += (" — UYARI: kalan %d < yayın rezervi %d (kapak/playlist/altyazı "
                      "403 alabilir; yükleme ayrı kovada)" % (kalan_birim, rezerv))
        if h["basarisiz"]:
            satir += " — başarısız çağrı %d" % h["basarisiz"]
        try:
            n = len(studio_bekleyenler())
            if n:
                satir += " — Studio'da bekleyen %d iş (youtube_kota.py studio-bekleyenler)" % n
        except Exception:                               # noqa: BLE001
            pass
        return satir
    except Exception as e:                              # noqa: BLE001
        return "YouTube kota: hesaplanamadı (%s)" % e


def ozet(yol=None, simdi=None) -> dict:
    an = _simdi(simdi)
    bugun, okundu = _bugunkuler(yol, an)
    h = bugunku_harcama(yol, an)
    sifir = sifirlanma_ani(an)
    metodlar, kaynaklar = {}, {}
    for k in bugun:
        for tablo, anahtar in ((metodlar, k.get("metod")), (kaynaklar, k.get("kaynak"))):
            s = tablo.setdefault(str(anahtar), {"cagri": 0, "birim": 0, "insert": 0, "basarisiz": 0})
            adet = int(k.get("adet") or 1)
            s["cagri"] += adet
            s["birim"] += int(k.get("birim") or 0)
            s["insert"] += int(k.get("insert") or 0)
            if not k.get("basarili", True):
                s["basarisiz"] += adet
    try:
        studio_sayisi = len(studio_bekleyenler())
    except Exception:                                   # noqa: BLE001
        studio_sayisi = None
    return {
        "surum": 1,
        "olusturma_utc": an.isoformat(timespec="seconds"),
        "pasifik_gunu": h["pasifik_gunu"],
        "ortak": {"harcanan": h["ortak"], "limit": GUNLUK_HAVUZ,
                  "kalan": max(0, GUNLUK_HAVUZ - h["ortak"])},
        "insert": {"cagri": h["insert"], "limit": INSERT_GUNLUK_CAGRI},
        "sifirlanma": {"utc": sifir.isoformat(timespec="seconds"),
                       "yerel": sifir.astimezone().isoformat(timespec="seconds"),
                       "kalan_sn": int((sifir - an).total_seconds()),
                       "kalan_metin": _sure_metni((sifir - an).total_seconds())},
        "metodlar": dict(sorted(metodlar.items(), key=lambda x: -x[1]["birim"])),
        "kaynaklar": dict(sorted(kaynaklar.items(), key=lambda x: -x[1]["birim"])),
        "basarisiz_cagri": h["basarisiz"],
        "tahmin_iceren": h["tahmin_iceren"],
        "yayin_rezervi": yayin_rezervi(),
        "toplu_esik": int(GUNLUK_HAVUZ * TOPLU_ESIK_ORANI),
        "studio_bekleyen": studio_sayisi,
        "defter": defter_yolu(yol),
        "defter_okunabildi": okundu,
        "saglik_satiri": saglik_satiri(yol, an),
        "not": "Yalnız bu depodan yapılan çağrılar görülür (alt sınır).",
    }


# ---------------------------------------------------------------------------
# Merkezi yakalama
# ---------------------------------------------------------------------------

def kaynak_tespit() -> str:
    """Çağıran betik. Zamanlayıcı görevleri `pythonw.exe` ile koşuyor
    (setup_task_scheduler.ps1); aynı betik konsoldan koşarsa 'elle:'."""
    try:
        ana = sys.modules.get("__main__")
        dosya = getattr(ana, "__file__", None) or (sys.argv[0] if sys.argv else "")
        ad = os.path.splitext(os.path.basename(dosya or ""))[0] or "-c"
        if ad == "__main__":
            ad = os.path.basename(os.path.dirname(dosya)) or ad
        pythonw = os.path.basename(sys.executable or "").lower().startswith("pythonw")
        if ad in ZAMANLANMIS_BETIKLER and pythonw:
            return ad
        return "elle:" + ad
    except Exception:                                   # noqa: BLE001
        return "bilinmiyor"


def _hata_nedeni(e) -> str:
    try:
        govde = e.content.decode("utf-8", "replace") if isinstance(e.content, bytes) else str(e.content)
        return json.loads(govde)["error"]["errors"][0]["reason"]
    except Exception:                                   # noqa: BLE001
        return "http_%s" % getattr(getattr(e, "resp", None), "status", "?")


def _hedef(uri):
    try:
        q = parse_qs(urlparse(uri).query)
        for anahtar in ("videoId", "id", "playlistId"):
            if q.get(anahtar):
                return q[anahtar][0][:120]
    except Exception:                                   # noqa: BLE001
        pass
    return None


try:
    from googleapiclient.errors import HttpError as _HttpError
    from googleapiclient.http import HttpRequest as _HttpRequest
except Exception:                                       # noqa: BLE001
    _HttpRequest = None
    KotaliHttpRequest = None
else:
    class KotaliHttpRequest(_HttpRequest):
        """`build(..., requestBuilder=KotaliHttpRequest)`. Davranış AYNI;
        yalnız sonuç deftere yazılır. Hiçbir çağrıyı ENGELLEMEZ."""

        def _kaydet(self, basarili, hata=None):
            try:
                neden = _hata_nedeni(hata) if hata is not None else None
                kaydet(metod_adi(self.methodId), basarili=basarili,
                       kaynak=kaynak_tespit(), hedef=_hedef(self.uri), hata=neden)
                if neden == "quotaExceeded":
                    _studio_isi_kaydet(self)
            except Exception:                           # noqa: BLE001
                pass

        def execute(self, http=None, num_retries=0):
            if self.resumable:
                # Üst sınıf next_chunk'ı döngüde çağırıyor; kayıt orada.
                return super().execute(http=http, num_retries=num_retries)
            try:
                sonuc = super().execute(http=http, num_retries=num_retries)
            except _HttpError as e:
                self._kaydet(False, e)
                raise
            self._kaydet(True)
            return sonuc

        def next_chunk(self, http=None, num_retries=0):
            try:
                durum, govde = super().next_chunk(http=http, num_retries=num_retries)
            except _HttpError as e:
                self._kaydet(False, e)
                raise
            if govde is not None:
                self._kaydet(True)
            return durum, govde


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

ELLE_ISLEM_ORNEGI = (
    "Tamamlanan her iş için elle işlemler defterine de yaz, örn.:\n"
    "  python elle_islem.py ekle --platform youtube --proje \"Sabah Senin\" "
    "--islem kapak_degistirdi --ayrinti \"Studio'dan kapak yüklendi (SB-...)\" "
    "--kaynak claude\n"
    "İş türü -> --islem: kapak=kapak_degistirdi, playlist=oynatma_listesi, "
    "gizlilik=gizlilik_degistirdi, video_update=duzenledi; Shorts için "
    "--platform youtube_shorts.")


def _elle_islem_satiri(i, kaynak) -> str:
    return ("python elle_islem.py ekle --platform %s --proje \"%s\" --islem %s "
            "--ayrinti \"Studio'dan %s (%s)\" --kaynak %s" % (
                "youtube_shorts" if i.get("dikey") else "youtube",
                i.get("proje") or "", ELLE_ISLEM_ESLEMESI.get(i.get("is_turu"), "diger"),
                i.get("ayrinti") or i.get("is_turu"), i.get("id"), kaynak))


def _yazdir_ozet(o):
    print(o["saglik_satiri"])
    print("Pasifik günü %s — kalan %d birim; sıfırlanma %s (yerel)" % (
        o["pasifik_gunu"], o["ortak"]["kalan"], o["sifirlanma"]["yerel"]))
    print("Metod kırılımı:")
    for ad, s in o["metodlar"].items():
        print("  %-24s %5d çağrı %6d birim%s" % (
            ad, s["cagri"], s["birim"], ("  (başarısız %d)" % s["basarisiz"]) if s["basarisiz"] else ""))
    print("Kaynak kırılımı:")
    for ad, s in o["kaynaklar"].items():
        print("  %-24s %5d çağrı %6d birim" % (ad, s["cagri"], s["birim"]))
    if o["tahmin_iceren"]:
        print("Not: tahmini maliyet içeriyor (captions.download / başarısız çağrı).")
    if not o["defter_okunabildi"]:
        print("UYARI: defter okunamadı: %s" % o["defter"])


def main(argv=None) -> int:
    for akis in (sys.stdout, sys.stderr):
        try:
            akis.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="YouTube Data API kota defteri",
                                 epilog=ELLE_ISLEM_ORNEGI,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--defter", default=None, help="defter yolu (varsayılan: repo kökü)")
    alt = ap.add_subparsers(dest="komut")
    o = alt.add_parser("ozet", help="bugünün özeti")
    o.add_argument("--json", action="store_true")
    s = alt.add_parser("son", help="son kayıtlar")
    s.add_argument("--adet", type=int, default=20)
    sb = alt.add_parser("studio-bekleyenler", help="Studio'dan tamamlanabilecek işler",
                        epilog=ELLE_ISLEM_ORNEGI,
                        formatter_class=argparse.RawDescriptionHelpFormatter)
    sb.add_argument("--json", action="store_true")
    sb.add_argument("--tumu", action="store_true", help="tamamlananlar dahil")
    st = alt.add_parser("studio-tamamla", help="elle yapılan bir işi kapat",
                        epilog=ELLE_ISLEM_ORNEGI,
                        formatter_class=argparse.RawDescriptionHelpFormatter)
    st.add_argument("kimlik")
    st.add_argument("--kaynak", default="claude")
    args = ap.parse_args(argv)

    if args.komut == "son":
        try:
            son = kayitlar(args.defter)[-max(0, args.adet):]
        except FileNotFoundError:
            son = []
        for k in son:
            print("%s %-22s %5s birim  %-8s %s%s" % (
                k.get("ts"), k.get("metod"), k.get("birim"),
                "tamam" if k.get("basarili", True) else "HATA",
                k.get("kaynak"), ("  " + str(k.get("hata"))) if k.get("hata") else ""))
        return 0
    if args.komut == "studio-bekleyenler":
        isler = studio_bekleyenler(tumu=args.tumu)
        if args.json:
            print(json.dumps(isler, ensure_ascii=True, indent=2))
        else:
            if not isler:
                print("Studio'da bekleyen iş yok.")
            for i in isler:
                print("%s  %s" % (i.get("durum"), _is_satiri(i)))
        return 0
    if args.komut == "studio-tamamla":
        eslesen = [i for i in studio_bekleyenler() if i.get("id") == args.kimlik]
        if not eslesen or not studio_bekleyen_tamamla(args.kimlik, args.kaynak):
            print("Bekleyen iş bulunamadı: %s" % args.kimlik)
            return 1
        print("Tamamlandı: %s" % _is_satiri(eslesen[0]))
        print("Elle işlemler defterine de yaz:")
        print("  " + _elle_islem_satiri(eslesen[0], args.kaynak))
        return 0
    veri = ozet(args.defter)
    if args.komut == "ozet" and args.json:
        # ASCII: cp1254 konsolda ve başka ajanların okumasında kodlama derdi yok.
        print(json.dumps(veri, ensure_ascii=True, indent=2))
    else:
        _yazdir_ozet(veri)
    return 0


if __name__ == "__main__":
    sys.exit(main())
