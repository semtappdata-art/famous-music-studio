"""Görsel dil ÖNİZLEME sürücüsü (prototip) — yalnızca göstermek içindir, boru hattına bağlı değildir.

"Görsel dil" (gorsel_dil.kapak_uret + huzmeli backdrop + nabız + doku + derecelendirme)
ile tek bir şarkıda (varsayılan: Bu Gece Kazandık) kapak ve kısa video önizlemeleri üretir.

Bu NORMAL BİR MODÜLDÜR — auto_process'e bağlı DEĞİL, zamanlayıcı görevi YOK. Var olma
sebebi yalnızca kullanıcının YENİ görsel dili görmesi; kataloğa ya da boru hattına
dokunmaz. Kullanıcı onayından ÖNCE başka hiçbir kod bunu çağırmaz.

Kullanım:
    python gorsel_prototip.py [--proje "Bu Gece Kazandık"] [--cikti C:\\...\\onizleme] \
        [--baslangic 60] [--uzunluk 8]
"""

import argparse
import json
import os
import subprocess
import sys

import config
import ffmpeg_utils
import gorsel_dil as gd

KOK = os.path.dirname(os.path.abspath(__file__))
VARSAYILAN_CIKTI = os.path.join(os.environ.get("TEMP", KOK), "opencode", "gorsel_dil_onizleme")

# (etiket, genişlik, yükseklik) — 16:9 uzun format, 9:16 Shorts/TikTok/Reels
BOYUTLAR = [("16x9", 1920, 1080), ("9x16", 1080, 1920)]


def _cikti_utf8() -> None:
    """Konsol çıktısını UTF-8'e çeker (tiktok_publish_plan ile aynı desen).

    Windows'ta sys.stdout.encoding ANSI kod sayfası (cp1254) oluyor ve rapor
    satırlarındaki →/⏱ gibi karakterler UnicodeEncodeError ile çökertiyordu.
    İki adım: konsol kod sayfası 65001 + akışlar UTF-8. Hata TÜKENDİRMEZ."""
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        except Exception:                                    # noqa: BLE001
            pass
    for akis in (sys.stdout, sys.stderr):
        try:
            akis.reconfigure(encoding="utf-8", errors="replace")
        except Exception:                                    # noqa: BLE001
            pass


