# -*- coding: utf-8 -*-
"""WaveSpeed sağlayıcısı (sahne_parti_uret._wavespeed_uret).

Kilitlenen davranış — FATURA KURALI:
- Gönderim POST'u BİR kez atılır; bağlantı hatasında TEKRAR YOK (çift
  üretim = çift fatura). Bu deponun Instagram `media_publish` kuralıyla
  aynı sınıf: yanıt kaybolduysa iş yapılmış olabilir.
- Yoklama GET'i idempotent: ağ hatası/429/5xx'te devam eder.
- `completed` + outputs URL'i → indir + PNG doğrula; terminal durumda
  (`failed`/`cancelled`/`timeout`/`deleted`) False.
- Anahtar yoksa ağa ÇIKILMAZ (fail-closed).
"""
import importlib.util
import os

import pytest

BETIK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "dj_sets", "Deep-Medusa", "sahne_parti_uret.py")


def _yukle():
    spec = importlib.util.spec_from_file_location("sahne_parti_uret", BETIK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Yanit:
    def __init__(self, status_code=200, govde=None):
        self.status_code = status_code
        self._govde = govde if govde is not None else {}

    def json(self):
        return self._govde


@pytest.fixture()
def mod():
    return _yukle()


def _anahtar(monkeypatch):
    monkeypatch.setenv("WAVESPEED_API_KEY", "test-anahtar")


def test_anahtar_yoksa_aga_cikilmaz(mod, monkeypatch, tmp_path):
    monkeypatch.delenv("WAVESPEED_API_KEY", raising=False)
    cagrilar = []

    class _SahteRequests:
        @staticmethod
        def post(*a, **k):
            cagrilar.append("post")
            raise AssertionError("ağa çıkılmamalıydı")

    monkeypatch.setitem(__import__("sys").modules, "requests", _SahteRequests())
    assert mod._wavespeed_uret("x", str(tmp_path / "a.png")) is False
    assert cagrilar == []


def test_post_baglanti_hatasinda_tekrar_yok(mod, monkeypatch, tmp_path):
    """Fatura kuralı: POST ConnectionError verirse ikinci POST YOK, GET YOK."""
    _anahtar(monkeypatch)
    sayim = {"post": 0, "get": 0}

    import requests as _gercek

    def _sahte_post(*a, **k):
        sayim["post"] += 1
        raise _gercek.ConnectionError("kopuk")

    def _sahte_get(*a, **k):
        sayim["get"] += 1
        raise AssertionError("GET çağrılmamalıydı")

    monkeypatch.setattr("requests.post", _sahte_post)
    monkeypatch.setattr("requests.get", _sahte_get)
    assert mod._wavespeed_uret("x", str(tmp_path / "a.png")) is False
    assert sayim == {"post": 1, "get": 0}


def test_reddedilen_gonderimde_yoklama_yok(mod, monkeypatch, tmp_path):
    _anahtar(monkeypatch)
    monkeypatch.setattr("requests.post",
                        lambda *a, **k: _Yanit(402, {"code": 402, "message": "yetersiz bakiye"}))

    def _sahte_get(*a, **k):
        raise AssertionError("GET çağrılmamalıydı")

    monkeypatch.setattr("requests.get", _sahte_get)
    assert mod._wavespeed_uret("x", str(tmp_path / "a.png")) is False


def test_basarili_akis_indirir_ve_dogrular(mod, monkeypatch, tmp_path):
    from PIL import Image

    _anahtar(monkeypatch)
    kaynak = tmp_path / "kaynak.png"
    Image.new("RGB", (16, 9), "navy").save(kaynak)
    hedef = tmp_path / "cikti.png"

    monkeypatch.setattr("requests.post",
                        lambda *a, **k: _Yanit(200, {"code": 200,
                                                     "data": {"id": "gorev-1", "status": "created"}}))
    kuyruk = [{"code": 200, "data": {"status": "processing"}},
              {"code": 200, "data": {"status": "completed",
                                      "outputs": ["https://cdn.ornek/x.png"]}}]
    monkeypatch.setattr("requests.get", lambda *a, **k: _Yanit(200, kuyruk.pop(0)))
    import shutil
    import urllib.request
    monkeypatch.setattr(urllib.request, "urlretrieve",
                        lambda url, yol: shutil.copy(kaynak, yol))
    monkeypatch.setattr("time.sleep", lambda s: None)

    assert mod._wavespeed_uret("gece yat", str(hedef)) is True
    with Image.open(hedef) as im:
        im.verify()


def test_terminal_durumda_false(mod, monkeypatch, tmp_path):
    _anahtar(monkeypatch)
    monkeypatch.setattr("requests.post",
                        lambda *a, **k: _Yanit(200, {"code": 200,
                                                     "data": {"id": "gorev-2"}}))
    monkeypatch.setattr("requests.get",
                        lambda *a, **k: _Yanit(200, {"code": 200,
                                                     "data": {"status": "failed",
                                                              "error": "bozuk"}}))
    monkeypatch.setattr("time.sleep", lambda s: None)
    assert mod._wavespeed_uret("x", str(tmp_path / "a.png")) is False


def test_yukleme_baglanti_hatasinda_en_fazla_iki_deneme(mod, monkeypatch, tmp_path):
    """Yükleme faturalandırılmaz — bağlantı hatasında EN FAZLA 2 deneme."""
    _anahtar(monkeypatch)
    sayim = {"post": 0}
    import requests as _gercek

    def _sahte_post(*a, **k):
        sayim["post"] += 1
        raise _gercek.ConnectionError("kopuk")

    monkeypatch.setattr("requests.post", _sahte_post)
    ref = tmp_path / "ref.jpg"
    ref.write_bytes(b"\xff\xd8\xff\x00")
    assert mod._wavespeed_yukle(str(ref)) is None
    assert sayim["post"] == 2


def test_yukleme_referans_yoksa_aga_cikilmaz(mod, monkeypatch, tmp_path):
    _anahtar(monkeypatch)

    def _sahte_post(*a, **k):
        raise AssertionError("ağa çıkılmamalıydı")

    monkeypatch.setattr("requests.post", _sahte_post)
    assert mod._wavespeed_yukle(str(tmp_path / "olmayan.jpg")) is None


def test_duzenle_gonderim_hatasinda_tekrar_yok(mod, monkeypatch, tmp_path):
    """Edit gönderim POST'u da tek deneme (fatura kuralı)."""
    _anahtar(monkeypatch)
    monkeypatch.setattr(mod, "_wavespeed_yukle", lambda yol: "https://cdn/x.png")
    sayim = {"post": 0, "get": 0}
    import requests as _gercek

    def _sahte_post(*a, **k):
        sayim["post"] += 1
        raise _gercek.ConnectionError("kopuk")

    def _sahte_get(*a, **k):
        sayim["get"] += 1
        raise AssertionError("GET çağrılmamalıydı")

    monkeypatch.setattr("requests.post", _sahte_post)
    monkeypatch.setattr("requests.get", _sahte_get)
    ref = tmp_path / "ref.jpg"
    ref.write_bytes(b"\xff\xd8\xff\x00")
    assert mod._wavespeed_duzenle("p", str(ref), str(tmp_path / "c.png")) is False
    assert sayim == {"post": 1, "get": 0}


def test_duzenle_basarili(mod, monkeypatch, tmp_path):
    from PIL import Image

    _anahtar(monkeypatch)
    monkeypatch.setattr(mod, "_wavespeed_yukle", lambda yol: "https://cdn/x.png")
    monkeypatch.setattr("requests.post",
                        lambda *a, **k: _Yanit(200, {"code": 200,
                                                     "data": {"id": "g-9"}}))
    kuyruk = [{"code": 200, "data": {"status": "processing"}},
              {"code": 200, "data": {"status": "completed",
                                          "outputs": ["https://cdn/z.png"]}}]
    monkeypatch.setattr("requests.get", lambda *a, **k: _Yanit(200, kuyruk.pop(0)))
    kaynak = tmp_path / "k.png"
    Image.new("RGB", (16, 9), "navy").save(kaynak)
    import shutil
    import urllib.request
    monkeypatch.setattr(urllib.request, "urlretrieve",
                        lambda url, yol: shutil.copy(kaynak, yol))
    monkeypatch.setattr("time.sleep", lambda s: None)
    hedef = tmp_path / "kare2.png"
    ref = tmp_path / "ref.jpg"
    ref.write_bytes(b"\xff\xd8\xff\x00")
    assert mod._wavespeed_duzenle("p", str(ref), str(hedef)) is True
    with Image.open(hedef) as im:
        im.verify()


def test_kare2_referans_yoksa_aga_cikilmaz(mod, monkeypatch, tmp_path):
    _anahtar(monkeypatch)

    def _sahte_post(*a, **k):
        raise AssertionError("ağa çıkılmamalıydı")

    monkeypatch.setattr("requests.post", _sahte_post)
    # kok altında _arda yok → referans bulunamaz, yüklemeye geçilmez
    assert mod._kare2_calistir(str(tmp_path)) == 3


def test_kare2_zaten_varsa_atlar(mod, monkeypatch, tmp_path):
    _anahtar(monkeypatch)
    (tmp_path / mod.KARE2_DOSYA).write_bytes(b"x")
    assert mod._kare2_calistir(str(tmp_path)) == 0


def test_birlestir_basarili(mod, monkeypatch, tmp_path):
    from PIL import Image

    _anahtar(monkeypatch)
    monkeypatch.setattr(mod, "_wavespeed_yukle", lambda yol: "https://cdn/r.png")
    monkeypatch.setattr("requests.post",
                        lambda *a, **k: _Yanit(200, {"code": 200,
                                                     "data": {"id": "g-b"}}))
    kuyruk = [{"code": 200, "data": {"status": "processing"}},
              {"code": 200, "data": {"status": "completed",
                                          "outputs": ["https://cdn/b.png"]}}]
    monkeypatch.setattr("requests.get", lambda *a, **k: _Yanit(200, kuyruk.pop(0)))
    kaynak = tmp_path / "k.png"
    Image.new("RGB", (16, 9), "navy").save(kaynak)
    import shutil
    import urllib.request
    monkeypatch.setattr(urllib.request, "urlretrieve",
                        lambda url, yol: shutil.copy(kaynak, yol))
    monkeypatch.setattr("time.sleep", lambda s: None)
    hedef = tmp_path / "aday.png"
    assert mod._wavespeed_birlestir("p", ["a.png", "b.png"], str(hedef)) is True
    with Image.open(hedef) as im:
        im.verify()


def test_birlestir_gonderim_hatasinda_tekrar_yok(mod, monkeypatch, tmp_path):
    _anahtar(monkeypatch)
    monkeypatch.setattr(mod, "_wavespeed_yukle", lambda yol: "https://cdn/r.png")
    sayim = {"post": 0, "get": 0}
    import requests as _gercek

    def _sahte_post(*a, **k):
        sayim["post"] += 1
        raise _gercek.ConnectionError("kopuk")

    def _sahte_get(*a, **k):
        sayim["get"] += 1
        raise AssertionError("GET çağrılmamalıydı")

    monkeypatch.setattr("requests.post", _sahte_post)
    monkeypatch.setattr("requests.get", _sahte_get)
    assert mod._wavespeed_birlestir("p", ["a.png"], str(tmp_path / "c.png")) is False
    assert sayim == {"post": 1, "get": 0}


def test_birlestir_referans_sayisi_kapili(mod, monkeypatch, tmp_path):
    _anahtar(monkeypatch)

    def _sahte_post(*a, **k):
        raise AssertionError("ağa çıkılmamalıydı")

    monkeypatch.setattr("requests.post", _sahte_post)
    assert mod._wavespeed_birlestir("p", [], str(tmp_path / "c.png")) is False
    assert mod._wavespeed_birlestir("p", ["1", "2", "3", "4"],
                                     str(tmp_path / "c.png")) is False


def test_kapak_aday_referans_yoksa_aga_cikilmaz(mod, monkeypatch, tmp_path):
    _anahtar(monkeypatch)

    def _sahte_post(*a, **k):
        raise AssertionError("ağa çıkılmamalıydı")

    monkeypatch.setattr("requests.post", _sahte_post)
    assert mod._kapak_aday_calistir(str(tmp_path)) == 3


def test_kapak_aday_zaten_varsa_atlar(mod, monkeypatch, tmp_path):
    _anahtar(monkeypatch)
    (tmp_path / mod.KAPAK_ADAY_DOSYA).write_bytes(b"x")
    assert mod._kapak_aday_calistir(str(tmp_path)) == 0


def test_nvidia_anahtar_yoksa_aga_cikilmaz(mod, monkeypatch, tmp_path):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)

    def _sahte_post(*a, **k):
        raise AssertionError("ağa çıkılmamalıydı")

    monkeypatch.setattr("requests.post", _sahte_post)
    assert mod._nvidia_uret("x", str(tmp_path / "a.png")) is False


