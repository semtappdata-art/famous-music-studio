# -*- coding: utf-8 -*-
"""GEÇMİŞTE SİLİNMİŞ zorunlu AI beyanını (`containsSyntheticMedia`) geri yazar.

ELLE, TEK SEFERLİK çalıştırılır — hiçbir zamanlayıcı görevine BAĞLI DEĞİL
(`upload/tiktok_publish_plan.py` ile aynı sınıf: var olma sebebi elle bir
adım). CLAUDE.md'nin "yeni bir modül yazarken üç soru" kuralının cevapları:

  1. Kim çağıracak? — operatör, elle: `python upload/ai_beyani_onar.py`.
  2. Hangi zamanlayıcı görevinden? — HİÇBİRİ, bilerek. Bu bir GEÇMİŞ HASAR
     onarımı (bir kez biter) ve her video 51 birim YouTube kotası yiyor;
     saatlik hatta bağlamak, yükleme kotasını sürekli tırtıklayan ve
     bittiğinde ASIL yüklemeleri düşüren bir iş demekti (2026-09-06'da
     `_drain_golden_hour_queue` ile tam olarak bu oldu).
  3. Çalışmadığını nasıl anlarız? — her adım `ai_beyani_onar.log`'a yazılıyor,
     her koşunun sonunda "kalan" sayısı basılıyor ve onarılanlar
     `upload/ai_beyani_onarim.json`'da damgalanıyor. "Kalan: 0" görülene kadar
     iş BİTMEMİŞTİR.

NEDEN VAR — doğrulanmış geçmiş hasar
------------------------------------
`upload/set_privacy.py`'nin ilk sürümü `videos.update(part="status", ...)`
çağrısını gövdede YALNIZCA `privacyStatus` ile yapıyordu. `videos.update`
KISMİ GÜNCELLEME YAPMAZ: `part` içinde olup gövdede verilmeyen her mutable
alan SİLİNİR. Yani o betiğin her çalıştırması, dokunduğu videonun YouTube'a
karşı ZORUNLU olan AI-üretimi beyanını (`containsSyntheticMedia: True`) ve
`selfDeclaredMadeForKids: False` alanını sessizce siliyordu. Betik bugün
düzeltildi (`guvenli_status_govdesi()`), ama GEÇMİŞ yazımlar geride kaldı:

  * `444daac` (2026-09-07 15:06) — yayındaki TÜM videolar Content ID taraması
    için geçici olarak unlisted'a çekildi (16 proje, uzun format + Shorts).
  * `2d6da01` (40 dakika sonra) — hepsi geri public yapıldı.
  * 2026-09-11 — `Küllerimden Geç` unlisted'a çekildi (kopya ses kaydı).

Bu videolarda YouTube'a giden SON `status` yazımı o bozuk gövdeydi; beyan
silinmiş KABUL EDİLMELİDİR.

VE DOĞRULANAMIYOR: `videos.list(part="status")` `containsSyntheticMedia`
alanını GERİ DÖNDÜRMÜYOR (yazılabilir ama okunamaz — 2026-09-11'de canlı bir
videoda ölçüldü). Yani "hangi videoda silinmiş" diye API'den bakmanın yolu
YOK; sadece Studio'dan elle görülebiliyor.

Onarım yöntemi: videoyu MEVCUT gizliliğine YENİDEN yazmak. Görünürlük
değişmez, beyan geri gelir.

NEDEN HEDEF LİSTESİ "HEPSİ" — ve neden sabit liste DEĞİL
--------------------------------------------------------
Hedefler `uyumluluk.proje_klasorleri()` ile ÜÇ içerik kökünden (projects /
dj_sets / derlemeler) ve her projenin `state.json`'ındaki
`youtube_video_id` + `youtube_shorts_video_id` alanlarından TÜRETİLİYOR.
Kaynakta TEK BİR video kimliği bile gömülü değil: bu deponun belgelenmiş
"bayatlayan sabit liste" hata sınıfı (bkz. `uyumluluk.KOK_ADLARI`'nın
gerekçesi — kök listesini elle sayan her yer `derlemeler/`i atlamıştı).

"Hangi videolar ETKİLENDİ" sorusu ise KESİN olarak türetilemiyor, üç ayrı
sebeple — bu yüzden varsayılan olarak HEPSİ hedefleniyor:

  a. Beyanın durumu API'den OKUNAMIYOR (yukarıya bkz.), yani "onarılmış mı"
     diye ayırt edecek bir gerçek kaynak yok.
  b. Hasar üç AYRI olaydan geliyor ve üçüncüsü (2026-09-11, `Küllerimden
     Geç`) ilk iki toplu işlemin commit'lerinde YOK. Git geçmişini ayrıştırıp
     "etkilenen" kümesini kurmak, eksik bir kümeyi KESİNMİŞ gibi gösterirdi.
  c. `state.json`'daki `youtube_privacy` bir AYNA, YouTube gerçeği DEĞİL
     (CLAUDE.md; `latest_release.py:31`) — geçmişi ondan okumak da olmaz.

Zaten doğru olan bir videoya beyanı yeniden yazmak ZARARSIZ: gönderilen
değerler kanal seviyesinde SABİT ve `upload/youtube_upload.py`'nin her
yüklemede KOŞULSUZ gönderdikleriyle birebir aynı (idempotent yeniden-beyan).
Bedeli, etkilenmemiş 10 video için tek seferlik ~510 birim kota.

GİZLİLİK DEĞİŞMEZ — İKİ KAT KORUMA
----------------------------------
  1. Her video kendi MEVCUT gizliliğine yazılır ve o gizlilik `state.json`'dan
     DEĞİL, `videos.list(part="status")` ile YOUTUBE'DAN okunur. Okuma
     başarısızsa video ATLANIR — tahminle yazılmaz (eksik gövde zaten
     korumaya çalıştığımız alanı silen gövdenin ta kendisi olurdu).
  2. GÜVENLİK KEMERİ (`kemer_kontrol`): bu betik hiçbir koşulda bir videoyu
     `unlisted`/`private`'tan `public`'e ÇEVİREMEZ. (1) doğru çalıştığı sürece
     kemerin ateşlenmesi imkânsız — ama `Küllerimden Geç` (`-CQ7MmUygTQ` +
     Shorts `jN78mJrZd3c`) BİLEREK unlisted ve public yapılması kanalın en
     büyük riski olan "inauthentic content" politikasına doğrudan yem
     (CLAUDE.md, "Küllerimden Geç ... public YAPMA"). O kadar pahalı bir hata,
     tek bir mantık satırının doğruluğuna bırakılmaz. Kemer video kimliğine
     DEĞİL, geçişin YÖNÜNE bakıyor — yani yarın eklenecek videolar da kapsam
     içinde. Koruma testi: `tests/test_ai_beyani_onar.py`.

KURU KOŞU VARSAYILAN
--------------------
Gerçek yazım için AÇIK bir `--uygula` bayrağı gerekir. Kuru koşu ağa YAZMAZ
ama OKUR (video başına 1 birim) — mevcut gizliliği tahmin etmek yerine
gerçekten okumak, kuru koşunun raporunu güvenilir kılan şeyin ta kendisi.

KOTA
----
Video başına: 1 (`videos.list`) + 50 (`videos.update`) = 51 birim.
Günlük tavan 10.000 ve saatlik yükleme hattı video başına ~1600 birim yiyor,
bu yüzden `--limit` VARSAYILAN olarak küçük (`VARSAYILAN_LIMIT`): bir koşu
kotanın ~%6'sını alır, iş birkaç koşuya yayılır. `quotaExceeded` gelirse
TEMİZ DURULUR — o ana kadarki ilerleme diskte, bir sonraki koşu kaldığı
yerden devam eder.

DEVAM EDEBİLİRLİK — neden state.json'a DEĞİL, ayrı bir dosyaya
--------------------------------------------------------------
Onarılan videolar `upload/ai_beyani_onarim.json`'a (`DURUM_DOSYASI`) video
kimliği bazında damgalanıyor. `state.json`'a bir `ai_beyani_onarildi_at`
damgası da düşünüldü ve ÜÇ sebeple seçilmedi:

  * Damga VİDEO bazlı, state ise PROJE bazlı: bir projenin uzun formatı
    onarılıp Shorts'u kotaya takılabiliyor. Proje seviyesindeki tek bir damga
    bu yarım durumu ANLATAMAZ, yani devam edebilirlik yalan söylerdi.
  * `state.json` kataloğun kalıcı verisi ve git'te izleniyor; tek seferlik bir
    onarım kampanyasının izi oraya kalıcı olarak girmemeli.
  * Bu dosya bittiğinde SİLİNEBİLİR; state.json silinemez.

Yazım yine de ATOMİK: `state_io._atomik_yaz` kullanılıyor (`.tmp` + `fsync` +
`os.replace`). Yeni bir atomik yazıcı YAZILMADI — bu desen bu depoda bir kez
çoğaltılıp sorun olmuştu (bkz. `state_io.py` docstring'i), ikinci kez
çoğaltmanın anlamı yok. Yarıda kesilen bir koşu (Ctrl+C, kota, ağ) en fazla
"son video onarıldı ama damgası yazılamadı" durumunu bırakır; o videonun
bir sonraki koşuda yeniden yazılması ZARARSIZ (idempotent).
"""

