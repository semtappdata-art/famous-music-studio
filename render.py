"""Suno ses dosyalarından tüm platformlar için video üreten ana script.

Kullanım:
    python render.py --project projects/sarki-adi
    python render.py --all
"""

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import config
import ffmpeg_utils
import uyumluluk
import validate_project
from audio_highlight import find_highlight

COVER_NAMES = ["cover.jpg", "cover.jpeg", "cover.png"]
COVER_VERTICAL_NAMES = ["cover_vertical.jpg", "cover_vertical.jpeg", "cover_vertical.png"]
ART_NAMES = ["art.jpg", "art.jpeg", "art.png"]
AUDIO_NAMES = ["audio.wav", "audio.mp3", "audio.m4a"]

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

    highlight_start = meta.get("highlight_start")
    highlight_end = meta.get("highlight_end")
    if (highlight_start is None) != (highlight_end is None):
        print(
            "  UYARI: meta.json'da highlight_start/highlight_end alanlarından sadece biri "
            "belirtilmiş, ikisi de gerekli — göz ardı edilip otomatik tespite geçiliyor."
        )
        highlight_start = highlight_end = None
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
            ffmpeg_utils.render_video(
                art_path, audio_path, tmp_path, width, height, title, theme,
                marquee_override=marquee_override,
                start_time=highlight_start if use_highlight else None,
                end_time=highlight_end if use_highlight else None,
                backdrop_video=None if use_highlight else backdrop_path,
                hud_path=None if use_highlight else _hud(width, height),
                # Sahne modu sadece uzun formatta: 45 saniyelik dikey
                # kesitte kart hâlâ doğru iş - kapak kimliğini o taşıyor.
                kart_goster=not (config.DJ_SAHNE_MODU and backdrop_path
                                 and not use_highlight),
                intro_cover=intro_cover,
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