def test_nvidia_gecersiz_boyut_aga_cikmaz(mod, monkeypatch, tmp_path):
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test")

    def _sahte_post(*a, **k):
        raise AssertionError("ağa çıkılmamalıydı")

    monkeypatch.setattr("requests.post", _sahte_post)
    assert mod._nvidia_uret("x", str(tmp_path / "a.png"), boyut="saçma") is False


def test_nvidia_baglanti_hatasinda_tekrar_yok(mod, monkeypatch, tmp_path):
    """Ücretsiz kredi de olsa fatura kuralı: POST TEK DENEME."""
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test")
    sayim = {"post": 0}
    import requests as _gercek

    def _sahte_post(*a, **k):
        sayim["post"] += 1
        raise _gercek.ConnectionError("kopuk")

    monkeypatch.setattr("requests.post", _sahte_post)
    assert mod._nvidia_uret("x", str(tmp_path / "a.png")) is False
    assert sayim["post"] == 1


def test_nvidia_basarili_cozer_ve_kaydeder(mod, monkeypatch, tmp_path):
    import base64
    import io
    from PIL import Image

    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test")
    tampon = io.BytesIO()
    Image.new("RGB", (16, 9), "navy").save(tampon, format="PNG")
    b64 = base64.b64encode(tampon.getvalue()).decode()
    monkeypatch.setattr("requests.post",
                        lambda *a, **k: _Yanit(200, {"artifacts": [{
                            "base64": b64, "finishReason": "SUCCESS"}]}))
    hedef = tmp_path / "n.png"
    assert mod._nvidia_uret("gece yat", str(hedef)) is True
    with Image.open(hedef) as im:
        im.verify()


