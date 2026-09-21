"""notify.py testleri — SAHTE bir HTTP katmanıyla.

NEDEN (2026-09-11): `notify_config.json` repo kökünde hiç oluşturulmamıştı,
`send()` her çağrıda sessizce False dönüyordu ve telefona bugüne kadar TEK BİR
bildirim gitmemişti — buna bağlı tüm emniyet ağları (TikTok taslak hatırlatması,
watch_projects nabzı, token/karantina uyarıları, haftalık rapor) ölüydü.
Bu testler iki şeyi çiviliyor: (1) kanal kuruluyken DOĞRU URL/gövde/başlıkla
istek atılıyor ve True dönüyor, (2) kanal kurulu değilken sessiz kalmıyor
(koşu başına BİR kez log'a uyarı düşüyor).

GERÇEK ntfy.sh isteği ATILMIYOR — `requests.post` her testte sahtesiyle
değiştiriliyor; sahte katman kurulmadan bir istek denenirse test patlar.
"""

import io
import json
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "upload"))

import notify


class _SahteYanit:
    def __init__(self, kod=200):
        self.status_code = kod

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("HTTP %s" % self.status_code)


@pytest.fixture(autouse=True)
def _temiz_durum(monkeypatch):
    """Her test kendi 'koşu'su gibi başlasın: uyarı hafızası sıfırlanır ve
    gerçek ağ çağrısı imkânsız hale getirilir."""
    notify._uyarilanlar.clear()

    def _yasak(*a, **k):
        raise AssertionError("GERÇEK HTTP isteği denendi — test sahte katman kullanmalı")

    monkeypatch.setattr(notify.requests, "post", _yasak)
    yield
    notify._uyarilanlar.clear()


def _config_yaz(monkeypatch, tmp_path, icerik):
    p = tmp_path / "notify_config.json"
    p.write_text(json.dumps(icerik), encoding="utf-8")
    monkeypatch.setattr(notify, "_CONFIG_PATH", str(p))
    return p


def _sahte_main_log(monkeypatch, tmp_path):
    """Çalışan scriptin LOG_PATH'ini taklit et (auto_process.py deseni)."""
    log_path = tmp_path / "auto_process.log"
    sahte_main = types.ModuleType("__main__")
    sahte_main.LOG_PATH = str(log_path)
    monkeypatch.setitem(sys.modules, "__main__", sahte_main)
    return log_path


def test_send_dogru_url_govde_ve_baslikla_gidiyor(monkeypatch, tmp_path):
    _config_yaz(monkeypatch, tmp_path, {"ntfy_topic": "fms-test-konusu-123"})
    cagrilar = []

    def _sahte_post(url, data=None, headers=None, timeout=None):
        cagrilar.append({"url": url, "data": data, "headers": headers, "timeout": timeout})
        return _SahteYanit(200)

    monkeypatch.setattr(notify.requests, "post", _sahte_post)

    assert notify.send("TikTok", "'Gece Sürüşü' taslak bekliyor — yayınla.") is True
    assert len(cagrilar) == 1
    c = cagrilar[0]
    # 2026-09-11: baslik artik HTTP header'inda DEGIL, JSON govdesinde — header'lar
    # latin-1 ile kodlaniyor ve Turkce i/I/s/g patliyordu. ntfy'nin JSON publish
    # uc noktasi kok yola POST istiyor, konu adi govdede gidiyor.
    assert c["url"] == "https://ntfy.sh/"
    govde = json.loads(c["data"].decode("utf-8"))
    assert govde["topic"] == "fms-test-konusu-123"
    assert govde["title"] == "TikTok"
    assert govde["message"] == "'Gece Sürüşü' taslak bekliyor — yayınla."
    assert govde["priority"] == 3
    assert c["headers"] == {"Content-Type": "application/json"}
    assert c["timeout"] == (5, 10)

