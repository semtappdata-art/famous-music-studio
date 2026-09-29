"""DJ setlerinin uzun formatı için ücretsiz stok VİDEO havuzu indirir (Pexels).

Neden video, neden stok, neden AI değil:

  * Uzun setler 41-81 dakika. Tek bir `art.jpg` o süre boyunca ekranda sabit
    kalıyor ve sıkıcı (kullanıcı geri bildirimi). Backdrop'ın yavaş pan'i
    hareket veriyor ama görüntü ÇEŞİTLİLİĞİ vermiyor.
  * AI video bu işi çözemiyor: ölçüldü, Kling 3.0 std/sessiz 5 saniye =
    7,5 kredi. 45 kredilik bir bütçe 30 saniye benzersiz görüntü demek ve
    81 dakikada 162 kez tekrarlanır. Hiçbir bütçe 81 dakikayı AI ile
    dolduramaz.
  * Pexels'in ücretsiz VİDEO arşivi aynı anahtarla çalışıyor (stock_art.py
    ile aynı `stock_art_config.json`). Dört sorgu = 60 klip = ~22 dakika
    benzersiz 1080p görüntü, 81 dakikada yalnızca ~3,7 tekrar. Yani AI'dan
    44 kat fazla çeşitlilik, sıfır maliyet.

Lisans: Pexels License — ücretsiz, ticari kullanıma açık, atıf zorunlu değil.
Görüntü OLDUĞU GİBİ kullanılıyor; kimsenin benzerliği AI ile üretilmiyor, bu
yüzden DJ Famous'un onay kuralı (bkz. dj_sets/README.md) burada devreye
girmiyor.

Kullanım:
    python stock_video.py --set "dj_sets/Just Relax"
    python stock_video.py --set "dj_sets/Just Relax" --dry-run
"""

import argparse
import hashlib
import json
import os
import sys

import requests

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)

import config
from stock_art import _load_api_key

VIDEO_API = "https://api.pexels.com/videos/search"
PER_PAGE = 30
REQUEST_TIMEOUT = 30
# Havuz proje KLASÖRÜNDE değil, ortak bir önbellekte: aynı klipler birden
# fazla sette kullanılabilsin ve her sette yeniden indirilmesin. Setler
# 41-81 dakika, klipler ~20 sn — proje başına kopyalamak yüzlerce MB'ı
# gereksiz yere çoğaltırdı.
CACHE_DIR = os.path.join(REPO, ".stock_video_cache")

# Tek bir dosyada makul üst sınır. Pexels 4K sürümler de döndürüyor; burada
# 720p seçiliyor çünkü bu görüntü ekranda HAM gösterilmiyor: arka planda
# gblur=sigma=10 ile bulanıklaştırılıp kartın arkasında duruyor (bkz.
# arka_plan_kur). Blur'dan sonra 720p ile 1080p arasında görünür fark yok,
# ama dosya 3-4 kat küçük. Ölçüm: 1080p sürümlerde tek klip 12-60 MB ve
# indirme dakikalar sürüyordu — 34 klip için kabul edilemez.
MAX_GENISLIK = 1280

# Sorgular temaya göre. Hepsi ATMOSFER odaklı, insan/nesne odaklı DEĞİL —
# stock_art.py'deki aynı gerekçe: nesne aramaları katalog/ürün çekimi
# getiriyor, burada da yüz odaklı klipler setin ambient havasını bozuyor.
# SAHNE MODU sorguları (bkz. config.DJ_SAHNE_MODU). Buradaki hepsi GERÇEK
# performans görüntüsü - soyut ışık/duman değil, insan ve ekipman.
#
# YÜZ ARANMIYOR, bilerek: "dj hands", "silhouette", "back view", "close up
# turntable". DJ Famous gerçek ve isimli bir kişi; stok görüntüdeki BAŞKA
# birinin yüzünü onun yerine göstermek izleyiciyi yanıltır. Eller, siluet ve
# ekipman "gerçek insan çalıyor" hissini kimseyi taklit etmeden veriyor.
SAHNE_SORGULARI = [
    "dj hands mixer close up",
    "dj turntable close up night",
    "dj silhouette crowd lights",
    "dj booth back view club",
    "mixing console lights close up",
    "dj playing night club dark",
]

TEMA_SORGULARI = {
    "dj": [
        "neon lights bokeh night abstract",
        "city night traffic timelapse",
        "smoke slow motion dark background",
        "rain window night city lights",
        "dark club lights abstract",
        "night highway lights motion blur",
    ],
    "_varsayilan": [
        "abstract dark background motion",
        "bokeh lights slow motion",
        "clouds timelapse moody",
        "water reflection night lights",
    ],
}


