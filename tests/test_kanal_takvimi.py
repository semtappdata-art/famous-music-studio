# -*- coding: utf-8 -*-
"""turev_takvimi — kanal geneli İNSAN EMEĞİ gönderileri (Söz Defteri / Kulis).

Kullanıcı kararları (2026-09-13, TikTok LIVE planı): haftada en fazla 2 insan emeği
gönderisi; şarkı kesiti tavanlarına SAYILMAZ; aynı gün şarkı kesitiyle çakışmaz; yeni
şarkı yayınının ±24 saatinde yok; golden-hour; projeye bağlı olmayan kayıt
`kanal_takvimi.json`'da. Ağa ÇIKMAZ, gerçek dosyalara YAZMAZ (her şey tmp_path).
"""

import datetime
import json
import os
import subprocess
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)
sys.path.insert(0, os.path.join(_REPO, "upload"))

import config                                             # noqa: E402
import uyumluluk                                          # noqa: E402
import turev_takvimi as TT                                # noqa: E402

TR = datetime.timezone(datetime.timedelta(hours=3))


def T(y, mo, d, h=0, mi=0):
    return datetime.datetime(y, mo, d, h, mi, tzinfo=TR).timestamp()


def iso(y, mo, d, h=0, mi=0):
    return datetime.datetime(y, mo, d, h, mi, tzinfo=TR).isoformat()


SS = {"youtube_video_id": "Ozn9", "youtube_uploaded_at": "2026-09-13T02:22:17",
      "youtube_publish_at": "2026-09-13T09:00:00Z"}          # T0 = 13 Eyl 12:00 TR


@pytest.fixture(autouse=True)
def agsiz(monkeypatch):
    import socket
    import notify

    def _yasak(*a, **k):
        raise AssertionError("kanal takvimi testi ağa/bildirime çıktı")

    monkeypatch.setattr(socket.socket, "connect", _yasak)
    for ad in ("send", "send_text", "send_photo"):
        monkeypatch.setattr(notify, ad, _yasak)


@pytest.fixture
def kok(tmp_path, monkeypatch):
    for ad in ("projects", "dj_sets"):
        (tmp_path / ad).mkdir()
    monkeypatch.setattr(uyumluluk, "KOKLER",
                        (str(tmp_path / "projects"), str(tmp_path / "dj_sets")))
    monkeypatch.setattr(uyumluluk, "kontrol", lambda proje, asama="render": ([], []))
    monkeypatch.setattr(TT, "DJ_KILIT_YOLU", str(tmp_path / "yok.lock"))
    monkeypatch.setattr(TT, "KANAL_TAKVIMI_YOLU", str(tmp_path / "kanal_takvimi.json"))
    return tmp_path


def _proje(kok, ad, st, meta=None, ses=True):
    p = kok / "projects" / ad
    p.mkdir(parents=True)
    (p / "state.json").write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
    (p / "meta.json").write_text(json.dumps(meta or {"title": ad, "theme": "pop"},
                                            ensure_ascii=False), encoding="utf-8")
    if ses:
        (p / "audio.wav").write_bytes(b"x")
    return str(p)


def _ekle(tur, an, baslik="Söz Defteri #1", simdi=None):
    return TT.kanal_plan(tur, an, baslik, simdi=simdi or T(2026, 9, 13, 8), uygula=True)


def _kanal(tk, kid):
    return next(o for o in tk["kanal_gonderileri"] if o["id"] == kid)


# --- Kayıt yeri ------------------------------------------------------------------