import argparse
import json
import os
import sys
import time

UPLOAD_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(UPLOAD_DIR)
sys.path.insert(0, UPLOAD_DIR)
sys.path.insert(0, REPO)

# Windows konsolu ANSI kod sayfasında (cp1254) açılıyor ve bu betiğin bastığı
# proje adları Türkçe. `tiktok_publish_plan.py`'de aynı eksiklik modülü
# BÜTÜNÜYLE kullanılamaz yapmıştı (UnicodeEncodeError).
for _akis in (sys.stdout, sys.stderr):
    try:
        _akis.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

import set_privacy
import state_io
import uyumluluk
from gizli_maskele import maskele, maskele_istisna
from youtube_auth import get_authenticated_service

# Kendi log dosyası — `auto_process.log`'a YAZILMIYOR: `watch_projects.py`'nin
# nabız gözcüsü (`_heartbeat_check`) makine arızasını o dosyanın mtime'ından
# anlıyor. Elle çalıştırılan bir onarım betiğinin oraya yazması, ölmüş bir
# otomasyonu "canlı" göstermek demekti (tests/conftest.py'nin 2. maddesiyle
# aynı zarar).
LOG_PATH = os.path.join(REPO, "ai_beyani_onar.log")

# İlerleme dosyası. Adının `DURUM_DOSYASI` olması BİLİNÇLİ: `tests/conftest.py`
# bu addaki her repo-içi yolu otomatik olarak geçici klasöre çekiyor, yani
# hiçbir test (bugün yazılanlar dahil değil, YARIN yazılacaklar dahil) gerçek
# ilerleme dosyasını kirletemiyor.
DURUM_DOSYASI = os.path.join(UPLOAD_DIR, "ai_beyani_onarim.json")

