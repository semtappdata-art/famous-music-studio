# -*- coding: utf-8 -*-
"""`suno_ab_olcum.js` saf hesap fonksiyonları (2026-09-13).

Betik tarayıcıda (Suno sekmesinin konsolunda) koşuyor; depoda JS test altyapısı
YOK ve paket kurmak yasak. Bu yüzden: `node --check` ile sözdizimi, sonra
betiğin `module.exports` ile dışarı verdiği SAF fonksiyonlar (Web Audio'ya
dokunmayan hesaplar) küçük bir Node koşumuyla sentetik verilerde doğrulanıyor.
Node yoksa testler atlanır (sessiz değil: pytest "skipped" gösterir).

Tarayıcıya özgü kısım (AudioWorklet / ScriptProcessor toplayıcısı) burada
koşturulamıyor; yalnız kaynakta bulunduğu ve eski `setInterval` toplayıcısının
geri gelmediği doğrulanıyor. O toplayıcı 2026-09-13'te gizli sekmede 14 sn'de
15 örnek topladı: zamanlayıcılar arka plan sekmesinde kısıtlanıyor.
"""

import json
import os
import shutil
import subprocess

import pytest

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JS = os.path.join(_KOK, "suno_ab_olcum.js")
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="node kurulu değil")


def _kos(tmp_path, govde):
    betik = tmp_path / "kosum.js"
    betik.write_text(
        "const ab = require(process.argv[2]);\n"
        "const out = {};\n" + govde + "\n"
        "console.log(JSON.stringify(out));\n",
        encoding="utf-8")
    r = subprocess.run([NODE, str(betik), JS], capture_output=True, text=True,
                       encoding="utf-8", timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout.strip().splitlines()[-1])


def test_node_sozdizimi():
    r = subprocess.run([NODE, "--check", JS], capture_output=True, text=True,
                       encoding="utf-8", timeout=60)
    assert r.returncode == 0, r.stderr


def test_saf_fonksiyonlar_disari_veriliyor(tmp_path):
    out = _kos(tmp_path, "out.adlar = Object.keys(ab).sort();")
    for ad in ("kirpilmaSay", "kirpilmaBitir", "nakaratTespit", "crestDb",
               "sonSessizlik", "erkenSonme", "varyantFarki", "ozetle"):
        assert ad in out["adlar"], ad


def test_kaynakta_gizli_sekme_toplayicisi_var_setinterval_yok():
    kaynak = open(JS, encoding="utf-8").read()
    assert "audioWorklet" in kaynak
    assert "createScriptProcessor" in kaynak
    assert "setInterval" not in kaynak


def test_kirpilma_ardisik_ornek_ve_blok_siniri(tmp_path):
    out = _kos(tmp_path, """
const E = Math.pow(10, -0.1 / 20);
let d = ab.kirpilmaSay([0, 0.995, 0.996, 0.2, 0.999, 0.3, -0.995, -0.999, -0.9999], E);
out.tek = ab.kirpilmaBitir(d);
// Aynı ardışık dizi iki bloğa bölünmüş: sınırda kopmamalı.
let d2 = ab.kirpilmaSay([0.1, 0.995], E);
d2 = ab.kirpilmaSay([0.996, 0.1], E, d2);
out.bolunmus = ab.kirpilmaBitir(d2);
out.temiz = ab.kirpilmaBitir(ab.kirpilmaSay([0.5, -0.9, 0.98], E));
""")
    # İki olay: [0.995, 0.996] (2 örnek) ve [-0.995, -0.999, -0.9999] (3 örnek).
    # Tek başına 0.999 kırpılma OLAYI değil (ardışık değil), ama en uzun >= 1.
    assert out["tek"]["olay"] == 2
    assert out["tek"]["ornek"] == 5
    assert out["tek"]["en_uzun"] == 3
    assert out["bolunmus"]["olay"] == 1 and out["bolunmus"]["ornek"] == 2
    assert out["temiz"]["olay"] == 0 and out["temiz"]["ornek"] == 0


def _kayit_js(ifade_mid, bas=0, bit=60, adim=0.05, tepe="0.5"):
    return ("(() => { const k = []; for (let i = 0; ; i++) { const t = %s + i * %s;"
            " if (t >= %s) break; const mid = %s; k.push([+t.toFixed(3), mid, 0, %s]); }"
            " return k; })()" % (bas, adim, bit, ifade_mid, tepe))


def test_nakarat_enerji_artisi_tespiti(tmp_path):
    out = _kos(tmp_path, """
out.gec = ab.nakaratTespit(%s);
out.soguk = ab.nakaratTespit(%s);
out.sivri = ab.nakaratTespit(%s);
out.bos = ab.nakaratTespit([]);
""" % (_kayit_js("t < 32 ? 0.05 : 0.2"),
       _kayit_js("0.2"),
       _kayit_js("(t >= 10 && t < 10.5) ? 0.4 : (t < 40 ? 0.05 : 0.2)")))
    assert out["gec"] == 32.0
    assert out["soguk"] == 0.0                     # nakaratla açılan şarkı
    assert out["sivri"] == 40.0                    # 0,5 sn'lik tek sıçrama sayılmıyor
    assert out["bos"] is None