def test_kanal_kaydi_kokteki_dosyaya_yazilir_kuru_varsayilan_ezmez(kok):
    yol = TT.KANAL_TAKVIMI_YOLU
    r = TT.kanal_plan("soz_defteri", iso(2026, 9, 15, 20, 30), "Söz Defteri #1 — Sabah Senin",
                      ilgili_proje="Sabah Senin", simdi=T(2026, 9, 13, 8))
    assert not r["yazildi"] and not os.path.exists(yol)          # varsayılan KURU
    k = r["kayit"]
    assert k["id"] == "KNL-2026-09-15-soz_defteri" and k["platform"] == "tiktok"
    assert k["insan_emegi"] and k["kanal_geneli"] and k["elle"]
    assert k["sarki_kesiti_tavanina_sayilir"] is False and k["tempo_sayilir"] is False
    assert k["en_gec"] == iso(2026, 9, 17, 22)                    # hedef + 2 gün
    r = TT.kanal_plan("soz_defteri", iso(2026, 9, 15, 20, 30), "Söz Defteri #1 — Sabah Senin",
                      ilgili_proje="Sabah Senin", simdi=T(2026, 9, 13, 8), uygula=True)
    assert r["yazildi"]
    with open(yol, encoding="utf-8") as f:
        veri = json.load(f)
    assert [g["id"] for g in veri["gonderiler"]] == ["KNL-2026-09-15-soz_defteri"]
    veri["gonderiler"][0]["baslik"] = "elle değişti"
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False)
    r = _ekle("soz_defteri", iso(2026, 9, 15, 20, 30))
    assert not r["yazildi"] and "zaten var" in r["sebep"]
    with open(yol, encoding="utf-8") as f:
        assert json.load(f)["gonderiler"][0]["baslik"] == "elle değişti"
    # projelerin state.json'ına hiçbir şey yazılmaz
    assert not any(n.endswith("state.json") for n in os.listdir(str(kok)))


def test_en_gec_haftayi_asmaz_ve_proje_kulis_turu_aynen(kok):
    k = TT.kanal_plan("kulis", iso(2026, 9, 19, 13), "Kulis #1", simdi=T(2026, 9, 13, 8))["kayit"]
    assert k["en_gec"] == iso(2026, 9, 20, 22)                    # Pazar 22:00'de kesilir
    proje_kulis = next(x for x in TT.TUR_TANIMLARI["projects"] if x["tur"] == "kulis")
    assert proje_kulis["platform"] == "youtube"                   # mevcut tür değişmedi
    assert TT.KANAL_TUR_TANIMLARI["kulis"]["platform"] == "tiktok"
    assert "tiktok_live_duyuru" not in TT.KANAL_TUR_TANIMLARI
    assert all(x["tur"] != "tiktok_live_duyuru" for kk in TT.TUR_TANIMLARI.values() for x in kk)


def test_gercek_kanal_dosyasi_testte_okunmaz_yazilmaz(kok, monkeypatch):
    monkeypatch.setattr(TT, "KANAL_TAKVIMI_YOLU", TT.GERCEK_KANAL_TAKVIMI_YOLU)
    once = (open(TT.GERCEK_KANAL_TAKVIMI_YOLU, "rb").read()
            if os.path.exists(TT.GERCEK_KANAL_TAKVIMI_YOLU) else None)
    with pytest.raises(TT.TurevHatasi):
        _ekle("kulis", iso(2026, 12, 19, 13))
    tk = TT.takvim(gun=400, simdi=T(2026, 9, 13, 8), klasorler=[])
    assert tk["kanal_gonderileri"] == []
    sonra = (open(TT.GERCEK_KANAL_TAKVIMI_YOLU, "rb").read()
             if os.path.exists(TT.GERCEK_KANAL_TAKVIMI_YOLU) else None)
    assert once == sonra


def test_bozuk_kanal_dosyasi_fail_closed(kok):
    with open(TT.KANAL_TAKVIMI_YOLU, "w", encoding="utf-8") as f:
        f.write("{bozuk")
    with pytest.raises(TT.TurevHatasi):
        _ekle("kulis", iso(2026, 9, 19, 13))
    tk = TT.takvim(gun=7, simdi=T(2026, 9, 13, 8), klasorler=[])
    assert tk["kanal_takvimi_okunamadi"] is True and tk["kanal_gonderileri"] == []


