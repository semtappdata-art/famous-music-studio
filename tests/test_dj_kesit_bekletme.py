# -*- coding: utf-8 -*-
"""DJ kesit BEKLETME + seçim kuralları (kullanıcı kararı 2026-09-13).

VAKA: `dj_sets/Just Relax` state'inde `dj_tarama_temiz: true` var, kesitlerde
`enerji` alanı YOK. Bugünkü kodla 18 Eylül Cuma 18:00 DJ koşusu `kesit_sec`'in
"enerji yoksa dosya adı sırası" dalına düşüp `clip_01.mp4`'ü (setin 5:32 anı)
YouTube'a yükleyecekti — yani telif eşleşmelerinin toplandığı İLK 6 DAKİKANIN
içinden, küratörlüksüz bir kesit.

Üç ayrı kemer, üçü de FAIL-CLOSED:
  1. `kesit_beklet` (state) — YALNIZ kesit yayınını durdurur; `yayin_beklet`
     gibi uyumluluk HATASI üretmez, yani setin başka akışlarına dokunmaz.
  2. İlk `config.DJ_KESIT_ILK_YASAK_SN` saniyeden kesit seçilmez; `bas`
     bilinmeyen kesit de seçilmez.
  3. Sıralama bilgisi (`enerji` ya da `izlenme_sirasi`) olmayan kesit seçilmez;
     bunun yerine TEK bir bildirim gider (state damgasıyla).

Ağa ÇIKMAZ: gönderici sahte, `uyumluluk.kontrol` sahte, her şey tmp_path'te.
"""

import datetime
import json
import os
import time

import pytest

import config
import dj_clips
import uyumluluk


def _set_kur(kok, ad="Test Set", state=None, kesitler=("clip_01.mp4",)):
    d = os.path.join(str(kok), ad)
    os.makedirs(os.path.join(d, "output"))
    with open(os.path.join(d, "meta.json"), "w", encoding="utf-8") as f:
        json.dump({"title": ad, "theme": "dj"}, f)
    with open(os.path.join(d, "state.json"), "w", encoding="utf-8") as f:
        json.dump(state or {}, f, ensure_ascii=False)
    for n in kesitler:
        with open(os.path.join(d, "output", n), "wb") as f:
            f.write(b"x")
    return d


def _st(d):
    with open(os.path.join(d, "state.json"), encoding="utf-8") as f:
        return json.load(f)


def _hazir(clips, **ek):
    st = {
        "youtube_video_id": "TAM",
        "youtube_shorts_video_id": "S1",
        "youtube_shorts_uploaded_at": time.strftime(
            "%Y-%m-%dT%H:%M:%S",
            time.localtime(time.time() - dj_clips.KESIT_MIN_ARA_SN - 3600)),
        "dj_tarama_temiz": True,
        "dj_clips": clips,
    }
    st.update(ek)
    return st


BEKLET = {"sebep": "kullanıcı kararı 2026-09-13: test", "istendi_at": "2026-09-13T04:00:00+03:00"}
IYI = [{"dosya": "clip_01.mp4", "bas": 900.0, "son": 945.0, "enerji": 1}]


@pytest.fixture(autouse=True)
def _ortam(monkeypatch):
    monkeypatch.setattr(config, "DJ_ON_TARAMA", True)
    monkeypatch.setattr(uyumluluk, "kontrol", lambda proje, asama="render": ([], []))
    monkeypatch.setattr(dj_clips, "_kapi_uyar", lambda anahtar, mesaj: None)


def _yukleme_yasak(monkeypatch):
    cagri = []
    monkeypatch.setattr(dj_clips, "kesit_yayinla",
                        lambda set_dir, kesit, **k: cagri.append((set_dir, kesit)))
    return cagri


# --- 1. kesit_beklet ---------------------------------------------------------

def test_kesit_beklet_kesiti_durdurur(tmp_path, monkeypatch):
    d = _set_kur(tmp_path, state=_hazir(IYI, kesit_beklet=BEKLET))
    kesit, sebep = dj_clips.yayina_uygun_mu(d)
    assert kesit is None
    assert "kesit_beklet" in sebep and "test" in sebep
    cagri = _yukleme_yasak(monkeypatch)
    gonderilen = []
    s = dj_clips.supur(str(tmp_path), log=lambda *a: None,
                       gonder=lambda b, m: gonderilen.append(b) or True)
    assert s["yayinlanan"] == 0 and cagri == [] and gonderilen == []


@pytest.mark.parametrize("deger", ["evet", ["x"], 1, {"sebep": ""}])
def test_kesit_beklet_dict_olmayan_dolu_deger_de_bekletir(tmp_path, deger):
    d = _set_kur(tmp_path, state=_hazir(IYI, kesit_beklet=deger))
    kesit, _ = dj_clips.yayina_uygun_mu(d)
    assert kesit is None


@pytest.mark.parametrize("deger", [None, "", {}, []])
def test_bos_kesit_beklet_bekletme_sayilmaz(tmp_path, deger):
    d = _set_kur(tmp_path, state=_hazir(IYI, kesit_beklet=deger))
    kesit, sebep = dj_clips.yayina_uygun_mu(d)
    assert kesit is not None, sebep


