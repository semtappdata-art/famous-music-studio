"""Suno ses dosyalarından tüm platformlar için video üreten ana script.

Kullanım:
    python render.py --project projects/sarki-adi
    python render.py --all
"""

import argparse
import hashlib
import json
import math
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import config
import ffmpeg_utils
import gorsel_dil
import state_io
import uyumluluk
import validate_project
from audio_highlight import find_highlight

COVER_NAMES = ["cover.jpg", "cover.jpeg", "cover.png"]
COVER_VERTICAL_NAMES = ["cover_vertical.jpg", "cover_vertical.jpeg", "cover_vertical.png"]
ART_NAMES = ["art.jpg", "art.jpeg", "art.png"]
AUDIO_NAMES = ["audio.wav", "audio.mp3", "audio.m4a"]

# --- Görsel Dil Parametre Önbelleği (gorsel_dil.py) ---
GORS_DIL_OLCUM_ALANI = "gorsel_dil_olcum"

# Render çıktısı ÖNCE bu sonekle yazılıyor, ffmpeg 0 ile döndükten SONRA
# os.replace ile nihai adına taşınıyor (bkz. render_one). state_io.py'deki
# atomik yazım deseninin aynısı, aynı gerekçeyle: ffmpeg `-y` ile DOĞRUDAN
# nihai dosyaya yazdığı sürece yarıda kesilen bir render diskte "yarım ama VAR"
# bir .mp4 bırakır.
PARCALI_SONEK = ".partial.mp4"

# ffprobe'un ÇALIŞTIRILAMADIĞI bir koşuda uyarı koşu başına BİR kez yazılsın diye
# (bkz. video_butun_mu). Sessizce sertleşmek de sessizce gevşemek de kötü —
# CLAUDE.md, "BAĞLANTI seviyesindeki sessiz arıza".
_FFPROBE_YOK_UYARILDI = False