# state.json'daki video kimliği alanları. (etiket, anahtar) — etiket sadece
# log içindir.
VIDEO_ANAHTARLARI = (
    ("uzun", "youtube_video_id"),
    ("shorts", "youtube_shorts_video_id"),
)

# YouTube Data API v3 birim maliyetleri (resmî tablo).
LIST_BIRIMI = 1
UPDATE_BIRIMI = 50
VIDEO_BASINA_BIRIM = LIST_BIRIMI + UPDATE_BIRIMI
GUNLUK_KOTA = 10000

# Koşu başına en fazla kaç video. 12 x 51 = 612 birim = günlük kotanın ~%6'sı;
# saatlik yükleme hattı (video başına ~1600 birim) rahatça sığmaya devam eder.
# Tamamını tek koşuda yapmak için: --limit 100 (42 video = ~2.142 birim = %21).
VARSAYILAN_LIMIT = 12

# Kemerin kapattığı geçişler: bu gizliliklerden `public`'e ASLA çıkılmaz.
YUKSELTILEMEZ_GIZLILIKLER = ("unlisted", "private")

# `quotaExceeded` imzaları. Metin üzerinden bakılıyor: googleapiclient'ın
# `HttpError`'ı da, taklit/sarmalayıcı istisnalar da aynı sözcüğü taşıyor ve
# tek bir istisna tipine bağlanmak bu kontrolü kütüphane sürümüne bağımlı
# yapardı.
KOTA_IMZALARI = (
    "quotaexceeded",
    "dailylimitexceeded",
    "ratelimitexceeded",
    "userratelimitexceeded",
)