def test_kesit_beklet_uyumluluk_hatasi_URETMEZ_diger_akislar_etkilenmez(tmp_path, monkeypatch):
    """`yayin_beklet`'ten farkı bu: politika kapısı temiz kalır, yani
    Facebook/Telegram/Bluesky geri doldurması, TikTok planı vb. durmaz."""
    monkeypatch.undo()
    d = _set_kur(tmp_path, state={"kesit_beklet": BEKLET, "youtube_video_id": "v"},
                 kesitler=())
    hatalar, _ = uyumluluk.kontrol(d, "yukleme")
    assert not any("kesit_beklet" in h or "BEKLET" in h for h in hatalar), hatalar


def test_kesit_yayinla_dogrudan_cagrilsa_da_bekletmede_RAISE(tmp_path):
    d = _set_kur(tmp_path, state=_hazir(IYI, kesit_beklet=BEKLET))
    with pytest.raises(RuntimeError) as e:
        dj_clips.kesit_yayinla(d, IYI[0], log=lambda *a: None)
    assert "kesit_beklet" in str(e.value)
    assert "youtube_clip_video_id" not in _st(d)


def test_bekletme_alani_adi_configten():
    assert config.DJ_KESIT_BEKLETME_ALANI == "kesit_beklet"


# --- 2. ilk 6 dakika -----------------------------------------------------------

def test_ilk_6_dakika_haric_sonraki_en_enerjili_secilir(tmp_path):
    clips = [{"dosya": "clip_01.mp4", "bas": 332.53, "son": 377.53, "enerji": 1},
             {"dosya": "clip_02.mp4", "bas": 1491.35, "son": 1536.35, "enerji": 2}]
    d = _set_kur(tmp_path, state=_hazir(clips), kesitler=("clip_01.mp4", "clip_02.mp4"))
    kesit, sebep = dj_clips.yayina_uygun_mu(d)
    assert kesit is not None and kesit["dosya"] == "clip_02.mp4", sebep


def test_tum_kesitler_ilk_6_dakikadaysa_kesit_yok(tmp_path):
    clips = [{"dosya": "clip_01.mp4", "bas": 10.0, "son": 55.0, "enerji": 1},
             {"dosya": "clip_02.mp4", "bas": 315.0, "son": 360.0, "enerji": 2}]
    d = _set_kur(tmp_path, state=_hazir(clips), kesitler=("clip_01.mp4", "clip_02.mp4"))
    kesit, sebep = dj_clips.yayina_uygun_mu(d)
    assert kesit is None and "ilk" in sebep and "dakika" in sebep


def test_pencere_6_dakika_sinirina_tasiyorsa_da_elenir(tmp_path):
    """Kural pencerenin BAŞINA bakar: 350-395 penceresi ilk 6 dakikaya değiyor."""
    clips = [{"dosya": "clip_01.mp4", "bas": 350.0, "son": 395.0, "enerji": 1}]
    d = _set_kur(tmp_path, state=_hazir(clips))
    assert dj_clips.kesit_sec(d) is None


@pytest.mark.parametrize("bas", [None, "abc", -5])
def test_bas_bilinmeyen_kesit_secilmez(tmp_path, bas):
    k = {"dosya": "clip_01.mp4", "son": 945.0, "enerji": 1}
    if bas is not None:
        k["bas"] = bas
    d = _set_kur(tmp_path, state=_hazir([k]))
    assert dj_clips.kesit_sec(d) is None


def test_esik_configten_okunuyor(tmp_path, monkeypatch):
    clips = [{"dosya": "clip_01.mp4", "bas": 332.53, "son": 377.53, "enerji": 1}]
    d = _set_kur(tmp_path, state=_hazir(clips))
    assert dj_clips.kesit_sec(d) is None
    monkeypatch.setattr(config, "DJ_KESIT_ILK_YASAK_SN", 100)
    assert dj_clips.kesit_sec(d)["dosya"] == "clip_01.mp4"


def test_kesit_yayinla_ilk_6_dakikadaki_kesidi_RAISE(tmp_path):
    k = {"dosya": "clip_01.mp4", "bas": 332.53, "son": 377.53, "enerji": 1}
    d = _set_kur(tmp_path, state=_hazir([k]))
    with pytest.raises(RuntimeError):
        dj_clips.kesit_yayinla(d, k, log=lambda *a: None)
    assert "youtube_clip_video_id" not in _st(d)


# --- 3. sıralama bilgisi yok -> kesit yok, TEK bildirim --------------------------

JR_CLIPS = [{"dosya": "clip_01.mp4", "bas": 332.53, "son": 377.53, "bayt": 2505728},
            {"dosya": "clip_02.mp4", "bas": 1491.35, "son": 1536.35, "bayt": 2512728},
            {"dosya": "clip_03.mp4", "bas": 2101.41, "son": 2146.41, "bayt": 2514612}]
JR_DOSYA = ("clip_01.mp4", "clip_02.mp4", "clip_03.mp4")


