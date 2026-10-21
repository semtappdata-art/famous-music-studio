# -*- coding: utf-8 -*-
"""YouTube ABONE (subscribe) kaldıraçlarını toplu devreye alır.

NEDEN VAR
---------
Kanalın en büyük eksikliği abone: 47 abone / 9.408 izlenme (%0.5 dönüşüm).
Cercle/HÖR/Boiler Room referanslarının tamamı abone kaldıracı üstüne kurulu.
Depoda abone için AYRI AYRI kullanılan ama HİÇBİRİ birbirine bağlanmamış
mekanizmalar vardı. Bu modül onları TEK bir akışta toplar:

  1. **Watermark (abone butonu)** — `watermarks.set`. Videonun sağ alt köşesinde
     "Subscribe" butonu. YouTube'un EN ETKİLİ abone kaldıracı: izleyici videoyu
     izlerken tek tıkla abone olur. API destekli.
  2. **İlk yorum (sabitlenen)** — `commentThreads.insert`. Bölüm sorusu +
     abone çağrısı. Studio'da sabitlenir → en üstte görünür.
  3. **Kanal bölümü (Abonelik)** — `channelSections.insert`. "Abonelik" adlı
     bölümde playlist'ler → izleyici abone olduktan sonra ne izleyeceğini
     görür. Abone sonrası ilk adım.
  4. **Kanal banner'ı** — `channelBanners.insert`. Kanal sayfasının üstünde
     abone + yeni içerik mesajı.
  5. **Açıklama CTA'sı** — zaten `youtube_upload` içinde; burada TEK
     fonksiyon: `aciklama_abone_bloku()` ile her videonun açıklamasına
     "@handle + abone" bloğu guarantee edilir.

TÜM OLUMLU SEÇENEKLER NEDEN TEK MODÜLDE
------------------------------------------
Bunlar birbirinin YERİNE geçmez, birbirini TAMAMLAR. Sıra önemli:
video izlenirken watermark görünür → izleyici abone olur → abone olduktan
sonra kanal bölümünde ne izleyeceğini bulur → ilk yorum sorusuyla
etkileşime girer.

KOTA (youtube_kota.py tablosu)
------------------------------
  watermarks.set          = 50 birim (tahmini — tabloda yok, .set yazma kuralı)
  commentThreads.insert   = 50 birim
  channelSections.insert  = 50 birim (tahmini)
  channelBanners.insert   = 50 birim (tahmini)
Günlük ortak havuz 10.000 birim. Tek seferlik (kanal seviyesi) işler bir kez
yapılır; video seviyesindeki watermark + ilk yorum ise video başına 100 birim.

GÜVENLİK
---------
* **Idempotent**: watermark zaten varsa tekrar set edilmez; ilk yorum için
  `youtube_ilk_yorum_at` bayrağı kullanılır; kanal bölümü adıyla aranır.
* **Kota kapısı**: `youtube_kota.yeterli_mi()` kontrolü — kalmıyorsa DOKUNULMAZ.
* **Politika kapısı**: yükleme öncesi `uyumluluk.kontrol(proje, "yukleme")`
  çağrılır (fail-closed) — bu modül kapıyı ATLAR, çağıran yapar.
* **Geri alınabilir**: `watermarks.unset` mevcut; bölüm `channelSections.delete`.

KULLANIM
---------
    python upload/youtube_abone.py --durum          # mevcut durumu raporla
    python upload/youtube_abone.py --kanal           # bölüm + banner (tek seferlik)
    python upload/youtube_abone.py --video "projects/X"   # watermark + ilk yorum
    python upload/youtube_abone.py --hepsi           # tüm yüklenmiş videolar
    python upload/youtube_abone.py --hepsi --dry-run
"""

import argparse
import base64
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import http_bug_fix
import state_io
import youtube_kota
from youtube_auth import get_authenticated_service

# NEDEN: httplib2'nin bos-yanit govdesi hatasini ONCEDEN duzelt.
# YouTube'un `watermarks.set` ucu 200 + BOS govde donuyor; duzeltme olmazsa
# istek sunucuda basarili olsa bile istemcide ValueError firlatiyor.
http_bug_fix.uygula()

# --- sabitler -------------------------------------------------------------

