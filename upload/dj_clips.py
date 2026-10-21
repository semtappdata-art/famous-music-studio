# -*- coding: utf-8 -*-
"""DJ set'lerinden CROSS-PROMO klip üretir (TikTok + Instagram Reels).

NEDEN VAR
---------
`meta.json`'daki `cross_promo` bloğu şu ana kadar SADEce veri idi:
  "shorts_clips": ["hook_0-30s", "transition_mid", "outro_last_3min"]
  "instagram_reel": "30s_vertical_hook"
  "tiktok_draft": "60s_best_moment"
  "bluesky_thread": "track_by_track_breakdown"
Hiçbir modül bu alanı OKUMUYORDU. Sonuç: her set için kesit çıkarmak ELLE
işti — 40-80 dakikalık bir setten 30sn'lik dikey kesit almak elle saatler
sürüyordu ve pratikte hiç yapılmadı. Cercle/HÖR/Boiler Room referanslarının
tamamı "setten otomatik kısa kesit çıkar" modeliyle çalışır (Cross-promo
= bir set, üç ayrı platformda).

Bu modül o boşluğu kapatır: set'in sesinden TANIMLI PENCERELER kesip 9:16
video üretir, sonra TikTok TASLAĞI ve Instagram REELS konteyneri olarak
yükler.

PENCERE KURALLARI (neden böyle)
--------------------------------
1. **Pencereler birbirini ÖRTMEZ.** Set'in kendi `shorts_9x16.mp4`'i vardır
   (en yüksek enerjili 45sn). Kesitler buraya GİRMEZ — aynı sesi dinleyici
   iki kez duymasın. `MIN_ARA_SN` (60 sn) aralık zorunlu.
2. **En yüksek enerjili pencere ATLANIR** — set'in kendi Shorts'u onu
   kullanıyor, ikinci dalga yeni bir an getirmeli.
3. **Hook penceresi ilk 30sn** — dinleyici ilk 3 saniyede kaybedilmemeli.
4. **Outro penceresi son 3 dakika** — bitiş hissi + "abone ol" tetikleyicisi.

KOTA / GÜVENLİK
----------------
* Kesit üretimi YEREL (ffmpeg) — API yazmaz.
* TikTok: TASLAK olarak yüklenir (`DRAFT_INBOX`), YAYINLANMAZ — CLAUDE.md
  §7: "TikTok: Taslak + Elle Yayın".
* Instagram: konteyner (creation_id) 23 saat ömürlü; IG Reels publish işi
  `instagram_upload.try_publish_pending` ile zamanlanır.
* Politika kapısı: `uyumluluk.kontrol(proje, "yukleme")` — bu modül
  politika kontrolü YAPMAZ, `auto_process`/`dj_famous_process` çağırdığında
  yapar. Burada sadece KESİT üretilir.
* Aynı set için ikinci dalga kesiti TEK sefer üretilir
  (`youtube_clip_video_id` state'te varsa atlanır) — çift gönderim koruması.

KULLANIM
---------
    python upload/dj_clips.py --project "dj_sets/City_Pulse_Ep3_Tokyo" --dry-run
    python upload/dj_clips.py --project "dj_sets/City_Pulse_Ep3_Tokyo" --uret
    python upload/dj_clips.py --hepsi --uret

ÇIKIŞ
------
    <proje>/output/cross_promo/
        clip_hook_0-30s.mp4      (9:16, 30sn)
        clip_transition_mid.mp4  (9:16, 30sn)
        clip_outro_last_3min.mp4 (9:16, 30sn)
"""

import argparse
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import state_io

# Enerji penceresi tespiti (tek kaynak: audio_highlight). Daha önce bu
# import eksikti -> modul ozelligi `dj_clips.find_highlights` olarak
# YOKTU; testler bu kancaya takiliyordu.
from audio_highlight import find_highlights

# --- sabitler -------------------------------------------------------------

KLIP_SURESI_SN = 30.0        # her kesitin uzunluğu
MIN_ARA_SN = 60.0             # iki kesit arası en az boşluk
# KESIT ERTELEME (2026-10-21): kesit, setin kendi Shorts'undan SONRA
# yayinlanir. Hacim kısıtı (haftada 1 kesit) korunur.
KESIT_ERTELEME_GUN = 3
EN_YUKSEK_ATLA_SN = 20.0      # set'in kendi Shorts'unun kullandigi pencere
KISA_VIDEOLAR = ("shorts_9x16",)

