# -*- coding: utf-8 -*-
"""ek_platform_backfill._platform_yayin_bildir testleri.

Bildirim kalıbı: defter + notify. Her iki kanal da hatayı
sessizce yakalar — testlerde mock ile izlenir.
"""

import json
import os
import sys
from unittest.mock import patch

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_UPLOAD = os.path.join(_REPO, "upload")
for _yol in (_REPO, _UPLOAD):
    if _yol not in sys.path:
        sys.path.insert(0, _yol)

import ek_platform_backfill as E
import elle_islem as EI
import uyumluluk


def _proje(kok, ad, **ek):
    p = kok / ad
    p.mkdir(parents=True, exist_ok=True)
    st = {"youtube_video_id": "yt-" + ad}
    st.update(ek)
    (p / "state.json").write_text(json.dumps(st, ensure_ascii=False),
                                  encoding="utf-8")
    return str(p)


@pytest.fixture
def kok(tmp_path, monkeypatch):
    k = tmp_path / "projects"
    k.mkdir()
    monkeypatch.setattr(uyumluluk, "KOKLER", (str(k),))
    return k


def test_defter_hatasi_sessiz(kok, capsys):
    """elle_islem patlasa da fonksiyon exception fışkırmaz."""
    p = _proje(kok, "A")
    with patch.object(EI, "ekle", side_effect=RuntimeError("x")):
        E._platform_yayin_bildir(p, "telegram", "test", log=print)
    out, _err = capsys.readouterr()
    assert "bildirim defter hatası" in out


def test_notify_yapilmaz(kok):
    """notify.is_configured() False ise notify.send çağrılmaz."""
    p = _proje(kok, "B")
    with patch.object(EI, "ekle", return_value={"durum": "eklendi"}), \
         patch("notify.is_configured", return_value=False), \
         patch("notify.send") as mock_send:
        E._platform_yayin_bildir(p, "bluesky", "test", log=print)
        mock_send.assert_not_called()


def test_notify_yapilir(kok):
    """notify.is_configured() True ise notify.send çağrılır."""
    p = _proje(kok, "C")
    with patch.object(EI, "ekle", return_value={"durum": "eklendi"}), \
         patch("notify.is_configured", return_value=True), \
         patch("notify.send") as mock_send:
        E._platform_yayin_bildir(p, "bluesky", "test", log=print)
        mock_send.assert_called_once()
        assert "bluesky yayında: C" in mock_send.call_args[0]


def test_her_hatta_sessiz(kok):
    """elle_islem ve notify ikisi de patlarsa exception fışkırmaz."""
    p = _proje(kok, "D")
    with patch.object(EI, "ekle", side_effect=RuntimeError("x")), \
         patch("notify.is_configured",
               side_effect=RuntimeError("y")):
        E._platform_yayin_bildir(p, "telegram", "test", log=print)
