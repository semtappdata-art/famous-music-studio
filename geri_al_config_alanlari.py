# -*- coding: utf-8 -*-
"""
config.py'den KAYIP 77 alani geri getirir.

NEDEN (2026-10-21): `c4caed5` commit'inde `config.py` UZERINE YAZILDI ve
o anki surumde olmayan 77 ust-duzey sabit dustu. Bunlar:
  - TIKTOK_SET_HOOKS_EN / TIKTOK_SET_SORULARI_EN / TIKTOK_DERLEME_HOOKS
    -> TikTok kit uretimi AttributeError ile PATIYORDU
  - YAYIN_RITMI_* (5) -> yayin ritmi kurallari varsayilana dusuyordu
  - TUREV_* (18) -> turev takvimi calismiyordu
  - YOUTUBE_* (8), *_CONVERSION_RATE_TARGET (8) -> buyume/analitik hedefleri
  - SES_LIMITER_*, END_SCREEN_*, STIL_* -> diger kural ayarlari

Yontem: eski config.py (c4caed5^) AST ile cozulur, kayip tanimlar
KENDI ARALARINDAKI BAGIMLILIK SIRASI korunarak yeniden config.py'ye yazilir
(tek bir blok halinde, sona eklenir).
"""
import ast
import io
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

REPO = "."


def _ustel_atamalar(src):
    """[(ad, kaynak_metni)] — dosyadaki SIRAYA gore."""
    agac = ast.parse(src)
    cikti = []
    for node in agac.body:
        adlar = []
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    adlar.append(t.id)
            deger_node = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            adlar.append(node.target.id)
            deger_node = node.value
        else:
            continue
        for ad in adlar:
            seg = ast.get_source_segment(src, node)
            if seg:
                cikti.append((ad, seg))
    return cikti


def main():
    eski_src = subprocess.run(
        ["git", "show", "c4caed5^:config.py"], capture_output=True, text=True,
        encoding="utf-8", errors="replace", cwd=REPO).stdout
    if not eski_src:
        print("HATA: eski config.py alinamadi")
        return 1
    yeni_src = io.open("config.py", encoding="utf-8").read()

    eski_atamalar = _ustel_atamalar(eski_src)
    yeni_adlar = {ad for ad, _ in _ustel_atamalar(yeni_src)}
    kayip = [(ad, seg) for ad, seg in eski_atamalar if ad not in yeni_adlar]

    if not kayip:
        print("  Kayip alan yok — config.py guncel")
        return 0

    baslik = (
        "\n# ==========================================================================\n"
        "# GERI GETIRILEN ALANLAR (2026-10-21)\n"
        "# --------------------------------------------------------------------------\n"
        "# `c4caed5` commit'inde config.py uzerine yazildi ve asagidaki %d sabit\n"
        "# dustu. Bunlarin BIRI TikTok kit uretimini AttributeError ile patiriyordu,\n"
        "# digerleri yayin ritmi / turev takvimi / buyume hedeflerini varsayilana\n"
        "# dusuruyordu. Kaynak: git show c4caed5^:config.py\n"
        "# SIRA KORUNARAK geri eklendi (aralarindaki bagimliliklar bozulmaz).\n"
        "# ==========================================================================\n"
    ) % len(kayip)

    govde = baslik + "\n" + "\n\n".join(seg for _, seg in kayip) + "\n"

    # config.py'nin sonuna ekle (import'lar ve ana govde bozulmaz)
    yeni_src = yeni_src.rstrip("\n") + "\n" + govde
    io.open("config.py", "w", encoding="utf-8").write(yeni_src)
    print("  config.py: %d alan geri getirildi" % len(kayip))

    # dogrulama
    yeni_adlar2 = {ad for ad, _ in _ustel_atamalar(io.open("config.py", encoding="utf-8").read())}
    eksik = [ad for ad, _ in kayip if ad not in yeni_adlar2]
    if eksik:
        print("  HATA: hala eksik: %s" % eksik[:5])
        return 1
    print("  dogrulama: %d alanin tamami yerinde" % len(kayip))
    return 0


if __name__ == "__main__":
    sys.exit(main())
