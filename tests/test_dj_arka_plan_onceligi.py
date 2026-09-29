# -*- coding: utf-8 -*-
"""DJ arka planı ÖNCELİK SIRASI (dj_famous_process._arka_plani_hazirla).

Kilitlenen davranış — ESKİ SESSİZ ARIZA:
`set_icin_arka_plan` yalnızca `else` dalındaydı, yani `DJ_ARDA_GORSELLERI=True`
olan her sette bölüm-sahne sistemi ÖLÜ KODDU. `Deep-Medusa`'nın
`sahne_parti.json`'ı (5 yat sahnesi) ve `bolumler.json`'ı (13 bölüm) diskte
duruyor ama videoya hiç girmiyordu; yerine `arda_tshirt_slideshow_45s.mp4`
38 dakika dönüyordu. Bu dalın testi de yoktu.

Sıra artık: (1) sahne zaman çizgisi (dosyalar diskte) → (2) Arda döngüsü →
(3) stok havuz. Sahnesi OLMAYAN setler eskisi gibi Arda döngüsünü alır.
"""
import ast
import json
import os

import pytest

import dj_famous_process as djp
import config


def _sahne_seti(kok: str, sahne_dosyalari: bool = True) -> str:
    """Minimum bir bölüm-sahne seti kurar (dosyalar isteğe bağlı)."""
    set_dir = os.path.join(kok, "Test Set")
    os.makedirs(set_dir, exist_ok=True)
    with open(os.path.join(set_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump({"title": "Test Set", "theme": "dj"}, f)
    with open(os.path.join(set_dir, "bolumler.json"), "w", encoding="utf-8") as f:
        json.dump({"parcalar": [
            {"sira": 1, "ad": "Opening", "bas": 0, "zaman": "0:00"},
            {"sira": 2, "ad": "Rise", "bas": 60, "zaman": "1:00"},
        ]}, f)
    with open(os.path.join(set_dir, "sahne_parti.json"), "w", encoding="utf-8") as f:
        json.dump({"sahneler": [
            {"id": "hero", "bas": "Opening", "bitis": "Rise", "dosya": "sahne_hero.png"},
        ]}, f)
    if sahne_dosyalari:
        # bolum_sahneleri() ses süresini ffprobe ile okur; küçük bir wav üret.
        import subprocess
        ses = os.path.join(set_dir, "audio.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
                        "-i", "sine=frequency=440:duration=90", ses],
                       capture_output=True, text=True, check=False)
        if not os.path.isfile(ses):
            pytest.skip("ffmpeg yok — ses üretilemedi")
        with open(os.path.join(set_dir, "sahne_hero.png"), "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n")
    return set_dir


@pytest.fixture()
def arda_arka_plani(monkeypatch, tmp_path):
    """Arda döngüsü VAR gibi davran (config'i geçici olarak işaretle)."""
    yol = tmp_path / "arda.mp4"
    yol.write_bytes(b"arda")
    monkeypatch.setattr(config, "DJ_ARKA_PLAN_VIDEO", True, raising=False)
    monkeypatch.setattr(config, "DJ_ARDA_GORSELLERI", True, raising=False)
    monkeypatch.setattr(config, "DJ_ARDA_BACKDROP", str(yol), raising=False)
    return yol


def test_sahne_cizgisi_arda_dongusunu_ezer(monkeypatch, tmp_path, arda_arka_plani):
    """ASIL KORUMA: sahnesi olan set Arda döngüsünü DEĞİL sahne hattını kullanır."""
    set_dir = _sahne_seti(str(tmp_path))
    if not os.path.isfile(os.path.join(set_dir, "audio.wav")):
        pytest.skip("ses yok")
    cagrilar = {"sahne": 0, "kopya": 0}

    import stock_video
    gercek = stock_video.set_icin_arka_plan

    def _sahte_set(yol, zorla=False):
        cagrilar["sahne"] += 1
        return os.path.join(yol, "backdrop.mp4")

    def _sahte_kopya(*a, **k):
        cagrilar["kopya"] += 1

    monkeypatch.setattr(stock_video, "set_icin_arka_plan", _sahte_set)
    monkeypatch.setattr("shutil.copy2", _sahte_kopya)
    djp._arka_plani_hazirla(set_dir)
    assert cagrilar["sahne"] == 1, "sahne hattı çağrılmalıydı"
    assert cagrilar["kopya"] == 0, "Arda döngüsü sahneyi EZMEMELİ"
    assert gercek is not None  # gerçek fonksiyon yerinde kalsın (yanlış import koruması)


def test_sahnesi_olmayan_set_arda_dongusunu_alir(monkeypatch, tmp_path, arda_arka_plani):
    """Sahne çizgisi olmayan set eskisi gibi Arda döngüsüne düşer."""
    set_dir = os.path.join(tmp_path, "Sahnesiz Set")
    os.makedirs(set_dir)
    with open(os.path.join(set_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump({"title": "Sahnesiz Set", "theme": "dj"}, f)
    cagrilar = {"sahne": 0}

    import stock_video

    def _sahte_set(yol, zorla=False):
        cagrilar["sahne"] += 1
        return None

    monkeypatch.setattr(stock_video, "set_icin_arka_plan", _sahte_set)
    djp._arka_plani_hazirla(set_dir)
    assert cagrilar["sahne"] == 0, "sahnesiz set Arda döngüsünü almalıydı"
    assert os.path.isfile(os.path.join(set_dir, "backdrop.mp4"))


def test_sahne_dosyalari_eksikse_arda_dongusune_duser(monkeypatch, tmp_path, arda_arka_plani):
    """Yarım kalmış sahne seti sessizce Arda döngüsüne düşer (üretim durmaz)."""
    set_dir = _sahne_seti(str(tmp_path), sahne_dosyalari=False)
    cagrilar = {"sahne": 0}

    import stock_video

    def _sahte_set(yol, zorla=False):
        cagrilar["sahne"] += 1
        return None

    monkeypatch.setattr(stock_video, "set_icin_arka_plan", _sahte_set)
    djp._arka_plani_hazirla(set_dir)
    assert cagrilar["sahne"] == 0
    assert os.path.isfile(os.path.join(set_dir, "backdrop.mp4"))


def test_arka_plan_video_kapaliysa_hicbir_sey_yapmaz(monkeypatch, tmp_path, arda_arka_plani):
    monkeypatch.setattr(config, "DJ_ARKA_PLAN_VIDEO", False, raising=False)
    set_dir = _sahne_seti(str(tmp_path))
    djp._arka_plani_hazirla(set_dir)
    assert not os.path.isfile(os.path.join(set_dir, "backdrop.mp4"))


def test_sira_ast_ile_kilitli():
    """Kaynak sırası muhafızı: sahne kontrolü copy2'den ÖNCE gelmeli.

    Davranış testi config'e bağlı; bu muhafız kodu okuyup sırayı kilitler —
    biri satırları geri alırsa (Arda bloğu yeniden başa geçerse) burada patlar.
    """
    kaynak = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "dj_famous_process.py")
    with open(kaynak, encoding="utf-8") as f:
        agac = ast.parse(f.read())
    bulundu = False
    for dugum in ast.walk(agac):
        if isinstance(dugum, ast.FunctionDef) and dugum.name == "_arka_plani_hazirla":
            bulundu = True
            satirlar = {}
            for alt in ast.walk(dugum):
                metin = ast.dump(alt)
                if "set_icin_arka_plan" in metin and isinstance(alt, ast.Attribute):
                    satirlar.setdefault("sahne", alt.lineno)
                if "copy2" in metin and isinstance(alt, ast.Attribute):
                    satirlar.setdefault("kopya", alt.lineno)
            assert "sahne" in satirlar and "kopya" in satirlar, satirlar
            assert satirlar["sahne"] < satirlar["kopya"], (
                "sahne hattı Arda kopyasından ÖNCE gelmeli — eski sessiz arıza: "
                "sahne sistemi yalnızca else dalında kaldığı için ölü koddu")
    assert bulundu, "_arka_plani_hazirla bulunamadı"


def test_process_set_arka_plani_cagiriyor():
    """process_set backdrop hazırlığını TEK yerden çağırır (satır içi kopya yok)."""
    kaynak = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "dj_famous_process.py")
    with open(kaynak, encoding="utf-8") as f:
        kaynak_metin = f.read()
    assert "copy2(" not in kaynak_metin.split("def _arka_plani_hazirla")[1] \
        .split("def process_set")[1], \
        "process_set içinde satır içi Arda kopyası kalmamalı"
    assert "_arka_plani_hazirla(project_dir)" in kaynak_metin
