"""Render'dan ÖNCE bir projenin tüm girdilerini doğrulayan sağlık kontrolleri.

Amaç: saatler süren bir render+upload sürecinin sonunda bozuk bir video ya da
eksik bir kapakla karşılaşmak yerine, bu sınıf hataları render BAŞLAMADAN
yakalamak — bugüne kadar bu projede tekrar tekrar düşülen hatalar (art.jpg'nin
yanlışlıkla metin içermesi, bozuk/okunamayan ses dosyası, geçersiz meta.json)
buradan otomatik tespit ediliyor. render.py her proje için render'dan önce
bunu otomatik çağırır — elle çalıştırmaya gerek yok, ama tek başına da
kullanılabilir:

    python validate_project.py --project "projects/sarki-adi"
    python validate_project.py --all      # projects/ + dj_sets/ + derlemeler/

HATA (error) seviyesindeki bulgular render'ı durdurur; UYARI (warning)
seviyesindekiler sadece loglanır, render devam eder.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

import config
from datetime import datetime
import hashlib
import re

AUDIO_NAMES = ["audio.wav", "audio.mp3", "audio.m4a"]
COVER_NAMES = ["cover.jpg", "cover.jpeg", "cover.png"]
ART_NAMES = ["art.jpg", "art.jpeg", "art.png"]

# YouTube Algoritması Blueprint — Yasak AI Hashtag Listesi (SAFETY-003)
YASAK_AI_HASHTAGS = frozenset({
    "#aigenerated", "#aimusic", "#artificialintelligence", "#machinelearning",
    "#aiart", "#deeplearning", "#neuralnetwork", "#generativeai",
    "#aicontent", "#aimade", "#aicreated", "#syntheticmedia"
})

# İzin verilen AI hashtag'ler (marka uyumlu)
IZINLI_AI_HASHTAGS = frozenset({
    "#aiassistedmusic", "#sunoai", "#aicreativity", "#aimusicproduction"
})

# Zorunlu açıklama şablonu (META-002)
ZORUNLU_ACIKLAMA_SATIRLARI = [
    "🎵 Famous Music Studio — AI-assisted Turkish music production",
    "🌙 Gece Masalları album · Night Drive DJ sets · Melodic Techno · Arabesk · Trap",
    "🎧 Listen everywhere: https://distrokid.com/hyperfollow/famousmusicstudio/gece-masallar",
    "☕ Support: https://ko-fi.com/famousmusicstudio",
    "📱 TikTok: @famousmusicstudio | Instagram: @famous_music_studio",
    "📧 Booking: booking@famousmusicstudio.com"
]

# Golden Hour pencereleri (PUBLISH-001)
GOLDEN_HOUR_PENCERELERI = [
    (12, 14),  # 12:00-14:00
    (18, 22)   # 18:00-22:00
]

# Ana playlist kategorileri (CHANNEL-001)
ANA_PLAYLISTLER = {
    "gece_surusu": "🎧 Gece Sürüşleri",
    "arabesk_trap": "🌙 Arabesk & Trap Vibes",
    "dj_setler": "🎛️ DJ Setler",
    "yeni_cikanlar": "🆕 Yeni Çıkanlar"
}


def _find(project_dir: str, names: list) -> str | None:
    for name in names:
        path = os.path.join(project_dir, name)
        if os.path.isfile(path):
            return path
    return None


def _ffprobe_duration(path: str) -> float | None:
    """Dosyanın (ses ya da video) süresini okur — ffprobe hiç çalışamıyorsa ya
    da dosya bozuksa None döner (ffprobe kendisi de format/codec algılayarak
    bozuk dosyaları genelde reddeder, bu yüzden bu basit bir "okunabilirlik"
    testi olarak yeterli)."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        return None
    try:
        return float(result.stdout.strip())
    except ValueError:
        return None


def _valid_image(path: str) -> bool:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0", path],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return result.returncode == 0 and bool(result.stdout.strip())