def _ornek_kareler_mean_parlaklik(video: str, sure: float) -> list[float]:
    """Videodan sabit ~8fps örnekleyip her karenin ortalama parlaklığını (0-255) döndürür.

    Nabız dönemi 0.2-1.2 sn aralığında olduğundan, toplam kare sayısına bağlı
    örnekleme (örn. 8sn'de 16 kare = her 0.5 sn) nabız tepelerini kaçırabilir
    (aliasing). 8fps, en hızlı nabızda bile dönem başına ~1 kare → 0.7 kare/sn
    dönemi için 5-6 örnek verir — tepe/çukur ikisi de yakalanır."""
    fps = 8
    cmd = [
        "ffmpeg", "-v", "error", "-i", video,
        "-vf", f"fps={fps},scale=160:-2,format=gray",
        "-f", "rawvideo", "-pix_fmt", "gray", "-",
    ]
    r = subprocess.run(cmd, capture_output=True, timeout=120)
    if r.returncode != 0 or not r.stdout:
        return []
    w = 160
    h = len(r.stdout) // (max(1, int(sure * fps)) * w) if sure else 1
    if h < 1:
        h = 1
    kare_bayt = w * h
    sonuc = []
    for i in range(len(r.stdout) // kare_bayt):
        dilim = r.stdout[i * kare_bayt:(i + 1) * kare_bayt]
        if dilim:
            sonuc.append(sum(dilim) / len(dilim))
    return sonuc


def _proje_parametreleri(proje_dir: str, meta: dict) -> dict:
    """Şarkıdan türetilen tüm görsel dil parametrelerini hesaplar (rapor için)."""
    title = meta.get("title") or os.path.basename(proje_dir)
    theme = meta.get("theme") or config.DEFAULT_THEME
    art = os.path.join(proje_dir, "art.jpg")
    audio = next(
        (os.path.join(proje_dir, f) for f in ("audio.wav", "audio.mp3")
         if os.path.isfile(os.path.join(proje_dir, f))),
        None,
    )
    if not art or not os.path.isfile(art):
        print(f"UYARI: art.jpg yok — {proje_dir} (fallback vignette kullanılır).")
        art = None
    if not audio or not os.path.isfile(audio):
        print(f"HATA: audio.wav/mp3 yok — {proje_dir}")
        sys.exit(1)

    bpm, sure = gd.measure_bpm(audio)
    sinif = gd.enerji_sinifi(bpm)
    nabiz_expr, hz, flash = gd.nabiz_ifadesi(bpm)
    seed = gd._song_hash(title)
    grain = gd.doku_filtresi(seed ^ 0xA55A)
    mood = gd.mood_olc(title)
    accent = tuple(config.THEMES[theme]["accent"])
    dominant = gd.hakim_renk(art) if art else accent
    grade = gd.derecelendirme_filtresi(mood, accent)
    duzen = gd.kapak_duzeni_sec(title)

    return {
        "title": title, "theme": theme, "art": art, "audio": audio,
        "bpm": bpm, "sure": sure, "sinif": sinif,
        "nabiz_expr": nabiz_expr, "nabiz_hz": hz, "flash_per_sn": flash,
        "seed": seed, "grain": grain, "mood": mood, "accent": accent,
        "dominant": dominant, "grade": grade, "kapak_duzeni": duzen,
    }


def _rapor(p: dict) -> None:
    onay = "GÜVENLİ" if p["flash_per_sn"] < 3 else "RİSKLİ!"
    print("  Parametre raporu (şarkıdan türetilen):")
    print(f"    BPM............ {p['bpm']:.1f}  (süre {p['sure']:.0f} sn) → sınıf: {p['sinif']}")
    print(f"    Nabız.......... {p['nabiz_expr']}  ({p['nabiz_hz']:.2f} Hz)  flash {p['flash_per_sn']:.2f}/sn [{onay}]")
    print(f"    Doku (grain)... {p['grain']}")
    print(f"    Mood........... {p['mood']}  accent: {p['accent']}  dominant: {p['dominant']}")
    print(f"    Grade.......... {p['grade']}")
    print(f"    Kapak düzeni... {p['kapak_duzeni']}  (seed 0x{p['seed']:08x})")


def _huzmeli_backdrop(p: dict, w: int, h: int, out: str) -> str:
    print(f"  Huzmeli backdrop {w}x{h} üretiliyor...", end=" ", flush=True)
    yol = gd.huzmeli_backdrop_uret(p["art"], w, h, p["seed"], cache_dir=out)
    print(os.path.basename(yol))
    return yol


def _video_onizleme(p: dict, w: int, h: int, out: str, baslangic: float, uzunluk: float) -> str:
    yol = os.path.join(out, f"onizleme_{w}x{h}_{p['sinif']}.mp4")
    dil = dict(p)
    dil["backdrop"] = _huzmeli_backdrop(p, w, h, out)
    print(f"  Video {w}x{h} render ({uzunluk:.0f} sn, başlangıç {baslangic:.0f} sn)...", end=" ", flush=True)
    ffmpeg_utils.render_video(
        art_path=p["art"],
        audio_path=p["audio"],
        output_path=yol,
        width=w, height=h,
        title=p["title"], theme=p["theme"],
        start_time=baslangic, end_time=baslangic + uzunluk,
        dil_params=dil,
    )
    parlaklik = _ornek_kareler_mean_parlaklik(yol, uzunluk)
    print("OK")
    if parlaklik:
        print(f"      Parlaklık örneği: min {min(parlaklik):.0f} / max {max(parlaklik):.0f} "
              f"(nabız farkı ~{max(parlaklik) - min(parlaklik):.0f}/255, n={len(parlaklik)})")
    return yol


def _kapak_onizleme(p: dict, konsept: str, w: int, h: int, out: str) -> str:
    yol = os.path.join(out, f"kapak_{konsept}_{w}x{h}.png")
    print(f"  Kapak {konsept} {w}x{h}...", end=" ", flush=True)
    gd.kapak_uret(
        bg_path=p["art"], out_path=yol, title=p["title"],
        accent=p["accent"],
        out_w=w, out_h=h, konsept=konsept,
    )
    print("OK")
    return yol


def main() -> None:
    _cikti_utf8()
    ap = argparse.ArgumentParser(description="Görsel dil önizleme sürücüsü (prototip)")
    ap.add_argument("--proje", default="Bu Gece Kazandık")
    ap.add_argument("--cikti", default=None)
    ap.add_argument("--baslangic", type=float, default=60.0)
    ap.add_argument("--uzunluk", type=float, default=8.0)
    a = ap.parse_args()

    proje_dir = os.path.join(KOK, "projects", a.proje)
    if not os.path.isdir(proje_dir):
        print(f"HATA: {proje_dir} yok")
        sys.exit(1)
    meta = {}
    mp = os.path.join(proje_dir, "meta.json")
    if os.path.isfile(mp):
        meta = json.load(open(mp, encoding="utf-8"))
    out = a.cikti or VARSAYILAN_CIKTI
    os.makedirs(out, exist_ok=True)

    print(f"Görsel dil prototipi — {a.proje}")
    print("=" * 64)
    p = _proje_parametreleri(proje_dir, meta)
    _rapor(p)

    print("\nKapak önizlemeleri (3 konsept × 2 oran):")
    for _konsept in ("threshold", "split", "negatif"):
        for _ad, _w, _h in BOYUTLAR:
            _kapak_onizleme(p, _konsept, _w, _h, out)

    print("\nVideo önizlemeleri (nabız + doku + derecelendirme, huzmeli backdrop):")
    for _ad, _w, _h in BOYUTLAR:
        _video_onizleme(p, _w, _h, out, a.baslangic, a.uzunluk)

    print("\nÇıktılar:", out)
    print("Kullanıcıya göster — onaylamadan boru hattına (auto_process/generate_cover) bağlama.")


if __name__ == "__main__":
    main()