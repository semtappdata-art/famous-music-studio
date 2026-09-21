# -*- coding: utf-8 -*-
"""Elle işlemler defteri — otomasyonun DIŞINDA yapılan işlerin TEK kaydı.

    python elle_islem.py ekle --platform tiktok --proje "Sabah Senin" \
        --islem yayinladi --ayrinti "telefondan yayınladım"
    python elle_islem.py listele --gun 7 [--json]
    python elle_islem.py ozet --gun 1 [--json]
    python elle_islem.py backfill            # KURU: hiçbir şey yazmaz
    python elle_islem.py backfill --uygula   # yalnız DEFTERE yazar, state'e ASLA
    python elle_islem.py sozluk              # geçerli platform / işlem anahtarları

NEDEN VAR (2026-09-13, kullanıcı isteği: "otomasyon verilerine elle yapılan tüm
işlemleri de dahil et"): TikTok taslağını telefondan yayınlamak, Studio'dan
gizlilik değiştirmek, Instagram'da arşivlemek, bir projeyi bekletmeye almak...
bunlar ya hiç kaydedilmiyordu ya da dağınık yerlerde duruyordu (`*_kaynak`
metinleri, CLAUDE.md kararları, denetim belgeleri). Raporlar, pano ve sesli
asistan bu yüzden bu işleri GÖREMİYORDU.

SÖZLEŞME (pano ve Hermes aynı biçimi okuyor — değiştirme):
  * Dosya `elle_islemler.jsonl` (repo kökü), UTF-8, satır başına bir JSON nesnesi.
  * Alanlar: id ("EI-YYYYMMDD-HHMMSS-xxxx"), zaman (ISO 8601, +03:00; işlemin
    gerçekleştiği an), zaman_yaklasik (bool), kayit_zamani, platform, proje
    (klasör adı | null), islem (aşağıdaki SÖZLÜK), ayrinti, kaynak
    (telegram|pano|claude|backfill|cli), kanit (| null), state_etkisi (| null).
  * Ekleme: dosya kilidi altında oku -> tekrar kontrolü -> TEK `os.write` ile
    tüm satır (O_APPEND). İki yazıcı aynı anda satır bozamaz.
  * Tekrar koruması: (platform, proje, islem, zaman ±10 dk) eşleşirse yeni
    satır YAZILMAZ, "zaten_kayitli" döner.

STATE'E YANSITMA — yalnız GÜVENLİ ve açıkça tanımlı eşlemeler:
  * tiktok + yayinladi -> MEVCUT `tiktok_publish_plan.isaretle_yayinlandi(kaynak=...)`
    (yeni yazma yolu yok). `build_plan` `hazir=False` diyorsa RED: ne state ne
    defter yazılır (Telegram onayındaki kuralın aynısı).
  * youtube / youtube_shorts + gizlilik_degistirdi / liste_disi_yapti ->
    `<onek>_elle_gizlilik_notu` NOT alanı. `*_privacy` (istenen; latest_release,
    geri doldurmalar ona bağlı) ve `*_privacy_gercek` (youtube_stats'ın API
    ÖLÇÜMÜ; kayma dedektörü onu okuyor) YAZILMAZ: bir beyan ölçüm değildir.
  * Diğer her şey yalnız deftere.
  Otomatik doğrulama (`tiktok_yayin_dogrulama`, PUBLISH_COMPLETE) deftere
  YAZMAZ — otomasyonun işi; ama özetlerde "elle yayınlandı (API ile doğrulandı)"
  olarak görünür (`api_dogrulanan_tiktok`).

ÜÇ SORU (CLAUDE.md):
  1. Kim çağırıyor? — kullanıcı/asistan CLI (`ekle`), Hermes becerisi
     `.hermes/skills/elle-islem-kaydi`, `upload/tiktok_yayin_onayi.onayla`
     (başarılı işarette, kaynak=telegram); okuyanlar
     `weekly_report.gunluk_izlenme_raporu` / `_haftalik_satirlar` ve
     `saglik_kontrol.elle_islemler_defteri`.
  2. Hangi zamanlayıcı? — yazma tarafında YOK (olgunun kaynağı insan); okuma
     saatlik `auto_process.main()` finally -> saglik_kontrol + weekly_report.
  3. Çalışmadığını nasıl anlarız? — bozuk satır saatlik sağlık kontrolünde
     UYARI; testler `tests/test_elle_islem.py`.

TEST KORUMASI: `PYTEST_CURRENT_TEST` ortamında GERÇEK deftere yazma REDDEDİLİR
ve gerçek defter boş okunur. Testler yolu `yol=` parametresiyle ya da
`ELLE_ISLEMLER_DEFTERI` ortam değişkeniyle verir (conftest'e dokunmadan).
"""

import argparse
import contextlib
import datetime
import json
import os
import re
import secrets
import sys
import time
import unicodedata

REPO = os.path.dirname(os.path.abspath(__file__))
UPLOAD = os.path.join(REPO, "upload")

DEFTER_ADI = "elle_islemler.jsonl"
GERCEK_DEFTER_YOLU = os.path.join(REPO, DEFTER_ADI)
ORTAM_DEGISKENI = "ELLE_ISLEMLER_DEFTERI"

TZ = datetime.timezone(datetime.timedelta(hours=3))
TEKRAR_PENCERESI_SN = 10 * 60
GELECEK_TOLERANSI_SN = 60 * 60
KILIT_BEKLEME_SN = 15.0
KILIT_BAYAT_SN = 120.0

PLATFORMLAR = ("youtube", "youtube_shorts", "tiktok", "instagram", "facebook",
               "telegram", "bluesky", "suno", "site", "diger")
PLATFORM_ADLARI = {
    "youtube": "YouTube", "youtube_shorts": "YouTube Shorts", "tiktok": "TikTok",
    "instagram": "Instagram", "facebook": "Facebook", "telegram": "Telegram",
    "bluesky": "Bluesky", "suno": "Suno", "site": "Site", "diger": "Diğer",
}

# KONTROLLÜ SÖZLÜK — anahtar: kısa fiil, değer: rapordaki Türkçe karşılığı.
# Yeni anahtar eklemek sözleşme değişikliğidir (pano da okuyor).
ISLEMLER = {
    "yayinladi": "yayınladı",
    "gizlilik_degistirdi": "gizliliği değiştirdi",
    "liste_disi_yapti": "liste dışı yaptı",
    "arsivledi": "arşivledi",
    "sildi": "sildi",
    "kapak_degistirdi": "kapağı değiştirdi",
    "oynatma_listesi": "oynatma listesini düzenledi",
    "telif_itirazi": "telif itirazı",
    "bekletmeye_aldi": "bekletmeye aldı",
    "bekletmeden_cikardi": "bekletmeden çıkardı",
    "uretti": "üretti",
    "secti": "seçti",
    "profil_linki": "profil linkini değiştirdi",
    "yorum_yaniti": "yorum yanıtladı",
    "duzenledi": "düzenledi",
    "kontrol_etti": "elle kontrol etti",
    "diger": "diğer",
    # 2026-09-13 TikTok web planlama (upload/tiktok_web.py isaretle) — yalnız Claude/CLI yazar.
    "planladi": "planladı",
}
KAYNAKLAR = ("telegram", "pano", "claude", "backfill", "cli")
GIZLILIK_DEGERLERI = ("public", "unlisted", "private")
ZORUNLU_ALANLAR = ("id", "zaman", "platform", "islem", "kaynak")
API_ETIKETI = "elle yayınlandı (API ile doğrulandı)"


class ElleIslemHatasi(ValueError):
    """Doğrulama ya da yazma reddi — mesaj kullanıcıya olduğu gibi gösterilir."""


# --------------------------------------------------------------------------
# Yol ve test koruması
# --------------------------------------------------------------------------

