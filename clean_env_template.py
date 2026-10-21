# -*- coding: utf-8 -*-
"""
.env.template icindeki GERCEK anahtarlari placeholder ile degistirir.

GUVENLIK (2026-10-21): .env.template dosyasinda 13 gercek API anahtari
sizmis ti (OpenRouter, Together, Google, HF, Runway, Higgsfield, Stability,
Luma, Pika, Kling, MiniMax, Haiper, Postwire). GitHub secret scanning
push'u reddetti ve bu anahtarlar repo history'sinde kaliyor.

Bu script:
  1) .env.template'teki tum anahtar degerlerini placeholder yapar
  2) Eski anahtarlari dosyadan tamamen siler (gizli degil, gecmis temizligi)
  3) Kullaniciya rotate edilecek anahtar listesini raporlar

NOT: Anahtarlarin GERCEKTEN rotate edilmesi saglayicida (dashboard'dan)
yapilmalidir. Bu script sadece sizintiyi kapatir.
"""
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

YOL = ".env.template"

# Deger gercek-gini gibi gorunen anahtar adlari (placeholder olmayanlar)
GERCEK_DESEN = re.compile(
    r"^([A-Z_]*(?:API_KEY|TOKEN|SECRET|PASSWORD)[A-Z_]*)=(.+)$",
    re.MULTILINE,
)

# Placeholder kaliplari (bunlar zaten guvenli)
GUVENLI_DEGER_DESEN = re.compile(
    r"^(x{8,}|YOUR_[A-Z_]*|xxx+|<[^>]+>|changeme|placeholder|"
    r"sk-or-v1-[0-9a-f]{8,}|gsk_x+|hf_[a-zA-Z0-9]{8,})$"
)


def main():
    with open(YOL, encoding="utf-8") as f:
        icerik = f.read()

    degisen = []
    sifreli = []

    def degistir(m):
        ad, deger = m.group(1), m.group(2).strip()
        # zaten guvenli mi?
        if GUVENLI_DEGER_DESEN.match(deger):
            return m.group(0)
        # gercek anahtar -> placeholder
        sifreli.append(ad)
        return "%s=YOUR_%s_HERE" % (ad, ad)

    yeni = GERCEK_DESEN.sub(degistir, icerik)

    if yeni != icerik:
        with open(YOL, "w", encoding="utf-8") as f:
            f.write(yeni)
        print("  .env.template guncellendi")

    print("\n  TEMIZLENEN ANAHTARLAR (%d):" % len(sifreli))
    for a in sifreli:
        print("    - %s" % a)

    print("\n  ! BU ANAHTARLAR ARTIK SIZINTILI: rotate ET (dashboard'dan yeni anahtar al)")
    print("    OpenRouter  : https://openrouter.ai/keys")
    print("    Together   : https://api.together.xyz/settings/api-keys")
    print("    Google     : https://aistudio.google.com/app/apikey")
    print("    HuggingFace: https://huggingface.co/settings/tokens")
    print("    Postwire   : https://app.postwire.io")
    print("    Runway/Higgsfield/Stability/Luma/Pika/Kling/MiniMax/Haier")
    print("      -> ilgili dashboard'dan rotate et")
    return 0


if __name__ == "__main__":
    sys.exit(main())