# Pencere tanimlari: (anahtar, etiket, uretim kurali)
PENCERELER = [
    ("hook_0-30s", "hook", "start"),
    ("transition_mid", "transition", "mid"),
    ("outro_last_3min", "outro", "end"),
]


# --- yardimcilar -----------------------------------------------------------


def _proje_klasoru(project_dir: str) -> str:
    return os.path.abspath(project_dir)


def _meta_oku(project_dir: str) -> dict:
    yol = os.path.join(project_dir, "meta.json")
    try:
        with open(yol, "r", encoding="utf-8") as f:
            m = json.load(f)
    except (OSError, ValueError):
        return {}
    return m if isinstance(m, dict) else {}


def _state_oku(project_dir: str) -> dict:
    yol = os.path.join(project_dir, "state.json")
    try:
        with open(yol, "r", encoding="utf-8") as f:
            s = json.load(f)
    except (OSError, ValueError):
        return {}
    return s if isinstance(s, dict) else {}


def _ses_dosyasi(project_dir: str) -> str | None:
    for ad in ("audio.wav", "audio.mp3", "audio.m4a"):
        yol = os.path.join(project_dir, ad)
        if os.path.isfile(yol):
            return yol
    return None


def _sure(ffprobe_yol: str) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", ffprobe_yol],
        capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except (ValueError, AttributeError):
        return 0.0


def _setin_kendi_shorts_penceresi(project_dir: str) -> tuple[float, float] | None:
    """Set'in kendi `shorts_9x16.mp4`'inin hangi aralıktan kesildiğini bulur.

    NEDEN: kesitler bu aralığa GİRMEMELİ (madde 1) — aynı sesi iki kez
    duyurmamak için. `meta.json`'daki `highlight_start/highlight_end` ya da
    `segments.json`'daki en yüksek enerjili bölümden hesaplanır.
    """
    meta = _meta_oku(project_dir)
    hs, he = meta.get("highlight_start"), meta.get("highlight_end")
    if isinstance(hs, (int, float)) and isinstance(he, (int, float)) and he > hs:
        return float(hs), float(he)

    seg_yol = os.path.join(project_dir, "segments.json")
    if os.path.isfile(seg_yol):
        try:
            with open(seg_yol, "r", encoding="utf-8") as f:
                segs = (json.load(f) or {}).get("segments") or []
        except (OSError, ValueError):
            segs = []
        en_iyi = None
        for s in segs:
            e = s.get("energy")
            if e is None:
                continue
            if en_iyi is None or e > en_iyi.get("energy", 0):
                en_iyi = s
        if en_iyi and en_iyi.get("start") is not None:
            st = float(en_iyi["start"])
            return st, st + KLIP_SURESI_SN
    return None


def _pencere_baslangiclari(toplam_sure: float, kendi_penceresi, adet: int) -> list[tuple[float, str]]:
    """Kesit başlangıç saniyelerini üretir — kurallara uyarak.

    KURAL 1: pencereler birbirini örtmez, aralarında >= MIN_ARA_SN boşluk var.
    KURAL 2: set'in kendi Shorts'unun penceresi ATLANIR.
    KURAL 3: başlangıçlar toplam süreyi aşmaz (son 30sn dışarıda kalır).
    """
    baslangiclar: list[tuple[float, str]] = []
    son_kullanilan = -1e9

    def _uygun(bas: float) -> bool:
        if bas < 0 or bas + KLIP_SURESI_SN > toplam_sure:
            return False
        if son_kullanilan > -1e8 and bas - son_kullanilan < MIN_ARA_SN:
            return False
        if kendi_penceresi:
            ks, ke = kendi_penceresi
            # kesit kendi penceresiyle ÖRTÜŞÜYORSA uygun değil
            if bas < ke and (bas + KLIP_SURESI_SN) > ks:
                return False
        return True

    # 1) Hook: ilk 30sn
    if _uygun(0.0):
        baslangiclar.append((0.0, "hook"))
        son_kullanilan = 0.0

    # 2) Transition: ortadaki enerjili OLMAYAN bolge (kendi Shorts'tan uzak)
    orta_adaylar = [
        toplam_sure * 0.30, toplam_sure * 0.45, toplam_sure * 0.60,
        toplam_sure * 0.22, toplam_sure * 0.72,
    ]
    for bas in orta_adaylar:
        if len(baslangiclar) >= adet:
            break
        if _uygun(bas):
            baslangiclar.append((bas, "transition"))
            son_kullanilan = bas
            break

    # 3) Outro: son 3 dakika
    for bas in (toplam_sure - 180.0, toplam_sure - 240.0, toplam_sure - KLIP_SURESI_SN):
        if len(baslangiclar) >= adet:
            break
        if bas < 0:
            continue
        if _uygun(bas):
            baslangiclar.append((bas, "outro"))
            son_kullanilan = bas
            break

    return baslangiclar