def defter_yolu(yol=None) -> str:
    """Açık yol > `ELLE_ISLEMLER_DEFTERI` > repo kökündeki gerçek defter."""
    if yol:
        return os.path.abspath(yol)
    ortam = os.environ.get(ORTAM_DEGISKENI)
    if ortam:
        return os.path.abspath(ortam)
    return GERCEK_DEFTER_YOLU


def _testte_gercek_defter(yol: str) -> bool:
    return bool(os.environ.get("PYTEST_CURRENT_TEST")) and (
        os.path.normcase(os.path.abspath(yol))
        == os.path.normcase(os.path.abspath(GERCEK_DEFTER_YOLU)))


# --------------------------------------------------------------------------
# Zaman
# --------------------------------------------------------------------------

def _iso(dt: datetime.datetime) -> str:
    return dt.astimezone(TZ).replace(microsecond=0).isoformat()


def zaman_ts(deger):
    """ISO metni -> epoch. Saat dilimsizse +03:00 sayılır. Okunamazsa None."""
    if not isinstance(deger, str) or not deger.strip():
        return None
    try:
        dt = datetime.datetime.fromisoformat(deger.strip())
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)
    return dt.timestamp()


def zaman_coz(deger=None, simdi=None) -> tuple:
    """(iso, yaklasik_mi). Yalnız tarih verilirse 12:00 + yaklaşık."""
    if deger is None or (isinstance(deger, str) and not deger.strip()):
        t = simdi if simdi is not None else time.time()
        return _iso(datetime.datetime.fromtimestamp(t, TZ)), False
    if not isinstance(deger, str):
        raise ElleIslemHatasi("zaman metin olmalı (ISO 8601), gelen: %r" % (deger,))
    s = deger.strip()
    yaklasik = False
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        s += "T12:00:00"
        yaklasik = True
    try:
        dt = datetime.datetime.fromisoformat(s)
    except ValueError:
        raise ElleIslemHatasi(
            "zaman okunamadı: %r — biçim ör. 2026-09-13T14:30 ya da "
            "2026-09-13T14:30:00+03:00 (yalnız tarih de olur)" % deger)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)
    return _iso(dt), yaklasik


# --------------------------------------------------------------------------
# Proje
# --------------------------------------------------------------------------

def _nfc(metin) -> str:
    return unicodedata.normalize("NFC", str(metin))


def _proje_klasorleri(proje_klasorleri=None) -> list:
    if proje_klasorleri is not None:
        return list(proje_klasorleri)
    import uyumluluk
    return list(uyumluluk.proje_klasorleri())


def proje_coz(proje, proje_klasorleri=None) -> tuple:
    """(klasör_adı, tam_yol) ya da (None, None). Olmayan proje -> hata."""
    if proje is None or (isinstance(proje, str) and not proje.strip()):
        return None, None
    ad = _nfc(os.path.basename(os.path.normpath(str(proje).strip())))
    for yol in _proje_klasorleri(proje_klasorleri):
        if _nfc(os.path.basename(os.path.normpath(yol))) == ad:
            return ad, yol
    raise ElleIslemHatasi(
        "proje bulunamadı: %r — projects/, dj_sets/, derlemeler/ altındaki bir "
        "KLASÖR adı olmalı (projeyle ilgili değilse proje verme)" % proje)


