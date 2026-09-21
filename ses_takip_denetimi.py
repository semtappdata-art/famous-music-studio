# -*- coding: utf-8 -*-
"""`ses_ve_tarz_takibi.md` ile diskteki ana kataloğun TUTARLILIK denetimi.

NEDEN VAR (2026-09-12'de bedeli ödendi): CLAUDE.md'de yazılı kural şu —
*"yeni bir şarkı stil etiketi yazmadan önce `ses_ve_tarz_takibi.md`'ye bak,
art arda aynı vokal cinsiyetini/dokusunu tekrarlama."* Kural uygulandı ama
**dosya yanlıştı**: üç gerçek üretim (Beton Krallığı, Gece Sürüşü, Sofraya
Gelmedin) tabloda hiç yoktu. Yani kuralı uygulayan kişi/ajan YANLIŞ BİR
GEÇMİŞE baktı ve son üç üretimin üçü de erkek-erkek düet oldu; kadın vokal
`Kumdan Denize`'den beri (bir haftadan uzun) hiç kullanılmadı.

Dosya elle düzeltildi, ama düzeltmenin kendisi bir koruma DEĞİL: dosya elle
tutuluyor, bir daha unutulabilir — dosyanın kendi son paragrafı da bunu
itiraf ediyor. Bu modül o boşluğu kapatıyor.

**ŞİDDET: UYARI, hata DEĞİL.** Takip dosyasının eskimesi yayını DURDURMAZ.
Bu bir üretim PLANLAMA aracı; bir telif/politika kapısı değil. (Karşılaştır:
`uyumluluk.py`'deki md5 tekrar kontrolü 2026-09-11'de UYARI'dan HATA'ya
çekildi — ama oradaki gerekçe "aynı sesi kanalda ikinci kez yayınlamak geri
alınamaz" idi. Burada geri alınamaz bir zarar yok: eskimiş bir tablo en fazla
bir sonraki şarkının vokalini tekrarlatır, ki o da düzeltilebilir.)

**SESSİZCE GEÇMEK YASAK.** Dosya elle düzenleniyor, yani biçimi ufak ufak
değişebilir. Tablo ayrıştırılamazsa bu modül `durum="okunamadi"` döndürüp
UYARI üretir — "anlamadım, o hâlde temiz" demez. Bugünün ana hatası tam olarak
buydu: kontrol edilmeyen bir şey "sorun yok" diye okundu.

NE KONTROL EDİLİYOR (üçü de ana katalog = `projects/` içindir; `dj_sets/` ve
`derlemeler/` kendi hatlarında izleniyor, takip dosyası da öyle diyor):

1. Diskte olup tabloda OLMAYAN proje — bugünkü arızanın ta kendisi.
2. Tabloda olup diskte karşılığı OLMAYAN satır. `(üretilmedi)` işaretli
   satırlar MUAF: "Neon Kalp" satırı, fikrin düşünülüp bırakıldığı bilgisi
   kayıtta kalsın diye BİLEREK duruyor (bkz. takip dosyasının satır notları).
   Onu "hayalet" saymak, her koşuda tekrarlayan bir yanlış pozitif demekti —
   ve tekrarlayan yanlış pozitif, uyarıyı tümden değersizleştirir.
3. Tablodaki tema, `projects/<isim>/meta.json`'daki `"theme"` ile aynı mı.

Proje listesi kanonik yardımcıdan alınıyor (`uyumluluk.proje_klasorleri`) —
`.`/`_` ön ekli klasör filtresini burada YENİDEN YAZMAK, bu deponun "kod
doğru ama YANLIŞ KÜMEYE bakıyor" arıza sınıfını davet ederdi.

BAĞLANTI: `saglik_kontrol.ses_takip_tutarliligi()` → `saglik_kontrol.kontrol_et()`
→ `auto_process.main()`'in `finally` bloğu (`_saglik_kontrol`) → SAATLİK
Görev Zamanlayıcı görevi. Bildirim `saglik_kontrol._bildir` ile GÜNDE BİR.
"""

