# -*- coding: utf-8 -*-
"""Hashtag düzeltmesi ve TikTok yayın kitinin açıklaması (2026-09-13).

İKİ AYRI KARAR, İKİ AYRI KAPSAM:
  (a) `social_text.hashtag()` "&" işaretini SİLİYORDU: "R&B" -> `#RB` (anlamsız
      bir etiket; `pop` temasının `related` listesinde). "&" -> "n" (`#RnB`)
      düzeltmesi bir HATA düzeltmesi olduğu için HER platformda geçerli.
  (b) Şarkı adı etiketi + tema bazlı Türkçe keşif etiketleri + 5-6 etiket +
      `#fyp/#foryou/#viral` yok + `#keşfet` en fazla 1 kuralı YALNIZ TikTok
      kitinin açıklamasında. Instagram/Shorts/Telegram/Bluesky/Facebook
      `build_caption()`la AYNEN kalıyor (arşiv tutarlılığı) — son test bunu
      değişiklikten ÖNCE üretilmiş bir arşive karşı ölçüyor.

Ağa çıkmaz; gerçek katalog yalnız OKUNUR (meta.json).
"""

import io
import json
import os
import re
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _yol in (_REPO, os.path.join(_REPO, "upload")):
    if _yol not in sys.path:
        sys.path.insert(0, _yol)

import config
import social_text as ST
import uyumluluk

ARSIV = os.path.join(_REPO, "tests", "build_caption_arsivi_2026-09-13.json")
MODLAR = ("etiket", "aciklama", "etiket+aciklama")

# AI vurgulu etiket: gövdesi bu köklerle başlayan ya da bunları içeren hashtag.
# Beyan CÜMLESİ (aciklama modu) hashtag değildir; yalnız `#` ile başlayan
# parçalar taranır.
_AI_BASLAR = ("ai", "yapay", "suno", "artificial")
_AI_ICERIR = ("yapayzeka", "suno", "artificial", "aimusic", "aimüzik",
              "aigenerated", "aiart")
_YASAK_KESIF = re.compile(r"^#(fyp|foryou|foryoupage|viral)", re.IGNORECASE)
_LINK = ("http", "www.", "youtu", ".com")


def _etiketler(metin):
    return [p for p in metin.split() if p.startswith("#")]


def _ai_vurgulu(etiket):
    govde = etiket[1:].casefold()
    return govde.startswith(_AI_BASLAR) or any(k in govde for k in _AI_ICERIR)


def _katalog_metalari():
    bulunan = []
    for p in uyumluluk.proje_klasorleri():
        yol = os.path.join(p, "meta.json")
        if os.path.isfile(yol):
            with io.open(yol, encoding="utf-8") as f:
                bulunan.append((os.path.basename(p), json.load(f)))
    return bulunan


def _sentetik_metalar():
    metalar = []
    for anahtar in config.THEMES:
        if anahtar != "dj":
            metalar.append({"title": "Örnek Şarkı", "theme": anahtar})
    metalar.append({"title": "City Pulse Set", "theme": "dj"})
    for stil in config.SET_STILLERI:
        metalar.append({"title": "Night Drive", "theme": "dj", "set_style": stil})
    metalar.append(_derleme_meta())
    return metalar


def _derleme_meta():
    return {"title": "Gece Seansı Vol. 1", "theme": "hiphop", "derleme": True,
            "derleme_temalari": ["hiphop", "hiphop", "pop", "arabesk", "rock"],
            "derleme_liste": [{"sira": i + 1, "ad": "Parça %d" % i, "zaman": "0:00"}
                              for i in range(5)]}


@pytest.fixture(params=MODLAR)
def ai_modu(request, monkeypatch):
    monkeypatch.setattr(config, "TIKTOK_AI_BEYANI", request.param)
    return request.param


# --------------------------------------------------------------------------
# (a) & -> n  (HER platform)
# --------------------------------------------------------------------------