# --- Kurallar ---------------------------------------------------------------------

def test_haftada_en_fazla_iki_ve_ayni_gun_iki_yok(kok):
    assert config.TUREV_INSAN_EMEGI_HAFTALIK_TAVAN == 2
    _ekle("soz_defteri", iso(2026, 9, 15, 20, 30))
    with pytest.raises(TT.TurevHatasi, match="aynı gün"):
        _ekle("kulis", iso(2026, 9, 15, 12, 30))
    _ekle("kulis", iso(2026, 9, 19, 13))
    with pytest.raises(TT.TurevHatasi, match="haftalık"):
        _ekle("soz_defteri", iso(2026, 9, 20, 19))
    _ekle("soz_defteri", iso(2026, 9, 22, 20, 30))                # sonraki hafta serbest
    TT.iptal("KNL-2026-09-19-kulis", sebep="test")
    _ekle("soz_defteri", iso(2026, 9, 20, 19))                    # iptal yer açar


def test_takvimde_ucuncu_elle_kayit_haftalik_tavana_takilir(kok):
    _ekle("soz_defteri", iso(2026, 9, 15, 20, 30))
    _ekle("kulis", iso(2026, 9, 19, 13))
    with open(TT.KANAL_TAKVIMI_YOLU, encoding="utf-8") as f:
        veri = json.load(f)
    fazla = dict(veri["gonderiler"][0], id="KNL-elle-fazla", hedef_an=iso(2026, 9, 20, 19),
                 en_gec=iso(2026, 9, 20, 22))                     # hedef sırasında 3. gelir
    veri["gonderiler"].append(fazla)
    with open(TT.KANAL_TAKVIMI_YOLU, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False)
    tk = TT.takvim(gun=8, simdi=T(2026, 9, 13, 8), klasorler=[])
    assert len(tk["kanal_gonderileri"]) == 2
    dusen = next(o for o in tk["dusenler"] if o["id"] == "KNL-elle-fazla")
    assert dusen["etkin"] == "iptal_cakisma"


def test_golden_hour_disi_reddedilir_elle_kayit_pencereye_kayar(kok):
    with pytest.raises(TT.TurevHatasi, match="golden"):
        _ekle("soz_defteri", iso(2026, 9, 15, 16))
    _ekle("kulis", iso(2026, 9, 19, 13))
    with open(TT.KANAL_TAKVIMI_YOLU, encoding="utf-8") as f:
        veri = json.load(f)
    veri["gonderiler"][0]["hedef_an"] = iso(2026, 9, 19, 15)
    with open(TT.KANAL_TAKVIMI_YOLU, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False)
    tk = TT.takvim(gun=8, simdi=T(2026, 9, 13, 8), klasorler=[])
    assert _kanal(tk, "KNL-2026-09-19-kulis")["an"] == iso(2026, 9, 19, 18)


def test_sarki_kesiti_tavanina_ve_gunluk_turev_tavanina_sayilmaz(kok):
    a = _proje(kok, "Sabah Senin", SS)
    TT.plan_uret(a, simdi=T(2026, 9, 13, 4), uygula=True)
    _ekle("soz_defteri", iso(2026, 9, 14, 20, 30), simdi=T(2026, 9, 13, 5))
    tk = TT.takvim(gun=7, simdi=T(2026, 9, 13, 5), klasorler=[a])
    top = next(o for o in tk["olaylar"] if o["tur"] == "topluluk_soz_anket")
    assert top["an"] == iso(2026, 9, 14, 12)                      # günlük türev tavanı dolu gün
    kanal = _kanal(tk, "KNL-2026-09-14-soz_defteri")
    assert kanal["an"] == iso(2026, 9, 14, 20, 30)                # yine de aynı gün yerleşir
    assert kanal["sarki_kesiti_tavanina_sayilir"] is False
    # tiktok_web ve hatırlatma yalnız `olaylar`ı okur: kanal gönderisi orada YOK
    assert all(o["kok"] != "kanal" for o in tk["olaylar"])
    assert tk["kurallar"]["insan_emegi_haftalik_tavan"] == 2