def _file_hash(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def validate(project_dir: str) -> tuple[list[str], list[str]]:
    """(errors, warnings) döner — errors boşsa render güvenle başlayabilir."""
    errors: list[str] = []
    warnings: list[str] = []

    # 0) Render kilidi (editoryal kapı, politika DEĞİL): state.json'da
    #    `render_kilit` doluysa görseller netleşmemiş / onay verilmemiş demektir.
    #    İlk kontrol olmasının sebebi: diğer tüm kontrollerin maliyeti boşa
    #    gitmesin ve log'un ilk satırı sebebi söylesin. Kaldırmak: onay sonrası
    #    alanı state.json'dan silmek (render yapıldıktan sonra kilit geri
    #    konmaz — kilit proje başına TEK seferlik).
    try:
        with open(os.path.join(project_dir, "state.json"), encoding="utf-8") as f:
            _st = json.load(f)
        if isinstance(_st, dict) and _st.get("render_kilit"):
            errors.append(
                "render_kilit aktif (%s) — görsel onayı bekleniyor, "
                "render başlatılmıyor." % _st.get("render_kilit")
            )
            return errors, warnings
    except (OSError, ValueError):
        pass

    # 1) audio — var mı, ffprobe ile okunabiliyor mu, süresi mantıklı mı
    audio_path = _find(project_dir, AUDIO_NAMES)
    if not audio_path:
        errors.append("audio.wav/.mp3/.m4a bulunamadı.")
    else:
        duration = _ffprobe_duration(audio_path)
        if duration is None:
            errors.append(
                f"{os.path.basename(audio_path)} ffprobe ile okunamadı — dosya bozuk "
                "veya indirme yarım kalmış olabilir."
            )
        elif duration <= 1.0:
            errors.append(f"{os.path.basename(audio_path)} süresi {duration:.2f}s — çok kısa/geçersiz.")

    # 2) meta.json — geçerli JSON mu, theme tanınıyor mu, character'a portre var mı
    meta_path = os.path.join(project_dir, "meta.json")
    meta: dict = {}
    theme = None
    if os.path.isfile(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except json.JSONDecodeError as e:
            errors.append(f"meta.json geçersiz JSON: {e}")

        theme = meta.get("theme")
        if theme and theme not in config.THEMES:
            errors.append(
                f"meta.json'daki theme={theme!r} config.THEMES'te tanımlı değil "
                f"(geçerli: {', '.join(config.THEMES)})."
            )

        character = meta.get("character")
        if character:
            try:
                from cover_generator import find_character_image
                if not find_character_image(character):
                    warnings.append(
                        f"meta.json'daki character={character!r} için characters/ klasöründe "
                        "portre bulunamadı — procedural gradyana düşülecek (render durmaz)."
                    )
            except ImportError:
                pass

        # DJ set artist name check
        if theme == "dj":
            marquee = meta.get("marquee_text")
            if not marquee or "DJ Famous" not in marquee:
                errors.append(
                    "DJ setlerde marquee_text 'DJ Famous' içermelidir (şu an: %r)" % marquee
                )

        # BÜYÜME (madde 9): chapter/tracklist başlıkları yer tutucu olmamalı —
        # "Track 3" aramada indekslenmez, tıklanmaz. UYARI (render durmaz).
        tracklist = meta.get("tracklist")
        if isinstance(tracklist, list) and tracklist:
            import re as _re
            yer_tutucu = [
                (t.get("title") or "")
                for t in tracklist
                if isinstance(t, dict) and _re.match(r"^(Track|Par\u00e7a|B\u00f6l\u00fcm)\s*\d+\s*$", (t.get("title") or "").strip(), _re.IGNORECASE)
            ]
            if yer_tutucu:
                errors.append(
                    "tracklist'te %d yer tutucu başlık var (%s) — duygulu başlık yaz "
                    "(örn. 'Golden Hour - Peak Energy'); chapter SEO'su düşer. KIRMIZI ÇİZGİ: Placeholder = render durduruluyor." % (len(yer_tutucu), ", ".join(yer_tutucu[:3]))
                )
    else:
        warnings.append("meta.json yok — başlık/tema varsayılanları kullanılacak.")

    # 3) cover/art — geçerli görsel mi, art yanlışlıkla cover ile birebir aynı mı
    #    (CLAUDE.md: "art.jpg METİNSİZ olmalı" kuralının ihlaline işaret eder —
    #    Kalbim Oynuyor ve ilk otomasyon/Yeniden Doğacağım'da birkaç kez düşülen hata)
    cover_path = _find(project_dir, COVER_NAMES)
    art_path = _find(project_dir, ART_NAMES)

    if cover_path and not _valid_image(cover_path):
        errors.append(f"{os.path.basename(cover_path)} geçerli bir görsel olarak okunamadı.")
    if art_path and not _valid_image(art_path):
        errors.append(f"{os.path.basename(art_path)} geçerli bir görsel olarak okunamadı.")

    if cover_path and art_path and _file_hash(cover_path) == _file_hash(art_path):
        warnings.append(
            "cover ve art dosyaları byte-birebir aynı — art.jpg METİNSİZ olmalı (bu projede "
            "birkaç kez düşülen bir hata), cover'ın (başlık metni içerebilir) yanlışlıkla art "
            "olarak da kullanıldığının işareti olabilir. Blur backdrop'ta okunaksız bir lekeye "
            "dönüşebilir — kontrol et."
        )
    # cover.jpg render.py'de zorunlu (art.jpg opsiyonel, yoksa düz renge düşülür) —
    # o kontrolü burada tekrar etmiyoruz, render_project zaten kendi hata mesajını basıyor.

    # 2b) Meta zorunlu alanlar ve ek kontroller
    # Kontrol edilen alanlar: title, theme, set_style, marquee_text, art_query
    required_meta = ["title", "theme", "set_style", "marquee_text", "art_query"]
    # DJ setleri için location da zorunlu
    if theme == "dj":
        required_meta.append("location")
    for field in required_meta:
        if field not in meta or not meta[field]:
            errors.append(f"meta.json'da zorunlu alan eksik veya boş: {field}")
    # DJ set speciale marquee_text kontrolü (zaten var ama tekrar)
    if theme == "dj":
        marquee = meta.get("marquee_text")
        if not marquee or "DJ Famous" not in marquee:
            errors.append(
                "DJ setlerde marquee_text 'DJ Famous' içermelidir (şu an: %r)" % marquee
            )
        # Location alt alanları kontrolü
        location = meta.get("location", {})
        if not isinstance(location, dict):
            errors.append("DJ setlerde location objesi olmalıdır (dict)")
        else:
            loc_required = ["city", "country", "landmark", "gps", "story", "story_tr"]
            for field in loc_required:
                if field not in location or not location[field]:
                    errors.append(f"DJ setlerde location.{field} zorunlu alan eksik veya boş")
            # GPS format kontrolü
            gps = location.get("gps", "")
            if gps and not re.match(r'^-?\d+(\.\d+)?,-?\d+(\.\d+)?$', gps):
                errors.append(f"location.gps formatı 'lat,lon' olmalıdır (şu an: {gps!r})")
    # sozler.md varlığı (opsiyonel uyarı)
    sozler_path = os.path.join(project_dir, "sozler.md")
    if not os.path.isfile(sozler_path):
        warnings.append("sozler.md dosyası bulunamadı — lyric yoksa instrumental set beklenir.")
    # structure.txt varlığı (opsiyonel uyarı)
    struct_path = os.path.join(project_dir, "structure.txt")
    if not os.path.isfile(struct_path):
        warnings.append("structure.txt dosyası bulunamadı — bölüm yapısı ve süre tahmini eksik.")
    # Platform politikasi kontrolleri (bkz. uyumluluk.py). Render'dan once
    # calisiyor cunku render.py bu fonksiyonu zaten cagiriyor - ayri bir kanca
    # acmak yerine mevcut kapiyi kullaniyoruz.
    #
    # FAIL-CLOSED (2026-09-12): kapi COKERSE bu bir UYARI degil HATA. Eskiden
    # istisna `warnings`e yaziliyor ve render DEVAM ediyordu - yani kapinin
    # calismamasi "temiz" sayiliyordu. Burasi yayin degil URETIM adimi oldugu
    # icin karar auto_process/dj_famous_process'tekinden AYRI dusunuldu;
    # gerekce sunlar:
    #
    #   1. SIDDET, kapinin KENDI cevabiyla ayni olmali. Iki satir yukarida
    #      `kontrol()`un dondugu HATA'lar dogrudan `errors`a giriyor ve render'i
    #      durduruyor. Kapinin "hata var" demesi render'i durduruyorsa,
    #      "cevap veremiyorum" demesi de durdurmali - aksi hâlde kapiyi
    #      atlatmanin en kolay yolu onu BOZMAK olurdu.
    #   2. Bu yonun maliyeti GERI ALINABILIR, tersi degil. Durdurulan render
    #      bir sonraki kosuda yeniden denenir; hicbir dis sistemde iz birakmaz.
    #      Fail-open'in maliyeti ise saatlerce suren bir render'in bosa
    #      harcanmasi: kapi yukleme asamasinda da (AYNI process, AYNI import)
    #      cokecegi icin o video zaten yayinlanamayacak.
    #   3. "Kullanici neden video cikmadigini anlamali" sarti KARSILANIYOR:
    #      bu liste `print_report()` ile "[<proje>] HATA: ..." olarak basiliyor
    #      ve `render.render_project()` ustune "Render durduruldu: N dogrulama
    #      hatasi" satirini ekliyor. Mesaj bu yuzden ne yapilacagini da soyluyor.
    #
    # KAPSAM: bu `errors` listesi YALNIZCA bu projeye ait. `render_project()`
    # sadece bu proje icin False doner, `auto_process`/`dj_famous_process` de
    # sadece bu projeyi atlar - dongu bir sonraki projeyle devam eder.
    #
    # NOT: yukleme kapisinin (auto_process/dj_famous_process) fail-closed
    # olmasi bu satiri GEREKSIZ KILMIYOR. Oradaki kapi yayini durdurur, bu
    # kapi ise bosa gidecek uretimi durdurur; ikisi farkli seye mal oluyor.
    try:
        import uyumluluk
        u_hata, u_uyari = uyumluluk.kontrol(project_dir, "render")
        errors.extend(u_hata)
        warnings.extend(u_uyari)
    except Exception as e:
        errors.append(
            "uyumluluk (politika) kapisi CALISTIRILAMADI: %s — fail-closed, "
            "render baslatilmiyor. Kapi cevap veremedigi surece bu projenin "
            "telif/tekrar-icerik kontrolu YAPILAMIYOR demektir; once "
            "`python uyumluluk.py` ile hatayi gider." % str(e)[:120])

    # 4b) YOUTUBE ALGORİTMASI BLUEPRINT VALIDASYONU (URETIM_KURALLARI_YOUTUBE_ALGORITMA.md)
    # Bu validasyonlar meta.json yüklendikten sonra çalışır; meta yoksa atlanır.
    if meta:
        _validate_youtube_metadata(project_dir, meta, errors, warnings)
        _validate_youtube_content_structure(project_dir, meta, errors, warnings)
        _validate_youtube_tech_production(project_dir, meta, errors, warnings)
        _validate_youtube_publish_strategy(project_dir, meta, errors, warnings)
        _validate_youtube_channel_health(project_dir, meta, errors, warnings)
        _validate_youtube_safety_policies(project_dir, meta, errors, warnings)
        _validate_youtube_measurement(project_dir, meta, errors, warnings)

    # 4c) MCP ONKONTROL (senarist/dis-referans) — UYARI, fail-open.
    # Gerekce: politika kapisi degil, zenginlestirme. Eksik MCP render'i
    # durdurmamali; gozlem `print_report` UYARI satiri + test_kurallar.
    warnings.extend(_mcp_onkontrol())

    # 5) KALITE KAPISI (2026-09): ses ve kapak kalitesi
    _kalite_kontrolu(project_dir, errors, warnings)

    return errors, warnings


def _mcp_onkontrol() -> list[str]:
    """MCP onkontrol (senarist/dis-referans zenginlestirme).

    Cagiran: validate() — render.py her render oncesi cagirir, yeni
    Zamanlayici gorevi YOK (saatlik auto_process finally zinciri).
    Gozlem: eksik/devre-disi sunucu varsa `[proje] UYARI: MCP onkontrol...`
    satiri basilir. Bilerek UYARI (HATA degil): MCP zenginlestirme
    atlanabilir, politika kapisi (uyumluluk) degil.

    Returns:
        Uyari listesi (bossa hersey hazir).
    """
    gerekli = ("fetch", "memory", "sequential-thinking", "filesystem",
               "github", "sqlite")
    kok = os.path.dirname(os.path.abspath(__file__))
    yol = os.path.join(kok, ".pi", "mcp.json")
    try:
        with open(yol, encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, ValueError):
        return ["MCP onkontrol YAPILAMADI (.pi/mcp.json okunamadi) — "
                "senarist/dis-referans zenginlestirme atlandi (render durmaz)."]
    sunucular = cfg.get("mcpServers", {}) if isinstance(cfg, dict) else {}
    eksik = [s for s in gerekli
             if not isinstance(sunucular.get(s), dict)
             or not sunucular[s].get("enabled")]
    if eksik:
        return ["MCP onkontrol: %s eksik/devre-disi — senarist/dis-referans "
                "zenginlestirme atlandi (render durmaz)." % ", ".join(eksik)]
    return []


def _kalite_kontrolu(project_dir: str, errors: list[str], warnings: list[str]) -> None:
    """Ses + kapak kalitesi kontrolü.

    Ses: RMS db (çok sessiz / çok yüksek), yanlık süresi.
    Kapak: çözünürlük, aspect ratio.
    """
    # --- Ses ---
    audio_path = _find(project_dir, AUDIO_NAMES)
    if audio_path and not any("audio" in e.lower() for e in errors):
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error",
                 "-filter:a", "volumedetect",
                 "-show_entries", "frame_tags=volume",
                 "-of", "csv=p=0", audio_path],
                capture_output=True, text=True, encoding="utf-8",
                timeout=30)
            if result.returncode == 0:
                for satir in result.stdout.strip().split("\n"):
                    if "mean_volume" in satir:
                        try:
                            db = float(satir.split(":")[1].strip().replace(" dB", ""))
                            if db < -30:
                                errors.append(
                                    f"ses çok sessiz (RMS {db:.1f} dB) — "
                                    f"Suno'da tekrar üret veya ses dosyasını değiştir")
                            elif db > -3:
                                warnings.append(
                                    f"ses çok yüksek (RMS {db:.1f} dB) — distorsiyon riski")
                        except (ValueError, IndexError):
                            pass
                    if "max_volume" in satir:
                        try:
                            db_max = float(satir.split(":")[1].strip().replace(" dB", ""))
                            if db_max < -20:
                                warnings.append(
                                    f"ses peak çok düşük ({db_max:.1f} dB) — dinleyici sesini açmalı")
                        except (ValueError, IndexError):
                            pass
        except Exception:
            pass

        # Yanlık kontrolü
        try:
            result = subprocess.run(
                ["ffmpeg", "-i", audio_path,
                 "-af", "silencedetect=noise=-50dB:d=3",
                 "-f", "null", "-"],
                capture_output=True, text=True, encoding="utf-8",
                timeout=60)
            import re
            matches = re.findall(r"silence_start:\s*([\d.]+)", result.stderr)
            if len(matches) >= 2:
                warnings.append(
                    f"ses içinde {len(matches)} yanlık bölüm var — dinleyici deneyimi düşük")
        except Exception:
            pass

    # --- Kapak ---
    cover_path = _find(project_dir, COVER_NAMES)
    if cover_path and _valid_image(cover_path):
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error",
                 "-select_streams", "v:0",
                 "-show_entries", "stream=width,height",
                 "-of", "csv=p=0", cover_path],
                capture_output=True, text=True, encoding="utf-8",
                timeout=10)
            if result.returncode == 0:
                wh = result.stdout.strip().split(",")
                if len(wh) == 2:
                    w, h = int(wh[0]), int(wh[1])
                    if w < 800 or h < 450:
                        errors.append(
                            f"kapak çözünürlüğü çok düşük ({w}x{h}) — YouTube feed'te bulanık")
                    ratio = w / h if h else 0
                    if abs(ratio - 16/9) > 0.1:
                        warnings.append(
                            f"kapak aspect oranı {ratio:.2f} — 16:9 bekleniyor, pillarbox olabilir")
                    if w < 3000 or h < 3000:
                        warnings.append(
                            f"kapak çözünürlüğü {w}x{h} — profesyonel standart 3000x3000, YouTube Öneri: 3000x3000 minimum (thumbnail A/B test ve yüksek çözünürlük için)")
        except Exception:
            pass