import json
import os
import re
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import uyumluluk  # noqa: E402  (sys.path REPO'yu gordukten SONRA)

# Mutlak yol ZORUNLU: goreli birakilirsa yanlis cwd'de dosya "yok" gorunur.
# `uyumluluk.KOKLER`'de dusulen tuzagin aynisi (bkz. o modulun yorumu) — ama
# burada sonuc daha sinsi olurdu: "okunamadi" uyarisi her kosuda tekrarlanip
# gercek bir arizaymis gibi gorunurdu.
TAKIP_DOSYASI = os.path.join(REPO, "ses_ve_tarz_takibi.md")

# Tabloda "diskte karsiligi YOK ama satir BILEREK duruyor" isareti.
URETILMEDI_ISARETI = "üretilmedi"

# Bildirim/log'da kac uyari tam metin gosterilecek (gerisi sayiyla ozetlenir).
# Tavan olmadan, tablo tamamen bozulursa telefona 18 maddelik bir duvar giderdi.
UYARI_GOSTERIM_TAVANI = 6

_AYRAC_SATIRI = re.compile(r"^[\s|:\-]+$")
_PARANTEZ = re.compile(r"\([^()]*\)")


class TakipOkunamadi(Exception):
    """Takip dosyasi yok / tablo bulunamadi / tabloda tek veri satiri yok.

    AYRI bir sinif, cunku cagirani "temiz" ile karistirmamali: bu durum
    SESSIZCE GECILMEZ, kendisi bir uyari uretir.
    """


def _tr_kucuk(s: str) -> str:
    """Turkce-guvenli kucuk harf.

    `"İ".lower()` Python'da `i` + U+0307 (BIRLESEN NOKTA) uretir ve eslesme
    sessizce basarisiz olur — bu depoda altyazi hizalamasinda 14 kelimeyi
    kaybettiren tuzak (bkz. `caption_align._norm_word`). Burada da gercek risk
    var: "Kader Ortaklari" vb. klasor adlariyla tablo hucreleri eslestiriliyor.
    """
    return s.replace("İ", "i").replace("I", "ı").lower()


def _sadelestir(hucre: str) -> str:
    """Markdown susunu ve parantezli aciklamalari atar, bosluklari tekler.

    Ornekler (hepsi bugunku gercek dosyadan):
      "Gece Sürüşü *(eski adı: Shudhniy L)*" -> "Gece Sürüşü"
      "elektronik (Afro-House/Arabic EDM)"   -> "elektronik"
      "Neon Kalp **(üretilmedi)**"           -> "Neon Kalp"
    """
    s = hucre.replace("`", "").replace("*", "")
    onceki = None
    while onceki != s:                      # ic ice parantez icin tekrarli
        onceki = s
        s = _PARANTEZ.sub(" ", s)
    return " ".join(s.split())


def _anahtar(hucre: str) -> str:
    return _tr_kucuk(_sadelestir(hucre))


def _hucreler(satir: str):
    s = satir.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [h.strip() for h in s.split("|")]