def test_nvidia_http_hatasinda_false(mod, monkeypatch, tmp_path):
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test")
    yanit = _Yanit(402, {})
    yanit.text = "kredi bitti"
    monkeypatch.setattr("requests.post", lambda *a, **k: yanit)
    assert mod._nvidia_uret("x", str(tmp_path / "a.png")) is False


def test_nvidia_artifact_yoksa_false(mod, monkeypatch, tmp_path):
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test")
    monkeypatch.setattr("requests.post",
                        lambda *a, **k: _Yanit(200, {"artifacts": [{
                            "finishReason": "CONTENT_FILTERED"}]}))
    assert mod._nvidia_uret("x", str(tmp_path / "a.png")) is False


def test_together_anahtar_yoksa_aga_cikilmaz(mod, monkeypatch, tmp_path):
    monkeypatch.delenv("TOGETHER_API_KEY", raising=False)
    monkeypatch.setattr("requests.post", lambda *a, **k: (_ for _ in ()).throw(AssertionError("ağa çıkılmamalı")))
    assert mod._together_uret("x", str(tmp_path / "a.png")) is False


def test_huggingface_anahtar_yoksa_aga_cikilmaz(mod, monkeypatch, tmp_path):
    monkeypatch.delenv("HUGGINGFACE_API_TOKEN", raising=False)
    monkeypatch.delenv("HF_TOKEN", raising=False)
    assert mod._huggingface_uret("x", str(tmp_path / "a.png")) is False