# ============================================================
# YOUTUBE ALGORİTMASI BLUEPRINT — VALIDASYON KURALLARI
# Bu fonksiyonlar URETIM_KURALLARI_YOUTUBE_ALGORITMA.md içindeki
# 25 kuralı kod olarak zorunlu kılar.
# ============================================================


def _validate_youtube_metadata(project_dir: str, meta: dict,
                                 errors: list[str], warnings: list[str]) -> None:
    """META-001/002/003/004/005: Başlık, açıklama, etiketler, bölümler, hashtag."""
    # META-001: Başlık formatı — ≤60 karakter, 'Famous Music Studio' ile başla
    title = meta.get("title", "")
    if title:
        if len(title) > 60:
            errors.append(f"META-001: Başlık {len(title)} karakter — 60 karakter sınırı aşıldı (mobil truncation).")
        if not title.startswith("Famous Music Studio"):
            errors.append("META-001: Başlık 'Famous Music Studio' ile başlamalı (marka pozisyonu).")
        # Clickbait koruması (SAFETY-001) - basit heuristic
        clickbait_kelimeler = ["BEST", "EN İYİ", "ŞOK", "HARİKA", "İNANAMAYACAK", "MÜKEMMEL"]
        for kw in clickbait_kelimeler:
            if kw.lower() in title.lower():
                warnings.append(f"SAFETY-001: Başlıkta potansiyel clickbait kelimesi: '{kw}' — içerik vaatini karşılayıp karşılamadığını kontrol et.")
    else:
        errors.append("META-001: meta.json'da 'title' alanı eksik.")

    # META-002: Açıklama — İlk 6 satır şablon eşleşmeli
    description = meta.get("description", "")
    if description:
        desc_lines = [l.strip() for l in description.split("\n") if l.strip()]
        for i, required in enumerate(ZORUNLU_ACIKLAMA_SATIRLARI):
            if i >= len(desc_lines):
                errors.append(f"META-002: Açıklama satır {i+1} eksik — şablon: {required}")
            elif required.lower() not in desc_lines[i].lower():
                warnings.append(f"META-002: Açıklama satır {i+1} şablondan sapıyor — bekleyen: {required}")
    else:
        warnings.append("META-002: meta.json'da 'description' alanı yok — upload.py şablonu kullanacak.")

    # META-003: Etiketler — 8 specific + 3 broad
    tags = meta.get("tags", [])
    if isinstance(tags, list) and tags:
        specific = [t for t in tags if len(t.split()) >= 2 or "turkish" in t.lower() or "arabesk" in t.lower() or "techno" in t.lower() or "melodic" in t.lower()]
        broad = [t for t in tags if t.lower() in ("music", "youtube music", "new music 2026", "new music", "2026 music")]
        if len(specific) < 8:
            warnings.append(f"META-003: Specific etiket sayısı {len(specific)} < 8 — niche etiket ekle (örn. 'turkish pop', 'arabesk trap', 'melodic techno mix').")
        if len(broad) != 3:
            warnings.append(f"META-003: Broad etiket sayısı {len(broad)} != 3 — tam 3 broad etiket olmalı (music, youtube music, new music 2026).")
    else:
        warnings.append("META-003: meta.json'da 'tags' listesi eksik veya boş.")

    # META-004: Bölümler (Chapters) — Minimum 3, açıklayıcı başlıklar
    tracklist = meta.get("tracklist")
    if isinstance(tracklist, list) and tracklist:
        if len(tracklist) < 3:
            warnings.append(f"META-004: Chapter/bölüm sayısı {len(tracklist)} < 3 — minimum 3 chapter gerekli (YouTube chapter SEO).")
        yer_tutucu = []
        for t in tracklist:
            if isinstance(t, dict):
                title_t = (t.get("title") or "").strip()
                if re.match(r"^(Track|Parça|Bölüm|Chapter)\s*\d+\s*$", title_t, re.IGNORECASE):
                    yer_tutucu.append(title_t)
        if yer_tutucu:
            errors.append(f"META-004: {len(yer_tutucu)} yer tutucu chapter başlığı — duygulu başlık yaz (örn. 'Golden Hour - Peak Energy'). KIRMIZI ÇİZGİ: Placeholder chapter başlığı (Track N) = Chapter SEO kaybı, render durduruluyor.")
    else:
        warnings.append("META-004: meta.json'da 'tracklist' (chapters) eksik — uzun videolarda chapter SEO kaybı.")

    # META-005: Hashtags — 3-5 niche + 1 broad, yasak AI hashtag yok (SAFETY-003)
    hashtags = meta.get("hashtags", [])
    if isinstance(hashtags, list) and hashtags:
        niche = [h for h in hashtags if h.lower() not in ("#music", "#youtubemusic", "#newmusic2026", "#newmusic", "#2026music")]
        broad = [h for h in hashtags if h.lower() in ("#music", "#youtubemusic", "#newmusic2026", "#newmusic", "#2026music")]
        if len(niche) < 3 or len(niche) > 5:
            warnings.append(f"META-005: Niche hashtag sayısı {len(niche)} — 3-5 arası olmalı.")
        if len(broad) != 1:
            warnings.append(f"META-005: Broad hashtag sayısı {len(broad)} — tam 1 olmalı (#music vb.).")
        # SAFETY-003: Yasak AI hashtag kontrolü
        for h in hashtags:
            h_low = h.lower().lstrip("#")
            if f"#{h_low}" in YASAK_AI_HASHTAGS:
                errors.append(f"SAFETY-003: YASAK AI hashtag tespit edildi: {h} — izin verilenler: {', '.join(sorted(IZINLI_AI_HASHTAGS))}")
    else:
        warnings.append("META-005: meta.json'da 'hashtags' listesi eksik.")