def test_tiktok_web_kurallari_kanal_gonderisini_tiktok_gonderisi_saymaz(kok):
    import tiktok_web
    a = _proje(kok, "Sabah Senin", SS)
    _ekle("soz_defteri", iso(2026, 9, 15, 20, 30))
    baglam = tiktok_web._baglam(T(2026, 9, 13, 8), klasorler=[a])
    assert all(o.get("kok") != "kanal" for o in baglam["turev"])


def test_ayni_gun_sarki_kesitiyle_cakismaz_tiktok_web_plani(kok):
    b = _proje(kok, "Beni Birakma", dict(SS, youtube_publish_at="2026-09-01T09:00:00Z",
                                         tiktok_web={"durum": "planlandi",
                                                     "planlanan_an": iso(2026, 9, 15, 12, 15)}))
    _ekle("soz_defteri", iso(2026, 9, 15, 20, 30))
    tk = TT.takvim(gun=8, simdi=T(2026, 9, 13, 8), klasorler=[b])
    assert _kanal(tk, "KNL-2026-09-15-soz_defteri")["an"] == iso(2026, 9, 16, 12)
    st = json.loads(open(os.path.join(b, "state.json"), encoding="utf-8").read())
    st["tiktok_web"]["durum"] = "iptal"
    open(os.path.join(b, "state.json"), "w", encoding="utf-8").write(json.dumps(st))
    tk = TT.takvim(gun=8, simdi=T(2026, 9, 13, 8), klasorler=[b])
    assert _kanal(tk, "KNL-2026-09-15-soz_defteri")["an"] == iso(2026, 9, 15, 20, 30)


def test_ayni_gun_sarki_kesitiyle_cakismaz_turev_kesiti(kok):
    a = _proje(kok, "Sabah Senin", SS)
    TT.plan_uret(a, simdi=T(2026, 9, 13, 4), uygula=True)
    once = TT.takvim(gun=14, simdi=T(2026, 9, 22, 10), klasorler=[a])
    kesit = next(o for o in once["olaylar"] if o["tur"] == "tiktok_ikinci_kesit")
    gun = datetime.datetime.fromisoformat(kesit["an"])
    r = _ekle("soz_defteri", iso(gun.year, gun.month, gun.day, 19), simdi=T(2026, 9, 22, 10))
    tk = TT.takvim(gun=14, simdi=T(2026, 9, 22, 10), klasorler=[a])
    assert next(o for o in tk["olaylar"] if o["tur"] == "tiktok_ikinci_kesit")["an"] == kesit["an"]
    an = datetime.datetime.fromisoformat(_kanal(tk, r["kayit"]["id"])["an"])
    assert an.date() == gun.date() + datetime.timedelta(days=1)   # kesit öncelikli: ertesi gün
    assert (an.hour, an.minute) == (12, 0)


def test_yeni_sarki_yayininin_24_saatinde_yok(kok):
    y = _proje(kok, "Yeni Sarki", {"youtube_video_id": "y",
                                   "youtube_publish_at": "2026-09-15T17:00:00Z"})  # 20:00 TR
    _ekle("soz_defteri", iso(2026, 9, 15, 20, 30))
    tk = TT.takvim(gun=8, simdi=T(2026, 9, 13, 8), klasorler=[y])
    assert _kanal(tk, "KNL-2026-09-15-soz_defteri")["an"] == iso(2026, 9, 17, 12)