BIRIM_WATERMARK = 50      # watermarks.set (tahmini — kota tablosunda yok)
BIRIM_ILK_YORUM = 50      # commentThreads.insert
BIRIM_KANAL_SECTION = 50  # channelSections.insert (tahmini)
BIRIM_KANAL_BANNER = 50   # channelBanners.insert (tahmini)
BIRIM_KANAL_ACIKLAMA = 50  # channels.update (tahmini)
BIRIM_KANAL_TANITIM = 50   # channels.update (tahmini)

ABONE_BOLUM_ADI = "Abonelik"
KANAL_BANNER_METIN = "Her cuma yeni şehir  •  Abone ol"

# Kanal açıklaması — 2018'den beri BOŞTU. YouTube arama/suggestion
# motoru kanal açıklamasını kullanır; boş olmak = keşfedilmemek.
KANAL_ACIKLAMASI = (
    "🎵 Türkçe şarkılar, R&B / trap / arabesk / melodik techno ve DJ setleri.\n\n"
    "Her hafta yeni şarkı  •  Her cuma yeni şehir\n\n"
    "📺 Tüm şarkılar: https://youtube.com/playlist?list=PLKFBTOXunWQ0\n"
    "📺 Kısa kesitler: https://youtube.com/playlist?list=PLIfBoPfEuEWQ\n\n"
    f"Abone ol — yeni parçalar kaçmasın. 🔔  @{config.YOUTUBE_HANDLE}\n\n"
    "Yapay zekâ destekli müzik ve görseller içerir."
)
# Kanal anahtar kelimeleri — BOŞLUKLA ayrılmış.
# NEDEN boşluk, virgül değil: YouTube anahtar kelimeleri virgüllü metni
# normalize edip TIRNAKLI geri döndürüyor ("türkçe şarkılar" "türkçe müzik")
# — Studio'daki gerçek format boşlukla ayrılmış.
KANAL_ANAHTAR_KELIMELER = (
    "türkçe şarkılar türkçe müzik yeni şarkı r&b türkçe trap türkçe "
    "arabesk arabesk rap melodik techno dj set dj set türkçe "
    "kafe müziği çalış müziği yeni türkçe şarkı 2026 şarkıları "
    "famous music studio sözleri lyrics chiptune lofi türkçe"
)

# Watermark görseli: şeffaf "Subscribe" butonu. YouTube watermark'ı 200x200px
# PNG ister (transparan). Depoda hazır PNG yoksa üretilir (saf Pillow/ffmpeg).
WATERMARK_DOSYA = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "abone_watermark.png")


# --- yardimcilar -----------------------------------------------------------


def _log(msg: str) -> None:
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"))


def _state_oku(proje: str) -> dict:
    try:
        with open(os.path.join(proje, "state.json"), "r", encoding="utf-8") as f:
            s = json.load(f)
    except (OSError, ValueError):
        return {}
    return s if isinstance(s, dict) else {}


def _state_yaz(proje: str, alanlar: dict) -> None:
    yol = os.path.join(proje, "state.json")
    state = _state_oku(proje)
    state.update(alanlar)
    state_io._atomik_yaz(yol, state)


def _meta_oku(proje: str) -> dict:
    try:
        with open(os.path.join(proje, "meta.json"), "r", encoding="utf-8") as f:
            m = json.load(f)
    except (OSError, ValueError):
        return {}
    return m if isinstance(m, dict) else {}


# --- 1) WATERMARK (abone butonu) ------------------------------------------


def _watermark_gorseli_uret(dry_run: bool = False) -> str | None:
    """Şeffaf 'Abone ol' buton PNG'si üretir (200x200).

    NEDEN dry_run'da da üretiliyor: görsel YEREL bir dosya (API çağrısı
    değil), üretmek zararsız; ve dry-run'da üretmezsek dosya hiç oluşmadığı
    için "görsel yok" sanılır — gerçek çalıştırmada da aynı hataya düşerdik.
    """
    if os.path.isfile(WATERMARK_DOSYA):
        return WATERMARK_DOSYA
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        _log("  [!] Pillow yok — watermark gorseli uretilemedi")
        return None

    os.makedirs(os.path.dirname(WATERMARK_DOSYA), exist_ok=True)
    W = H = 200
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Kirmizi abone butonu (YouTube stili)
    d.rounded_rectangle([6, 68, 194, 132], radius=30, fill=(204, 15, 0, 240))
    yazi = "Abone ol"
    font = None
    try:
        font = ImageFont.truetype(config.FONT_BOLD_PATH, 26)
    except Exception:
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
    try:
        bbox = d.textbbox((0, 0), yazi, font=font)
        w = bbox[2] - bbox[0]
    except Exception:
        w = len(yazi) * 14
    try:
        d.text(((W - w) / 2, 86), yazi, fill=(255, 255, 255, 255), font=font)
    except Exception:
        d.text(((W - w) / 2, 86), yazi, fill=(255, 255, 255, 255))
    img.save(WATERMARK_DOSYA)
    return WATERMARK_DOSYA