def _validate_youtube_content_structure(project_dir: str, meta: dict,
                                         errors: list[str], warnings: list[str]) -> None:
    """CONTENT-001/002/003/004/005: Hook, retention, session extension, engagement, AI beyanı."""
    # CONTENT-001: Hook — İlk 30sn %70+ retention hedefi (render.py COLD_OPEN + DIKEY_HOOK kontrolü)
    # Bu validasyonda sadece meta.json'da ilgili alanların varlığını kontrol ediyoruz.
    # Gerçek retention analizi için olcum_temel_cizgi.py kullanılır.
    if not meta.get("cold_open_enabled", True):
        warnings.append("CONTENT-001: Cold open devre dışı — ilk 30sn retention hedefi (%70+) zorlaşabilir.")
    if not meta.get("dikey_hook_enabled", True):
        warnings.append("CONTENT-001 (Shorts): Dikey hook devre dışı — ilk 1sn chorus kesiti + 'Sesini Aç' animasyonu eksik.")

    # CONTENT-002: Retention yapısı — Görsel nabız, bölüm bazlı görsel değişim
    if not meta.get("gorse_nabiz_enabled", True):
        warnings.append("CONTENT-002: Görsel nabız devre dışı — ~25sn'de hue/pan vurgusu eksik (retention riski).")
    sozler_path = os.path.join(project_dir, "sozler.md")
    structure_path = os.path.join(project_dir, "structure.txt")
    if os.path.isfile(sozler_path) and os.path.isfile(structure_path):
        # Söz zamanlaması varsa bölüm bazlı görsel değişim ZORUNLU (render.py'de implementasyon)
        pass  # render.py zaten bunu yapıyor
    else:
        warnings.append("CONTENT-002: sozler.md veya structure.txt eksik — bölüm bazlı görsel değişim (zoom/pan/hue) uygulanamayacak.")

    # CONTENT-003: Session Extension — End card + Playlist ataması
    if not meta.get("end_card_text"):
        warnings.append("CONTENT-003: end_card_text eksik — video bitiş 15sn'de 'Sonraki parça' kartı çıkmayacak.")
    # Playlist ataması upload.py'de yapılır; burada meta.json'da playlist_ids alanı kontrolü
    playlist_ids = meta.get("playlist_ids", [])
    if not playlist_ids:
        warnings.append("CONTENT-003: meta.json'da 'playlist_ids' eksik — video en az 1 ana playlist'e eklenmeli (session extension).")
    else:
        # En az 1 ANA_PLAYLISTLER'e atanmış mı?
        if not any(pid in str(ANA_PLAYLISTLER.values()) for pid in playlist_ids):
            warnings.append(f"CONTENT-003: Playlist ataması ana kategorilerden biri değil — önerilen: {list(ANA_PLAYLISTLER.values())}")

    # CONTENT-004: Engagement Hooks — 3 nokta
    engagement_points = meta.get("engagement_points", [])
    if not engagement_points or len(engagement_points) < 3:
        warnings.append("CONTENT-004: Engagement hook noktaları < 3 — şablon: 0:30, orta, bitiş-15sn.")

    # CONTENT-005: AI Beyanı — Sadece metadata, pikselde YOK
    if not meta.get("ai_disclosure", True):
        errors.append("CONTENT-005: AI beyanı (ai_disclosure) eksik — YouTube 'containsSyntheticMedia=True' + açıklama satırı ZORUNLU.")
    # Pikselde AI rozeti YASAK — render.py'de implementasyon kontrolü
    if meta.get("ai_badge_on_video", False):
        errors.append("CONTENT-005: ai_badge_on_video=true — KIRMIZI ÇİZGİ: Video üzerine AI rozeti/overlay YASAK (sadece metadata).")


