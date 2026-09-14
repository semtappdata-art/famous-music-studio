# -*- coding: utf-8 -*-
"""YouTube STUDIO PLANLI YÜKLEME (`upload/youtube_studio.py`, 2026-09-13).

Kullanıcı kararı: "YouTube'da bu ve buna benzer bekleme durumlarında Chrome Studio'dan sıra
bekletme yap." Video Studio'dan ŞİMDİ yüklenir, Gizli + "Planla" ile tempo kuralının izin
verdiği public anına kurulur. Tempo EZİLMEZ — yalnız YÜKLEME anı öne alınır.

Bu testler kod tarafını kilitler: plan-oner tempo/golden-hour hesabı, paket metinlerinin
`build_snippet`/`build_shorts_snippet` ile aynı olması, isaretle reddi ve yazımı, tempo
düzeltmesi (Studio planlı projede tempo YÜKLEME değil PUBLIC anından), public an gelmeden
diğer platformların gitmemesi, günde 1 bildirim, cp1254 CLI, gerçek state'e yazılmaması.

Ağa çıkmaz (gönderici sahte, API çağıran her yol yamalı), gerçek `projects/`e ve gerçek
deftere yazmaz (KOKLER + ELLE_ISLEMLER_DEFTERI + DURUM_DOSYASI tmp_path).
"""

import ast
import hashlib
import io
import json
import os
import sys
import time
from datetime import datetime, timezone

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_UPLOAD = os.path.join(_REPO, "upload")
for _yol in (_REPO, _UPLOAD):
    if _yol not in sys.path:
        sys.path.insert(0, _yol)

import auto_process as ap                                   # noqa: E402
import config                                               # noqa: E402
import ek_platform_backfill as EPB                          # noqa: E402
import elle_islem as EI                                     # noqa: E402
import facebook_backfill as FBB                             # noqa: E402
import turev_takvimi as TT                                  # noqa: E402
import uyumluluk                                            # noqa: E402
import youtube_playlists as YP                              # noqa: E402
import youtube_studio as YS                                 # noqa: E402
import youtube_upload as YU                                 # noqa: E402

SAAT = 3600
GUN = 24 * SAAT


def _an(g, s, dk=0, ay=9):
    return datetime(2026, ay, g, s, dk, tzinfo=config.TR_TZ).timestamp()


# 2026-09-13 09:50 TR — Sabah Senin 10:05'te yüklenecek, 12:00'de public.
T = _an(13, 9, 50)


def _yerel(ts):
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(ts))


def _z(ts):
    return datetime.fromtimestamp(ts, timezone.utc).replace(microsecond=0) \
        .isoformat().replace("+00:00", "Z")


def _proje(kok, ad, durum=None, render=True, tema="pop"):
    p = kok / ad
    p.mkdir(parents=True, exist_ok=True)
    (p / "meta.json").write_text(json.dumps({"title": ad, "theme": tema}, ensure_ascii=False),
                                 encoding="utf-8")
    (p / "audio.wav").write_bytes(("ses-" + ad).encode("utf-8"))
    if render:
        (p / "output").mkdir(exist_ok=True)
        (p / "output" / "youtube_16x9.mp4").write_bytes(b"uzun-mp4")
        (p / "output" / "shorts_9x16.mp4").write_bytes(b"kisa-mp4")
    (p / "cover.png").write_bytes(b"png16x9")
    (p / "cover_vertical.png").write_bytes(b"png9x16")
    (p / "state.json").write_text(json.dumps(durum or {}, ensure_ascii=False), encoding="utf-8")
    return str(p)


def _st(p):
    with open(os.path.join(p, "state.json"), encoding="utf-8") as f:
        return json.load(f)


def _sabah(kok, yuklendi=T + 15 * 60, public=_an(13, 12)):
    return _proje(kok / "projects", "Sabah Senin", {
        "youtube_video_id": "SabahSenin1", "youtube_uploaded_at": _yerel(yuklendi),
        "youtube_privacy": "public", "youtube_publish_at": _z(public)})


