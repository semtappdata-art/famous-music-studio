# -*- coding: utf-8 -*-
"""Yayınlanmış şarkılardan uzun format derleme üretir — SIFIR Suno maliyetiyle.

NEDEN VAR (2026-09-11 piyasa araştırması):

1. **Suno kotası projenin gerçek tavanı.** Aylık indirme sınırlı ve hem katalog
   hem DJ setleri aynı kotadan besleniyor. Derleme, kotaya HİÇ dokunmadan uzun
   format üreten tek kaldıraç: malzeme zaten üretilmiş ve yayınlanmış.

2. **Uzun format izlenme süresinde çok daha verimli.** Kanalın kendi ölçümü:
   video başına 85 dk (şarkı) / 689 dk (DJ seti). Derleme, şarkı hattını uzun
   format tarafına taşıyor.

3. **"Toplu üretim" görüntüsünü azaltıyor — asıl sebep bu.** YouTube
   15 Temmuz 2025'te "repetitious content" politikasını "inauthentic content"
   olarak yeniden adlandırdı: "toplu üretilmiş, jenerik... yaratıcının özgün
   bakış açısını eklemeyen AI içeriği" para kazanmaya uygun değil; yaptırım
   kanal kapatmaya kadar gidiyor. Günde 2 şarkı × 6 tarz bu tanıma en çok
   benzeyen desen. Derleme KÜRATÖRLÜK katmanı ekliyor: seçim, sıralama,
   bölüm başlıkları.

TASARIM KARARLARI:

* Yalnızca YAYINDA olan şarkılar. Liste dışı (unlisted) olanlar atlanıyor —
  'Küllerimden Geç' gibi kopyalar derlemeye girmemeli.
* Sıralama izlenmeye göre, EN ÇOK İZLENEN ÖNDE. Derlemede ilk 30 saniye
  izleyiciyi tutar ya da kaybeder; en güçlü parçayı sona saklamak riskli.
* Parçalar arası çapraz geçiş (sert kesme değil) — DJ setindeki gerekçeyle aynı.
* `state.json`'da TELİF İŞARETİ (`telif_araliklari` YA DA `telif_eser`,
  bkz. `TELIF_ISARETLERI`) taşıyan şarkılar TAMAMEN atlanıyor.
  Derleme yeniden yayın demek; telifli malzemeyi ikinci kez yayınlamak
  City Pulse'ta yaşananı tekrarlamak olur.
  GARANTİYİ DOĞRULAYAN TEST: `tests/test_derleme_telif_kapisi.py`
  (bu satır bir GARANTİ; testsiz yazılmış bir garanti bu depoda
  `dj_famous_process.py`'nin maskeleyici yorumuyla aynı sınıfa girer —
  bkz. CLAUDE.md).
* Bölüm zaman damgaları üretiliyor (`derleme_liste`). YouTube bunları açıklamada
  bölüm (chapter) olarak okuyor; hem gezinmeyi hem küratörlük sinyalini artırıyor.

Kullanım:
    python derleme.py --ad "Arabesk Gece" --tema arabesk
    python derleme.py --ad "En Çok Dinlenenler" --en-iyi --hedef-dk 40
    python derleme.py --ad "..." --en-iyi --dry-run
"""

import argparse
import collections
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

import config
# md5 + boyut ön filtresi `uyumluluk.py`'den İÇE AKTARILIYOR, KOPYALANMIYOR:
# aynı hash'i iki yerde ayrı ayrı hesaplayan kod, ikisi ayrıştığında sessizce
# farklı cevap verir. (Aynı karar `upload/youtube_playlists.py`'de de verildi:
# oradaki enerji sıralaması `derleme._enerji`'yi kopyalamıyor, içe aktarıyor.)
import uyumluluk

