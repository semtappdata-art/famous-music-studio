# -*- coding: utf-8 -*-
"""TikTok elle yayınının TELEGRAM yanıtıyla depoya işaretlenmesi (2026-09-13).

NEDEN VAR: `tiktok_published_at` alanının tek yazanı bir CLI komutuydu
(`tiktok_publish_plan.py --yayinlandi`) ve UNUTULUYORDU — katalogda işaret taşıyan
kayıt neredeyse yok, `_tiktok_ikiz_kapisi`'nın en ağır kuralı yine kör. Çözüm:
hatırlatma mesajı kullanıcıya NET bir yanıt kalıbı veriyor ("yayınladım <ad>"),
yanıtı ZATEN dinleyen Hermes gateway'i proje-yerel bir beceriyle TEK bir
betiği (`upload/tiktok_yayin_onayi.py`) çalıştırıyor.

BOT HERMES İLE PAYLAŞILIYOR: depoda `getUpdates`/webhook YOK ve olmamalı
(ikinci tüketici Hermes'in mesajlarını çalar). Bu dosyadaki
`test_betik_ag_ve_kabuk_kullanmiyor` bunun da muhafızı.

Hiçbir test ağa çıkmaz, gerçek `projects/`e dokunmaz (katalog kökü `tmp_path`),
gerçek bildirim göndermez (`notify.send` taklit; conftest de kanalı kapatıyor).
"""

import io
import json
import os
import re
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_UPLOAD = os.path.join(_REPO, "upload")
for _yol in (_REPO, _UPLOAD):
    if _yol not in sys.path:
        sys.path.insert(0, _yol)

import tiktok_publish_plan as TPP
import tiktok_upload
import uyumluluk
import tiktok_yayin_onayi as ONAY

BETIK = os.path.join(_UPLOAD, "tiktok_yayin_onayi.py")


# --------------------------------------------------------------------------
# Fikstürler
# --------------------------------------------------------------------------

def _proje(kok, klasor, durum=None, baslik=None, ses=None, video=True):
    p = kok / klasor
    p.mkdir(parents=True, exist_ok=True)
    (p / "state.json").write_text(
        json.dumps(durum or {}, ensure_ascii=False), encoding="utf-8")
    (p / "meta.json").write_text(
        json.dumps({"title": baslik or klasor, "theme": "pop"}, ensure_ascii=False),
        encoding="utf-8")
    # Varsayılan: her projenin sesi FARKLI — ikiz kapısı yalnız bilerek kurulunca işlesin.
    (p / "audio.wav").write_bytes(ses if ses is not None else ("ses-" + klasor).encode("utf-8"))
    if video:
        (p / "output").mkdir(exist_ok=True)
        (p / "output" / TPP.VIDEO_ADI).write_bytes(b"sahte-mp4")
    return str(p)