def test_enerji_yoksa_kesit_secilmez(tmp_path):
    d = _set_kur(tmp_path, state=_hazir(JR_CLIPS), kesitler=JR_DOSYA)
    assert dj_clips.kesit_sec(d) is None
    kesit, sebep = dj_clips.yayina_uygun_mu(d)
    assert kesit is None and sebep.startswith(dj_clips.SIRALAMA_EKSIK_SEBEBI)


def test_izlenme_sirasi_da_siralama_bilgisi_sayilir(tmp_path):
    clips = [dict(JR_CLIPS[1], izlenme_sirasi=2), dict(JR_CLIPS[2], izlenme_sirasi=1)]
    d = _set_kur(tmp_path, state=_hazir(clips), kesitler=JR_DOSYA[1:])
    assert dj_clips.kesit_sec(d)["dosya"] == "clip_03.mp4"


def test_izlenme_sirasi_enerjinin_ONUNE_gecer(tmp_path):
    clips = [dict(JR_CLIPS[1], enerji=1), dict(JR_CLIPS[2], enerji=2, izlenme_sirasi=1)]
    d = _set_kur(tmp_path, state=_hazir(clips), kesitler=JR_DOSYA[1:])
    assert dj_clips.kesit_sec(d)["dosya"] == "clip_03.mp4"


def test_siralama_eksikse_TEK_bildirim_gider_ve_damgalanir(tmp_path, monkeypatch):
    d = _set_kur(tmp_path, state=_hazir(JR_CLIPS), kesitler=JR_DOSYA)
    cagri = _yukleme_yasak(monkeypatch)
    gonderilen = []

    def gonder(baslik, mesaj):
        gonderilen.append((baslik, mesaj))
        return True

    s1 = dj_clips.supur(str(tmp_path), log=lambda *a: None, gonder=gonder)
    s2 = dj_clips.supur(str(tmp_path), log=lambda *a: None, gonder=gonder)
    assert s1["yayinlanan"] == 0 and s2["yayinlanan"] == 0 and cagri == []
    assert len(gonderilen) == 1, gonderilen
    assert "Test Set" in gonderilen[0][1]
    assert _st(d).get("kesit_siralama_bildirildi_at")


def test_bildirim_gonderilemezse_damga_atilmaz_sonraki_kosu_dener(tmp_path, monkeypatch):
    d = _set_kur(tmp_path, state=_hazir(JR_CLIPS), kesitler=JR_DOSYA)
    _yukleme_yasak(monkeypatch)
    sayac = []
    dj_clips.supur(str(tmp_path), log=lambda *a: None,
                   gonder=lambda b, m: sayac.append(1) and False)
    assert "kesit_siralama_bildirildi_at" not in _st(d)
    dj_clips.supur(str(tmp_path), log=lambda *a: None,
                   gonder=lambda b, m: sayac.append(1) or True)
    assert len(sayac) == 2 and _st(d).get("kesit_siralama_bildirildi_at")


def test_kuru_kosu_bildirim_gondermez_state_yazmaz(tmp_path):
    d = _set_kur(tmp_path, state=_hazir(JR_CLIPS), kesitler=JR_DOSYA)
    once = _st(d)
    dj_clips.supur(str(tmp_path), log=lambda *a: None, dry_run=True,
                   gonder=lambda b, m: (_ for _ in ()).throw(AssertionError("gönderdi")))
    assert _st(d) == once


def test_bekletilen_set_siralama_bildirimi_de_ALMAZ(tmp_path, monkeypatch):
    _set_kur(tmp_path, state=_hazir(JR_CLIPS, kesit_beklet=BEKLET), kesitler=JR_DOSYA)
    _yukleme_yasak(monkeypatch)
    gonderilen = []
    dj_clips.supur(str(tmp_path), log=lambda *a: None,
                   gonder=lambda b, m: gonderilen.append(1) or True)
    assert gonderilen == []


# --- 4. Just Relax'in gerçek şekli, 18 Eylül 18:00 ------------------------------

def _just_relax_state(**ek):
    st = {"youtube_video_id": "wo2xZBU6VjU",
          "youtube_shorts_video_id": "257Hke4MSMg",
          "youtube_shorts_uploaded_at": "2026-09-07T16:18:57",
          "dj_tarama_temiz": True, "dj_clips": JR_CLIPS}
    st.update(ek)
    return st


def test_just_relax_18_eylulde_kesit_YAYINLANMAZ(tmp_path):
    t = time.mktime(datetime.datetime(2026, 9, 18, 18, 0, 30).timetuple())
    d = _set_kur(tmp_path, "Just Relax", _just_relax_state(), JR_DOSYA)
    kesit, _ = dj_clips.yayina_uygun_mu(d, simdi=t)
    assert kesit is None
    d2 = _set_kur(tmp_path, "Just Relax B", _just_relax_state(kesit_beklet=BEKLET), JR_DOSYA)
    kesit, sebep = dj_clips.yayina_uygun_mu(d2, simdi=t)
    assert kesit is None and "kesit_beklet" in sebep