def _validate_youtube_tech_production(project_dir: str, meta: dict,
                                       errors: list[str], warnings: list[str]) -> None:
    """TECH-001/002/003/004: Kapak, video kalitesi, dosya isimlendirme, DJ set."""
    # TECH-001: Kapak — İki oran (16:9 + 9:16), tipografi kuralları
    cover_16x9 = os.path.join(project_dir, "cover.png")
    cover_9x16 = os.path.join(project_dir, "cover_vertical.png")
    if not os.path.isfile(cover_16x9):
        errors.append("TECH-001: cover.png (16:9) eksik — YouTube uzun video kapak.")
    if not os.path.isfile(cover_9x16):
        errors.append("TECH-001: cover_vertical.png (9:16) eksik — Shorts/Reels/TikTok kapak.")
    # Tipografi ve logo kontrolü generate_cover.py'de yapılır; burada dosya varlığı yeterli

    # TECH-002: Video kalitesi — Platform bazlı spec (render.py parametreleri)
    # validate() içinde _kalite_kontrolu() zaten çözünürlüğü kontrol ediyor
    pass

    # TECH-003: Dosya isimlendirme — {project_id}_{platform}_{timestamp}.{ext}
    state_path = os.path.join(project_dir, "state.json")
    if os.path.isfile(state_path):
        try:
            with open(state_path, encoding="utf-8") as f:
                state = json.load(f)
            rendered = state.get("rendered", {})
            for platform, info in rendered.items():
                if isinstance(info, dict):
                    filepath = info.get("filepath", "")
                    if filepath:
                        fname = os.path.basename(filepath)
                        # Basit format kontrolü
                        if not re.match(r"^[a-z0-9-]+_[a-z0-9_]+_\d{8}_\d{6}\.(mp4|jpg|png|wav|mp3)$", fname):
                            warnings.append(f"TECH-003: Dosya adı formatı standart dışı: {fname} — bekleyen: {{project}}_{{platform}}_{{YYYYMMDD_HHMMSS}}.ext")
        except Exception:
            pass

    # TECH-004: DJ Set özel kuralları
    if meta.get("theme") == "dj":
        tracklist = meta.get("tracklist", [])
        if not tracklist:
            errors.append("TECH-004: DJ set için 'tracklist' zorunlu (her track: start_time, end_time, title, artist, bpm, key).")
        else:
            for i, t in enumerate(tracklist):
                if not isinstance(t, dict):
                    continue
                required = ["start_time", "end_time", "title", "artist", "bpm", "key"]
                for field in required:
                    if field not in t or not t[field]:
                        warnings.append(f"TECH-004: Track {i+1} için '{field}' alanı eksik.")
        # Chapter (ffmeta) render.py'de üretilir; meta'da tracklist varsa chapter beklenir
        # HUD efektleri render.py parametreleri — burada sadece meta kontrolü
        if not meta.get("dj_hud_enabled", True):
            warnings.append("TECH-004: DJ HUD (nefes/sahne modu) devre dışı — marka kimliği zayıflar.")


