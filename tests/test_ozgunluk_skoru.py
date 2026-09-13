# -*- coding: utf-8 -*-
"""Özgünlük skoru (ozgunluk_skoru.py) — ölçüm aritmetiği ve sözleşmeler.

Ağa çıkmaz, gerçek katalog/defter/anlık görüntü dosyalarına YAZMAZ (tmp_path).
Görsel testleri ffmpeg yoksa atlanır.
"""

import json
import os
import shutil
import subprocess
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)
sys.path.insert(0, os.path.join(_REPO, "upload"))

import ozgunluk_skoru as OS  # noqa: E402

FFMPEG = shutil.which("ffmpeg")
ffmpeg_gerek = pytest.mark.skipif(not FFMPEG, reason="ffmpeg yok")


def _png(yol, filtre, boyut="320x180"):
    subprocess.run([FFMPEG, "-v", "error", "-y", "-f", "lavfi", "-i",
                    "color=c=0x303030:s=%s:d=1" % boyut, "-vf", filtre, "-frames:v", "1",
                    str(yol)], check=True)
    return str(yol)


# --- görsel ölçümler ---------------------------------------------------------

@ffmpeg_gerek
def test_phash_ayni_goruntu_0_farkli_goruntu_uzak(tmp_path):
    a = _png(tmp_path / "a.png", "drawbox=x=0:y=0:w=160:h=180:c=white:t=fill")
    b = _png(tmp_path / "b.png", "drawbox=x=0:y=0:w=160:h=180:c=white:t=fill")
    c = _png(tmp_path / "c.png", "drawbox=x=0:y=0:w=320:h=90:c=white:t=fill")
    assert OS.hamming(OS.phash(a), OS.phash(b)) == 0
    assert OS.hamming(OS.phash(a), OS.phash(c)) >= 14
    assert 0 <= OS.phash(a) < (1 << 63)


@ffmpeg_gerek
def test_bindirme_kutusu_ve_duzen_sinifi(tmp_path):
    art = _png(tmp_path / "art.png", "null")
    ust = _png(tmp_path / "ust.png", "drawbox=x=100:y=16:w=120:h=50:c=white:t=fill")
    alt_sol = _png(tmp_path / "altsol.png", "drawbox=x=10:y=130:w=90:h=40:c=white:t=fill")
    k = OS.bindirme_kutusu(ust, art)
    assert k is not None
    x0, y0, x1, y1 = k
    assert 45 <= x0 <= 55 and 105 <= x1 <= 115 and y0 <= 10 and 30 <= y1 <= 35
    assert OS.duzen_sinifi(k) == "orta-ust"
    assert OS.duzen_sinifi(OS.bindirme_kutusu(alt_sol, art)) == "sol-alt"
    assert OS.bindirme_kutusu(art, art) is None
    assert OS.duzen_sinifi(None) == "yok"
    assert OS.duzen_sinifi((0, 37, 159, 89)) == "genis-alt"


@ffmpeg_gerek
def test_karanlik_desature(tmp_path):
    koyu = _png(tmp_path / "koyu.png", "null")
    parlak = _png(tmp_path / "p.png", "drawbox=x=0:y=0:w=320:h=180:c=0xff8800:t=fill")
    assert OS.karanlik_desature(koyu) is True
    assert OS.karanlik_desature(parlak) is False


# --- metin ölçümleri ---------------------------------------------------------

def test_baslik_kalibi_siniflandirma():
    assert OS.baslik_kalibi("Yeraltı (Sözleri) | Türkçe Hip-Hop Şarkısı") == "K1"
    assert OS.baslik_kalibi("Yeraltı — Sözleri | Famous Music Studio") == "K2"
    assert OS.baslik_kalibi("Yeraltı (Sözleri) · şehrin altındaki ses") == "K3"
    assert OS.baslik_kalibi("Just Relax") == "diger"


def test_tekrar_orani():
    assert OS.tekrar_orani(["K1"] * 10) == 1.0
    assert OS.tekrar_orani(["K1", "K2", "K1", "K3"]) == 0.5
    assert OS.tekrar_orani([]) is None


def test_ortak_satir_orani_link_blogu_ayrica():
    a = "hook a\n\nA | Famous Music Studio\n\n📷 Instagram: https://x\nsoru a"
    b = "hook b\n\nB | Famous Music Studio\n\n📷 Instagram: https://x\nsoru b"
    # satırlar: 4 + 4 = 8; ortak yalnız link satırı (2 örnek) -> 2/8
    assert OS.ortak_satir_orani([a, b]) == pytest.approx(2 / 8)
    assert OS.ortak_satir_orani([a, b], link_haric=True) == pytest.approx(0.0)
    assert OS.ortak_satir_orani(["tek"]) is None