def test_crest_db(tmp_path):
    out = _kos(tmp_path, "out.c = ab.crestDb(%s);" % _kayit_js("0.25", bit=10, tepe="0.5"))
    assert abs(out["c"] - 6.02) < 0.05


def test_son_sessizlik(tmp_path):
    out = _kos(tmp_path, """
out.kuyruk = ab.sonSessizlik(%s, 186.5);
out.yok = ab.sonSessizlik(%s, 186.5);
""" % (_kayit_js("t < 184 ? 0.2 : 0.001", bas=180, bit=186.5),
       _kayit_js("0.2", bas=180, bit=186.5)))
    assert 2.4 <= out["kuyruk"] <= 2.6
    assert out["yok"] < 0.1


def test_erken_sonme(tmp_path):
    out = _kos(tmp_path, """
out.soner = ab.erkenSonme({40: 0.2, 60: 0.18, 80: 0.08});
out.saglam = ab.erkenSonme({40: 0.2, 60: 0.2, 80: 0.15});
out.eksik = ab.erkenSonme({40: 0.2});
""")
    assert out["soner"]["erken_sonme"] is True and abs(out["soner"]["oran"] - 0.4) < 1e-9
    assert out["saglam"]["erken_sonme"] is False
    assert out["eksik"] is None


def test_varyant_farki(tmp_path):
    out = _kos(tmp_path, """
const a = {MY_ortanca: 4.2, nakarat_sn: 30, crest_db: 9, sure: 170, son_sessizlik_sn: 0.4};
out.ayni = ab.varyantFarki(a, Object.assign({}, a));
out.farkli = ab.varyantFarki(a, {MY_ortanca: 2.1, nakarat_sn: 55, crest_db: 5, sure: 250,
                                 son_sessizlik_sn: 3.0});
out.eksikli = ab.varyantFarki(a, {MY_ortanca: 4.1, nakarat_sn: null, crest_db: 9});
""")
    assert out["ayni"]["karar"] == "esit_dinleyerek_sec" and out["ayni"]["skor"] == 0
    assert out["farkli"]["karar"] == "belirgin"
    for k in ("MY_ortanca", "nakarat_sn", "crest_db"):
        assert k in out["farkli"]["farklar"]
    assert out["eksikli"]["karar"] == "esit_dinleyerek_sec"


def test_ozetle_yeni_olcutler_ve_isaret_onceligi(tmp_path):
    out = _kos(tmp_path, """
const r = {
  sure: 250,
  bas: %s,
  son: %s,
  noktalar: {40: %s, 60: %s, 80: %s},
  kirpilma: {olay: 1, ornek: 3, en_uzun: 3},
};
out.enerji = ab.ozetle(r);
out.isaret = ab.ozetle(Object.assign({}, r, {nakarat_isaret: 41.3}));
""" % (_kayit_js("t < 32 ? 0.05 : 0.2"),
       _kayit_js("t < 247 ? 0.2 : 0.001", bas=243.5, bit=250),
       _kayit_js("0.2", bit=2), _kayit_js("0.18", bit=2), _kayit_js("0.05", bit=2)))
    e = out["enerji"]
    # Eski alanlar duruyor.
    for k in ("sure", "ilk_ses_sn", "MY_ortanca", "MY_max", "sustain_sn", "son_tepe_orani"):
        assert k in e, k
    assert e["nakarat_sn"] == 32.0 and e["nakarat_yontem"] == "enerji"
    assert e["kirpilma_olay"] == 1 and e["kirpilma_ornek"] == 3
    assert e["crest_db"] is not None
    assert 2.9 <= e["son_sessizlik_sn"] <= 3.1
    assert e["erken_sonme"] is True
    assert e["sure_asimi"] is True
    assert out["isaret"]["nakarat_sn"] == 41.3
    assert out["isaret"]["nakarat_yontem"] == "isaret"


def test_ozetle_eski_bicim_kayitla_cokmuyor(tmp_path):
    """14 sn'lik eski `olc()` sonuçları ([t, mid, yan], nokta/kırpılma yok)
    hâlâ özetlenebilmeli; yeni alanlar null."""
    out = _kos(tmp_path, """
const eski = { sure: 166.6,
  bas: (() => { const k = []; for (let t = 0; t < 14; t += 0.05) k.push([+t.toFixed(2), 0.1, 0.02]); return k; })(),
  son: (() => { const k = []; for (let t = 160; t < 166; t += 0.05) k.push([+t.toFixed(2), 0.1, 0.02]); return k; })() };
out.o = ab.ozetle(eski);
""")
    o = out["o"]
    assert o["MY_ortanca"] == 5.0
    assert o["erken_sonme"] is None and o["kirpilma_olay"] is None