# Kok yollar MUTLAK. Goreli birakilirsa yanlis cwd'de os.path.isdir False doner,
# fonksiyon SESSIZCE bos sonuc uretir (adaylar() bos liste -> "yeterli sarki yok").
# Ayni duzeltme bugun dj_tarama_kontrol.py ve upload/youtube_analytics.py'de de
# yapildi; derleme.py Gorev Zamanlayici'dan/baska bir klasorden de cagrilabiliyor.
_KOK = os.path.dirname(os.path.abspath(__file__))
KAYNAK = os.path.join(_KOK, "projects")
HEDEF_KOK = os.path.join(_KOK, "derlemeler")
AUDIO_ADLARI = ("audio.wav", "audio.mp3", "audio.m4a")

# Parçalar arası çapraz geçiş. 2 sn ile başlamıştı; 6 sn'ye çıkarıldı çünkü
# 2 saniye "yapıştırma", 6 saniye "miks". YouTube'un yeniden kullanım
# politikasının testi: "izleyici orijinal ile senin videonun arasında ANLAMLI
# BİR FARK ayırt edebiliyor mu". Politikanın saydığı katkı türlerinden biri
# "substantive editing ... unique to your channel"; 2 saniyelik acrossfade
# o eşiği karşılamıyor, gerçek üst üste binme karşılıyor.
GECIS_SN = 6.0

# TELİF KAPISI — bir kaydı derlemeden ÇIKARMAYA TEK BAŞINA yeten state.json
# alanları. Koruma testi: `tests/test_derleme_telif_kapisi.py`.
#
# NEDEN İKİ ALAN (2026-09-12'de eklendi; eskiden SADECE `telif_araliklari`):
# bu iki alan ELLE yazılıyor — depoda hiçbir kod onları üretmiyor
# (`dj_tarama_kontrol.py` karantina kurar ama telif_* alanlarını YAZMAZ),
# yani kapı "operatör HER İKİ yarısını da doldurur" KONVANSİYONUNA
# dayanıyordu. Content ID eşleşmesi eserin TAMAMINI kapsadığında ya da
# aralıklar henüz çıkarılmadığında `telif_eser` tek başına yazılır ve o
# hâlde şarkı derlemeye GİRERDİ. Bu tam olarak aynı dosyadaki
# `_md5_tekrarini_ele`'nin kapattığı boşluk: oradaki koruma da
# "kopya olan taraf ELLE liste dışına alınmış" konvansiyonuna dayanıyordu.
# `uyumluluk.kontrol()`'ün kendi mesajı bile yarımlığı öngörüyor
# (`durum.get("telif_eser") or "eser adı yok"`) — tersi de aynı ölçüde olur.
#
# MALİYET ASİMETRİK, karar bu yüzden kolay: yanlış pozitifin bedeli bir
# şarkının bir derlemede EKSİK kalması (üstelik log'a düşerek); yanlış
# negatifin bedeli, City Pulse Set'in HÂLÂ AÇIK olan telif itirazının
# üstüne İKİNCİ bir ihlal eklemek.
#
# `telif_notu` BİLEREK LİSTEDE YOK: o serbest metin bir alan ve "kontrol
# edildi, telif yok" gibi TERSİ bir cümle de taşıyabilir; kapıyı bir
# notun varlığına bağlamak "işaret" ile "yorum"u karıştırmak olurdu.
TELIF_ISARETLERI = ("telif_araliklari", "telif_eser")

# Derleme kapagi icin stok gorsel sorgulari. Tek sarkininkinden farkli:
# derleme bir ALBUM hissi vermeli, tek bir anin fotografi degil.
DERLEME_ART_SORGU = {
    "arabesk": "rainy night window city lights melancholy",
    "hiphop": "urban night street neon underpass",
    "pop": "neon lights bokeh night party",
    "elektronik": "abstract light trails dark motion",
    "akustik": "warm lamp light wooden room evening",
    "rock": "dark stage smoke lights concert",
    "_karma": "night city skyline lights long exposure",
}


def _sure(yol: str) -> float:
    o = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", yol], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.strip()
    try:
        return float(o)
    except ValueError:
        return 0.0


def _ses_bul(proje: str):
    for n in AUDIO_ADLARI:
        y = os.path.join(proje, n)
        if os.path.isfile(y):
            return y
    return None


