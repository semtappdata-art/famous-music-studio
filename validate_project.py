"""Render'dan ÖNCE bir projenin tüm girdilerini doğrulayan sağlık kontrolleri.

Amaç: saatler süren bir render+upload sürecinin sonunda bozuk bir video ya da
eksik bir kapakla karşılaşmak yerine, bu sınıf hataları render BAŞLAMADAN
yakalamak — bugüne kadar bu projede tekrar tekrar düşülen hatalar (art.jpg'nin
yanlışlıkla metin içermesi, bozuk/okunamayan ses dosyası, geçersiz meta.json)
buradan otomatik tespit ediliyor. render.py her proje için render'dan önce
bunu otomatik çağırır — elle çalıştırmaya gerek yok, ama tek başına da
kullanılabilir:

    python validate_project.py --project "projects/sarki-adi"
    python validate_project.py --all

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
        capture_output=True, text=True,
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
        capture_output=True, text=True,
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
    #    Kalbim Oynuyor ve ilk otomasyon/Küllerimden Geç'te birkaç kez düşülen hata)
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
    group.add_argument("--all", action="store_true", help="projects/ altındaki tüm klasörleri kontrol et")
    args = parser.parse_args()

    if args.project:
        project_dirs = [args.project]
    else:
        base = "projects"
        project_dirs = [
            os.path.join(base, name)
            for name in sorted(os.listdir(base))
            if os.path.isdir(os.path.join(base, name))
        ] if os.path.isdir(base) else []

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
