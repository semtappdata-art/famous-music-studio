# -*- coding: utf-8 -*-
"""TikTok taslağının yayınlanıp yayınlanmadığını API'den SALT OKUNUR doğrulama
(2026-09-13, `upload/tiktok_yayin_dogrulama.py`).

İkinci katman: kullanıcı Telegram'dan "yayınladım <ad>" yazmayı unutsa bile
`POST /v2/post/publish/status/fetch/` `PUBLISH_COMPLETE` + dolu
`publicaly_available_post_id` döndürdüğünde proje işaretlenir.

Hiçbir test ağa çıkmaz (taşıma katmanı sahte), gerçek `projects/`e ve gerçek
`saglik_durum.json`'a dokunmaz (tmp_path), gerçek bildirim göndermez
(`notify.send` taklit; conftest de kanalı kapatıyor).
"""

import ast
import io
import json
import os
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_UPLOAD = os.path.join(_REPO, "upload")
for _yol in (_REPO, _UPLOAD):
    if _yol not in sys.path:
        sys.path.insert(0, _yol)

import requests

import notify
import tiktok_publish_plan as TPP
import uyumluluk
import tiktok_yayin_dogrulama as TYD

SAHTE_TOKEN = "act.SAHTE-GIZLI-TOKEN-9f8e7d6c5b4a"


# --------------------------------------------------------------------------
# Fikstürler
# --------------------------------------------------------------------------

def _proje(kok, klasor, durum=None, video=True):
    p = kok / klasor
    p.mkdir(parents=True, exist_ok=True)
    (p / "state.json").write_text(
        json.dumps(durum or {}, ensure_ascii=False), encoding="utf-8")
    (p / "meta.json").write_text(
        json.dumps({"title": klasor, "theme": "pop"}, ensure_ascii=False),
        encoding="utf-8")
    (p / "audio.wav").write_bytes(("ses-" + klasor).encode("utf-8"))
    if video:
        (p / "output").mkdir(exist_ok=True)
        (p / "output" / TPP.VIDEO_ADI).write_bytes(b"sahte-mp4")
    return str(p)


def _durum(proje):
    with open(os.path.join(proje, "state.json"), "r", encoding="utf-8") as f:
        return json.load(f)


class _Yanit:
    def __init__(self, kod=200, govde=None, metin=None):
        self.status_code = kod
        self._govde = govde
        self.text = metin if metin is not None else json.dumps(govde or {})

    def json(self):
        if self._govde is None:
            raise ValueError("json degil")
        return self._govde


def _ok(status, post_ids=None, fail_reason=None):
    data = {"status": status}
    if post_ids is not None:
        data["publicaly_available_post_id"] = post_ids
    if fail_reason is not None:
        data["fail_reason"] = fail_reason
    return _Yanit(200, {"data": data, "error": {"code": "ok", "message": "", "log_id": "L"}})


def _hata(kod, mesaj="", http=400):
    return _Yanit(http, {"data": {}, "error": {"code": kod, "message": mesaj, "log_id": "L"}})


class _Ag:
    """publish_id -> yanıt (ya da yanıt listesi / istisna). Çağrıları kaydeder."""

    def __init__(self, harita):
        self.harita = harita
        self.cagrilar = []

    def __call__(self, url, headers=None, json=None, timeout=None, **kw):
        assert url == TYD.API_URL
        assert timeout is not None, "zaman aşımı olmadan istek yok"
        pid = json["publish_id"]
        self.cagrilar.append(pid)
        cevap = self.harita[pid]
        if isinstance(cevap, list):
            cevap = cevap.pop(0)
        if isinstance(cevap, BaseException):
            raise cevap
        return cevap


@pytest.fixture
def kok(tmp_path, monkeypatch):
    k = tmp_path / "projects"
    k.mkdir()
    monkeypatch.setattr(uyumluluk, "KOKLER", (str(k),))
    monkeypatch.setattr(TYD, "DURUM_DOSYASI", str(tmp_path / "saglik_durum.json"))
    return k


@pytest.fixture
def bildirim(monkeypatch):
    kayit = {"send": [], "uyari": []}

    def _send(baslik, mesaj):
        kayit["send"].append((baslik, mesaj))
        return True

    def _uyar(anahtar, mesaj):
        kayit["uyari"].append((anahtar, mesaj))

    monkeypatch.setattr(notify, "send", _send)
    monkeypatch.setattr(notify, "uyar_bir_kez", _uyar)
    return kayit