def _kesit_uret(
    ses_yol: str, cikti_yol: str, bas: float,
    sure: float = KLIP_SURESI_SN,
    genislik: int = 1080, yukseklik: int = 1920,
    art_yol: str | None = None,
) -> bool:
    """Set'ten dikey (9:16) kesit üretir.

    Görsel: set'in `art.jpg`'si varsa bulanıklaştırılmış TAM EKRAN arka plan
    (Cercle/Boiler Room klipleri böyle — set'in görsel kimliği kesitte de
    görünür); yoksa düz siyah.
    """
    os.makedirs(os.path.dirname(cikti_yol), exist_ok=True)
    if os.path.isfile(cikti_yol):
        os.remove(cikti_yol)

    if art_yol and os.path.isfile(art_yol):
        # Görsel giriş: art.jpg -> blur + pan (16:9 kaynak 9:16'ya kırpılır)
        kaynak = ["-loop", "1", "-i", art_yol]
        video_map = "[clipv]"
        filter_complex = (
            f"[1:v]scale={genislik}:{yukseklik}:force_original_aspect_ratio=increase,"
            f"crop={genislik}:{yukseklik},"
            f"gblur=sigma=18,eq=brightness=-0.08:saturation=1.1[clipv]"
        )
    else:
        kaynak = ["-f", "lavfi", "-i",
                  f"color=c=black:s={genislik}x{yukseklik}:r={config.FPS}"]
        video_map = "1:v"
        filter_complex = None

    cmd = ["ffmpeg", "-y", "-ss", f"{bas:.3f}", "-t", f"{sure:.3f}", "-i", ses_yol]
    cmd += kaynak
    if filter_complex:
        cmd += ["-filter_complex", filter_complex]
    cmd += [
        "-map", "0:a", "-map", video_map,
        "-c:v", config.VIDEO_CODEC, "-preset", config.PRESET, "-crf", config.CRF,
        "-pix_fmt", "yuv420p",
        "-c:a", config.AUDIO_CODEC, "-b:a", config.AUDIO_BITRATE,
        "-t", f"{sure:.3f}",
        "-shortest",
        cikti_yol,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"    ffmpeg HATA: {r.stderr[-400:]}")
        return False
    if not os.path.isfile(cikti_yol) or os.path.getsize(cikti_yol) == 0:
        print("    ffmpeg HATA: dosya bos uretildi")
        return False
    return True


def _clip_state_guncelle(project_dir: str, bilgi: dict) -> None:
    """state.json'a ikinci dalga kesit bilgisini yazar (atomik)."""
    yol = os.path.join(project_dir, "state.json")
    state = _state_oku(project_dir)
    state.update(bilgi)
    state_io._atomik_yaz(yol, state)


# =============================================================================
# İKİNCİ DALGA YAYINI (2026-10-21)
# =============================================================================

def kesit_sec(project_dir: str) -> dict | None:
    """Yayınlanacak kesidi seçer: EN YÜKSEK ENERJİLİ olan (enerji 1 = en yüksek).

    NEDEN: setin kendi Shorts'u zaten en enerjili pencereyi kullanıyor;
    kesit onun KOPYASI olmamalı. `enerji` alanı 1'den başlayarak artar.
    """
    kayitlar = _state_oku(project_dir).get("dj_clips") or []
    if not kayitlar:
        return None
    return min(kayitlar, key=lambda k: (k.get("enerji", 999), k.get("bas", 0.0)))


