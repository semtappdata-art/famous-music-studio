"""meta.json'daki title + theme'e göre otomatik cover.png (başlıklı, platform
thumbnail'i) ve art.png (metinsiz, video kartı + arka plan blur kaynağı) üretir.

Proje bilinçli olarak sadece ffmpeg kullanıyor (Pillow/Playwright gibi ek bir
görsel işleme bağımlılığı eklemiyor) — tema rengine göre radial gradyan arka
plan + şarkı başlığından türetilen deterministik bokeh dokusu + (cover.png
için) ortalanmış başlık metni.

meta.json'da bir "character" alanı varsa (bkz. karakter_roster.md) ve
characters/<karakter-slug>.jpg|jpeg|png dosyası mevcutsa, arka plan kaynağı
olarak o karakterin hazır portresi kullanılır (procedural gradyan yerine) —
art.png bu portrenin AYNISI (metinsiz), cover.png ise üstüne başlık metni
eklenmiş hâli olur. Dosya henüz yoksa (karakter roster'da olup portre daha
hazırlanmamışsa) sessizce procedural gradyana düşülür.

Kullanım:
    python generate_cover.py --project "projects/sarki-adi"

Sadece EKSİK olan dosyayı üretir, var olanın üstüne yazmaz — elle hazırlanmış
özel bir cover/art varsa dokunulmaz. auto_process.py, render'dan önce bunu bir
projede cover eksikse otomatik çağırır; yani artık görselleri elle hazırlamak
zorunlu değil, sadece audio.wav + (opsiyonel) meta.json yeterli.
"""

import argparse
import hashlib
import json
import os
import random
import re
import shutil
import subprocess

import config
import stock_art

CANVAS_SIZE = 1600  # art.png (video kartı + backdrop kaynağı) — HER ZAMAN kare, video pipeline'ı bunu varsayıyor
COVER_SIZE_WIDE = (1600, 900)  # cover.png — YouTube uzun-format thumbnail'i (16:9)
COVER_SIZE_TALL = (900, 1600)  # cover_vertical.png — Shorts/TikTok/Instagram kapağı (9:16)
CHARACTERS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "characters")
# config.LOGO_PATH kaydı düz siyah zemin üzerine koyu/mat bir altın tonuyla
# kaydedilmiş — kapaklarda daha canlı görünsün diye colorkey'den SONRA
# uygulanan bir parlaklık/doygunluk düzeltmesi (kullanıcı geri bildirimiyle
# eklendi, "altın daha parlak olsun").
# 2026-09-07: değer bir kez daha yükseltildi (brightness 0.10->0.16,
# contrast 1.15->1.25) — koyu/siyaha yakın fotoğraf arka planlarında
# (bkz. koyu hâle notu) logo hâlâ soluk kalıyordu.
LOGO_BRIGHTEN_FILTER = "eq=brightness=0.16:saturation=1.9:contrast=1.25,curves=r='0/0 0.5/0.7 1/1':g='0/0 0.5/0.6 1/1'"
# Koyu/siyaha yakın arka planlarda (gece fotoğrafları, karartılmış bokeh
# tabanı) ince sunburst çizgileri ve küçük "FAMOUS" yazısı arka planla aynı
# tona düşüp neredeyse görünmez oluyordu (kullanıcı geri bildirimi: "logo
# siyah zeminde çok kayboluyor"). Çözüm parlaklığı daha da artırmak yerine
# (gerçek altın tonunu soldurup beyaza yakınlaştırırdı) logonun ARKASINA
# bulanıklaştırılmış+parlatılmış bir "hâle" (glow) kopyası eklemek.
#
# 2026-09-11 — bu TEK BAŞINA yetmedi: parlak/sıcak tonlu fotoğraflarda
# (ör. "Son Kez"in altın bina cephesi, "Sessiz Mektup"un açık kumsalı)
# altın-üstüne-altın kontrastı sıfıra iniyor ve 246 px feed boyutunda logo
# tamamen kayboluyordu (ölçüldü: logonun feed piksellerinde yarattığı
# ortalama luma farkı sadece 22.8/255). PARLAK bir hâle burada hiçbir işe
# yaramıyor, çünkü zemin zaten parlak. Eklenen katman: logonun kendi
# alfasından türetilen KOYU (siyah) bir gölge halesi — bulanıklaştırılıp
# alfası çoğaltılarak ışınların arasını dolduruyor, yani amblem hangi
# fotoğrafın üstüne gelirse gelsin kendi koyu zeminini yanında getiriyor.
# Katman sırası: arka plan -> koyu hâle -> (dar) altın ışıma -> keskin logo.
# Işımanın sigması küçültüldü (0.03*h): geniş bir ışıma koyu hâleyi yıkayıp
# etkisiz bırakıyordu (denendi, ölçüldü).
LOGO_GOLGE_SIGMA_ORANI = 0.085   # koyu hâlenin yumuşaklığı (logo yüksekliğine oranla)
LOGO_GOLGE_COGALTMA = 6.0        # bulanık alfayı çoğalt: ışınların arası dolsun
LOGO_GOLGE_OPAKLIK = 0.72        # nihai koyuluk — 0.78 ile ölçülen fark ihmal edilebilir,
                                 # 0.72 fotoğrafı daha az bastırıyor
LOGO_ISIMA_SIGMA_ORANI = 0.03    # altın ışıma (koyu zeminlerde işe yarayan eski glow)