@pytest.fixture(autouse=True)
def gercek_ag_yasak(monkeypatch):
    """Sahte taşıma verilmeden istek denenirse test PATLASIN."""
    import socket

    def _yasak(*a, **k):
        raise AssertionError("doğrulama testleri gerçek ağa çıkmamalı")

    monkeypatch.setattr(socket.socket, "connect", _yasak)
    monkeypatch.setattr(requests, "post", _yasak)


def _kos(ag, log=None, token=SAHTE_TOKEN, gunluk=False, **kw):
    satirlar = [] if log is None else log
    uykular = kw.pop("uykular", [])

    def _token():
        if isinstance(token, BaseException):
            raise token
        return {"access_token": token}

    fn = TYD.gunluk_dogrulama if gunluk else TYD.dogrula
    sonuc = fn(log=satirlar.append, post=ag, token_al=_token,
               uyku=uykular.append, **kw)
    return sonuc, satirlar


# --------------------------------------------------------------------------
# 1. PUBLISH_COMPLETE + post id -> işaret
# --------------------------------------------------------------------------

def test_publish_complete_post_id_ile_isaretliyor_kaynak_ve_tek_bildirim(kok, bildirim):
    a = _proje(kok, "Gece Sürüşü", {"tiktok_publish_id": "v~A"})
    b = _proje(kok, "Son Kez", {"tiktok_publish_id": "v~B"})
    ag = _Ag({"v~A": _ok("PUBLISH_COMPLETE", [7400000000000000001]),
              "v~B": _ok("PUBLISH_COMPLETE", ["7400000000000000002"])})
    sonuc, satirlar = _kos(ag)

    for p, pid in ((a, "7400000000000000001"), (b, "7400000000000000002")):
        d = _durum(p)
        assert d["tiktok_published_at"]
        assert d["tiktok_post_ids"] == [pid]
        assert d["tiktok_publish_status"] == "PUBLISH_COMPLETE"
        assert d["tiktok_status_checked_at"]
        k = d["tiktok_published_kaynak"]
        assert k.startswith("TikTok API publish/status (otomatik doğrulama), ")
        assert "tespit anı" in k and "yaklaşık" in k
        assert "tiktok_dogrulandi" not in d, "yayınlamak gözle doğrulamak değildir"

    assert len(bildirim["send"]) == 1, bildirim["send"]
    baslik, mesaj = bildirim["send"][0]
    assert mesaj.startswith("TikTok'ta yayında doğrulandı (API): ")
    assert "Gece Sürüşü" in mesaj and "Son Kez" in mesaj
    assert sorted(sonuc["isaretlenen"]) == ["Gece Sürüşü", "Son Kez"]


def test_mevcut_isaretleme_fonksiyonu_kullaniliyor(kok, bildirim, monkeypatch):
    _proje(kok, "Sarki", {"tiktok_publish_id": "v~1"})
    cagri = []
    gercek = TPP.isaretle_yayinlandi

    def _sarmal(proje, *a, **k):
        cagri.append(k)
        return gercek(proje, *a, **k)

    monkeypatch.setattr(TPP, "isaretle_yayinlandi", _sarmal)
    _kos(_Ag({"v~1": _ok("PUBLISH_COMPLETE", ["1"])}))
    assert len(cagri) == 1
    assert cagri[0]["kaynak"].startswith("TikTok API publish/status")


def test_ikinci_kosuda_ayni_proje_icin_bildirim_yok(kok, bildirim):
    _proje(kok, "Sarki", {"tiktok_publish_id": "v~1"})
    ag = _Ag({"v~1": _ok("PUBLISH_COMPLETE", ["1"])})
    _kos(ag)
    _kos(ag)
    assert len(ag.cagrilar) == 1, "işaretli proje artık aday değil"
    assert len(bildirim["send"]) == 1


def test_bildirim_basarisiz_isareti_geri_almiyor(kok, bildirim, monkeypatch):
    p = _proje(kok, "Sarki", {"tiktok_publish_id": "v~1"})

    def _patla(*a, **k):
        raise RuntimeError("telegram yok")

    monkeypatch.setattr(notify, "send", _patla)
    sonuc, satirlar = _kos(_Ag({"v~1": _ok("PUBLISH_COMPLETE", ["1"])}))
    assert _durum(p)["tiktok_published_at"]
    assert any("bildirim" in s.lower() for s in satirlar), satirlar