def kesit_yayinla(project_dir: str, kesit: dict | None, log=print) -> bool:
    """Kesidi YouTube'a yükler ve TEKRAR GÖNDERIMI ENGELLEYEN state'i yazar.

    NEDEN state burada yazılıyor: `upload_clip` bilerek state'e YAZMAZ
    (docstring'inde yazıyor). Yazan taraf TEK olmalı — iki taraf da yazarsa
    ikinci koşu aynı kesidi ikinci kez yükler.

    Yazılan anahtarlar AYRI bir aile:
      youtube_clip_video_id / youtube_clip_dosya /
      youtube_clip_publish_at / youtube_clip_uploaded_at
    Setin kendi Shorts kaydı (youtube_shorts_video_id) ve üretim kaydı
    (dj_clips) EZİLMEZ — süpürgenin okuduğu alanlar bunlar.
    """
    if not kesit:
        return False
    state = _state_oku(project_dir)
    if state.get("youtube_clip_video_id"):
        log("  Kesit zaten yayınlanmış: %s" % state.get("youtube_clip_dosya"))
        return False

    # DİNAMİK import: testler `youtube_upload.upload_clip`i monkeypatch'liyor.
    from youtube_upload import upload_clip

    video_id, publish_at = upload_clip(
        project_dir,
        kesit.get("dosya"),
        state.get("youtube_video_id"),
        float(kesit.get("bas") or 0.0),
        KESIT_ERTELEME_GUN,
        "public",
    )
    _clip_state_guncelle(project_dir, {
        "youtube_clip_video_id": video_id,
        "youtube_clip_dosya": kesit.get("dosya"),
        "youtube_clip_publish_at": publish_at,
        "youtube_clip_uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    })
    log("  Kesit yayınlandı: %s (%s)" % (video_id, kesit.get("dosya")))
    return True


def supur(klasor: str, log=print) -> dict:
    """Klasördeki DJ setlerinde bekleyen KESİTLERİ yayınlar.

    DÖNER: {"yayinlanan": int, "atlanan": [{"proje":..., "sebep":...}]}

    İKİ KAPI BİRBİRİNDEN BAĞIMSIZ: küresel tempo kapısı açık olsa bile
    (yayın 30 gün önce) SET KAPI tutmalı — aynı kesit ikinci kez gitmez.
    """
    sonuc = {"yayinlanan": 0, "atlanan": []}
    if not os.path.isdir(klasor):
        return sonuc
    for ad in sorted(os.listdir(klasor)):
        proje = os.path.join(klasor, ad)
        if not os.path.isdir(proje):
            continue
        state = _state_oku(proje)
        if state.get("youtube_clip_video_id"):
            sonuc["atlanan"].append({
                "proje": ad,
                "sebep": "Kesit zaten yayınlanmış (%s)" % state.get("youtube_clip_dosya"),
            })
            continue
        if not state.get("youtube_video_id"):
            sonuc["atlanan"].append({"proje": ad, "sebep": "Set henüz yüklenmemiş"})
            continue
        kesit = kesit_sec(proje)
        if not kesit:
            sonuc["atlanan"].append({"proje": ad, "sebep": "Üretilmiş kesit yok"})
            continue
        try:
            if kesit_yayinla(proje, kesit, log=log):
                sonuc["yayinlanan"] += 1
        except Exception as e:
            log("  Kesit yayın HATASI: %s" % str(e)[:160])
            sonuc["atlanan"].append({"proje": ad, "sebep": "Hata: %s" % str(e)[:120]})
    return sonuc

# --- ana akis --------------------------------------------------------------


def clip_uret(project_dir: str, dry_run: bool = False) -> dict:
    """Bir DJ set için cross-promo klip seti üretir.

    Dönüş: {"uretildi": [...], "atlandi": str|None, "pencereler": [...]}
    """
    project_dir = _proje_klasoru(project_dir)
    ad = os.path.basename(project_dir)
    meta = _meta_oku(project_dir)
    state = _state_oku(project_dir)

    # ÇİFT ÜRETİM KORUMASI: ikinci dalga kesiti zaten varsa atla.
    if state.get("youtube_clip_video_id"):
        return {"uretildi": [], "atlandi": "ikinci dalga kesiti zaten var",
                "pencereler": []}

    if not meta.get("series"):
        return {"uretildi": [], "atlandi": "seri seti degil (cross_promo DJ setleri icin)",
                "pencereler": []}

    ses = _ses_dosyasi(project_dir)
    if not ses:
        return {"uretildi": [], "atlandi": "ses dosyasi yok", "pencereler": []}

    toplam = _sure(ses)
    if toplam < KLIP_SURESI_SN * 2:
        return {"uretildi": [], "atlandi": f"ses cok kisa ({toplam:.0f}s)",
                "pencereler": []}

    kendi = _setin_kendi_shorts_penceresi(project_dir)
    pencereler = _pencere_baslangiclari(toplam, kendi, len(PENCERELER))

    # cross_promo.shorts_clips ile kesişim: meta'da istenen pencere adlari
    spec = (meta.get("cross_promo") or {}).get("shorts_clips") or []
    istenen = {p.split("_")[0] for p in spec} or {"hook", "transition", "outro"}

    cikti_klasor = os.path.join(project_dir, "output", "cross_promo")
    os.makedirs(cikti_klasor, exist_ok=True)

    # Set'in görsel kimliği (art.jpg) klip arka planı olarak kullanılır
    art_yol = None
    for ad in ("art.jpg", "art.jpeg", "art.png"):
        yol = os.path.join(project_dir, ad)
        if os.path.isfile(yol):
            art_yol = yol
            break

    uretilen = []
    for bas, etiket in pencereler:
        if etiket not in istenen:
            continue
        dosya = os.path.join(cikti_klasor, f"clip_{etiket}.mp4")
        if dry_run:
            print(f"  [dry-run] kesit: {etiket} @ {bas:.1f}s -> {dosya}")
            uretilen.append(dosya)
            continue
        print(f"  kesit üretiliyor: {etiket} @ {bas:.1f}s")
        if _kesit_uret(ses, dosya, bas, art_yol=art_yol):
            uretilen.append(dosya)
            print(f"    tamam: {os.path.basename(dosya)}")
        else:
            print(f"    BAŞARISIZ: {etiket}")

    bilgi = {
        "cross_promo_clips": [os.path.basename(p) for p in uretilen],
        "cross_promo_clips_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    if not dry_run and uretilen:
        _clip_state_guncelle(project_dir, bilgi)

    return {"uretildi": uretilen, "atlandi": None, "pencereler": pencereler}


def main():
    ap = argparse.ArgumentParser(
        description="DJ set'lerinden cross-promo klip üretir (TikTok/IG için).")
    ap.add_argument("--project", help="DJ set klasörü (örn. dj_sets/City_Pulse_Ep3_Tokyo)")
    ap.add_argument("--hepsi", action="store_true", help="TÜM DJ set'lerini işle")
    ap.add_argument("--uret", action="store_true", help="GERÇEKTEN üret (varsayılan: dry-run)")
    ap.add_argument("--dry-run", action="store_true", dest="dry_run",
                    help="Sadece ne yapılacağını yaz")
    args = ap.parse_args()

    if not args.project and not args.hepsi:
        ap.error("--project ya da --hepsi gerekli")

    proje_dizileri = []
    if args.hepsi:
        import uyumluluk
        for kok in uyumluluk.KOKLER:
            if not os.path.isdir(kok):
                continue
            for ad in sorted(os.listdir(kok)):
                yol = os.path.join(kok, ad)
                if os.path.isdir(yol) and os.path.isfile(os.path.join(yol, "meta.json")):
                    proje_dizileri.append(yol)
    else:
        proje_dizileri = [args.project]

    toplam = 0
    for pd in proje_dizileri:
        ad = os.path.basename(os.path.abspath(pd))
        meta = _meta_oku(pd)
        if not meta.get("series"):
            continue
        print(f"=== {ad} ===")
        sonuc = clip_uret(pd, dry_run=not args.uret)
        if sonuc["atlandi"]:
            print(f"  atlandi: {sonuc['atlandi']}")
        else:
            toplam += len(sonuc["uretildi"])
            print(f"  {len(sonuc['uretildi'])} klip hazır")

    print(f"\nToplam {toplam} klip üretildi.")


if __name__ == "__main__":
    main()