def tabloyu_ayristir(metin: str) -> dict:
    """Takip dosyasinin metninden tabloyu okur.

    Donus: {"satirlar": [...], "bozuk_satirlar": [ham metin, ...]}
    Her satir: {"ad", "anahtar", "tema", "uretilmedi"}.

    KIRILGAN OLMAMASI icin: baslik satiri ADIYLA bulunuyor ve sutun sirasi
    basliktan turetiliyor (sutunlar yer degistirse de calisir); ayrac satiri
    bicimi serbest; tablo dosyanin neresinde olursa olsun bulunur.
    Bulunamazsa TakipOkunamadi — sessiz gecis YOK.
    """
    satirlar = metin.splitlines()
    basi = None
    sutun = {}
    for i, ham in enumerate(satirlar):
        if not ham.strip().startswith("|"):
            continue
        kucuk = [_anahtar(h) for h in _hucreler(ham)]
        if "şarkı" in kucuk and "tema" in kucuk:
            basi = i
            sutun = {"ad": kucuk.index("şarkı"), "tema": kucuk.index("tema")}
            break
    if basi is None:
        raise TakipOkunamadi(
            "tabloda 'Şarkı' ve 'Tema' başlıklı bir satır bulunamadı")

    kayitlar = []
    bozuk = []
    en_buyuk = max(sutun.values())
    for ham in satirlar[basi + 1:]:
        s = ham.strip()
        if not s.startswith("|"):
            break                            # tablo bitti
        if _AYRAC_SATIRI.match(s):
            continue                         # |---|---|
        hucreler = _hucreler(s)
        if len(hucreler) <= en_buyuk:
            # Sutunu eksik satir. ATLANMIYOR, RAPORLANIYOR: sessizce atlamak
            # "tabloda yok" sonucunu dogurur ve sebebi gorunmez olurdu.
            bozuk.append(s[:120])
            continue
        ham_ad = hucreler[sutun["ad"]]
        ad = _sadelestir(ham_ad)
        if not ad:
            bozuk.append(s[:120])
            continue
        kayitlar.append({
            "ad": ad,
            "anahtar": _anahtar(ham_ad),
            "tema": _anahtar(hucreler[sutun["tema"]]),
            # Isaret PARANTEZ ATILMADAN once aranmali: `_sadelestir` onu siler.
            "uretilmedi": URETILMEDI_ISARETI in _tr_kucuk(ham_ad),
        })

    if not kayitlar:
        raise TakipOkunamadi("tablo başlığı bulundu ama tek bir veri satırı yok")
    return {"satirlar": kayitlar, "bozuk_satirlar": bozuk}


def _projects_koku() -> str:
    """Ana katalog kokunu KANONIK listeden secer, elle birlestirmez."""
    for k in uyumluluk.KOKLER:
        if os.path.basename(k) == "projects":
            return k
    return os.path.join(REPO, "projects")     # kok listesi degisirse son care


def _tema(proje: str):
    """`meta.json`'daki `theme`. Donus: (tema|None, hata_metni|None).

    `uyumluluk._meta` BILEREK kullanilmiyor: o gizli (alt cizgili) bir isim ve
    politika kapisinin ic sozlesmesine bagli (`DurumBozuk` firlatiyor, cunku
    orada bozuk meta bir KAPI kararidir). Burada bozuk bir meta yalnizca
    "temayi karsilastiramadim" demek — ayni gerekce `weekly_report`'un
    `saglik_kontrol._bildir`'i kopyalamasinda da yazili.
    """
    yol = os.path.join(proje, "meta.json")
    if not os.path.isfile(yol):
        return None, "meta.json yok"
    try:
        with open(yol, "r", encoding="utf-8") as f:
            veri = json.load(f)
    except (OSError, ValueError) as e:
        return None, "meta.json okunamadı (%s)" % str(e)[:60]
    tema = veri.get("theme")
    if not isinstance(tema, str) or not tema.strip():
        return None, "meta.json'da 'theme' yok"
    return tema.strip(), None


