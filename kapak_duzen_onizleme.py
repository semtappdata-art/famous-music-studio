# -*- coding: utf-8 -*-
"""Kapak DÜZEN adayları önizlemesi + KAPALI mesafe kapısı (özgünlük planı §2a, Aşama 1 iş 5).

NEDEN VAR: 20 şarkı kapağının 19'u birebir aynı düzende (ortalı üst başlık + ortada logo,
`generate_cover._add_title_text`). Tam görüntü pHash'i bu tekrarı GÖREMİYOR; tekrar
fotoğrafta değil ŞABLONDA. Kullanıcı kararı (2026-09-13): 3 düzenlik rotasyon — ama önce
ÖNİZLEME, onaydan sonra kod. Kullanıcı daha önce bir düzen değişikliğini reddetti
(`_compose_cover_rich`), bu yüzden bu modül:

  * `generate_cover.py`'yi DEĞİŞTİRMEZ, yalnız yardımcılarını (ölçümlü sığdırma, logo
    katmanları) içe aktarır;
  * YAYIN KODUNA BAĞLI DEĞİLDİR: hiçbir zamanlayıcı görevi çağırmaz, state/meta yazmaz,
    çıktı yalnız `--cikti` klasörüne gider (varsayılan Masaüstü scratch klasörü);
  * mesafe kapısı `MESAFE_KAPISI_AKTIF = False` ile KAPALI gelir. Aşama 2'de (onaylanan
    düzenler `generate_cover`'a girince) bayrak `config.py`'ye taşınacak ve kapı yeni
    kapak üretiminin son adımı olacak; o zamana kadar yalnız hesap fonksiyonları kullanılır.

Kullanım:
    python kapak_duzen_onizleme.py [--cikti <klasör>] [--projeler "projects/Sabah Senin" ...]

Sabit kalanlar (bugünkü düzenden): punto tavanı kısa kenar x 0,14, ölçümlü sığdırma,
en fazla 2 satır, logonun koyu hâlesi, metinsiz `art.*` kaynağı. EKLENMEYENLER: ayraç,
alt şerit, büyük logo bloğu (`YASAK_OGELER`).
"""

import argparse
import math
import os
import re
import shutil
import subprocess
import sys

import config
import generate_cover as gc

_KOK = os.path.dirname(os.path.abspath(__file__))
VARSAYILAN_CIKTI = os.path.join(os.path.expanduser("~"), "Desktop",
                                "kapak_duzen_onizleme_2026-09-13")
VARSAYILAN_PROJELER = ("Sabah Senin", "Yükseliş", "Kırık Zincir")
# Fotoğrafsız (prosedürel `art.png`) bir örnek yerine sırayla denenecek fotoğraflı şarkılar.
YEDEK_PROJELER = ("Yeraltı", "Sessiz Mektup", "Son Kez")

# --------------------------------------------------------------------------
# Mesafe kapısı (KAPALI)
# --------------------------------------------------------------------------
# Aşama 2'de config.py'ye taşınacak (config.KAPAK_MESAFE_KAPISI_AKTIF). Bugün bu modül
# hiçbir yayın yolunda çağrılmıyor; bayrak yalnız tasarımı ve testlerini sabitliyor.
MESAFE_KAPISI_AKTIF = False
PHASH_ESIGI = 14          # tüm geçmiş kapaklara karşı en küçük pHash mesafesi
DUZEN_PENCERESI = 3       # son N yayında aynı düzen kimliği yok
IOU_ESIGI = 0.6           # son N yayının bindirme kutusuna karşı IoU tavanı
BINDIRME_FARK_ESIGI = 45  # 160x90 ızgarada kapak - art farkı; üstü bindirme pikseli
BINDIRME_IZGARA = (160, 90)

YASAK_OGELER = ("ayrac", "alt_serit", "buyuk_logo")

