# -*- coding: utf-8 -*-
"""Zorunlu AI beyan satırı — `config.AI_BEYAN_SATIRLARI` (kullanıcı kararı, 2026-09-13).

KARAR ÖZETİ:
  * Satır içerik türüne göre küçük bir set: vokalli şarkı / vokalsiz / DJ seti;
    derleme vokalli satırı alır. Söz kısmı ÖNCE, ifade "AI destekli" ("yapay zeka"
    değil). İngilizce projeler aynı kalıbın İngilizcesini alır.
  * TikTok kit, Instagram ve Facebook açıklamasında TAM OLARAK BİR satır, hashtag
    bloğundan hemen önce. YouTube açıklamasına EKLENMEZ (containsSyntheticMedia
    bayrağı aynen), Telegram/Bluesky değişmez.
  * Kamuya açık HİÇBİR metinde üretim aracının adı geçmez (bu dosyadaki tarama).
  * DJ hattında eski "caption + ayrı beyan satırı" ÇİFT beyan üretmez.

Ağa çıkmaz; gerçek katalog yalnız OKUNUR.
"""

import ast
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

import config
import social_text as ST
import uyumluluk

SATIRLAR = config.AI_BEYAN_SATIRLARI
TUM_SATIRLAR = {s for dil in SATIRLAR.values() for s in dil.values()}
_ARAC_ADI = re.compile(r"suno", re.IGNORECASE)
_TIK = chr(96) * 3


def _beyan_sayisi(metin):
    return sum(1 for s in metin.splitlines() if s.strip() in TUM_SATIRLAR)


def _sozler(tmp_path, stil="deep female vocals, 90 BPM", temiz="Bir satır söz\nİkinci satır",
            eksik=False, temiz_bolumu=True):
    baslik = "## Sözler (EKSİK, tamamlanmalı)" if eksik else "## Sözler"
    parcalar = ["# Deneme", "", "## Stil Etiketi (kutuya yapıştır)", "", _TIK, stil, _TIK, "",
                baslik, "", _TIK, "[Verse]", "satır", _TIK, ""]
    if temiz_bolumu:
        parcalar += ["## Temiz Sözler (açıklama için)", "", _TIK, temiz, _TIK, ""]
    yol = tmp_path / "deneme_sozler.md"
    yol.write_text("\n".join(parcalar), encoding="utf-8")
    return str(yol)


def _katalog():
    bulunan = []
    for p in uyumluluk.proje_klasorleri():
        yol = os.path.join(p, "meta.json")
        if os.path.isfile(yol):
            with io.open(yol, encoding="utf-8") as f:
                bulunan.append((p, json.load(f)))
    return bulunan


# --------------------------------------------------------------------------
# 1. Her dal doğru satırı seçiyor
# --------------------------------------------------------------------------

@pytest.mark.parametrize("meta,sozler,dil,tur", [
    ({"title": "Şarkı", "theme": "pop"}, None, "tr", "vokalli"),          # sözler dosyası yok = belirsiz
    ({"title": "Song", "theme": "pop", "language": "en"}, None, "en", "vokalli"),
    ({"title": "Şarkı", "theme": "elektronik"}, {"stil": "melodic techno, no vocals, 124 bpm"}, "tr", "vokalsiz"),
    ({"title": "Şarkı", "theme": "akustik"}, {"temiz": ""}, "tr", "vokalsiz"),
    ({"title": "Song", "theme": "pop", "language": "en"}, {"stil": "instrumental only"}, "en", "vokalsiz"),
    ({"title": "Şarkı", "theme": "rock"}, {"stil": "opens cold on the vocal with no instrumental intro"}, "tr", "vokalli"),
    ({"title": "Şarkı", "theme": "rock"}, {"temiz": "", "eksik": True}, "tr", "vokalli"),
    ({"title": "Şarkı", "theme": "rock"}, {"temiz_bolumu": False}, "tr", "vokalli"),
    ({"title": "Just Relax", "theme": "dj", "set_style": "deep_house"}, None, "en", "dj"),
    ({"title": "Night Drive", "theme": "dj", "set_style": "techno_chill"}, None, "en", "dj"),
    ({"title": "Gece Seti", "theme": "dj", "language": "tr"}, None, "tr", "dj"),
    ({"title": "Gece Seansı", "theme": "hiphop", "derleme": True,
      "derleme_temalari": ["hiphop"]}, {"stil": "no vocals"}, "tr", "vokalli"),
])
def test_her_dal_dogru_satiri_seciyor(tmp_path, monkeypatch, meta, sozler, dil, tur):
    yol = _sozler(tmp_path, **sozler) if sozler is not None else None
    monkeypatch.setattr(ST, "dogrulanmis_sozler_yolu", lambda baslik: yol)
    assert ST.ai_beyan_turu(meta) == tur
    assert ST.ai_beyan_satiri(meta) == SATIRLAR[dil][tur]