def test_hashtag_ampersand_rnb():
    assert ST.hashtag("R&B") == "#RnB"
    assert ST.hashtag("Drum & Bass") == "#DrumnBass"
    assert ST.hashtag("Türkçe Rap") == "#TürkçeRap"      # eski davranış korunuyor


def test_pop_temasi_build_caption_rnb_tasiyor():
    metin = ST.build_caption({"title": "Bir Bahar Daha", "theme": "pop"})
    assert "#RnB" in metin and "#RB" not in _etiketler(metin)


# --------------------------------------------------------------------------
# (b) TikTok kit açıklaması
# --------------------------------------------------------------------------

@pytest.mark.parametrize("tema", [t for t in config.THEMES if t != "dj"])
def test_tiktok_sarki_etiketleri(tema):
    meta = {"title": "Kırık Zincir", "theme": tema}
    etiketler = ST.tiktok_kit_hashtagleri(meta)
    assert "#KırıkZincir" in etiketler, etiketler
    assert 5 <= len(etiketler) <= 6, etiketler
    assert not [e for e in etiketler if _YASAK_KESIF.match(e)], etiketler
    assert sum(1 for e in etiketler if e.casefold().startswith("#keşfet")) <= 1
    assert len({e.casefold() for e in etiketler}) == len(etiketler), "tekrar eden etiket"
    metin = ST.build_tiktok_kit_caption(meta)
    assert metin.splitlines()[-1].split() == etiketler, "hashtag bloğu son satır"
    ilk = metin.splitlines()[0]
    assert "Kırık Zincir" in ilk and config.THEMES[tema]["label"] in ilk, ilk


def test_tiktok_kesif_etiketleri_config_tema_havuzundan():
    meta = {"title": "Kırık Zincir", "theme": "rock"}
    havuz = {e.casefold() for e in config.TEMA_KESIF_ETIKETLERI["rock"]}
    etiketler = ST.tiktok_kit_hashtagleri(meta)
    sabit = {e.casefold() for e in config.BRAND_HASHTAGS + ["#KırıkZincir", "#Rock"]}
    assert {e.casefold() for e in etiketler} - sabit <= havuz


def test_ai_vurgulu_etiket_yok_tum_temalar(ai_modu):
    for meta in _sentetik_metalar() + [m for _, m in _katalog_metalari()]:
        metin = ST.build_tiktok_kit_caption(meta)
        vurgulu = [e for e in _etiketler(metin) if _ai_vurgulu(e)]
        assert not vurgulu, (meta.get("title"), vurgulu)


def test_deterministik():
    for meta in _sentetik_metalar():
        assert ST.build_tiktok_kit_caption(dict(meta)) == ST.build_tiktok_kit_caption(dict(meta))
        assert ST.tiktok_kit_hashtagleri(dict(meta)) == ST.tiktok_kit_hashtagleri(dict(meta))


def test_derleme_dali():
    meta = _derleme_meta()
    etiketler = ST.tiktok_kit_hashtagleri(meta)
    assert "#Derleme" in etiketler and "#HipHop" in etiketler, etiketler
    assert "#GeceSeansıVol1" in etiketler
    assert 5 <= len(etiketler) <= 6, etiketler
    metin = ST.build_tiktok_kit_caption(meta)
    satirlar = [s for s in metin.split("\n\n")]
    assert "derleme" in satirlar[0].casefold() and "Gece Seansı Vol. 1" in satirlar[0]
    hook = satirlar[1]
    assert hook in config.TIKTOK_DERLEME_HOOKS, hook
    assert hook not in config.HOOK_LINES and hook not in config.HOOK_LINES_EN
    assert ST.tiktok_kit_turu(meta) == "derleme"


