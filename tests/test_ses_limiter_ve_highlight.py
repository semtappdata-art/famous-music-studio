# -*- coding: utf-8 -*-
"""Render öncesi koşullu true-peak limiter + Shorts kesitinin `highlight_start`
ile nakarat başından başlaması (2026-09-13, `suno_kalite_onerileri.md` §1 #8/#9).

LİMİTER — neden KOŞULLU ve neden loudnorm DEĞİL:
Suno çıktıları zaten −12,9 … −14,8 LUFS. Genel normalizasyon bir şey
kazandırmıyor, üstelik tek geçişli loudnorm pompalayabilir. Tek gerçek risk
true peak: iki ses −0,5 / −0,7 dBTP'de ve AAC 192k kodlaması tepeyi taşırabilir.
Bu yüzden zincire YALNIZ ölçülen TP −1,0 dBTP'yi AŞARSA limiter giriyor.

ÖLÇÜM ARIZASI RENDER'I DURDURMAMALI: limiter bir iyileştirme, kapı değil.
ffmpeg ölçemezse eski davranış (limitersiz) sürer ve log'a UYARI düşer —
"sessizce limitersiz" değil, görünür biçimde limitersiz.

Burada ffmpeg ÇALIŞTIRILMIYOR: ölçüm ve render taklit. Gerçek ffmpeg davranışı
(4× aşırı örneklemeli alimiter'ın gerçek dosyada TP'yi −1'in altına çektiği,
düz alimiter'ın ise AAC sonrası TP'yi KÖTÜLEŞTİRDİĞİ) geliştirme sırasında
katalog dosyalarıyla elle ölçüldü; bkz. `config.SES_LIMITER_*` yorumu.
"""

import hashlib
import json
import os

import pytest

import config
import dj_clips
import ffmpeg_utils
import render


# ---------------------------------------------------------------------------
# ffmpeg_utils.ses_olc — ebur128 özet ayrıştırması
# ---------------------------------------------------------------------------

_EBUR128_CIKTI = """\
[Parsed_ebur128_0 @ 0000] t: 0.1  TARGET:-23 LUFS    M:-120.7 S:-120.7     I: -70.0 LUFS       LRA:   0.0 LU  FTPK: -5.0 dBFS  TPK: -5.0 dBFS
[Parsed_ebur128_0 @ 0000] Summary:

  Integrated loudness:
    I:         -13.1 LUFS
    Threshold: -23.2 LUFS

  Loudness range:
    LRA:         3.7 LU
    Threshold: -33.3 LUFS
    LRA low:   -15.0 LUFS
    LRA high:  -11.3 LUFS

  True peak:
    Peak:       -0.5 dBFS
"""


class _Sonuc:
    def __init__(self, rc, stderr):
        self.returncode = rc
        self.stderr = stderr
        self.stdout = ""


def test_ses_olc_ozeti_ayristiriyor_ara_satirlari_degil(monkeypatch):
    cagrilar = []

    def sahte_run(cmd, **k):
        cagrilar.append(cmd)
        return _Sonuc(0, _EBUR128_CIKTI)

    monkeypatch.setattr(ffmpeg_utils.subprocess, "run", sahte_run)
    olcum = ffmpeg_utils.ses_olc("x.wav")
    assert olcum == {"lufs": -13.1, "tp": -0.5, "lra": 3.7}
    assert any("ebur128=peak=true" in str(p) for p in cagrilar[0])


def test_ses_olc_ffmpeg_hatasinda_istisna(monkeypatch):
    monkeypatch.setattr(ffmpeg_utils.subprocess, "run", lambda c, **k: _Sonuc(1, "bozuk"))
    with pytest.raises(RuntimeError):
        ffmpeg_utils.ses_olc("x.wav")


def test_ses_olc_ozet_yoksa_ya_da_sonsuzsa_istisna(monkeypatch):
    monkeypatch.setattr(ffmpeg_utils.subprocess, "run", lambda c, **k: _Sonuc(0, "ozet yok"))
    with pytest.raises(RuntimeError):
        ffmpeg_utils.ses_olc("x.wav")
    sessiz = _EBUR128_CIKTI.replace("-0.5 dBFS", "-inf dBFS")
    monkeypatch.setattr(ffmpeg_utils.subprocess, "run", lambda c, **k: _Sonuc(0, sessiz))
    with pytest.raises(RuntimeError):
        ffmpeg_utils.ses_olc("x.wav")


# ---------------------------------------------------------------------------
# Karar kuralı
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("tp,beklenen", [
    (-0.5, True), (-0.7, True), (-0.99, True),
    (-1.0, False),            # "AŞIYORSA": tam sınır limiter almıyor
    (-1.5, False), (-4.4, False),
])
def test_limiter_yalniz_tp_esigi_asinca(tp, beklenen):
    assert config.SES_TP_ESIK_DBTP == -1.0
    assert render.limiter_gerekli({"tp": tp}) is beklenen


