# -*- coding: utf-8 -*-
"""`tests/conftest.py` korumasının `derleme.HEDEF_KOK` için KANITI.

Neden ayrı bir dosya: conftest'teki autouse fixture'ın kapsamı bir liste
(`KORUNAN_YOL_ADLARI`) ve o listeden bir ad düşerse HİÇBİR test kırılmaz —
koruma sessizce yok olur, tam da CLAUDE.md'nin "sessizce False dönen koruma,
olmayan korumadan kötüdür" dediği sınıf. Bu dosya o boşluğu kapatıyor:
`derleme.HEDEF_KOK` bir testin içinden GÖRÜLDÜĞÜNDE depo dışını göstermek
ZORUNDA.

Neden önemli: `derleme.uret()` `HEDEF_KOK` altına önce `.tmp-<ad>` klasörü
açıyor, sonra `os.replace` ile `<HEDEF_KOK>/<ad>`e taşıyor. Yönlendirme
olmasaydı `uret()` çağıran ve yolu kendisi yamalamayan bir test, gerçek
`derlemeler/` klasörüne (yayınlanmış `Gece Seansı Vol. 1` ve 1,4 GB medyanın
yanına) yazardı — ve oradaki her klasör `dj_famous_process.py --base
derlemeler` için "bekleyen set" demek, yani yayın kuyruğu.

`derleme.uret()` BURADA ÇAĞRILMIYOR: gerçek bir üretim ffmpeg/render
gerektiriyor, saatler sürüyor ve diski dolduruyor. Bunun yerine `uret()`in
diske dokunduğu İKİ yol da (geçici + hedef) aynı sabitten türediği için
sabitin kendisi ve ona yazmanın nereye düştüğü doğrulanıyor.
"""

import os
import sys

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _KOK)

import derleme  # noqa: E402

_GERCEK = os.path.join(_KOK, "derlemeler")


def test_hedef_kok_depo_disina_cekiliyor():
    """Bir testin gördüğü HEDEF_KOK, gerçek `derlemeler/` OLAMAZ."""
    gorulen = os.path.abspath(derleme.HEDEF_KOK)
    assert gorulen != _GERCEK, (
        "derleme.HEDEF_KOK test içinde gerçek derlemeler/ klasörünü gösteriyor "
        "— tests/conftest.py'deki KORUNAN_YOL_ADLARI koruması düşmüş."
    )
    assert not gorulen.startswith(_KOK + os.sep), (
        "derleme.HEDEF_KOK hâlâ depo içinde: %s" % gorulen
    )


def test_uret_in_yazdigi_iki_yol_da_gercek_klasorun_disinda():
    """`uret()`in yazdığı `.tmp-<ad>` ve `<ad>` yolları depo dışına düşüyor."""
    ad = "Conftest Kanit Derlemesi"
    gecici = os.path.abspath(os.path.join(derleme.HEDEF_KOK, ".tmp-" + ad))
    hedef = os.path.abspath(os.path.join(derleme.HEDEF_KOK, ad))
    for yol in (gecici, hedef):
        assert not yol.startswith(_KOK + os.sep), yol

    # Gerçekten yazılabiliyor mu (yönlendirilen yolun ebeveyni var mı) ve
    # yazılan şey gerçek klasörde GÖRÜNMÜYOR mu — ikisi birden.
    os.makedirs(gecici, exist_ok=True)
    with open(os.path.join(gecici, "audio.wav"), "w", encoding="utf-8") as f:
        f.write("sahte")
    assert os.path.isfile(os.path.join(gecici, "audio.wav"))
    assert not os.path.exists(os.path.join(_GERCEK, ".tmp-" + ad))
    assert not os.path.exists(os.path.join(_GERCEK, ad))


def test_koruma_listesinde_hedef_kok_var():
    """Liste doğrudan da çivileniyor: ad düşerse mesaj net olsun."""
    import conftest

    assert "HEDEF_KOK" in conftest.KORUNAN_YOL_ADLARI
