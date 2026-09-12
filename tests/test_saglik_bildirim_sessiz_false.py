# -*- coding: utf-8 -*-
"""saglik_kontrol._bildir — `notify.send` SESSİZCE False dönerse de damga atmamalı.

NEDEN (2026-09-11, ikinci düzeltme): ilk düzeltme sadece `notify.send`in
İSTİSNA fırlattığı yolu kapatmıştı (bkz. test_saglik_bildirim.py). Ama
`notify.py`nin üç başarısızlık yolunun ÜÇÜ DE istisna fırlatmıyor, sessizce
`False` dönüyor: kanal hiç kurulu değil, ağ yok, ntfy.sh 5xx. Bu yollarda
damga hâlâ atılıyordu — yani "Instagram token'ın doldu" uyarısı, gönderimin
başarısız olduğu gün kayboluyor ve 24 saat tekrar denenmiyordu. Modülün TÜM
var oluş gerekçesi sessiz duruşu yakalamak; bu tam olarak sessiz duruştu.
"""

import json
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "upload"))

import saglik_kontrol as SK


def _sahte_notify(monkeypatch, gonderilen, sonuc=True):
    """notify.py ntfy.sh'a GERÇEK HTTP isteği atıyor — testte sahtesi konuyor.

    `sonuc` gerçek sözleşmeyi taklit ediyor: `send()` bool döner.
    """
    m = types.ModuleType("notify")

    def send(baslik, mesaj, **k):
        gonderilen.append((baslik, mesaj))
        return sonuc

    m.send = send
    m.is_configured = lambda: bool(sonuc)
    monkeypatch.setitem(sys.modules, "notify", m)
    return m


def test_send_false_donunce_damga_atilmaz_ve_bir_sonraki_kosu_dener(tmp_path, monkeypatch):
    yol = str(tmp_path / "d.json")
    monkeypatch.setattr(SK, "DURUM_DOSYASI", yol)
    gonderilen = []
    _sahte_notify(monkeypatch, gonderilen, sonuc=False)

    # 1. koşu: kanal kurulu değil / ağ yok -> False, DAMGA YOK.
    assert SK._bildir("b", "m", "anahtar") is False
    assert "anahtar" not in SK._durum()
    assert not os.path.isfile(yol) or json.load(open(yol, encoding="utf-8")) == {}

    # 2. koşu (aynı gün): gün damgası engel olmamalı, TEKRAR denenmeli.
    assert SK._bildir("b", "m", "anahtar") is False
    assert len(gonderilen) == 2

    # Hat düzelince gerçekten gönderilip damgalanmalı.
    _sahte_notify(monkeypatch, gonderilen, sonuc=True)
    assert SK._bildir("b", "m", "anahtar") is True
    assert SK._durum()["anahtar"]

    # ...ve artık aynı gün susmalı (gürültü kontrolü hâlâ çalışıyor).
    assert SK._bildir("b", "m", "anahtar") is False
    assert len(gonderilen) == 3


def test_instagram_suresi_dolmus_token_her_kosuda_yeniden_dener(tmp_path, monkeypatch):
    """Uçtan uca: gerçek uyarı yolu (süresi dolmuş Instagram token'ı).

    Bildirim gitmediği sürece saatlik koşu tekrar denemeli — bu düzeltmenin
    asıl korumak istediği senaryo.
    """
    monkeypatch.setattr(SK, "DURUM_DOSYASI", str(tmp_path / "d.json"))
    token = tmp_path / "instagram_token.json"
    # expires_in mtime'a göre göreli: negatif değer "çoktan dolmuş" demek.
    token.write_text(json.dumps({"expires_in": -864000}), encoding="utf-8")
    monkeypatch.setattr(SK, "INSTAGRAM_TOKEN", str(token))

    gonderilen = []
    _sahte_notify(monkeypatch, gonderilen, sonuc=False)
    for _ in range(3):
        s = SK.instagram_token_suresi(log=lambda *a, **k: None)
        assert s.get("uyari") is True
    assert len(gonderilen) == 3          # her koşuda yeniden denendi

    _sahte_notify(monkeypatch, gonderilen, sonuc=True)
    SK.instagram_token_suresi(log=lambda *a, **k: None)
    assert len(gonderilen) == 4
    SK.instagram_token_suresi(log=lambda *a, **k: None)
    assert len(gonderilen) == 4          # başarıdan sonra gün içinde sus