def sorgular_icin(theme: str | None, set_style: str | None = None,
                  sahne: bool = False) -> list[str]:
    """Stok video arama sorgulari.

    `set_style` verilmisse (DJ setlerinde meta.json'daki alan) o stilin kendi
    sorgulari kullanilir - techno bir setin arkasinda deep house setiyle ayni
    goruntunun donmesi, iki seti gorsel olarak da ayirt edilemez yapiyordu.
    Stil tanimsizsa temaya, o da yoksa varsayilana dusulur.
    """
    stil = config.SET_STILLERI.get(set_style or "")
    if sahne:
        # Sahne sorgularini stilin KENDI sorgulariyla birlestiriyoruz.
        # Ilk surum burada erken donuyordu ve SET_STILLERI["video_sorgulari"]
        # tamamen olu koda donusmustu: DJ_SAHNE_MODU acikken deep_house ile
        # techno_chill ayni goruntuleri aliyordu. Oysa o alan tam da iki seti
        # gorsel olarak ayirmak icin eklenmisti (bkz. config.SET_STILLERI notu).
        ozel = list(stil.get("video_sorgulari") or []) if stil else []
        return list(SAHNE_SORGULARI) + ozel

    if stil and stil.get("video_sorgulari"):
        return list(stil["video_sorgulari"])
    return list(TEMA_SORGULARI.get(theme or "", TEMA_SORGULARI["_varsayilan"]))

def _dosya_adi(video_id, genislik) -> str:
    return "pexels_%s_%s.mp4" % (video_id, genislik)


def _en_uygun_dosya(video: dict) -> dict | None:
    """Videonun sürümleri arasından MAX_GENISLIK'i aşmayan en büyüğünü seçer."""
    en_iyi = None
    for f in video.get("video_files", []):
        if f.get("file_type") != "video/mp4":
            continue
        g = f.get("width") or 0
        if g > MAX_GENISLIK or g <= 0:
            continue
        if not en_iyi or g > en_iyi["width"]:
            en_iyi = f
    return en_iyi


def _indir(url: str, hedef: str) -> bool:
    """Videoyu indirir. Yarım dosya BIRAKMAZ — bir sonraki koşu onu geçerli
    sanıp bozuk bir klibi ffmpeg'e verirdi (stock_art._indir ile aynı gerekçe)."""
    gecici = hedef + ".part"
    try:
        with requests.get(url, stream=True, timeout=REQUEST_TIMEOUT) as r:
            r.raise_for_status()
            with open(gecici, "wb") as f:
                for parca in r.iter_content(chunk_size=1 << 16):
                    if parca:
                        f.write(parca)
        os.replace(gecici, hedef)
        return True
    except Exception:
        for y in (gecici, hedef):
            try:
                if os.path.isfile(y):
                    os.remove(y)
            except OSError:
                pass
        return False