def test_limiter_olcum_yoksa_eklenmiyor():
    assert render.limiter_gerekli(None) is False
    assert render.limiter_gerekli({}) is False


def test_limiter_bayragi_kapaliysa_eklenmiyor(monkeypatch):
    monkeypatch.setattr(config, "SES_LIMITER_ACIK", False)
    assert render.limiter_gerekli({"tp": -0.1}) is False


def test_limiter_filtresi_loudnorm_icermiyor_ve_seviye_kapali():
    f = ffmpeg_utils.limiter_filtresi()
    assert "alimiter" in f
    assert "level=false" in f           # otomatik kazanç KAPALI: loudness değişmesin
    assert "loudnorm" not in f and "dynaudnorm" not in f


# ---------------------------------------------------------------------------
# render_video: -af yalnız ses_limiter=True iken
# ---------------------------------------------------------------------------

def _render_video_komutu(monkeypatch, tmp_path, **k):
    komutlar = []

    def sahte_run(cmd, **kw):
        komutlar.append(cmd)
        return _Sonuc(0, "")

    monkeypatch.setattr(ffmpeg_utils.subprocess, "run", sahte_run)
    monkeypatch.setattr(ffmpeg_utils, "get_audio_duration", lambda p: 120.0)
    monkeypatch.setattr(ffmpeg_utils, "bastaki_sessizlik", lambda p: 0.0)
    monkeypatch.setattr(ffmpeg_utils, "ensure_card_mask", lambda: "mask.png")
    monkeypatch.setattr(ffmpeg_utils, "ensure_vignette", lambda *a: "vig.png")
    ffmpeg_utils.render_video(None, "a.wav", str(tmp_path / "o.mp4"), 1920, 1080,
                              "T", "pop", **k)
    return komutlar[-1]


def test_render_video_limiter_istenince_af_ekleniyor(monkeypatch, tmp_path):
    cmd = _render_video_komutu(monkeypatch, tmp_path, ses_limiter=True)
    assert "-af" in cmd
    assert cmd[cmd.index("-af") + 1] == ffmpeg_utils.limiter_filtresi()


def test_render_video_varsayilan_eski_komut(monkeypatch, tmp_path):
    """Varsayılan (DJ kesitleri dahil bugünkü bütün çağıranlar) HİÇ değişmiyor."""
    cmd = _render_video_komutu(monkeypatch, tmp_path)
    assert "-af" not in cmd
    assert not any("alimiter" in str(p) for p in cmd)


# ---------------------------------------------------------------------------
# render_project: ölçüm -> state -> karar
# ---------------------------------------------------------------------------

def _proje(tmp_path, monkeypatch, meta=None, state=None, olcum=None, olcum_hatasi=None,
           highlight=(10.0, 55.0)):
    (tmp_path / "audio.wav").write_bytes(b"RIFF0000WAVEdata")
    (tmp_path / "cover.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (tmp_path / "meta.json").write_text(
        json.dumps(meta if meta is not None else {"title": "Test", "theme": "pop"}),
        encoding="utf-8")
    if state is not None:
        (tmp_path / "state.json").write_text(json.dumps(state), encoding="utf-8")

    kayit = {"render": [], "olcum_sayisi": 0, "highlight_sayisi": 0}

    def sahte_olc(yol):
        kayit["olcum_sayisi"] += 1
        if olcum_hatasi is not None:
            raise olcum_hatasi
        return dict(olcum)

    def sahte_highlight(a, s):
        kayit["highlight_sayisi"] += 1
        return highlight

    def sahte_render(art, audio, output_path, w, h, *a, **k):
        kayit["render"].append({"w": w, "h": h, **k})
        open(output_path, "wb").write(b"\x00" * 8)

    monkeypatch.setattr(render.validate_project, "validate", lambda d: ([], []))
    monkeypatch.setattr(render.validate_project, "print_report", lambda d, e, u: None)
    monkeypatch.setattr(render, "find_highlight", sahte_highlight)
    monkeypatch.setattr(render.ffmpeg_utils, "ensure_card_mask", lambda: None)
    monkeypatch.setattr(render.ffmpeg_utils, "ensure_art_backdrop", lambda *a, **k: None)
    monkeypatch.setattr(render.ffmpeg_utils, "ensure_vignette", lambda *a, **k: None)
    monkeypatch.setattr(render.ffmpeg_utils, "render_video", sahte_render)
    monkeypatch.setattr(render.ffmpeg_utils, "ses_olc", sahte_olc)
    return str(tmp_path), kayit


def _platform(kayit, w):
    return [r for r in kayit["render"] if r["w"] == w][0]


