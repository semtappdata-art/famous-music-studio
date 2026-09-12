# -*- coding: utf-8 -*-
"""DJ setleri için sci-fi HUD kaplaması (şeffaf PNG üretir).

Referans (kullanıcının gönderdiği "NOXELUNE HOUSE" karesi) üç katmandan
oluşuyordu: sahne + HUD + hareket. Bu modül ORTADAKİ katmanı üretiyor ve
tamamı ffmpeg ile çiziliyor — hiçbir AI kredisi harcanmıyor, çözünürlük
başına bir kez üretilip önbelleğe alınıyor.

Referanstan bilinçli FARKLAR:

  * Köşe ayraçları ve kenar sütunları burada SABİT çiziliyor, ama ekolayzer
    ÇİZİLMİYOR — onu render zaten setin GERÇEK sesinden üretiyor
    (bkz. ffmpeg_utils._build_filter_complex). Referanstaki dalga formu
    dekoratif; bizimki sesin kendisi.

  * Referansta sayılar uydurma ("12.58.4", "89.58.1"). Buradaki etiketler de
    dekoratif ama ANLAMLI olanları (başlık, süre) render tarafında gerçek
    değerlerle basılıyor; HUD yalnızca çerçeveyi veriyor.

PIL yok (kurulu değil), o yüzden her şey drawbox/drawtext zinciriyle
çiziliyor — köşeler L şeklinde iki dikdörtgen olarak kuruluyor.

ÖNEMLİ — NEDEN OPAK SİYAH ÜZERİNE ÇİZİLİYOR: ilk sürüm şeffaf bir RGBA
tuvaline çiziyordu ve `drawbox` HİÇBİR ŞEY üretmedi (drawtext çalıştı).
Sebep: drawbox şeffaf zeminde alfa kanalına yazmıyor, yalnızca RGB'yi
karıştırıyor; alfa 0'da kaldığı için kutular görünmez oluyor. Alfa 1.0
verildiğinde bile aynı. Bu yüzden HUD opak siyah üzerine çiziliyor ve
`blend=all_mode=screen` ile bindirililiyor: screen modunda siyah hiçbir şey
katmıyor (x + 0 - 0 = x), parlak çizgiler ise ekliyor — üstelik bu, HUD'a
istediğimiz parıltı hissini bedava veriyor.
"""

import os
import subprocess

import config

HUD_DIR = "assets"

# Referanstaki soğuk mavi. Markanın altın tonu (logo) burada KULLANILMIYOR:
# HUD kartın/sahnenin ÜSTÜNDE duran teknik bir katman, sahnenin rengiyle
# yarışmaması gerekiyor. Altın HUD sıcak sahnelerde kayboluyordu.
HUD_RENK = "0x7FE8FF"
HUD_OPAKLIK = 0.55


def _cizgi(x, y, w, h, opaklik=None):
    o = HUD_OPAKLIK if opaklik is None else opaklik
    return ("drawbox=x=%d:y=%d:w=%d:h=%d:color=%s@%.2f:t=fill"
            % (int(x), int(y), max(1, int(w)), max(1, int(h)), HUD_RENK, o))


def hud_yolu(width: int, height: int) -> str:
    return os.path.join(HUD_DIR, "dj_hud_%dx%d.png" % (width, height))


def ensure_hud(width: int, height: int, marka: str = "DJ FAMOUS") -> str:
    """HUD kaplamasını (şeffaf PNG) üretir ve yolunu döner; varsa yeniden üretmez."""
    yol = hud_yolu(width, height)
    if os.path.isfile(yol):
        return yol
    os.makedirs(HUD_DIR, exist_ok=True)

    m = int(min(width, height) * 0.035)       # kenar boşluğu
    kol = int(width * 0.075)                  # köşe ayracının kol uzunluğu
    kal = max(2, int(height / 540))           # çizgi kalınlığı
    font = os.path.relpath(config.FONT_PATH, os.getcwd()).replace("\\", "/")

    p = ["color=c=black:s=%dx%d:d=1:rate=1" % (width, height)]

    # Dört köşe ayracı (L). Kapalı bir çerçeve yerine köşeler: referanstaki
    # gibi "kadraj" hissi veriyor ve sahnenin kenarlarını boğmuyor.
    for kx, ky, ix, iy in ((m, m, 1, 1), (width - m, m, -1, 1),
                           (m, height - m, 1, -1), (width - m, height - m, -1, -1)):
        x0 = kx if ix > 0 else kx - kol
        p.append(_cizgi(x0, ky if iy > 0 else ky - kal, kol, kal))
        y0 = ky if iy > 0 else ky - kol
        p.append(_cizgi(kx if ix > 0 else kx - kal, y0, kal, kol))

    # Üstte, köşelerin arasında ince bir ayraç — ortası BOŞ bırakılıyor ki
    # sahnedeki özne (Arda) çizgiyle kesilmesin.
    ust_y = m + int(height * 0.055)
    bosluk = int(width * 0.34)
    sol_b = m + kol + int(width * 0.02)
    p.append(_cizgi(sol_b, ust_y, (width // 2 - bosluk // 2) - sol_b, max(1, kal // 2), 0.38))
    sag_b = width // 2 + bosluk // 2
    p.append(_cizgi(sag_b, ust_y, (width - m - kol - int(width * 0.02)) - sag_b,
                    max(1, kal // 2), 0.38))

    # Yan sütunlar: eşit aralıklı kısa bloklar (referanstaki veri şeritleri).
    blok_h = max(3, int(height * 0.012))
    blok_w = int(width * 0.030)
    for i in range(7):
        y = int(height * 0.30) + i * int(blok_h * 2.2)
        o = 0.50 - i * 0.045
        p.append(_cizgi(m + kal * 3, y, int(blok_w * (1.0 - i * 0.08)), blok_h, o))
        w2 = int(blok_w * (0.5 + (i % 3) * 0.25))
        p.append(_cizgi(width - m - kal * 3 - w2, y, w2, blok_h, o))

    # Marka etiketi — sağ üstte, referanstaki "NOXELUNE HOUSE" konumunda.
    # Köşe ayracının ALTINA konumlanıyor: ilk denemede ayraçla aynı hizadaydı
    # ve iki öğe birbirine yapışık görünüyordu.
    p.append("drawtext=fontfile=%s:text='%s':fontcolor=%s@0.92:fontsize=%d:"
             "x=w-text_w-%d:y=%d"
             % (font, marka, HUD_RENK, int(height * 0.030),
                m + kal * 4, m + int(height * 0.022)))

    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
           "-f", "lavfi", "-i", ",".join(p),
           "-frames:v", "1", "-update", "1", yol]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError("HUD üretilemedi: %s" % r.stderr[-800:])
    return yol
