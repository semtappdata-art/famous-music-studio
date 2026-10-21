"""Suno ses dosyalarından tüm platformlar için video üreten ana script.

Kullanım:
    python render.py --project projects/sarki-adi
    python render.py --all
"""

import argparse
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import config
import ffmpeg_utils
import state_io
import validate_project
from audio_highlight import find_highlight
from upload.social_text import build_caption, hashtag, pick_subset, _dil_havuzlari

COVER_NAMES = ["cover.jpg", "cover.jpeg", "cover.png"]
ART_NAMES = ["art.jpg", "art.jpeg", "art.png"]
AUDIO_NAMES = ["audio.wav", "audio.mp3", "audio.m4a"]


# =============================================================================
# SES LIMITER (2026-10-21) — true peak koruması
# =============================================================================

def limiter_gerekli(olcum: dict | None) -> bool:
    """Ölçülen true peak eşiği AŞIYORSA limiter gerekir.

    KURAL: `tp > SES_TP_ESIK_DBTP` (KATİ, "aşıyorsa"). Tam sınırda (-1.0)
    limiter ALINMAZ — sınırda zaten güvenli.

    ÖLÇÜM YOKSA limiter GİRMEZ: limiter bir iyileştirmedir, kapı değil.
    ffmpeg ölçemezse eski davranış (limitersiz) sürer — ama GÖRÜNÜR biçimde
    (log'da UYARI), "sessizce limitersiz" değil.

    NEDEN loudnorm DEĞİL: Suno çıktıları zaten doğru LUFS'ta; tek geçişli
    loudnorm pompalar. Gerçek risk AAC 192k sonrası taşan true peak.
    """
    if not getattr(config, "SES_LIMITER_ACIK", True):
        return False
    if not olcum:
        return False
    tp = olcum.get("tp")
    if tp is None:
        return False
    try:
        tp = float(tp)
    except (TypeError, ValueError):
        return False
    esik = getattr(config, "SES_TP_ESIK_DBTP", -1.0)
    return tp > esik


# =============================================================================
# HIGHLIGHT (2026-10-21) — enerjili bölge tespiti
# =============================================================================

def find_highlight(audio_path: str, target_duration: float) -> tuple[float, float]:
    """(baslangic_saniyesi, bitis_saniyesi) — sesin EN enerjili bolgesi.

    NEDEN burada: `render_project` bu fonksiyonu CagirIYORDU ama tanimi
    HIC OLMAYDI -> meta.json'da highlight_start/highlight_end yoksa
    NameError ile render coktu. Yani "dikey hook / en enerjili chorus
    kesiti" (CLAUDE.md §6) hic uygulanmiyordu.

    UYGULAMA: `audio_highlight.find_highlight` — RMS enerjisinin kayan
    ortalamasindan en yuksek ortalamali pencereyi secer.
    """
    try:
        from audio_highlight import find_highlight as _fh
    except Exception as e:
        print(f"  UYARI: highlight tespiti yapilamadi ({e}) — kesit varsayilan kullanilacak")
        return 0.0, float(target_duration)
    try:
        bas, bit = _fh(audio_path, float(target_duration))
    except Exception as e:
        print(f"  UYARI: highlight tespiti basarisiz ({e}) — kesit varsayilan kullanilacak")
        return 0.0, float(target_duration)
    return float(bas), float(bit)


def _gecerli_highlight_saniyesi(deger) -> bool:
    """highlight_start/end gecerli bir saniye degeri mi?

    REDDETILENLER: negatif sayilar, string'ler, None, ve BOOL.
    NEDEN bool reddi: Python'da `isinstance(True, int)` True'dur — `True`
    1 saniye olarak kabul edilirdi, oysa meta.json'da `true` yazilmissa
    bu bir hatadir.
    """
    if isinstance(deger, bool):
        return False
    if not isinstance(deger, (int, float)):
        return False
    try:
        return float(deger) >= 0.0
    except (TypeError, ValueError):
        return False