def test_config_yokken_send_false_ve_kosu_basina_tek_uyari(monkeypatch, tmp_path):
    monkeypatch.setattr(notify, "_CONFIG_PATH", str(tmp_path / "yok.json"))
    log_path = _sahte_main_log(monkeypatch, tmp_path)

    assert notify.is_configured() is False
    # 17 projelik bir koşuyu taklit et
    for _ in range(17):
        assert notify.send("TikTok", "mesaj") is False

    satirlar = [s for s in io.open(log_path, encoding="utf-8").read().splitlines() if s.strip()]
    assert len(satirlar) == 1, satirlar  # 17 kez değil, bir kez
    assert "kanali kurulu DEGIL" in satirlar[0]


def test_bozuk_json_da_sessiz_kalmiyor(monkeypatch, tmp_path):
    p = tmp_path / "notify_config.json"
    p.write_text("{bozuk", encoding="utf-8")
    monkeypatch.setattr(notify, "_CONFIG_PATH", str(p))
    log_path = _sahte_main_log(monkeypatch, tmp_path)

    assert notify.is_configured() is False
    assert notify.send("X", "y") is False
    assert "kanali kurulu DEGIL" in io.open(log_path, encoding="utf-8").read()


def test_gonderim_hatasi_da_bir_kez_loglaniyor(monkeypatch, tmp_path):
    _config_yaz(monkeypatch, tmp_path, {"ntfy_topic": "fms-test"})
    log_path = _sahte_main_log(monkeypatch, tmp_path)

    def _patlayan_post(*a, **k):
        raise OSError("ağ yok")

    monkeypatch.setattr(notify.requests, "post", _patlayan_post)

    assert notify.send("X", "y") is False
    assert notify.send("X", "y") is False
    satirlar = [s for s in io.open(log_path, encoding="utf-8").read().splitlines() if s.strip()]
    assert len(satirlar) == 1
    assert "gonderilemedi" in satirlar[0]


def test_http_500_false_donuyor(monkeypatch, tmp_path):
    _config_yaz(monkeypatch, tmp_path, {"ntfy_topic": "fms-test"})
    _sahte_main_log(monkeypatch, tmp_path)
    monkeypatch.setattr(notify.requests, "post", lambda *a, **k: _SahteYanit(500))
    assert notify.send("X", "y") is False


def test_log_path_yoksa_patlamiyor(monkeypatch, tmp_path):
    """saglik_kontrol.py gibi LOG_PATH tanımlamayan scriptlerde stderr'e düşer."""
    monkeypatch.setattr(notify, "_CONFIG_PATH", str(tmp_path / "yok.json"))
    monkeypatch.setitem(sys.modules, "__main__", types.ModuleType("__main__"))
    assert notify.send("X", "y") is False


def test_tiktok_bildirimi_kanal_yokken_golden_houra_bakmadan_cikiyor(monkeypatch, tmp_path):
    """Yanıltıcı log satırının kaynağı: kanal yokken de 'golden-hour bekleniyor'
    deniyordu. Artık kanal kontrolü ÖNCE ve sebep açıkça yazılıyor."""
    import config
    import tiktok_upload

    monkeypatch.setattr(notify, "_CONFIG_PATH", str(tmp_path / "yok.json"))
    log_path = _sahte_main_log(monkeypatch, tmp_path)

    def _golden_hour_cagrilmamali():
        raise AssertionError("kanal yokken golden-hour kontrolüne gidilmemeli")

    monkeypatch.setattr(config, "next_golden_publish_time", _golden_hour_cagrilmamali)

    # İki bekleyen proje — uyarı yine de tek satır
    for ad in ("p1", "p2"):
        d = tmp_path / ad
        d.mkdir()
        (d / "state.json").write_text(
            json.dumps({"tiktok_publish_id": "abc"}), encoding="utf-8"
        )
        assert tiktok_upload.notify_pending_publish(str(d)) is False

    satirlar = [s for s in io.open(log_path, encoding="utf-8").read().splitlines() if s.strip()]
    assert len(satirlar) == 1, satirlar
    assert "golden-hour" in satirlar[0] and "DEGIL" in satirlar[0]