def test_stil_jaccard():
    ort, maks = OS.stil_jaccard([{"a", "b"}, {"a", "b"}, {"c"}])
    assert maks == 1.0 and ort == pytest.approx(1 / 3)
    assert OS.stil_jaccard([{"a"}]) == (None, None)


# --- bileşen aritmetiği ------------------------------------------------------

def test_insan_emegi_puani():
    assert OS.insan_emegi_puani(0, 93) == 0
    assert OS.insan_emegi_puani(1, 20) == pytest.approx(100 / 3)
    assert OS.insan_emegi_puani(5, 20) == 100
    assert OS.insan_emegi_puani(0, 0) is None


def test_ritim_puani():
    assert OS.ritim_puani(0) == 100
    assert OS.ritim_puani(2) == 60
    assert OS.ritim_puani(9) == 0


def test_toplam_agirliklar_ve_olculemedi():
    assert OS.toplam({"K": 5, "M": 27, "I": 0, "R": 0}) == round(0.3 * 5 + 0.25 * 27)
    assert OS.toplam({"K": 100, "M": 100, "I": 100, "R": 100}) == 100
    assert OS.toplam({"K": None, "M": 100, "I": 100, "R": 100}) is None


def test_kapak_ve_metin_puanlari():
    assert OS.kapak_puani(0.95) == pytest.approx(5)
    assert OS.metin_puani(0.47, 1.0) == pytest.approx(26.5)
    assert OS.metin_puani(None, 1.0) is None


# --- uçtan uca (sahte katalog, ffmpeg ve snippet sahte) ----------------------

def _proje(kok, ad, state, meta=None):
    d = kok / ad
    d.mkdir(parents=True)
    (d / "meta.json").write_text(json.dumps(meta or {"title": ad, "theme": "rock"}),
                                 encoding="utf-8")
    (d / "state.json").write_text(json.dumps(state), encoding="utf-8")
    return str(d)


def _sahte(monkeypatch):
    monkeypatch.setattr(OS, "_kapak_olcumu", lambda p: {"duzen": "orta-ust",
                                                         "phash": None, "karanlik": False})
    monkeypatch.setattr(OS, "_snippet", lambda meta: {
        "title": "%s (Sözleri) | Türkçe Rock Şarkısı" % meta["title"],
        "description": "hook %s\n\n%s | Famous Music Studio\n\n🌐 Website: https://w"
                       % (meta["title"], meta["title"])})


def test_hesapla_json_sozlesmesi_ve_kopya_haric(tmp_path, monkeypatch):
    _sahte(monkeypatch)
    kok = tmp_path / "projects"
    p1 = _proje(kok, "A", {"youtube_video_id": "a", "youtube_uploaded_at": "2026-09-10T12:00:00"})
    p2 = _proje(kok, "B", {"youtube_video_id": "b", "youtube_uploaded_at": "2026-09-12T20:00:00"})
    p3 = _proje(kok, "Kopya", {"youtube_video_id": "k", "kopya_notu": "x",
                               "youtube_uploaded_at": "2026-09-12T21:00:00"})
    kanal = tmp_path / "kanal.json"
    kanal.write_text(json.dumps({"gonderiler": []}), encoding="utf-8")
    simdi = OS.ts_oku("2026-09-13T10:00:00+03:00")
    v = OS.hesapla(simdi=simdi, klasorler=[p1, p2, p3], kanal_yolu=str(kanal),
                   defter_yolu=str(tmp_path / "defter.jsonl"))
    for alan in ("skor", "hafta", "bilesenler", "kirilim", "olculemedi", "hesaplandi_at"):
        assert alan in v
    assert set(v["bilesenler"]) == {"K", "M", "I", "R"}
    assert v["kirilim"]["son_yayinlar"] == ["B", "A"]          # kopya hariç, yeni önce
    assert v["kirilim"]["kapak"]["sablon_tekrar_orani"] == 1.0
    assert v["bilesenler"]["K"] == 0
    assert v["kirilim"]["metin"]["baslik_kalibi_tekrar_orani"] == 1.0
    json.dumps(v, ensure_ascii=False)                       # serileşebilir


def test_olculemedi_satiri_sessiz_degil(tmp_path, monkeypatch):
    _sahte(monkeypatch)

    def patla(meta):
        raise RuntimeError("snippet yok")
    monkeypatch.setattr(OS, "_snippet", patla)
    p1 = _proje(tmp_path / "projects", "A", {"youtube_video_id": "a",
                                             "youtube_uploaded_at": "2026-09-10T12:00:00"})
    v = OS.hesapla(simdi=OS.ts_oku("2026-09-13T10:00:00+03:00"), klasorler=[p1],
                   kanal_yolu=str(tmp_path / "yok.json"), defter_yolu=str(tmp_path / "d"))
    assert v["skor"] is None
    assert any(o.startswith("M") for o in v["olculemedi"])
    assert "ölçülemedi" in OS.ozet_satiri(v, None)