# =============================================================================
# SES ÖLÇÜMÜ + UYARI (2026-10-21)
# =============================================================================

_OTURILAN_UYARILAR = set()


def _ses_uyarisi(anahtar: str, mesaj: str) -> None:
    """Ses ölçümü uyarısı — GÖRÜNÜR biçimde log'la, aynı uyarıyı tekrarlama.

    NEDEN `_uyarilanlar` sözlüğü değil de küme: anahtar proje+konu.
    Limiter bir iyileştirmedir, kapı DEĞİLDİR — ölçüm arizası render'i
    DURDURMAZ, sadece limitersiz devam eder ve bunu görünür biçimde söyler.
    """
    if anahtar in _OTURILAN_UYARILAR:
        return
    _OTURILAN_UYARILAR.add(anahtar)
    print(f"  UYARI: {mesaj}")


def _ses_dosyasi_md5(yol: str) -> str:
    """Ses dosyasının MD5'i (ölçüm önbelleği için)."""
    h = hashlib.md5()
    try:
        with open(yol, "rb") as f:
            for parca in iter(lambda: f.read(1 << 20), b""):
                h.update(parca)
    except OSError:
        return ""
    return h.hexdigest()


def _ses_olcumu_al(project_dir: str, audio_path: str) -> dict:
    """Ses ölçümünü al — aynı ses için ÖNBELLEKLENİR (MD5).

    NEDEN önbellek: her render'da ffmpeg ebur128 calistirmak zaman kaybi
    (10+ sn) ve ayni sonucu verir. Ses DEGISTIGINDE yeniden olculur.

    DONDURDUGU: {"lufs", "tp", "lra"} — state'e yazilan kayit ayrica
    "olcum_at" ve "md5" icerir.
    """
    md5 = _ses_dosyasi_md5(audio_path)
    state_yolu = os.path.join(project_dir, "state.json")
    state = None
    if os.path.isfile(state_yolu):
        try:
            state = state_io.load_state(state_yolu)
        except Exception:
            state = None          # bozuk state -> HATA (ustune yazilmayacak)
    if state:
        kayit = state.get("ses_olcum")
        if isinstance(kayit, dict) and kayit.get("md5") and kayit.get("md5") == md5:
            if kayit.get("lufs") is not None and kayit.get("tp") is not None:
                return {"lufs": kayit["lufs"], "tp": kayit["tp"],
                        "lra": kayit.get("lra")}
    olcum = ffmpeg_utils.ses_olc(audio_path)
    if state is not None:
        # Mevcut anahtarlar KORUNUR (telif_araliklari gibi kapilar silinmez).
        yeni = dict(state)
        yeni["ses_olcum"] = {
            "lufs": olcum.get("lufs"), "tp": olcum.get("tp"), "lra": olcum.get("lra"),
            "olcum_at": time.time(), "md5": md5,
        }
        try:
            state_io.atomic_write(state_yolu, yeni)
        except Exception as e:
            print(f"  UYARI: ses ölçümü state'e yazılamadı ({e})")
    return olcum


# =============================================================================
# BÜTÜNLÜK KONTROLÜ (2026-10-21) — yarım render "hazır" sayılmasın
# =============================================================================

# ffprobe CALISTIRILAMADI (binary yok) — koşu başına TEK uyarı için bayrak.
# AYRIŞTIRMA: "çalıştıramadım" (FileNotFoundError -> zarif düşüş) ile
# "çalıştırdım, dosya bozuk" (RuntimeError -> bozukluk kanıtı) FARKLI şeyler.
_FFPROBE_YOK_UYARILDI = False