class GizlilikYukseltmeHatasi(RuntimeError):
    """Güvenlik kemeri ateşlendi: unlisted/private -> public denemesi."""


class KotaBitti(RuntimeError):
    """YouTube kotası tükendi — koşu TEMİZ durur, ilerleme korunur."""


def log(mesaj: str) -> None:
    """Tek satır log. Maskeleme YAZMADAN ÖNCE (auto_process.log ile aynı
    desen); log'a yazamamak onarımı ASLA durdurmamalı."""
    satir = "[%s] %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), maskele(mesaj))
    print(satir)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(satir + "\n")
    except OSError:
        pass


def _durum_oku(yol: str = None) -> dict:
    """İlerleme dosyasını okur. Bozuk/eksikse BOŞ sözlük (onarım baştan
    başlar; zararsız, çünkü yeniden yazmak idempotent)."""
    yol = yol or DURUM_DOSYASI
    try:
        with open(yol, encoding="utf-8") as f:
            veri = json.load(f)
    except (OSError, ValueError):
        return {}
    return veri if isinstance(veri, dict) else {}


def _durum_yaz(veri: dict, yol: str = None) -> None:
    """İlerleme dosyasını ATOMİK yazar (`state_io` — yeni yazıcı YOK)."""
    state_io._atomik_yaz(yol or DURUM_DOSYASI, veri)


def onarildi_mi(durum: dict, video_id: str) -> bool:
    return bool(durum.get(video_id))


def hedef_videolar(kokler=None, proje_filtresi: str = None) -> list:
    """ÜÇ içerik kökündeki state.json'lardan video hedeflerini TÜRETİR.

    Sabit kimlik listesi YOK (gerekçe: modül docstring'i). Dönen her öğe:
    `{"proje": <klasör>, "ad": <klasör adı>, "etiket": "uzun"/"shorts",
      "video_id": ...}`
    """
    hedefler = []
    for klasor in uyumluluk.proje_klasorleri(kokler):
        durum_yolu = os.path.join(klasor, "state.json")
        try:
            with open(durum_yolu, encoding="utf-8") as f:
                durum = json.load(f)
        except (OSError, ValueError):
            # Bozuk/eksik state: bu betik YAYIN yapmıyor, sadece mevcut
            # videoları onarıyor — kimliği okunamayan projeyi atlamak doğru.
            continue
        if not isinstance(durum, dict):
            continue
        ad = os.path.basename(klasor)
        if proje_filtresi and proje_filtresi.lower() not in ad.lower():
            continue
        for etiket, anahtar in VIDEO_ANAHTARLARI:
            video_id = durum.get(anahtar)
            if isinstance(video_id, str) and video_id.strip():
                hedefler.append({
                    "proje": klasor,
                    "ad": ad,
                    "etiket": etiket,
                    "video_id": video_id.strip(),
                })
    return hedefler


def kota_hatasi_mi(e: BaseException) -> bool:
    metin = ("%s %s" % (type(e).__name__, e)).lower()
    return any(imza in metin for imza in KOTA_IMZALARI)


def mevcut_status(youtube, video_id: str):
    """Videonun GÜNCEL `status` sözlüğü (YouTube'dan). Okunamazsa None.

    `state.json`'daki `youtube_privacy` BİLEREK kullanılmıyor: o bir AYNA,
    YouTube gerçeği değil (CLAUDE.md, `latest_release.py:31`). Kota hatası
    burada `KotaBitti`ye çevriliyor ki koşu "atla" değil "temiz dur" yapsın.
    """
    try:
        yanit = youtube.videos().list(part="status", id=video_id).execute()
    except Exception as e:                      # noqa: BLE001 - sınıfa değil imzaya bakıyoruz
        if kota_hatasi_mi(e):
            raise KotaBitti(maskele_istisna(e))
        log("  HATA (status okunamadı, video ATLANDI): %s" % maskele_istisna(e))
        return None
    ogeler = yanit.get("items") or []
    if not ogeler:
        return None
    return ogeler[0].get("status") or {}