def _validate_youtube_publish_strategy(project_dir: str, meta: dict,
                                        errors: list[str], warnings: list[str]) -> None:
    """PUBLISH-001/002/003/004/005: YouTube, IG, TikTok, FB, TG/Bluesky yayım stratejisi."""
    # PUBLISH-001: YouTube Native Schedule — Golden Hour
    publish_at = meta.get("publish_at")
    if publish_at:
        try:
            dt = datetime.fromisoformat(publish_at.replace("Z", "+00:00"))
            hour = dt.hour
            in_golden = any(start <= hour < end for start, end in GOLDEN_HOUR_PENCERELERI)
            if not in_golden:
                warnings.append(f"PUBLISH-001: Yayın saati {hour:02d}:00 — Golden Hour (12-14 / 18-22) dışında. CTR/APV etkilenebilir.")
        except Exception:
            warnings.append("PUBLISH-001: publish_at formatı ISO 8601 olmalı (örn. 2026-10-20T18:30:00+03:00).")
    else:
        warnings.append("PUBLISH-001: meta.json'da 'publish_at' yok — Golden Hour'da native schedule önerilir.")
    # Shorts ayrı upload (aynı video ID) — upload.py'de implementasyon

    # PUBLISH-002: Instagram Reels — Container + Publish (23sa ömür)
    # Sadece meta kontrolü; upload_instagram.py implementasyon
    if not meta.get("ig_container_strategy", True):
        warnings.append("PUBLISH-002: Instagram container stratejisi devre dışı — 23sa ömürlü container + media_publish akışı önerilir.")

    # PUBLISH-003: TikTok — Draft + Elle Yayın
    if not meta.get("tiktok_draft_upload", True):
        warnings.append("PUBLISH-003: TikTok draft upload devre dışı — tiktok_publish_plan.py CLI akışı önerilir.")

    # PUBLISH-004: Facebook Reels — Native Schedule
    if not meta.get("fb_native_schedule", True):
        warnings.append("PUBLISH-004: Facebook native schedule (video_state=SCHEDULED) devre dışı.")

    # PUBLISH-005: Telegram / Bluesky — Sadece Backfill
    if not meta.get("telegram_backfill_only", True):
        warnings.append("PUBLISH-005: Telegram/Bluesky doğrudan upload — sadece ek_platform_backfill.py (Golden Hour + günlük tavan + politika kapısı) kullanılmalı.")