@pytest.fixture
def kok(tmp_path, monkeypatch):
    for ad in ("projects", "dj_sets", "derlemeler"):
        (tmp_path / ad).mkdir()
    monkeypatch.setattr(uyumluluk, "KOKLER", tuple(str(tmp_path / k) for k in
                                                    ("projects", "dj_sets", "derlemeler")))
    monkeypatch.setenv(EI.ORTAM_DEGISKENI, str(tmp_path / "defter.jsonl"))
    monkeypatch.setattr(YS, "DURUM_DOSYASI", str(tmp_path / "saglik_durum.json"))
    monkeypatch.setattr(YS, "_uyumluluk_hatalari", lambda p: [])
    monkeypatch.setattr(YS, "_shorts_saat", lambda: 0.0)
    return tmp_path


def _klasorler():
    return list(uyumluluk.proje_klasorleri())


# ---------------------------------------------------------------------------
# 1) plan-oner — tempo + golden-hour
# ---------------------------------------------------------------------------

def test_taban_auto_process_ile_ayni():
    assert YS._taban_sn() == ap.MIN_YAYIN_ARALIGI_SN


def test_plan_oner_52sa_taban_sonrasi_ilk_golden_hour(kok):
    _sabah(kok)
    _proje(kok / "projects", "Bu Gece Kazandık")
    s = YS.plan_oner(gun=10, simdi=T)
    assert [o["proje"] for o in s["oneriler"]] == ["Bu Gece Kazandık"]
    o = s["oneriler"][0]
    # 13 Eyl 12:00 + 52 sa = 15 Eyl 16:00 -> golden-hour dışı -> 18:00.
    assert o["onerilen_an"] == "2026-09-15T18:00:00+03:00"
    assert o["shorts_onerilen_an"] == o["onerilen_an"]      # 24 sa kuralı canlı değil
    assert o["sebep"].startswith("tempo")


def test_plan_oner_shorts_24sa_kurali_canliysa_ertesi_gun(kok, monkeypatch):
    monkeypatch.setattr(YS, "_shorts_saat", lambda: 24.0)
    _sabah(kok)
    _proje(kok / "projects", "Bu Gece Kazandık")
    o = YS.plan_oner(simdi=T)["oneriler"][0]
    assert o["onerilen_an"] == "2026-09-15T18:00:00+03:00"
    assert o["shorts_onerilen_an"] == "2026-09-16T18:00:00+03:00"


def test_plan_oner_iki_aday_zincirlenir(kok):
    _sabah(kok)
    _proje(kok / "projects", "Bu Gece Kazandık")
    _proje(kok / "projects", "Yeni Şarkı")
    anlar = {o["proje"]: o["onerilen_an"] for o in YS.plan_oner(simdi=T)["oneriler"]}
    assert anlar["Bu Gece Kazandık"] == "2026-09-15T18:00:00+03:00"
    # 15 Eyl 18:00 + 52 sa = 17 Eyl 22:00 (pencere [18,22) dışında) -> 18 Eyl 12:00.
    assert anlar["Yeni Şarkı"] == "2026-09-18T12:00:00+03:00"


def test_plan_oner_dj_seti_ile_48sa(kok):
    _sabah(kok)
    _proje(kok / "dj_sets", "Gece Seti", {
        "youtube_video_id": "GeceSeti001", "youtube_uploaded_at": _yerel(T - GUN),
        "youtube_privacy": "public", "youtube_publish_at": _z(_an(16, 12))}, tema="dj")
    _proje(kok / "projects", "Bu Gece Kazandık")
    o = YS.plan_oner(simdi=T)["oneriler"][0]
    assert o["onerilen_an"] == "2026-09-18T12:00:00+03:00"    # set + 48 sa


def test_plan_oner_ayni_gun_baska_youtube_yayini_yok(kok):
    _sabah(kok)
    _proje(kok / "projects", "Küllerimden Geç", {
        "youtube_video_id": "Kullerimden", "youtube_uploaded_at": _yerel(T - 200 * SAAT),
        "youtube_privacy": "public", "youtube_public_ani_tempo_disi": _z(_an(15, 13))})
    _proje(kok / "projects", "Bu Gece Kazandık")
    o = YS.plan_oner(simdi=T)["oneriler"][0]
    assert o["onerilen_an"] == "2026-09-16T12:00:00+03:00"


def test_tempo_engeli_yoksa_aday_degil_saatlik_hat_yukler(kok):
    _sabah(kok, yuklendi=T - 200 * SAAT, public=T - 199 * SAAT)
    _proje(kok / "projects", "Bu Gece Kazandık")
    s = YS.plan_oner(simdi=T)
    assert s["oneriler"] == []
    assert any(d["proje"] == "Bu Gece Kazandık" and "tempo engeli yok" in d["sebep"]
               for d in s["aday_degil"])


