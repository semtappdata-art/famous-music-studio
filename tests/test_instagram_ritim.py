# -*- coding: utf-8 -*-
"""instagram_upload.try_publish_pending — ritim R3b (şarkı günde en fazla 2 platform).

Konteyner ZATEN var: tavan doluysa yalnız ertesi günün ilk golden-hour'una kadar taze
kalacaksa bekler (SEBEP_RITIM); bayatlayacaksa yayınlar (gönderiyi sessizce düşürmemek
için). Ağ çağrıları sahte.
"""

import json
import os
import sys
import time

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _y in (_REPO, os.path.join(_REPO, "upload")):
    if _y not in sys.path:
        sys.path.insert(0, _y)

import config
import instagram_upload as IG


class _Yanit:
    def json(self):
        return {"status_code": "FINISHED"}


def _kur(tmp_path, monkeypatch, yas_saat):
    bugun = time.strftime("%Y-%m-%d")
    st = {"youtube_video_id": "v", "youtube_uploaded_at": bugun + "T00:01:00",
          "youtube_shorts_video_id": "s", "youtube_shorts_uploaded_at": bugun + "T00:01:00",
          "instagram_creation_id": "C1",
          "instagram_container_created_at": time.strftime(
              "%Y-%m-%dT%H:%M:%S", time.localtime(time.time() - yas_saat * 3600))}
    p = tmp_path / "Sarki"
    p.mkdir()
    (p / "state.json").write_text(json.dumps(st), encoding="utf-8")
    monkeypatch.setattr(config, "YAYIN_RITMI_SARKI_GUNLUK_PLATFORM_TAVANI", 2, raising=False)
    monkeypatch.setattr(config, "next_golden_publish_time", lambda *a, **k: None)
    monkeypatch.setattr(IG, "get_access_token", lambda: {"access_token": "t", "ig_user_id": "u"})
    monkeypatch.setattr(IG, "_graph_istek", lambda *a, **k: _Yanit())
    yayin = []
    monkeypatch.setattr(IG, "_publish_container", lambda *a, **k: yayin.append(1) or "M1")
    return str(p), yayin


def test_tavan_dolu_taze_konteyner_bekler(tmp_path, monkeypatch):
    p, yayin = _kur(tmp_path, monkeypatch, yas_saat=0)
    monkeypatch.setattr(IG, "_konteyner_yarina_dayanir", lambda st: True)
    sebep = {}
    assert IG.try_publish_pending(p, sebep_out=sebep) is None
    assert sebep["kod"] == IG.SEBEP_RITIM and yayin == []


def test_tavan_dolu_ama_bayatlayacak_konteyner_yayinlanir(tmp_path, monkeypatch):
    p, yayin = _kur(tmp_path, monkeypatch, yas_saat=0)
    monkeypatch.setattr(IG, "_konteyner_yarina_dayanir", lambda st: False)
    assert IG.try_publish_pending(p) == "M1" and yayin == [1]


def test_tavan_bosken_normal_yayin(tmp_path, monkeypatch):
    p, yayin = _kur(tmp_path, monkeypatch, yas_saat=0)
    monkeypatch.setattr(config, "YAYIN_RITMI_SARKI_GUNLUK_PLATFORM_TAVANI", 3)
    assert IG.try_publish_pending(p) == "M1"


def test_yarina_dayanir_hesabi():
    assert IG._konteyner_yarina_dayanir({}) is False
    eski = {"instagram_container_created_at": time.strftime(
        "%Y-%m-%dT%H:%M:%S", time.localtime(time.time() - 22 * 3600))}
    assert IG._konteyner_yarina_dayanir(eski) is False