def video_butun_mu(path: str, log=print) -> bool:
    """Bir render çıktısının VAR olduğunu değil, BÜTÜN olduğunu söyler.

    NEDEN VAR (2026-09-12): `auto_process._is_rendered()` ve
    `dj_famous_process._is_rendered()` hazırlığı YALNIZCA `os.path.isfile` ile
    ölçüyordu. ffmpeg `-y` ile doğrudan nihai dosyaya yazdığı için yarıda
    kesilen bir render (süreç öldürülür, elektrik gider, pil biter,
    `ExecutionTimeLimit` dolar, `MAX_PARALLEL_RENDERS=2` ile ikinci render
    çakılır) diskte 0 baytlık ya da yarım bir .mp4 bırakıyor; `isfile` buna
    True diyor, sonraki koşu render'ı ATLIYOR ve BOZUK videoyu altı platforma
    yüklüyor. Log'da yalnızca "Zaten render edilmiş" yazdığı için arıza SESSİZ.

    İKİ AYRI DÜZELTME VAR ve BİRBİRİNİN YERİNE GEÇMİYOR — ikisi de bilerek:
      * `render_one` artık geçici ada yazıp `os.replace` ediyor (aşağı bak):
        BUNDAN SONRAKİ render'larda yarım dosya nihai adla HİÇ var olmuyor.
        Kökten çözüm, ama yalnızca ileriye dönük.
      * bu fonksiyon: DİSKTE ŞU AN duran (eski, atomik-öncesi) yarım dosyaları
        da yakalıyor, ve `os.replace`'in kapsamadığı durumları da — dosya
        sonradan bozulursa, ya da elle/başka bir araçla yarım kopyalanırsa.

    ÖLÇÜT SIRASI:
      1. dosya yok             -> False
      2. 0 bayt                -> False (ffprobe'a hiç girmeden; en sık vaka,
         süreç muxer'ı açar açmaz ölmüşse dosya boştur)
      3. ffprobe süre veremedi -> False (yarım mp4'te `moov atom not found`;
         moov atom'unu ffmpeg dosyanın SONUNA yazdığı için kesik bir dosyada
         ASLA bulunmaz — %1/%10/%50/%90 kesme oranlarıyla ölçüldü, dördü de
         rc=1 verdi)
      4. süre <= 0             -> False
      5. aksi hâlde            -> True

    ffprobe'un KENDİSİ çalıştırılamıyorsa (kurulu değil / PATH'te yok) ZARİF
    DÜŞÜŞ: eski `isfile` davranışına dönülüyor ve koşu başına BİR kez log'a
    satır düşüyor. "Çalıştıramadım" (OSError) ile "çalıştırdım, dosyayı
    okuyamadı" (RuntimeError) AYRI şeyler: ikincisi bozukluk KANITIdır,
    birincisi bilgisizliktir — ve bilgisizliği "yeniden render et"e çevirmek
    ffprobe'suz bir makinede boru hattını sonsuz render'a sokardı.

    ffprobe ÇAĞRISI KOPYALANMADI: `ffmpeg_utils.get_audio_duration()` tam da bu
    komutu (`-show_entries format=duration`) çalıştırıyor ve video dosyasında da
    aynen çalışıyor (format süresi, akış türünden bağımsız). Mantık kopyalamak
    bu deponun belgelenmiş hata sınıfı — o yüzden OKUNDU ve ORTAK KULLANILDI.
    Bu fonksiyonun BURADA (render.py'de) durmasının sebebi de aynı: hem
    `auto_process.py` hem `dj_famous_process.py` bu modülü zaten
    `render_module` olarak import ediyor, yani tek gövde iki çağırana yetiyor.

    MALİYET: `_is_rendered()` proje başına koşuda BİR kez çağrılıyor
    (`process_project()` içinde, iki dosyada da TEK çağrı yeri), yani en fazla
    2 ffprobe süreci. Ölçüm: diskteki 48 gerçek çıktıda dosya başına ~0,077 sn
    -> koşu başına ~0,15 sn. Render'ın kendisi tek şarkıda 2 dk 26 sn.
    ÖNBELLEK EKLENMEDİ: mtime+boyut anahtarlı bir önbellek ölçülemez bir kazanç
    için geriye kendi tazeleme hatalarını bırakırdı.
    """
    global _FFPROBE_YOK_UYARILDI
    if not os.path.isfile(path):
        return False
    try:
        if os.path.getsize(path) == 0:
            return False
    except OSError:
        return False
    try:
        sure = ffmpeg_utils.get_audio_duration(path)
    except OSError:
        # FileNotFoundError DAHİL: ffprobe ÇALIŞTIRILAMADI -> eski davranışa dön.
        if not _FFPROBE_YOK_UYARILDI:
            _FFPROBE_YOK_UYARILDI = True
            log("  UYARI: ffprobe çalıştırılamadı — render çıktılarının BÜTÜNLÜĞÜ "
                "bu koşuda DOĞRULANAMIYOR, yalnızca dosyanın varlığına bakılıyor "
                "(yarım bir .mp4 'hazır' sayılabilir).")
        return True
    except RuntimeError:
        # ffprobe ÇALIŞTI ve süre veremedi/geçersiz verdi -> dosya bozuk/yarım.
        return False
    return sure > 0


def find_cover(project_dir: str) -> str | None:
    for name in COVER_NAMES:
        path = os.path.join(project_dir, name)
        if os.path.isfile(path):
            return path
    return None


def find_intro_cover(project_dir: str, width: int, height: int) -> str | None:
    """Açılışta tam ekran gösterilecek kapak — platformun oranına göre YATAY
    (cover.png, 16:9) ya da DİKEY (cover_vertical.png, 9:16) olanı.

    NEDEN kapak, art.jpg değil: amaç ilk karenin izleyicinin TIKLADIĞI görselle
    birebir aynı olması (bkz. config.INTRO_KAPAK). cover.png zaten YouTube'a
    yüklenen küçük resmin ta kendisi — başlık yazısı ve logosuyla birlikte.
    art.jpg ise başlıksız, kare bir görsel; tıklama sürekliliğini kurmuyor."""
    names = COVER_VERTICAL_NAMES if height > width else COVER_NAMES
    for name in names:
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