def _hedef_gizlilik(mevcut: str) -> str:
    """Yazılacak gizlilik = OKUNAN gizlilik. Değişiklik YOK.

    Ayrı bir fonksiyon olması bilinçli: güvenlik kemerinin gerçek boru hattı
    içinde ateşlendiğini gösteren test bu dikişten giriyor (bu fonksiyon
    bozulsa bile kemer yazımı durduruyor mu?).
    """
    return mevcut


def kemer_kontrol(mevcut: str, yazilacak: str) -> None:
    """GÜVENLİK KEMERİ: unlisted/private -> public geçişi ASLA yapılamaz.

    Video kimliğine göre DEĞİL, geçişin yönüne göre çalışıyor — sabit bir
    kimlik listesi yarın eklenen bir videoyu kapsamazdı (`Küllerimden Geç`
    gerekçesi: modül docstring'i).
    """
    if mevcut in YUKSELTILEMEZ_GIZLILIKLER and yazilacak == "public":
        raise GizlilikYukseltmeHatasi(
            "GÜVENLİK KEMERİ: %s -> public engellendi. Bu betik gizlilik "
            "DEĞİŞTİRMEZ, sadece AI beyanını geri yazar." % mevcut
        )
    if mevcut != yazilacak:
        raise GizlilikYukseltmeHatasi(
            "GÜVENLİK KEMERİ: gizlilik değiştirilemez (%s -> %s)"
            % (mevcut, yazilacak)
        )