def test_kaydirma_siniri_asilirsa_duser_state_yazilmaz(kok):
    y = _proje(kok, "Yeni Sarki", {"youtube_video_id": "y",
                                   "youtube_publish_at": "2026-09-19T18:00:00Z"})  # Cmt 21:00
    _ekle("kulis", iso(2026, 9, 19, 13))                          # en_gec Pazar 22:00
    once = open(TT.KANAL_TAKVIMI_YOLU, "rb").read()
    tk = TT.takvim(gun=8, simdi=T(2026, 9, 13, 8), klasorler=[y])
    assert tk["kanal_gonderileri"] == []
    assert next(o for o in tk["dusenler"] if o["id"] == "KNL-2026-09-19-kulis")["etkin"] \
        == "iptal_cakisma"
    assert open(TT.KANAL_TAKVIMI_YOLU, "rb").read() == once


# --- Görünürlük --------------------------------------------------------------------

def test_gunluk_rapor_satiri_ve_sirada_ne_kanali_gorur(kok):
    _ekle("soz_defteri", iso(2026, 9, 15, 20, 30), baslik="Söz Defteri #1 — Sabah Senin")
    satirlar = TT.bugun_yarin_satirlari(simdi=T(2026, 9, 14, 10), klasorler=[])
    assert len(satirlar) == 1 and "Söz Defteri #1 — Sabah Senin" in satirlar[0]
    assert "insan emeği" in satirlar[0] and "tiktok" in satirlar[0]
    assert TT.sirada_ne(simdi=T(2026, 9, 14, 10), klasorler=[])["id"] == \
        "KNL-2026-09-15-soz_defteri"


def test_hatirlatma_kanal_gonderisine_gitmez(kok, monkeypatch):
    monkeypatch.setattr(config, "TUREV_HATIRLATMA_AKTIF", True)
    _ekle("soz_defteri", iso(2026, 9, 15, 20, 30))
    giden = []
    r = TT.hatirlatma_sirasi(lambda *a: None, simdi=T(2026, 9, 15, 20, 45), klasorler=[],
                             gonder=lambda m: giden.append(m) or True)
    assert giden == [] and r["gonderilen"] is None


def test_cli_cp1254_kanal_plan_kuru_uygula_ve_takvim_json(kok):
    yol = str(kok / "cli_kanal.json")
    env = dict(os.environ, PYTHONIOENCODING="cp1254")
    betik = os.path.join(_REPO, "turev_takvimi.py")
    ortak = ["--kanal", "soz_defteri", "--hedef", "2026-09-15T20:30:00+03:00",
             "--baslik", "Söz Defteri #1 — Sabah Senin", "--ilgili-proje", "Sabah Senin",
             "--kanal-yolu", yol, "--simdi", "2026-09-13T08:00:00+03:00"]
    p = subprocess.run([sys.executable, betik, "plan"] + ortak, capture_output=True, env=env,
                       timeout=120)
    assert p.returncode == 0, p.stderr.decode("utf-8", "replace")
    assert "KURU" in p.stdout.decode("utf-8") and not os.path.exists(yol)
    p = subprocess.run([sys.executable, betik, "plan"] + ortak + ["--uygula"],
                       capture_output=True, env=env, timeout=120)
    assert p.returncode == 0, p.stderr.decode("utf-8", "replace")
    assert os.path.exists(yol)
    p = subprocess.run([sys.executable, betik, "takvim", "--gun", "8", "--json",
                        "--kok", str(kok / "projects"), "--kanal-yolu", yol,
                        "--simdi", "2026-09-13T08:00:00+03:00"],
                       capture_output=True, env=env, timeout=120)
    assert p.returncode == 0, p.stderr.decode("utf-8", "replace")
    veri = json.loads(p.stdout.decode("utf-8"))
    assert [o["tur"] for o in veri["kanal_gonderileri"]] == ["soz_defteri"]
    p = subprocess.run([sys.executable, betik, "plan"], capture_output=True, env=env, timeout=120)
    assert p.returncode == 2