def _gorsel_dil_parametreleri(project_dir: str, audio_path: str, art_path: str,
                              meta: dict) -> dict | None:
    """Görsel dil parametrelerini hesaplar; None ise bayrak kapalı ya da ölçülemedi.

    measure_bpm state.json'da önbellekli (audio md5'li): tekrar render'larda
    librosa yüklemesi yapılmaz. Backdrop path dahil DEĞİL — her platform için
    çözünürlük ayrı olduğu için render_one içinde üretiliyor."""
    if not config.GORSEL_DIL_AKTIF:
        return None

    audio_md5 = None
    try:
        audio_md5 = _dosya_md5(audio_path)
    except OSError:
        pass

    durum = {}
    try:
        durum = uyumluluk._durum(project_dir)
    except Exception:  # noqa: BLE001
        pass

    onceki = durum.get(GORS_DIL_OLCUM_ALANI)
    if (isinstance(onceki, dict)
            and onceki.get("md5") == audio_md5
            and isinstance(onceki.get("bpm"), (int, float))):
        bpm = float(onceki["bpm"])
        sure = float(onceki.get("sure", 0))
    else:
        try:
            bpm, sure = gorsel_dil.measure_bpm(audio_path)
        except Exception as e:
            print(f"  UYARI: görsel dil BPM ölçümü başarısız: {type(e).__name__}: {e}")
            return None
        # State'i tazele
        try:
            taze = uyumluluk._durum(project_dir)
            taze[GORS_DIL_OLCUM_ALANI] = {
                "bpm": bpm, "sure": sure,
                "md5": audio_md5,
                "olcum_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
            state_io.durum_yaz(project_dir, taze)
        except Exception:  # noqa: BLE001
            pass

    title = meta.get("title") or os.path.basename(project_dir)
    theme_key = meta.get("theme", config.DEFAULT_THEME)
    theme = config.THEMES.get(theme_key, config.THEMES[config.DEFAULT_THEME])
    accent = tuple(theme["accent"])

    import gorsel_dil as _gd
    seed = _gd._song_hash(title)
    nabiz_expr, nabiz_hz, flash_per_sn = _gd.nabiz_ifadesi(bpm)
    mood = _gd.mood_olc(title)
    grain = _gd.doku_filtresi(seed ^ 0xA55A)
    grade = _gd.derecelendirme_filtresi(mood, accent)

    if flash_per_sn >= 3:
        print(f"  UYARI: görsel dil flash hızı fotoepilepsi eşiğini aşıyor: "
              f"{flash_per_sn:.2f}/sn (sinif={_gd.enerji_sinifi(bpm)})")

    return {
        "nabiz_expr": nabiz_expr, "grain": grain, "grade": grade,
        "seed": seed, "accent": accent, "bpm": bpm,
    }


# state.json'daki ölçüm anahtarı: {"lufs", "tp", "lra", "olcum_at", "md5"}.
SES_OLCUM_ALANI = "ses_olcum"


def _ses_uyarisi(anahtar: str, mesaj: str) -> None:
    """Satırı ÇALIŞAN betiğin log'una da düşürür (koşu başına bir kez).

    NEDEN print YETMİYOR: saatlik görev `pythonw` ile koşuyor ve orada
    `sys.stdout` None; `print` hiçbir yere gitmiyor (gorev_sarmalayici.py).
    render.py'nin bütün print'leri zamanlanmış koşuda GÖRÜNMEZ. Limiter kararı
    ve ölçüm arızası "çalıştı mı?" sorusunun cevabı, log'da olmalı."""
    try:
        import notify
        notify.uyar_bir_kez(anahtar, mesaj)
    except Exception:  # noqa: BLE001 — log satırı render'ı asla durdurmamalı
        pass


def _dosya_md5(yol: str) -> str:
    h = hashlib.md5()
    with open(yol, "rb") as f:
        for parca in iter(lambda: f.read(1 << 20), b""):
            h.update(parca)
    return h.hexdigest()


def _olcum_gecerli(olcum) -> bool:
    return (isinstance(olcum, dict)
            and all(isinstance(olcum.get(k), (int, float))
                    and not isinstance(olcum.get(k), bool)
                    for k in ("lufs", "tp", "lra")))


def ses_olcumu(project_dir: str, audio_path: str) -> dict | None:
    """Sesin loudness/true-peak ölçümü; state.json önbellekli. Başarısızsa None.

    SIRA:
      1. sesin md5'i; state.json'daki `ses_olcum.md5` aynıysa ffmpeg'e HİÇ
         girilmeden o kayıt dönüyor (take değişmediyse tekrar ölçülmez).
      2. değilse `ffmpeg_utils.ses_olc` (ebur128=peak=true).
      3. state.json ZATEN VARSA ölçüm `state_io` ile yazılıyor; yazmadan hemen
         önce state TAZE okunuyor (render dakikalar sürüyor, bu arada yükleme
         adımları ya da paralel bir koşu başka anahtar yazmış olabilir).

    state.json YOKSA OLUŞTURULMUYOR, bilerek: yeni bir projede ilk render
    yüklemeden ÖNCE koşuyor ve `tiktok_upload`, `bluesky_upload`,
    `facebook_upload` taramaları "state.json yoksa bu proje hiç yüklenmemiş,
    atla" varsayımıyla çalışıyor. Yalnız `ses_olcum` içeren bir state.json o
    varsayımı sessizce bozardı. Bedeli: ilk render'da ölçüm önbelleğe girmez,
    yeniden render'da (birkaç saniye) tekrar ölçülür.

    BOZUK state.json'ın ÜSTÜNE YAZILMIYOR (uyumluluk._durum HATA sınıfı): onu
    `{}` sayıp yazmak `telif_araliklari` gibi kapıları silerdi. Ölçüm yine de
    bu render'da kullanılıyor.

    Hiçbir arıza render'ı DURDURMUYOR: None dönüyor, çağıran limitersiz
    (eski davranış) sürüyor ve log'a UYARI düşüyor."""
    ad = os.path.basename(os.path.normpath(project_dir))
    state_yolu = os.path.join(project_dir, "state.json")
    try:
        md5 = _dosya_md5(audio_path)
    except OSError as e:
        mesaj = (f"UYARI: ses ölçümü yapılamadı ({ad}): ses okunamadı: {e} — "
                 f"limiter kararı verilemedi, render limitersiz sürüyor")
        print("  " + mesaj)
        _ses_uyarisi(f"ses_olcum:{ad}", mesaj)
        return None

    durum_okunabildi = True
    try:
        durum = uyumluluk._durum(project_dir)
    except Exception as e:  # noqa: BLE001 — DurumBozuk dahil
        durum_okunabildi = False
        durum = {}
        print(f"  UYARI: state.json okunamadı ({type(e).__name__}); ses ölçümü bu "
              f"render'da kullanılacak ama state'e YAZILMAYACAK")

    onceki = durum.get(SES_OLCUM_ALANI)
    if _olcum_gecerli(onceki) and onceki.get("md5") == md5:
        print(f"  ses ölçümü (state'ten, aynı ses): {onceki['lufs']} LUFS, "
              f"TP {onceki['tp']} dBTP, LRA {onceki['lra']} LU")
        return onceki

    try:
        olcum = ffmpeg_utils.ses_olc(audio_path)
    except Exception as e:  # noqa: BLE001 — OSError (ffmpeg yok) dahil
        mesaj = (f"UYARI: ses ölçümü başarısız ({ad}): {type(e).__name__}: "
                 f"{str(e)[:200]} — limiter kararı verilemedi, render limitersiz "
                 f"(eski davranış) sürüyor")
        print("  " + mesaj)
        _ses_uyarisi(f"ses_olcum:{ad}", mesaj)
        return None

    kayit = {
        "lufs": olcum["lufs"], "tp": olcum["tp"], "lra": olcum["lra"],
        "olcum_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "md5": md5,
    }
    print(f"  ses ölçümü: {kayit['lufs']} LUFS, TP {kayit['tp']} dBTP, LRA {kayit['lra']} LU")
    if durum_okunabildi and os.path.isfile(state_yolu):
        try:
            taze = uyumluluk._durum(project_dir)
            taze[SES_OLCUM_ALANI] = kayit
            state_io.durum_yaz(project_dir, taze)
        except Exception as e:  # noqa: BLE001
            print(f"  UYARI: ses ölçümü state.json'a yazılamadı: {type(e).__name__}: {e}")
    return kayit


def limiter_gerekli(olcum) -> bool:
    """Ölçülen TP `config.SES_TP_ESIK_DBTP`yi AŞIYORSA (eşitse değil) True.
    Ölçüm yoksa / geçersizse False: limiter bir iyileştirme, kapı değil."""
    if not config.SES_LIMITER_ACIK or not isinstance(olcum, dict):
        return False
    tp = olcum.get("tp")
    if isinstance(tp, bool) or not isinstance(tp, (int, float)):
        return False
    return tp > config.SES_TP_ESIK_DBTP


def _gecerli_saniye(x) -> bool:
    return (isinstance(x, (int, float)) and not isinstance(x, bool)
            and math.isfinite(x) and x >= 0)


def meta_highlight(meta: dict, audio_path: str | None = None):
    """meta.json'dan Shorts kesiti: `(bas, son)` ya da None (= otomatik tespit).

      * iki alan da yok                  -> None (bugünkü davranış)
      * YALNIZ `highlight_start` (2026-09-13) -> (bas, bas + HIGHLIGHT_DURATION).
        Nakaratın başını elle işaretlemenin en ucuz yolu; RMS penceresi bazen
        nakaratın ortasından kesiyor (`suno_kalite_onerileri.md` §1 #9).
        Geçersizse (negatif, sayı değil, sesin sonundan sonra) UYARI + None.
      * YALNIZ `highlight_end`           -> UYARI + None (eski davranış aynen)
      * ikisi de var                     -> olduğu gibi (eski davranış aynen)

    OTOMATİK `highlight_start` ÖNERİSİ YOK, bilerek: sözlerdeki ilk [Chorus]'un
    ZAMANI yerelde hiçbir yerde tutulmuyor. Tek zaman kaynağı olan altyazı
    hizalaması (`upload/youtube_captions.py` -> `caption_align.align`)
    YouTube'un ASR altyazısını API'den indirip geçici klasörde hizalıyor ve
    sonucu yerelde saklamıyor; üstelik yükleme SONRASI çalışıyor, Shorts
    render'ı ise yüklemeden ÖNCE. Tahminle yazılan bir başlangıç, RMS
    tespitinden daha kötü olurdu.

    DJ kesitleri (`dj_clips.clip_uret`) bu fonksiyonu KULLANMIYOR."""
    bas = meta.get("highlight_start")
    son = meta.get("highlight_end")
    if bas is None and son is None:
        return None
    if son is None:
        if not _gecerli_saniye(bas):
            print(f"  UYARI: meta.json highlight_start geçersiz ({bas!r}) — "
                  f"otomatik tespite geçiliyor.")
            return None
        if audio_path:
            try:
                toplam = ffmpeg_utils.get_audio_duration(audio_path)
            except (OSError, RuntimeError):
                toplam = None
            if toplam is not None and bas >= toplam:
                print(f"  UYARI: meta.json highlight_start ({bas}) sesin süresini "
                      f"({toplam:.1f}s) aşıyor — otomatik tespite geçiliyor.")
                return None
        return bas, bas + config.HIGHLIGHT_DURATION
    if bas is None:
        print(
            "  UYARI: meta.json'da yalnız highlight_end var; highlight_start olmadan "
            "kullanılamaz — göz ardı edilip otomatik tespite geçiliyor."
        )
        return None
    return bas, son


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

    # GÖRSEL DİL — şarkıdan türetilen nabız/doku/derecelendirme parametreleri.
    # Backdrop burada DEĞİL, render_one içinde her platform için ayrı üretiliyor.
    dil_base = _gorsel_dil_parametreleri(project_dir, audio_path, art_path or "", meta)
    if dil_base is not None:
        print(f"  görsel dil: aktif (BPM {dil_base['bpm']:.1f}, nabız dahil)")

    # KOŞULLU TRUE-PEAK LİMİTER (2026-09-13, bkz. config.SES_LIMITER_*).
    # Yalnız ölçülen TP eşiği AŞARSA zincire limiter giriyor; loudnorm yok.
    # Ölçüm arızası render'ı durdurmuyor (ses_olcumu None -> limitersiz).
    ses_olcum = ses_olcumu(project_dir, audio_path)
    ses_limiter = limiter_gerekli(ses_olcum)
    if ses_olcum is not None:
        proje_adi = os.path.basename(os.path.normpath(project_dir))
        karar = "EKLENDİ" if ses_limiter else "yok"
        satir = (f"ses: '{proje_adi}' TP {ses_olcum['tp']} dBTP, {ses_olcum['lufs']} LUFS "
                 f"-> limiter {karar} (eşik {config.SES_TP_ESIK_DBTP} dBTP)")
        print("  " + satir)
        _ses_uyarisi(f"ses_karar:{proje_adi}", satir)

    # DJ Famous gibi özel içerikler için kayan yazının içeriğini override eder
    # (ör. "DJ Famous  •  Hafta 1 Seti  •  #DJFamous ...") — sabit alt satır
    # ("Famous Music Studio") HER ZAMAN aynı kalır, bundan etkilenmez.
    marquee_override = meta.get("marquee_text")

    output_dir = os.path.join(project_dir, "output")
    os.makedirs(output_dir, exist_ok=True)

    elle = meta_highlight(meta, audio_path)
    highlight_start, highlight_end = elle if elle else (None, None)
    if highlight_start is None or highlight_end is None:
        if config.HIGHLIGHT_PLATFORMS:
            print("  highlight otomatik tespit ediliyor (en yoğun bölüm)...")
            highlight_start, highlight_end = find_highlight(audio_path, config.HIGHLIGHT_DURATION)
            print(f"  highlight: {highlight_start:.1f}s - {highlight_end:.1f}s")
    else:
        print(f"  highlight (meta.json'dan): {highlight_start:.1f}s - {highlight_end:.1f}s")

    # Proje klasöründe backdrop.mp4 varsa (DJ setleri için stock_video.py
    # üretiyor) arka plan bulanık art.jpg yerine o video oluyor — ama YALNIZCA
    # uzun formatta. 45 saniyelik bir Short'ta tek görsel zaten sıkıcı değil;
    # asıl sorun 80 dakikalık sette hiç değişmeyen bir karede.
    backdrop_path = os.path.join(project_dir, "backdrop.mp4")
    if not os.path.isfile(backdrop_path):
        backdrop_path = None
    else:
        print(f"  arka plan: video ({backdrop_path}) — uzun formatta")

    # HUD kaplaması — arka plan videosuyla AYNI kapsamda: sadece backdrop.mp4
    # olan projelerde (yani DJ setlerinde) ve sadece uzun formatta. Kapsamı
    # backdrop'a bağlamak bilinçli: HUD tek başına, sabit bulanık art.jpg
    # arka planın üzerinde bağlamsız bir çerçeve gibi duruyor.
    hud_hazir = {}

    def _hud(width, height):
        if not (config.DJ_HUD and backdrop_path):
            return None
        if (width, height) not in hud_hazir:
            try:
                import dj_hud
                hud_hazir[(width, height)] = dj_hud.ensure_hud(width, height)
            except Exception as e:
                print(f"  UYARI: HUD üretilemedi, kaplamasız devam ediliyor: {e}")
                hud_hazir[(width, height)] = None
        return hud_hazir[(width, height)]

    def render_one(platform_key, width, height):
        output_path = os.path.join(output_dir, f"{platform_key}.mp4")
        # ATOMİK ÇIKTI (2026-09-12): ffmpeg NİHAİ ada DEĞİL, geçici bir ada
        # yazıyor; dosya ancak ffmpeg 0 ile döndükten sonra os.replace ile
        # nihai adına geçiyor. os.replace aynı klasör içinde Windows'ta da
        # atomik (state_io.durum_yaz ile birebir aynı desen). Böylece yarıda
        # kesilen bir render'ın ardında `youtube_16x9.mp4` adıyla yarım bir
        # dosya KALAMIYOR; geride kalan `.youtube_16x9.partial.mp4` ise
        # RENDER_OUTPUTS'ta olmadığı için hiçbir adımı yanıltmıyor ve bir
        # sonraki render `-y` ile üstüne yazıyor.
        # Geçici ad platform anahtarını TAŞIYOR: MAX_PARALLEL_RENDERS=2 ile
        # aynı anda koşan iki render aynı geçici dosyaya yazmasın diye.
        tmp_path = os.path.join(output_dir, f".{platform_key}{PARCALI_SONEK}")
        print(f"  -> {platform_key} ({width}x{height}) render ediliyor...")
        use_highlight = platform_key in config.HIGHLIGHT_PLATFORMS
        # Açılış kapağı sadece config.INTRO_KAPAK_PLATFORMLAR'daki platformlarda —
        # Shorts akışında küçük resim izleyiciye hiç gösterilmediği için orada
        # tıklama sürekliliği diye bir şey yok.
        intro_cover = (find_intro_cover(project_dir, width, height)
                       if platform_key in config.INTRO_KAPAK_PLATFORMLAR else None)
        try:
            # Görsel dil backdrop: her platform için çözünürlüğü ayrı, cache key ayrı.
            # backdrop.mp4 KULLANILAN projede (DJ sahne modu) huzmeli yok sayılır
            # — render_video `use_backdrop_video` dalında öncelik videodadır.
            render_dil = dict(dil_base) if dil_base else None
            if render_dil and art_path:
                try:
                    render_dil["backdrop"] = gorsel_dil.huzmeli_backdrop_uret(
                        art_path, width, height, dil_base["seed"],
                        cache_dir=output_dir)
                except Exception as e:
                    print(f"  UYARI: huzmeli backdrop üretilemedi: {e}")
                    render_dil = None
            ffmpeg_utils.render_video(
                art_path, audio_path, tmp_path, width, height, title, theme,
                marquee_override=marquee_override,
                start_time=highlight_start if use_highlight else None,
                end_time=highlight_end if use_highlight else None,
                backdrop_video=None if use_highlight else backdrop_path,
                hud_path=None if use_highlight else _hud(width, height),
                kart_goster=not (config.DJ_SAHNE_MODU and backdrop_path
                                 and not use_highlight),
                intro_cover=intro_cover,
                ses_limiter=ses_limiter,
                dil_params=render_dil,
            )
        except BaseException:
            # Hata/iptal durumunda yarım geçici dosyayı bırakma. Süreç
            # ÖLDÜRÜLÜRSE bu dal hiç çalışmaz — sorun değil, o zaman da
            # geride kalan dosyanın adı nihai ad DEĞİL (yukarıdaki nota bak).
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            raise
        # ffmpeg 0 ile döndü: dosya artık BÜTÜN, nihai adına atomik geçiş.
        os.replace(tmp_path, output_path)
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
    group.add_argument(
        "--all", action="store_true",
        # Yardım metni KANONIK listeden türüyor: elle yazılsaydı dördüncü bir
        # kök açıldığında sessizce eskirdi (bkz. uyumluluk.KOK_ADLARI).
        help="%s altındaki tüm proje klasörlerini render et"
             % ", ".join("%s/" % k for k in uyumluluk.KOK_ADLARI))
    args = parser.parse_args()

    if args.project:
        project_dirs = [args.project]
    else:
        # NEDEN kanonik listeye bağlandı: burada kök listesi ELLE sayılıyordu
        # ("projects") ve `dj_sets/` ile `derlemeler/` eklendiğinde bu satır
        # sessizce geride kaldı — elle yapılan tam-katalog koşusu kataloğun bir
        # bölümünü HİÇ görmüyor, üstelik hata da vermiyordu. Ayrıca göreli
        # "projects" yanlış cwd'de os.path.isdir'den False alıp "klasör yok"
        # diyordu; uyumluluk.KOKLER MUTLAK, yani cwd'den bağımsız.
        project_dirs = list(uyumluluk.proje_klasorleri())
        if not project_dirs:
            print("HATA: hiçbir içerik kökünde (%s) proje klasörü yok."
                  % ", ".join(uyumluluk.KOK_ADLARI))
            sys.exit(1)

    all_ok = True
    for project_dir in project_dirs:
        if not render_project(project_dir):
            all_ok = False

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