# --------------------------------------------------------------------------
# 2. İşaretlememesi gereken durumlar
# --------------------------------------------------------------------------

def test_publish_complete_post_id_yoksa_isaret_yok_durum_yazildi(kok, bildirim):
    p = _proje(kok, "Sarki", {"tiktok_publish_id": "v~1"})
    sonuc, satirlar = _kos(_Ag({"v~1": _ok("PUBLISH_COMPLETE")}))
    d = _durum(p)
    assert "tiktok_published_at" not in d
    assert "tiktok_post_ids" not in d
    assert d["tiktok_publish_status"] == "PUBLISH_COMPLETE"
    assert d["tiktok_status_checked_at"]
    assert bildirim["send"] == []
    assert any("Sarki" in s for s in satirlar), "görünür olmalı"


def test_bos_post_id_listesi_de_isaret_degil(kok, bildirim):
    p = _proje(kok, "Sarki", {"tiktok_publish_id": "v~1"})
    _kos(_Ag({"v~1": _ok("PUBLISH_COMPLETE", [])}))
    assert "tiktok_published_at" not in _durum(p)


def test_inboxta_bekleyen_taslak_yalniz_durum(kok, bildirim):
    p = _proje(kok, "Sarki", {"tiktok_publish_id": "v~1"})
    _kos(_Ag({"v~1": _ok("SEND_TO_USER_INBOX")}))
    d = _durum(p)
    assert d["tiktok_publish_status"] == "SEND_TO_USER_INBOX"
    assert "tiktok_published_at" not in d
    assert "tiktok_status_sonraki_deneme" not in d


def test_hazir_false_ise_isaret_yok_durum_yazildi(kok, bildirim):
    p = _proje(kok, "Sarki", {"tiktok_publish_id": "v~1",
                              "yayin_beklet": "telif incelemesi"})
    sonuc, satirlar = _kos(_Ag({"v~1": _ok("PUBLISH_COMPLETE", ["1"])}))
    d = _durum(p)
    assert "tiktok_published_at" not in d
    assert d["tiktok_publish_status"] == "PUBLISH_COMPLETE"
    assert d.get("tiktok_status_isaret_engeli")
    assert bildirim["send"] == []
    assert any("Sarki" in s and "işaretlenmedi" in s for s in satirlar), satirlar


def test_zaten_isaretli_ya_da_publish_id_yok_aday_degil(kok, bildirim):
    _proje(kok, "Isaretli", {"tiktok_publish_id": "v~1",
                             "tiktok_published_at": "2026-09-01T10:00:00"})
    _proje(kok, "Yuklenmemis", {"youtube_video_id": "y"})
    _proje(kok, "Denenmez", {"tiktok_publish_id": "v~3",
                             "tiktok_status_denenmez": "invalid_publish_id"})
    ag = _Ag({})
    sonuc, satirlar = _kos(ag)
    assert ag.cagrilar == []
    assert sonuc["sorgulanan"] == 0
    assert any("aday yok" in s for s in satirlar), satirlar


# --------------------------------------------------------------------------
# 3. Hata / süresi dolmuş -> soğuma ve "denenmez"
# --------------------------------------------------------------------------

def test_hata_sogumaya_giriyor_ikinci_kosuda_sorgu_yok(kok, bildirim):
    p = _proje(kok, "Sarki", {"tiktok_publish_id": "v~1"})
    ag = _Ag({"v~1": _hata("invalid_publish_id", "publish_id not found")})
    _kos(ag)
    d = _durum(p)
    assert d["tiktok_publish_status"] == "HATA"
    assert "invalid_publish_id" in d["tiktok_status_hata"]
    assert d["tiktok_status_sonraki_deneme"]
    assert d["tiktok_status_hata_sayisi"] == 1
    _kos(ag)
    assert len(ag.cagrilar) == 1, "soğuma süresince aynı ölü ID yeniden sorgulanmamalı"