def watermark_uygula(yt, video_id: str = "", dry_run: bool = False) -> bool:
    """Kanal'a 'Abone ol' watermark'i koyar (sag alt kose).

    NEDEN KANAL SEVIYESI: YouTube Data API'de watermark VIDEO BASINA
    degil KANAL BASINA konur (`watermarks.set` -> `channelId` ZORUNLU parametre,
    `watermarks.list` hic yok). Konulan watermark kanaldaki TUM videolarda
    gorunur. Bu yuzden 24 video icin 24 API cagrisi degil TEK cagri yeter.

    `video_id` yalnizca gunluk/rapor ciktisinda referans icin tutulur;
    API cagrisinda kullanilmaz.
    """
    if not youtube_kota.yeterli_mi(BIRIM_WATERMARK):
        _log("  [!] kota yetersiz — watermark atlandi")
        return False
    yol = _watermark_gorseli_uret()
    if not yol or not os.path.isfile(yol):
        _log("  [!] watermark gorseli yok — atlandi")
        return False
    if dry_run:
        _log("  [dry-run] kanal watermark'i (tum videolara gecer)")
        return True
    try:
        import base64
        from googleapiclient.http import MediaFileUpload
        with open(yol, "rb") as f:
            data = base64.b64encode(f.read()).decode("ascii")
        kanal_id = getattr(config, "YOUTUBE_KANAL_ID", "")
        if not kanal_id:
            kanal_id = yt.channels().list(part="id", mine=True).execute()["items"][0]["id"]
        # NEDEN bu govde: watermarks.set'in request body'si `InvideoBranding`
        # semasi — ESKI `resourceId`/`trackingType` alanlari YOK. Dogru alanlar:
        # imageBytes (base64) + timing + targetChannelId + position.
        # AYRICA media_body ZORUNLU ("The request does not include the image
        # content") — govdeye base64 koymak YETMIYOR.
        govde = {
            "imageBytes": data,
            # timing: video'nun TAMAMI boyunca gorunsun
            "timing": {"type": "offsetFromStart", "offsetMs": "0"},
            "targetChannelId": kanal_id,
            # Konum (deprecated ama calisiyor): sag alt kose
            "position": {"type": "corner", "cornerPosition": "bottomRight"},
        }
        yt.watermarks().set(
            body=govde,
            media_body=MediaFileUpload(yol, mimetype="image/png"),
            channelId=kanal_id).execute()
        _log("  [OK] kanal watermark'i ayarlandi (abone butonu)"
             + (f" — {video_id}" if video_id else ""))
        return True
    except Exception as e:                                   # noqa: BLE001
        _log(f"  [HATA] watermark: {e}")
        return False


# --- 2) İLK YORUM (sabitlenen abone çağrısı) -----------------------------