@pytest.mark.parametrize("durum,render,sebep", [
    ({"yayin_beklet": {"sebep": "x"}}, True, "yayin_beklet"),
    ({}, False, "render"),
])
def test_elemeler(kok, durum, render, sebep):
    _sabah(kok)
    _proje(kok / "projects", "Aday", durum, render=render)
    s = YS.plan_oner(simdi=T)
    assert s["oneriler"] == []
    assert any(d["proje"] == "Aday" and sebep in d["sebep"] for d in s["aday_degil"])


def test_yuklu_ve_dj_projesi_aday_degil(kok):
    _sabah(kok)
    p = _proje(kok / "projects", "Yuklu", {"youtube_video_id": "Zaten123456"})
    d = _proje(kok / "dj_sets", "Set", {}, tema="dj")
    baglam = YS._baglam(YS._katalog()[0])
    assert YS.aday_degerlendir(p, _st(p), baglam, T) == ("degil", "YouTube'a zaten yüklü (Zaten123456)")
    assert "ana katalog dışı" in YS.aday_degerlendir(d, {}, baglam, T)[1]
    assert [x["proje"] for x in YS.plan_oner(simdi=T)["aday_degil"]] == []


def test_uyumluluk_hatasi_aday_degil(kok, monkeypatch):
    _sabah(kok)
    _proje(kok / "projects", "Aday")
    monkeypatch.setattr(YS, "_uyumluluk_hatalari", lambda p: ["md5 kopyası"])
    s = YS.plan_oner(simdi=T)
    assert s["oneriler"] == [] and "uyumluluk" in s["aday_degil"][-1]["sebep"]


# ---------------------------------------------------------------------------
# 2) paket — metinler build_* ile AYNI, kapak, playlist, Studio alanları
# ---------------------------------------------------------------------------

def test_paket_metinleri_build_ile_ayni_ve_sha1(kok):
    _sabah(kok)
    p = _proje(kok / "projects", "Bu Gece Kazandık")
    pk = YS.paket(p, simdi=T, uzun_id="BGKuzun0001", kapak_hazirla=False)
    meta = YU.load_meta(p)
    uzun, kisa = YU.build_snippet(meta), YU.build_shorts_snippet(meta, "BGKuzun0001")
    assert pk["uzun"]["baslik"] == uzun["title"]
    assert pk["uzun"]["aciklama"] == uzun["description"]
    assert pk["uzun"]["etiketler"] == uzun["tags"]
    assert pk["uzun"]["kategori_id"] == "10" and pk["uzun"]["dil"] == "tr"
    assert pk["kisa"]["aciklama"] == kisa["description"]
    assert pk["kisa"]["baslik"] == kisa["title"]
    assert pk["aciklama_sha1"] == hashlib.sha1(uzun["description"].encode("utf-8")).hexdigest()
    assert pk["shorts_aciklama_sha1"] == hashlib.sha1(kisa["description"].encode("utf-8")).hexdigest()
    assert pk["onerilen_an"] == "2026-09-15T18:00:00+03:00"
    assert pk["uzun"]["video"].endswith(os.path.join("output", "youtube_16x9.mp4"))
    alanlar = {a["alan"]: a["deger"] for a in pk["studio_alanlari"]}
    assert alanlar["Değiştirilmiş içerik"] == "Evet"
    assert "çocuklara özel değil" in alanlar["Kitle"]
    assert alanlar["Kategori"] == "Müzik" and alanlar["Video dili"] == "Türkçe"
    assert "Planla" in alanlar["Görünürlük"]


def test_paket_shorts_uzun_id_yoksa_sha1_yok_uyari_var(kok):
    _sabah(kok)
    p = _proje(kok / "projects", "Bu Gece Kazandık")
    pk = YS.paket(p, simdi=T, kapak_hazirla=False)
    assert pk["shorts_aciklama_sha1"] is None
    assert any("--uzun-id" in u for u in pk["uyarilar"])


