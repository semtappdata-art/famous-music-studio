# -*- coding: utf-8 -*-
"""Haftalık ÖZGÜNLÜK SKORU (ozgunluk_plani.md §2g) — SALT OKUR.

Toplam = 0,30·K + 0,25·M + 0,25·İ + 0,20·R  (0-100, yuvarlanır)

  K kapak   100 × (1 − son 10 yayında şablon/düzen tekrar oranı). Düzen kimliği plan §1.1
            yöntemiyle: kapak ile KENDİ `art.*`'ı aynı kırpımla 160×90 griye indirilir,
            farkı > 45 olan pikseller başlık+logonun kendisidir; bu "bindirme kutusu"nun
            kaba konumu düzen sınıfıdır (orta-ust, sol-alt, genis-alt ...). Ek rapor:
            geçmişe en küçük pHash mesafesi, karanlık-desatüre kapak oranı.
  M metin   50 × (1 − uzun açıklama ortak satır oranı) + 50 × (1 − başlık kalıbı tekrar
            oranı). Açıklamalar `youtube_upload.build_snippet(meta)` KURU çalıştırılarak
            üretilir (ağ yok). Başlık kalıbı state'te `youtube_baslik_kalibi` varsa o,
            yoksa başlıktan sınıflanır. Link bloğu hariç oran ayrıca raporlanır.
  İ insan   100 × min(1, insan emeği gönderisi ÷ (0,15 × son 7 gün kamuya açık gönderi)).
  R ritim   max(0, 100 − 20 × son 7 gün ihlal) — ihlaller `yayin_ritmi.ihlaller` (R1/R2/R3).

"Son 10 yayın" = uzun formatı yayına çıkmış en yeni 10 proje (tüm kökler). `kopya_notu`
taşıyan projeler HARİÇ: bilerek liste dışı tutulan bir kopya izleyicinin feed'inde yok,
ama kapağı/metni asılla aynı olduğu için sayılsa tekrar oranını YAPAY biçimde şişirirdi
(`olcum_temel_cizgi.KOPYA_PROJELER` ile aynı gerekçe).

Bir bileşen ölçülemezse değeri `None`, sebebi `olculemedi` listesinde; TOPLAM da `None`
olur — kalan ağırlıklarla "yeniden normalize edilmiş" bir sayı üretmek sessiz bir
ölçüm değişikliği olurdu. Haftalık satır bunu "ölçülemedi (<sebep>)" diye yazar.

ÜÇ SORU: çağıran `weekly_report._haftalik_satirlar` → `_ozgunluk_satiri` (saatlik
`auto_process.main()` finally → `haftalik_gozden_gecirme`, haftada bir); pano/Hermes
`python ozgunluk_skoru.py --json`. Anlık görüntü `ozgunluk_olcum.json` YALNIZ haftalık
özet başarıyla gönderildiğinde yazılır. Koruma: tests/test_ozgunluk_skoru.py.
Görseller Pillow OLMADAN, ffmpeg ile ham piksele çözülür.
"""

import argparse
import collections
import datetime
import itertools
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time

_KOK = os.path.dirname(os.path.abspath(__file__))
if os.path.join(_KOK, "upload") not in sys.path:
    sys.path.insert(1, os.path.join(_KOK, "upload"))

import yayin_ritmi  # noqa: E402

GUN_SN = 24 * 3600.0
SON_N = 10
AGIRLIKLAR = {"K": 0.30, "M": 0.25, "I": 0.25, "R": 0.20}
INSAN_EMEGI_HEDEF_ORANI = 0.15
RITIM_IHLAL_CEZASI = 20
BINDIRME_W, BINDIRME_H, BINDIRME_ESIK = 160, 90, 45
GERCEK_OLCUM_YOLU = os.path.join(_KOK, "ozgunluk_olcum.json")
ORTAM_DEGISKENI = "OZGUNLUK_OLCUM_DOSYASI"
KAPAK_ADLARI = ("cover.png", "cover.jpg", "cover.jpeg")
ART_ADLARI = ("art.jpg", "art.png", "art.jpeg")
INSAN_EMEGI_DESENI = re.compile(r"söz defteri|kulis|topluluk|KNL-", re.IGNORECASE)
KNL_DESENI = re.compile(r"KNL-[0-9]{4}-[0-9]{2}-[0-9]{2}-[a-z_]+")