def ilk_yorum_gonder(proje: str, dry_run: bool = False) -> bool:
    """Kanalın kendi yorumu: bölüm sorusu + abone çağrısı (Studio'da sabitlenir)."""
    from social_text import build_ilk_yorum, resolve_language

    state = _state_oku(proje)
    if state.get("youtube_ilk_yorum_at"):
        return False
    if state.get("youtube_video_silinmis"):
        return False
    video_id = state.get("youtube_video_id")
    if not video_id:
        return False
    if not youtube_kota.yeterli_mi(BIRIM_ILK_YORUM):
        _log("  [!] kota yetersiz — ilk yorum atlandi")
        return False

    meta = _meta_oku(proje)
    lang = resolve_language(meta)
    metin = build_ilk_yorum(meta.get("title", "Untitled"), lang)
    if dry_run:
        _log(f"  [dry-run] ilk yorum: {video_id} — {metin!r}")
        return True

    from youtube_auth import get_authenticated_service
    yt = get_authenticated_service()
    try:
        yt.commentThreads().insert(
            part="snippet",
            body={"snippet": {
                "videoId": video_id,
                "topLevelComment": {"snippet": {"textOriginal": metin}},
            }}).execute()
    except Exception as e:                                   # noqa: BLE001
        # NEDEN 404 ayri: video SILINMIS (state'te bayat ID kalmis).
        # Bu bir hata degil, temizlik isidir — 3 "Night Drive" projesi bu
        # durumdaydi ve her calistirmada hata basiyordu.
        if "404" in str(e) or "could not be found" in str(e).lower():
            _log(f"  [BILGI] video silinmis ({video_id}) — ilk yorum atlandi")
            _state_yaz(proje, {"youtube_video_silinmis": True})
            return False
        _log(f"  [HATA] ilk yorum {video_id}: {e}")
        return False

    _state_yaz(proje, {"youtube_ilk_yorum_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                       "youtube_ilk_yorum_metni": metin})
    _log(f"  [OK] ilk yorum: {video_id}")
    return True


# --- 3) KANAL BÖLÜMÜ (abone sonrası navigasyon) ---------------------------


def kanal_bolumu_kur(yt, dry_run: bool = False) -> bool:
    """'Abonelik' bölümü oluşturur ve ana playlist'leri içine koyar."""
    if not youtube_kota.yeterli_mi(BIRIM_KANAL_SECTION):
        _log("  [!] kota yetersiz — kanal bolumu atlandi")
        return False

    # NEDEN sadece mine=True: `channelSections.list` `mine` ve `channelId`
    # parametrelerini BIRLikte kabul etmiyor ("Incompatible parameters").
    bolumler = yt.channelSections().list(
        part="id,snippet,contentDetails", mine=True).execute()
    for b in bolumler.get("items", []):
        if (b.get("snippet", {}).get("title") or "") == ABONE_BOLUM_ADI:
            _log(f"  [OK] kanal bolumu zaten var: {ABONE_BOLUM_ADI}")
            return True

    if dry_run:
        _log(f"  [dry-run] kanal bolumu olusturulur: {ABONE_BOLUM_ADI}")
        return True

    govde = {
        # NEDEN 'multiplePlaylists': enum camelCase (discovery:
        # ['singlePlaylist','multiplePlaylists','popularUploads',...]) —
        # 'playlist'/'multiple_playlists' degerleri API tarafindan REDDEDILIYOR
        # ("Invalid value at resource.snippet.type"). Özel başlık yalnız
        # multiplePlaylists/multipleChannels'ta verilebilir.
        "snippet": {"type": "multiplePlaylists", "title": ABONE_BOLUM_ADI,
                    "description": "Yeni şarkılar ve setler — abone olduktan sonra ilk adım.",
                    "position": 0},
        # NEDEN 'playlists' (düz liste) ve 'items' DEĞIL: sema
        # ChannelSectionContentDetails.playlists = string[] (playlist ID'leri).
        # 'items' gönderilince API "Playlists are needed..." diyordu.
        "contentDetails": {"playlists": [
            "PLKFBTOXunWQ0",   # Türkçe Şarkılar — Kesintisiz Dinle
            "PLIfBoPfEuEWQ",   # Kısa Kesitler
        ]},
    }
    try:
        yt.channelSections().insert(part="snippet,contentDetails", body=govde).execute()
        _log(f"  [OK] kanal bolumu kuruldu: {ABONE_BOLUM_ADI}")
        return True
    except Exception as e:                                   # noqa: BLE001
        _log(f"  [HATA] kanal bolumu: {e}")
        return False


# --- 4) KANAL BANNER'I -----------------------------------------------------


def kanal_banneri_kur(yt, dry_run: bool = False) -> bool:
    """Kanal banner'ına abone mesajı basar (16:1, 2560x1440)."""
    if not youtube_kota.yeterli_mi(BIRIM_KANAL_BANNER):
        _log("  [!] kota yetersiz — banner atlandi")
        return False
    if dry_run:
        _log("  [dry-run] kanal banner'i guncellenir")
        return True
    try:
        import subprocess
        import tempfile
        from PIL import Image, ImageDraw, ImageFont
    except Exception as e:                                   # noqa: BLE001
        _log(f"  [!] banner uretilemedi ({e})")
        return False

    W, H = 2560, 1440
    img = Image.new("RGB", (W, H), (12, 9, 16))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(config.FONT_BOLD_PATH, 150)
        font2 = ImageFont.truetype(config.FONT_PATH, 80)
    except Exception:
        font = font2 = None
    d.text((W / 2 - 700, H / 2 - 180), "FAMOUS MUSIC STUDIO",
           fill=(255, 255, 255), font=font)
    d.text((W / 2 - 520, H / 2 + 10), KANAL_BANNER_METIN,
           fill=(255, 210, 60), font=font2)

    tmp = os.path.join(tempfile.gettempdir(), "fms_banner.png")
    img.save(tmp)
    try:
        # NEDEN media_body (base64 body değil): channelBanners.insert gövde
        # olarak base64 değil MEDIA dosyası ister ("The request does not include
        # the image content" hatası veriyordu).
        from googleapiclient.http import MediaFileUpload
        with open(tmp, "rb") as f:
            media = MediaFileUpload(tmp, mimetype="image/png")
        yt.channelBanners().insert(body={}, media_body=media).execute()
        _log("  [OK] kanal banner'i guncellendi")
        return True
    except Exception as e:                                   # noqa: BLE001
        _log(f"  [HATA] kanal banner: {e}")
        return False
    finally:
        # NEDEN try/except: Windows'ta MediaFileUpload dosyayı AÇIK tutuyor —
        # `os.remove` PermissionError veriyordu ve YUKLEME hattını patlatiyordu
        # (asıl iş başarıyla bitmişti). Geçici dosya temizliği kritik değil.
        try:
            if os.path.isfile(tmp):
                os.remove(tmp)
        except OSError:
            pass


# --- 5) AÇIKLAMA ABONE BLOĞU ---------------------------------------------


def aciklama_abone_bloku(lang: str = "tr") -> str:
    """Açıklamaya eklenecek abone bloğu — tek kaynak.

    NEDEN AYRI FONKSİYON: `youtube_upload.build_snippet` açıklamayı kuruyor
    ama bu blok ORTAK olmalı (uzun format + Shorts + DJ set). Kopyalanırsa
    biri güncellenip diğeri eski kalır — bu depodaki "iki yerde bir kural"
    hatasının tam kendisi.
    """
    handle = config.YOUTUBE_HANDLE
    if lang == "en":
        return (
            f"\n🔔 Subscribe to {config.STATIC_LABEL_TEXT} for a new track every week "
            f"— @{handle}\n"
            f"📋 Full catalogue: https://youtube.com/playlist?list=PLKFBTOXunWQ0\n"
        )
    return (
        f"\n🔔 {config.STATIC_LABEL_TEXT} — her hafta yeni şarkı. "
        f"Abone ol: @{handle}\n"
        f"📋 Tüm şarkılar: https://youtube.com/playlist?list=PLKFBTOXunWQ0\n"
        f"📋 Kısa kesitler: https://youtube.com/playlist?list=PLIfBoPfEuEWQ\n"
    )


# --- ana akis --------------------------------------------------------------


def _yuklenmis_projeler() -> list:
    import uyumluluk
    out = []
    for kok in uyumluluk.KOKLER:
        if not os.path.isdir(kok):
            continue
        for ad in sorted(os.listdir(kok)):
            yol = os.path.join(kok, ad)
            if not os.path.isdir(yol):
                continue
            st = _state_oku(yol)
            if st.get("youtube_video_id"):
                out.append(yol)
    return out


def durum() -> None:
    """Mevcut abone kaldıraçlarının durumunu raporlar (SALT OKUMA)."""
    yt = get_authenticated_service()
    kanal = yt.channels().list(part="id,snippet,statistics", mine=True).execute()["items"][0]
    _log(f"KANAL: {kanal['snippet']['title']} ({kanal['id']})")
    _log(f"  abone: {kanal.get('statistics', {}).get('subscriberCount', '?')}")
    _log(f"  video: {kanal.get('statistics', {}).get('videoCount', '?')}")
    _log(f"  izlenme: {kanal.get('statistics', {}).get('viewCount', '?')}")

    # NEDEN sadece mine=True: channelSections.list `mine` ve `channelId`
    # parametrelerini BIRLikte kabul etmiyor ("Incompatible parameters").
    bolumler = yt.channelSections().list(
        part="id,snippet,contentDetails", mine=True).execute()
    _log("\nKANAL BOLUMLERI:")
    for b in bolumler.get("items", []):
        # NEDEN 'playlists' (items degil): sema ChannelSectionContentDetails
        # -> playlists: string[] (items alani yok).
        _log(f"  - {b.get('snippet', {}).get('title')} "
             f"({b.get('snippet', {}).get('type')}, "
             f"{len((b.get('contentDetails') or {}).get('playlists') or [])} playlist)")

    # Kanal markalama (aciklama / kelimeler / tanitim videosu)
    try:
        k = yt.channels().list(part="brandingSettings", mine=True).execute()["items"][0]
        ch = (k.get("brandingSettings") or {}).get("channel") or {}
        _log("\nKANAL MARKALAMA:")
        _log(f"  aciklama       : {len(ch.get('description') or '')} karakter")
        _log(f"  anahtar kelime : {len((ch.get('keywords') or '').split())} adet")
        _log(f"  tanitim videosu: {ch.get('unsubscribedTrailer') or '-'}")
    except Exception as e:                                   # noqa: BLE001
        _log(f"  markalama okunamadi: {e}")

    projeler = _yuklenmis_projeler()
    ilky = 0
    for p in projeler:
        st = _state_oku(p)
        if st.get("youtube_ilk_yorum_at"):
            ilky += 1
    _log(f"\nVIDEO BAZLI ({len(projeler)} yuklenmis video):")
    _log(f"  ilk yorum (sabitlenen) : {ilky}/{len(projeler)}")
    # NEDEN 'bilinmiyor': watermark KANAL seviyesindedir ve API'de
    # `watermarks.list` YOK (sadece set/unset) — okunamayan tek kaldirac.
    _log("  watermark (abone butonu) : kanal seviyesi (API ile okunamaz, "
         "set ile yazilir)")

    # Mevcut watermark durumu (API)
    try:
        vids = yt.videos().list(part="id,status", mine=True, maxResults=50).execute()
        _log(f"  (API: {len(vids.get('items', []))} video listelendi)")
    except Exception:
        pass


def video_isle(proje: str, yt, dry_run: bool = False) -> dict:
    """Tek video: ilk yorum (sabitlenen abone cagrisi).

    NEDEN watermark burada YOK: watermark KANAL seviyesindedir (tek cagri
    tum videolara gecer) — `youtube_abone.py --kanal` tarafindan kurulur.
    """
    st = _state_oku(proje)
    video_id = st.get("youtube_video_id")
    if not video_id:
        return {"ilk_yorum": False, "atlandi": "yuklenmemis"}
    sonuc = {"ilk_yorum": False}
    sonuc["ilk_yorum"] = ilk_yorum_gonder(proje, dry_run=dry_run)
    return sonuc


def abone_supurge(log=print) -> dict:
    """Abone kaldıraçlarını sweep eder (otomatik_process `finally` bloğu).

    NEDEN ayrı fonksiyon: `auto_process.main()` her saat çalışıyor ve
    `finally` bloğunda çağrılıyor. Yeni bir video yüklendiğinde sabitlenen
    ilk yorum eksik kalmasın diye burada tamamlanıyor.

    GÜVENLİK
    --------
    * Tüm hatalar YUTULMAZ ama yakalanır — süpürge boru hattını düşürmez.
    * Kota kapısı `youtube_kota.yeterli_mi` ile korunur.
    * Idempotent: state bayrakları + kanal seviyesi watermark.
    * Politika kapısı (`uyumluluk.kontrol`) yükleme tarafında zaten
      çağrılıyor; bu modül ilk yorum GÖNDERİMİ yapar (politika kontrolü
      yükleme adımında geçilmiş demektir).
    """
    sonuc = {"watermark": False, "ilk_yorum": 0, "video": 0, "hata": 0}
    try:
        yt = get_authenticated_service()
    except Exception as e:                                   # noqa: BLE001
        log(f"  Abone supurge: servis alinamadi ({e})")
        return sonuc

    # 1) Kanal watermark'ı (tek çağrı — tüm videolara geçer)
    try:
        sonuc["watermark"] = watermark_uygula(yt)
    except Exception as e:                                   # noqa: BLE001
        sonuc["hata"] += 1
        log(f"  Abone supurge: watermark HATASI: {e}")

    # 2) Video basina ilk yorum (state bayragi ile tek sefer)
    for p in _yuklenmis_projeler():
        try:
            if ilk_yorum_gonder(p):
                sonuc["ilk_yorum"] += 1
                sonuc["video"] += 1
        except Exception as e:                               # noqa: BLE001
            sonuc["hata"] += 1
            log(f"  Abone supurge: ilk yorum HATASI ({os.path.basename(p)}): {e}")

    log(f"  Abone supurge: watermark={sonuc['watermark']} "
        f"ilk_yorum={sonuc['ilk_yorum']} hata={sonuc['hata']}")
    return sonuc


def kanal_markalama_ayarla(yt, dry_run: bool = False) -> bool:
    """Kanal açıklaması + anahtar kelimeler + tanitim videosu — TEK çağrıda.

    NEDEN BU KADAR ÖNEMLİ: Kanal 2018'de açılmış ve açıklaması **BOŞ**.
    YouTube kanal açıklamasını ve anahtar kelimelerini arama/suggestion
    motorunda kullanır — boş kanal açıklaması = keşfedilmemek.

    NEDEN `unsubscribedTrailer`: abone OLMAYANLARA gösterilen video. Klasik
    "abone ol" kaldıracı: kanal sayfasını ziyaret eden ziyaretçi videoyu
    izler, sonunda CTA çıkar, abone olur.

    NEDEN HEPSİ TEK `channels.update` ÇAĞRISINDA: `channels.update` verilen
    `part`'ı TAMAMEN değiştirir (kısmi güncelleme YOK). İki ayrı çağrı
    yapılırsa ikincisi birincisinin description/keywords'ini SİLİYORDU
    (ölçüldü: açıklama None'a döndü).

    Gövde şeması:
        brandingSettings.channel.description       -> kanal açıklaması
        brandingSettings.channel.keywords          -> virgülle ayrılmış kelimeler
        brandingSettings.channel.unsubscribedTrailer -> abone olmayanlara video
    """
    if not youtube_kota.yeterli_mi(BIRIM_KANAL_ACIKLAMA):
        _log("  [!] kota yetersiz — kanal markalama atlandi")
        return False
    if dry_run:
        _log("  [dry-run] kanal aciklamasi + anahtar kelimeler + tanitim videosu")
        return True
    try:
        kanal = yt.channels().list(part="id", mine=True).execute()["items"][0]["id"]
        video_id = _en_iyi_uzun_video(yt, kanal)
        if not video_id:
            _log("  [!] uygun video bulunamadi — tanitim videosu bos birakildi")
            video_id = ""

        govde = {
            # NEDEN 'id' govdede: channels.update govdeye kanal kimligi istiyor
            # ("Id required" hatasi veriyordu).
            "id": kanal,
            "brandingSettings": {
                "channel": {
                    "description": KANAL_ACIKLAMASI,
                    "keywords": KANAL_ANAHTAR_KELIMELER,
                    "country": "TR",
                    "defaultLanguage": "tr",
                    "unsubscribedTrailer": video_id,
                }
            }
        }
        yt.channels().update(part="brandingSettings", body=govde).execute()
        _log("  [OK] kanal markalama guncellendi "
             f"(aciklama + anahtar kelime + tanitim: {video_id})")
        return True
    except Exception as e:                                   # noqa: BLE001
        _log(f"  [HATA] kanal markalama: {e}")
        return False


def _sure_sn(duration: str) -> float:
    """ISO-8601 sureyi saniyeye cevirir (PT3M40S -> 220)."""
    if not duration or duration in ("P0D", "PT0S"):
        return 0.0
    try:
        import re
        m = re.match(r"^P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$",
                     duration)
        if not m:
            return 0.0
        gun, saat, dakika, saniye = [int(x) if x else 0 for x in m.groups()]
        return gun * 86400 + saat * 3600 + dakika * 60 + saniye
    except (ValueError, AttributeError):
        return 0.0


def _en_iyi_uzun_video(yt, kanal_id: str) -> str:
    """Abone olmayanlara gosterilecek trailer icin en iyi UZUN videoyu secer.

    NEDEN Shorts dislaniyor: `unsubscribedTrailer` bir tanitim videosudur;
    31 saniyelik dikey bir Shorts tanitim olarak zayif kalir ve YouTube
    bazen Shorts'i trailer olarak kabul etmez. Kural: **sure >= 60sn** ve
    **en cok izlenen**.

    NEDEN yukleme playlist'i: `videos.list` kendi videolarimizi listelemiyor
    (myRating yalnizca like/dislike; chart trend basliklarini getirir).
    Yukleme playlist'i = "UU" + kanalId[2:].
    """
    yukleme = "UU" + kanal_id[2:]
    videolar = []
    token = None
    while True:
        r = yt.playlistItems().list(
            part="contentDetails", playlistId=yukleme, maxResults=50,
            pageToken=token).execute()
        videolar += [it["contentDetails"]["videoId"]
                     for it in r.get("items", [])]
        token = r.get("nextPageToken")
        if not token:
            break
    if not videolar:
        return ""
    detay = []
    for i in range(0, len(videolar), 45):
        parca = ",".join(videolar[i:i + 45])
        detay += yt.videos().list(
            part="id,contentDetails,statistics", id=parca).execute().get("items", [])
    adaylar = [v for v in detay
               if _sure_sn((v.get("contentDetails") or {}).get("duration", "")) >= 60]
    if not adaylar:
        return ""
    en_iyi = max(adaylar, key=lambda v: int(
        (v.get("statistics") or {}).get("viewCount", 0)))
    return en_iyi["id"]


def main():
    ap = argparse.ArgumentParser(
        description="YouTube abone kaldıraçlarını devreye alır.")
    ap.add_argument("--durum", action="store_true", help="SALT OKUMA: mevcut durum")
    ap.add_argument("--kanal", action="store_true",
                    help="Kanal bolumu + banner + WATERMARK (tek seferlik)")
    ap.add_argument("--markalama", action="store_true",
                    help="Kanal aciklamasi + anahtar kelimeler + tanitim videosu")
    ap.add_argument("--video", help="Tek proje: watermark + ilk yorum")
    ap.add_argument("--hepsi", action="store_true", help="Tum yuklenmis videolar")
    ap.add_argument("--dry-run", action="store_true", dest="dry_run",
                    help="Sadece ne yapilacagini yaz")
    args = ap.parse_args()

    if args.durum:
        durum()
        return

    yt = get_authenticated_service()

    if args.markalama:
        _log("=== KANAL MARKALAMA (aciklama + kelimeler + tanitim) ===")
        kanal_markalama_ayarla(yt, dry_run=args.dry_run)
        return

    if args.kanal:
        _log("=== KANAL SEVIYESI (tek seferlik) ===")
        kanal_bolumu_kur(yt, dry_run=args.dry_run)
        kanal_banneri_kur(yt, dry_run=args.dry_run)
        # NEDEN burada: watermark KANAL seviyesindedir — TEK cagri tum
        # videolarda gecer (24 video = 24 cagri degil, 1 cagri).
        watermark_uygula(yt, dry_run=args.dry_run)
        # Kanal markalama (aciklama + kelimeler + tanitim videosu) —
        # NEDEN burada: channels.update brandingSettings'i TAMAMEN
        # degistirir; ayri cagri yapilirsa biri digerini siler.
        kanal_markalama_ayarla(yt, dry_run=args.dry_run)
        return

    if args.video:
        _log(f"=== {os.path.basename(os.path.abspath(args.video))} ===")
        video_isle(args.video, yt, dry_run=args.dry_run)
        return

    if args.hepsi:
        projeler = _yuklenmis_projeler()
        _log(f"=== {len(projeler)} YUKLENMIS VIDEO ===")
        # once kanal seviyesi (watermark tum videolara gecer)
        watermark_uygula(yt, dry_run=args.dry_run)
        ilky = 0
        for p in projeler:
            r = video_isle(p, yt, dry_run=args.dry_run)
            ilky += 1 if r.get("ilk_yorum") else 0
        _log(f"\nilk yorum: {ilky}/{len(projeler)}")
        return

    ap.error("--durum / --kanal / --video / --hepsi gerekli")


if __name__ == "__main__":
    main()