def test_insan_emegi_kanal_takvimi_ve_defter_tekrarsiz(tmp_path):
    kanal = tmp_path / "kanal.json"
    kanal.write_text(json.dumps({"gonderiler": [
        {"id": "KNL-2026-09-12-soz_defteri", "durum": "yayinlandi",
         "hedef_an": "2026-09-12T20:30:00+03:00", "yayin": {"an": "2026-09-12T20:31:00+03:00"}},
        {"id": "KNL-2026-09-19-kulis", "durum": "planlandi", "hedef_an": "2026-09-19T13:00:00+03:00"},
    ]}), encoding="utf-8")
    defter = tmp_path / "defter.jsonl"
    defter.write_text("\n".join(json.dumps(k, ensure_ascii=False) for k in [
        {"id": "EI-1", "zaman": "2026-09-12T20:35:00+03:00", "platform": "tiktok",
         "islem": "yayinladi", "kaynak": "cli", "ayrinti": "Söz Defteri #1 (KNL-2026-09-12-soz_defteri)"},
        {"id": "EI-2", "zaman": "2026-09-11T13:00:00+03:00", "platform": "youtube",
         "islem": "yayinladi", "kaynak": "cli", "ayrinti": "Topluluk gönderisi: kulis"},
        {"id": "EI-3", "zaman": "2026-09-11T13:00:00+03:00", "platform": "youtube",
         "islem": "gizlilik_degistirdi", "kaynak": "cli", "ayrinti": "x"},
    ]) + "\n", encoding="utf-8")
    simdi = OS.ts_oku("2026-09-13T10:00:00+03:00")
    sayi, kimlikler = OS.insan_emegi_gonderileri(simdi, str(kanal), str(defter))
    assert sayi == 2, kimlikler


def test_anlik_goruntu_gercek_dosyaya_testte_yazmaz(tmp_path):
    with pytest.raises(OS.OzgunlukHatasi):
        OS.anlik_kaydet("2026-W37", {"skor": 8}, yol=OS.GERCEK_OLCUM_YOLU)
    yol = tmp_path / "olcum.json"
    OS.anlik_kaydet("2026-W36", {"skor": 8}, yol=str(yol))
    OS.anlik_kaydet("2026-W37", {"skor": 12}, yol=str(yol))
    assert OS.onceki_skor("2026-W38", yol=str(yol)) == 12
    assert OS.onceki_skor("2026-W37", yol=str(yol)) == 8
    assert OS.onceki_skor("2026-W36", yol=str(yol)) is None


def test_ozet_satiri_bicimi():
    assert OS.ozet_satiri({"skor": 31}, 8) == "Özgünlük skoru: 31/100 (geçen hafta 8)"
    assert OS.ozet_satiri({"skor": 31}, None) == "Özgünlük skoru: 31/100 (geçen hafta: yok)"


def test_cli_json(tmp_path, monkeypatch, capsysbinary):
    monkeypatch.setattr(OS, "hesapla", lambda **k: {"skor": 8, "hafta": "2026-W37",
                                                    "bilesenler": {}, "kirilim": {},
                                                    "olculemedi": [], "hesaplandi_at": "x"})
    assert OS.main(["--json", "--simdi", "2026-09-13T10:00:00+03:00"]) == 0
    veri = json.loads(capsysbinary.readouterr().out.decode("utf-8"))
    assert veri["skor"] == 8


# --- weekly_report bağlantısı ------------------------------------------------

def test_weekly_report_satiri(monkeypatch, tmp_path):
    import weekly_report as W
    monkeypatch.setattr(OS, "hesapla", lambda **k: {"skor": 31, "hafta": k and "x"})
    monkeypatch.setattr(OS, "onceki_skor", lambda hafta, yol=None: 8)
    satir = W._ozgunluk_satiri(OS.ts_oku("2026-09-14T10:00:00+03:00"))
    assert satir == "Özgünlük skoru: 31/100 (geçen hafta 8)"

    def patla(**k):
        raise RuntimeError("katalog yok")
    monkeypatch.setattr(OS, "hesapla", patla)
    assert W._ozgunluk_satiri(0.0).startswith("Özgünlük skoru: ölçülemedi (")


def test_weekly_report_haftalik_satirlarda_cagriliyor():
    import ast
    agac = ast.parse(open(os.path.join(_REPO, "weekly_report.py"), encoding="utf-8").read())
    fn = next(n for n in agac.body if isinstance(n, ast.FunctionDef)
              and n.name == "_haftalik_satirlar")
    assert any(isinstance(n, ast.Call) and getattr(n.func, "id", None) == "_ozgunluk_satiri"
               for n in ast.walk(fn))