def test_soguma_bitince_yeniden_deneniyor(kok, bildirim):
    p = _proje(kok, "Sarki", {"tiktok_publish_id": "v~1"})
    ag = _Ag({"v~1": [_hata("internal_error", http=500), _ok("SEND_TO_USER_INBOX")]})
    t0 = 1_800_000_000
    _kos(ag, simdi=t0)
    _kos(ag, simdi=t0 + TYD.SOGUMA_SN - 60)
    assert len(ag.cagrilar) == 1
    _kos(ag, simdi=t0 + TYD.SOGUMA_SN + 60)
    assert len(ag.cagrilar) == 2
    d = _durum(p)
    assert d["tiktok_publish_status"] == "SEND_TO_USER_INBOX"
    for alan in ("tiktok_status_hata", "tiktok_status_sonraki_deneme",
                 "tiktok_status_hata_sayisi"):
        assert alan not in d, "başarılı yanıt eski hata izini temizlemeli"


def test_kalici_hata_tavaninda_denenmez_isareti(kok, bildirim):
    p = _proje(kok, "Sarki", {"tiktok_publish_id": "v~1"})
    ag = _Ag({"v~1": _hata("invalid_publish_id")})
    t = 1_800_000_000
    for i in range(TYD.KALICI_HATA_TAVANI):
        _kos(ag, simdi=t + i * (TYD.SOGUMA_SN + 60))
    d = _durum(p)
    assert d.get("tiktok_status_denenmez"), d
    once = len(ag.cagrilar)
    _kos(ag, simdi=t + 100 * TYD.SOGUMA_SN)
    assert len(ag.cagrilar) == once, "denenmez ID sonsuza kadar sorgulanmamalı"


def test_failed_durumu_hemen_denenmez(kok, bildirim):
    p = _proje(kok, "Sarki", {"tiktok_publish_id": "v~1"})
    _kos(_Ag({"v~1": _ok("FAILED", fail_reason="file_format_check_failed")}))
    d = _durum(p)
    assert d["tiktok_publish_status"] == "FAILED"
    assert "file_format_check_failed" in d["tiktok_status_denenmez"]
    assert "tiktok_published_at" not in d


def test_token_gecersiz_kodu_kosuyu_durduruyor_projeye_hata_yazmiyor(kok, bildirim):
    a = _proje(kok, "A", {"tiktok_publish_id": "v~1"})
    _proje(kok, "B", {"tiktok_publish_id": "v~2"})
    ag = _Ag({"v~1": _hata("access_token_invalid", http=401),
              "v~2": _ok("PUBLISH_COMPLETE", ["1"])})
    sonuc, satirlar = _kos(ag)
    assert ag.cagrilar == ["v~1"], "genel hata: diğer adaylar denenmez"
    assert "tiktok_status_sonraki_deneme" not in _durum(a)
    assert sonuc["tamamlandi"] is False
    assert bildirim["uyari"], "token geçersiz görünür olmalı"


def test_hiz_siniri_kosuyu_durduruyor(kok, bildirim):
    _proje(kok, "A", {"tiktok_publish_id": "v~1"})
    _proje(kok, "B", {"tiktok_publish_id": "v~2"})
    ag = _Ag({"v~1": _hata("rate_limit_exceeded", http=429), "v~2": _ok("SEND_TO_USER_INBOX")})
    sonuc, _ = _kos(ag)
    assert ag.cagrilar == ["v~1"]
    assert sonuc["tamamlandi"] is False


def test_tasima_hatasi_yeniden_deneniyor(kok, bildirim):
    p = _proje(kok, "Sarki", {"tiktok_publish_id": "v~1"})
    ag = _Ag({"v~1": [requests.exceptions.ConnectionError("koptu"),
                      requests.exceptions.Timeout("gecikti"),
                      _ok("PUBLISH_COMPLETE", ["1"])]})
    _kos(ag)
    assert len(ag.cagrilar) == 3
    assert _durum(p)["tiktok_published_at"]


def test_tasima_hatasi_surerse_kosu_durur_projeye_yazilmaz(kok, bildirim):
    p = _proje(kok, "Sarki", {"tiktok_publish_id": "v~1"})
    ag = _Ag({"v~1": [requests.exceptions.ConnectionError("koptu")] * 10})
    sonuc, satirlar = _kos(ag)
    assert len(ag.cagrilar) == TYD.TASIMA_DENEME
    assert sonuc["tamamlandi"] is False
    assert _durum(p) == {"tiktok_publish_id": "v~1"}