def _durum(proje):
    with open(os.path.join(proje, "state.json"), "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def kok(tmp_path, monkeypatch):
    k = tmp_path / "projects"
    k.mkdir()
    monkeypatch.setattr(uyumluluk, "KOKLER", (str(k),))
    return k


@pytest.fixture(autouse=True)
def ag_ve_kabuk_yasak(monkeypatch):
    """Betik çalışırken ağa ya da kabuğa çıkılırsa test PATLASIN."""
    import socket
    import subprocess

    def _yasak(*a, **k):
        raise AssertionError("onay yolu ağa/kabuğa çıkmamalı")

    monkeypatch.setattr(socket.socket, "connect", _yasak)
    monkeypatch.setattr(subprocess, "Popen", _yasak)
    monkeypatch.setattr(subprocess, "run", _yasak)
    monkeypatch.setattr(os, "system", _yasak)


def _calistir(capsys, *argv):
    kod = ONAY.main(list(argv))
    return kod, capsys.readouterr().out


# --------------------------------------------------------------------------
# 1. Doğru proje işaretleniyor, kaynak alanı yazılıyor
# --------------------------------------------------------------------------

def test_tam_adla_isaretliyor_ve_kaynak_yaziyor(kok, capsys):
    p = _proje(kok, "Sabah Senin", {"tiktok_publish_id": "v_inbox_file~v2.111"})
    _proje(kok, "Sabaha Kadar", {"tiktok_publish_id": "v_inbox_file~v2.222"})
    kod, cikti = _calistir(capsys, "Sabah Senin")
    assert kod == 0, cikti
    d = _durum(p)
    assert d["tiktok_published_at"]
    assert d["tiktok_published_kaynak"].startswith("Telegram onayı (kullanıcı), ")
    assert d["tiktok_published_at"] in d["tiktok_published_kaynak"]
    assert "Sabah Senin" in cikti
    # Benzer adlı komşu projeye DOKUNULMADI
    assert "tiktok_published_at" not in _durum(str(kok / "Sabaha Kadar"))


def test_tiktok_dogrulandi_YAZILMIYOR(kok, capsys):
    """Yayınlamak doğrulamak değildir (tiktok_publish_plan docstring'i)."""
    p = _proje(kok, "Sarki", {"tiktok_publish_id": "v~1"})
    assert _calistir(capsys, "Sarki")[0] == 0
    assert "tiktok_dogrulandi" not in _durum(p)


def test_normalize_eslesme_turkce_harfsiz_ve_kucuk_harf(kok, capsys):
    """Telefonda 'kirik zincir' yazan kullanıcı 'Kırık Zincir'i işaretleyebilmeli."""
    p = _proje(kok, "Kırık Zincir", {"tiktok_publish_id": "v~1"})
    kod, cikti = _calistir(capsys, "  kirik   ZİNCİR ")
    assert kod == 0, cikti
    assert _durum(p)["tiktok_published_at"]


def test_basindaki_yayinladim_kelimesi_yok_sayiliyor(kok, capsys):
    p = _proje(kok, "Son Kez", {"tiktok_publish_id": "v~1"})
    assert _calistir(capsys, "yayınladım Son Kez")[0] == 0
    assert _durum(p)["tiktok_published_at"]


def test_meta_basligiyla_eslesiyor_klasor_adi_farkli(kok, capsys):
    p = _proje(kok, "gece_seansi_vol1", {"tiktok_publish_id": "v~1"},
               baslik="Gece Seansı Vol. 1")
    assert _calistir(capsys, "Gece Seansı Vol. 1")[0] == 0
    assert _durum(p)["tiktok_published_at"]


def test_proje_koduyla_isaretliyor(kok, capsys):
    p = _proje(kok, "Yeraltı", {"tiktok_publish_id": "v_inbox_file~v2.7681"})
    kod_metni = tiktok_upload.yayin_kodu("v_inbox_file~v2.7681")
    assert re.fullmatch(r"T[0-9A-F]{4}", kod_metni)
    kod, cikti = _calistir(capsys, kod_metni.lower())
    assert kod == 0, cikti
    assert _durum(p)["tiktok_published_at"]


def test_mevcut_isaretleme_fonksiyonu_CAGRILIYOR(kok, capsys, monkeypatch):
    """Mantık kopyalanmadı: tek yazan `TPP.isaretle_yayinlandi`."""
    _proje(kok, "Sarki", {"tiktok_publish_id": "v~1"})
    cagri = []
    gercek = TPP.isaretle_yayinlandi

    def _sarmal(proje, *a, **k):
        cagri.append((proje, k))
        return gercek(proje, *a, **k)

    monkeypatch.setattr(TPP, "isaretle_yayinlandi", _sarmal)
    assert _calistir(capsys, "Sarki")[0] == 0
    assert len(cagri) == 1
    assert cagri[0][1].get("kaynak", "").startswith("Telegram onayı")


def test_kaynak_parametresi_tek_atomik_yazimda(kok, monkeypatch):
    """Damga ve kaynak AYNI yazımda — ikisi arasında süreç ölürse yarım kayıt kalmasın."""
    p = _proje(kok, "Sarki", {"tiktok_publish_id": "v~1"})
    yazimlar = []
    monkeypatch.setattr(TPP.state_io, "durum_yaz",
                        lambda proje, veri: yazimlar.append(dict(veri)))
    TPP.isaretle_yayinlandi(p, zaman="2026-09-13T20:00:00", kaynak="X, 2026-09-13T20:00:00")
    assert len(yazimlar) == 1
    assert yazimlar[0]["tiktok_published_kaynak"] == "X, 2026-09-13T20:00:00"
    assert yazimlar[0]["tiktok_published_at"] == "2026-09-13T20:00:00"


# --------------------------------------------------------------------------
# 2. İşaretlememesi gereken durumlar
# --------------------------------------------------------------------------

def test_belirsiz_ad_isaretlemiyor_adaylari_listeliyor(kok, capsys):
    a = _proje(kok, "Gece", {"tiktok_publish_id": "v~1"})
    b = _proje(kok, "Gece Sürüşü", {"tiktok_publish_id": "v~2"})
    c = _proje(kok, "Gece Yarısı", {"tiktok_publish_id": "v~3"})
    kod, cikti = _calistir(capsys, "gece s")
    assert kod != 0
    for p in (a, b, c):
        assert "tiktok_published_at" not in _durum(p)
    assert "Gece Sürüşü" in cikti


def test_iki_projede_ayni_baslik_BELIRSIZ(kok, capsys):
    a = _proje(kok, "Night Drive", {"tiktok_publish_id": "v~1"})
    (kok.parent / "dj_sets").mkdir()
    b = _proje(kok.parent / "dj_sets", "Night Drive", {"tiktok_publish_id": "v~2"})
    import uyumluluk as U
    U.KOKLER = (str(kok), str(kok.parent / "dj_sets"))  # monkeypatch fikstürü geri alır
    kod, cikti = _calistir(capsys, "Night Drive")
    assert kod != 0
    assert "tiktok_published_at" not in _durum(a)
    assert "tiktok_published_at" not in _durum(b)
    assert "BELİRSİZ" in cikti


def test_bulunamayan_ad_isaretlemiyor(kok, capsys):
    p = _proje(kok, "Sarki", {"tiktok_publish_id": "v~1"})
    kod, cikti = _calistir(capsys, "Hiç Olmayan Şarkı")
    assert kod != 0
    assert "tiktok_published_at" not in _durum(p)
    assert "BULUNAMADI" in cikti


def test_bos_ya_da_eksik_arguman(kok, capsys):
    assert _calistir(capsys)[0] != 0
    assert _calistir(capsys, "   ")[0] != 0
    assert _calistir(capsys, "a", "b")[0] != 0


def test_zaten_isaretli_IDEMPOTENT(kok, capsys):
    p = _proje(kok, "Sarki", {"tiktok_publish_id": "v~1",
                              "tiktok_published_at": "2026-09-10T19:00:00"})
    kod, cikti = _calistir(capsys, "Sarki")
    assert kod == 0
    assert "ZATEN" in cikti
    d = _durum(p)
    assert d["tiktok_published_at"] == "2026-09-10T19:00:00"
    assert "tiktok_published_kaynak" not in d


def test_publish_id_yoksa_isaretlemiyor(kok, capsys):
    p = _proje(kok, "Sarki", {"youtube_video_id": "abc"})
    kod, cikti = _calistir(capsys, "Sarki")
    assert kod != 0
    assert "tiktok_published_at" not in _durum(p)
    assert "İŞARETLENMEDİ" in cikti


def test_uyumluluk_hatasi_hazir_false_isaretlemiyor(kok, capsys, monkeypatch):
    p = _proje(kok, "Telifli", {"tiktok_publish_id": "v~1"})
    monkeypatch.setattr(uyumluluk, "kontrol",
                        lambda proje, asama: (["telif eşleşmesi kayıtlı (Örnek)"], []))
    kod, cikti = _calistir(capsys, "Telifli")
    assert kod != 0
    assert "tiktok_published_at" not in _durum(p)
    assert "telif eşleşmesi" in cikti


def test_ikiz_kapisi_hazir_false_isaretlemiyor(kok, capsys):
    """İkizi TikTok'ta ZATEN yayınlanmış proje işaretlenmez (gerçek kapı)."""
    _proje(kok, "Orijinal", {"tiktok_publish_id": "v~o",
                             "tiktok_published_at": "2026-09-05T19:00:00"},
           ses=b"ayni-ses")
    kopya = _proje(kok, "Kopya", {"tiktok_publish_id": "v~k"}, ses=b"ayni-ses")
    kod, cikti = _calistir(capsys, "Kopya")
    assert kod != 0
    assert "tiktok_published_at" not in _durum(kopya)
    assert "Orijinal" in cikti


def test_build_plan_cokerse_isaretlemiyor(kok, capsys, monkeypatch):
    p = _proje(kok, "Sarki", {"tiktok_publish_id": "v~1"})

    def _cok(proje):
        raise RuntimeError("beklenmedik")

    monkeypatch.setattr(TPP, "build_plan", _cok)
    kod, cikti = _calistir(capsys, "Sarki")
    assert kod != 0
    assert "tiktok_published_at" not in _durum(p)


# --------------------------------------------------------------------------
# 3. Güvenlik: argüman kabuğa gitmiyor, ağ yok, çıktı cp1254 konsolda çökmüyor
# --------------------------------------------------------------------------

def test_kabuk_ozel_karakterli_arguman_zararsiz(kok, capsys, tmp_path):
    hedef = tmp_path / "silinmemeli.txt"
    hedef.write_text("x", encoding="utf-8")
    p = _proje(kok, "Sarki", {"tiktok_publish_id": "v~1"})
    kod, cikti = _calistir(capsys, '$(rm -f "%s"); `whoami` | & ; Sarki' % hedef)
    assert kod != 0
    assert hedef.exists()
    assert "tiktok_published_at" not in _durum(p)


def test_betik_ag_ve_kabuk_kullanmiyor():
    """Statik muhafız: bot Hermes ile paylaşılıyor — depoda update okuyan kod YOK."""
    kaynak = io.open(BETIK, encoding="utf-8").read()
    for yasak in ("subprocess", "os.system", "os.popen", "shell=True", "requests",
                  "urllib", "socket", "getUpdates", "setWebhook", "import notify",
                  "eval(", "exec("):
        assert yasak not in kaynak, "onay betiğinde yasak ifade: %s" % yasak


def test_depoda_getupdates_cagrisi_yok():
    """Bot API'nin güncelleme okuyan yöntemleri kodda STRING olarak geçmemeli.

    Belgelerde/yorumlarda (`notify.py` kurulum adımı, `ag_yeniden_deneme.py`
    gerekçesi) kelime serbest — orada ters tırnakla ya da çıplak URL olarak
    geçiyor. Aranan: tırnak içinde yöntem adı ya da ".../getUpdates" dizesi,
    yani bir istek kurabilecek biçim.
    """
    desen = re.compile(
        r"""['"](?:[^'"\n]*/)?(?:getUpdates|setWebhook|deleteWebhook)['"?]""")
    bulunan = []
    for kok_dizin, dizinler, dosyalar in os.walk(_REPO):
        dizinler[:] = [d for d in dizinler
                       if d not in (".git", ".claude", "__pycache__", "tests",
                                    ".pytest_cache", "node_modules")]
        for ad in dosyalar:
            if not ad.endswith(".py"):
                continue
            yol = os.path.join(kok_dizin, ad)
            try:
                metin = io.open(yol, encoding="utf-8").read()
            except (OSError, UnicodeDecodeError):
                continue
            if desen.search(metin):
                bulunan.append(yol)
    assert not bulunan, bulunan


def test_cikti_cp1254_konsolda_cokmuyor(kok, monkeypatch):
    _proje(kok, "Kırık Zincir 🔥 — Özel", {"tiktok_publish_id": "v~1"})
    ham = io.BytesIO()
    akis = io.TextIOWrapper(ham, encoding="cp1254", errors="strict")
    monkeypatch.setattr(sys, "stdout", akis)
    kod = ONAY.main(["Kırık Zincir 🔥 — Özel"])
    akis.flush()
    metin = ham.getvalue().decode("utf-8")
    assert kod == 0
    assert "Kırık Zincir" in metin


def test_cikti_kisa(kok, capsys):
    _proje(kok, "Sarki", {"tiktok_publish_id": "v~1"})
    _, cikti = _calistir(capsys, "Sarki")
    assert 0 < len(cikti.strip().splitlines()) <= 3
    assert len(cikti) < 600


# --------------------------------------------------------------------------
# 4. Hatırlatma mesajı
# --------------------------------------------------------------------------

@pytest.fixture
def kanal(monkeypatch):
    import config
    import notify
    giden = []
    monkeypatch.setattr(notify, "is_configured", lambda: True)
    monkeypatch.setattr(notify, "send", lambda t, m: giden.append((t, m)) or True)
    monkeypatch.setattr(config, "next_golden_publish_time", lambda *a, **k: None)
    return giden


def test_hatirlatma_yanit_talimati_ad_ve_kod_iceriyor(kok, kanal):
    p = _proje(kok, "Sabah Senin", {"tiktok_publish_id": "v_inbox_file~v2.9"})
    assert tiktok_upload.notify_pending_publish(p) is True
    assert len(kanal) == 1
    _, mesaj = kanal[0]
    assert "Sabah Senin" in mesaj
    assert "yayınladım Sabah Senin" in mesaj
    assert tiktok_upload.yayin_kodu("v_inbox_file~v2.9") in mesaj


def test_hatirlatmadaki_kalip_onay_betigiyle_eslesiyor(kok, kanal, capsys):
    """Döngü: mesajdaki yanıt satırı AYNEN betiğe verilince doğru proje işaretlenir."""
    p = _proje(kok, "Yürek Yarası", {"tiktok_publish_id": "v~9"})
    tiktok_upload.notify_pending_publish(p)
    satir = [s for s in kanal[0][1].splitlines() if "yayınladım " in s][0]
    yanit = satir[satir.index("yayınladım "):].strip()
    assert _calistir(capsys, yanit)[0] == 0
    assert _durum(p)["tiktok_published_at"]


def test_hatirlatma_damga_ve_tek_sefer_davranisi_degismedi(kok, kanal):
    p = _proje(kok, "Sarki", {"tiktok_publish_id": "v~1"})
    assert tiktok_upload.notify_pending_publish(p) is True
    assert _durum(p)["tiktok_notified"] is True
    assert "tiktok_published_at" not in _durum(p), "hatırlatma işaretleme YAPMAZ"
    assert tiktok_upload.notify_pending_publish(p) is False
    assert len(kanal) == 1


def test_hatirlatma_golden_hour_disinda_gitmiyor(kok, kanal, monkeypatch):
    import config
    p = _proje(kok, "Sarki", {"tiktok_publish_id": "v~1"})
    monkeypatch.setattr(config, "next_golden_publish_time", lambda *a, **k: 12345)
    assert tiktok_upload.notify_pending_publish(p) is False
    assert kanal == []
    assert "tiktok_notified" not in _durum(p)


def test_yayin_kodu_kararli_ve_bos_idde_none():
    assert tiktok_upload.yayin_kodu("abc") == tiktok_upload.yayin_kodu("abc")
    assert tiktok_upload.yayin_kodu("abc") != tiktok_upload.yayin_kodu("abd")
    assert tiktok_upload.yayin_kodu(None) is None
    assert tiktok_upload.yayin_kodu("") is None