def _telif_isareti(st: dict) -> str:
    """state.json'da telif işareti varsa ALAN ADINI, yoksa "" döndürür.

    BOŞ LİSTE (`[]`) İŞARET SAYILMAZ — bilerek: `state_io` göçünde
    temizlenmiş bir kayıt tam olarak böyle görünüyor
    (`{"telif_araliklari": []}`, bkz. `tests/test_state_io.py`) ve
    `uyumluluk.kontrol()` de aynı truthiness kuralını kullanıyor. "Aralık
    listesi boş" = "eşleşme yok"; bunu işaret saymak temizlenmiş her kaydı
    kalıcı olarak derleme dışında bırakırdı.

    BOZUK TİP (ör. alanın liste yerine düz metin olması) İŞARET SAYILIR:
    truthy olduğu için kapı KAPANIR. Doğru yön bu — "bu alanı okuyamıyorum"
    ile "temiz" aynı şey değil (`uyumluluk.py`'nin `DurumBozuk` kararıyla
    aynı gerekçe).
    """
    for alan in TELIF_ISARETLERI:
        if st.get(alan):
            return alan
    return ""


def _md5_tekrarini_ele(havuz: list) -> list:
    """Aynı sesi (md5) taşıyan adaylardan SADECE BİRİNİ bırakır.

    NEDEN VAR (2026-09-11): `adaylar()` kopyayı yalnızca
    `youtube_privacy in ("unlisted", "private")` filtresiyle eliyordu — yani
    koruma tamamen "kopya olan taraf ELLE liste dışına alınmış" KONVANSİYONUNA
    bağlıydı. `uyumluluk.py`'deki md5 tekrar kapısı bugün sıkılaştırıldı ve
    bundan SONRA iki public kopyanın oluşmasını engelliyor, ama MEVCUT/GEÇMİŞ
    veri için hiçbir garanti vermiyor: bir gün o konvansiyon uygulanmazsa
    (ya da `state.json` bozulup `youtube_privacy` kaybolursa) aynı kayıt
    derlemeye İKİ KEZ girerdi. Bu tam olarak YouTube'un "önemli değişiklik
    yapılmadan bir araya getirilmiş şarkı koleksiyonu" tarifidir — ve
    derlemenin var olma sebebi (bkz. modül başlığı) tam olarak o
    "inauthentic content" politikasına karşı KÜRATÖRLÜK göstermek. Yani bu
    boşluk, derlemenin kendi amacını tersine çeviriyordu.

    HANGİSİ KALIR — İLK YAYINLANAN (`youtube_uploaded_at`), eşitse/tarih
    yoksa alfabetik (deterministik olsun diye). İZLENME SAYISI BİLEREK
    KULLANILMIYOR: bu deponun kendi vakası tam tersini söylüyor —
    'Küllerimden Geç' (7 Eylül, İKİNCİ yükleme) 182 izlenmeyle orijinali
    'Yeniden Doğacağım'ı (1 Eylül, 146) GEÇİYOR. "Çok izlenen kalsın" kuralı
    kanalın asıl kaydı olarak KOPYAYI seçerdi; üstelik izlenme bir METRİK,
    kanonik kayıt ise bir KİMLİK sorusu (`sec()`in docstring'indeki aynı
    gerekçe). Orijinali tutmak ayrıca playlist/link/açıklama geçmişini de
    bozmaz.

    ELEME SESSİZ DEĞİL: stderr'e bir satır basılıyor. Sessiz bir eleme,
    sonradan "bu şarkı derlemede neden yok" sorusunu cevapsız bırakır —
    bu deponun en pahalı hata sınıfı tam olarak "sessizce bir şey yapmayan
    koruma" (bkz. CLAUDE.md). stdout DEĞİL stderr: `--dry-run` çıktısı
    (sıra/zaman tablosu) boru hattına verilebilir olmalı.

    YAN ETKİLER — BİLEREK DÜZELTİLMEDİ:

    * `hedef_dk`: havuz küçülünce `sec()` hedef süreye ulaşamayabilir; o zaman
      elindeki HER parçayı alıp daha kısa bir derleme üretir (döngü zaten
      `toplam >= hedef_dk*60` ile duruyor, ulaşamazsa doğal olarak biter) ve
      2 parçanın altına düşerse `uret()` zaten "yeterli şarkı yok" diyor.
      Bunu telafi etmek YANLIŞ olurdu: elenen parça hedefe zaten SAHTE bir
      katkı yapıyordu — dakikayı dolduruyor ama derlemenin tek savunması olan
      küratörlüğü yok ediyordu. Kısa ama tekrarsız bir derleme, hedef süreyi
      aynı kaydı iki kez çalarak tutturan bir derlemeden iyidir.
    * `_enerji()` / enerji eğrisi: iki birebir aynı dosyanın RMS'i de birebir
      aynı çıkar, yani eğri sıralamasında YAN YANA düşerlerdi — dinleyici aynı
      şarkıyı arka arkaya iki kez duyardı (tam olarak `upload/youtube_playlists`
      `_shorts` listesini ayırma gerekçesi). Eleme bunu düzeltiyor, bozmuyor;
      üstelik bir librosa yüklemesi de eksiliyor. Eğri MANTIĞI değişmiyor.
    """
    # Boyut ÖN FİLTRESİ — `uyumluluk.py`'deki desenin AYNISI (orada
    # `os.path.getsize(bs) != benim_boyut: continue`): md5 pahalı, boyut
    # bedava. Burada N adaylı hâli: önce boyuta göre grupla, md5'i SADECE
    # boyutu birden fazla adayda tekrarlanan gruplarda hesapla. Bugünkü
    # gerçek havuzda 17 dosyanın 17'si tekil boyutta — yani md5 HİÇ
    # hesaplanmıyor, koruma pratikte bedava.
    boyut_gruplari = collections.defaultdict(list)
    for p in havuz:
        try:
            boyut_gruplari[os.path.getsize(p["ses"])].append(p)
        except OSError as e:
            # OSError SADECE bu adayın md5 kontrolünü düşürür, aday havuzda
            # KALIR — ama sessizce değil. (uyumluluk.py'deki aynı karar:
            # kilitli/okunamayan bir dosya yüzünden kontrolün TAMAMEN devre
            # dışı kalması ve kimsenin bunu bilmemesi asıl tehlike.)
            print("derleme: '%s' boyutu okunamadı (%s) — md5 tekrar kontrolü "
                  "bu aday için YAPILAMADI" % (p["ad"], e), file=sys.stderr)

    # Tekrar eden md5'in hangi adayının KALACAĞINI seçen anahtar (yukarıdaki
    # gerekçe). `yuklendi` ISO-8601 metin, sözlüksel sıralaması = zaman sırası.
    def _oncelik(p):
        return (p.get("yuklendi") or "9999", p["ad"])

    elenen = set()
    for boyut, grup in boyut_gruplari.items():
        if len(grup) < 2:
            continue                       # boyut tekil -> md5'e hiç bakma
        md5_gruplari = collections.defaultdict(list)
        for p in grup:
            try:
                md5_gruplari[uyumluluk._md5(p["ses"])].append(p)
            except OSError as e:
                print("derleme: '%s' sesi okunamadı (%s) — md5 tekrar kontrolü "
                      "bu aday için YAPILAMADI" % (p["ad"], e), file=sys.stderr)
        for imza, ayni in md5_gruplari.items():
            if len(ayni) < 2:
                continue
            kalan = min(ayni, key=_oncelik)
            for p in ayni:
                if p is kalan:
                    continue
                elenen.add(id(p))
                print("derleme: '%s' derlemeden ELENDİ — sesi '%s' ile BİREBİR "
                      "AYNI (md5 %s, %d bayt); aynı kayıt bir derlemede iki kez "
                      "geçemez. Kalan: ilk yayınlanan."
                      % (p["ad"], kalan["ad"], imza[:8], boyut), file=sys.stderr)

    return [p for p in havuz if id(p) not in elenen]