def test_fal_anahtar_yoksa_aga_cikilmaz(mod, monkeypatch, tmp_path):
    monkeypatch.delenv("FAL_KEY", raising=False)
    assert mod._fal_uret("x", str(tmp_path / "a.png")) is False


def test_provider_calistir_bilinmeyen_false(mod, monkeypatch, tmp_path):
    monkeypatch.setattr(mod, "_ucretsiz_uret", lambda p, h: False)
    assert mod._provider_calistir("bilinmez", "p", str(tmp_path / "a.png")) is False


def test_smart_zincir_birinci_basarisiz_ikinci_basarili(mod, monkeypatch, tmp_path):
    """Limit sorunu: ilk sağlayıcı (nvidia) başarısız olursa ikinciye geçer."""
    monkeypatch.setattr(mod, "_nvidia_uret", lambda p, h: False)
    monkeypatch.setattr(mod, "_wavespeed_uret", lambda p, h: True)
    assert mod._smart_calistir("p", str(tmp_path / "a.png")) is True


def test_smart_zincir_her_basarisiz_false(mod, monkeypatch, tmp_path):
    monkeypatch.setattr(mod, "_nvidia_uret", lambda p, h: False)
    monkeypatch.setattr(mod, "_wavespeed_uret", lambda p, h: False)
    monkeypatch.setattr(mod, "_together_uret", lambda p, h: False)
    monkeypatch.setattr(mod, "_huggingface_uret", lambda p, h: False)
    monkeypatch.setattr(mod, "_ucretsiz_uret", lambda p, h: False)
    assert mod._smart_calistir("p", str(tmp_path / "a.png")) is False