# --------------------------------------------------------------------------
# 4. Tavan, hız sınırı, günde bir damga
# --------------------------------------------------------------------------

def test_kosu_basina_tavan_ve_istekler_arasi_bekleme(kok, bildirim):
    for i in range(TYD.KOSU_TAVANI + 3):
        _proje(kok, "S%02d" % i, {"tiktok_publish_id": "v~%d" % i})
    ag = _Ag({"v~%d" % i: _ok("SEND_TO_USER_INBOX") for i in range(TYD.KOSU_TAVANI + 3)})
    uykular = []
    sonuc, _ = _kos(ag, uykular=uykular)
    assert len(ag.cagrilar) == TYD.KOSU_TAVANI
    # 30 istek/dakika sınırı: ardışık istekler arasında en az 2 sn
    assert len(uykular) >= TYD.KOSU_TAVANI - 1
    assert all(u >= 2.0 for u in uykular)


def test_en_uzun_suredir_sorgulanmayan_once(kok, bildirim):
    _proje(kok, "Yeni", {"tiktok_publish_id": "v~1",
                         "tiktok_status_checked_at": "2026-09-12T10:00:00"})
    _proje(kok, "Hic", {"tiktok_publish_id": "v~2"})
    _proje(kok, "Eski", {"tiktok_publish_id": "v~3",
                         "tiktok_status_checked_at": "2026-09-01T10:00:00"})
    ag = _Ag({k: _ok("SEND_TO_USER_INBOX") for k in ("v~1", "v~2", "v~3")})
    _kos(ag)
    assert ag.cagrilar == ["v~2", "v~3", "v~1"]


def test_gunde_bir_damga_basarida_atiliyor(kok, bildirim):
    _proje(kok, "Sarki", {"tiktok_publish_id": "v~1"})
    ag = _Ag({"v~1": _ok("SEND_TO_USER_INBOX")})
    _kos(ag, gunluk=True)
    with open(TYD.DURUM_DOSYASI, encoding="utf-8") as f:
        assert json.load(f)[TYD.GUN_DAMGASI]
    _kos(ag, gunluk=True)
    assert len(ag.cagrilar) == 1, "aynı gün ikinci kez sorgu yok"


def test_basarisizlikta_damga_yok(kok, bildirim):
    _proje(kok, "Sarki", {"tiktok_publish_id": "v~1"})
    ag = _Ag({"v~1": [requests.exceptions.ConnectionError("koptu")] * TYD.TASIMA_DENEME
              + [_ok("SEND_TO_USER_INBOX")]})
    _kos(ag, gunluk=True)
    assert not os.path.isfile(TYD.DURUM_DOSYASI) or \
        TYD.GUN_DAMGASI not in json.load(open(TYD.DURUM_DOSYASI, encoding="utf-8"))
    _kos(ag, gunluk=True)
    assert len(ag.cagrilar) == TYD.TASIMA_DENEME + 1, "sonraki koşu yeniden denemeli"


def test_token_yok_uyari_satiri_istisna_yok_damga_yok(kok, bildirim):
    _proje(kok, "Sarki", {"tiktok_publish_id": "v~1"})
    ag = _Ag({})
    sonuc, satirlar = _kos(ag, token=FileNotFoundError("tiktok_token.json yok"), gunluk=True)
    assert ag.cagrilar == []
    assert bildirim["uyari"], "token yokluğu görünür olmalı"
    assert any("token" in s.lower() for s in satirlar), satirlar
    assert not os.path.isfile(TYD.DURUM_DOSYASI)


def test_aday_yoksa_token_bile_alinmiyor(kok, bildirim):
    cagri = []
    TYD.dogrula(log=lambda s: None, post=_Ag({}),
                token_al=lambda: cagri.append(1) or {"access_token": "x"},
                uyku=lambda s: None)
    assert cagri == [], "aday yokken token yenileme isteği bile atılmamalı"


# --------------------------------------------------------------------------
# 5. Sır sızıntısı
# --------------------------------------------------------------------------

