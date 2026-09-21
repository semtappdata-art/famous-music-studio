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
import subprocess
import sys

import config

AUDIO_NAMES = ["audio.wav", "audio.mp3", "audio.m4a"]
COVER_NAMES = ["cover.jpg", "cover.jpeg", "cover.png"]
ART_NAMES = ["art.jpg", "art.jpeg", "art.png"]


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
                from generate_cover import find_character_image
                if not find_character_image(character):
                    warnings.append(
                        f"meta.json'daki character={character!r} için characters/ klasöründe "
                        "portre bulunamadı — procedural gradyana düşülecek (render durmaz)."
                    )
            except ImportError:
                pass
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

    return errors, warnings


def print_report(project_dir: str, errors: list[str], warnings: list[str]) -> None:
    name = os.path.basename(os.path.normpath(project_dir))
    for e in errors:
        print(f"  [{name}] HATA: {e}")
    for w in warnings:
        print(f"  [{name}] UYARI: {w}")


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