class OzgunlukHatasi(RuntimeError):
    """Ölçüm/yazma reddi."""


ts_oku = yayin_ritmi.ts_oku


def hafta_damgasi(t=None) -> str:
    """ISO yıl-hafta ("2026-W37") — weekly_report._hafta ile aynı tanım."""
    y, w, _ = datetime.date.fromtimestamp(t if t is not None else time.time()).isocalendar()
    return "%d-W%02d" % (y, w)


# --------------------------------------------------------------------------
# Görsel ölçümler (ffmpeg → ham piksel)
# --------------------------------------------------------------------------

_ONBELLEK = {}


def _ffmpeg():
    yol = shutil.which("ffmpeg")
    if not yol:
        raise OzgunlukHatasi("ffmpeg bulunamadı")
    return yol


def _ham(yol, w, h, pix="gray", kirp=True):
    try:
        st = os.stat(yol)
    except OSError as e:
        raise OzgunlukHatasi("görsel okunamadı: %s (%s)" % (yol, e))
    anahtar = (os.path.abspath(yol), st.st_mtime, st.st_size, w, h, pix, kirp)
    if anahtar in _ONBELLEK:
        return _ONBELLEK[anahtar]
    filtre = ("scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d" % (w, h, w, h)
              if kirp else "scale=%d:%d" % (w, h))
    r = subprocess.run([_ffmpeg(), "-v", "error", "-i", yol, "-vf", filtre, "-frames:v", "1",
                        "-f", "rawvideo", "-pix_fmt", pix, "-"],
                       capture_output=True, timeout=60,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    kanal = 3 if pix == "rgb24" else 1
    if r.returncode != 0 or len(r.stdout) != w * h * kanal:
        raise OzgunlukHatasi("ffmpeg çözümleyemedi: %s" % os.path.basename(yol))
    _ONBELLEK[anahtar] = r.stdout
    return r.stdout


_COS = [[math.cos((2 * x + 1) * u * math.pi / 64) for x in range(32)] for u in range(8)]


def phash(yol) -> int:
    """63 bit pHash: 32×32 gri → DCT → sol üst 8×8 (DC hariç) → medyan eşiği."""
    p = _ham(yol, 32, 32, kirp=False)
    satirlar = [p[i * 32:(i + 1) * 32] for i in range(32)]
    katsayi = []
    for v in range(8):
        cv = _COS[v]
        sutun = [sum(satirlar[y][x] * cv[y] for y in range(32)) for x in range(32)]
        for u in range(8):
            if u == 0 and v == 0:
                continue
            cu = _COS[u]
            katsayi.append(sum(sutun[x] * cu[x] for x in range(32)))
    medyan = sorted(katsayi)[len(katsayi) // 2]
    bits = 0
    for i, k in enumerate(katsayi):
        if k > medyan:
            bits |= 1 << i
    return bits


def hamming(a, b) -> int:
    return bin(a ^ b).count("1")


def bindirme_kutusu(kapak, art, esik=BINDIRME_ESIK):
    """(x0, y0, x1, y1) 160×90 ızgarada, ya da None (bindirme yok).

    Gürültü koruması: en az 2 farklı piksel içeren satır/sütunlar sayılır (JPEG
    kenar gürültüsü tek pikselle kutuyu şişirmesin)."""
    w, h = BINDIRME_W, BINDIRME_H
    a, b = _ham(kapak, w, h), _ham(art, w, h)
    sutun = [0] * w
    satir = [0] * h
    for y in range(h):
        o = y * w
        for x in range(w):
            if abs(a[o + x] - b[o + x]) > esik:
                sutun[x] += 1
                satir[y] += 1
    xs = [x for x in range(w) if sutun[x] >= 2]
    ys = [y for y in range(h) if satir[y] >= 2]
    if not xs or not ys:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


def duzen_sinifi(kutu, w=BINDIRME_W, h=BINDIRME_H) -> str:
    if kutu is None:
        return "yok"
    x0, y0, x1, y1 = kutu
    if (x1 - x0 + 1) >= 0.85 * w:
        yatay = "genis"
    else:
        cx = (x0 + x1) / 2.0
        yatay = "sol" if cx < 0.38 * w else ("sag" if cx > 0.62 * w else "orta")
    cy = (y0 + y1) / 2.0
    dikey = "ust" if cy < 0.4 * h else ("alt" if cy > 0.6 * h else "orta")
    return "%s-%s" % (yatay, dikey)


def karanlik_desature(yol) -> bool:
    """Ortalama V < 0,35 ve ortalama S ≤ 0,10 (plan §1.1)."""
    p = _ham(yol, 32, 18, pix="rgb24")
    n = len(p) // 3
    tv = ts = 0.0
    for i in range(n):
        r, g, b = p[3 * i], p[3 * i + 1], p[3 * i + 2]
        mx, mn = max(r, g, b), min(r, g, b)
        tv += mx / 255.0
        ts += (mx - mn) / mx if mx else 0.0
    return (tv / n) < 0.35 and (ts / n) <= 0.10


def _ilk_dosya(proje, adlar):
    for a in adlar:
        y = os.path.join(proje, a)
        if os.path.isfile(y):
            return y
    return None


def _kapak_olcumu(proje) -> dict:
    kapak = _ilk_dosya(proje, KAPAK_ADLARI)
    if not kapak:
        raise OzgunlukHatasi("kapak yok: %s" % os.path.basename(proje))
    art = _ilk_dosya(proje, ART_ADLARI)
    return {"duzen": duzen_sinifi(bindirme_kutusu(kapak, art)) if art else "art-yok",
            "phash": phash(kapak), "karanlik": karanlik_desature(kapak)}


# --------------------------------------------------------------------------
# Metin ölçümleri
# --------------------------------------------------------------------------

_K1 = re.compile(r"^.+ \(Sözleri\) \| Türkçe .+ Şarkısı$")
_K2 = re.compile(r"^.+ — Sözleri \| Famous Music Studio$")
_K3 = re.compile(r"^.+ \(Sözleri\) · .+$")


def baslik_kalibi(baslik) -> str:
    b = (baslik or "").strip()
    if _K1.match(b):
        return "K1"
    if _K2.match(b):
        return "K2"
    if _K3.match(b):
        return "K3"
    return "diger"


def tekrar_orani(etiketler):
    if not etiketler:
        return None
    return collections.Counter(etiketler).most_common(1)[0][1] / float(len(etiketler))


def _link_satiri(s) -> bool:
    return "http://" in s or "https://" in s


def ortak_satir_orani(aciklamalar, link_haric=False):
    """Başka en az bir açıklamada da geçen satırların oranı (satır örneği bazında)."""
    if len(aciklamalar) < 2:
        return None
    kumeler = []
    for a in aciklamalar:
        satirlar = {s.strip() for s in (a or "").split("\n") if s.strip()}
        if link_haric:
            satirlar = {s for s in satirlar if not _link_satiri(s)}
        kumeler.append(satirlar)
    toplam = sum(len(k) for k in kumeler)
    if not toplam:
        return None
    sayac = collections.Counter(s for k in kumeler for s in k)
    return sum(1 for k in kumeler for s in k if sayac[s] >= 2) / float(toplam)


def stil_jaccard(kumeler):
    kumeler = [k for k in kumeler if k]
    if len(kumeler) < 2:
        return None, None
    degerler = [len(a & b) / float(len(a | b)) for a, b in itertools.combinations(kumeler, 2)]
    return sum(degerler) / len(degerler), max(degerler)


def _stil_kumesi(baslik):
    try:
        import stock_art
        yol = stock_art.find_lyrics_file(baslik)
    except Exception:  # noqa: BLE001
        return None
    if not yol or not os.path.isfile(yol):
        return None
    with open(yol, "r", encoding="utf-8") as f:
        metin = f.read()
    m = re.search(r"^## Stil[^\n]*\n(.*?)(?=^## |\Z)", metin, re.S | re.M)
    if not m:
        return None
    blok = re.search(r"```\s*\n(.*?)```", m.group(1), re.S)
    govde = blok.group(1) if blok else m.group(1)
    return {k for k in re.findall(r"[a-z][a-z\-]{2,}", govde.lower())}


def _snippet(meta):
    import youtube_upload
    return youtube_upload.build_snippet(meta)


# --------------------------------------------------------------------------
# Bileşen aritmetiği
# --------------------------------------------------------------------------

def kapak_puani(oran):
    return None if oran is None else 100.0 * (1.0 - oran)


def metin_puani(ortak, baslik):
    if ortak is None or baslik is None:
        return None
    return 50.0 * (1.0 - ortak) + 50.0 * (1.0 - baslik)


def insan_emegi_puani(insan, toplam):
    if not toplam:
        return None
    return 100.0 * min(1.0, insan / (INSAN_EMEGI_HEDEF_ORANI * toplam))


def ritim_puani(ihlal):
    return max(0, 100 - RITIM_IHLAL_CEZASI * int(ihlal))


def toplam(bilesenler):
    if any(bilesenler.get(k) is None for k in AGIRLIKLAR):
        return None
    return int(round(sum(AGIRLIKLAR[k] * bilesenler[k] for k in AGIRLIKLAR)))


# --------------------------------------------------------------------------
# İnsan emeği gönderileri
# --------------------------------------------------------------------------

def insan_emegi_gonderileri(simdi, kanal_yolu=None, defter_yolu=None, gun=7):
    """(sayı, kimlikler) — son `gun` gündeki yayınlanmış insan emeği gönderileri.

    Kaynaklar: `kanal_takvimi.json` `durum=yayinlandi` (Topluluk dahil) + elle işlem
    defterindeki `yayinladi` kayıtlarından ayrıntısı Söz Defteri/Kulis/Topluluk/KNL-
    olanlar. Defterdeki kayıt bir KNL kimliğine atıf yapıyorsa ve o kimlik takvimde
    zaten sayıldıysa İKİNCİ kez sayılmaz."""
    bas = simdi - gun * GUN_SN
    kimlikler = []
    if kanal_yolu is None:
        try:
            import turev_takvimi
            kanal_yolu = turev_takvimi.KANAL_TAKVIMI_YOLU
        except Exception:  # noqa: BLE001
            kanal_yolu = os.path.join(_KOK, "kanal_takvimi.json")
    try:
        with open(kanal_yolu, "r", encoding="utf-8") as f:
            veri = json.load(f)
    except (OSError, ValueError):
        veri = {}
    for k in (veri.get("gonderiler") or []) if isinstance(veri, dict) else []:
        if not isinstance(k, dict) or k.get("durum") != "yayinlandi":
            continue
        an = ts_oku((k.get("yayin") or {}).get("an")) or ts_oku(k.get("hedef_an"))
        if an is not None and bas <= an <= simdi:
            kimlikler.append(k.get("id"))
    import elle_islem
    kayitlar, _bozuk = elle_islem.oku(defter_yolu)
    for k in kayitlar:
        if k.get("islem") != "yayinladi":
            continue
        metin = "%s %s" % (k.get("ayrinti") or "", k.get("proje") or "")
        if not INSAN_EMEGI_DESENI.search(metin):
            continue
        an = elle_islem.zaman_ts(k.get("zaman"))
        if an is None or not (bas <= an <= simdi):
            continue
        atif = KNL_DESENI.findall(metin)
        if atif and any(a in kimlikler for a in atif):
            continue
        kimlikler.append(atif[0] if atif else k.get("id"))
    return len(kimlikler), kimlikler


# --------------------------------------------------------------------------
# Hesap
# --------------------------------------------------------------------------

def _json(yol):
    try:
        with open(yol, "r", encoding="utf-8") as f:
            v = json.load(f)
        return v if isinstance(v, dict) else None
    except FileNotFoundError:
        return {}
    except (OSError, ValueError):
        return None


def hesapla(simdi=None, klasorler=None, kanal_yolu=None, defter_yolu=None) -> dict:
    t = time.time() if simdi is None else float(simdi)
    bas_zaman = time.time()
    if klasorler is None:
        import uyumluluk
        klasorler = list(uyumluluk.proje_klasorleri())
    olculemedi, kirilim, bilesen = [], {}, {}

    # --- katalog ---
    yayinlar, okunamayan = [], []
    for p in klasorler:
        st, meta = _json(os.path.join(p, "state.json")), _json(os.path.join(p, "meta.json"))
        if st is None or meta is None:
            okunamayan.append(os.path.basename(p))
            continue
        if st.get("kopya_notu") or meta.get("kopya_notu"):
            continue
        an = yayin_ritmi.uzun_yayin_ani(st)
        if an is None or an > t:
            continue
        yayinlar.append((an, p, st, meta))
    yayinlar.sort(key=lambda x: x[0], reverse=True)
    son = yayinlar[:SON_N]
    kirilim["son_yayinlar"] = [os.path.basename(os.path.normpath(p)) for _, p, _, _ in son]
    if okunamayan:
        kirilim["okunamayan_state"] = okunamayan
    if not son:
        olculemedi.append("katalog: yayına çıkmış uzun format yok")

    # --- K kapak ---
    kapak = {"duzenler": {}, "hatalar": []}
    olcumler = {}
    for an, p, _, _ in yayinlar:
        ad = os.path.basename(os.path.normpath(p))
        try:
            olcumler[ad] = _kapak_olcumu(p) if ad in kirilim["son_yayinlar"] else {
                "phash": phash(_ilk_dosya(p, KAPAK_ADLARI) or os.path.join(p, "cover.png"))}
        except Exception as e:  # noqa: BLE001
            kapak["hatalar"].append("%s: %s" % (ad, str(e)[:80]))
    duzenler = [olcumler[a]["duzen"] for a in kirilim["son_yayinlar"]
                if a in olcumler and "duzen" in olcumler[a]]
    kapak["duzenler"] = dict(collections.Counter(duzenler))
    kapak["sablon_tekrar_orani"] = tekrar_orani(duzenler)
    if len(duzenler) < max(1, len(son) // 2):
        bilesen["K"] = None
        olculemedi.append("K: kapak düzeni ölçülemedi (%d/%d; %s)" % (
            len(duzenler), len(son), "; ".join(kapak["hatalar"][:2]) or "sebep yok"))
    else:
        bilesen["K"] = kapak_puani(kapak["sablon_tekrar_orani"])
    sirali = [os.path.basename(os.path.normpath(p)) for _, p, _, _ in yayinlar]
    min_ph = None
    for i, ad in enumerate(sirali[:SON_N]):
        h = (olcumler.get(ad) or {}).get("phash")
        if h is None:
            continue
        for eski in sirali[i + 1:]:
            he = (olcumler.get(eski) or {}).get("phash")
            if he is not None:
                d = hamming(h, he)
                if min_ph is None or d < min_ph[0]:
                    min_ph = (d, ad, eski)
    kapak["min_phash_gecmise"] = ({"mesafe": min_ph[0], "cift": [min_ph[1], min_ph[2]]}
                                  if min_ph else None)
    karanlik = [olcumler[a]["karanlik"] for a in kirilim["son_yayinlar"]
                if a in olcumler and "karanlik" in olcumler[a]]
    kapak["karanlik_desature_orani"] = (sum(karanlik) / float(len(karanlik))
                                        if karanlik else None)
    kirilim["kapak"] = kapak

    # --- M metin ---
    metin = {}
    try:
        snippetler = [(_snippet(meta), st) for _, _, st, meta in son]
        kaliplar = [st.get("youtube_baslik_kalibi") or baslik_kalibi(s.get("title"))
                    for s, st in snippetler]
        aciklamalar = [s.get("description") or "" for s, _ in snippetler]
        metin["baslik_kaliplari"] = dict(collections.Counter(kaliplar))
        metin["baslik_kalibi_tekrar_orani"] = tekrar_orani(kaliplar)
        metin["ortak_satir_orani"] = ortak_satir_orani(aciklamalar)
        metin["ortak_satir_orani_link_haric"] = ortak_satir_orani(aciklamalar, link_haric=True)
        bilesen["M"] = metin_puani(metin["ortak_satir_orani"],
                                   metin["baslik_kalibi_tekrar_orani"])
        if bilesen["M"] is None:
            olculemedi.append("M: en az 2 yayın gerekli")
    except Exception as e:  # noqa: BLE001
        bilesen["M"] = None
        olculemedi.append("M: açıklama üretilemedi (%s: %s)" % (type(e).__name__, str(e)[:80]))
    kirilim["metin"] = metin

    # --- İ insan emeği + R ritim ---
    try:
        olaylar = yayin_ritmi.olaylar(klasorler)
        haftalik = [o for o in olaylar if t - 7 * GUN_SN <= o["ts"] <= t]
        insan, kimlikler = insan_emegi_gonderileri(t, kanal_yolu, defter_yolu)
        toplam_gonderi = len(haftalik) + insan
        bilesen["I"] = insan_emegi_puani(insan, toplam_gonderi)
        kirilim["insan_emegi"] = {"gonderi": insan, "kimlikler": kimlikler,
                                  "haftalik_kamuya_acik": toplam_gonderi,
                                  "oran": (insan / float(toplam_gonderi)) if toplam_gonderi
                                  else None}
        if bilesen["I"] is None:
            olculemedi.append("İ: son 7 günde kamuya açık gönderi yok")
        ihl = yayin_ritmi.ihlaller(olaylar, bas=t - 7 * GUN_SN, bit=t + 1)
        bilesen["R"] = ritim_puani(len(ihl))
        kirilim["ritim"] = {"ihlal": len(ihl),
                            "kurallar": dict(collections.Counter(i["kural"] for i in ihl)),
                            "ornekler": [i["aciklama"] for i in ihl[:8]]}
    except Exception as e:  # noqa: BLE001
        for k in ("I", "R"):
            bilesen.setdefault(k, None)
        olculemedi.append("İ/R: olaylar okunamadı (%s: %s)" % (type(e).__name__, str(e)[:80]))

    # --- stil çeşitliliği (rapor alanı, toplama girmez) ---
    try:
        kumeler = [_stil_kumesi(meta.get("title") or "") for _, _, _, meta in son]
        ort, maks = stil_jaccard(kumeler)
        kirilim["stil"] = {"jaccard_ort": ort, "jaccard_maks": maks,
                           "etiketli": sum(1 for k in kumeler if k),
                           "tema": dict(collections.Counter(
                               meta.get("theme") or "?" for _, _, _, meta in son))}
    except Exception as e:  # noqa: BLE001
        kirilim["stil"] = {"hata": str(e)[:80]}

    yuvarla = {k: (None if v is None else round(v, 1)) for k, v in bilesen.items()}
    for k in AGIRLIKLAR:
        yuvarla.setdefault(k, None)
    return {
        "skor": toplam(bilesen) if all(k in bilesen for k in AGIRLIKLAR) else None,
        "hafta": hafta_damgasi(t),
        "bilesenler": yuvarla,
        "agirliklar": AGIRLIKLAR,
        "kirilim": kirilim,
        "olculemedi": olculemedi,
        "hesaplandi_at": datetime.datetime.fromtimestamp(t, yayin_ritmi.TR).isoformat(
            timespec="seconds"),
        "sure_sn": round(time.time() - bas_zaman, 2),
    }


# --------------------------------------------------------------------------
# Haftalık anlık görüntü + özet satırı
# --------------------------------------------------------------------------

def olcum_yolu(yol=None):
    if yol:
        return os.path.abspath(yol)
    return os.path.abspath(os.environ.get(ORTAM_DEGISKENI) or GERCEK_OLCUM_YOLU)


def _testte_gercek(yol):
    return bool(os.environ.get("PYTEST_CURRENT_TEST")) and (
        os.path.normcase(os.path.abspath(yol)) == os.path.normcase(GERCEK_OLCUM_YOLU))


def anlik_kaydet(hafta, veri, yol=None):
    yol = olcum_yolu(yol)
    if _testte_gercek(yol):
        raise OzgunlukHatasi("test sırasında GERÇEK ölçüm dosyasına yazma reddedildi")
    mevcut = _json(yol) or {}
    haftalar = mevcut.get("haftalar") if isinstance(mevcut.get("haftalar"), dict) else {}
    haftalar[hafta] = {"skor": veri.get("skor"), "bilesenler": veri.get("bilesenler"),
                       "olculemedi": veri.get("olculemedi"),
                       "hesaplandi_at": veri.get("hesaplandi_at")}
    import state_io
    state_io._atomik_yaz(yol, {"surum": 1, "haftalar": haftalar})


def onceki_skor(hafta, yol=None):
    """`hafta`dan ÖNCEKİ en yeni haftanın skoru (yoksa None)."""
    yol = olcum_yolu(yol)
    if _testte_gercek(yol):
        return None
    veri = _json(yol) or {}
    haftalar = veri.get("haftalar") if isinstance(veri.get("haftalar"), dict) else {}
    oncekiler = sorted(h for h in haftalar if h < hafta)
    return (haftalar[oncekiler[-1]] or {}).get("skor") if oncekiler else None


def ozet_satiri(veri, onceki) -> str:
    if veri.get("skor") is None:
        return "Özgünlük skoru: ölçülemedi (%s)" % (
            "; ".join(veri.get("olculemedi") or []) or "sebep yazılmadı")[:200]
    if onceki is None:
        return "Özgünlük skoru: %d/100 (geçen hafta: yok)" % veri["skor"]
    return "Özgünlük skoru: %d/100 (geçen hafta %s)" % (veri["skor"], onceki)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Haftalık özgünlük skoru (salt okur).")
    ap.add_argument("--json", action="store_true", help="pano sözleşmesi")
    ap.add_argument("--simdi", default=None, help="ISO an (geriye dönük hesap)")
    args = ap.parse_args(argv)
    simdi = ts_oku(args.simdi) if args.simdi else None
    veri = hesapla(simdi=simdi)
    if args.json:
        cikti = json.dumps(veri, ensure_ascii=False, indent=2) + "\n"
    else:
        b = veri.get("bilesenler") or {}
        cikti = "\n".join([
            ozet_satiri(veri, onceki_skor(veri.get("hafta") or hafta_damgasi())),
            "  K kapak %s · M metin %s · İ insan emeği %s · R ritim %s" % tuple(
                b.get(k) for k in ("K", "M", "I", "R")),
            "  kırılım: " + json.dumps(veri.get("kirilim"), ensure_ascii=False),
        ]) + "\n"
    sys.stdout.buffer.write(cikti.encode("utf-8"))
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