# --------------------------------------------------------------------------
# Düzen tanımları (veri)
# --------------------------------------------------------------------------
# logo_oran 0.18: bugünkü 0.26'dan küçük (köşe amblemi), 0.14-0.15 feed boyutunda
# (~246 px) okunmuyordu — önizlemede görüldü. Başlıkta ince koyu kontur: açık zeminde
# (gökyüzü, güneş parlaması) yalnız gölge yetmedi.
# baslik_capa: sol_alt | alt_bant | sol_orta  ·  font: normal | kalin
# logo_kose: sag_ust | sag_alt | sol_ust     ·  kirpma_odak: orta | ust_ucte_bir
DUZENLER = {
    "D2": {"kimlik": "D2", "ad": "alt-sol sade",
           "baslik_capa": "sol_alt", "font": "normal", "maks_satir": 2,
           "punto_tavan_orani": 0.14, "genislik_orani": 0.80, "hizalama": "L",
           "logo_kose": "sag_ust", "logo_oran": 0.18,
           "kirpma_odak": "orta", "renk_derecelendirme": True, "dekor": ()},
    "D3": {"kimlik": "D3", "ad": "alt bant",
           "baslik_capa": "alt_bant", "font": "normal", "maks_satir": 2,
           "punto_tavan_orani": 0.14, "genislik_orani": 0.72, "hizalama": "C",
           "logo_kose": "sag_alt", "logo_oran": 0.18,
           "kirpma_odak": "ust_ucte_bir", "renk_derecelendirme": True, "dekor": ()},
    "D4": {"kimlik": "D4", "ad": "tipografik",
           "baslik_capa": "sol_orta", "font": "kalin", "maks_satir": 1,
           "punto_tavan_orani": 0.14, "genislik_orani": 0.86, "hizalama": "L",
           "logo_kose": "sol_ust", "logo_oran": 0.18,
           "kirpma_odak": "orta", "renk_derecelendirme": True, "dekor": ()},
}

# --------------------------------------------------------------------------
# Mood -> renk derecelendirmesi (cover-mood-variation'daki MOOD_COLOR_MODIFIERS fikri,
# prosedürel aksan rengi yerine FOTOĞRAF derecelendirmesine uyarlandı). Hafif değerler:
# fotoğrafı değiştirmek değil, feed'de karanlık-desatüre tekdüzeliği kırmak.
# --------------------------------------------------------------------------
MOOD_COLOR_MODIFIERS = {
    "melancholy": "eq=saturation=0.88:brightness=-0.01,colorbalance=bs=0.06:bm=0.04",
    "gritty": "eq=contrast=1.12:saturation=0.82",
    "dreamy": "eq=brightness=0.04:saturation=1.10,colorbalance=rh=0.04:bh=0.05",
    "warm": "colorbalance=rs=0.06:rm=0.05:bs=-0.05",
    "dark": "eq=brightness=-0.03:contrast=1.08",
    "energetic": "eq=saturation=1.25:contrast=1.08",
    "romantic": "colorbalance=rm=0.06:bm=0.03,eq=saturation=1.08",
    "calm": "eq=saturation=0.92,colorbalance=bm=0.04:gm=0.02",
    "cinematic": "colorbalance=bs=0.06:rh=0.05,eq=contrast=1.06",
    "nostalgic": "colorbalance=rs=0.04:gm=0.02:bh=-0.05,eq=saturation=0.85",
}
# Stil etiketindeki İngilizce sıfat -> mood. Metinde EN ERKEN geçen anahtar kazanır.
MOOD_ANAHTARLARI = {
    "melancholy": "melancholy", "melancholic": "melancholy", "ballad": "melancholy",
    "sad": "melancholy", "gritty": "gritty", "raw": "gritty", "dreamy": "dreamy",
    "ethereal": "dreamy", "warm": "warm", "dark": "dark", "moody": "dark",
    "powerful": "energetic", "energetic": "energetic", "anthemic": "energetic",
    "upbeat": "energetic", "romantic": "romantic", "tender": "romantic",
    "calm": "calm", "soft": "calm", "gentle": "calm", "cinematic": "cinematic",
    "nostalgic": "nostalgic", "retro": "nostalgic",
}


