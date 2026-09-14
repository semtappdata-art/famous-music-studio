# -*- coding: utf-8 -*-
"""Suno stil tarifine eklenecek mix / vokal / düzenleme ifadelerini seçer.

Kullanım (Suno ajanları ve `suno-video-render` skill'i için):
    python suno_stil.py --proje "Bu Gece Kazandık"             # tür meta.json'dan
    python suno_stil.py --proje "Yeni Şarkı" --tur hiphop      # klasör henüz yoksa
    python suno_stil.py --proje "Yeni Şarkı" --tur hiphop --json

NEDEN VAR (2026-09-13, `suno_kalite_onerileri.md` §2 ve §7): mix cümlesi her
şarkıya birebir kopyalanıyordu. Aynı dizinin bütün katalogda tekrarlanması,
aynı Persona / aynı iskelet / aynı kapak düzeniyle üst üste binince kanalı
YouTube'un "toplu üretilmiş içerik" tanımına yaklaştıran şablon izlerinden biri.

SEÇİM DETERMİNİSTİK: her ifade `sha1("<ad>|<kategori>|<ifade>")` ile
sıralanıyor, ilk N'i alınıyor. Aynı şarkı için ajan komutu kaç kez çalıştırırsa
çalıştırsın aynı tarif çıkar; `hash()` KULLANILMIYOR (süreç başına tuzlanır,
her koşu farklı tarif verirdi — tests/test_suno_stil.py iki farklı
PYTHONHASHSEED ile bunu sınıyor). Ad NFC + kırpma + casefold ile normalize:
`_sozler.md`'den kopyalanan NFD bir "ı" başka tarif üretmesin.

Havuz `config.STIL_IFADE_HAVUZU`; kuralları (sanatçı adı / Suno / AI yok,
`wide vocal` yok) orada ve testte.

ÜÇ SORU (CLAUDE.md):
1. Kim çağırıyor? Suno'da stil tarifi yazan ajan/insan, elle; skill notu
   `.claude/skills/suno-video-render/SKILL.md`. Boru hattı ÇAĞIRMIYOR —
   stil tarifi Suno'ya gitmeden önce yazılıyor, render'dan çok önce.
2. Hangi zamanlayıcı? Hiçbiri, bilerek: bu bir üretim-öncesi yardımcı.
3. Çalışmadığını nasıl anlarız? Tür bulunamazsa sıfır olmayan çıkış kodu ve
   `--tur` iste diyen mesaj; sessizce boş tarif dönmüyor.
"""

import argparse
import hashlib
import json
import os
import sys
import unicodedata

import config

KATEGORI_ADET = (("mix", None), ("vokal", 1), ("duzenleme", 1))


def _normal_ad(ad: str) -> str:
    return unicodedata.normalize("NFC", ad).strip().casefold()


def _sirala(ad: str, kategori: str, secenekler: list) -> list:
    anahtar = _normal_ad(ad)
    return sorted(
        secenekler,
        key=lambda ifade: hashlib.sha1(
            ("%s|%s|%s" % (anahtar, kategori, ifade)).encode("utf-8")).hexdigest())


def stil_ifadeleri(proje: str, tur: str) -> dict:
    """`{"tur", "mix": [...], "vokal": [...], "duzenleme": [...], "cumle"}`.

    Bilinmeyen tür (DJ dahil) ValueError: sessizce başka türün havuzuna
    düşmek, rock şarkıya elektronik mix tarifi yazdırırdı."""
    havuz = config.STIL_IFADE_HAVUZU.get(tur)
    if havuz is None:
        raise ValueError("'%s' için stil havuzu yok (geçerli: %s)"
                         % (tur, ", ".join(sorted(config.STIL_IFADE_HAVUZU))))
    sonuc = {"tur": tur}
    parcalar = []
    for kategori, adet in KATEGORI_ADET:
        n = config.STIL_MIX_ADET if adet is None else adet
        secilen = _sirala(proje, kategori, havuz[kategori])[:n]
        sonuc[kategori] = secilen
        parcalar.extend(secilen)
    sonuc["cumle"] = ", ".join(parcalar)
    return sonuc


def turu_bul(proje: str, kokler=None):
    """Proje klasörü varsa `meta.json`daki `theme`; yoksa None."""
    import uyumluluk
    hedef = _normal_ad(proje)
    for klasor in uyumluluk.proje_klasorleri(kokler):
        if _normal_ad(os.path.basename(os.path.normpath(klasor))) != hedef:
            continue
        try:
            with open(os.path.join(klasor, "meta.json"), "r", encoding="utf-8") as f:
                return json.load(f).get("theme")
        except (OSError, ValueError):
            return None
    return None


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Suno stil tarifi için mix/vokal/düzenleme ifadeleri.")
    p.add_argument("--proje", required=True, help="Şarkı / proje klasörü adı")
    p.add_argument("--tur", help="Tür (pop, rock, elektronik, akustik, hiphop, arabesk). "
                                 "Verilmezse proje klasörünün meta.json'undan okunur.")
    p.add_argument("--json", action="store_true", help="Makine okunur çıktı")
    a = p.parse_args(argv)

    tur = a.tur or turu_bul(a.proje)
    if not tur:
        print("HATA: '%s' için tür bulunamadı (proje klasörü/meta.json yok). "
              "--tur ile ver." % a.proje, file=sys.stderr)
        return 2
    try:
        sonuc = stil_ifadeleri(a.proje, tur)
    except ValueError as e:
        print("HATA: %s" % e, file=sys.stderr)
        return 2

    if a.json:
        print(json.dumps(sonuc, ensure_ascii=False))
    else:
        print("tür: %s" % tur)
        print("mix/master: %s" % ", ".join(sonuc["mix"]))
        print("vokal:      %s" % ", ".join(sonuc["vokal"]))
        print("düzenleme:  %s" % ", ".join(sonuc["duzenleme"]))
        print("stil tarifine eklenecek cümle:")
        print(sonuc["cumle"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