@pytest.mark.parametrize("stil", [None] + list(config.SET_STILLERI))
def test_dj_set_dali(stil):
    meta = {"title": "Just Relax", "theme": "dj"}
    if stil:
        meta["set_style"] = stil
    etiketler = ST.tiktok_kit_hashtagleri(meta)
    assert "#DJSet" in etiketler and "#JustRelax" in etiketler, etiketler
    assert 5 <= len(etiketler) <= 6, etiketler
    if stil:
        ilk_stil = ST.hashtag(config.SET_STILLERI[stil]["etiketler"][0])
        assert ilk_stil in etiketler, etiketler
    metin = ST.build_tiktok_kit_caption(meta)
    satirlar = metin.split("\n\n")
    assert "Just Relax" in satirlar[0] and "DJ Set" in satirlar[0], satirlar[0]
    assert satirlar[1] in config.TIKTOK_SET_HOOKS_EN, satirlar[1]
    assert "New track out now" not in metin
    assert not any(h in metin for h in config.HOOK_LINES_EN)
    assert ST.tiktok_kit_turu(meta) == "set"


def test_katalog_kit_aciklamasi_2200_utf16_ve_link_yok(ai_modu):
    metalar = [m for _, m in _katalog_metalari()] + _sentetik_metalar()
    assert metalar
    for meta in metalar:
        metin = ST.build_tiktok_kit_caption(meta)
        assert len(metin.encode("utf-16-le")) // 2 <= 2200, meta.get("title")
        for parca in _LINK:
            assert parca not in metin.casefold(), (meta.get("title"), parca)


def test_ai_beyani_modlari_aciklamada():
    meta = {"title": "Kırık Zincir", "theme": "rock"}
    beyan = ST.ai_beyan_satiri(meta)
    for mod, olmali in (("etiket", False), ("aciklama", True), ("etiket+aciklama", True)):
        metin = ST.build_tiktok_kit_caption(meta, ai_beyani=mod)
        assert (beyan in metin) is olmali, mod
        if olmali:
            satirlar = metin.split("\n\n")
            assert satirlar[-2] == beyan, "beyan hashtag bloğundan HEMEN önce"
            assert not satirlar[-2].startswith("#"), "beyan bir hashtag değil"
    # DJ seti İngilizce DJ satırını alır
    set_metin = ST.build_tiktok_kit_caption({"title": "Just Relax", "theme": "dj"},
                                            ai_beyani="aciklama")
    assert config.AI_BEYAN_SATIRLARI["en"]["dj"] in set_metin


# --------------------------------------------------------------------------
# Diğer platformlar DEĞİŞMEDİ (arşiv karşılaştırması)
# --------------------------------------------------------------------------

def test_build_caption_arsivle_ayni_tek_fark_rnb():
    """Arşiv, bu değişiklikten ÖNCEKİ kodla gerçek katalog + sentetik temalardan
    üretildi. `build_caption` yeniden düzenlendi (TikTok kitiyle ortak gövde);
    Shorts/Telegram/Bluesky metni (varsayılan çağrı) bayt bayt aynı kalmalı, yalnız
    `#RB` -> `#RnB`. Instagram/Facebook çağrısı (`ai_beyani=True`, 2026-09-13
    kullanıcı kararı) İKİNCİ beklenen farkı taşır: hashtag bloğundan hemen önce
    TEK beyan satırı — başka hiçbir satır değişmez."""
    with io.open(ARSIV, encoding="utf-8") as f:
        kayitlar = json.load(f)["kayitlar"]
    assert len(kayitlar) >= 20
    assert any("#RB" in k["caption"] for k in kayitlar), "arşiv #RB içermeli (test anlamlı)"
    for k in kayitlar:
        beklenen = k["caption"].replace("#RB", "#RnB")
        assert ST.build_caption(k["meta"]) == beklenen, k["kaynak"]
        govde, etiketler = beklenen.rsplit("\n\n", 1)
        ig_fb = "%s\n\n%s\n\n%s" % (govde, ST.ai_beyan_satiri(k["meta"]), etiketler)
        assert ST.build_caption(k["meta"], ai_beyani=True) == ig_fb, k["kaynak"]