def mood_bul(stil_metni):
    """Stil etiketinden mood çıkarır; bulunamazsa None (TAHMİN ETMEZ — ef1792f kuralı)."""
    metin = (stil_metni or "").lower()
    en_iyi = None
    for kelime, mood in MOOD_ANAHTARLARI.items():
        m = re.search(r"\b%s\b" % re.escape(kelime), metin)
        if m and (en_iyi is None or m.start() < en_iyi[0]):
            en_iyi = (m.start(), mood)
    return en_iyi[1] if en_iyi else None


def stil_etiketi(baslik):
    """`*_sozler.md` içindeki stil etiketi kod bloğu ("Stil Etiketi" / "Style kutusu"); yoksa ""."""
    try:
        import stock_art
        yol = stock_art.find_lyrics_file(baslik)
    except Exception:                                        # noqa: BLE001
        yol = None
    if not yol or not os.path.isfile(yol):
        return ""
    with open(yol, encoding="utf-8") as f:
        satirlar = f.read().splitlines()
    for i, s in enumerate(satirlar):
        if re.search(r"(?i)stil etiketi|style kutusu", s):
            icerde, blok = False, []
            for t in satirlar[i + 1:i + 30]:
                if t.strip().startswith("```"):
                    if icerde:
                        return " ".join(blok).strip()
                    icerde = True
                    continue
                if icerde:
                    blok.append(t.strip())
    return ""


# --------------------------------------------------------------------------
# Görüntü ölçümleri (ffmpeg -> ham gri piksel, saf Python)
# --------------------------------------------------------------------------