def havuz_kur(theme: str | None, hedef_sure: float, seed: str = "",
              dry_run: bool = False, set_style: str | None = None,
              sahne: bool = False) -> dict:
    """`hedef_sure` saniyeyi karşılayacak kadar klip indirir.

    Hedef süre kadar İNDİRMİYOR: arka plan döngüye alınacağı (`-stream_loop
    -1`) için havuzun bir kesir olması yeterli.

    Kaç klip inecek, kliplerin TOPLAM süresine göre değil, kurulacak arka
    planın süresine göre hesaplanıyor — çünkü her klipten yalnızca KLIP_SN
    saniye kullanılıyor (bkz. arka_plan_kur). Klip başına net katkı
    KLIP_SN - GECIS_SN. Eskiden seçim kliplerin ham süresine bakıyordu ve
    48 saniyelik bir klip havuzu doldurmuş sayılıyordu; oysa o klipten
    videoya sadece 8 saniye giriyordu, yani gerçek arka plan hedeflenenin
    çok altında kalıp fazla tekrar ediyordu.
    """
    anahtar = _load_api_key()
    if not anahtar:
        return {"hata": "Pexels anahtarı yok (stock_art_config.json)"}

    os.makedirs(CACHE_DIR, exist_ok=True)
    sorgular = sorgular_icin(theme, set_style, sahne)

    adaylar = []
    for q in sorgular:
        try:
            r = requests.get(VIDEO_API, headers={"Authorization": anahtar},
                             params={"query": q, "per_page": PER_PAGE,
                                     "orientation": "landscape", "size": "medium"},
                             timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            veri = r.json()
        except Exception as e:
            print("  UYARI: '%s' sorgusu başarısız: %s" % (q, str(e)[:80]))
            continue
        for v in veri.get("videos", []):
            f = _en_uygun_dosya(v)
            if not f:
                continue
            adaylar.append({
                "id": v.get("id"), "sure": float(v.get("duration") or 0),
                "url": f["link"], "genislik": f["width"], "yukseklik": f["height"],
            })

    if not adaylar:
        return {"hata": "hiç video bulunamadı"}

    # Deterministik sıra: aynı set her çalıştırmada aynı havuzu alsın —
    # yeniden render'da arka planın sessizce değişmesi istenmiyor
    # (stock_art'taki _secim_indeksi ile aynı gerekçe).
    tohum = int(hashlib.sha256((seed or "").encode("utf-8")).hexdigest()[:8], 16)
    adaylar.sort(key=lambda a: hashlib.sha256(
        ("%d-%s" % (tohum, a["id"])).encode("utf-8")).hexdigest())

    # Arka plan hedefi: setin altıda biri, en az 3 en fazla 6 dakika.
    # Üst sınır bilinçli — 80 dakikalık bir sete 13 dakikalık benzersiz
    # görüntü kurmak ~120 klip indirmek demekti. 5 dakikalık bulanık bir
    # döngü, kartın arkasında tekrar ettiği fark edilmeyen bir aralık.
    arka_plan_hedefi = min(300.0, max(180.0, hedef_sure / 6.0))
    klip_basina = max(1.0, KLIP_SN - GECIS_SN)
    gereken_klip = int(arka_plan_hedefi / klip_basina) + 1

    # KLIP_SN'den kısa klipler arka_plan_kur tarafından zaten eleniyor —
    # onları indirip çöpe atmamak için burada da eleniyor.
    secilen = [a for a in adaylar if a["sure"] >= KLIP_SN + 1.0][:gereken_klip]
    toplam = len(secilen) * klip_basina + GECIS_SN

    if dry_run:
        return {"kuru": True, "aday": len(adaylar), "secilen": len(secilen),
                "gereken_klip": gereken_klip,
                "arka_plan_sn": round(toplam, 1),
                "hedef_sn": round(arka_plan_hedefi, 1),
                "sorgu": len(sorgular)}

    yollar, indirilen = [], 0
    for a in secilen:
        hedef = os.path.join(CACHE_DIR, _dosya_adi(a["id"], a["genislik"]))
        if os.path.isfile(hedef) and os.path.getsize(hedef) > 0:
            yollar.append(hedef)
            continue
        if _indir(a["url"], hedef):
            yollar.append(hedef)
            indirilen += 1

    return {"klip": len(yollar), "indirilen": indirilen,
            "arka_plan_sn": round(toplam, 1), "yollar": yollar}



# --- Klipleri tek bir sürekli arka plana dönüştürme -------------------------

GECIS_SN = 1.2       # klipler arası çapraz geçiş
KLIP_SN = 8.0        # her klipten kullanılacak süre


def _sure(yol: str) -> float:
    import subprocess
    o = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                        "-of", "csv=p=0", yol], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.strip()
    try:
        return float(o)
    except ValueError:
        return 0.0


# Tek bir ffmpeg cagrisinda en fazla kac girdi olsun. 44 klibi ayni anda
# vermek sistemi bellekten dusurdu (arka plan gorevi "low memory" ile
# oldurulda): ffmpeg her girdi icin ayri bir decoder + filtre zinciri aciyor
# ve gblur kare tamponu tutuyor, yani maliyet girdi sayisiyla dogru orantili.
# 8 girdi olculdu ve rahat calisiyor.
TOPLU_GIRDI = 8