def test_metinler_kullanici_kararindaki_gibi():
    assert SATIRLAR["tr"]["vokalli"] == "Söz: Famous Music Studio · Müzik ve vokal: AI destekli"
    assert SATIRLAR["tr"]["vokalsiz"] == "Müzik: AI destekli · Famous Music Studio"
    assert SATIRLAR["tr"]["dj"] == "Seçki ve miks: DJ Famous · Müzik: AI destekli"
    assert SATIRLAR["en"]["vokalli"] == "Lyrics: Famous Music Studio · Music & vocals: AI-assisted"
    assert SATIRLAR["en"]["vokalsiz"] == "Music: AI-assisted · Famous Music Studio"
    assert SATIRLAR["en"]["dj"] == "Selection & mix: DJ Famous · Music: AI-assisted"


def test_satir_kurallari():
    for dil, set_ in SATIRLAR.items():
        for tur, satir in set_.items():
            assert not _ARAC_ADI.search(satir), satir
            assert "yapay zeka" not in satir.casefold(), satir
            assert not satir.lstrip().startswith("#") and "#" not in satir, "beyan hashtag değil"
            assert ("AI destekli" if dil == "tr" else "AI-assisted") in satir
            if tur == "vokalli":
                assert satir.startswith("Söz:" if dil == "tr" else "Lyrics:"), "söz kısmı ÖNCE"


def test_eski_disclosure_girisi_yeni_sabite_bagli():
    assert ST.build_ai_disclosure_line("tr") == SATIRLAR["tr"]["vokalli"]
    assert ST.build_ai_disclosure_line("en") == SATIRLAR["en"]["vokalli"]
    meta = {"title": "Just Relax", "theme": "dj"}
    assert ST.build_ai_disclosure_line("en", meta=meta) == SATIRLAR["en"]["dj"]


# --------------------------------------------------------------------------
# 2. Gerçek katalog: TikTok / IG / FB'de TAM BİR satır; diğerlerinde yok
# --------------------------------------------------------------------------

def test_katalog_tiktok_ig_fb_aciklamasinda_tam_bir_beyan_digerlerinde_yok():
    assert config.TIKTOK_AI_BEYANI == "aciklama"
    katalog = _katalog()
    assert katalog
    for proje, meta in katalog:
        ad = os.path.basename(proje)
        ig_fb = ST.build_caption(meta, ai_beyani=True)
        tiktok = ST.build_tiktok_kit_caption(meta)
        assert _beyan_sayisi(ig_fb) == 1, ad
        assert _beyan_sayisi(tiktok) == 1, ad
        for metin in (ig_fb, tiktok):
            paragraflar = metin.split("\n\n")
            assert paragraflar[-2] in TUM_SATIRLAR, (ad, "hashtag bloğundan hemen önce")
            assert paragraflar[-1].startswith("#")
        assert _beyan_sayisi(ST.build_caption(meta)) == 0, (ad, "Shorts/Telegram/Bluesky değişmez")
        assert len(ig_fb) <= 2200, (ad, "Instagram açıklama sınırı")


def test_youtube_aciklamasina_beyan_eklenmez_bayrak_aynen():
    import youtube_upload
    for proje, meta in _katalog()[:6]:
        uzun = youtube_upload.build_snippet(meta)
        kisa = youtube_upload.build_shorts_snippet(meta, "abc123")
        assert _beyan_sayisi(uzun["description"]) == 0
        assert _beyan_sayisi(kisa["description"]) == 0
    kaynak = io.open(os.path.join(_UPLOAD, "youtube_upload.py"), encoding="utf-8").read()
    assert "containsSyntheticMedia" in kaynak