def test_paket_metinlerinde_suno_yok_ai_satiri_kurala_uygun(kok):
    _sabah(kok)
    p = _proje(kok / "projects", "Bu Gece Kazandık")
    pk = YS.paket(p, simdi=T, uzun_id="BGKuzun0001", kapak_hazirla=False)
    izinli = {s for dil in config.AI_BEYAN_SATIRLARI.values() for s in dil.values()}
    for bolum in (pk["uzun"], pk["kisa"]):
        metin = "\n".join([bolum["baslik"], bolum["aciklama"]] + list(bolum["etiketler"]))
        assert "suno" not in metin.casefold()
        assert "yapay zeka" not in metin.casefold()
        for satir in metin.splitlines():
            if "AI destekli" in satir or "AI-assisted" in satir:
                assert satir.strip() in izinli
    assert YS.metin_denetimi("Suno ile yapıldı")                # denetim gerçekten yakalıyor
    assert YS.metin_denetimi(pk["uzun"]["aciklama"]) == []


def test_paket_playlist_adlari_youtube_playlists_mantigindan(kok):
    _sabah(kok)
    p = _proje(kok / "projects", "Bu Gece Kazandık")
    pk = YS.paket(p, simdi=T, kapak_hazirla=False)
    uzun = [x["anahtar"] for x in pk["uzun"]["playlistler"]]
    kisa = [x["anahtar"] for x in pk["kisa"]["playlistler"]]
    assert uzun == ["pop", YP.ZINCIR_ANAHTARI] and kisa == [YP.SHORTS_ANAHTARI]
    adlar = [x["ad"] for x in pk["uzun"]["playlistler"] + pk["kisa"]["playlistler"]]
    assert YP.KOLEKSIYONLAR[YP.ZINCIR_ANAHTARI]["title"] in adlar
    assert YP.KOLEKSIYONLAR[YP.SHORTS_ANAHTARI]["title"] in adlar
    assert any(a.startswith("Pop Şarkılar") for a in adlar)


def test_kapak_jpeg_2mb_altina_iner(kok, tmp_path):
    kaynak = tmp_path / "cover.png"
    kaynak.write_bytes(b"x")
    cagrilar = []

    def calistir(cmd, **kw):
        cagrilar.append(cmd)
        boyut = 3 * 1024 * 1024 if len(cagrilar) == 1 else 500 * 1024
        with open(cmd[-1], "wb") as f:
            f.write(b"\0" * boyut)
        return type("R", (), {"returncode": 0, "stderr": ""})()
    hedef = str(tmp_path / "out" / "kapak.jpg")
    s = YS.kapak_jpeg(str(kaynak), hedef, calistir=calistir)
    assert s["yol"] == hedef and s["bayt"] <= YS.KAPAK_MAX_BAYT and len(cagrilar) == 2
    assert cagrilar[0][0] == "ffmpeg"


# ---------------------------------------------------------------------------
# 3) isaretle — red ve yazım
# ---------------------------------------------------------------------------

def _isaretle(p, an="2026-09-15T18:00:00+03:00", sha=None, **kw):
    if sha is None:
        sha = YS.sha1(YU.build_snippet(YU.load_meta(p))["description"])
    kw.setdefault("simdi", T)
    kw.setdefault("yuklendi", T)
    return YS.isaretle(p, "BGKuzun0001", an, sha, **kw)


def test_isaretle_yazar_state_io_ve_defter(kok):
    _sabah(kok)
    p = _proje(kok / "projects", "Bu Gece Kazandık")
    s = _isaretle(p, shorts_id="BGKkisa0001")
    st = _st(p)
    public = _an(15, 18)
    assert st["youtube_video_id"] == "BGKuzun0001"
    assert st["youtube_publish_at"] == _z(public) == "2026-09-15T15:00:00Z"
    assert st["youtube_uploaded_at"] == _yerel(T)
    assert st["youtube_privacy"] == "public"          # istenen; YouTube'da private+Planla
    k = st[YS.ALAN]
    assert k["an"] == "2026-09-15T18:00:00+03:00" and k["kaynak"] == "YouTube Studio (Chrome)"
    assert k["sha1"] == s["kayit"]["sha1"] and k["gorunurluk_studio"] == "Gizli + Planla"
    assert st["youtube_shorts_video_id"] == "BGKkisa0001"
    assert st["youtube_shorts_publish_at"] == _z(public)
    assert st["youtube_shorts_uploaded_at"] == _yerel(T)
    assert "youtube_playlists" not in st              # Studio'da eklenmediyse API senkronu
    assert not uyumluluk._yayindan_cekilmis(st)       # playlist/altyazı yayında sayar
    satirlar, _ = EI.oku()
    assert {(r["platform"], r["islem"]) for r in satirlar} == {
        ("youtube", "planladi"), ("youtube_shorts", "planladi")}