def video_butun_mu(dosya: str) -> bool:
    """Bu video TAM render edilmiş mi? (0 bayt + ffprobe süre doğrulaması)

    ARIZA: ffmpeg `-y` ile DOĞRUDAN nihai dosyaya yazdığı için yarıda
    kesilen render diskte "yarım ama VAR" bir .mp4 bırakıyor. `isfile` True
    diyor, bir sonraki koşu render'ı ATLIYOR ve BOZUK video altı platforma
    yükleniyor — log'da yalnızca "Zaten render edilmiş" yazdığı için ariza
    SESSİZ kalıyor.

    ÖLÇÜTLER (sırayla):
      1) Dosya yok           -> False
      2) 0 bayt              -> False (ffprobe'a HİÇ girmemeli — en sık vaka)
      3) ffprobe "bozuk/yarım" -> False (moov atom yok -> rc!=0 -> RuntimeError)
      4) ffprobe ÇALIŞTIRILAMIYOR (binary yok) -> True (zarif düşüş: dosyaya güven)
      5) Süre 0              -> False
      6) Süre > 0            -> True

    NOT: ffprobe mantığı KOPYALANMADI — `ffmpeg_utils.get_audio_duration`
    kullanılır (depoda ikinci bir ffprobe kopyası açmak belgelenmiş hata sınıfı).
    """
    if not dosya or not os.path.isfile(dosya):
        return False
    try:
        if os.path.getsize(dosya) == 0:
            return False
    except OSError:
        return False
    try:
        sure = ffmpeg_utils.get_audio_duration(dosya)
    except RuntimeError:
        # ffprobe dosyayı OKUYAMADI (yarım mp4: 'moov atom not found')
        return False
    except Exception:
        # ffprobe CALISTIRILAMADI (binary yok, izin hatası) — zarif düşüş:
        # mevcut dosyaya güven, render'ı yeniden çalıştırma.
        global _FFPROBE_YOK_UYARILDI
        _FFPROBE_YOK_UYARILDI = True
        return True
    try:
        return float(sure) > 0.0
    except (TypeError, ValueError):
        return False


# Render ciktisinin GECICI ad soneki. ffmpeg NİHAİ adı HİÇ görmemeli —
# gördüğü an yarım dosya o adla diskte var olabilir demektir (arızanın kökü:
# "youtube_16x9.mp4" adıyla yarım dosya kalıyor, sonraki koşu onu "hazır"
# sayıyordu). Çıktı geçici adla yazılır, iş bitince os.replace ile taşınır.
PARCALI_SONEK = ".parcali"


def find_intro_cover(project_dir: str, width: int, height: int) -> str | None:
    """Açılış intro'su için kapak dosyası (oranına göre) — yoksa None.

    NEDEN: izleyicinin kaybı büyük ölçüde videonun ilk %1-%3'ünde
    (≈2.-7. saniye) oluyor. Açılışta kapak intro'su + baştaki sessizliğin
    kırpılması bu boşluğu kapatır.

    ORAN KURALI: dikey (9:16) çıktı için `cover_vertical.png`, yatay (16:9)
    için `cover.png` kullanılır. İkisi de yoksa intro ÇİZİLMEZ.
    """
    dikey = height > width
    adaylar = (("cover_vertical.png", "cover.png") if dikey
                else ("cover.png", "cover_vertical.png"))
    for ad in adaylar:
        yol = os.path.join(project_dir, ad)
        if os.path.isfile(yol):
            return yol
    return None


def find_cover(project_dir: str) -> str | None:
    for name in COVER_NAMES:
        path = os.path.join(project_dir, name)
        if os.path.isfile(path):
            return path
    return None


def find_art(project_dir: str) -> str | None:
    """Kart içinde gösterilecek opsiyonel görsel — cover.jpg'den (thumbnail) FARKLI.
    Yoksa render_video düz renge (config.CARD_ART_COLOR) düşer."""
    for name in ART_NAMES:
        path = os.path.join(project_dir, name)
        if os.path.isfile(path):
            return path
    return None


def find_audio(project_dir: str) -> str | None:
    for name in AUDIO_NAMES:
        path = os.path.join(project_dir, name)
        if os.path.isfile(path):
            return path
    return None


