# -*- coding: utf-8 -*-
"""state_io._atomik_yaz() testleri — YARIM state.json'u kilitliyor.

NEDEN: uc ayri yerde state.json dogrudan `open(..., "w")` ile hedefin ustune
yaziliyordu. `open` dosyayi once SIFIRLIYOR; `json.dump` bitmeden surec olurse
diskte yarim bir JSON kaliyor. 2026-09-11'de uyumluluk._durum() sertlestirildi
ve bozuk bir state.json artik HATA uretip yayini durduruyor — yani yarim bir
yazim tum boru hattini durdurur. Bu testler yazma tarafinin bunu bir daha
uretemeyecegini kilitliyor.
"""

import json
import os

import pytest

import state_io


def _oku(yol):
    with open(yol, "r", encoding="utf-8") as f:
        return json.load(f)


def test_tam_yazar_ve_tmp_birakmaz(tmp_path):
    hedef = str(tmp_path / "state.json")
    veri = {"youtube_video_id": "abc123", "tr": "Türkçe ğüşıöç", "n": 42}

    state_io._atomik_yaz(hedef, veri)

    assert _oku(hedef) == veri
    # .tmp os.replace ile TUKETILMIS olmali — kalirsa hem cop hem (gitignore
    # olmasaydi) commit'lenecek bir artik.
    assert not os.path.exists(hedef + ".tmp")
    assert sorted(os.listdir(str(tmp_path))) == ["state.json"]


def test_turkce_karakterler_escape_edilmiyor(tmp_path):
    # ensure_ascii=False: dosya elle de okunabilir kalsin (deponun aliskanligi).
    hedef = str(tmp_path / "state.json")
    state_io._atomik_yaz(hedef, {"ad": "Küllerimden Geç"})
    ham = open(hedef, "r", encoding="utf-8").read()
    assert "Küllerimden Geç" in ham


def test_yarida_kesilen_yazim_ESKI_dosyayi_bozmuyor(tmp_path, monkeypatch):
    """ASIL KORUMA: yazim ortasinda surec olurse hedef ESKI halinde kalmali.

    Eski kod (`open(hedef, "w")` + json.dump) bu senaryoda hedefi sifirlanmis
    ya da yarim birakiyordu; uyumluluk._durum() onu DurumBozuk sayip yayini
    durdururdu. Kesinti `json.dump`in ortasinda patlayarak taklit ediliyor.
    """
    hedef = str(tmp_path / "state.json")
    eski = {"telif_araliklari": [[0, 30]], "telif_eser": "Bring Me To Life"}
    state_io._atomik_yaz(hedef, eski)

    gercek_dump = json.dump

    def patlayan_dump(veri, f, **kw):
        # Biraz yazip ortada oluyoruz — gercek bir kill/guc kesintisi gibi.
        f.write('{\n  "telif_ara')
        raise KeyboardInterrupt("guc kesintisi taklidi")

    monkeypatch.setattr(state_io.json, "dump", patlayan_dump)
    with pytest.raises(KeyboardInterrupt):
        state_io._atomik_yaz(hedef, {"telif_araliklari": [], "yeni": True})
    monkeypatch.setattr(state_io.json, "dump", gercek_dump)

    # Hedef DOKUNULMAMIS: telif kapisi hala kapali.
    assert _oku(hedef) == eski
    # Yarim veri .tmp'de kaldi (bu yuzden .gitignore'a *.json.tmp eklendi).
    assert os.path.exists(hedef + ".tmp")


def test_durum_yaz_proje_klasorune_yazar(tmp_path):
    proje = tmp_path / "city_pulse_set"
    proje.mkdir()
    state_io.durum_yaz(str(proje), {"dj_tarama_temiz": True})
    assert _oku(str(proje / "state.json")) == {"dj_tarama_temiz": True}


def test_uyumluluk_atomik_yazilan_dosyayi_okuyabiliyor(tmp_path):
    """Uctan uca: yazan taraf ile sertlestirilen okuyan taraf uyusuyor mu."""
    import uyumluluk
    proje = tmp_path / "proje"
    proje.mkdir()
    state_io.durum_yaz(str(proje), {"youtube_uploaded_at": "2026-09-11T12:00:00"})
    assert uyumluluk._durum(str(proje))["youtube_uploaded_at"].startswith("2026")


def test_kaydet_ve_update_state_atomik_yolu_kullaniyor(tmp_path):
    """Uc cagri noktasindan ikisi gercekten state_io'ya bagli mi.

    (Ucuncusu dj_famous_process._kaydet_durum; o dosyada baska bir ajan
    calistigi icin bu turda dokunulmadi.)
    """
    import dj_tarama_kontrol
    proje = tmp_path / "set"
    proje.mkdir()
    dj_tarama_kontrol._kaydet(str(proje), {"a": 1})
    dj_tarama_kontrol._kaydet(str(proje), {"b": 2})
    assert _oku(str(proje / "state.json")) == {"a": 1, "b": 2}
    assert not os.path.exists(str(proje / "state.json.tmp"))

    import sys
    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "upload"))
    import youtube_upload
    youtube_upload._update_state(str(proje), {"youtube_video_id": "xyz"})
    st = _oku(str(proje / "state.json"))
    assert st == {"a": 1, "b": 2, "youtube_video_id": "xyz"}
    assert not os.path.exists(str(proje / "state.json.tmp"))