def test_isaretle_playlistler_eklendi_bayragi(kok):
    _sabah(kok)
    p = _proje(kok / "projects", "Bu Gece Kazandık")
    _isaretle(p, shorts_id="BGKkisa0001", playlistler_eklendi=True)
    st = _st(p)
    ids = YP._load_playlist_ids()
    assert st["youtube_playlists"] == [ids["pop"], ids[YP.ZINCIR_ANAHTARI], ids[YP.SHORTS_ANAHTARI]]
    assert st["youtube_playlist_id"] == ids["pop"]
    assert st["youtube_shorts_playlist_id"] == ids[YP.SHORTS_ANAHTARI]


@pytest.mark.parametrize("an,beklenen", [
    ("2026-09-14T18:00:00+03:00", "52"),               # taban ihlali
    ("2026-09-16T16:00:00+03:00", "golden-hour"),      # pencere dışı
    ("2026-09-13T08:00:00+03:00", "geçmiş"),           # geçmiş an
])
def test_isaretle_kural_disi_ani_reddeder(kok, an, beklenen):
    _sabah(kok)
    p = _proje(kok / "projects", "Bu Gece Kazandık")
    once = _st(p)
    with pytest.raises(YS.YoutubeStudioHatasi) as e:
        _isaretle(p, an=an)
    assert beklenen in str(e.value)
    assert _st(p) == once and EI.oku()[0] == []


def test_isaretle_sha1_uyusmazsa_bekletmede_ve_kimlik_bozuksa_reddeder(kok):
    _sabah(kok)
    p = _proje(kok / "projects", "Bu Gece Kazandık")
    with pytest.raises(YS.YoutubeStudioHatasi, match="sha1"):
        _isaretle(p, sha="0" * 40)
    with pytest.raises(YS.YoutubeStudioHatasi, match="video kimliği"):
        YS.isaretle(p, "kısa", "2026-09-15T18:00:00+03:00", "x", simdi=T)
    b = _proje(kok / "projects", "Bekleyen", {"yayin_beklet": {"sebep": "render"}})
    with pytest.raises(YS.YoutubeStudioHatasi, match="yayin_beklet"):
        _isaretle(b)
    assert EI.oku()[0] == []


def test_isaretle_shorts_24sa_kurali_canliysa_erken_shorts_reddedilir(kok, monkeypatch):
    monkeypatch.setattr(YS, "_shorts_saat", lambda: 24.0)
    _sabah(kok)
    p = _proje(kok / "projects", "Bu Gece Kazandık")
    with pytest.raises(YS.YoutubeStudioHatasi, match="Shorts"):
        _isaretle(p, shorts_id="BGKkisa0001", shorts_an="2026-09-15T18:00:00+03:00")
    _isaretle(p, shorts_id="BGKkisa0001")
    assert _st(p)["youtube_shorts_publish_at"] == _z(_an(16, 18))


def test_isaretle_ayni_kayit_tekrarinda_zaten(kok):
    _sabah(kok)
    p = _proje(kok / "projects", "Bu Gece Kazandık")
    _isaretle(p)
    assert _isaretle(p)["durum"] == "zaten"


def test_gercek_state_yazimi_testte_reddedilir():
    gercek = os.path.join(_REPO, "projects", "Bu Gece Kazandık")
    yol = os.path.join(gercek, "state.json")
    once = os.path.getmtime(yol) if os.path.isfile(yol) else None
    with pytest.raises(YS.YoutubeStudioHatasi, match="GERÇEK"):
        YS.isaretle(gercek, "BGKuzun0001", "2026-09-15T18:00:00+03:00", "x")
    assert (os.path.getmtime(yol) if os.path.isfile(yol) else None) == once


# ---------------------------------------------------------------------------
# 4) TEMPO DÜZELTMESİ (auto_process) — Studio planlıda tempo PUBLIC anından
# ---------------------------------------------------------------------------

def _ap_proje(tmp_path, ad, **alanlar):
    d = tmp_path / ad
    d.mkdir()
    (d / "meta.json").write_text(json.dumps({"title": ad}), encoding="utf-8")
    (d / "state.json").write_text(json.dumps(alanlar), encoding="utf-8")
    return str(d)


def _studio(an_ts):
    return {"an": datetime.fromtimestamp(an_ts, config.TR_TZ).isoformat(),
            "kaynak": "YouTube Studio (Chrome)", "sha1": "x"}