def _gri_ham(yol, w, h, kirp=True):
    if kirp:
        vf = ("scale=%d:%d:force_original_aspect_ratio=increase:flags=area,crop=%d:%d,"
              "format=gray" % (w, h, w, h))
    else:
        vf = "scale=%d:%d:flags=area,format=gray" % (w, h)
    ham = subprocess.run(["ffmpeg", "-v", "error", "-i", yol, "-vf", vf, "-frames:v", "1",
                          "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                         capture_output=True, timeout=60).stdout
    if len(ham) < w * h:
        raise RuntimeError("görüntü çözülemedi: %s" % yol)
    return ham[:w * h]


_N = 32
_COS = [[math.cos((2 * x + 1) * u * math.pi / (2 * _N)) for x in range(_N)] for u in range(8)]


def phash(yol):
    """32x32 gri -> DCT -> sol üst 8x8 (DC hariç 63 katsayı) -> medyan eşiği -> 63 bit int."""
    p = _gri_ham(yol, _N, _N, kirp=False)
    satir = [[sum(p[y * _N + x] * _COS[u][x] for x in range(_N)) for y in range(_N)]
             for u in range(8)]
    katsayi = []
    for u in range(8):
        for v in range(8):
            if u == 0 and v == 0:
                continue
            katsayi.append(sum(satir[u][y] * _COS[v][y] for y in range(_N)))
    medyan = sorted(katsayi)[len(katsayi) // 2]
    deger = 0
    for c in katsayi:
        deger = (deger << 1) | (1 if c > medyan else 0)
    return deger


def hamming(a, b):
    return bin(int(a) ^ int(b)).count("1")


def bindirme_kutusu(kapak, art):
    """Kapak ile KENDİ art'ı aynı kırpımla 160x90'a indirilir; farkı eşiği aşan
    piksellerin kutusu (x0, y0, x1, y1), dahil. Fark yoksa None (plan §1.1)."""
    w, h = BINDIRME_IZGARA
    a, b = _gri_ham(kapak, w, h), _gri_ham(art, w, h)
    xs, ys = [], []
    for y in range(h):
        for x in range(w):
            i = y * w + x
            if abs(a[i] - b[i]) > BINDIRME_FARK_ESIGI:
                xs.append(x)
                ys.append(y)
    if not xs:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


def iou(k1, k2):
    if not k1 or not k2:
        return 0.0
    ix0, iy0 = max(k1[0], k2[0]), max(k1[1], k2[1])
    ix1, iy1 = min(k1[2], k2[2]), min(k1[3], k2[3])
    kesisim = max(0, ix1 - ix0 + 1) * max(0, iy1 - iy0 + 1)
    alan = lambda k: (k[2] - k[0] + 1) * (k[3] - k[1] + 1)   # noqa: E731
    birlesim = alan(k1) + alan(k2) - kesisim
    return kesisim / birlesim if birlesim > 0 else 0.0


def mesafe_kapisi(aday, gecmis, aktif=None):
    """(gecti, sebepler). `aday`/`gecmis` öğeleri: {"phash", "duzen", "kutu"}; `gecmis`
    eskiden yeniye sıralı. ÜÇ koşul birlikte: pHash >= PHASH_ESIGI TÜM geçmişe; düzen
    kimliği son DUZEN_PENCERESI yayından farklı; bindirme IoU son N'e karşı < IOU_ESIGI.
    Bayrak kapalıyken yayını ENGELLEMEZ (hesap fonksiyonları yine çalışır)."""
    if aktif is None:
        aktif = MESAFE_KAPISI_AKTIF
    if not aktif:
        return True, ["kapı kapalı (MESAFE_KAPISI_AKTIF=False)"]
    sebepler = []
    ph = aday.get("phash")
    if ph is None:
        sebepler.append("pHash hesaplanamadı (fail-closed)")
    else:
        for g in gecmis:
            if g.get("phash") is not None and hamming(ph, g["phash"]) < PHASH_ESIGI:
                sebepler.append("pHash mesafesi %d < %d (%s)" % (
                    hamming(ph, g["phash"]), PHASH_ESIGI, g.get("ad", "geçmiş kapak")))
                break
    son = list(gecmis)[-DUZEN_PENCERESI:]
    if any(g.get("duzen") == aday.get("duzen") for g in son):
        sebepler.append("düzen kimliği %s son %d yayında kullanıldı" % (
            aday.get("duzen"), DUZEN_PENCERESI))
    for g in son:
        o = iou(aday.get("kutu"), g.get("kutu"))
        if o >= IOU_ESIGI:
            sebepler.append("bindirme IoU %.2f >= %.2f (%s)" % (o, IOU_ESIGI,
                                                                  g.get("ad", "geçmiş kapak")))
            break
    return (not sebepler), sebepler


# --------------------------------------------------------------------------
# Önizleme üretimi
# --------------------------------------------------------------------------

def _font_rel(kalin):
    yol = (config.FONT_BOLD_PATH if kalin and config.FONT_BOLD_PATH else config.FONT_PATH)
    try:
        rel = os.path.relpath(yol, os.getcwd())
    except ValueError:                                       # farklı sürücü
        rel = yol
    return rel.replace(os.sep, "/")


def _sigdir(baslik, rel_font, kullanilabilir, en_buyuk, maks_satir):
    if maks_satir >= 2:
        return gc._basligi_sigdir(baslik, rel_font, kullanilabilir, en_buyuk)
    esc = gc._escape_drawtext(baslik)
    birim = gc._metin_piksel_genisligi(esc, rel_font) or max(1, len(baslik)) * 0.5
    return esc, max(1, min(en_buyuk, int(kullanilabilir / birim))), 1


def _art_bul(proje):
    for ad in ("art.jpg", "art.jpeg", "art.png"):
        yol = os.path.join(proje, ad)
        if os.path.isfile(yol):
            return yol
    return None


def fotografli_mi(proje):
    """Stok/elle fotoğraf `art.jpg` olarak yazılıyor; `art.png` prosedürel bokeh yolu."""
    art = _art_bul(proje)
    return bool(art) and art.lower().endswith((".jpg", ".jpeg"))


def filtre_zinciri(duzen, w, h, baslik, mood=None):
    """(filter_complex, logo_var) — [0:v] art, [1:v] logo."""
    d = DUZENLER[duzen]
    basis = min(w, h)
    rel_font = _font_rel(d["font"] == "kalin")
    en_buyuk = int(basis * d["punto_tavan_orani"])
    esc, punto, satir = _sigdir(baslik, rel_font, w * d["genislik_orani"], en_buyuk,
                                d["maks_satir"])
    kirp_y = "(ih-oh)*0.25" if d["kirpma_odak"] == "ust_ucte_bir" else "(ih-oh)/2"
    zincir = ("scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d:(iw-ow)/2:%s"
              % (w, h, w, h, kirp_y))
    if d["renk_derecelendirme"] and mood in MOOD_COLOR_MODIFIERS:
        zincir += "," + MOOD_COLOR_MODIFIERS[mood]
    kenar = int(w * 0.07)
    if d["baslik_capa"] == "sol_alt":
        xy = "x=%d:y=h*0.93-text_h" % kenar
    elif d["baslik_capa"] == "alt_bant":
        xy = "x=(w-text_w)/2:y=h*0.86-text_h"
    else:                                                    # sol_orta
        xy = "x=%d:y=h*0.55-text_h/2" % kenar
    zincir += (",drawtext=fontfile=%s:text='%s':fontcolor=white:fontsize=%d:"
               "text_align=%s:borderw=2:bordercolor=black@0.45:"
               "shadowcolor=black@0.75:shadowx=3:shadowy=3:%s"
               % (rel_font, esc, punto, d["hizalama"], xy))
    if not config.LOGO_PATH:
        return "[0:v]" + zincir + "[out]", False
    logo_h = int(basis * d["logo_oran"])
    pay_x, pay_y = int(w * 0.045), int(h * 0.045)
    if d["logo_kose"] == "sag_ust":
        x_ifade, y = "main_w-overlay_w-%d" % pay_x, pay_y
    elif d["logo_kose"] == "sag_alt":
        x_ifade, y = "main_w-overlay_w-%d" % pay_x, h - logo_h - pay_y
    else:                                                    # sol_ust
        x_ifade, y = str(pay_x), pay_y
    return "[0:v]" + zincir + "[bg];" + gc._logo_katmanlari(logo_h, x_ifade, y), True


def uret(proje, duzen, oran, cikti_yolu, baslik, mood=None):
    art = _art_bul(proje)
    if not art:
        raise FileNotFoundError("art.* yok: %s" % proje)
    w, h = gc.COVER_SIZE_WIDE if oran == "16x9" else gc.COVER_SIZE_TALL
    fc, logo = filtre_zinciri(duzen, w, h, baslik, mood)
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", art]
    if logo:
        cmd += ["-i", config.LOGO_PATH]
    cmd += ["-filter_complex", fc, "-map", "[out]", "-frames:v", "1", "-update", "1",
            cikti_yolu]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError("önizleme üretilemedi (%s %s): %s" % (duzen, oran, r.stderr[-600:]))
    return cikti_yolu


def _kontakt(satirlar, oran, cikti_yolu):
    """satirlar: [[D1, D2, D3, D4 yolları (None = siyah)]]."""
    cw, ch = (640, 360) if oran == "16x9" else (270, 480)
    rel_font = _font_rel(True)
    girdiler, parcalar, satir_etiketleri, sayac = [], [], [], 0
    etiket = ("D1 bugün", "D2 alt-sol", "D3 alt bant", "D4 tipografik")
    for r, hucreler in enumerate(satirlar):
        hucre_etiketleri = []
        for c, yol in enumerate(hucreler):
            i = sayac
            sayac += 1
            if yol:
                girdiler += ["-i", yol]
                kaynak = "[%d:v]scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d" % (
                    i, cw, ch, cw, ch)
            else:
                girdiler += ["-f", "lavfi", "-i", "color=black:s=%dx%d:d=0.04" % (cw, ch)]
                kaynak = "[%d:v]null" % i
            parcalar.append("%s,drawtext=fontfile=%s:text='%s':fontsize=%d:fontcolor=white:"
                            "box=1:boxcolor=black@0.6:x=6:y=6,setsar=1[h%d_%d]"
                            % (kaynak, rel_font, etiket[c], 22 if oran == "16x9" else 16, r, c))
            hucre_etiketleri.append("[h%d_%d]" % (r, c))
        parcalar.append("%shstack=inputs=%d[s%d]" % ("".join(hucre_etiketleri),
                                                     len(hucre_etiketleri), r))
        satir_etiketleri.append("[s%d]" % r)
    if len(satir_etiketleri) == 1:
        parcalar.append("[s0]null[out]")
    else:
        parcalar.append("%svstack=inputs=%d[out]" % ("".join(satir_etiketleri),
                                                     len(satir_etiketleri)))
    cmd = (["ffmpeg", "-v", "error", "-y"] + girdiler
           + ["-filter_complex", ";".join(parcalar), "-map", "[out]", "-frames:v", "1",
              "-update", "1", cikti_yolu])
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError("kontakt sayfası üretilemedi: %s" % r.stderr[-600:])
    return cikti_yolu


def _proje_yolu(deger):
    if os.path.isdir(deger):
        return os.path.abspath(deger)
    return os.path.join(_KOK, "projects", deger)


def _baslik(proje):
    return (gc.load_meta(proje).get("title") or os.path.basename(os.path.normpath(proje)))


def projeleri_sec(adlar):
    """(seçilen yollar, notlar). Fotoğrafsız örnek yedek listeden fotoğraflı biriyle değişir."""
    secilen, notlar = [], []
    kullanilan = {os.path.normcase(_proje_yolu(a)) for a in adlar}
    for ad in adlar:
        yol = _proje_yolu(ad)
        if os.path.isdir(yol) and fotografli_mi(yol):
            secilen.append(yol)
            continue
        for yedek in YEDEK_PROJELER:
            yy = _proje_yolu(yedek)
            if os.path.normcase(yy) not in kullanilan and os.path.isdir(yy) and fotografli_mi(yy):
                kullanilan.add(os.path.normcase(yy))
                secilen.append(yy)
                notlar.append("%s fotoğraflı değil (art.* prosedürel ya da yok) -> yerine %s"
                              % (ad, yedek))
                break
    return secilen, notlar


def main(argv=None):
    ap = argparse.ArgumentParser(description="Kapak düzen adaylarını önizler (yayına girmez).")
    ap.add_argument("--cikti", default=VARSAYILAN_CIKTI)
    ap.add_argument("--projeler", nargs="+", default=None,
                    help="proje klasörü yolu ya da projects/ altındaki ad")
    args = ap.parse_args(argv)

    if args.projeler:
        projeler, notlar = [_proje_yolu(p) for p in args.projeler], []
    else:
        projeler, notlar = projeleri_sec(VARSAYILAN_PROJELER)
    cikti = os.path.abspath(args.cikti)
    os.makedirs(cikti, exist_ok=True)
    for n in notlar:
        print("NOT:", n)

    kontakt = {"16x9": [], "9x16": []}
    for proje in projeler:
        baslik = _baslik(proje)
        slug = gc._slugify(baslik) or "proje"
        mood = mood_bul(stil_etiketi(baslik))
        print("%s: mood=%s" % (baslik, mood or "yok (derecelendirme yok)"))
        for oran, d1_ad in (("16x9", "cover.png"), ("9x16", "cover_vertical.png")):
            d1_kaynak = os.path.join(proje, d1_ad)
            d1 = None
            if os.path.isfile(d1_kaynak):
                d1 = os.path.join(cikti, "%s_D1_%s.png" % (slug, oran))
                shutil.copyfile(d1_kaynak, d1)
            satir = [d1]
            for duzen in DUZENLER:
                yol = os.path.join(cikti, "%s_%s_%s.png" % (slug, duzen, oran))
                uret(proje, duzen, oran, yol, baslik, mood)
                satir.append(yol)
                print("  ", yol)
            kontakt[oran].append(satir)
    for oran, satirlar in kontakt.items():
        if satirlar:
            yol = _kontakt(satirlar, oran, os.path.join(cikti, "kontakt_%s.png" % oran))
            print("kontakt:", yol)
    return 0


if __name__ == "__main__":
    sys.exit(main())