def test_smart_zincir_tek_giris_her_yerde(mod, monkeypatch, tmp_path):
    """Her saglayici TEK deneme — tekrar yok (kredi muhafizi)."""
    sayim = {"nvidia": 0, "wavespeed": 0, "together": 0,
             "huggingface": 0, "ucretsiz": 0}
    def yap(tag):
        def _f(p, h):
            sayim[tag] += 1
            return False
        return _f
    monkeypatch.setattr(mod, "_nvidia_uret", yap("nvidia"))
    monkeypatch.setattr(mod, "_wavespeed_uret", yap("wavespeed"))
    monkeypatch.setattr(mod, "_together_uret", yap("together"))
    monkeypatch.setattr(mod, "_huggingface_uret", yap("huggingface"))
    monkeypatch.setattr(mod, "_ucretsiz_uret", yap("ucretsiz"))
    mod._smart_calistir("p", str(tmp_path / "a.png"))
    assert sayim == {"nvidia": 1, "wavespeed": 1, "together": 1,
                     "huggingface": 1, "ucretsiz": 1}, sayim


def test_together_anahtar_yoksa_aga_cikilmaz(mod, monkeypatch, tmp_path):
    monkeypatch.delenv("TOGETHER_API_KEY", raising=False)
    monkeypatch.setattr("requests.post", lambda *a, **k: (_ for _ in ()).throw(AssertionError("ağa çıkılmamalı")))
    assert mod._together_uret("x", str(tmp_path / "a.png")) is False


def test_huggingface_anahtar_yoksa_aga_cikilmaz(mod, monkeypatch, tmp_path):
    monkeypatch.delenv("HUGGINGFACE_API_TOKEN", raising=False)
    monkeypatch.delenv("HF_TOKEN", raising=False)
    assert mod._huggingface_uret("x", str(tmp_path / "a.png")) is False


def test_fal_anahtar_yoksa_aga_cikilmaz(mod, monkeypatch, tmp_path):
    monkeypatch.delenv("FAL_KEY", raising=False)
    assert mod._fal_uret("x", str(tmp_path / "a.png")) is False


def test_provider_calistir_bilinmeyen_false(mod, monkeypatch, tmp_path):
    monkeypatch.setattr(mod, "_ucretsiz_uret", lambda p, h: False)
    assert mod._provider_calistir("bilinmez", "p", str(tmp_path / "a.png")) is False


def test_smart_zincir_birinci_basarisiz_ikinci_basarili(mod, monkeypatch, tmp_path):
    monkeypatch.setattr(mod, "_nvidia_uret", lambda p, h: False)
    monkeypatch.setattr(mod, "_wavespeed_uret", lambda p, h: True)
    assert mod._smart_calistir("p", str(tmp_path / "a.png")) is True


def test_smart_zincir_her_basarisiz_false(mod, monkeypatch, tmp_path):
    monkeypatch.setattr(mod, "_nvidia_uret", lambda p, h: False)
    monkeypatch.setattr(mod, "_wavespeed_uret", lambda p, h: False)
    monkeypatch.setattr(mod, "_together_uret", lambda p, h: False)
    monkeypatch.setattr(mod, "_huggingface_uret", lambda p, h: False)
    monkeypatch.setattr(mod, "_ucretsiz_uret", lambda p, h: False)
    assert mod._smart_calistir("p", str(tmp_path / "a.png")) is False


def test_smart_zincir_tek_giris_her_yerde(mod, monkeypatch, tmp_path):
    sayim = {"nvidia": 0, "wavespeed": 0, "together": 0,
             "huggingface": 0, "ucretsiz": 0}
    def yap(tag):
        def _f(p, h):
            sayim[tag] += 1
            return False
        return _f
    monkeypatch.setattr(mod, "_nvidia_uret", yap("nvidia"))
    monkeypatch.setattr(mod, "_wavespeed_uret", yap("wavespeed"))
    monkeypatch.setattr(mod, "_together_uret", yap("together"))
    monkeypatch.setattr(mod, "_huggingface_uret", yap("huggingface"))
    monkeypatch.setattr(mod, "_ucretsiz_uret", yap("ucretsiz"))
    mod._smart_calistir("p", str(tmp_path / "a.png"))
    assert sayim == {"nvidia": 1, "wavespeed": 1, "together": 1,
                     "huggingface": 1, "ucretsiz": 1}, sayim