def test_alan_adi_auto_process_aynasi_ile_ayni():
    assert ap.STUDIO_PLAN_ALANI == YS.ALAN


def test_studio_planli_public_anindan_52sa_yeni_yayini_engeller(tmp_path):
    simdi = time.time()
    public = simdi - 30 * SAAT
    a = _ap_proje(tmp_path, "Planli", youtube_video_id="v", youtube_privacy="public",
                  youtube_uploaded_at=_yerel(simdi - 80 * SAAT), youtube_publish_at=_z(public),
                  **{YS.ALAN: _studio(public)})
    b = _ap_proje(tmp_path, "Yeni")
    assert ap._auto_pace_count([b], [a, b]) == 0                 # 30 sa < 52 sa


def test_studio_planli_gec_isaretlenen_yukleme_ani_tabani_uzatmaz(tmp_path):
    """Kırmızı çekirdek: işaret public anından SONRA atıldıysa `youtube_uploaded_at`
    public anından geç olur. Eski kod max(yükleme, public) aldığı için tabanı
    yükleme damgasından yeniden başlatıyordu."""
    simdi = time.time()
    public = simdi - 53 * SAAT
    a = _ap_proje(tmp_path, "Planli", youtube_video_id="v", youtube_privacy="public",
                  youtube_uploaded_at=_yerel(simdi - 10 * SAAT), youtube_publish_at=_z(public),
                  **{YS.ALAN: _studio(public)})
    b = _ap_proje(tmp_path, "Yeni")
    assert abs(ap._son_yeni_yayin_ani([a]) - public) < 2
    assert ap._auto_pace_count([b], [a, b]) == 1


def test_studio_planli_publish_at_okunamazsa_kayittaki_an_sayilir(tmp_path):
    simdi = time.time()
    public = simdi + 10 * SAAT
    a = _ap_proje(tmp_path, "Planli", youtube_video_id="v", youtube_privacy="public",
                  youtube_uploaded_at=_yerel(simdi - 100 * SAAT), youtube_publish_at="bozuk",
                  **{YS.ALAN: _studio(public)})
    assert abs(ap._son_yeni_yayin_ani([a]) - public) < 2


def test_studio_yuklemesi_gunluk_pencereyi_baslatmaz(tmp_path):
    """Studio'dan ŞİMDİ yüklenen ama 40 sa sonra public olacak video izleyiciye görünen bir
    paylaşım değil: arkadaki geri doldurmayı (taban muaf) günlük pencereyle bekletmemeli."""
    simdi = time.time()
    public = simdi + 40 * SAAT
    a = _ap_proje(tmp_path, "Planli", youtube_video_id="v", youtube_privacy="public",
                  youtube_uploaded_at=_yerel(simdi - SAAT), youtube_publish_at=_z(public),
                  youtube_shorts_uploaded_at=_yerel(simdi - SAAT),
                  **{YS.ALAN: _studio(public)})
    geri = _ap_proje(tmp_path, "Geri", youtube_video_id="g",
                     youtube_uploaded_at=_yerel(simdi - 300 * SAAT))
    assert ap._auto_pace_count([geri], [a, geri]) == 1


def test_studio_public_ani_gectiyse_gunluk_pencerede_sayilir(tmp_path):
    simdi = time.time()
    public = simdi - 2 * SAAT
    a = _ap_proje(tmp_path, "Planli", youtube_video_id="v", youtube_privacy="public",
                  youtube_uploaded_at=_yerel(simdi - 60 * SAAT), youtube_publish_at=_z(public),
                  **{YS.ALAN: _studio(public)})
    geri = _ap_proje(tmp_path, "Geri", youtube_video_id="g",
                     youtube_uploaded_at=_yerel(simdi - 300 * SAAT))
    assert ap._auto_pace_count([geri], [a, geri]) == 0           # 2 sa < 24 sa / 1


# ---------------------------------------------------------------------------
# 5) Public an gelmeden diğer platformlar GİTMEZ
# ---------------------------------------------------------------------------

def _planli_state(public, simdi):
    return {"youtube_video_id": "BGKuzun0001", "youtube_privacy": "public",
            "youtube_uploaded_at": _yerel(simdi - SAAT), "youtube_publish_at": _z(public),
            "youtube_shorts_video_id": "BGKkisa0001", "youtube_shorts_privacy": "public",
            "youtube_shorts_publish_at": _z(public), YS.ALAN: _studio(public)}