def adaylar(tema: str | None = None) -> list:
    """Derlemeye girebilecek şarkılar: yayında, sesi var, telif işareti yok."""
    liste = []
    if not os.path.isdir(KAYNAK):
        return liste
    for ad in sorted(os.listdir(KAYNAK)):
        proje = os.path.join(KAYNAK, ad)
        sp, mp = os.path.join(proje, "state.json"), os.path.join(proje, "meta.json")
        if not (os.path.isfile(sp) and os.path.isfile(mp)):
            continue
        # `with`: json.load(open(...)) dosya tanicisini sizdiriyordu (CPython'da
        # refcount temizliyor ama garanti degil, 100+ projede acik tanitici birikir).
        # `except OSError` da sart: izin/okuma hatasi ValueError DEGIL, eskiden tek
        # bozuk/kilitli dosya adaylar()'in tamamini dusuruyordu.
        try:
            with open(sp, encoding="utf-8") as f:
                st = json.load(f)
            with open(mp, encoding="utf-8") as f:
                m = json.load(f)
        except (ValueError, OSError):
            continue
        if not st.get("youtube_video_id"):
            continue                      # henüz yayınlanmamış
        if st.get("youtube_privacy") in ("unlisted", "private"):
            continue                      # liste dışı/kopya — derlemeye girmez
        # TELİF KAPISI (garanti: derlemeler/README.md + modül başlığı;
        # koruma testi: tests/test_derleme_telif_kapisi.py)
        _isaret = _telif_isareti(st)
        if _isaret:
            # SESSİZ DEĞİL — `_md5_tekrarini_ele`'deki aynı gerekçe: sessiz bir
            # eleme "bu şarkı derlemede neden yok" sorusunu cevapsız bırakır ve
            # bu deponun en pahalı hata sınıfı tam olarak sessiz koruma
            # (bkz. CLAUDE.md). stdout DEĞİL stderr: `--dry-run` tablosu boru
            # hattına verilebilir olmalı.
            print("derleme: '%s' derlemeye ALINMADI — telif işareti var (%s: %r); "
                  "telifli malzemeyi ikinci kez yayınlamak City Pulse'ta "
                  "yaşananı tekrarlar." % (ad, _isaret, st.get(_isaret)),
                  file=sys.stderr)
            continue                      # telif eşleşmesi var, yeniden yayınlama
        if tema and m.get("theme") != tema:
            continue
        ses = _ses_bul(proje)
        if not ses:
            continue
        liste.append({
            "ad": ad, "ses": ses, "sure": _sure(ses),
            "tema": m.get("theme"), "izlenme": st.get("youtube_views", 0),
            # Kopya çiftinde hangisinin KALACAĞINI bu alan belirliyor
            # (bkz. _md5_tekrarini_ele): ilk yayınlanan kanonik kayıttır.
            "yuklendi": st.get("youtube_uploaded_at") or "",
        })
    # `youtube_privacy` filtresi (yukarıda) kopyayı yalnızca operatör onu ELLE
    # liste dışına aldıysa eliyor. Bu SON kapı konvansiyona değil DOSYANIN
    # KENDİSİNE bakıyor — gerekçe _md5_tekrarini_ele'nin docstring'inde.
    return _md5_tekrarini_ele(liste)


