# -*- coding: utf-8 -*-
"""YouTube Shorts / kesit açıklamasının son satırı: "TikTok'ta: famousmusicstudio".

Kullanıcı onayı 2026-09-13 (TikTok LIVE planı §3a-6): YENİ yüklemelerde tek satır,
hesap adı `config.SOCIAL_HANDLES["tiktok"]`. Geçmiş videolar (`fix_description`)
satırı ALMAZ. Uzun formatta link bloğu zaten TikTok'u taşıdığı için eklenmez.
Diğer platform metinleri (`build_caption`, TikTok kiti) DEĞİŞMEZ.
"""

import ast
import io
import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)
sys.path.insert(0, os.path.join(_REPO, "upload"))

import config                                             # noqa: E402
import social_text as ST                                  # noqa: E402
import youtube_upload as YU                               # noqa: E402

META = {"title": "Beni Bırakma", "theme": "pop"}
DJ = {"title": "Just Relax", "theme": "dj"}
SATIR = "TikTok'ta: famousmusicstudio"


def test_hesap_adi_config_sabitinden():
    assert config.SOCIAL_HANDLES["tiktok"] == "famousmusicstudio"
    assert YU.tiktok_hesap_satiri() == SATIR


def test_yeni_shorts_ve_kesit_aciklamasi_tek_satirla_biter():
    for d in (YU.build_shorts_snippet(META, "abc123")["description"],
              YU.build_shorts_snippet(META)["description"],
              YU.build_shorts_snippet(DJ, "abc123")["description"],
              YU.build_clip_snippet(DJ, "abc123", 400.0)["description"],
              YU.build_clip_snippet(DJ, None, 400.0)["description"]):
        assert d.endswith("\n\n" + SATIR), d[-80:]
        assert d.count(SATIR) == 1


def test_satir_disinda_shorts_aciklamasi_aynen():
    d = YU.build_shorts_snippet(META, "abc123")["description"]
    assert d == (ST.build_caption(META)
                 + "\n\n🎧 Şarkının tamamı kanalımızda: https://youtu.be/abc123"
                 + "\n\n" + SATIR)


def test_gecmis_video_duzeltmesi_satiri_eklemez():
    d = YU.build_shorts_snippet(META, "abc123", tiktok_satiri=False)["description"]
    assert SATIR not in d
    agac = ast.parse(io.open(YU.__file__, encoding="utf-8").read())
    fonks = {f.name: f for f in ast.walk(agac) if isinstance(f, ast.FunctionDef)}
    cagrilar = [c for c in ast.walk(fonks["fix_description"]) if isinstance(c, ast.Call)
                and getattr(c.func, "id", None) == "build_shorts_snippet"]
    assert cagrilar and all(any(k.arg == "tiktok_satiri" and k.value.value is False
                                for k in c.keywords) for c in cagrilar)
    yeni = [c for c in ast.walk(fonks["upload_short"]) if isinstance(c, ast.Call)
            and getattr(c.func, "id", None) == "build_shorts_snippet"]
    assert yeni and not any(k.arg == "tiktok_satiri" for c in yeni for k in c.keywords)


def test_uzun_format_ve_diger_platform_metinleri_degismez():
    uzun = YU.build_snippet(META)["description"]
    assert SATIR not in uzun
    assert uzun.count(config.SOCIAL_LINKS["tiktok"]) == 1         # mevcut link bloğu aynen
    for metin in (ST.build_caption(META), ST.build_caption(META, ai_beyani=True),
                  ST.build_tiktok_kit_caption(META), ST.build_caption(DJ)):
        assert "TikTok'ta:" not in metin


def test_handle_yoksa_satir_yok(monkeypatch):
    monkeypatch.setattr(config, "SOCIAL_HANDLES", {"instagram": "x"})
    assert YU.tiktok_hesap_satiri() == ""
    assert "TikTok'ta:" not in YU.build_shorts_snippet(META, "abc123")["description"]


def test_satirda_youtube_kanal_baglantisina_donusen_at_isareti_yok():
    # youtube.com/@famousmusicstudio başka bir kanal; @ YouTube'da kanal linkine dönüşür.
    assert "@" not in YU.tiktok_hesap_satiri()