def test_telegram_bluesky_public_oncesi_aday_degil_sonra_aday(tmp_path):
    simdi = time.time()
    assert EPB._public_ani(_planli_state(simdi + 40 * SAAT, simdi), simdi) is None
    assert EPB._public_ani(_planli_state(simdi - SAAT, simdi - 2 * SAAT), simdi) is not None


def test_facebook_backfill_public_oncesi_aday_degil(tmp_path, monkeypatch):
    simdi = time.time()
    once = _proje(tmp_path / "projects", "Planli", _planli_state(simdi + 40 * SAAT, simdi))
    sonra = _proje(tmp_path / "projects", "Acik", _planli_state(simdi - SAAT, simdi - 2 * SAAT))
    monkeypatch.setattr(FBB, "BASE", str(tmp_path / "projects"))
    monkeypatch.setattr(FBB, "belirsiz_mi", lambda st, k: False)
    liste = FBB.eksik_projeler()
    assert sonra in liste and once not in liste


def test_tiktok_t0_yukleme_degil_public_ani(tmp_path):
    simdi = time.time()
    public = simdi + 40 * SAAT
    assert abs(TT.t0_bul(_planli_state(public, simdi)) - public) < 2


def test_studio_planli_public_oncesi_sira_disi_sonra_secilir(tmp_path):
    simdi = time.time()
    once = _ap_proje(tmp_path, "Once", **_planli_state(simdi + 40 * SAAT, simdi))
    sonra = _ap_proje(tmp_path, "Sonra", **_planli_state(simdi - SAAT, simdi - 2 * SAAT))
    normal = _ap_proje(tmp_path, "Normal")
    secilebilir, bekleyen = ap._studio_planli_bekleyenleri_ayir([once, sonra, normal])
    assert secilebilir == [sonra, normal] and bekleyen == [once]


def test_process_project_public_oncesi_instagram_facebook_tiktok_adimina_gecmez(
        tmp_path, monkeypatch):
    simdi = time.time()
    p = _proje(tmp_path / "projects", "Planli", _planli_state(simdi + 40 * SAAT, simdi))
    olay = []
    import generate_cover
    import instagram_upload
    monkeypatch.setattr(generate_cover, "generate", lambda d: None)
    monkeypatch.setattr(ap, "_is_rendered", lambda d: True)
    monkeypatch.setattr(uyumluluk, "kontrol", lambda d, a: ([], []))
    monkeypatch.setattr(uyumluluk, "rapor_yaz", lambda *a, **k: None)
    monkeypatch.setattr(YP, "sync_project", lambda *a, **k: olay.append("playlist"))
    monkeypatch.setattr(YP, "get_authenticated_service", lambda: object())
    monkeypatch.setattr(ap, "_check_youtube_captions", lambda d, s: olay.append("altyazi"))
    monkeypatch.setattr(ap, "_tiktok_adimi", lambda *a: olay.append("tiktok"))
    monkeypatch.setattr(ap, "_check_instagram_pending", lambda d: olay.append("ig-bekleyen"))
    monkeypatch.setattr(instagram_upload, "upload_video", lambda d: olay.append("instagram"))
    monkeypatch.setattr(ap, "_ek_platformlari_isle", lambda *a: olay.append("ek"))
    monkeypatch.setattr(ap, "log", lambda m: olay.append(str(m)))
    ap.process_project(p, "public")
    assert not {"tiktok", "instagram", "ig-bekleyen", "ek"} & set(olay)
    assert any("Studio" in str(x) and "public" in str(x) for x in olay)


def test_main_studio_ayiricisi_drainden_sonra_kademelemeden_once():
    agac = ast.parse(open(os.path.join(_REPO, "auto_process.py"), encoding="utf-8").read())
    main = next(n for n in agac.body if isinstance(n, ast.FunctionDef) and n.name == "main")

    def satir(ad):
        return [n.lineno for n in ast.walk(main)
                if isinstance(n, ast.Call) and getattr(n.func, "id", None) == ad]
    dr, st, pace = (satir("_yalniz_drain_bekleyenleri_ayir"),
                    satir("_studio_planli_bekleyenleri_ayir"), satir("_auto_pace_count"))
    assert dr and st and pace and min(dr) < min(st) < min(pace)
    son = main.body[-1]
    govde = ast.get_source_segment(open(os.path.join(_REPO, "auto_process.py"),
                                        encoding="utf-8").read(), son)
    assert govde.index("_tiktok_web_sirasi()") < govde.index("_youtube_studio_sirasi()")