def onar(youtube=None, limit: int = VARSAYILAN_LIMIT, uygula: bool = False,
         kokler=None, proje: str = None, durum_yolu: str = None) -> dict:
    """Bekleyen videoların AI beyanını geri yazar (varsayılan: KURU KOŞU).

    `youtube` verilmezse kimlik doğrulama YAPILIR — kuru koşu da mevcut
    gizliliği gerçekten okur (video başına 1 birim).
    """
    hedefler = hedef_videolar(kokler, proje)
    durum = _durum_oku(durum_yolu)
    bekleyen = [h for h in hedefler if not onarildi_mi(durum, h["video_id"])]
    planlanan = bekleyen[:max(0, limit)]

    ozet = {
        "hedef": len(hedefler),
        "bekleyen": len(bekleyen),
        "planlanan": len(planlanan),
        "onarilan": 0,
        "kuru": 0,
        "atlanan": 0,
        "engellenen": 0,
        "hatali": 0,
        "kota_durdu": False,
        "kesildi": False,
        "tahmini_birim": len(planlanan) * (
            VIDEO_BASINA_BIRIM if uygula else LIST_BIRIMI),
    }

    log("AI beyanı onarımı — mod: %s" % ("UYGULA" if uygula else "KURU KOŞU"))
    log("  hedef video: %d, onarılmamış: %d, bu koşuda: %d (limit %d)"
        % (ozet["hedef"], ozet["bekleyen"], ozet["planlanan"], limit))
    log("  kota tahmini: ~%d birim (günlük tavan %d)"
        % (ozet["tahmini_birim"], GUNLUK_KOTA))
    if not planlanan:
        log("  yapılacak iş yok.")
        ozet["kalan"] = len(bekleyen)
        return ozet

    if youtube is None:
        youtube = get_authenticated_service()

    for hedef in planlanan:
        video_id = hedef["video_id"]
        etiket = "%s [%s] %s" % (hedef["ad"], hedef["etiket"], video_id)
        try:
            status = mevcut_status(youtube, video_id)
        except KotaBitti as e:
            log("  KOTA BİTTİ (okuma): %s — TEMİZ DURULUYOR, ilerleme korundu"
                % maskele_istisna(e))
            ozet["kota_durdu"] = True
            break
        except KeyboardInterrupt:
            log("  Ctrl+C — TEMİZ DURULUYOR, ilerleme korundu")
            ozet["kesildi"] = True
            break

        mevcut = (status or {}).get("privacyStatus")
        if not status or not mevcut:
            # Tahminle YAZMA: elde mevcut status olmadan gönderilecek gövde,
            # korumaya çalıştığımız alanları silen gövdenin ta kendisidir.
            log("  ATLANDI (gizlilik okunamadı): %s" % etiket)
            ozet["atlanan"] += 1
            continue

        yazilacak = _hedef_gizlilik(mevcut)
        try:
            kemer_kontrol(mevcut, yazilacak)
        except GizlilikYukseltmeHatasi as e:
            log("  ENGELLENDİ: %s — %s" % (etiket, e))
            ozet["engellenen"] += 1
            continue

        if not uygula:
            log("  [KURU] %s — gizlilik %s olarak KALACAK, AI beyanı yeniden "
                "yazılacak (~%d birim)" % (etiket, yazilacak, VIDEO_BASINA_BIRIM))
            ozet["kuru"] += 1
            continue

        govde = set_privacy.guvenli_status_govdesi(status, yazilacak)
        try:
            youtube.videos().update(
                part="status",
                body={"id": video_id, "status": govde},
            ).execute()
        except KeyboardInterrupt:
            log("  Ctrl+C — TEMİZ DURULUYOR, ilerleme korundu")
            ozet["kesildi"] = True
            break
        except Exception as e:                  # noqa: BLE001
            if kota_hatasi_mi(e):
                log("  KOTA BİTTİ (yazma): %s — TEMİZ DURULUYOR, ilerleme "
                    "korundu" % maskele_istisna(e))
                ozet["kota_durdu"] = True
                break
            log("  HATA (yazılamadı): %s — %s" % (etiket, maskele_istisna(e)))
            ozet["hatali"] += 1
            continue

        durum[video_id] = {
            "proje": hedef["ad"],
            "etiket": hedef["etiket"],
            "gizlilik": yazilacak,
            "ai_beyani_onarildi_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        # Her videodan SONRA yazılıyor (toplu değil): kota/Ctrl+C/ağ kesintisi
        # en fazla TEK videoluk tekrar maliyeti bıraksın.
        _durum_yaz(durum, durum_yolu)
        ozet["onarilan"] += 1
        log("  ONARILDI: %s — gizlilik %s (değişmedi), AI beyanı geri yazıldı"
            % (etiket, yazilacak))

    kalan = len([h for h in hedefler if not onarildi_mi(durum, h["video_id"])])
    ozet["kalan"] = kalan
    log("Bitti — onarılan %d, kuru %d, atlanan %d, engellenen %d, hatalı %d; "
        "KALAN %d" % (ozet["onarilan"], ozet["kuru"], ozet["atlanan"],
                      ozet["engellenen"], ozet["hatali"], kalan))
    if kalan and uygula:
        log("  Kalan videolar için betiği TEKRAR çalıştır (kaldığı yerden "
            "devam eder).")
    return ozet


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Geçmişte silinmiş zorunlu AI beyanını geri yazar. "
                    "Gizliliği DEĞİŞTİRMEZ. Varsayılan: kuru koşu.")
    ap.add_argument("--uygula", action="store_true",
                    help="GERÇEKTEN yaz (bayrak verilmezse sadece kuru koşu)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Kuru koşu (zaten varsayılan; --uygula'yı ezer)")
    ap.add_argument("--limit", type=int, default=VARSAYILAN_LIMIT,
                    help="Bu koşuda en fazla kaç video (varsayılan %d)"
                         % VARSAYILAN_LIMIT)
    ap.add_argument("--proje", default=None,
                    help="Sadece adı bu metni içeren projeler")
    args = ap.parse_args(argv)

    # İkisi de verilmişse GÜVENLİ olan kazanır.
    uygula = args.uygula and not args.dry_run
    if args.uygula and args.dry_run:
        log("UYARI: --uygula ve --dry-run birlikte verildi; KURU KOŞU yapılıyor.")

    ozet = onar(limit=args.limit, uygula=uygula, proje=args.proje)
    if not uygula:
        log("Hiçbir şey yazılmadı. Gerçek onarım için: --uygula")
    return 0


if __name__ == "__main__":
    sys.exit(main())