def test_token_hicbir_log_bildirim_ya_da_state_metninde_yok(kok, bildirim):
    a = _proje(kok, "A", {"tiktok_publish_id": "v~1"})
    b = _proje(kok, "B", {"tiktok_publish_id": "v~2"})
    _proje(kok, "C", {"tiktok_publish_id": "v~3"})
    ag = _Ag({
        "v~1": _hata("internal_error", "echo Bearer " + SAHTE_TOKEN, http=500),
        "v~2": _ok("PUBLISH_COMPLETE", ["9"]),
        "v~3": _Yanit(502, None, metin="<html>" + SAHTE_TOKEN + "</html>"),
    })
    sonuc, satirlar = _kos(ag)
    metinler = list(satirlar) + [m for _, m in bildirim["send"]] + \
        [m for _, m in bildirim["uyari"]] + \
        [json.dumps(_durum(p), ensure_ascii=False) for p in (a, b)] + \
        [json.dumps(sonuc, ensure_ascii=False, default=str)]
    for m in metinler:
        assert SAHTE_TOKEN not in m, m
    # Token hatası mesajı token'ı içerse bile sızmamalı
    satirlar2 = []
    _kos(_Ag({}), log=satirlar2, token=RuntimeError("refresh failed " + SAHTE_TOKEN),
         gunluk=True)
    for m in satirlar2 + [m for _, m in bildirim["uyari"]]:
        assert SAHTE_TOKEN not in m, m


def test_modul_yazan_tiktok_ucuna_cikmiyor():
    """Yalnız okuma: modülde init/upload/publish uç noktası geçmemeli."""
    kaynak = io.open(os.path.join(_UPLOAD, "tiktok_yayin_dogrulama.py"), encoding="utf-8").read()
    assert "/post/publish/status/fetch/" in kaynak
    for yasak in ("inbox/video/init", "video/init", "content/init", "requests.put"):
        assert yasak not in kaynak, yasak


# --------------------------------------------------------------------------
# 6. Bağlantı — auto_process
# --------------------------------------------------------------------------

def _auto_process_agaci():
    with io.open(os.path.join(_REPO, "auto_process.py"), encoding="utf-8") as f:
        return ast.parse(f.read())


def test_auto_process_finally_kancayi_cagiriyor():
    agac = _auto_process_agaci()
    main = next(d for d in ast.walk(agac)
                if isinstance(d, ast.FunctionDef) and d.name == "main")
    deneme = next(d for d in ast.walk(main) if isinstance(d, ast.Try) and d.finalbody)
    cagrilar = {d.func.id for d in ast.walk(ast.Module(body=deneme.finalbody, type_ignores=[]))
                if isinstance(d, ast.Call) and isinstance(d.func, ast.Name)}
    assert "_tiktok_yayin_dogrulama" in cagrilar, sorted(cagrilar)


def test_kanca_dogru_fonksiyonu_try_icinde_cagiriyor():
    agac = _auto_process_agaci()
    fn = next(d for d in ast.walk(agac)
              if isinstance(d, ast.FunctionDef) and d.name == "_tiktok_yayin_dogrulama")
    assert any(isinstance(x, ast.Try) for x in fn.body), "hata otomasyonu durdurabilir"
    assert "gunluk_dogrulama" in {d.func.id for d in ast.walk(fn)
                                  if isinstance(d, ast.Call) and isinstance(d.func, ast.Name)}
    assert "tiktok_yayin_dogrulama" in {a.module for a in ast.walk(fn)
                                        if isinstance(a, ast.ImportFrom)}


def test_is_fully_done_a_eklenmedi():
    agac = _auto_process_agaci()
    fn = next(d for d in ast.walk(agac)
              if isinstance(d, ast.FunctionDef) and d.name == "_is_fully_done")
    kaynak = ast.unparse(fn)
    assert "tiktok_published_at" not in kaynak
    assert "tiktok_publish_status" not in kaynak


def test_patlayan_kanca_yutuluyor(monkeypatch):
    import auto_process

    def _patla(*a, **k):
        raise RuntimeError("beklenmedik")

    satirlar = []
    monkeypatch.setattr(TYD, "gunluk_dogrulama", _patla)
    monkeypatch.setattr(auto_process, "log", satirlar.append)
    auto_process._tiktok_yayin_dogrulama()              # istisna FIRLATMAZ
    assert any("TikTok yayın doğrulama HATA" in s for s in satirlar), satirlar