# ---------------------------------------------------------------------------
# 6) Bildirim — günde en fazla 1 (kalıp B)
# ---------------------------------------------------------------------------

def test_bildirim_gunde_bir_ve_metin(kok):
    _sabah(kok)
    _proje(kok / "projects", "Bu Gece Kazandık")
    giden, satir = [], []
    gonder = lambda b, m: giden.append((b, m)) or True       # noqa: E731
    s = YS.plan_bildirimi(satir.append, simdi=T, klasorler=_klasorler(), gonder=gonder)
    assert s["gonderilen"] == "Bu Gece Kazandık"
    assert giden[0][1] == ("YouTube: Bu Gece Kazandık tempo nedeniyle bekliyor; Studio'dan "
                           "15.09 18:00'a planlanabilir. Claude Code'da 'YouTube Studio'dan "
                           "planla' yaz.")
    YS.plan_bildirimi(satir.append, simdi=T + 3 * SAAT, klasorler=_klasorler(), gonder=gonder)
    assert len(giden) == 1
    YS.plan_bildirimi(satir.append, simdi=T + GUN, klasorler=_klasorler(), gonder=gonder)
    assert len(giden) == 2
    assert all(x.startswith("  YouTube Studio planı:") for x in satir)


def test_bildirim_bayrak_kapaliysa_gonderilmez_ve_varsayilan_true(kok, monkeypatch):
    assert getattr(config, "YOUTUBE_STUDIO_PLAN_BILDIRIM") is True
    monkeypatch.setattr(config, "YOUTUBE_STUDIO_PLAN_BILDIRIM", False, raising=False)
    _sabah(kok)
    _proje(kok / "projects", "Bu Gece Kazandık")
    giden = []
    s = YS.plan_bildirimi(lambda m: None, simdi=T, klasorler=_klasorler(),
                          gonder=lambda b, m: giden.append(m) or True)
    assert giden == [] and "kapalı" in s["sebep"]


def test_bildirim_test_ortaminda_gercek_katalogu_okumaz(monkeypatch):
    monkeypatch.setattr(YS, "plan_oner", lambda *a, **k: pytest.fail("gerçek katalog okundu"))
    s = YS.plan_bildirimi(lambda m: None)
    assert "test ortamı" in s["sebep"]


def test_bildirim_gonderim_hatasi_damga_yazmaz(kok):
    _sabah(kok)
    _proje(kok / "projects", "Bu Gece Kazandık")
    s = YS.plan_bildirimi(lambda m: None, simdi=T, klasorler=_klasorler(),
                          gonder=lambda b, m: False)
    assert s["gonderilen"] is None and not os.path.isfile(YS.DURUM_DOSYASI)


# ---------------------------------------------------------------------------
# 7) CLI — cp1254 konsolda çökmez
# ---------------------------------------------------------------------------

def test_cli_cp1254_cokmez(kok, monkeypatch):
    _sabah(kok, yuklendi=time.time() - SAAT, public=time.time() + 5 * SAAT)
    _proje(kok / "projects", "Kırık Şarkı")
    for argv in (["plan-oner", "--json"], ["paket", "--proje", "Kırık Şarkı", "--json",
                                           "--kapaksiz"], ["durum", "--json"]):
        tampon = io.BytesIO()
        akis = io.TextIOWrapper(tampon, encoding="cp1254")
        monkeypatch.setattr(sys, "stdout", akis)
        assert YS.main(argv) == 0
        akis.flush()
        monkeypatch.setattr(sys, "stdout", sys.__stdout__)
        cikti = tampon.getvalue().decode("utf-8")
        json.loads(cikti)
        if argv[0] != "durum":
            assert "Kırık Şarkı" in cikti


def test_cli_isaretle_red_kodu_2_ve_yazmaz(kok, monkeypatch, capsys):
    _sabah(kok)
    p = _proje(kok / "projects", "Bu Gece Kazandık")
    once = _st(p)
    kod = YS.main(["isaretle", "--proje", "Bu Gece Kazandık", "--video-id", "BGKuzun0001",
                   "--an", "2026-09-14T18:00:00+03:00", "--sha1", "x"])
    assert kod == 2 and _st(p) == once
