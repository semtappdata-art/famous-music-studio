"""DJ seti bölüm damgaları + set başlığı + portre şablon (2026-09-14).

Kapsam:
- merge_dj_set_segments.bolum_baslangiclari (kırpma + crossfade aritmetiği)
- _bolum_adi / _mmss
- youtube_upload.set_bolumleri (yok/bozuk dosyada sessiz [])
- youtube_upload.set_basligi (stil → arama kalıbı, stilsiz → geri dönüş)
- build_snippet DJ dalı (başlık + Parçalar bloğu)
- ffmpeg_utils portre dalı (filtergraph'ta showspectrum/portre varlığı)
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "upload"))

from merge_dj_set_segments import _bolum_adi, _mmss, bolum_baslangiclari


def test_bolum_baslangici_crossfade_duser():
    kesimler = [(0.0, 180.0), (0.5, 190.5), (0.0, 200.0)]
    baslar = bolum_baslangiclari(kesimler, 3.0)
    assert baslar[0] == 0.0
    assert baslar[1] == round(180.0 - 3.0, 1)
    assert baslar[2] == round(180.0 - 3.0 + (190.5 - 0.5) - 3.0, 1)


def test_bolum_baslangici_tek_parca():
    assert bolum_baslangiclari([(0.0, 100.0)], 3.0) == [0.0]


def test_bolum_adi_parantez():
    assert _bolum_adi("Deep Medusa (Dive) 04.wav") == "Dive"


def test_bolum_adi_parantezsiz():
    assert _bolum_adi("Set Parcasi 07.wav") == "Set Parcasi"


def test_mmss():
    assert _mmss(0.0) == "0:00"
    assert _mmss(171.4) == "2:51"
    assert _mmss(3723.0) == "1:02:03"


def test_set_bolumleri_yoksa_bos():
    from youtube_upload import set_bolumleri
    assert set_bolumleri("/yok/boyle/bir/klasor") == []


def test_set_bolumleri_bozuksa_bos(tmp_path):
    from youtube_upload import set_bolumleri
    p = tmp_path / "bolumler.json"
    p.write_text("{bozuk", encoding="utf-8")
    assert set_bolumleri(str(tmp_path)) == []


def test_set_bolumleri_gecerli(tmp_path):
    from youtube_upload import set_bolumleri
    p = tmp_path / "bolumler.json"
    p.write_text(json.dumps({"parcalar": [
        {"sira": 1, "ad": "Opening", "bas": 0.0, "zaman": "0:00"},
        {"sira": 2, "ad": "Rise", "bas": 171.4, "zaman": "2:51"},
        {"sira": 3, "ad": "Pulse", "bas": 359.0, "zaman": "5:59"},
    ]}), encoding="utf-8")
    assert set_bolumleri(str(tmp_path)) == [
        {"zaman": "0:00", "ad": "Opening"},
        {"zaman": "2:51", "ad": "Rise"},
        {"zaman": "5:59", "ad": "Pulse"},
    ]


def test_set_basligi_stilli():
    from youtube_upload import set_basligi
    baslik = set_basligi({"title": "Deep Medusa", "set_style": "deep_house", "yil": 2026})
    assert baslik == "Deep House Night Mix 2026 | Deep Medusa (DJ Famous Set)"


def test_set_basligi_yil_donar():
    # meta["yil"] varsa içinde bulunulan yıl ne olursa olsun o kullanılır.
    from youtube_upload import set_basligi
    assert "2026" in set_basligi({"title": "X", "set_style": "deep_house", "yil": 2026})


def test_set_basligi_stilsiz():
    from youtube_upload import set_basligi
    assert set_basligi({"title": "X"}) == "X (DJ Famous Set)"


def test_build_snippet_dj_baslik_ve_bolum():
    from youtube_upload import build_snippet
    meta = {"title": "Deep Medusa", "theme": "dj", "set_style": "deep_house", "yil": 2026,
            "set_liste": [{"zaman": "0:00", "ad": "Opening"},
                          {"zaman": "2:51", "ad": "Rise"},
                          {"zaman": "5:59", "ad": "Pulse"}]}
    s = build_snippet(meta)
    assert s["title"] == "Deep House Night Mix 2026 | Deep Medusa (DJ Famous Set)"
    assert "0:00 Opening" in s["description"]
    assert "5:59 Pulse" in s["description"]
    assert s["defaultLanguage"] == "en"


def test_build_snippet_dj_listesiz_bolum_yok():
    from youtube_upload import build_snippet
    meta = {"title": "Deep Medusa", "theme": "dj", "set_style": "deep_house"}
    s = build_snippet(meta)
    assert "Parçalar:" not in s["description"]
    # Başlık yine kalıplı (liste yokluğu başlığı bozmamalı)
    assert "Deep Medusa (DJ Famous Set)" in s["title"]


def test_portre_dali_filtergraph():
    import ffmpeg_utils
    g = ffmpeg_utils._build_filter_complex(
        1920, 1080, 15.0, "T", False, "dj", "M",
        backdrop_video=False, hud_index=None, kart_goster=False,
        intro_index=None, dil_params=None, portre_index=3)
    assert "showspectrum" in g
    assert "[portre]" in g
    assert "drawbox" in g


def test_portresiz_graph_temiz():
    import ffmpeg_utils
    g = ffmpeg_utils._build_filter_complex(
        1920, 1080, 15.0, "T", False, "dj", "M",
        backdrop_video=False, hud_index=None, kart_goster=False,
        intro_index=None, dil_params=None, portre_index=None)
    assert "showspectrum" not in g
    assert "[portre]" not in g