def _state_oku(proje_yol: str) -> dict:
    try:
        with open(os.path.join(proje_yol, "state.json"), "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _state_oku_kesin(proje_yol: str) -> dict:
    """Yazmadan önce: okunamıyorsa YAZMA (üstüne `{}` yazmak kaydı silerdi)."""
    yol = os.path.join(proje_yol, "state.json")
    try:
        with open(yol, "r", encoding="utf-8") as f:
            d = json.load(f)
    except FileNotFoundError:
        raise ElleIslemHatasi("state.json yok: %s — state notu yazılamadı" % yol)
    except (OSError, ValueError) as e:
        raise ElleIslemHatasi("state.json okunamadı (%s) — üstüne yazılmadı: %s"
                              % (type(e).__name__, yol))
    if not isinstance(d, dict):
        raise ElleIslemHatasi("state.json bir sözlük değil: %s" % yol)
    return d


# --------------------------------------------------------------------------
# Okuma
# --------------------------------------------------------------------------

def _satir_hatasi(k) -> str:
    if not isinstance(k, dict):
        return "JSON nesnesi değil"
    eksik = [a for a in ZORUNLU_ALANLAR if not k.get(a)]
    if eksik:
        return "eksik alan: " + ", ".join(eksik)
    if k.get("platform") not in PLATFORMLAR:
        return "geçersiz platform: %s" % k.get("platform")
    if k.get("islem") not in ISLEMLER:
        return "sözlük dışı işlem: %s" % k.get("islem")
    if zaman_ts(k.get("zaman")) is None:
        return "zaman okunamadı"
    return ""


def oku(yol=None) -> tuple:
    """(kayitlar, bozuk). Bozuk satır okumayı DURDURMAZ, yalnız listelenir.

    bozuk: [{"satir": n, "hata": metin}]. Dosya yoksa ([], []).
    """
    yol = defter_yolu(yol)
    if _testte_gercek_defter(yol):
        return [], []
    kayitlar, bozuk = [], []
    try:
        with open(yol, "rb") as f:
            ham = f.read()
    except FileNotFoundError:
        return [], []
    for no, satir in enumerate(ham.split(b"\n"), 1):
        if not satir.strip():
            continue
        try:
            k = json.loads(satir.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as e:
            bozuk.append({"satir": no, "hata": "JSON okunamadı (%s)" % type(e).__name__})
            continue
        hata = _satir_hatasi(k)
        if hata:
            bozuk.append({"satir": no, "hata": hata})
            continue
        kayitlar.append(k)
    return kayitlar, bozuk


# --------------------------------------------------------------------------
# Yazma
# --------------------------------------------------------------------------

@contextlib.contextmanager
def _kilit(yol: str):
    """Komşu `.kilit` dosyasıyla süreçler arası kilit (O_CREAT|O_EXCL)."""
    kilit = yol + ".kilit"
    klasor = os.path.dirname(kilit)
    if klasor:
        os.makedirs(klasor, exist_ok=True)
    bitis = time.monotonic() + KILIT_BEKLEME_SN
    while True:
        try:
            fd = os.open(kilit, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            try:
                os.write(fd, str(os.getpid()).encode("ascii"))
            finally:
                os.close(fd)
            break
        except (FileExistsError, PermissionError):
            try:
                if time.time() - os.path.getmtime(kilit) > KILIT_BAYAT_SN:
                    os.remove(kilit)
                    continue
            except OSError:
                pass
            if time.monotonic() > bitis:
                raise ElleIslemHatasi("defter kilidi alınamadı (%s) — başka bir "
                                      "yazıcı takılı kalmış olabilir" % kilit)
            time.sleep(0.02)
    try:
        yield
    finally:
        try:
            os.remove(kilit)
        except OSError:
            pass


def _satir_ekle(yol: str, kayit: dict) -> None:
    veri = (json.dumps(kayit, ensure_ascii=False) + "\n").encode("utf-8")
    try:
        with open(yol, "rb") as f:
            f.seek(0, os.SEEK_END)
            if f.tell() > 0:
                f.seek(-1, os.SEEK_END)
                if f.read(1) != b"\n":
                    veri = b"\n" + veri      # yarım kalmış satıra yapışma
    except FileNotFoundError:
        pass
    klasor = os.path.dirname(yol)
    if klasor:
        os.makedirs(klasor, exist_ok=True)
    fd = os.open(yol, os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_BINARY", 0),
                 0o644)
    try:
        os.write(fd, veri)                   # TEK yazım: satır bütün iner
        os.fsync(fd)
    finally:
        os.close(fd)


def _tekrar_bul(kayitlar, platform, proje, islem, ts):
    for k in kayitlar:
        if (k.get("platform") == platform and k.get("islem") == islem
                and (k.get("proje") or None) == (proje or None)):
            kts = zaman_ts(k.get("zaman"))
            if kts is not None and abs(kts - ts) <= TEKRAR_PENCERESI_SN:
                return k
    return None


def _gizlilik_tahmini(metin: str):
    s = _katla(metin)
    bulunan = set()
    if re.search(r"\bpublic\b|herkese acik|herkes\b", s):
        bulunan.add("public")
    if re.search(r"\bunlisted\b|liste disi", s):
        bulunan.add("unlisted")
    if re.search(r"\bprivate\b|\bgizli\b|sadece ben|ozel\b", s):
        bulunan.add("private")
    return bulunan.pop() if len(bulunan) == 1 else None


def _tiktok_yayin_yansit(kayit: dict, proje_yol: str):
    """MEVCUT `isaretle_yayinlandi` yolu. Red -> ElleIslemHatasi (hiçbir şey yazılmaz)."""
    if UPLOAD not in sys.path:
        sys.path.append(UPLOAD)
    import tiktok_publish_plan as TPP

    durum = TPP._durum_oku(proje_yol)
    import tiktok_web as TW
    if TW.web_aktif(durum):
        return _tiktok_web_yansit(kayit, proje_yol, TW)
    if not durum.get("tiktok_publish_id"):
        return None, ("taslak kaydı yok (tiktok_publish_id) — yalnız deftere yazıldı, "
                      "state işareti atılmadı")
    if durum.get("tiktok_published_at"):
        return None, "state zaten işaretli (%s) — state değişmedi" % durum["tiktok_published_at"]
    try:
        plan = TPP.build_plan(proje_yol)
    except Exception as e:                                   # noqa: BLE001
        raise ElleIslemHatasi("yayın planı hesaplanamadı (%s) — kayıt yazılmadı"
                              % type(e).__name__)
    if not plan.get("hazir"):
        raise ElleIslemHatasi(
            "REDDEDİLDİ: '%s' plana göre yayınlanmamalıydı — %s. Kayıt yazılmadı. "
            "Gerçekten yayınlandıysa bilgisayardan: python "
            "upload/tiktok_publish_plan.py --yayinlandi-hepsi"
            % (kayit.get("proje"), plan.get("engel") or "sebep bilinmiyor"))
    yerel = datetime.datetime.fromisoformat(kayit["zaman"]).astimezone(TZ)
    try:
        yazildi, mesaj = TPP.isaretle_yayinlandi(
            proje_yol, zaman=yerel.strftime("%Y-%m-%dT%H:%M:%S"),
            kaynak="Elle işlemler defteri (%s, %s)%s" % (
                kayit["kaynak"], kayit["id"],
                " — yaklaşık zaman" if kayit.get("zaman_yaklasik") else ""))
    except TPP.IsaretlemeHatasi as e:
        raise ElleIslemHatasi("İŞARETLENMEDİ: %s" % e)
    if not yazildi:
        return None, mesaj
    return "tiktok_published_at, tiktok_published_kaynak", mesaj


def _tiktok_web_yansit(kayit: dict, proje_yol: str, TW):
    """WEB PLANI (tiktok_web.py, 2026-09-13): `yayinladi` -> `tiktok_web.yayinlandi_isaretle`
    (mevcut `isaretle_yayinlandi` onun içinde). Red -> ElleIslemHatasi (hiçbir şey yazılmaz)."""
    try:
        yazildi, mesaj = TW.yayinlandi_isaretle(
            proje_yol, kaynak="Elle işlemler defteri (%s, %s)" % (kayit["kaynak"], kayit["id"]),
            simdi=zaman_ts(kayit.get("kayit_zamani")))
    except TW.TiktokWebHatasi as e:
        raise ElleIslemHatasi("İŞARETLENMEDİ: %s — kayıt yazılmadı" % e)
    if not yazildi:
        return None, mesaj
    return "tiktok_web.yayinlandi, tiktok_published_at, tiktok_published_kaynak", mesaj


def _youtube_gizlilik_notu(kayit: dict, proje_yol: str, gizlilik):
    onek = "youtube" if kayit["platform"] == "youtube" else "youtube_shorts"
    if kayit["islem"] == "liste_disi_yapti":
        if gizlilik and gizlilik != "unlisted":
            raise ElleIslemHatasi("liste_disi_yapti ile gizlilik=%s çelişiyor" % gizlilik)
        hedef = "unlisted"
    else:
        hedef = gizlilik or _gizlilik_tahmini(kayit.get("ayrinti") or "")
    durum = _state_oku_kesin(proje_yol)
    alan = onek + "_elle_gizlilik_notu"
    durum[alan] = {
        "deger": hedef,
        "zaman": kayit["zaman"],
        "zaman_yaklasik": bool(kayit.get("zaman_yaklasik")),
        "video_id": durum.get(onek + "_video_id"),
        "ayrinti": kayit.get("ayrinti"),
        "kaynak": kayit.get("kaynak"),
        "kayit_id": kayit["id"],
        "not": ("Kullanıcı beyanı. `%s_privacy` (istenen) ve `%s_privacy_gercek` "
                "(API ölçümü) BİLEREK değiştirilmedi." % (onek, onek)),
    }
    import state_io
    state_io.durum_yaz(proje_yol, durum)
    return alan, "%s yazıldı (deger=%s)" % (alan, hedef)


def _state_yansit(kayit: dict, proje_yol, gizlilik):
    if proje_yol is None:
        return None, ""
    p, i = kayit["platform"], kayit["islem"]
    if p == "tiktok" and i == "yayinladi":
        etkisi, mesaj = _tiktok_yayin_yansit(kayit, proje_yol)
        # Ana taslak ZATEN işaretliyse bu yayın bir türev olabilir (türev kancası).
        if etkisi is None and mesaj.startswith("state zaten işaretli"):
            return _turev_yansit(kayit, proje_yol, mesaj)
        return etkisi, mesaj
    if p in ("youtube", "youtube_shorts") and i in ("gizlilik_degistirdi", "liste_disi_yapti"):
        return _youtube_gizlilik_notu(kayit, proje_yol, gizlilik)
    if i == "yayinladi":
        return _turev_yansit(kayit, proje_yol, "")
    return None, ""


def _turev_yansit(kayit: dict, proje_yol: str, onceki_mesaj: str):
    """TÜREV TAKVİMİ kancası (2026-09-13): `yayinladi` -> `turev_takvimi.elle_yayin_eslestir`.

    Eşleşme proje + platform + `config.TUREV_ELLE_ESLESME_SAAT` içindeki
    `planlandi`/`onay_bekliyor` türev kaydı; tek aday `yayinlandi` olur, birden
    fazla aday işaretlenmez ve mesajda raporlanır. VARSAYILAN-GÜVENLİ: türev
    tarafındaki her hata yalnız mesaja düşer, defter kaydını DÜŞÜRMEZ."""
    try:
        import turev_takvimi
        etkisi, mesaj = turev_takvimi.elle_yayin_eslestir(
            proje_yol, kayit["platform"], kayit["zaman"], kayit["id"])
    except Exception as e:                                   # noqa: BLE001
        etkisi, mesaj = None, "türev eşleşmesi yapılamadı (%s)" % type(e).__name__
    return etkisi, " — ".join(m for m in (onceki_mesaj, mesaj) if m)


def ekle(platform, islem, ayrinti, proje=None, zaman=None, kaynak="cli", kanit=None,
         zaman_yaklasik=False, yol=None, state_yansit=True, state_etkisi=None,
         gizlilik=None, proje_klasorleri=None, simdi=None) -> dict:
    """Deftere bir elle işlem ekler.

    Döner: {"durum": "eklendi"|"zaten_kayitli", "kayit": {...}, "mesaj": metin}.
    Doğrulama/red -> `ElleIslemHatasi` ve HİÇBİR ŞEY yazılmaz.
    `state_yansit=False` çağıran state'i kendisi yazdıysa (Telegram onayı,
    backfill): o durumda `state_etkisi` olduğu gibi kaydedilir.
    """
    if platform not in PLATFORMLAR:
        raise ElleIslemHatasi("geçersiz platform: %r — geçerli: %s"
                              % (platform, ", ".join(PLATFORMLAR)))
    if islem not in ISLEMLER:
        raise ElleIslemHatasi("sözlük dışı işlem: %r — geçerli: %s"
                              % (islem, ", ".join(ISLEMLER)))
    if kaynak not in KAYNAKLAR:
        raise ElleIslemHatasi("geçersiz kaynak: %r — geçerli: %s"
                              % (kaynak, ", ".join(KAYNAKLAR)))
    if not isinstance(ayrinti, str) or not ayrinti.strip():
        raise ElleIslemHatasi("ayrinti boş olamaz (ne yapıldığını bir cümleyle yaz)")
    if len(ayrinti) > 2000:
        raise ElleIslemHatasi("ayrinti çok uzun (%d > 2000 karakter)" % len(ayrinti))
    if kanit is not None and not isinstance(kanit, str):
        raise ElleIslemHatasi("kanit metin ya da boş olmalı")
    if gizlilik is not None and gizlilik not in GIZLILIK_DEGERLERI:
        raise ElleIslemHatasi("gizlilik şunlardan biri olmalı: %s"
                              % ", ".join(GIZLILIK_DEGERLERI))
    proje_ad, proje_yol = proje_coz(proje, proje_klasorleri)
    zaman_iso, tarih_yalniz = zaman_coz(zaman, simdi)
    t = simdi if simdi is not None else time.time()
    ts = zaman_ts(zaman_iso)
    if ts > t + GELECEK_TOLERANSI_SN:
        raise ElleIslemHatasi("zaman gelecekte olamaz: %s" % zaman_iso)

    kayit_dt = datetime.datetime.fromtimestamp(t, TZ)
    kayit = {
        "id": "EI-%s-%s" % (kayit_dt.strftime("%Y%m%d-%H%M%S"), secrets.token_hex(2)),
        "zaman": zaman_iso,
        "zaman_yaklasik": bool(zaman_yaklasik or tarih_yalniz),
        "kayit_zamani": _iso(kayit_dt),
        "platform": platform,
        "proje": proje_ad,
        "islem": islem,
        "ayrinti": " ".join(ayrinti.split()),
        "kaynak": kaynak,
        "kanit": (kanit.strip() or None) if isinstance(kanit, str) else None,
        "state_etkisi": None,
    }

    yol = defter_yolu(yol)
    if _testte_gercek_defter(yol):
        raise ElleIslemHatasi("test sırasında GERÇEK deftere yazma reddedildi — "
                              "yol= ya da %s ver" % ORTAM_DEGISKENI)
    with _kilit(yol):
        kayitlar, _ = oku(yol)
        eski = _tekrar_bul(kayitlar, platform, proje_ad, islem, ts)
        if eski is not None:
            return {"durum": "zaten_kayitli", "kayit": eski,
                    "mesaj": "ZATEN KAYITLI: %s (%s)" % (eski.get("id"), eski.get("zaman"))}
        if state_yansit:
            etkisi, state_mesaji = _state_yansit(kayit, proje_yol, gizlilik)
        else:
            etkisi, state_mesaji = state_etkisi, ""
        kayit["state_etkisi"] = etkisi
        _satir_ekle(yol, kayit)
    mesaj = "EKLENDİ: %s" % kayit["id"]
    if state_mesaji:
        mesaj += " — " + state_mesaji
    return {"durum": "eklendi", "kayit": kayit, "mesaj": mesaj}


# --------------------------------------------------------------------------
# Listeleme / özet
# --------------------------------------------------------------------------

def _pencere(kayitlar, gun, t):
    esik = t - float(gun) * 86400
    sonuc = []
    for k in kayitlar:
        ts = zaman_ts(k.get("zaman"))
        if ts is not None and esik <= ts <= t + GELECEK_TOLERANSI_SN:
            sonuc.append(k)
    sonuc.sort(key=lambda k: zaman_ts(k.get("zaman")), reverse=True)
    return sonuc


def listele(gun=7, platform=None, proje=None, yol=None, simdi=None) -> list:
    t = simdi if simdi is not None else time.time()
    kayitlar, _ = oku(yol)
    sonuc = _pencere(kayitlar, gun, t)
    if platform:
        sonuc = [k for k in sonuc if k.get("platform") == platform]
    if proje:
        ad = _nfc(os.path.basename(os.path.normpath(proje)))
        sonuc = [k for k in sonuc if _nfc(k.get("proje") or "") == ad]
    return sonuc


def api_dogrulanan_tiktok(gun=1, simdi=None, proje_klasorleri=None, kayitlar=None) -> list:
    """Otomatik doğrulamanın işaretlediği TikTok yayınları (deftere YAZILMAZ).

    TikTok'ta yayın her zaman ELLE (API yayınlayamıyor); PUBLISH_COMPLETE onun
    kanıtı. Defterde aynı proje için bir yayın kaydı varsa tekrar gösterilmez.
    """
    t = simdi if simdi is not None else time.time()
    esik = t - float(gun) * 86400
    defterde = {_nfc(k.get("proje")) for k in (kayitlar or [])
                if k.get("platform") == "tiktok" and k.get("islem") == "yayinladi"
                and k.get("proje")}
    sonuc = []
    for yol in _proje_klasorleri(proje_klasorleri):
        st = _state_oku(yol)
        kaynak = st.get("tiktok_published_kaynak")
        if not isinstance(kaynak, str) or "PUBLISH_COMPLETE" not in kaynak:
            continue
        ts = zaman_ts(st.get("tiktok_published_at"))
        if ts is None or not (esik <= ts <= t + GELECEK_TOLERANSI_SN):
            continue
        ad = _nfc(os.path.basename(os.path.normpath(yol)))
        if ad in defterde:
            continue
        sonuc.append({"platform": "tiktok", "proje": ad, "islem": "yayinladi",
                      "zaman": _iso(datetime.datetime.fromtimestamp(ts, TZ)),
                      "zaman_yaklasik": True, "ayrinti": API_ETIKETI,
                      "kaynak": "api_dogrulama", "api_dogrulandi": True})
    sonuc.sort(key=lambda k: zaman_ts(k["zaman"]), reverse=True)
    return sonuc


def _api_isaretle(kayitlar, proje_klasorleri):
    """Defterdeki TikTok yayın kayıtlarına `api_dogrulandi` ekler (kopya sözlük)."""
    ilgili = [k for k in kayitlar if k.get("platform") == "tiktok"
              and k.get("islem") == "yayinladi" and k.get("proje")]
    if not ilgili:
        return list(kayitlar)
    yollar = {_nfc(os.path.basename(os.path.normpath(y))): y
              for y in _proje_klasorleri(proje_klasorleri)}
    sonuc = []
    for k in kayitlar:
        if k in ilgili and _nfc(k["proje"]) in yollar:
            st = _state_oku(yollar[_nfc(k["proje"])])
            if st.get("tiktok_publish_status") == "PUBLISH_COMPLETE":
                k = dict(k, api_dogrulandi=True)
        sonuc.append(k)
    return sonuc


def ozet(gun=1, yol=None, simdi=None, proje_klasorleri=None, api=True) -> dict:
    t = simdi if simdi is not None else time.time()
    kayitlar, bozuk = oku(yol)
    pencere = _pencere(kayitlar, gun, t)
    api_listesi, api_hatasi = [], None
    if api:
        try:
            pencere = _api_isaretle(pencere, proje_klasorleri)
            api_listesi = api_dogrulanan_tiktok(gun, t, proje_klasorleri, kayitlar)
        except Exception as e:                               # noqa: BLE001
            api_hatasi = "%s: %s" % (type(e).__name__, str(e)[:100])
    platformlar, islemler = {}, {}
    for k in pencere + api_listesi:
        platformlar[k["platform"]] = platformlar.get(k["platform"], 0) + 1
        islemler[k["islem"]] = islemler.get(k["islem"], 0) + 1
    return {"gun": gun, "toplam": len(pencere) + len(api_listesi),
            "defter": len(pencere), "api_dogrulanan_sayisi": len(api_listesi),
            "platform": platformlar, "islem": islemler, "kayitlar": pencere,
            "api_dogrulanan": api_listesi, "bozuk_satir": len(bozuk),
            "api_hatasi": api_hatasi}


def _kayit_satiri(k: dict) -> str:
    ts = zaman_ts(k.get("zaman"))
    an = time.strftime("%d.%m %H:%M", time.localtime(ts)) if ts is not None else "?"
    if k.get("zaman_yaklasik"):
        an += "~"
    parca = PLATFORM_ADLARI.get(k.get("platform"), k.get("platform"))
    if k.get("proje"):
        parca += " · " + k["proje"]
    if k.get("kaynak") == "api_dogrulama":
        return "  %s %s: %s" % (an, parca, API_ETIKETI)
    metin = ISLEMLER.get(k.get("islem"), k.get("islem"))
    if k.get("api_dogrulandi"):
        metin += " (API ile doğrulandı)"
    ayrinti = " ".join(str(k.get("ayrinti") or "").split())
    if ayrinti:
        metin += " — " + (ayrinti if len(ayrinti) <= 70 else ayrinti[:67] + "...")
    return "  %s %s: %s" % (an, parca, metin)


def ozet_satirlari(oz: dict, tavan: int = 8) -> list:
    """Rapor satırları (başlıksız). En yeni önce; tavanı aşan kısım "+N daha"."""
    hepsi = sorted(oz.get("kayitlar", []) + oz.get("api_dogrulanan", []),
                   key=lambda k: zaman_ts(k.get("zaman")) or 0, reverse=True)
    satirlar = [_kayit_satiri(k) for k in hepsi[:tavan]]
    if len(hepsi) > tavan:
        satirlar.append("  +%d daha" % (len(hepsi) - tavan))
    return satirlar


def platform_kirilimi(oz: dict) -> str:
    return ", ".join("%s %d" % (PLATFORM_ADLARI.get(p, p), n)
                     for p, n in sorted(oz.get("platform", {}).items(),
                                        key=lambda x: (-x[1], x[0])))


def saglik_durumu(yol=None) -> dict:
    """Sağlık kontrolü için: {"durum": "yok"|"tamam"|"bozuk", ...}."""
    yol = defter_yolu(yol)
    if _testte_gercek_defter(yol) or not os.path.exists(yol):
        return {"durum": "yok", "kayit": 0, "bozuk": []}
    kayitlar, bozuk = oku(yol)
    return {"durum": "bozuk" if bozuk else "tamam", "kayit": len(kayitlar),
            "bozuk": bozuk[:10], "bozuk_sayisi": len(bozuk)}


# --------------------------------------------------------------------------
# Geriye dönük doldurma (SALT OKUMA kaynaklar; yazılan tek yer defter)
# --------------------------------------------------------------------------

_TR_KATLA = str.maketrans({
    "ı": "i", "İ": "i", "I": "i", "ğ": "g", "Ğ": "g", "ü": "u", "Ü": "u",
    "ş": "s", "Ş": "s", "ö": "o", "Ö": "o", "ç": "c", "Ç": "c",
})
ELLE_IFADELERI = ("kullanici", "elle", "studio", "telefondan", "uygulamadan")
OTOMASYON_IFADELERI = ("api ile", "otomatik", "publish_complete", "betik", "script")
_GECMIS_FIIL = re.compile(
    r"\b(yapıldı|yaptı|aldı|alındı|arşivledi|arşivlendi|sildi|silindi|gizledi|"
    r"gizlendi|açtı|açıldı|çekildi|çekti)\b", re.IGNORECASE)
_ISO_TARIH = re.compile(r"(20\d\d-\d\d-\d\d)")
_AYLAR = {"Eyl": 9, "Ağu": 8, "Eki": 10}


def _katla(metin) -> str:
    return _nfc(metin).translate(_TR_KATLA).lower()


def _siniflandir(metin: str) -> str:
    s = _katla(metin)
    elle = any(i in s for i in ELLE_IFADELERI)
    oto = any(i in s for i in OTOMASYON_IFADELERI)
    if oto:
        return "otomasyon" if not elle else "belirsiz"
    return "elle" if elle else "belirsiz"


def _saat_tahmini(metin: str, tarih: str) -> tuple:
    """(iso, yaklasik, hassasiyet 1..3)."""
    m = re.search(re.escape(tarih) + r"[ T]+(\d{1,2}):(\d{2})", metin)
    if m:
        return "%sT%02d:%s:00+03:00" % (tarih, int(m.group(1)), m.group(2)), False, 3
    s = _katla(metin)
    for kelime, saat in (("aksam", "19:00"), ("gece", "23:00"), ("sabah", "09:00"),
                         ("ogle", "12:30")):
        if kelime in s:
            return "%sT%s:00+03:00" % (tarih, saat), True, 2
    return "%sT12:00:00+03:00" % tarih, True, 1


def _aday(platform, proje, islem, ayrinti, zaman, yaklasik, hassasiyet, kanit, dayanak):
    return {"platform": platform, "proje": proje, "islem": islem, "ayrinti": ayrinti,
            "zaman": zaman, "zaman_yaklasik": yaklasik, "_hassasiyet": hassasiyet,
            "kanit": kanit, "dayanak": dayanak}


def _tiktok_url(post_id: str) -> str:
    return "https://www.tiktok.com/@famousmusicstudio/video/%s" % post_id


def _cumle_adaylari(metin, proje, platform, dayanak, adaylar, belirsiz):
    """Serbest state metnini (kopya_notu, plan sebebi) yan cümlelere bölüp tarar."""
    genel = _ISO_TARIH.search(metin)
    for parca in re.split(r"(?<=[.;,])\s+", metin):
        if not _GECMIS_FIIL.search(parca):
            continue
        s = _katla(parca)
        if "liste dis" in s or "unlisted" in s:
            islem, gizlilik = "liste_disi_yapti", "unlisted"
        elif "public" in s or "herkese acik" in s:
            islem, gizlilik = "gizlilik_degistirdi", "public"
        elif "arsiv" in s:
            islem, gizlilik = "arsivledi", None
        else:
            continue
        plt = "youtube_shorts" if "shorts" in s else platform
        sinif = _siniflandir(parca)
        ozet_parca = " ".join(parca.split())[:160]
        if sinif != "elle":
            belirsiz.append({"dayanak": dayanak, "metin": ozet_parca,
                             "neden": "elle olduğu belli değil (%s)" % sinif})
            continue
        tarih_m = _ISO_TARIH.search(parca) or genel
        if not tarih_m:
            belirsiz.append({"dayanak": dayanak, "metin": ozet_parca, "neden": "tarih yok"})
            continue
        zaman, yaklasik, hassas = _saat_tahmini(parca, tarih_m.group(1))
        vid = re.search(r"\(([A-Za-z0-9_-]{11})\)", parca)
        ayrinti = ozet_parca + (" [gizlilik: %s]" % gizlilik if gizlilik else "")
        adaylar.append(_aday(plt, proje, islem, ayrinti, zaman, yaklasik, hassas,
                             vid.group(1) if vid else None, dayanak))


def _state_kaynaklari(klasorler, adaylar, belirsiz, otomasyon):
    kapak_toplu = []
    for yol in klasorler:
        ad = _nfc(os.path.basename(os.path.normpath(yol)))
        st = _state_oku(yol)
        if not st:
            continue
        # TikTok yayını: API yayınlayamıyor -> her yayın ELLE; PUBLISH_COMPLETE
        # damgası otomasyonun TESPİTİDİR, deftere girmez (özetlerde görünür).
        pub = st.get("tiktok_published_at")
        if pub:
            kaynak = st.get("tiktok_published_kaynak") or ""
            if "PUBLISH_COMPLETE" in kaynak or "otomatik" in _katla(kaynak):
                otomasyon.append({"dayanak": "%s/state tiktok_published_kaynak" % ad,
                                  "neden": "otomatik doğrulama damgası (tespit anı)"})
            else:
                iso, _ = zaman_coz(pub)
                pid = re.search(r"\b(7\d{18})\b", kaynak)
                ayrinti = ("TikTok'ta yayınlandı (uygulamadan, elle)" + (
                    " — " + " ".join(kaynak.split())[:140] if kaynak else
                    " — state'te kaynak metni yok"))
                adaylar.append(_aday("tiktok", ad, "yayinladi", ayrinti, iso, False, 3,
                                     _tiktok_url(pid.group(1)) if pid else None,
                                     "%s/state tiktok_published_at" % ad))
        plan = st.get("youtube_gorunurluk_plani")
        if isinstance(plan, dict) and isinstance(plan.get("sebep"), str):
            _cumle_adaylari(plan["sebep"], ad, "youtube",
                            "%s/state youtube_gorunurluk_plani.sebep" % ad, adaylar, belirsiz)
        if isinstance(st.get("kopya_notu"), str):
            _cumle_adaylari(st["kopya_notu"], ad, "youtube",
                            "%s/state kopya_notu" % ad, adaylar, belirsiz)
        bek = st.get("yayin_beklet")
        if isinstance(bek, dict):
            sebep = str(bek.get("sebep") or "")
            dayanak = "%s/state yayin_beklet" % ad
            if _siniflandir(sebep) == "elle" and zaman_ts(bek.get("istendi_at")):
                iso, _ = zaman_coz(bek["istendi_at"])
                adaylar.append(_aday("diger", ad, "bekletmeye_aldi",
                                     "Kullanıcı kararıyla yayın bekletmeye alındı — "
                                     + " ".join(sebep.split())[:160], iso, True, 2,
                                     None, dayanak))
            else:
                belirsiz.append({"dayanak": dayanak, "metin": sebep[:120],
                                 "neden": "kullanıcı kararı olduğu ya da zaman belli değil"})
        for alan, islem_metni in (("telif_itiraz_kaynak", "Studio'da telif/hak talebi durumu elle kontrol edildi"),
                                  ("dj_tarama_temiz_kaynak", "Studio'da hak talebi elle kontrol edildi (temiz)")):
            metin = st.get(alan)
            if not isinstance(metin, str):
                continue
            dayanak = "%s/state %s" % (ad, alan)
            tarih = _ISO_TARIH.search(metin)
            if "studio" in _katla(metin) and tarih:
                durum = st.get("telif_itiraz_durumu") if alan == "telif_itiraz_kaynak" else None
                ayrinti = islem_metni + (" — durum: %s" % durum if durum else "") + \
                    " — " + " ".join(metin.split())[:120]
                adaylar.append(_aday("youtube", ad, "kontrol_etti", ayrinti,
                                     "%sT12:00:00+03:00" % tarih.group(1), True, 1, None, dayanak))
            else:
                belirsiz.append({"dayanak": dayanak, "metin": metin[:120],
                                 "neden": "Studio/tarih ifadesi yok"})
        if isinstance(st.get("telif_notu"), str) and "elle" in _katla(st["telif_notu"]):
            belirsiz.append({"dayanak": "%s/state telif_notu" % ad,
                             "metin": " ".join(st["telif_notu"].split())[:120],
                             "neden": "telif bölümleri ELLE çıkarılmış ama çıkarma TARİHİ yok "
                                      "(yalnız eşleşme günü)"})
        if st.get("youtube_thumbnail_updated_at"):
            kapak_toplu.append(st["youtube_thumbnail_updated_at"])
    if kapak_toplu:
        en_sik = max(set(kapak_toplu), key=kapak_toplu.count)
        belirsiz.append({"dayanak": "state youtube_thumbnail_updated_at (%d proje)" % len(kapak_toplu),
                         "metin": "%d projede aynı damga %s" % (kapak_toplu.count(en_sik), en_sik),
                         "neden": "toplu API/betik güncellemesi görünümünde; elle (Studio) "
                                  "yapıldığına dair ifade yok"})


# CLAUDE.md: serbest metin güvenilir biçimde genel ayrıştırılamaz -> HEDEFLİ
# desenler. Desen metinde yoksa aday da yok (belge değiştiyse sessizce düşer,
# kuru çıktıda görünür).
def _claude_md_kaynagi(metin, bilinen, adaylar, belirsiz):
    def _satir(m):
        return "CLAUDE.md:%d" % (metin.count("\n", 0, m.start()) + 1)

    m = re.search(r"Kullanıcı Studio'dan geri\s+aldı", metin)
    if m and "Küllerimden Geç" in bilinen:
        kesin = "2026-09-12 21:27" in metin and "2026-09-12 22:38" in metin
        adaylar.append(_aday(
            "youtube", "Küllerimden Geç", "gizlilik_degistirdi",
            "Kullanıcı uzun formatı Studio'dan geri public yaptı (21:27 API okumasından "
            "sonra, 22:38 ölçümünden önce) [gizlilik: public]",
            "2026-09-12T22:00:00+03:00" if kesin else "2026-09-12T12:00:00+03:00",
            True, 2 if kesin else 1, "-CQ7MmUygTQ", _satir(m)))
    m = re.search(r"Kullanıcı `Yeniden Doğacağım` videosunda kapak eksikliği[^.]*?liste\s+dışı\s+yaptı",
                  metin)
    if m and "Yeniden Doğacağım" in bilinen:
        adaylar.append(_aday(
            "youtube", "Yeniden Doğacağım", "liste_disi_yapti",
            "Kullanıcı kapak eksikliği yüzünden uzun formatı liste dışı yaptı (CLAUDE.md "
            "'ASIL kayıt' maddesi, 2026-09-12 gece)",
            "2026-09-12T23:00:00+03:00", True, 2, "kZML9g4GdBs", _satir(m)))
    for desen, neden in (
            (r"2026-09-11'de bir oturum[^.]*?gizlemişti",
             "Küllerimden Geç'i gizleyen bir Claude oturumuydu (kullanıcı değil); yöntem kayıtlı değil"),
            (r"KAYITSIZ şekilde \(büyük ihtimalle Studio'dan elle\)",
             "Bu Gece Kazandık unlisted'a çekilmesi: kullanıcı gizlemediğini söyledi, yapan bilinmiyor"),
            (r"kullanıcı telefondan arşivleyecek",
             "Instagram arşivi GELECEK zaman — yapıldığı kayıtlı değil")):
        m = re.search(desen, metin)
        if m:
            belirsiz.append({"dayanak": _satir(m), "metin": " ".join(m.group(0).split())[:120],
                             "neden": neden})


def _bolum(metin, baslik_deseni):
    m = re.search(baslik_deseni, metin)
    if not m:
        return None, None
    son = re.search(r"\n#{2,3} ", metin[m.end():])
    return m, metin[m.start(): m.end() + (son.start() if son else len(metin))]


def _metindeki_proje(metin, bilinen):
    """Metinde EN ÖNCE geçen proje adı (eşit konumda en uzun)."""
    en = None
    for ad in bilinen:
        i = metin.find(ad)
        if i >= 0 and (en is None or i < en[0] or (i == en[0] and len(ad) > len(en[1]))):
            en = (i, ad)
    return en[1] if en else None


def _envanter_kaynagi(dosya, metin, bilinen, adaylar, belirsiz):
    adi = os.path.basename(dosya)
    yil_m = re.search(r"(20\d\d)-\d\d-\d\d", adi)
    yil = int(yil_m.group(1)) if yil_m else 2026
    belirsiz_sayisi = 0
    satir_re = re.compile(
        r"^\|\s*(\d+)\s*\|\s*(\d{1,2}) (\w{3}) (\d{2}):(\d{2})\s*\|([^|]*)\|([^|]*)\|"
        r".*?/video/(\d+)\s*\|\s*$", re.M)
    for m in satir_re.finditer(metin):
        ay = _AYLAR.get(m.group(3))
        hucre = m.group(7)
        if "İÇERİK:" in hucre:
            proje = _metindeki_proje(hucre.split("İÇERİK:", 1)[1], bilinen)
        elif "(kesin" in hucre or "(yüksek" in hucre:
            proje = _metindeki_proje(hucre.split("(", 1)[0], bilinen)
        else:
            proje = None
        if not ay or not proje:
            belirsiz_sayisi += 1
            continue
        iso = "%04d-%02d-%02dT%s:%s:00+03:00" % (yil, ay, int(m.group(2)), m.group(4), m.group(5))
        adaylar.append(_aday(
            "tiktok", proje, "yayinladi",
            "TikTok'ta yayında (Studio listesi, içerik eşleşmesi: %s)" % " ".join(hucre.split())[:120],
            iso, False, 3, _tiktok_url(m.group(8)), "%s tablo #%s" % (adi, m.group(1))))
    if belirsiz_sayisi:
        belirsiz.append({"dayanak": "%s ana tablo" % adi,
                         "metin": "%d gönderinin şarkısı belirsiz/olası" % belirsiz_sayisi,
                         "neden": "içerik eşleşmesi kesin değil (başlık içerikle uyuşmuyor)"})

    # İçerik haritası (başlığa DEĞİL içeriğe göre; CLAUDE.md dersi).
    icerik = {}
    _, bol = _bolum(metin, r"\n## İçerik doğrulaması[^\n]*")
    if bol:
        for m in re.finditer(r"^\|\s*(\d{19}) \([^)]*\)\s*\|[^|]*\|([^|]*)\|[^|]*\|\s*$", bol, re.M):
            proje = _metindeki_proje(m.group(2), bilinen)
            if proje:
                icerik[m.group(1)] = proje

    m_bas, bol = _bolum(metin, r"\n## Görünürlük değişiklikleri \((20\d\d-\d\d-\d\d), Studio listesinden[^\n]*")
    if bol:
        tarih = m_bas.group(1)
        saat = "09:00" if "sabah Sadece ben" in metin else "12:00"
        for m in re.finditer(r"^\|\s*https://\S+/video/(\d{19})\s*\|", bol, re.M):
            pid = m.group(1)
            proje = icerik.get(pid)
            if not proje:
                belirsiz.append({"dayanak": "%s Görünürlük değişiklikleri" % adi, "metin": pid,
                                 "neden": "içerik doğrulaması tablosunda yok"})
                continue
            adaylar.append(_aday(
                "tiktok", proje, "gizlilik_degistirdi",
                "TikTok Studio'dan Herkes -> Sadece ben (başlığa göre yapılan gizleme; içerik: %s)" % proje,
                "%sT%s:00+03:00" % (tarih, saat), True, 2, _tiktok_url(pid),
                "%s Görünürlük değişiklikleri" % adi))

    m_bas, bol = _bolum(metin, r"\n## UYGULANDI \((20\d\d-\d\d-\d\d) (\d\d):(\d\d)[^0-9]+(\d\d):(\d\d) TRT, ([^)\n]*)\)")
    if bol:
        bas = int(m_bas.group(2)) * 60 + int(m_bas.group(3))
        son = int(m_bas.group(4)) * 60 + int(m_bas.group(5))
        orta = (bas + son) // 2
        iso = "%sT%02d:%02d:00+03:00" % (m_bas.group(1), orta // 60, orta % 60)
        for m in re.finditer(r"^\|\s*(\d{19}) \(([^)]*)\)\s*\|([^|]*)\|([^|]*)\|([^|]*)\|\s*$", bol, re.M):
            once = m.group(4).replace("*", "").strip()
            sonra = m.group(5).replace("*", "").strip()
            if "dokunulmadı" in sonra or once == sonra:
                continue
            proje = _metindeki_proje(m.group(3), bilinen)
            if not proje:
                belirsiz.append({"dayanak": "%s UYGULANDI" % adi, "metin": m.group(1),
                                 "neden": "içerik proje adıyla eşleşmedi"})
                continue
            adaylar.append(_aday(
                "tiktok", proje, "gizlilik_degistirdi",
                "TikTok Studio web'den görünürlük: %s -> %s (içerik doğrulamasına göre)" % (once, sonra),
                iso, True, 2, _tiktok_url(m.group(1)), "%s UYGULANDI" % adi))


def _kontrol_listesi_kaynagi(metin, belirsiz):
    for no, satir in enumerate(metin.split("\n"), 1):
        if re.match(r"^\s*[-*]\s*\[[xX]\]", satir) or "YAPILDI" in satir:
            neden = ("platform/işlem otomatik çıkarılamıyor" if _ISO_TARIH.search(satir)
                     else "işaretli ama TARİHSİZ")
            belirsiz.append({"dayanak": "buyume_kontrol_listesi.md:%d" % no,
                             "metin": " ".join(satir.split())[:120], "neden": neden})


def _ayni_olay(a, b) -> bool:
    if (a["platform"], a.get("proje") or None, a["islem"]) != \
            (b["platform"], b.get("proje") or None, b["islem"]):
        return False
    ta, tb = zaman_ts(a["zaman"]), zaman_ts(b["zaman"])
    if ta is None or tb is None:
        return False
    if abs(ta - tb) <= TEKRAR_PENCERESI_SN:
        return True
    if a.get("zaman_yaklasik") or b.get("zaman_yaklasik"):
        return a["zaman"][:10] == b["zaman"][:10]
    return False


def _birlestir(adaylar) -> list:
    sonuc = []
    for a in adaylar:
        es = next((b for b in sonuc if _ayni_olay(a, b)), None)
        if es is None:
            sonuc.append(dict(a))
            continue
        if a["_hassasiyet"] > es["_hassasiyet"]:
            es.update(zaman=a["zaman"], zaman_yaklasik=a["zaman_yaklasik"],
                      _hassasiyet=a["_hassasiyet"])
        if a["dayanak"] not in es["dayanak"].split(" + "):
            es["dayanak"] += " + " + a["dayanak"]
        kanitlar = [k for k in (es.get("kanit"), a.get("kanit")) if k]
        birlesik = []
        for k in " ; ".join(kanitlar).split(" ; "):
            if k and k not in birlesik:
                birlesik.append(k)
        es["kanit"] = " ; ".join(birlesik) or None
    return sonuc


def backfill(uygula=False, yol=None, repo=None, proje_klasorleri=None, simdi=None) -> dict:
    """Dağınık kaynaklardan geçmiş elle işlemleri toplar. Varsayılan KURU.

    Kaynaklar SALT OKUNUR. `uygula=True` yalnız DEFTERE yazar (state'e asla:
    `ekle(..., state_yansit=False)`).
    """
    repo = repo or REPO
    klasorler = _proje_klasorleri(proje_klasorleri)
    bilinen = [_nfc(os.path.basename(os.path.normpath(y))) for y in klasorler]
    adaylar, belirsiz, otomasyon = [], [], []

    _state_kaynaklari(klasorler, adaylar, belirsiz, otomasyon)

    def _oku_md(ad):
        try:
            with open(os.path.join(repo, ad), "r", encoding="utf-8") as f:
                return _nfc(f.read())
        except OSError:
            return None

    metin = _oku_md("CLAUDE.md")
    if metin:
        _claude_md_kaynagi(metin, bilinen, adaylar, belirsiz)
    metin = _oku_md("buyume_kontrol_listesi.md")
    if metin:
        _kontrol_listesi_kaynagi(metin, belirsiz)
    try:
        envanterler = sorted(a for a in os.listdir(repo)
                             if re.fullmatch(r"tiktok_envanteri_.*\.md", a))
    except OSError:
        envanterler = []
    for ad in envanterler:
        metin = _oku_md(ad)
        if metin:
            _envanter_kaynagi(ad, metin, bilinen, adaylar, belirsiz)

    adaylar = [a for a in adaylar if a.get("proje") is None or a["proje"] in bilinen]
    adaylar = _birlestir(adaylar)
    adaylar.sort(key=lambda a: zaman_ts(a["zaman"]))

    mevcut, _ = oku(yol)
    eklenecek, zaten = [], []
    for a in adaylar:
        (zaten if any(_ayni_olay(a, k) for k in mevcut) else eklenecek).append(a)

    yazilan, hatalar = 0, []
    if uygula:
        for a in eklenecek:
            try:
                s = ekle(a["platform"], a["islem"],
                         "%s (dayanak: %s)" % (a["ayrinti"], a["dayanak"]),
                         proje=a["proje"], zaman=a["zaman"], kaynak="backfill",
                         kanit=a["kanit"], zaman_yaklasik=a["zaman_yaklasik"], yol=yol,
                         state_yansit=False, state_etkisi=None,
                         proje_klasorleri=klasorler, simdi=simdi)
            except ElleIslemHatasi as e:
                hatalar.append({"aday": a, "hata": str(e)})
                continue
            if s["durum"] == "eklendi":
                yazilan += 1
            else:
                zaten.append(a)
    return {"kuru": not uygula, "adaylar": eklenecek, "zaten_kayitli": zaten,
            "belirsiz": belirsiz, "otomasyon_atlandi": otomasyon,
            "yazilan": yazilan, "hatalar": hatalar}


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _cikti_utf8() -> None:
    """cp1254 konsolda Türkçe/emoji çıktısı çökmesin (yalnız main'de; bkz.
    `tiktok_publish_plan._cikti_utf8` — o modülü yalnız bunun için import
    etmek social_text/config zincirini çekerdi)."""
    for akis in (sys.stdout, sys.stderr):
        try:
            akis.reconfigure(encoding="utf-8", errors="replace")
        except Exception:                                    # noqa: BLE001
            pass


def _json_bas(veri) -> None:
    print(json.dumps(veri, ensure_ascii=False, indent=2, default=str))


def _aday_satiri(a) -> str:
    return "  %s%s  %-14s %-20s %-19s %s" % (
        a["zaman"][:16].replace("T", " "), "~" if a.get("zaman_yaklasik") else " ",
        a["platform"], (a.get("proje") or "-")[:20], a["islem"], a["dayanak"])


def main(argv=None) -> int:
    _cikti_utf8()
    ap = argparse.ArgumentParser(description="Elle işlemler defteri")
    ap.add_argument("--defter", default=None, help="defter yolu (varsayılan: repo kökü)")
    alt = ap.add_subparsers(dest="komut", required=True)

    e = alt.add_parser("ekle", help="bir elle işlem kaydet")
    e.add_argument("--platform", required=True)
    e.add_argument("--proje", default=None)
    e.add_argument("--islem", required=True)
    e.add_argument("--ayrinti", required=True)
    e.add_argument("--zaman", default=None)
    e.add_argument("--yaklasik", action="store_true", help="zaman kesin değil")
    e.add_argument("--kaynak", default="cli")
    e.add_argument("--kanit", default=None)
    e.add_argument("--gizlilik", default=None, choices=GIZLILIK_DEGERLERI)
    e.add_argument("--json", action="store_true")

    l = alt.add_parser("listele")
    l.add_argument("--gun", type=float, default=7)
    l.add_argument("--platform", default=None)
    l.add_argument("--proje", default=None)
    l.add_argument("--json", action="store_true")

    o = alt.add_parser("ozet")
    o.add_argument("--gun", type=float, default=1)
    o.add_argument("--json", action="store_true")

    b = alt.add_parser("backfill")
    b.add_argument("--uygula", action="store_true", help="deftere YAZ (varsayılan kuru)")
    b.add_argument("--json", action="store_true")

    s = alt.add_parser("sozluk")
    s.add_argument("--json", action="store_true")

    args = ap.parse_args(argv)

    if args.komut == "sozluk":
        veri = {"platformlar": list(PLATFORMLAR), "islemler": ISLEMLER,
                "kaynaklar": list(KAYNAKLAR)}
        if args.json:
            _json_bas(veri)
        else:
            print("platform: " + ", ".join(PLATFORMLAR))
            print("islem   : " + ", ".join(ISLEMLER))
            print("kaynak  : " + ", ".join(KAYNAKLAR))
        return 0

    if args.komut == "ekle":
        try:
            sonuc = ekle(args.platform, args.islem, args.ayrinti, proje=args.proje,
                         zaman=args.zaman, kaynak=args.kaynak, kanit=args.kanit,
                         zaman_yaklasik=args.yaklasik, yol=args.defter,
                         gizlilik=args.gizlilik)
        except ElleIslemHatasi as hata:
            if args.json:
                _json_bas({"durum": "hata", "hata": str(hata)})
            else:
                print("HATA: %s" % hata)
            return 2
        if args.json:
            _json_bas(sonuc)
        else:
            print(sonuc["mesaj"])
        return 0

    if args.komut == "listele":
        kayitlar = listele(args.gun, args.platform, args.proje, yol=args.defter)
        if args.json:
            _json_bas(kayitlar)
        else:
            print("Son %g günde %d elle işlem" % (args.gun, len(kayitlar)))
            for k in kayitlar:
                print(_kayit_satiri(k))
        return 0

    if args.komut == "ozet":
        oz = ozet(args.gun, yol=args.defter)
        if args.json:
            _json_bas(oz)
        else:
            print("Son %g günde elle yapılanlar: %d%s" % (
                args.gun, oz["toplam"],
                (" (%s)" % platform_kirilimi(oz)) if oz["toplam"] else ""))
            for satir in ozet_satirlari(oz, tavan=50):
                print(satir)
            if oz["bozuk_satir"]:
                print("UYARI: defterde %d bozuk satır" % oz["bozuk_satir"])
        return 0

    if args.komut == "backfill":
        sonuc = backfill(uygula=args.uygula, yol=args.defter)
        if args.json:
            _json_bas(sonuc)
            return 0
        print("BACKFILL %s" % ("UYGULA" if args.uygula else "KURU (hiçbir şey yazılmadı)"))
        print("Eklenecek aday: %d" % len(sonuc["adaylar"]))
        for a in sonuc["adaylar"]:
            print(_aday_satiri(a))
        print("Zaten kayıtlı: %d" % len(sonuc["zaten_kayitli"]))
        print("Otomasyon (atlandı): %d" % len(sonuc["otomasyon_atlandi"]))
        for x in sonuc["otomasyon_atlandi"]:
            print("  %s — %s" % (x["dayanak"], x["neden"]))
        print("Belirsiz (eklenmedi): %d" % len(sonuc["belirsiz"]))
        for x in sonuc["belirsiz"]:
            print("  %s — %s | %s" % (x["dayanak"], x["neden"], x["metin"]))
        if args.uygula:
            print("YAZILAN: %d satır" % sonuc["yazilan"])
            for h in sonuc["hatalar"]:
                print("  HATA: %s" % h["hata"])
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