def test_tp_esik_ustunde_iki_platform_da_limiter_aliyor(tmp_path, monkeypatch):
    proje, kayit = _proje(tmp_path, monkeypatch,
                          olcum={"lufs": -13.1, "tp": -0.5, "lra": 3.7})
    assert render.render_project(proje) is True
    assert len(kayit["render"]) == 2
    assert all(r.get("ses_limiter") is True for r in kayit["render"])


def test_tp_esik_altinda_limiter_yok(tmp_path, monkeypatch):
    proje, kayit = _proje(tmp_path, monkeypatch,
                          olcum={"lufs": -13.7, "tp": -2.3, "lra": 2.4})
    assert render.render_project(proje) is True
    assert all(r.get("ses_limiter") is False for r in kayit["render"])


def test_olcum_hatasinda_render_suruyor_ve_uyari_basiliyor(tmp_path, monkeypatch, capsys):
    uyarilar = []
    monkeypatch.setattr(render, "_ses_uyarisi", lambda anahtar, mesaj: uyarilar.append(mesaj))
    proje, kayit = _proje(tmp_path, monkeypatch,
                          olcum_hatasi=RuntimeError("ffmpeg ölçemedi"))
    assert render.render_project(proje) is True
    assert len(kayit["render"]) == 2
    assert all(r.get("ses_limiter") is False for r in kayit["render"])
    cikti = capsys.readouterr().out
    assert "UYARI" in cikti and "limiter" in cikti.lower()
    assert uyarilar and "UYARI" in uyarilar[0]
    # Başarısız ölçüm state'e YAZILMIYOR (sonraki render yeniden denesin).
    assert not os.path.isfile(os.path.join(proje, "state.json"))


def test_ffmpeg_hic_yoksa_da_render_suruyor(tmp_path, monkeypatch):
    monkeypatch.setattr(render, "_ses_uyarisi", lambda anahtar, mesaj: None)
    proje, kayit = _proje(tmp_path, monkeypatch, olcum_hatasi=FileNotFoundError("ffmpeg"))
    assert render.render_project(proje) is True
    assert all(r.get("ses_limiter") is False for r in kayit["render"])


def test_olcum_state_e_yaziliyor_mevcut_anahtarlar_korunuyor(tmp_path, monkeypatch):
    proje, kayit = _proje(tmp_path, monkeypatch,
                          state={"youtube_video_id": "abc", "yayin_beklet": True},
                          olcum={"lufs": -12.9, "tp": -0.7, "lra": 6.7})
    assert render.render_project(proje) is True
    with open(os.path.join(proje, "state.json"), encoding="utf-8") as f:
        durum = json.load(f)
    assert durum["youtube_video_id"] == "abc" and durum["yayin_beklet"] is True
    so = durum["ses_olcum"]
    assert (so["lufs"], so["tp"], so["lra"]) == (-12.9, -0.7, 6.7)
    assert so["olcum_at"]
    md5 = hashlib.md5(open(os.path.join(proje, "audio.wav"), "rb").read()).hexdigest()
    assert so["md5"] == md5


def test_state_json_yoksa_olusturulmuyor(tmp_path, monkeypatch):
    """Yeni projede ilk render yüklemeden ÖNCE koşuyor; tiktok/bluesky/facebook
    taramaları "state.json yok = hiç yüklenmemiş" varsayıyor. Render yalnız
    ölçüm için state.json yaratıp o varsayımı bozmamalı."""
    proje, kayit = _proje(tmp_path, monkeypatch,
                          olcum={"lufs": -13.1, "tp": -0.5, "lra": 3.7})
    assert render.render_project(proje) is True
    assert not os.path.isfile(os.path.join(proje, "state.json"))
    assert all(r.get("ses_limiter") is True for r in kayit["render"])


def test_ayni_md5_icin_olcum_tekrarlanmiyor_ses_degisince_tekrarlaniyor(tmp_path, monkeypatch):
    proje, kayit = _proje(tmp_path, monkeypatch, state={},
                          olcum={"lufs": -13.1, "tp": -0.5, "lra": 3.7})
    render.render_project(proje)
    render.render_project(proje)
    assert kayit["olcum_sayisi"] == 1
    # İkinci render da önbellekteki ölçümle limiter'ı UYGULUYOR.
    assert all(r.get("ses_limiter") is True for r in kayit["render"])

    (tmp_path / "audio.wav").write_bytes(b"RIFF1111WAVEdata-yeni-take")
    render.render_project(proje)
    assert kayit["olcum_sayisi"] == 2