def _segment_hazirla(klip: str, cikti: str, genislik: int, yukseklik: int,
                     sahne: bool = False, sure_sn: float = KLIP_SN) -> bool:
    """Tek bir klipten normalize edilmis KLIP_SN saniyelik parca uretir.

    `sure_sn` (bölüm dolgusu): baş/kuyruk aralığı KLIP_SN'den kısaysa dilim
    o kadar kesilir — sabit 8 sn kesmek aralığı TAŞIRIRDI (ölçüldü: 4 sn'lik
    başa 8 sn'lik parça, toplam süre 13.6'ya çıktı). Varsayılan KLIP_SN,
    mevcut çağıranlar etkilenmez.

    Klip basina AYRI bir ffmpeg calistiriliyor: boylece bellekte hicbir zaman
    tek bir decoder'dan fazlasi olmuyor. Onceden hepsi tek komutta yapiliyordu
    ve 44 klipte sistem bellegi tukendi.

    Ortadan kesiliyor (-ss girdiden ONCE, hizli arama): Pexels klipleri
    10-48 sn arasi degisiyor ve bas/son saniyeleri sik sik fade-in/out
    iceriyor; ortasi hem daha canli hem gecisleri temiz tutuyor.

    Blur + parlaklik + egri BURADA, bir kez pisiyor: bu goruntu kartin
    ARKASINDA duracak. Ham stok klip fazla dikkat cekiyor ve koyu art.jpg
    kartini yutuyor. Sabit gorsel arka planla (ffmpeg_utils.ensure_art_backdrop)
    ayni islem, ama blur daha hafif - hareketin okunmasi gerekiyor.
    """
    import subprocess
    orta = max(0.0, (_sure(klip) - sure_sn) / 2.0)
    # Sigma 1080p'ye gore tanimli (config), burada CALISMA yuksekligine
    # olcekleniyor. Ayni sayiyi 720p'de kullanmak %50 daha guclu blur
    # demekti - render_video goruntuyu 1080p'ye buyuttugunde blur da
    # buyuyor, yani olcekleme yapilmazsa dogrulanan gorunum bozulurdu.
    # Sahne modunda görüntü kartın arkasında değil, kadrajın kendisi -
    # bulanıklaştırmak onu yok etmek olurdu.
    if sahne:
        ham_sigma, egri = config.DJ_SAHNE_BLUR_SIGMA, config.DJ_SAHNE_EGRISI
    else:
        ham_sigma, egri = config.DJ_ARKA_PLAN_BLUR_SIGMA, config.DJ_ARKA_PLAN_EGRISI
    sigma = ham_sigma * yukseklik / 1080.0
    vf = ("scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,"
          "fps=%d,setsar=1,gblur=sigma=%.2f,eq=%s,curves=all='%s',format=yuv420p"
          % (genislik, yukseklik, genislik, yukseklik, config.FPS,
             sigma, config.DJ_ARKA_PLAN_PARLAKLIK, egri))
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
           "-ss", "%.2f" % orta, "-t", "%.2f" % sure_sn, "-i", klip,
           "-vf", vf, "-an",
           # ARA dosya: ultrafast. Bu parca en az bir kez daha kodlanacak
           # (grup birlestirme + nihai birlestirme), dolayisiyla burada
           # config.PRESET ("medium") kullanmak sadece bekleme suresi
           # ekliyordu - olculdu: 10 klip 837 saniye. Dusuk CRF ile kalite
           # zaten korunuyor, kayip nihai kodlamada gorunmuyor.
           "-c:v", "libx264", "-preset", "ultrafast", "-crf", "16",
           "-pix_fmt", "yuv420p", cikti]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        return False
    return os.path.isfile(cikti) and os.path.getsize(cikti) > 0