def _alfa_carpani(kat: float) -> str:
    """colorchannelmixer'in `aa` üst sınırı 2.0 — daha yüksek bir çarpan için
    filtreyi zincirleyerek aynı etkiyi üretir (aa=6 -> 2*2*1.5)."""
    zincir, kalan = "", float(kat)
    while kalan > 1.001:
        adim = min(2.0, kalan)
        zincir += f",colorchannelmixer=aa={adim:g}"
        kalan /= adim
    if kalan < 0.999:
        zincir += f",colorchannelmixer=aa={kalan:g}"
    return zincir


def _logo_katmanlari(logo_h: int, x_ifade: str, y: int,
                     giris: str = "bg", cikis: str = "out") -> str:
    """[1:v] logosunu `giris` etiketli görüntünün üstüne bindiren filtre
    parçası (koyu hâle + altın ışıma + keskin logo), `cikis` etiketiyle biter.

    İki kapak düzeni de (sade ortalanmış ve prosedürel "rich") aynı katmanları
    kullansın diye tek yerde toplandı — daha önce zincir iki yerde kopyalanmıştı
    ve biri güncellenince diğeri geride kalıyordu."""
    golge_sigma = max(1, round(logo_h * LOGO_GOLGE_SIGMA_ORANI))
    isima_sigma = max(1, round(logo_h * LOGO_ISIMA_SIGMA_ORANI))
    koyuluk = _alfa_carpani(LOGO_GOLGE_COGALTMA) + _alfa_carpani(LOGO_GOLGE_OPAKLIK)
    return (
        f"[1:v]scale=-1:{logo_h},colorkey=0x000000:0.15:0.05,"
        f"{LOGO_BRIGHTEN_FILTER},format=rgba,split=3[logo][isima_src][golge_src];"
        f"[golge_src]lutrgb=r=0:g=0:b=0,gblur=sigma={golge_sigma}{koyuluk},format=rgba[golge];"
        f"[isima_src]gblur=sigma={isima_sigma},eq=brightness=0.55:saturation=1.6,format=rgba[isima];"
        f"[{giris}][golge]overlay=x={x_ifade}:y={y}[lg_golge];"
        f"[lg_golge][isima]overlay=x={x_ifade}:y={y}[lg_isima];"
        f"[lg_isima][logo]overlay=x={x_ifade}:y={y}[{cikis}]"
    )


_TR_TRANSLATE = str.maketrans("çÇğĞıİöÖşŞüÜ", "cCgGiIoOsSuU")


def _slugify(name: str) -> str:
    """'Kerem Ateşi' -> 'kerem-atesi' — characters/ klasöründeki portre dosya
    adlarıyla eşleşsin diye (karakter_roster.md'deki isimlerle aynı kurala göre)."""
    ascii_name = name.translate(_TR_TRANSLATE)
    return re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")


def find_character_image(character_name: str) -> str | None:
    slug = _slugify(character_name)
    for ext in (".jpg", ".jpeg", ".png"):
        path = os.path.join(CHARACTERS_DIR, slug + ext)
        if os.path.isfile(path):
            return path
    return None


def _find_existing_art(project_dir: str) -> str | None:
    for name in ("art.jpg", "art.jpeg", "art.png"):
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


def _escape_drawtext(text: str) -> str:
    text = text.replace("\\", "\\\\")
    text = text.replace(":", "\\:")
    text = text.replace("'", "’")
    text = text.replace("%", "\\%")
    return text


def _radial_background(out_path: str, accent: tuple[int, int, int]) -> None:
    """Tema accent renginin açık tonundan (merkez) neredeyse siyaha (kenarlar)
    radial gradyan — ffmpeg_utils.ensure_vignette ile aynı geq deseni."""
    light = tuple(c + (255 - c) * 0.55 for c in accent)
    dark = (12, 9, 16)
    size = CANVAS_SIZE

    dist = "hypot(X-W/2\\,Y-H/2)"
    maxdist = "hypot(W/2\\,H/2)"
    t = f"min(1\\,{dist}/{maxdist})"
    r_expr = f"{light[0]:.1f}+({dark[0] - light[0]:.1f})*{t}"
    g_expr = f"{light[1]:.1f}+({dark[1] - light[1]:.1f})*{t}"
    b_expr = f"{light[2]:.1f}+({dark[2] - light[2]:.1f})*{t}"

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=black:s={size}x{size}",
        "-vf", f"geq=r='{r_expr}':g='{g_expr}':b='{b_expr}'",
        "-frames:v", "1", "-update", "1",
        out_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"Arka plan üretilemedi: {result.stderr[-1000:]}")


def _add_bokeh(bg_path: str, out_path: str, accent: tuple[int, int, int], seed: int) -> None:
    """Düz radyal arka planın üstüne, şarkı başlığından türetilen SEED ile
    deterministik (her şarkı farklı ama tekrar üretilince aynı) birkaç yumuşak
    ışık lekesi (bokeh) ekler.

    Bunsuz art.png tamamen düz bir gradyandı: video render'da kart (ön plan) ve
    arka plan (o gradyanın bulanıklaştırılmış hâli) neredeyse ayırt edilemiyordu
    — kartın içi de boş kalıyordu. Bokeh dokusu hem art.png'ye (kart + backdrop
    kaynağı) hem cover.png'ye gerçek bir doku/derinlik katıyor, ffmpeg_utils.
    ensure_vignette()'teki bokeh formülüyle aynı yaklaşımı kullanıyor."""
    rng = random.Random(seed)
    size = CANVAS_SIZE
    light = tuple(c + (255 - c) * 0.55 for c in accent)
    white = (255, 255, 255)

    blobs = []
    for _ in range(rng.randint(5, 8)):
        cx = rng.uniform(0.12, 0.88) * size
        cy = rng.uniform(0.12, 0.88) * size
        sigma = rng.uniform(0.05, 0.14) * size
        peak = rng.uniform(30, 70)
        color = white if rng.random() < 0.35 else light
        blobs.append((cx, cy, sigma, peak, color))

    def _channel_expr(source: str, idx: int) -> str:
        terms = [f"{source}(X,Y)"]
        for cx, cy, sigma, peak, color in blobs:
            dist = f"hypot(X-{cx:.1f}\\,Y-{cy:.1f})"
            falloff = f"exp(-pow({dist}/{sigma:.1f}\\,2))"
            terms.append(f"{peak * color[idx] / 255:.3f}*{falloff}")
        return "clip(" + "+".join(terms) + "\\,0\\,255)"

    cmd = [
        "ffmpeg", "-y",
        "-i", bg_path,
        "-vf", f"geq=r='{_channel_expr('r', 0)}':g='{_channel_expr('g', 1)}':b='{_channel_expr('b', 2)}'",
        "-frames:v", "1", "-update", "1",
        out_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"Bokeh dokusu eklenemedi: {result.stderr[-1000:]}")