def _validate_youtube_channel_health(project_dir: str, meta: dict,
                                      errors: list[str], warnings: list[str]) -> None:
    """CHANNEL-001/002/003/004: Playlist, trailer, banner, community."""
    # CHANNEL-001: 4 Ana Playlist — En az 1'e atanmış olmalı
    playlist_ids = meta.get("playlist_ids", [])
    if not playlist_ids:
        warnings.append(f"CHANNEL-001: Playlist ataması yok — ana kategoriler: {list(ANA_PLAYLISTLER.values())}")
    
    # CHANNEL-002/003/004: Bu kontroller elle_islem.py / YouTube Studio'da yapılır
    # Sadece meta.json'da ilgili alanların varlığını hatırlatıyoruz
    if meta.get("theme") == "dj":
        if not meta.get("channel_trailer_updated", False):
            warnings.append("CHANNEL-002: DJ set sonrası channel trailer güncellenmeli (Night Drive DJ Cut).")
    if not meta.get("banner_updated", False):
        warnings.append("CHANNEL-003: Kanal banner güncellenmeli (2560x1440, safe area 1546x423).")
    # Community haftalık — elle_islem.py / weekly_community_post.py


def _validate_youtube_safety_policies(project_dir: str, meta: dict,
                                       errors: list[str], warnings: list[str]) -> None:
    """SAFETY-001/002/003/004: Clickbait, telif/MD5/AI, AI hashtag ban, günlük tavan."""
    # SAFETY-001: Clickbait koruması — zaten _validate_youtube_metadata içinde
    
    # SAFETY-002: Telif / MD5 / AI beyanı — uyumluluk.kontrol() içinde (fail-closed)
    # Burada sadece meta.json'da ilgili alanların varlığını kontrol
    if not meta.get("copyright_cleared", False):
        warnings.append("SAFETY-002: copyright_cleared=false — telif temizliği onayı bekleniyor (uyumluluk.kontrol fail-closed).")
    if not meta.get("md5_checked", False):
        warnings.append("SAFETY-002: md5_checked=false — MD5 kopya kontrolü bekleniyor (uyumluluk.kontrol fail-closed).")
    if not meta.get("compilation_flag", False) and meta.get("is_compilation", False):
        warnings.append("SAFETY-002: Derleme (compilation) damgası eksik — uyumluluk.kontrol'de kontrol edilir.")

    # SAFETY-003: AI hashtag ban — zaten _validate_youtube_metadata içinde

    # SAFETY-004: Günlük Yükleme Tavanı — Max 3 (state.json'da takip)
    state_path = os.path.join(project_dir, "state.json")
    if os.path.isfile(state_path):
        try:
            with open(state_path, encoding="utf-8") as f:
                state = json.load(f)
            daily_count = state.get("daily_upload_count", 0)
            if daily_count >= 3:
                errors.append(f"SAFETY-004: Günlük yükleme sayısı {daily_count} ≥ 3 — tavan aşıldı, bu proje bugün yüklenemez.")
        except Exception:
            pass