def _enerji(yol: str) -> float:
    """Parçanın RMS enerjisi (ortadan 90 sn). Akış kurgusu için."""
    try:
        import librosa
        import numpy as np
        y, sr = librosa.load(yol, sr=11025, mono=True, duration=90, offset=20)
        return float(np.sqrt((y * y).mean()))
    except Exception:
        return 0.0


def sec(havuz: list, hedef_dk: float) -> list:
    """Hedef süreye kadar seçer, sonra ENERJİ EĞRİSİNE göre sıralar.

    NEDEN İZLENMEYE GÖRE DEĞİL: izlenme sırası bir METRİKTEN üretilir, insan
    kararı içermez ve incelemeciye "şablonla üretilmiş" diye okunur. YouTube'un
    "Generic or Repetitive Content" kuralı tam da "creator's original,
    authentic insights or perspective" arıyor — küratörlüğün kendisi budur.
    Ayrıca müzikal olarak da doğrusu: izlenme sırası 144 BPM'den 86'ya,
    oradan 161'e atlıyordu; hiçbir DJ seti böyle kurulmaz.

    SEÇİM hâlâ izlenmeye göre — en çok izlenenden başlayıp `hedef_dk` dolana
    kadar; SABİT bir parça sayısı sınırı YOK (belge eskiden "en iyi 13 parça"
    diyordu, kodda böyle bir sınır hiç olmadı). SIRALAMA enerjiye göre:
    sakin açılış → yükseliş → tepe → iniş. Açılışta en sakin değil,
    ikinci en sakin parça var — ilk 30 saniye izleyiciyi tutmalı.
    """
    sirali = sorted(havuz, key=lambda x: -x["izlenme"])
    secilen, toplam = [], 0.0
    for p in sirali:
        if toplam >= hedef_dk * 60:
            break
        if p["sure"] <= 0:
            continue
        secilen.append(p)
        toplam += p["sure"]

    for p in secilen:
        p["enerji"] = _enerji(p["ses"])
    if not any(p["enerji"] for p in secilen):
        return secilen                     # librosa yoksa eski davranış

    # Eğri: enerjiye göre sırala, sonra düşükleri başa ve sona dağıt.
    e = sorted(secilen, key=lambda x: x["enerji"])
    acilis = e[1:2]                        # ikinci en sakin: giriş
    iniş = e[0:1] + e[2:4]                 # en sakinler sona
    orta = [p for p in e if p not in acilis + iniş]
    return acilis + orta + list(reversed(iniş))