# Tek sifir bayt. b-kacisi yerine bytes(1): bu dosya birden cok kacis
# katmanindan (JSON, heredoc) geciyor ve ters egik cizgi ucuncu kez
# yutuldu. bytes(1) hicbir katmanda bozulamaz.
BOS_BAYT = bytes(1)


def _metin_piksel_genisligi(escaped_text: str, rel_font: str,
                            olcum_fontsize: int = 60, satir: int = 1):
    """drawtext'in bu metni KAC PIKSEL genislikte cizecegini olcer.

    Neden olcum: baslik puntosu buyutulunce (0.075 -> 0.14) uzun basliklarin
    9:16 kapakta (900 px genislik) tuvali tasip kesilecegi ortaya cikti —
    "Sokaklar Beni Tanir" 126 px puntoda ~1040 px yer istiyor. Karakter basi
    ortalama genislik TAHMINI yeterli degil: olculen degerler harfe gore
    0.43-0.50 em arasinda degisiyor (Turkce 'ı/ğ/ş' dahil), yani %15'lik bir
    tahmin hatasi ya tasma ya gereksiz kucultme demek.

    Yontem: metni kucuk bir gri kareye cizdirip sagdaki son bos olmayan
    sutunu buluyoruz. drawtext genisligi punto ile DOGRUSAL oldugu icin tek
    olcum yeterli. ffmpeg'e tek, kisa bir cagri (~0.1 sn).

    Olcum basarisiz olursa None doner — cagiran taraf tahmine duser, kapak
    uretimi hicbir kosulda durmaz.
    """
    # Olcum tuvalinin YUKSEKLIGI satir sayisiyla buyuyor. NEDEN: iki satirlik
    # bir metin 140 px'lik tuvale sigmiyor (60 punto satir yuksekligi ~80 px),
    # ikinci satir tuvalin disinda kalirdi ve genisligi hic olculmezdi —
    # satir kirma sonrasi gercekte olandan KUCUK bir genislik doner, punto
    # oldugundan buyuk secilir ve baslik yine tasardi.
    g, y = 2400, 140 + 90 * (satir - 1)
    try:
        cmd = [
            "ffmpeg", "-v", "error", "-f", "lavfi",
            "-i", (f"color=black:s={g}x{y}:d=0.04,"
                   f"drawtext=fontfile={rel_font}:text='{escaped_text}':"
                   f"fontcolor=white:fontsize={olcum_fontsize}:x=10:y=30"),
            "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "gray", "-",
        ]
        ham = subprocess.run(cmd, capture_output=True, timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    if len(ham) < g * y:
        return None
    sag = 0
    for sat in range(y):
        # rstrip C seviyesinde: satir basina Python dongusu yok.
        u = len(ham[sat * g:(sat + 1) * g].rstrip(BOS_BAYT))
        if u > sag:
            sag = u
    if sag <= 10:
        return None
    return (sag - 10) / float(olcum_fontsize)      # punto basina genislik


# drawtext'e satir sonu olarak giden karakter: HAM (0x0A) satir sonu.
# DIKKAT — 2026-09-11'de olculdu, sezgiye TERS: ffmpeg'in filtre grafigi
# ayristiricisi tirnak icindeki metinde "\n" (ters egik cizgi + n) dizisini
# satir sonu OLARAK GORMUYOR; ters egik cizgiyi kacis karakteri sayip yutuyor
# ve ekrana duz bir 'n' harfi ciziliyor ("YenidennDogacagim" — gercek bir
# render'da goruldu). Tirnak icine konan HAM satir sonu ise sorunsuz geciyor.
# Ayrica: _escape_drawtext() ters egik cizgiyi ikiye katliyor ("\\" -> "\\\\"),
# bu yuzden satirlar TEK TEK kacirilip SONRA birlestiriliyor — once birlestirip
# sonra kacirmak satir sonunu her halukarda bozar.
DRAWTEXT_SATIR_SONU = "\n"
# Bir basligi kirmadan once kac satira kadar bolunebilecegi. 2'de birakildi:
# uc satirlik bir baslik kapak duzenini blok metne cevirir, fotografin ustunu
# kapatir (kullanicinin reddettigi "zengin"/dekoratif yone kayar).
MAKS_BASLIK_SATIRI = 2
# drawtext'in bir SATIR icin ayirdigi yukseklik, punto cinsinden (em) — yani
# iki satir arasindaki ilerleme. OLCULDU (2026-09-11, tahmin DEGIL): ayni metin
# tek satir ve iki satir olarak render edilip murekkep tabanlari
# karsilastirildi, fark 144 puntoda tam 192 px = 1.3333 em.
DRAWTEXT_SATIR_YUKSEKLIGI = 1.3333
# Baslik metin KUTUSUNUN ALTI ile ayrac cizgisi arasinda birakilan bosluk (em).
#
# NEDEN VAR (2026-09-11): eski ifade `y_rule - fs*(1.15 + 1.33*(n-1))` idi.
# Kutunun altini hesaplarsan `y_rule + 0.18*fs` cikiyor — yani metin kutusu
# ayracin 0.18 em ICINE giriyordu. Bu, kutuyu ayracin USTUNE oturtmayi
# amaclayan bir ifadenin YANLIS olmasi demek; 1.15 sabiti hicbir olcume
# dayanmiyordu.
#
# OLCULEN GERCEK DURUM (ayni gun, Segoe UI Bold, 16:9 ve 9:16, tek ve iki
# satirli basliklar): cizgi harfi FIILEN KESMIYORDU — cunku drawtext kutusunun
# alt ~0.395 em'i bos "internal leading"; en derin kuyruk (Ç/Ş sedillasi, p, y)
# kutunun tepesinden sadece 0.938 em asagi iniyor. Yani harfin alti ile cizgi
# arasinda 0.15-0.21 em (144 puntoda 22-27 px) kaliyordu. Pay POZITIFTI ama
# KAZAYLA pozitifti: kodun hedefledigi hizalama ile ekranda olani ayakta tutan
# sey, kodun hic bilmedigi bir font metrigiydi. Kuyrugu daha derin bir fontta
# (ya da config.FONT_BOLD_PATH degistiginde) sessizce kesmeye baslardi ve bu,
# hata vermeyen, sadece bazi basliklarda goze carpan bir bozulma olurdu.
# Simdi geometri ACIK: kutu ayracin ustunde bitiyor, pay 0.39-0.49 em.
BASLIK_AYRAC_BOSLUGU = 0.12


def _basligi_sigdir(title: str, rel_font: str, kullanilabilir: int,
                    en_buyuk: int) -> tuple[str, int, int]:
    """Basligi `kullanilabilir` piksel genisligine sigdirir.

    Doner: (drawtext'e verilecek KACIRILMIS metin, punto, satir sayisi).

    KARAR KURALI (2026-09-11, kullanici geri bildirimi: "9:16 kapakta uzun
    basliklar punto feda ediyor"):
      1. Once TEK satir, TAVAN puntoda (en_buyuk) denenir. Siginca is biter —
         kisa basliklar ("Son Kez") asla kirilmaz.
      2. Sigmiyorsa ve baslik EN AZ IKI KELIMEDEN olusuyorsa iki satira
         bolunur ve punto tavani KORUNUR. 9:16 kapak (900 px) Shorts/TikTok/
         Instagram'in asil dar tuvali; kaybi punto yerine satirdan karsilamak
         dogru yer.
      3. Bolme noktasi kelime sinirinda ve DENGELI secilir: her aday bolme
         gercekten olculur, en genis satiri en dar kalan aday kazanir
         (karakter sayisi tahmini yeterli degil — "İ" ile "ı" ayni sayida
         karakter ama farkli genislikte).
      4. Tek kelimelik baslik ("Yeralti") bolunemez — tek satirda kalir ve
         sadece o durumda punto kucultulur.
      5. Iki satir da tavan puntoda sigmiyorsa punto sigacak kadar kucultulur.
         ESKI ALT SINIR (basis*0.075) KALDIRILDI: min()/max() ikilisi alt
         siniri ancak metin GERCEKTEN sigmadiginda devreye sokuyordu, yani
         tek yaptigi sey tasmayi garantilemekti (denetim bulgusu: 44 karakterlik
         bir baslikta 1327 px metin 900 px tuvale "sigirilmis" gorunuyordu).
         Artik kucultme her zaman olculen genislige uyuyor.
    """
    tek_satir = _escape_drawtext(title)

    def _birim(escaped: str, satir: int) -> float:
        b = _metin_piksel_genisligi(escaped, rel_font, satir=satir)
        if b and b > 0:
            return b
        # Olcum basarisiz (ffmpeg yok/zaman asimi) — kaba tahmine dus, uretim
        # hicbir kosulda durmasin.
        en_uzun = max((len(p) for p in escaped.split(DRAWTEXT_SATIR_SONU)), default=1)
        return max(1, en_uzun) * 0.50

    birim = _birim(tek_satir, 1)
    if kullanilabilir / birim >= en_buyuk:
        return tek_satir, en_buyuk, 1

    kelimeler = title.split()
    if len(kelimeler) < 2 or MAKS_BASLIK_SATIRI < 2:
        return tek_satir, max(1, int(kullanilabilir / birim)), 1

    adaylar = []
    for i in range(1, len(kelimeler)):
        metin = (_escape_drawtext(" ".join(kelimeler[:i]))
                 + DRAWTEXT_SATIR_SONU
                 + _escape_drawtext(" ".join(kelimeler[i:])))
        adaylar.append(metin)
    if len(adaylar) > 6:
        # Cok kelimeli basliklarda her adayi olcmek ffmpeg cagrisi basina
        # ~0.1 sn — ortadan bolup tek olcumle yetiniyoruz.
        orta = len(kelimeler) // 2
        adaylar = [adaylar[orta - 1]]
    en_iyi, birim2 = min(((m, _birim(m, 2)) for m in adaylar), key=lambda p: p[1])
    return en_iyi, max(1, min(en_buyuk, int(kullanilabilir / birim2))), 2


def _add_title_text(
    bg_path: str, out_path: str, title: str, y_center_ratio: float = 0.5,
    out_w: int = CANVAS_SIZE, out_h: int = CANVAS_SIZE,
) -> None:
    """bg_path'teki görsele başlık + sabit marka satırını ortalayarak yazar,
    out_path'e yazar (bg_path değiştirilmez). y_center_ratio, başlığın dikey
    merkezinin canvas yüksekliğine oranı — procedural gradyanda tam ortada
    (0.5) durur, ama bir karakter portresi arka planken (bkz. generate())
    büst siluetiyle çakışmasın diye başın ÜSTÜNDEKİ boş alana (küçük bir
    oran) taşınır.

    out_w/out_h çıktı kanvası boyutu — generate() bunu HEM cover.png (16:9,
    COVER_SIZE_WIDE) HEM cover_vertical.png (9:16, COVER_SIZE_TALL) için ayrı
    ayrı çağırır (YouTube uzun-format ile Shorts/TikTok/Instagram farklı
    thumbnail en-boy oranı bekliyor — tek kare görsel ikisinde de kenarlarda
    çirkin pillarbox/letterbox şeridine yol açıyordu, kullanıcı geri
    bildirimiyle tespit edildi). Font boyutları min(out_w,out_h) baz alınarak
    hesaplanıyor ki iki farklı en-boy oranında da orantılı görünsün.

    bg_path kaynağı (procedural arka plan, karakter portresi ya da elle
    sağlanan bir art.jpg) HERHANGİ bir çözünürlükte/en-boy oranında olabilir
    — bu yüzden her zaman önce out_w x out_h'e scale+crop ediliyor (aynı
    normalizasyon ffmpeg_utils.py'nin video kartı için de yaptığı)."""
    rel_font = os.path.relpath(config.FONT_PATH, os.getcwd()).replace("\\", "/")
    label_escaped = _escape_drawtext(config.STATIC_LABEL_TEXT)
    basis = min(out_w, out_h)
    # 0.075 -> 0.14. NEDEN: kapak YouTube feed'inde ~246 piksel genisliginde
    # goruntuleniyor. Eski oran 1600x900 kapakta 67px yaziya denk geliyordu,
    # feed'de ~10 PIKSELE dusuyor ve okunmuyordu (2026-09-11'de kapak
    # arastirmasiyla olculdu: 9/9 kapakta baslik feed boyutunda secilemiyor).
    # Nis taramasi da ayni yone isaret etti: incelenen 54 muzik kapaginda
    # "ya cok az yazi ya cok buyuk yazi" deseni var; orta boy ince baslik
    # hicbirinde yok. YouTube'un kendi tavsiyesi de "okunabilir yazi tipi,
    # mumkun oldugunca buyuk".
    # Ust sinir 0.14; metin sigmiyorsa ONCE satira bolunur, ancak tek kelimelik
    # bir baslikta kucultuluyor (bkz. _basligi_sigdir). Eski ALT SINIR (0.075)
    # kaldirildi — sadece tasmayi maskeliyordu.
    en_buyuk = int(basis * 0.14)
    kullanilabilir = out_w * 0.86          # iki yanda %7 bosluk
    # Tek satira ZORLAMAK yerine gerekirse iki satira bol, punto tavanini
    # koru (bkz. _basligi_sigdir). ONCE: "Yeniden Dogacagim" 9:16 kapakta
    # 126 yerine 88 puntoya dusuyordu — kayip tam da en dar tuvalde,
    # Shorts/TikTok/Instagram kapaginda oluyordu.
    title_escaped, title_fontsize, satir_sayisi = _basligi_sigdir(
        title, rel_font, kullanilabilir, en_buyuk)
    label_fontsize = int(basis * 0.03)
    y_center = int(out_h * y_center_ratio)
    # Metin blogunun tahmini yuksekligi: Segoe UI'da drawtext satir yuksekligi
    # ~1.33 em (olculdu). Iki satirda blok yukari dogru buyudugu icin, tuvalin
    # ust kenarindan tasmamasi adina metin merkezi gerekirse asagi kaydiriliyor
    # (y_center_ratio=0.13 ile 16:9 kapakta iki satir tepeden kesiliyordu).
    blok_h = int(title_fontsize * 1.33 * satir_sayisi)
    en_ust = int(out_h * 0.04)
    if y_center - blok_h // 2 < en_ust:
        y_center = en_ust + blok_h // 2

    base_chain = (
        f"scale={out_w}:{out_h}:force_original_aspect_ratio=increase,"
        f"crop={out_w}:{out_h},"
        f"drawtext=fontfile={rel_font}:text='{title_escaped}':"
        f"fontcolor=white:fontsize={title_fontsize}:"
        # Golge sart: stok fotograflarin bir kismi acik tonlu (deniz, gokyuzu,
        # cicek) ve beyaz yazi orada kayboluyordu. Tek katmanli golge yetmedigi
        # icin kalin ve koyu.
        f"shadowcolor=black@0.75:shadowx=3:shadowy=3:"
        f"x=(w-text_w)/2:y={y_center}-(text_h/2)"
    )

    if config.LOGO_PATH:
        # Düz "Famous Music Studio" metni yerine gerçek amblem (bkz.
        # _compose_cover_rich'teki aynı yaklaşım/not) — ortalanmış.
        # 0.2 -> 0.26 (%30). NEDEN: 246 px feed boyutunda eski oran ~28 px'lik
        # bir amblem demekti ve o boyutta sunburst ışınları tek bir lekeye
        # dönüşüyordu. Daha fazlası düzeni bozardı — kullanıcı daha önce "dev
        # logo"lu dekoratif düzeni (_compose_cover_rich) reddetti; fotoğraf
        # kompozisyonun asıl unsuru kalmalı. Ölçülü artış + koyu hâle birlikte
        # ölçülen feed kontrastını 22.8'den 54.8'e (2.4x) çıkardı.
        logo_h = int(basis * 0.26)
        # Baslik 0.075'ten 0.14'e buyudugu icin logo konumu da asagi kaydi;
        # eski carpan (0.85) yeni puntoda logoyu yazinin uzerine bindiriyordu.
        # Iki satirli baslikta blok asagi dogru da buyuyor — o yuzden sabit bir
        # carpan yerine metin blogunun GERCEK yarim yuksekligi kullaniliyor,
        # yoksa logo ikinci satirin uzerine biniyordu.
        logo_y = y_center + blok_h // 2 + int(title_fontsize * 0.04)
        filter_complex = (
            f"[0:v]{base_chain}[bg];"
            + _logo_katmanlari(logo_h, "(main_w-overlay_w)/2", logo_y)
        )
        cmd = [
            "ffmpeg", "-y",
            "-i", bg_path,
            "-i", config.LOGO_PATH,
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-frames:v", "1", "-update", "1",
            out_path,
        ]
    else:
        filter_complex = (
            f"{base_chain},"
            f"drawtext=fontfile={rel_font}:text='{label_escaped}':"
            f"fontcolor=white@0.75:fontsize={label_fontsize}:"
            f"x=(w-text_w)/2:y={y_center}+{int(title_fontsize * 0.9)}"
        )
        cmd = [
            "ffmpeg", "-y",
            "-i", bg_path,
            "-vf", filter_complex,
            "-frames:v", "1", "-update", "1",
            out_path,
        ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"Başlık yazılamadı: {result.stderr[-1000:]}")


def _compose_cover_rich(
    bg_path: str, out_path: str, title: str, accent: tuple[int, int, int],
    out_w: int = CANVAS_SIZE, out_h: int = CANVAS_SIZE,
) -> None:
    """Procedural (temasız arka plan) kapaklar için zenginleştirilmiş kompozisyon:
    sol-alt yaslı düzen (Spotify "Now Playing" tarzı) + harf aralıklı tür etiketi +
    gölgeli kalın başlık + ince ayraç çizgisi + alt gradyan gölgeleme (bokeh dokusu
    metnin altına denk gelirse okunurluk garantisi) + alt kenarda tema-rengi ince bir
    marka şeridi (kataloğun tamamında tutarlı bir görsel imza). Sadece cover.png/
    cover_vertical.png için kullanılır — art.png (kart+backdrop kaynağı) bu
    kompozisyondan ETKİLENMEZ, aynı metinsiz bokeh dokusu kalır.

    out_w/out_h — generate() bunu HEM cover.png (16:9) HEM cover_vertical.png (9:16)
    için ayrı çağırır. Metin bloğu buna göre ALTTAN yukarı doğru istifleniyor (sabit
    bir üstten-oran yerine) ki kısa (900px) bir tuval taşırmasın, uzun (1600px) bir
    tuvalde de gereksiz yere tepede kalmasın. Font boyutları min(out_w,out_h) baz
    alınarak hesaplanıyor — iki oranda da aynı mutlak boyutta, tutarlı görünsün."""
    rel_font = os.path.relpath(config.FONT_PATH, os.getcwd()).replace("\\", "/")
    rel_font_bold = os.path.relpath(config.FONT_BOLD_PATH, os.getcwd()).replace("\\", "/")
    brand_escaped = _escape_drawtext(config.STATIC_LABEL_TEXT)
    accent_hex = "%02x%02x%02x" % accent
    basis = min(out_w, out_h)

    margin = int(out_w * 0.07)
    # Bu yol UZUN SUREDIR olcum yapmiyordu ve _add_title_text'ten DAHA BUYUK
    # punto kullaniyor (0.16): 9:16 tuvalde (900 px) katalogdaki 20 basligin
    # 13'u tasiyordu ("Yeniden Dogacagim" 144 puntoda 1258 px istiyor). Ustelik
    # bu yol stock_art.fetch_art basarisiz olunca SESSIZCE seciliyor, yani hata
    # ancak kapaga bakinca fark edilirdi. Artik ayni sigdirma/satir kirma
    # mantigi burada da kullaniliyor.
    title_metin, title_fs, title_satir = _basligi_sigdir(
        title, rel_font_bold, out_w - 2 * margin, int(basis * 0.16))
    subtitle_fs = int(basis * 0.048)
    rule_w = int(out_w * 0.09)
    bar_h = int(basis * 0.03)
    use_logo = bool(config.LOGO_PATH)
    # Amblem, düz metinden daha "kalın" göründüğü için daha yüksek bir slot
    # ayrılıyor — küçük thumbnail boyutunda bile "FAMOUS" okunsun diye
    # (kullanıcı geri bildirimiyle büyütüldü: ilk deneme çok küçüktü).
    logo_h = int(basis * 0.30)  # bu düzende logo zaten büyük, değiştirilmedi
    brand_h = logo_h if use_logo else subtitle_fs

    # Alttan yukarı istifleme: şerit -> marka (logo/metin) -> ayraç -> başlık.
    # Tür etiketi ("ARABESK"/"ELEKTRONİK" gibi harf aralıklı üst satır) kullanıcı
    # isteğiyle KALDIRILDI — tarz bilgisi zaten caption/hashtag'lerde var,
    # kapakta yer kaplıyordu. Tema rengi ayraç çizgisinde ve alt şeritte
    # kalmaya devam ediyor, yani görsel tarz kimliği kaybolmadı.
    y_bar = out_h - bar_h
    margin_bottom = int(out_h * 0.05)
    y_brand = y_bar - margin_bottom - brand_h
    y_rule = y_brand - int(out_h * 0.025) - 3
    # Baslik bloku ayracin USTUNE oturuyor: kutunun ALTI = y_title +
    # satir_sayisi * satir_yuksekligi. Bunu y_rule'un TAM USTUNDE tutmak icin
    # y_title'i kutu yuksekligi + kucuk bir bosluk kadar yukari aliyoruz.
    # Eski ifade `1.15 + 1.33*(n-1)` idi ve kutunun altini y_rule'un 0.18 em
    # ICINE sokuyordu; tema rengi ayrac ile son satirin `ç/ş/y/p` kuyruklari
    # arasinda kalan pay yalnizca font metriginin kazasiydi (bkz.
    # BASLIK_AYRAC_BOSLUGU'nun yanindaki olcumlu not). Formulun
    # dogrulugu yukari dogru yer olup olmadigina bagli degil: 16:9 (1600x900)
    # en dar durum ve orada bile iki satirli/tavan puntolu baslikta y_title
    # ~133 px kaliyor, yani tuvalden tasmiyor.
    y_title = y_rule - int(title_fs * (
        DRAWTEXT_SATIR_YUKSEKLIGI * title_satir + BASLIK_AYRAC_BOSLUGU))

    base_chain = (
        f"scale={out_w}:{out_h}:force_original_aspect_ratio=increase,"
        f"crop={out_w}:{out_h},"
        # Alt ~yarıyı kademeli karart — arka plan ne olursa olsun başlık ve altın
        # amblem okunur kalsın. Katsayı 0.55'ten 0.72'ye çıkarıldı ve karartma
        # daha yukarıdan (%50) başlıyor: prosedürel bokeh dokularında 0.55
        # yetiyordu ama GERÇEK fotoğraflara geçince (bkz. stock_art.py) parlak
        # gündüz kareleri geldi ve o kadar karartmada logo soluk kalıyordu.
        f"geq=r='r(X,Y)*(1-0.72*max(0\\,(Y-H*0.50)/(H*0.50)))':"
        f"g='g(X,Y)*(1-0.72*max(0\\,(Y-H*0.50)/(H*0.50)))':"
        f"b='b(X,Y)*(1-0.72*max(0\\,(Y-H*0.50)/(H*0.50)))',"
        # başlık — hafif gölge + kalın beyaz üst katman
        f"drawtext=fontfile={rel_font_bold}:text='{title_metin}':fontcolor=black@0.5:"
        f"fontsize={title_fs}:x={margin}+4:y={y_title}+5,"
        f"drawtext=fontfile={rel_font_bold}:text='{title_metin}':fontcolor=white:"
        f"fontsize={title_fs}:x={margin}:y={y_title},"
        # ayraç çizgisi
        f"drawbox=x={margin}:y={y_rule}:w={rule_w}:h=3:color=0x{accent_hex}@1.0:t=fill"
    )

    if use_logo:
        # Düz "Famous Music Studio" metni yerine gerçek amblem (altın sunburst +
        # wordmark) — logo düz SİYAH zemin üzerine kaydedilmiş (alfasız), colorkey
        # ile siyah şeffaflaştırılıp sadece altın kısım overlay ediliyor.
        filter_complex = (
            f"[0:v]{base_chain}[bg];"
            + _logo_katmanlari(logo_h, str(margin), y_brand, cikis="merged")
            + f";[merged]drawbox=x=0:y={y_bar}:w=iw:h={bar_h}:color=0x{accent_hex}@1.0:t=fill[out]"
        )
        cmd = [
            "ffmpeg", "-y",
            "-i", bg_path,
            "-i", config.LOGO_PATH,
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-frames:v", "1", "-update", "1",
            out_path,
        ]
    else:
        # Logo asset'i bulunamadı (gitignored, bu makinede henüz konmamış olabilir)
        # — sessizce düz metin marka satırına düş, hata verme.
        filter_complex = (
            f"{base_chain},"
            f"drawtext=fontfile={rel_font}:text='{brand_escaped}':fontcolor=white@0.75:"
            f"fontsize={subtitle_fs}:x={margin}:y={y_brand},"
            f"drawbox=x=0:y={y_bar}:w=iw:h={bar_h}:color=0x{accent_hex}@1.0:t=fill"
        )
        cmd = [
            "ffmpeg", "-y",
            "-i", bg_path,
            "-vf", filter_complex,
            "-frames:v", "1", "-update", "1",
            out_path,
        ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"Kapak kompozisyonu başarısız: {result.stderr[-1000:]}")


def generate(project_dir: str) -> None:
    meta = load_meta(project_dir)
    title = meta.get("title") or os.path.basename(os.path.normpath(project_dir))
    theme_key = meta.get("theme", config.DEFAULT_THEME)
    theme = config.THEMES.get(theme_key, config.THEMES[config.DEFAULT_THEME])
    character = meta.get("character")

    has_cover = any(
        os.path.isfile(os.path.join(project_dir, n))
        for n in ("cover.jpg", "cover.jpeg", "cover.png")
    )
    has_cover_vertical = any(
        os.path.isfile(os.path.join(project_dir, n))
        for n in ("cover_vertical.jpg", "cover_vertical.jpeg", "cover_vertical.png")
    )
    has_art = any(
        os.path.isfile(os.path.join(project_dir, n))
        for n in ("art.jpg", "art.jpeg", "art.png")
    )
    if has_cover and has_cover_vertical and has_art:
        return

    character_image = find_character_image(character) if character else None
    # has_art ise (elle sağlanmış bir görsel var, ör. karakter roster'ında olmayan
    # bir proje için manuel art.jpg — DJ Famous gibi) cover.png'yi o gerçek görselden
    # türetiyoruz; öncesinde bu durumda cover.png ilgisiz bir procedural gradyandan
    # üretiliyordu (art.jpg tamamen göz ardı ediliyordu) — sağlanan görselle
    # bağlantısız bir kapak çıkması bir hataydı.
    existing_art = _find_existing_art(project_dir) if has_art else None
    cleanup_paths = []
    fetched_stock_photo = False
    if character_image:
        bg_path = character_image
        bg_ext = os.path.splitext(character_image)[1]
        source_label = f"karakter portresi: {character}"
    elif existing_art:
        bg_path = existing_art
        bg_ext = os.path.splitext(existing_art)[1]
        source_label = "elle sağlanan art görseli"
    else:
        # Önce şarkının tarzına/sözlerine uygun GERÇEK bir fotoğraf denenir
        # (Pexels, bkz. stock_art.py) — kullanıcı isteği: kapak soyut bir
        # gradyan değil, tarzın çağrıştırdığı bir mekân/atmosfer olsun.
        # Başarısızsa (anahtar/ağ/sonuç yok) sessizce eski prosedürel bokeh
        # üretimine düşülür, otomasyon asla durmaz.
        stock_path = os.path.join(project_dir, "_stock_art_tmp.jpg")
        stock_query = stock_art.build_query(meta, theme, title)
        if stock_query and stock_art.fetch_art(title, stock_query, stock_path):
            bg_path = stock_path
            bg_ext = ".jpg"
            cleanup_paths = [stock_path]
            source_label = f"Pexels görseli ({stock_query!r})"
            fetched_stock_photo = True
        else:
            seed = int(hashlib.sha256(title.encode("utf-8")).hexdigest()[:8], 16)
            base_path = os.path.join(project_dir, "_bg_base_tmp.png")
            bg_path = os.path.join(project_dir, "_bg_tmp.png")
            bg_ext = ".png"
            _radial_background(base_path, theme["accent"])
            _add_bokeh(base_path, bg_path, theme["accent"], seed)
            cleanup_paths = [base_path, bg_path]
            source_label = f"{theme_key} teması"

    cover_path = os.path.join(project_dir, "cover.png")
    cover_vertical_path = os.path.join(project_dir, "cover_vertical.png")
    art_path = os.path.join(project_dir, f"art{bg_ext}")
    # DJ Famous kapaklarındaki (dj_sets/) sade/ortalanmış düzen — kullanıcı
    # isteğiyle TÜM gerçek fotoğraflara (karakter portresi, elle sağlanan
    # görsel, Pexels stok fotoğrafı) genelleştirildi. "Zengin" sol-alt blok
    # (ayraç + alt marka şeridi + büyük logo) kullanıcı tarafından beğenilmedi
    # ("yapılan değişiklikler hatalı oldu") — artık SADECE gerçek bir fotoğraf
    # hiç bulunamadığında (Pexels de başarısızsa) düşülen saf prosedürel bokeh
    # dokusunda kullanılıyor; bir fotoğrafın üzerine o kadar dekoratif öğe
    # binmesi fotoğrafı bastırıyordu.
    #
    # AYRICA: art.jpg bir kez yazıldıktan sonra "bizim indirdiğimiz stok
    # fotoğraf" ile "kullanıcının elle koyduğu görsel" ayırt EDİLEMİYOR — ikisini
    # aynı düzene bağlamak, yeniden çalıştırmada tasarımın sessizce değişmesini
    # de engelliyor (bu daha önce gerçekten oldu).
    is_photo = bool(character_image or existing_art or fetched_stock_photo)
    try:
        if not has_art:
            shutil.copy(bg_path, art_path)
            print(f"  art{bg_ext} üretildi ({source_label})")
        # cover.png (16:9, YouTube uzun-format thumbnail'i) ve cover_vertical.png
        # (9:16, Shorts/TikTok/Instagram kapağı) AYRI üretiliyor — tek kare görsel
        # ikisinde de kenarlarda pillarbox/letterbox şeridine yol açıyordu
        # (kullanıcı geri bildirimiyle tespit edildi).
        for missing, out_path, (out_w, out_h), label in (
            (not has_cover, cover_path, COVER_SIZE_WIDE, "cover.png"),
            (not has_cover_vertical, cover_vertical_path, COVER_SIZE_TALL, "cover_vertical.png"),
        ):
            if not missing:
                continue
            if is_photo:
                # DJ set stili: başlık üstteki boş alana yaslı, altında ince
                # logo/marka satırı — fotoğrafın kendisi kompozisyonun asıl
                # unsuru kalıyor (karakter portresinde ayrıca büst siluetiyle
                # çakışmayı da önlüyor).
                _add_title_text(bg_path, out_path, title, y_center_ratio=0.13, out_w=out_w, out_h=out_h)
            else:
                _compose_cover_rich(bg_path, out_path, title, theme["accent"], out_w=out_w, out_h=out_h)
            print(f"  {label} üretildi ({title!r}, {source_label})")
    finally:
        for tmp_path in cleanup_paths:
            if os.path.isfile(tmp_path):
                os.remove(tmp_path)


def main():
    parser = argparse.ArgumentParser(
        description="Bir projede eksik olan cover.png/art.png dosyalarını tema rengine göre üretir."
    )
    parser.add_argument("--project", required=True, help="Proje klasörü (örn. projects/sarki-adi)")
    args = parser.parse_args()
    generate(args.project)


if __name__ == "__main__":
    main()