def test_bozuk_state_ustune_yazilmiyor(tmp_path, monkeypatch):
    """Bozuk state.json HATA sınıfı (uyumluluk._durum). Ölçümü yazmak için onu
    `{}` sayıp üstüne yazmak `telif_araliklari` gibi kapıları SİLERDİ."""
    monkeypatch.setattr(render, "_ses_uyarisi", lambda anahtar, mesaj: None)
    proje, kayit = _proje(tmp_path, monkeypatch,
                          olcum={"lufs": -13.1, "tp": -0.5, "lra": 3.7})
    (tmp_path / "state.json").write_text("{bozuk", encoding="utf-8")
    assert render.render_project(proje) is True
    assert (tmp_path / "state.json").read_text(encoding="utf-8") == "{bozuk"
    # Ölçüm bu koşuda yine de KULLANILIYOR.
    assert all(r.get("ses_limiter") is True for r in kayit["render"])


# ---------------------------------------------------------------------------
# highlight_start
# ---------------------------------------------------------------------------

_OLCUM = {"lufs": -14.0, "tp": -3.0, "lra": 4.0}


def test_yalniz_highlight_start_varsa_kesit_oradan_45_sn(tmp_path, monkeypatch):
    proje, kayit = _proje(tmp_path, monkeypatch, olcum=_OLCUM,
                          meta={"title": "T", "theme": "pop", "highlight_start": 41.5})
    assert render.render_project(proje) is True
    assert kayit["highlight_sayisi"] == 0          # otomatik tespit ÇAĞRILMADI
    shorts = _platform(kayit, 1080)
    assert shorts["start_time"] == 41.5
    assert shorts["end_time"] == 41.5 + config.HIGHLIGHT_DURATION
    uzun = _platform(kayit, 1920)
    assert uzun["start_time"] is None and uzun["end_time"] is None


def test_highlight_yoksa_eski_otomatik_tespit(tmp_path, monkeypatch):
    proje, kayit = _proje(tmp_path, monkeypatch, olcum=_OLCUM, highlight=(12.0, 57.0))
    assert render.render_project(proje) is True
    assert kayit["highlight_sayisi"] == 1
    shorts = _platform(kayit, 1080)
    assert (shorts["start_time"], shorts["end_time"]) == (12.0, 57.0)


def test_iki_alan_birden_varsa_eskisi_gibi_aynen(tmp_path, monkeypatch):
    proje, kayit = _proje(tmp_path, monkeypatch, olcum=_OLCUM,
                          meta={"title": "T", "theme": "pop",
                                "highlight_start": 30, "highlight_end": 60})
    render.render_project(proje)
    assert kayit["highlight_sayisi"] == 0
    shorts = _platform(kayit, 1080)
    assert (shorts["start_time"], shorts["end_time"]) == (30, 60)


def test_yalniz_highlight_end_varsa_eskisi_gibi_otomatik(tmp_path, monkeypatch, capsys):
    proje, kayit = _proje(tmp_path, monkeypatch, olcum=_OLCUM, highlight=(5.0, 50.0),
                          meta={"title": "T", "theme": "pop", "highlight_end": 60})
    render.render_project(proje)
    assert kayit["highlight_sayisi"] == 1
    assert "UYARI" in capsys.readouterr().out


@pytest.mark.parametrize("deger", [-3, "kırk", True, None])
def test_gecersiz_highlight_start_otomatige_duser(tmp_path, monkeypatch, capsys, deger):
    meta = {"title": "T", "theme": "pop", "highlight_start": deger}
    proje, kayit = _proje(tmp_path, monkeypatch, olcum=_OLCUM, meta=meta)
    render.render_project(proje)
    assert kayit["highlight_sayisi"] == 1
    if deger is not None:
        assert "UYARI" in capsys.readouterr().out


def test_dj_kesitleri_highlight_start_tan_etkilenmiyor(tmp_path, monkeypatch):
    """dj_clips meta.json'daki highlight_start'ı OKUMUYOR: kendi enerji
    pencerelerini seçiyor ve en enerjilisini (ana Shorts'un eski penceresi)
    atmaya devam ediyor. Değişiklik yalnız render.render_project'te."""
    pencereler = [(500.0, 545.0), (150.0, 195.0), (900.0, 945.0)]
    monkeypatch.setattr(dj_clips, "find_highlights", lambda *a, **k: list(pencereler))

    def kur(ad, meta):
        d = tmp_path / ad
        (d / "output").mkdir(parents=True)
        (d / "audio.wav").write_bytes(b"")
        (d / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
        return str(d)

    duz = dj_clips.clip_uret(kur("A", {"title": "A", "theme": "dj"}), count=2, dry_run=True)
    isaretli = dj_clips.clip_uret(
        kur("B", {"title": "B", "theme": "dj", "highlight_start": 150.0}),
        count=2, dry_run=True)
    assert duz["pencereler"] == isaretli["pencereler"]
    assert [(p["bas"], p["son"]) for p in isaretli["pencereler"]] == [(150.0, 195.0),
                                                                       (900.0, 945.0)]