def _validate_youtube_measurement(project_dir: str, meta: dict,
                                   errors: list[str], warnings: list[str]) -> None:
    """MEASURE-001/002/003/004: Temel çizgi, günlük/haftalık rapor, elle işlem defteri."""
    # MEASURE-001: Temel çizgi ölçümü — Her kapak/video değişikliğinde
    if meta.get("cover_changed", False) or meta.get("video_changed", False):
        if not meta.get("baseline_captured", False):
            warnings.append("MEASURE-001: Kapak/video değişti ama 'olcum_temel_cizgi.py --cek' çalıştırılmamış — etki ölçülemez.")
    
    # MEASURE-004: Elle işlem defteri — elle_islem.py ile kayıt
    elle_islem_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "elle_islemler.jsonl")
    if not os.path.isfile(elle_islem_path):
        warnings.append("MEASURE-004: elle_islemler.jsonl bulunamadı — manuel işlemler kaydedilmeli (elle_islem.py ekle ...).")


def _safe_print(text: str) -> None:
    """Windows konsolu (cp1254) için emoji güvenli yazdırma."""
    try:
        print(text)
    except UnicodeEncodeError:
        # Emoji'leri ASCII karşılıklarıyla değiştir
        replacements = {
            '🎵': '[MUZIK]', '🌙': '[AY]', '🎧': '[KULAKLIK]',
            '☕': '[KAHVE]', '📱': '[TELEFON]', '📧': '[EPOSTA]',
            '🎛️': '[DJ]', '🆕': '[YENI]', '🔴': '[KIRMIZI]',
            '🟠': '[TURUNCU]', '🟡': '[SARI]', '🟢': '[YESIL]',
            '🔵': '[MAVI]', '🟣': '[MOR]', '⚠️': '[UYARI]', '✅': '[OK]',
            '❌': '[HATA]', '🎤': '[MIKROFON]', '🎸': '[GITAR]',
            '🎹': '[PIYANO]', '🎛': '[MIKSER]', '📊': '[GRAFIK]',
            '📈': '[ARTIS]', '📉': '[DUSUS]', '🎯': '[HEDEF]',
            '🔑': '[ANAHTAR]', '🔒': '[KILIT]', '🔓': '[ACIK]',
            '⏰': '[SAAT]', '⚡': '[YILDIRIM]', '💡': '[AMPOL]',
            '🚀': '[ROKET]', '🎬': '[KLAKET]', '📝': '[NOT]',
            '📋': '[LISTE]', '📂': '[KLASOR]', '📁': '[KLASOR2]',
        }
        for emoji, ascii_repr in replacements.items():
            text = text.replace(emoji, ascii_repr)
        # Kalan encode edilemeyen karakterleri temizle
        text = text.encode('cp1254', errors='replace').decode('cp1254')
        print(text)

def print_report(project_dir: str, errors: list[str], warnings: list[str]) -> None:
    name = os.path.basename(os.path.normpath(project_dir))
    for e in errors:
        _safe_print(f"  [{name}] HATA: {e}")
    for w in warnings:
        _safe_print(f"  [{name}] UYARI: {w}")


def main():
    parser = argparse.ArgumentParser(
        description="Render'dan önce bir projenin (veya tüm projelerin) girdilerini doğrular."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--project", help="Tek bir proje klasörü (örn. projects/sarki-adi)")
    group.add_argument("--all", action="store_true",
                       help="TÜM içerik köklerindeki (projects/, dj_sets/, derlemeler/) "
                            "klasörleri kontrol et")
    args = parser.parse_args()

    if args.project:
        project_dirs = [args.project]
    else:
        # ÜÇ içerik kökü de taranıyor. Eskiden sadece `projects/` idi: boru hattı
        # validate()'i zaten proje bazında çağırdığı için (render.py) bu etki
        # olarak küçüktü, ama ELLE yapılan tam-katalog koşusu ("her şey sağlam
        # mı") DJ setlerini ve derlemeleri hiç görmüyordu — yani "sorun yok"
        # çıktısı kataloğun bir bölümü için hiçbir şey ifade etmiyordu.
        # Kök listesi ELLE sayılmıyor: kanonik kaynak uyumluluk.KOKLER
        # (muhafız: tests/test_kok_listesi_muhafizi.py). Yollar MUTLAK, yani
        # script hangi klasörden çağrılırsa çağrılsın aynı kümeye bakıyor.
        # Import BURADA (modül düzeyinde değil): `uyumluluk` bu dosyada
        # bilerek TEMBEL import ediliyor (bkz. validate() içindeki try/except) —
        # bozuk bir uyumluluk.py render hattını durdurmasın diye. Aynı disiplin.
        import uyumluluk
        project_dirs = list(uyumluluk.proje_klasorleri())

    any_errors = False
    for project_dir in project_dirs:
        errors, warnings = validate(project_dir)
        if errors or warnings:
            print_report(project_dir, errors, warnings)
        else:
            print(f"  [{os.path.basename(os.path.normpath(project_dir))}] sorun yok.")
        if errors:
            any_errors = True

    sys.exit(1 if any_errors else 0)


if __name__ == "__main__":
    main()