def denetle(takip_dosyasi: str = None, proje_koku: str = None) -> dict:
    """Takip dosyasi ile diski karsilastirir. AGA CIKMAZ, HICBIR SEY YAZMAZ.

    Donus:
      {"durum": "tamam" | "uyari" | "okunamadi",
       "uyarilar": [str, ...],
       "eksik_satir": [...], "hayalet_satir": [...], "tema_uyusmazligi": [...],
       "proje_sayisi": int, "satir_sayisi": int}

    `durum == "okunamadi"` da bir UYARI durumudur (cagiran ikisini de loglar);
    ayri tutulmasinin sebebi tanidir: "tablo eskimis" ile "tabloyu hic
    okuyamadim" cok farkli iki duzeltme gerektiriyor.
    """
    yol = takip_dosyasi or TAKIP_DOSYASI
    sonuc = {"durum": "tamam", "uyarilar": [], "eksik_satir": [],
             "hayalet_satir": [], "tema_uyusmazligi": [],
             "proje_sayisi": 0, "satir_sayisi": 0, "dosya": yol}

    try:
        with open(yol, "r", encoding="utf-8") as f:
            metin = f.read()
    except OSError as e:
        sonuc["durum"] = "okunamadi"
        sonuc["uyarilar"].append(
            "takip dosyası okunamadı (%s): %s" % (os.path.basename(yol), str(e)[:80]))
        return sonuc

    try:
        tablo = tabloyu_ayristir(metin)
    except TakipOkunamadi as e:
        sonuc["durum"] = "okunamadi"
        sonuc["uyarilar"].append(
            "takip dosyası okunamadı — tablo ayrıştırılamadı (%s): %s. "
            "Biçim değiştiyse tablo başlığı 'Şarkı'/'Tema' sütunlarını "
            "taşımalı." % (os.path.basename(yol), e))
        return sonuc

    satirlar = tablo["satirlar"]
    sonuc["satir_sayisi"] = len(satirlar)
    for ham in tablo["bozuk_satirlar"]:
        sonuc["uyarilar"].append(
            "takip tablosunda ayrıştırılamayan satır (sütun eksik): %s" % ham)

    tablo_ad = {}
    for r in satirlar:
        if r["anahtar"] in tablo_ad:
            sonuc["uyarilar"].append(
                "takip tablosunda '%s' iki kez geçiyor" % r["ad"])
        tablo_ad.setdefault(r["anahtar"], r)

    kok = proje_koku or _projects_koku()
    diskte = {}
    for p in uyumluluk.proje_klasorleri(kok):
        diskte[_anahtar(os.path.basename(p))] = p
    sonuc["proje_sayisi"] = len(diskte)

    # 1) Diskte var, tabloda YOK — bugunku arizanin ta kendisi.
    for anahtar in sorted(diskte):
        if anahtar in tablo_ad:
            continue
        ad = os.path.basename(diskte[anahtar])
        sonuc["eksik_satir"].append(ad)
        sonuc["uyarilar"].append(
            "`projects/%s` diskte VAR ama takip tablosunda YOK — vokal "
            "çeşitliliği kuralı bu şarkıyı görmüyor." % ad)

    # 2) Tabloda var, diskte YOK. `(üretilmedi)` isaretliler MUAF.
    for r in satirlar:
        if r["anahtar"] in diskte or r["uretilmedi"]:
            continue
        sonuc["hayalet_satir"].append(r["ad"])
        sonuc["uyarilar"].append(
            "takip tablosundaki '%s' satırının diskte karşılığı yok — proje "
            "yeniden adlandırıldıysa satırı düzelt, fikir olarak duruyorsa "
            "'(üretilmedi)' işaretle." % r["ad"])

    # 3) Tema uyusmazligi.
    for anahtar, proje in sorted(diskte.items()):
        r = tablo_ad.get(anahtar)
        if not r:
            continue
        tema, hata = _tema(proje)
        if hata:
            sonuc["uyarilar"].append(
                "`projects/%s`: tema karşılaştırılamadı — %s"
                % (os.path.basename(proje), hata))
            continue
        if _tr_kucuk(tema) != r["tema"]:
            sonuc["tema_uyusmazligi"].append(
                {"ad": r["ad"], "tablo": r["tema"], "meta": tema})
            sonuc["uyarilar"].append(
                "'%s': takip tablosunda tema '%s', meta.json'da '%s'."
                % (r["ad"], r["tema"], tema))

    if sonuc["uyarilar"]:
        sonuc["durum"] = "uyari"
    return sonuc


def ozet(sonuc: dict, tavan: int = UYARI_GOSTERIM_TAVANI):
    """Uyari listesini gosterim tavanina kirpar (log ve bildirim ayni metni alsin)."""
    u = list(sonuc.get("uyarilar") or [])
    if len(u) <= tavan:
        return u
    return u[:tavan] + ["... ve %d uyarı daha" % (len(u) - tavan)]


if __name__ == "__main__":
    print(json.dumps(denetle(), ensure_ascii=False, indent=2))