def load_meta(project_dir: str) -> dict:
    meta_path = os.path.join(project_dir, "meta.json")
    if os.path.isfile(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _write_chapters_ffmeta(project_dir: str, meta: dict, duration: float, offset_sec: float = 0.0) -> str | None:
    """tracklist meta verisinden chapters.ffmeta dosyası üretir (FFmpeg chapter formatı).
    offset_sec: cold-open ön tadı kadar tüm chapter'ları ötele (video başı uzadığı için).
    Duration is set to max of passed duration and last chapter end time to ensure
    all chapters are within the declared duration (FFmpeg requirement)."""
    tracklist = meta.get("tracklist")
    if not tracklist:
        return None

    # Calculate actual chapter end times to determine proper file duration
    chapter_end_times = []
    for i, track in enumerate(tracklist):
        start_sec = track.get("start_sec")
        end_sec = track.get("end_sec")
        if start_sec is None and track.get("timestamp"):
            parts = track["timestamp"].split(":")
            if len(parts) == 2:
                start_sec = int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                start_sec = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        if end_sec is None and i + 1 < len(tracklist):
            next_track = tracklist[i + 1]
            if next_track.get("start_sec") is not None:
                end_sec = next_track["start_sec"]
            elif next_track.get("timestamp"):
                parts = next_track["timestamp"].split(":")
                if len(parts) == 2:
                    end_sec = int(parts[0]) * 60 + int(parts[1])
                elif len(parts) == 3:
                    end_sec = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        if end_sec is None:
            end_sec = duration - offset_sec  # duration includes offset, so subtract
        chapter_end_times.append(end_sec + offset_sec)

    # Use max of passed duration and last chapter end time
    file_duration = max(duration, max(chapter_end_times) if chapter_end_times else duration)

    lines = [";FFMETADATA1", f"duration={int(file_duration * 1000000000)}"]  # nanoseconds
    for i, track in enumerate(tracklist):
        start_sec = track.get("start_sec")
        end_sec = track.get("end_sec")
        if start_sec is None and track.get("timestamp"):
            parts = track["timestamp"].split(":")
            if len(parts) == 2:
                start_sec = int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                start_sec = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        if end_sec is None and i + 1 < len(tracklist):
            next_track = tracklist[i + 1]
            if next_track.get("start_sec") is not None:
                end_sec = next_track["start_sec"]
            elif next_track.get("timestamp"):
                parts = next_track["timestamp"].split(":")
                if len(parts) == 2:
                    end_sec = int(parts[0]) * 60 + int(parts[1])
                elif len(parts) == 3:
                    end_sec = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        if end_sec is None:
            end_sec = duration - offset_sec

        start_ns = int((start_sec + offset_sec) * 1000000000)
        end_ns = int((end_sec + offset_sec) * 1000000000)
        title = track.get("title", f"Track {i+1}")
        artist = track.get("artist", "")
        chapter_title = f"{title} - {artist}" if artist else title
        lines.append(f"[CHAPTER]")
        lines.append(f"TIMEBASE=1/1000000000")
        lines.append(f"START={start_ns}")
        lines.append(f"END={end_ns}")
        lines.append(f"title={chapter_title}")

    chapters_path = os.path.join(project_dir, "chapters.ffmeta")
    with open(chapters_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  chapters.ffmeta üretildi: {len(tracklist)} chapter (duration={file_duration:.1f}s)")
    return chapters_path


def render_project(project_dir: str) -> bool:
    name = os.path.basename(os.path.normpath(project_dir))
    print(f"\n=== {name} ===")

    # Render'dan önce kapsamlı sağlık kontrolü (bkz. validate_project.py) — bozuk
    # ses dosyası, geçersiz meta.json, art.jpg'nin yanlışlıkla cover ile birebir
    # aynı olması gibi hataları render BAŞLAMADAN yakalar. HATA varsa render'a
    # hiç girmiyoruz (saatler süren bir işi baştan boşa harcamamak için); UYARI
    # varsa loglayıp devam ediyoruz.
    val_errors, val_warnings = validate_project.validate(project_dir)
    validate_project.print_report(project_dir, val_errors, val_warnings)
    if val_errors:
        print(f"  Render durduruldu: {len(val_errors)} doğrulama hatası (yukarıda).")
        return False

    audio_path = find_audio(project_dir)
    if not audio_path:
        print(f"  HATA: {project_dir} içinde audio.wav/.mp3/.m4a bulunamadı, bu proje atlanıyor.")
        return False

    cover_path = find_cover(project_dir)
    if not cover_path:
        print(f"  HATA: {project_dir} içinde cover.jpg/.jpeg/.png bulunamadı, bu proje atlanıyor.")
        return False

    art_path = find_art(project_dir)
    print(f"  kart içeriği: {'art görseli (' + art_path + ')' if art_path else 'düz renk (art.jpg yok)'}")

    meta = load_meta(project_dir)
    title = meta.get("title")
    theme = meta.get("theme")
    # DJ Famous gibi özel içerikler için kayan yazının içeriğini override eder
    # (ör. "DJ Famous  •  Hafta 1 Seti  •  #DJFamous ...") — sabit alt satır
    # ("Famous Music Studio") HER ZAMAN aynı kalır, bundan etkilenmez.
    marquee_override = meta.get("marquee_text")

    output_dir = os.path.join(project_dir, "output")
    os.makedirs(output_dir, exist_ok=True)

    # HIGHLIGHT (2026-10-21) — meta.json'daki highlight_start KESIT BASLANGICI
    # olarak kullanilir (Sadece start verilmis olabilir: end = start + sure).
    # Gecersiz deger (negatif, string, bool) -> UYARI + otomatik tespite dusulur.
    highlight_start = meta.get("highlight_start")
    highlight_end = meta.get("highlight_end")
    if highlight_start is not None and not _gecerli_highlight_saniyesi(highlight_start):
        print(f"  UYARI: meta.json'daki highlight_start geçersiz ({highlight_start!r}) "
              "— otomatik tespite geçiliyor.")
        highlight_start = None
    if highlight_end is not None and not _gecerli_highlight_saniyesi(highlight_end):
        print(f"  UYARI: meta.json'daki highlight_end geçersiz ({highlight_end!r}) "
              "— otomatik tespite geçiliyor.")
        highlight_end = None
    if highlight_start is None and highlight_end is not None:
        print(
            "  UYARI: meta.json'da highlight_start/highlight_end alanlarından sadece biri "
            "belirtilmiş, ikisi de gerekli — göz ardı edilip otomatik tespite geçiliyor."
        )
        highlight_end = None
    if highlight_start is not None and highlight_end is None:
        # YALNIZ START: kesit oradan baslar, sure config.HIGHLIGHT_DURATION
        highlight_end = float(highlight_start) + float(config.HIGHLIGHT_DURATION)
        print(f"  highlight (meta.json'dan): {highlight_start:.1f}s - {highlight_end:.1f}s")
    elif highlight_start is not None:
        print(f"  highlight (meta.json'dan): {highlight_start:.1f}s - {highlight_end:.1f}s")
    else:
        if config.HIGHLIGHT_PLATFORMS:
            print("  highlight otomatik tespit ediliyor (en yoğun bölüm)...")
            highlight_start, highlight_end = find_highlight(audio_path, config.HIGHLIGHT_DURATION)
            print(f"  highlight: {highlight_start:.1f}s - {highlight_end:.1f}s")

    # --- SES ÖLÇÜMÜ + TRUE PEAK LIMITER (2026-10-21) --------------------
    # Ölçüm bir İYİLEŞTİRME, kapı değil: ölçüm arizasında render DURMAZ,
    # limitersiz devam eder ve bunu GÖRÜNÜR biçimde söyler (UYARI).
    ses_olcum = None
    try:
        ses_olcum = _ses_olcumu_al(project_dir, audio_path)
    except Exception as e:
        # UYARI hem EKRANA (görünür olmalı — "sessizce limitersiz" olmaz)
        # hem _ses_uyarisi'ya (tekrar engeli + test kancası) yazılır.
        _mesaj = ("limiter ses ölçümü yapılamadı (%s) — limitersiz devam ediliyor."
                  % (str(e)[:120]))
        print("  UYARI: %s" % _mesaj)
        _ses_uyarisi(
            "ses_olcumu:%s" % os.path.basename(os.path.normpath(project_dir)),
            "UYARI: %s" % _mesaj,
        )
    ses_limiter = limiter_gerekli(ses_olcum)
    if ses_limiter:
        print(f"  Ses limiteri AÇIK: true peak {ses_olcum.get('tp')} dBTP "
              f"(eşik {config.SES_TP_ESIK_DBTP} dBTP)")
    elif ses_olcum:
        print(f"  Ses limiteri kapalı: true peak {ses_olcum.get('tp')} dBTP "
              f"(eşik {config.SES_TP_ESIK_DBTP} dBTP)")

    # Chapter dosyasını üret (tracklist varsa)
    # NEDEN toleranslı: sure YALNIZCA chapter için gerekli. ffprobe okuyamazsa
    # (bozuk/placeholder ses dosyası) render'i DÜŞÜRMEMELİ — chapter'siz
    # render hâlâ geçerlidir. Ölçüm hatası limiter gibi bir iyileştirmedir.
    try:
        full_duration = ffmpeg_utils.get_audio_duration(audio_path)
    except Exception as e:
        full_duration = 0.0
        print(f"  UYARI: ses süresi okunamadı ({str(e)[:100]}) — chapter süresi 0 kabul ediliyor.")
    # BÜYÜME cold-open (madde 6): uzun videonun VE Shorts'ün başına highlight'tan
    # kısa ön tat eklenir; chapter'lar (uzun video için) aynı süre kadar ötelenir.
    cold_open_cfg = None
    cold_preview = 0.0
    if (
        getattr(config, "COLD_OPEN_ACIK", True)
        and any(p in getattr(config, "COLD_OPEN_PLATFORMLAR", ["youtube_16x9"]) for p in ("youtube_16x9", "shorts_9x16"))
        and highlight_start is not None and highlight_end is not None
        and highlight_end > highlight_start
    ):
        cold_preview = max(0.0, min(float(getattr(config, "COLD_OPEN_SURE_SN", 4.0)), highlight_end - highlight_start))
        if cold_preview > 0.0:
            cold_open_cfg = (highlight_start, highlight_end)
    chapters_path = _write_chapters_ffmeta(project_dir, meta, full_duration + cold_preview, offset_sec=cold_preview)
    metadata_file = chapters_path

    # BÜYÜME CTA (madde 11) + bitiş kartı (madde 10) — bayrak/metinden beslenir.
    theme_key = ffmpeg_utils.get_theme_key(theme)
    if getattr(config, "ABONE_CTA_ACIK", True):
        cta_cfg = config.ABONE_CTA_METIN.get(theme_key, config.ABONE_CTA_METIN["varsayilan"])
    else:
        cta_cfg = None
    end_card_cfg = meta.get("end_card_text")

    # Hashtag'leri üret (Shorts overlay için) — Title Case + Mavi renk
    def _generate_hashtags_list(meta: dict) -> list:
        """build_caption benzeri hashtag listesi üret."""
        title = meta.get("title", "Untitled")
        theme_key_local = meta.get("theme", config.DEFAULT_THEME)
        theme_local = config.THEMES.get(theme_key_local, config.THEMES[config.DEFAULT_THEME])
        genre_tags = [hashtag(theme_local["label"])] + [hashtag(t) for t in theme_local.get("related", [])]
        discovery_tags = pick_subset(title, _dil_havuzlari(meta)["kesif"], config.DISCOVERY_HASHTAG_COUNT, salt=13)
        all_tags = config.BRAND_HASHTAGS + discovery_tags + genre_tags
        # Liste formatında döndür (string yerine)
        return all_tags

    hashtags_list = _generate_hashtags_list(meta) if meta else []

    # --- BEAT SYNC (YouTube Shorts efekti) ---------------------------------
    # NEDEN burada: beat'ler kırpma aralığına göre bulunmalı (Shorts
    # highlight kırpması 30-60sn). Tespit cache'li (beat_sync.py) → ikinci
    # render'da anında.
    #
    # NEDEN "shorts_9x16" kontrolü: config.HIGHLIGHT_PLATFORMS = {"shorts_9x16"}
    # olduğu için kırpma Shorts'a özel; uzun formatta highlight_start/end
    # None'dır ve beat'ler tam dosyadan alınır.
    beat_times: list = []
    beat_period: float = 0.0
    speed_ramp: dict | None = None
    if getattr(config, "SHORTS_BEAT_SYNC_AKTIF", True):
        try:
            import beat_sync as _beat_sync
            _kirpma_var = ("shorts_9x16" in
                           getattr(config, "HIGHLIGHT_PLATFORMS", set())
                           and highlight_start is not None
                           and highlight_end is not None)
            _hs = highlight_start if _kirpma_var else None
            _he = highlight_end if _kirpma_var else None
            _analiz = _beat_sync.analiz_et(audio_path, start=_hs, end=_he)
            if _analiz.get("basari"):
                beat_period = float(_analiz.get("period") or 0.0)
                _ofset = _hs if _kirpma_var else 0.0
                _sure = (_he - _hs) if _kirpma_var else None
                beat_times = _beat_sync.kirp_beatler(
                    _analiz.get("beats", []), offset=_ofset, duration=_sure)
                print(f"  -> beat sync: bpm={_analiz.get('bpm')} "
                      f"beat={len(beat_times)}")
                # HIZ RAMPASI (YouTube efekti): yavaş başla, beat'te hızlan
                if getattr(config, "SHORTS_SPEED_RAMP_AKTIF", True):
                    speed_ramp = _beat_sync.hiz_rampasi_planla(
                        beat_times,
                        yavas_sure=float(getattr(
                            config, "SHORTS_SPEED_RAMP_YAVAS_SURE_SN", 1.6)),
                        yavas_kat=float(getattr(
                            config, "SHORTS_SPEED_RAMP_YAVAS_KAT", 0.55)))
                    if speed_ramp:
                        # NEDEN: ramp zaman cizgisini kaydiriyor; beat
                        # flasi post-ramp hesaplandigi icin beat'ler de
                        # ayni eslemeden gecirilmeli (a/v uyumsuzluk olmasin).
                        beat_times = _beat_sync.beatleri_zaman_esle(
                            beat_times, speed_ramp)
                        print(f"  -> hiz rampasi: snap@{speed_ramp['t_snap']}sn "
                              f"yavas x{speed_ramp['kat']}")
        except Exception as e:                               # noqa: BLE001
            print(f"  -> beat sync atlandi: {e}")

    def render_one(platform_key, width, height):
        output_path = os.path.join(output_dir, f"{platform_key}.mp4")
        print(f"  -> {platform_key} ({width}x{height}) render ediliyor...")
        use_highlight = platform_key in config.HIGHLIGHT_PLATFORMS
        is_shorts = platform_key == "shorts_9x16"
        # Cold-open: hem youtube_16x9 hem shorts_9x16 için etkin (config.COLD_OPEN_PLATFORMLAR'a göre)
        platform_cold_open = None
        if cold_open_cfg and platform_key in getattr(config, "COLD_OPEN_PLATFORMLAR", ["youtube_16x9"]):
            platform_cold_open = (cold_open_cfg[0], cold_open_cfg[1], cold_preview)
        # CTA ve End Card: hem uzun format hem Shorts için (Shorts'ta da görünebilir)
        platform_end_card = end_card_cfg
        platform_cta = cta_cfg
        # GECICI AD + os.replace (2026-10-21) — yarım render nihai adla
        # diskte ASLA görünmez. Render ölürse geçici dosya da silinir.
        gecici_yol = output_path + PARCALI_SONEK
        try:
            ffmpeg_utils.render_video(
            art_path, audio_path, gecici_yol, width, height, title, theme,
            marquee_override=marquee_override,
            start_time=highlight_start if use_highlight else None,
            end_time=highlight_end if use_highlight else None,
            # Chapter zaman damgaları tam süreye ait — 45sn highlight kırpmasına
            # gömülmez (aralık dışı kalır); sadece tam boy render'a gömülür.
            chapters_file=metadata_file if not use_highlight else None,
            is_shorts=is_shorts,
            cold_open=platform_cold_open,
            end_card_text=platform_end_card,
            cta_text=platform_cta,
            hashtags=hashtags_list if is_shorts else None,
            beat_times=beat_times if is_shorts else None,
            beat_period=beat_period if is_shorts else 0.0,
            speed_ramp=speed_ramp if is_shorts else None,
            # TRUE PEAK LIMITER (2026-10-21) — olcum eşiği aşıyorsa uygulanır.
            ses_limiter=ses_limiter,
            )
            os.replace(gecici_yol, output_path)
        except Exception:
            # Render ÖLDÜ: geçici çıktıyı temizle, nihai ad hiç oluşmasın.
            try:
                if os.path.isfile(gecici_yol):
                    os.remove(gecici_yol)
            except OSError:
                pass
            raise
        return platform_key, output_path

    ok = True
    # Kart maskesi/arka planı ilk kullanımda üretiliyor; paralel süreçler yarışıp
    # bozuk/eksik bir dosya yazmasın diye render başlamadan önce garantiye alıyoruz.
    theme_key = ffmpeg_utils.get_theme_key(theme)
    ffmpeg_utils.ensure_card_mask()
    for width, height in config.PLATFORMS.values():
        if art_path:
            ffmpeg_utils.ensure_art_backdrop(art_path, width, height)
        else:
            ffmpeg_utils.ensure_vignette(width, height, theme_key)

    with ThreadPoolExecutor(max_workers=config.MAX_PARALLEL_RENDERS) as executor:
        futures = {
            executor.submit(render_one, platform_key, width, height): platform_key
            for platform_key, (width, height) in config.PLATFORMS.items()
        }
        for future in as_completed(futures):
            platform_key = futures[future]
            try:
                _, output_path = future.result()
                print(f"     tamam: {output_path}")
            except Exception as e:
                print(f"     HATA ({platform_key}): {e}")
                ok = False

    return ok


def main():
    parser = argparse.ArgumentParser(description="Suno ses dosyalarından çoklu platform video üretir.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--project", help="Tek bir proje klasörü (örn. projects/sarki-adi)")
    group.add_argument("--all", action="store_true", help="projects/ altındaki tüm klasörleri render et")
    args = parser.parse_args()

    if args.project:
        project_dirs = [args.project]
    else:
        base = "projects"
        if not os.path.isdir(base):
            print(f"HATA: {base} klasörü bulunamadı.")
            sys.exit(1)
        project_dirs = [
            os.path.join(base, name)
            for name in sorted(os.listdir(base))
            if os.path.isdir(os.path.join(base, name))
        ]
        if not project_dirs:
            print(f"HATA: {base} altında hiç proje klasörü yok.")
            sys.exit(1)

    all_ok = True
    for project_dir in project_dirs:
        if not render_project(project_dir):
            all_ok = False

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