# --------------------------------------------------------------------------
# 3. Kamuya açık HİÇBİR metinde üretim aracının adı yok
# --------------------------------------------------------------------------

def test_katalog_kamuya_acik_metinlerde_arac_adi_yok():
    import bluesky_upload
    import telegram_upload
    import youtube_upload
    url = "https://youtu.be/abc123XYZ"
    bulgular = []
    for proje, meta in _katalog():
        dil = ST.resolve_language(meta)
        metinler = {
            "build_caption": ST.build_caption(meta),
            "instagram/facebook": ST.build_caption(meta, ai_beyani=True),
            "tiktok_kit": ST.build_tiktok_kit_caption(meta),
            "tiktok_kit_etiket": ST.build_tiktok_kit_caption(meta, ai_beyani="etiket+aciklama"),
            "bluesky": bluesky_upload.build_post_text(meta, url),
            "telegram": telegram_upload._build_telegram_caption(proje, meta),
            "beyan": ST.ai_beyan_satiri(meta),
        }
        for platform in ("instagram", "tiktok", "facebook"):
            metinler["ilk_yorum_" + platform] = ST.build_youtube_comment(url, dil, platform=platform)
        for ad, snip in (("youtube_uzun", youtube_upload.build_snippet(meta)),
                         ("youtube_shorts", youtube_upload.build_shorts_snippet(meta, "abc123"))):
            metinler[ad] = "\n".join([snip.get("title") or "", snip.get("description") or "",
                                      " ".join(snip.get("tags") or [])])
        for ad, metin in metinler.items():
            if _ARAC_ADI.search(metin or ""):
                bulgular.append((os.path.basename(proje), ad))
    assert not bulgular, bulgular


# --------------------------------------------------------------------------
# 4. Çağrı noktaları (ast): IG/FB beyanlı, DJ'de çift beyan yok
# --------------------------------------------------------------------------

def _agac(yol):
    return ast.parse(io.open(yol, encoding="utf-8").read())


def _build_caption_cagrilari(dugum):
    return [d for d in ast.walk(dugum) if isinstance(d, ast.Call)
            and getattr(d.func, "id", getattr(d.func, "attr", None)) == "build_caption"]


def _beyanli(cagri):
    return any(k.arg == "ai_beyani" and isinstance(k.value, ast.Constant) and k.value.value is True
               for k in cagri.keywords)


def _fonksiyon(agac, ad):
    return next(d for d in agac.body if isinstance(d, ast.FunctionDef) and d.name == ad)


@pytest.mark.parametrize("dosya,fonksiyon", [
    ("instagram_upload.py", "upload_video"),
    ("facebook_upload.py", "upload_reels"),
    ("facebook_upload.py", "upload_long"),
])
def test_instagram_facebook_cagrilari_beyanli(dosya, fonksiyon):
    cagrilar = _build_caption_cagrilari(_fonksiyon(_agac(os.path.join(_UPLOAD, dosya)), fonksiyon))
    assert cagrilar and all(_beyanli(c) for c in cagrilar), (dosya, fonksiyon)


@pytest.mark.parametrize("dosya", ["telegram_upload.py", "bluesky_upload.py", "youtube_upload.py"])
def test_telegram_bluesky_youtube_cagrilari_beyansiz(dosya):
    cagrilar = _build_caption_cagrilari(_agac(os.path.join(_UPLOAD, dosya)))
    assert cagrilar and not any(_beyanli(c) for c in cagrilar), dosya


def test_dj_hatti_cift_beyan_uretmiyor():
    yol = os.path.join(_REPO, "dj_famous_process.py")
    kaynak = io.open(yol, encoding="utf-8").read()
    assert "build_ai_disclosure_line(" not in kaynak, "eski ayrı satır geri gelmemeli"
    cagrilar = _build_caption_cagrilari(_agac(yol))
    assert cagrilar and all(_beyanli(c) for c in cagrilar)