def _xfade_birlestir(parcalar: list, cikti: str, nihai: bool = False) -> bool:
    """Hazir parcalari capraz gecislerle birlestirir (en fazla TOPLU_GIRDI tane).

    Parcalar zaten ayni cozunurluk/fps/SAR'da oldugu icin burada normalize
    filtresi YOK - sadece xfade zinciri. offset, o ana kadar birikmis sureden
    gecis payi dusulerek hesaplaniyor; yanlis offset klipleri ust uste
    bindirip kareyi donduruyor.

    Sureler dosyadan OKUNUYOR, KLIP_SN varsayilmiyor: ikinci seviyede
    birlestirilen girdiler grup dosyalari ve onlarin sureleri farkli.
    """
    import subprocess
    if not parcalar:
        return False
    if len(parcalar) == 1:
        import shutil
        shutil.copyfile(parcalar[0], cikti)
        return True

    girdiler, filtreler = [], []
    for i, y in enumerate(parcalar):
        girdiler += ["-i", y]

    onceki = "0:v"
    birikmis = _sure(parcalar[0])
    for i in range(1, len(parcalar)):
        cikis = "x%d" % i
        offset = max(0.0, birikmis - GECIS_SN)
        filtreler.append(
            "[%s][%d:v]xfade=transition=fade:duration=%.2f:offset=%.2f[%s]"
            % (onceki, i, GECIS_SN, offset, cikis)
        )
        onceki = cikis
        birikmis += _sure(parcalar[i]) - GECIS_SN

    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    cmd += girdiler
    # Ara seviyeler ultrafast (nasilsa yeniden kodlanacak), yalnizca NIHAI
    # dosya config.PRESET/CRF ile - render bu dosyayi okuyacak.
    preset = config.PRESET if nihai else "ultrafast"
    crf = config.CRF if nihai else "16"
    cmd += ["-filter_complex", ";".join(filtreler), "-map", "[%s]" % onceki,
            "-an",
            "-c:v", "libx264", "-preset", preset, "-crf", crf,
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", cikti]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        return False
    return os.path.isfile(cikti) and os.path.getsize(cikti) > 0


def arka_plan_kur(klipler: list, cikti: str, genislik: int = 1280,
                  yukseklik: int = 720, sahne: bool = False) -> bool:
    """Klipleri capraz gecislerle tek bir arka plan videosunda birlestirir.

    UC GECIS - hepsi bellek sinirli:
      1. Her klip TEK BASINA normalize edilip KLIP_SN saniyeye kirpilir.
      2. Parcalar TOPLU_GIRDI'lik gruplar halinde xfade ile birlestirilir.
      3. Grup dosyalari yine xfade ile tek dosyaya birlestirilir.

    Onceden tek bir ffmpeg cagrisinda 44 girdi aciliyordu ve isletim sistemi
    sureci bellek yetersizliginden oldurdu. Agac seklinde birlestirmek ayni
    sonucu veriyor ama hicbir asamada TOPLU_GIRDI'den fazla decoder acilmiyor.

    Cikti, asil render'da `-stream_loop -1` ile donguye alinacak; bu yuzden
    setin TAM suresini doldurmaya calismiyoruz.

    xfade kullaniliyor (sert kesme degil): ambient bir sette her 8 saniyede
    bir sert kesme rahatsiz edici, capraz gecis akisi koruyor.

    Cikti 720p, 1080p DEGIL. Bu goruntu gblur=sigma=14 ile bulaniklastirilmis
    halde kartin arkasinda duruyor; render_video zaten kendi scale+crop'unu
    uyguladigi icin 1280x720'yi 1920x1080'e buyutuyor ve bulanik icerikte
    bu buyutme gorunmuyor. Kazanc her asamada 2,25 kat daha az piksel:
    blur, xfade ve kodlama maliyetinin tamami piksel sayisiyla dogru
    orantili. Kaynak klipler de zaten 720p iniyor (MAX_GENISLIK), yani
    1080p'ye cikmak zaten uydurma bir buyutmeydi.
    """
    import shutil
    import tempfile

    gecerli = [k for k in klipler if os.path.isfile(k) and _sure(k) >= KLIP_SN + 1.0]
    if len(gecerli) < 2:
        return False

    gecici = tempfile.mkdtemp(prefix="backdrop_", dir=os.path.dirname(os.path.abspath(cikti)))
    try:
        parcalar = []
        for i, k in enumerate(gecerli):
            y = os.path.join(gecici, "seg_%03d.mp4" % i)
            if _segment_hazirla(k, y, genislik, yukseklik, sahne):
                parcalar.append(y)
        if len(parcalar) < 2:
            return False

        gruplar = []
        for i in range(0, len(parcalar), TOPLU_GIRDI):
            g = os.path.join(gecici, "grup_%03d.mp4" % (i // TOPLU_GIRDI))
            if _xfade_birlestir(parcalar[i:i + TOPLU_GIRDI], g):
                gruplar.append(g)
            else:
                # Sessizce dusmesin: bir grup kaybolursa arka plan beklenenden
                # kisa olur ve sebebi hicbir yerde gorunmezdi.
                print("  UYARI: %d klipten olusan grup birlestirilemedi, atlandi"
                      % len(parcalar[i:i + TOPLU_GIRDI]))
        if not gruplar:
            return False

        # Grup sayisi TOPLU_GIRDI'yi asarsa bir seviye daha indir. 8'lik
        # gruplarla 8 seviye = 64 grup = 512 klip; pratikte hic gerekmiyor
        # ama havuz buyurse sessizce patlamasin.
        seviye = 0
        while len(gruplar) > TOPLU_GIRDI:
            seviye += 1
            ust = []
            for i in range(0, len(gruplar), TOPLU_GIRDI):
                g = os.path.join(gecici, "ust%d_%03d.mp4" % (seviye, i // TOPLU_GIRDI))
                if _xfade_birlestir(gruplar[i:i + TOPLU_GIRDI], g):
                    ust.append(g)
            if not ust:
                return False
            gruplar = ust

        return _xfade_birlestir(gruplar, cikti, nihai=True)
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


ARKA_PLAN_ADI = "backdrop.mp4"


def set_sesi(set_dir: str) -> str | None:
    for ad in ("audio.wav", "audio.mp3", "audio.m4a"):
        y = os.path.join(set_dir, ad)
        if os.path.isfile(y):
            return y
    return None


def set_suresi(ses_yolu: str) -> float:
    import subprocess
    o = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                        "-of", "csv=p=0", ses_yolu], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.strip()
    try:
        return float(o)
    except ValueError:
        return 0.0


SAHNE_PARTI_ADI = "sahne_parti.json"


def bolum_sahneleri(set_dir: str):
    """Bölüm-sahne eşleşmesi: [(bas_sn, bit_sn, dosya)] sıralı liste.

    `sahne_parti.json` + `bolumler.json`'dan türetiliyor; dosyası diskte
    OLMAYAN sahne listeye GİRMEZ. Herhangi bir girdi eksik/bozuksa [] döner
    (çağıran havuz yoluna düşer — bu fonksiyon asla üretimi durdurmaz).
    """
    try:
        with open(os.path.join(set_dir, SAHNE_PARTI_ADI), encoding="utf-8") as f:
            spec = json.load(f)
        with open(os.path.join(set_dir, "bolumler.json"), encoding="utf-8") as f:
            bolumler = json.load(f)["parcalar"]
    except (OSError, ValueError, KeyError):
        return []
    baslar = {}
    for p in bolumler:
        try:
            baslar[p["ad"]] = float(p["bas"])
        except (KeyError, TypeError, ValueError):
            return []
    ses = set_sesi(set_dir)
    sure = set_suresi(ses) if ses else 0.0
    if sure <= 0:
        return []
    cikti = []
    for s in spec.get("sahneler", []):
        try:
            bas = baslar[s["bas"]]
            bit = baslar[s["bitis"]] if s.get("bitis") else sure
        except KeyError:
            continue
        yol = os.path.join(set_dir, s["dosya"])
        if bit > bas and os.path.isfile(yol):
            cikti.append((bas, bit, yol))
    cikti.sort()
    return cikti


def _sahne_segment_hazirla(gorsel: str, sure_sn: float, cikti: str,
                           genislik: int, yukseklik: int, sahne: bool = False) -> bool:
    """Durağan sahne görselinden SÜREli normalize parça üretir.

    `_segment_hazirla` ile AYNI derecelendirme (scale/crop/fps/blur/eq/curves)
    — havuz klipleriyle yan yana durunca renk farkı olmasın diye. Tek fark:
    girdi klip değil `-loop 1` ile döndürülen görsel. Ara dosya olduğu için
    ultrafast/crf16 (arka_plan_kur'un kuralı).
    """
    import subprocess
    if sure_sn <= 0:
        return False
    if sahne:
        ham_sigma, egri = config.DJ_SAHNE_BLUR_SIGMA, config.DJ_SAHNE_EGRISI
    else:
        ham_sigma, egri = config.DJ_ARKA_PLAN_BLUR_SIGMA, config.DJ_ARKA_PLAN_EGRISI
    sigma = ham_sigma * yukseklik / 1080.0
    vf = ("scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,"
          "fps=%d,setsar=1,gblur=sigma=%.2f,eq=%s,curves=all='%s',format=yuv420p"
          % (genislik, yukseklik, genislik, yukseklik, config.FPS,
             sigma, config.DJ_ARKA_PLAN_PARLAKLIK, egri))
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
           "-loop", "1", "-t", "%.2f" % sure_sn, "-i", gorsel,
           "-vf", vf, "-an",
           "-c:v", "libx264", "-preset", "ultrafast", "-crf", "16",
           "-pix_fmt", "yuv420p", cikti]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        return False
    return os.path.isfile(cikti) and os.path.getsize(cikti) > 0


def _video_segment_hazirla(klip: str, sure_sn: float, cikti: str,
                           genislik: int, yukseklik: int, sahne: bool = False) -> bool:
    """Video kaynaktan SÜREli normalize parça (bölüm aralığını doldurur).

    Kaynak aralıktan kısaysa `-stream_loop -1` ile döndürülür; uzunsa
    ortasından alınır. Derecelendirme `_segment_hazirla` ile AYNI (renk farkı
    olmasın). Kalabalık tepe bölümü gibi stok parti klipleri için."""
    import subprocess
    if sure_sn <= 0:
        return False
    ham = _sure(klip)
    if ham <= 0:
        return False
    if sahne:
        ham_sigma, egri = config.DJ_SAHNE_BLUR_SIGMA, config.DJ_SAHNE_EGRISI
    else:
        ham_sigma, egri = config.DJ_ARKA_PLAN_BLUR_SIGMA, config.DJ_ARKA_PLAN_EGRISI
    sigma = ham_sigma * yukseklik / 1080.0
    vf = ("scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,"
          "fps=%d,setsar=1,gblur=sigma=%.2f,eq=%s,curves=all='%s',format=yuv420p"
          % (genislik, yukseklik, genislik, yukseklik, config.FPS,
             sigma, config.DJ_ARKA_PLAN_PARLAKLIK, egri))
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    if ham < sure_sn:
        cmd += ["-stream_loop", "-1"]
    else:
        cmd += ["-ss", "%.2f" % max(0.0, (ham - sure_sn) / 2.0)]
    cmd += ["-t", "%.2f" % sure_sn, "-i", klip,
            "-vf", vf, "-an",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "16",
            "-pix_fmt", "yuv420p", cikti]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        return False
    return os.path.isfile(cikti) and os.path.getsize(cikti) > 0


def bolum_backdrop_kur(set_dir: str, havuz_yollari: list, cikti: str,
                       genislik: int = 1280, yukseklik: int = 720,
                       sahne: bool = False) -> bool:
    """Bölüm zamanlı backdrop: sahne aralıkları görselden, boşluklar havuzdan.

    Kapsanmayan baş/kuyruk (ör. rooftop'lu ilk bölüm) havuz klipleriyle
    KLIP_SN'lik dilimler hâlinde dolduruluyor. Birleştirme `_xfade_birlestir`
    ile (TOPLU_GIRDI gruplu — arka_plan_kur ile aynı ağaç). Sahne dosyası
    YOKSA buraya hiç girilmez (çağıran `bolum_sahneleri()` boşken atlar).
    """
    import shutil
    import tempfile

    araliklar = bolum_sahneleri(set_dir)
    if not araliklar:
        return False
    ses = set_sesi(set_dir)
    sure = set_suresi(ses) if ses else 0.0
    if sure <= 0:
        return False
    havuz = [k for k in havuz_yollari
             if os.path.isfile(k) and _sure(k) >= KLIP_SN + 1.0]
    if not havuz:
        return False

    gecici = tempfile.mkdtemp(prefix="bolum_", dir=os.path.dirname(os.path.abspath(cikti)))
    try:
        parcalar = []
        hi = 0

        def havuz_doldur(bit_sn: float, bas_sn: float) -> bool:
            nonlocal hi
            while bas_sn < bit_sn - 0.5:
                dilim = min(KLIP_SN, bit_sn - bas_sn)
                if dilim < GECIS_SN + 0.5:
                    # Kısa kuyruk kırıntısı atlanır (≤1.7 sn): render `-t`
                    # ile kesiyor, bu boşluk orada eriyor.
                    break
                y = os.path.join(gecici, "havuz_%03d.mp4" % len(parcalar))
                if not _segment_hazirla(havuz[hi % len(havuz)], y,
                                         genislik, yukseklik, sahne,
                                         sure_sn=dilim):
                    return False
                parcalar.append(y)
                hi += 1
                bas_sn += dilim - GECIS_SN
            return True

        bas_sn = 0.0
        for i, (sbas, sbit, yol) in enumerate(araliklar):
            if sbas > bas_sn and not havuz_doldur(sbas, bas_sn):
                return False
            y = os.path.join(gecici, "sahne_%02d.mp4" % i)
            if yol.lower().endswith(".mp4"):
                ok = _video_segment_hazirla(yol, sbit - sbas, y,
                                              genislik, yukseklik, sahne)
            else:
                ok = _sahne_segment_hazirla(yol, sbit - sbas, y,
                                              genislik, yukseklik, sahne)
            if not ok:
                return False
            parcalar.append(y)
            bas_sn = sbit - GECIS_SN
        if bas_sn < sure - 0.5 and not havuz_doldur(sure, bas_sn):
            return False
        if len(parcalar) < 2:
            return False

        gruplar = []
        for i in range(0, len(parcalar), TOPLU_GIRDI):
            g = os.path.join(gecici, "grup_%03d.mp4" % (i // TOPLU_GIRDI))
            if _xfade_birlestir(parcalar[i:i + TOPLU_GIRDI], g):
                gruplar.append(g)
            else:
                print("  UYARI: bölüm backdrop grubu birleştirilemedi, atlandı")
        if not gruplar:
            return False
        while len(gruplar) > TOPLU_GIRDI:
            ust = []
            for i in range(0, len(gruplar), TOPLU_GIRDI):
                g = os.path.join(gecici, "ust_%03d.mp4" % (i // TOPLU_GIRDI))
                if _xfade_birlestir(gruplar[i:i + TOPLU_GIRDI], g):
                    ust.append(g)
            if not ust:
                return False
            gruplar = ust
        return _xfade_birlestir(gruplar, cikti, nihai=True)
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


def set_icin_arka_plan(set_dir: str, zorla: bool = False) -> str | None:
    """Bir DJ seti için `<set>/backdrop.mp4` üretir; yolunu döner.

    Zaten varsa dokunmuyor (`zorla=True` hariç) — arka plan setin kimliğinin
    parçası, yeniden render'da sessizce değişmemeli. `render.py` bu dosyayı
    varsa kendiliğinden kullanıyor, yoksa eski bulanık art.jpg arka planına
    düşüyor; yani bu adımın başarısız olması render'ı DURDURMUYOR.
    """
    cikti = os.path.join(set_dir, ARKA_PLAN_ADI)
    sahne = bool(getattr(config, "DJ_SAHNE_MODU", False))
    # Uretim parmak izi: backdrop hangi ayarlarla pisirildiyse onu yaninda
    # tutuyoruz. Ilk surum sadece "dosya var mi" diye bakiyordu; sahne modu
    # SONRADAN eklendigi icin, mod oncesi uretilmis bulanik bir backdrop
    # sahne modunda oldugu gibi kullanilirdi - kart yok, tam ekran BULANIK
    # goruntu, yani sahne modunun tam tersi.
    imza = {
        "sahne": sahne,
        "sigma": config.DJ_SAHNE_BLUR_SIGMA if sahne else config.DJ_ARKA_PLAN_BLUR_SIGMA,
        "egri": config.DJ_SAHNE_EGRISI if sahne else config.DJ_ARKA_PLAN_EGRISI,
        "klip_sn": KLIP_SN, "gecis_sn": GECIS_SN,
    }
    # Sahne parmak izi YALNIZCA sahne dosyası varken ekleniyor: yokken eski
    # havuz backdrop'u aynen geçerli, sırf imza değişti diye bir kez boşa
    # yeniden kurmayalım. Dosya belirince/güncellenince anahtar değişir.
    _sahne_fp = [(b, e, os.path.basename(y), os.path.getsize(y))
                 for b, e, y in bolum_sahneleri(set_dir)]
    if _sahne_fp:
        imza["sahneler"] = _sahne_fp
    imza_yolu = os.path.join(set_dir, "backdrop.json")
    if os.path.isfile(cikti) and os.path.getsize(cikti) > 0 and not zorla:
        eski_imza = None
        try:
            with open(imza_yolu, "r", encoding="utf-8") as f:
                eski_imza = json.load(f)
        except (OSError, ValueError):
            pass
        if eski_imza == imza:
            return cikti
        print("  backdrop.mp4 farkli ayarlarla uretilmis, yeniden kuruluyor")

    mp = os.path.join(set_dir, "meta.json")
    meta = {}
    if os.path.isfile(mp):
        with open(mp, "r", encoding="utf-8") as f:
            meta = json.load(f)

    ses = set_sesi(set_dir)
    if not ses:
        return None
    sure = set_suresi(ses)
    if sure <= 0:
        return None

    sahne = bool(getattr(config, "DJ_SAHNE_MODU", False))
    sonuc = havuz_kur(meta.get("theme"), sure, seed=meta.get("title", ""),
                      set_style=meta.get("set_style"), sahne=sahne)
    if sonuc.get("hata") or not sonuc.get("yollar"):
        print("  stok video havuzu kurulamadı: %s" % sonuc.get("hata", "klip yok"))
        return None

    # Bölüm-sahne yolu (sahne_parti.json + dosyalar varsa): sahne aralıkları
    # görsellerden, baş/kuyruk havuzdan, tek TAM SÜRELİ dosya. Başarısız
    # olursa sessizce havuz yoluna düşer (render `-t` ile kesiyor, süre
    # kayması zararsız) — bu adım render'ı DURDURMUYOR.
    if bolum_sahneleri(set_dir):
        if bolum_backdrop_kur(set_dir, sonuc["yollar"], cikti, sahne=sahne):
            try:
                with open(imza_yolu, "w", encoding="utf-8") as f:
                    json.dump(imza, f, ensure_ascii=False, indent=2)
            except OSError:
                pass
            return cikti
        print("  bölüm backdrop kurulamadı, havuz yoluna düşülüyor")

    if not arka_plan_kur(sonuc["yollar"], cikti, sahne=sahne):
        print("  arka plan videosu birleştirilemedi")
        return None
    try:
        with open(imza_yolu, "w", encoding="utf-8") as f:
            json.dump(imza, f, ensure_ascii=False, indent=2)
    except OSError:
        pass
    return cikti


def main():
    ap = argparse.ArgumentParser(description="DJ seti için stok video havuzu indirir.")
    ap.add_argument("--set", required=True, help="Set klasörü (örn. 'dj_sets/Just Relax')")
    ap.add_argument("--dry-run", action="store_true", help="İndirme, ne olacağını yaz")
    ap.add_argument("--build", action="store_true",
                    help="İndir + birleştir: <set>/backdrop.mp4 üret")
    ap.add_argument("--force", action="store_true",
                    help="--build ile: backdrop.mp4 varsa bile yeniden üret")
    args = ap.parse_args()

    if args.build:
        yol = set_icin_arka_plan(args.set, zorla=args.force)
        print("backdrop: %s" % (yol or "ÜRETİLEMEDİ"))
        return

    mp = os.path.join(args.set, "meta.json")
    meta = {}
    if os.path.isfile(mp):
        with open(mp, "r", encoding="utf-8") as f:
            meta = json.load(f)

    import subprocess
    ses = None
    for ad in ("audio.wav", "audio.mp3", "audio.m4a"):
        y = os.path.join(args.set, ad)
        if os.path.isfile(y):
            ses = y
            break
    sure = 0.0
    if ses:
        o = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries",
                            "format=duration", "-of", "csv=p=0", ses],
                           capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.strip()
        sure = float(o) if o else 0.0

    print("set   : %s" % os.path.basename(os.path.normpath(args.set)))
    print("tema  : %s" % meta.get("theme"))
    print("süre  : %.1f dakika" % (sure / 60))
    s = havuz_kur(meta.get("theme"), sure, seed=meta.get("title", ""),
                  dry_run=args.dry_run, set_style=meta.get("set_style"),
                  sahne=bool(getattr(config, "DJ_SAHNE_MODU", False)))
    print(json.dumps({k: v for k, v in s.items() if k != "yollar"},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
