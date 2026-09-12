# -*- coding: utf-8 -*-
"""`derleme.zaman_damgalari()` + `_mmss()` — ucuz ama gerçek koruma (C-11).

NEDEN VAR (2026-09-12 denetimi): `derleme.uret()` uçtan uca hiç test edilmemiş
ve ffmpeg `concat`/`acrossfade` zincirini test etmek pahalı. Ama zincirin
ARİTMETİĞİ saf: `zaman_damgalari()` ve `_mmss()` ne diske ne ağa dokunuyor.

KORUNAN ASIL SÖZLEŞME: damgalar YouTube açıklamasına bölüm işareti olarak
giriyor ve bir kez yayınlandıktan sonra düzeltmek elle iş. `ses_birlestir()`
her komşu çift arasında `acrossfade=d=GECIS_SN` uyguluyor, yani birleşik ses
her geçişte GECIS_SN kısalıyor; `zaman_damgalari()` aynı düşümü YAPMAK
ZORUNDA. İkisi AYRI fonksiyonda ve aralarında hiçbir bağ yok — biri değişip
diğeri kalırsa damgalar sessizce kayar ve bunu ancak izleyici fark eder.

ÇALIŞMADIĞINI NASIL ANLARIZ: `test_toplam_sure_acrossfade_zinciriyle_ayni`
düşer — damga aritmetiği ile filtre zinciri aritmetiği ayrışmıştır.
"""

import os
import sys

import pytest

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _KOK)

import derleme                                          # noqa: E402


def _p(ad, sure):
    return {"ad": ad, "sure": float(sure)}


# --- zaman_damgalari ------------------------------------------------------

def test_ilk_parca_sifirdan_basliyor():
    d = derleme.zaman_damgalari([_p("A", 200), _p("B", 180)])
    assert d[0] == {"ad": "A", "bas": 0.0}


def test_gecis_her_komsu_ciftte_dusuluyor():
    """İki geçiş = 2 × GECIS_SN kayma. Sabit değişirse test onu takip eder."""
    g = derleme.GECIS_SN
    d = derleme.zaman_damgalari([_p("A", 200), _p("B", 180), _p("C", 240)])
    assert [x["ad"] for x in d] == ["A", "B", "C"]
    assert d[1]["bas"] == pytest.approx(200 - g)
    assert d[2]["bas"] == pytest.approx(200 - g + 180 - g)


def test_son_parcadan_gecis_dusulmuyor():
    """Son parçadan sonra geçiş YOK — düşülürse toplam süre kısa çıkar."""
    g = derleme.GECIS_SN
    d = derleme.zaman_damgalari([_p("A", 100), _p("B", 100)])
    toplam = d[-1]["bas"] + 100
    assert toplam == pytest.approx(200 - g)


def test_toplam_sure_acrossfade_zinciriyle_ayni():
    """ASIL SÖZLEŞME: damga aritmetiği = filtre zinciri aritmetiği.

    `ses_birlestir()` n-1 kez `acrossfade=d=GECIS_SN` uyguluyor; birleşik
    sesin süresi bu yüzden `toplam - (n-1)*GECIS_SN`. `uret()` toplam süreyi
    `damga[-1]["bas"] + son["sure"]` ile hesaplıyor — ikisi EŞİT OLMALI.
    """
    g = derleme.GECIS_SN
    sureler = [212.0, 187.5, 240.0, 199.0, 176.25]
    secilen = [_p("P%d" % i, s) for i, s in enumerate(sureler)]
    d = derleme.zaman_damgalari(secilen)
    damgadan = d[-1]["bas"] + sureler[-1]
    zincirden = sum(sureler) - (len(sureler) - 1) * g
    assert damgadan == pytest.approx(zincirden, abs=0.1)


def test_damgalar_KESINLIKLE_artan():
    """Geriye giden bir bölüm işareti YouTube'da sessizce yok sayılır."""
    secilen = [_p("A", 210), _p("B", 195), _p("C", 230), _p("D", 205)]
    baslar = [x["bas"] for x in derleme.zaman_damgalari(secilen)]
    assert baslar == sorted(baslar)
    assert len(set(baslar)) == len(baslar)


def test_bos_ve_tek_parca_cokmuyor():
    """`uret()` bu durumları daha önce eleyor, ama fonksiyon saf kalmalı."""
    assert derleme.zaman_damgalari([]) == []
    assert derleme.zaman_damgalari([_p("A", 120)]) == [{"ad": "A", "bas": 0.0}]


# --- _mmss ----------------------------------------------------------------

@pytest.mark.parametrize("sn,beklenen", [
    (0, "0:00"),
    (9, "0:09"),
    (59, "0:59"),
    (60, "1:00"),
    (61, "1:01"),
    (599, "9:59"),
    (600, "10:00"),
    (3599, "59:59"),
    (3600, "1:00:00"),                       # saat eşiği: formatın değiştiği yer
    (3661, "1:01:01"),
    (7325, "2:02:05"),
])
def test_mmss_bicimi(sn, beklenen):
    assert derleme._mmss(sn) == beklenen


def test_mmss_kesirli_saniyeyi_ASAGI_yuvarliyor():
    """Damgalar `round(t, 1)` ile kesirli geliyor — bölüm işareti tam saniye.

    Yukarı yuvarlamak işareti parçanın BİR SONRAKİ karesine kaydırırdı;
    aşağı yuvarlamak en kötü ihtimalle bir saniye erken başlatır.
    """
    assert derleme._mmss(59.9) == "0:59"
    assert derleme._mmss(3599.9) == "59:59"


def test_mmss_dakika_alani_iki_haneli():
    """"1:5" gibi bir çıktı YouTube tarafından bölüm işareti SAYILMAZ."""
    for sn in range(0, 4000, 7):
        m = derleme._mmss(sn)
        assert len(m.split(":")[-1]) == 2, m
        assert len(m.split(":")[-2]) == 2 or m.count(":") == 1, m


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