def _baskin_tema(secilen: list) -> str:
    """Seçilen parçalarda EN ÇOK geçen tema anahtarı (yoksa config.DEFAULT_THEME).

    NEDEN: karma bir derlemenin meta.json'ındaki `theme` alanı eskiden
    config.DEFAULT_THEME'e düşüyordu — yani derlemenin içeriğiyle hiç ilgisi
    olmayan sabit bir tür. Kapak rengi/atmosferi de bu alandan türediği için
    baskın tema en az yanıltıcı seçim.
    """
    sayac = collections.Counter(p.get("tema") for p in secilen if p.get("tema"))
    if not sayac:
        return config.DEFAULT_THEME
    return sayac.most_common(1)[0][0]


def zaman_damgalari(secilen: list) -> list:
    """Her parçanın derleme içindeki başlangıç saniyesi (çapraz geçiş düşülmüş)."""
    damga, t = [], 0.0
    for i, p in enumerate(secilen):
        damga.append({"ad": p["ad"], "bas": round(t, 1)})
        t += p["sure"] - (GECIS_SN if i < len(secilen) - 1 else 0)
    return damga


def _mmss(sn: float) -> str:
    sn = int(sn)
    return "%d:%02d" % (sn // 60, sn % 60) if sn < 3600 else \
           "%d:%02d:%02d" % (sn // 3600, (sn % 3600) // 60, sn % 60)


def ses_birlestir(secilen: list, cikti: str) -> bool:
    """Parçaları çapraz geçişlerle tek ses dosyasında birleştirir."""
    if len(secilen) < 2:
        return False
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    for p in secilen:
        cmd += ["-i", p["ses"]]
    # acrossfade zinciri: her adımda birikmiş ses bir sonrakiyle harmanlanıyor.
    parcalar, onceki = [], "0:a"
    for i in range(1, len(secilen)):
        cikis = "a%d" % i if i < len(secilen) - 1 else "aout"
        parcalar.append("[%s][%d:a]acrossfade=d=%.1f:c1=tri:c2=tri[%s]"
                        % (onceki, i, GECIS_SN, cikis))
        onceki = cikis
    cmd += ["-filter_complex", ";".join(parcalar), "-map", "[aout]", cikti]
    # timeout ZORUNLU: timeout'suz run() ffmpeg takilirsa (bozuk girdi, kilitli
    # dosya) SURESIZ bekler — Gorev Zamanlayici'dan calisan bir kosu sessizce
    # sonsuza kadar asili kalir, kilit dosyasi da birakmaz. 1 saat, 40 dakikalik
    # bir acrossfade zinciri icin fazlasiyla genis bir ust sinir.
    try:
        subprocess.run(cmd, check=True, timeout=3600)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False
    return os.path.isfile(cikti) and os.path.getsize(cikti) > 0


def uret(ad: str, tema: str | None, hedef_dk: float, dry_run: bool) -> dict:
    havuz = adaylar(tema)
    if len(havuz) < 2:
        return {"hata": "yeterli şarkı yok (%d bulundu)" % len(havuz)}

    secilen = sec(havuz, hedef_dk)
    if len(secilen) < 2:
        return {"hata": "seçim 2 şarkıdan az"}

    damga = zaman_damgalari(secilen)
    toplam = damga[-1]["bas"] + secilen[-1]["sure"]

    ozet = {
        "ad": ad, "tema": tema or "karma", "parca": len(secilen),
        "sure_dk": round(toplam / 60, 1),
        "liste": [{"sira": i + 1, "ad": d["ad"], "zaman": _mmss(d["bas"])}
                  for i, d in enumerate(damga)],
    }
    if dry_run:
        ozet["kuru"] = True
        return ozet

    # SIRA DEĞİŞTİ — NEDEN: eskiden önce `os.makedirs` + `ses_birlestir()`
    # (13 parçalık acrossfade zinciri, DAKİKALAR sürüyor), SONRA meta.json
    # yazılıyordu. O iki adım arasında kesilen bir koşu `derlemeler/` altında
    # audio.wav'ı olan ama meta.json'ı OLMAYAN bir klasör bırakıyordu. O klasör
    # yayın hattına girdiğinde build_snippet({}) ile üretilen başlık
    # "Untitled (Sözleri) | Türkçe Hip-Hop Şarkısı" oluyordu (canlı doğrulandı)
    # ve `derleme_liste`/`derleme_notu` olmadığı için bölüm damgaları ile
    # küratörlük gerekçesi — yani derlemenin "inauthentic content" politikasına
    # karşı varoluş sebebinin TAMAMI — kayboluyordu.
    #
    # SEÇİLEN ÇÖZÜM: geçici klasörde üret + sonda tek adımda `os.replace` ile
    # taşı, AYRICA meta.json'ı sesten ÖNCE yaz. Sadece "meta'yı önce yaz"
    # yetmiyordu: görünür klasör yine yarım (kesik audio.wav) hâliyle yayın
    # hattına girebiliyordu — geçici klasör `derlemeler/` altında TAMAMLANMAMIŞ
    # hiçbir klasörün görünmemesini sağlıyor. İkisi birlikte: kötü bir
    # zamanlamada `.tmp-` klasörü kalsa ve bir tarayıcı yine de onu görse bile
    # içinde TAM meta.json bulunur, "Untitled" senaryosu artık imkânsız.
    gecici = os.path.join(HEDEF_KOK, ".tmp-" + ad)
    if os.path.isdir(gecici):
        shutil.rmtree(gecici, ignore_errors=True)   # önceki yarım koşunun artığı
    os.makedirs(gecici, exist_ok=True)

    # meta.json: render.py/generate_cover.py bunu normal bir proje gibi işliyor.
    # `derleme_liste` YouTube açıklamasına bölüm (chapter) olarak basılıyor.
    m = {
        "title": ad,
        # `theme` GEÇERLİ bir config.THEMES anahtarı olmak ZORUNDA (kapak rengi,
        # validate_project, resolve_language hep buradan okuyor) — ama karma bir
        # derlemede config.DEFAULT_THEME'e düşmek keyfîydi: "Gece Seansı Vol. 1"
        # 13 parçanın yalnızca 5'i hiphop olmasına rağmen DEFAULT_THEME yüzünden
        # "hiphop" damgalanıyordu. Artık BASKIN parça temasına düşülüyor; asıl
        # tür kararını YouTube başlığında `derleme_temalari` veriyor (aşağıda).
        "theme": tema or _baskin_tema(secilen),
        "derleme": True,
        # Her parçanın teması, seçim sırasıyla. youtube_upload.build_snippet
        # başlıktaki tür etiketini BUNDAN türetiyor — meta'daki tek `theme`
        # alanı karma bir derlemeyi anlatmaya yetmiyor (bkz. yukarıdaki not).
        "derleme_temalari": [p.get("tema") for p in secilen],
        "derleme_liste": ozet["liste"],
        "marquee_text": "%s  •  Famous Music Studio" % ad,
        # Kapak icin stok gorsel sorgusu. generate_cover gorsel yoksa
        # stock_art'tan cekiyor; sorgu verilmezse temaya dusuyor ve karma
        # derlemede tema "karma" oldugu icin anlamsiz bir gorsel gelirdi.
        "art_query": DERLEME_ART_SORGU.get(tema or "", DERLEME_ART_SORGU["_karma"]),
        # Küratörlük gerekçesi -> YouTube açıklamasına. YouTube incelemecileri
        # "how you created, participated in, or produced your content" sorusuna
        # cevap ararken video açıklamasına bakıyor (para kazanma politikası).
        # Sıranın tesadüf değil karar olduğunu yazılı hale getiriyor.
        "derleme_notu": (
            "Bu %d parça kanalın kendi üretimi; sıralama izlenme sayısına göre "
            "değil, ENERJİ EĞRİSİNE göre kuruldu: sakin bir açılış, yükselen "
            "orta bölüm, %s ile tepe, ve en sakin parçayla iniş. Parçalar "
            "arasında %.0f saniyelik gerçek geçişler var — tek tek dinlemekten "
            "farklı, kesintisiz bir akış olarak tasarlandı."
            % (len(secilen), secilen[max(range(len(secilen)),
               key=lambda i: secilen[i].get("enerji", 0))]["ad"], GECIS_SN)
        ),
    }
    with open(os.path.join(gecici, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=2)

    if not ses_birlestir(secilen, os.path.join(gecici, "audio.wav")):
        shutil.rmtree(gecici, ignore_errors=True)   # yarım klasör bırakma
        return {"hata": "ses birleştirilemedi"}

    hedef = os.path.join(HEDEF_KOK, ad)
    if os.path.isdir(hedef):
        # Aynı adla yeniden üretim: dizin üstüne os.replace çalışmaz (Windows'ta
        # hedef dizin varsa hata), dosya dosya taşınıyor — her biri yine atomik.
        for _dosya in os.listdir(gecici):
            os.replace(os.path.join(gecici, _dosya), os.path.join(hedef, _dosya))
        os.rmdir(gecici)
    else:
        os.replace(gecici, hedef)
    ozet["klasor"] = hedef
    return ozet


def main():
    ap = argparse.ArgumentParser(description="Yayınlanmış şarkılardan derleme üretir.")
    ap.add_argument("--ad", required=True, help="Derlemenin adı (klasör + başlık)")
    ap.add_argument("--tema", help="Tek temadan derle (arabesk, hiphop, ...)")
    ap.add_argument("--en-iyi", action="store_true", help="Tüm temalardan, en çok izlenenler")
    ap.add_argument("--hedef-dk", type=float, default=40.0, help="Hedef süre (dakika)")
    ap.add_argument("--dry-run", action="store_true", help="Üretme, ne olacağını yaz")
    args = ap.parse_args()

    if not args.tema and not args.en_iyi:
        ap.error("--tema ya da --en-iyi vermelisin")

    s = uret(args.ad, args.tema, args.hedef_dk, args.dry_run)
    if s.get("hata"):
        print("HATA:", s["hata"])
        return
    print("%s  |  %s  |  %d parça  |  %.1f dakika"
          % (s["ad"], s["tema"], s["parca"], s["sure_dk"]))
    for x in s["liste"]:
        print("  %2d. %-8s %s" % (x["sira"], x["zaman"], x["ad"]))
    if s.get("klasor"):
        print("\nklasör:", s["klasor"])
        print("sonraki adım: python render.py  (derlemeler/ kökünü işler)")


if __name__ == "__main__":
    main()
