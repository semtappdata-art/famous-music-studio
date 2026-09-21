# -*- coding: utf-8 -*-
"""`upload/youtube_kota.py` — YouTube Data API kota defteri ve koruması.

NEDEN VAR (2026-09-13): ortak 10.000 birimlik havuz gece bitti; harcamanın
nereye gittiği HİÇBİR yere yazılmamıştı (tek kayıtlı iz `ai_beyani_onar.log`).
Sonuç: Sabah Senin'in kapak ve playlist adımları 403 aldı.

AĞ SAHTE: gerçek `googleapiclient` istek nesneleri `HttpMockSequence` ile
koşuyor, statik keşif belgesiyle (`static_discovery=True`) — hiçbir istek
makineden çıkmıyor. Her test deftere GEÇİCİ bir yoldan (ortam değişkeni)
yazıyor; `tests/conftest.py`'nin `DURUM_DOSYASI` yönlendirmesi ikinci kat.
"""

import ast
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD = os.path.join(REPO, "upload")
for _p in (UPLOAD, REPO):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import youtube_kota as K  # noqa: E402

UTC = timezone.utc
GERCEK_DEFTER = os.path.join(REPO, "youtube_kota_defteri.jsonl")


@pytest.fixture
def defter(tmp_path, monkeypatch):
    yol = str(tmp_path / "defter.jsonl")
    monkeypatch.setenv(K.ORTAM_DEGISKENI, yol)
    return yol


def _utc(*a):
    return datetime(*a, tzinfo=UTC)


def _satir_yaz(yol, kayitlar):
    with open(yol, "a", encoding="utf-8") as f:
        for k in kayitlar:
            f.write(json.dumps(k, ensure_ascii=False) + "\n")


def _oku(yol):
    with open(yol, encoding="utf-8") as f:
        return [json.loads(s) for s in f if s.strip()]


# --------------------------------------------------------------------------
# 1) MALİYET TABLOSU
# --------------------------------------------------------------------------

def test_maliyet_resmi_tablo():
    assert K.maliyet("videos.update") == (50, False, "ortak")
    assert K.maliyet("thumbnails.set")[0] == 50
    assert K.maliyet("playlistItems.insert")[0] == 50
    assert K.maliyet("captions.insert")[0] == 400
    assert K.maliyet("captions.update")[0] == 450
    assert K.maliyet("captions.list")[0] == 50
    for m in ("videos.list", "channels.list", "commentThreads.list",
              "playlistItems.list", "playlists.list"):
        assert K.maliyet(m) == (1, False, "ortak"), m


def test_insert_ayri_kovada_ortak_havuzdan_yemez():
    assert K.maliyet("videos.insert") == (0, False, "insert")
    assert K.maliyet("youtube.videos.insert") == (0, False, "insert")


def test_captions_download_tahmin_olarak_isaretli():
    birim, tahmin, _ = K.maliyet("captions.download")
    assert birim == 200 and tahmin is True


def test_bilinmeyen_metod_tahmin():
    assert K.maliyet("videos.rate")[1] is True
    assert K.maliyet("foo.list") == (1, True, "ortak")


def test_bugunku_harcama_toplami(defter):
    simdi = _utc(2026, 9, 13, 12, 0)
    K.kaydet("videos.update", adet=2, kaynak="elle:x", simdi=simdi)
    K.kaydet("videos.list", simdi=simdi)
    K.kaydet("videos.insert", simdi=simdi)
    K.kaydet("captions.download", simdi=simdi)
    h = K.bugunku_harcama(simdi=simdi)
    assert h["ortak"] == 100 + 1 + 200
    assert h["insert"] == 1
    assert h["tahmin_iceren"] is True
    assert K.kalan(simdi=simdi) == 10000 - 301
    assert K.yeterli_mi(9699, simdi=simdi) is True
    assert K.yeterli_mi(9700, simdi=simdi) is False


def test_basarisiz_cagri_en_az_bir_birim(defter):
    """Resmî: 'Every API request, even if invalid, will cost at least one
    quota point.' Tam maliyet bilinmiyor -> 1 + tahmin."""
    simdi = _utc(2026, 9, 13, 12, 0)
    K.kaydet("captions.insert", basarili=False, simdi=simdi)
    h = K.bugunku_harcama(simdi=simdi)
    assert h["ortak"] == 1 and h["tahmin_iceren"] is True


# --------------------------------------------------------------------------
# 2) PASİFİK GÜNÜ
# --------------------------------------------------------------------------

@pytest.fixture(params=["yedek", "zoneinfo"])
def saat_dilimi(request, monkeypatch):
    if request.param == "yedek":
        monkeypatch.setattr(K, "_pasifik_tz", lambda: None)
    elif K._pasifik_tz() is None:
        pytest.skip("tzdata yok (bu Windows makinesi) — yedek hesap sınanıyor")
    return request.param


def test_pasifik_gunu_tr_0959_1001(defter, saat_dilimi):
    once = _utc(2026, 9, 13, 6, 59)   # TR 09:59
    sonra = _utc(2026, 9, 13, 7, 1)   # TR 10:01
    assert str(K.pasifik_gunu(once)) == "2026-09-12"
    assert str(K.pasifik_gunu(sonra)) == "2026-09-13"
    K.kaydet("videos.update", simdi=once)
    assert K.bugunku_harcama(simdi=once)["ortak"] == 50
    assert K.bugunku_harcama(simdi=sonra)["ortak"] == 0
    assert K.sifirlanma_ani(once) == _utc(2026, 9, 13, 7, 0)


def test_kasim_yaz_saati_gecisi(saat_dilimi):
    # 2026-11-01 PDT -> PST. Sıfırlanma TR 10:00'dan 11:00'e kayar.
    assert K.sifirlanma_ani(_utc(2026, 10, 31, 20, 0)) == _utc(2026, 11, 1, 7, 0)
    assert K.sifirlanma_ani(_utc(2026, 11, 1, 12, 0)) == _utc(2026, 11, 2, 8, 0)
    assert str(K.pasifik_gunu(_utc(2026, 11, 2, 7, 59))) == "2026-11-01"  # TR 10:59
    assert str(K.pasifik_gunu(_utc(2026, 11, 2, 8, 1))) == "2026-11-02"   # TR 11:01
    # Mart geçişi (ikinci pazar): 2027-03-14
    assert K.sifirlanma_ani(_utc(2027, 3, 14, 12, 0)) == _utc(2027, 3, 15, 7, 0)


def test_yedek_hesap_zoneinfo_ile_ayni():
    tz = K._pasifik_tz()
    if tz is None:
        pytest.skip("tzdata yok — karşılaştırma CI'da (Linux) koşar")
    t = _utc(2026, 1, 1)
    while t < _utc(2028, 1, 1):
        assert K._yedek_ofset(t) == t.astimezone(tz).utcoffset(), t
        t += timedelta(minutes=30)


# --------------------------------------------------------------------------
# 3) DEFTER HATASI ÇAĞRIYI DÜŞÜRMEZ + DÖNDÜRME
# --------------------------------------------------------------------------

def test_defter_yazilamazsa_kaydet_patlamaz(tmp_path, monkeypatch):
    klasor = tmp_path / "klasor_dosya_degil"
    klasor.mkdir()
    monkeypatch.setenv(K.ORTAM_DEGISKENI, str(klasor))
    assert K.kaydet("videos.update") is False
    assert K.bugunku_harcama()["ortak"] == 0
    assert "YouTube kota" in K.saglik_satiri()


def test_otuz_gunden_eski_satirlar_dondurulur(defter):
    simdi = _utc(2026, 9, 13, 12)
    _satir_yaz(defter, [
        {"ts": "2026-08-01T00:00:00+00:00", "metod": "videos.list", "birim": 1},
        {"ts": "2026-09-10T00:00:00+00:00", "metod": "videos.list", "birim": 1},
    ])
    K._DONDURULEN.clear()
    K.kaydet("videos.list", simdi=simdi)
    tsler = [k["ts"][:10] for k in _oku(defter)]
    assert "2026-08-01" not in tsler
    assert tsler[0] == "2026-09-10" and len(tsler) == 2


def test_bozuk_satir_okumayi_dusurmez(defter):
    simdi = _utc(2026, 9, 13, 12)
    with open(defter, "w", encoding="utf-8") as f:
        f.write("{yarim satir\n")
    K.kaydet("videos.update", simdi=simdi)
    assert K.bugunku_harcama(simdi=simdi)["ortak"] == 50


def test_gec_yuklenen_modul_bile_gercek_deftere_yazamaz(monkeypatch):
    """Üretimde yakalandı: conftest yönlendirmesi geç yüklenen modülü görmüyor;
    başka bir test paketi gerçek deftere `elle:pytest` satırları yazdı."""
    monkeypatch.delenv(K.ORTAM_DEGISKENI, raising=False)
    monkeypatch.delenv(K.STUDIO_ORTAM_DEGISKENI, raising=False)
    monkeypatch.setattr(K, "DURUM_DOSYASI", GERCEK_DEFTER)   # yönlendirme YOKMUŞ gibi
    assert os.environ.get("PYTEST_CURRENT_TEST")
    once = os.path.getsize(GERCEK_DEFTER) if os.path.exists(GERCEK_DEFTER) else None
    yol = K.defter_yolu()
    assert os.path.normcase(os.path.abspath(yol)) != os.path.normcase(GERCEK_DEFTER)
    assert os.path.dirname(os.path.abspath(K.studio_dosya_yolu())) != REPO
    assert K.kaydet("videos.list", kaynak="elle:pytest-koruma") is True
    sonra = os.path.getsize(GERCEK_DEFTER) if os.path.exists(GERCEK_DEFTER) else None
    assert once == sonra, "test GERÇEK deftere yazdı"


def test_testte_gercek_deftere_yazilmaz(defter):
    assert os.path.abspath(K.defter_yolu()) != os.path.abspath(GERCEK_DEFTER)
    # conftest ikinci kat: ortam değişkeni olmasa bile modül sabiti tmp'de.
    assert os.path.abspath(K.DURUM_DOSYASI) != os.path.abspath(GERCEK_DEFTER)


# --------------------------------------------------------------------------
# 4) MERKEZİ YAKALAMA — gerçek googleapiclient, sahte ağ
# --------------------------------------------------------------------------

def _servis(yanitlar):
    from googleapiclient.discovery import build
    from googleapiclient.http import HttpMockSequence
    return build("youtube", "v3", http=HttpMockSequence(yanitlar),
                 developerKey="sahte", static_discovery=True,
                 requestBuilder=K.KotaliHttpRequest)


KOTA_403 = json.dumps({"error": {"code": 403, "message": "quota", "errors": [
    {"message": "quota", "domain": "youtube.quota", "reason": "quotaExceeded"}]}})


def test_metod_adi_request_methodId_den_okunur(defter):
    yt = _servis([({"status": "200"}, '{"items": []}'),
                  ({"status": "200"}, '{"items": []}')])
    yt.videos().list(part="status", id="VID1").execute()
    yt.captions().list(part="snippet", videoId="VID2").execute()
    k = _oku(defter)
    assert [x["metod"] for x in k] == ["videos.list", "captions.list"]
    assert [x["hedef"] for x in k] == ["VID1", "VID2"]
    assert all(x["basarili"] for x in k)
    assert K.bugunku_harcama()["ortak"] == 51


def test_quota_exceeded_basarisiz_kaydedilir(defter):
    from googleapiclient.errors import HttpError
    yt = _servis([({"status": "403"}, KOTA_403)])
    with pytest.raises(HttpError):
        yt.commentThreads().list(part="snippet",
                                 allThreadsRelatedToChannelId="C").execute()
    (k,) = _oku(defter)
    assert k["metod"] == "commentThreads.list"
    assert k["basarili"] is False and k["hata"] == "quotaExceeded"


def test_list_next_de_yakalanir(defter):
    yt = _servis([({"status": "200"}, '{"items": [], "nextPageToken": "T"}'),
                  ({"status": "200"}, '{"items": []}')])
    req = yt.playlistItems().list(part="snippet", playlistId="PL", maxResults=50)
    r = req.execute()
    req2 = yt.playlistItems().list_next(req, r)
    assert isinstance(req2, K.KotaliHttpRequest)
    req2.execute()
    assert [x["metod"] for x in _oku(defter)] == ["playlistItems.list"] * 2


def test_devam_ettirilebilir_yukleme_bir_kez_sayilir(defter, tmp_path):
    from googleapiclient.http import MediaFileUpload
    dosya = tmp_path / "v.mp4"
    dosya.write_bytes(b"x" * 10)
    yt = _servis([({"status": "200", "location": "https://upload.example/u"}, ""),
                  ({"status": "200"}, '{"id": "YENI"}')])
    req = yt.videos().insert(part="snippet,status", body={"snippet": {}},
                             media_body=MediaFileUpload(str(dosya), resumable=True))
    yanit = None
    while yanit is None:
        _, yanit = req.next_chunk()
    k = _oku(defter)
    assert len(k) == 1 and k[0]["metod"] == "videos.insert"
    h = K.bugunku_harcama()
    assert h["insert"] == 1 and h["ortak"] == 0


def test_defter_bozukken_istek_yine_doner(tmp_path, monkeypatch):
    klasor = tmp_path / "d"
    klasor.mkdir()
    monkeypatch.setenv(K.ORTAM_DEGISKENI, str(klasor))
    yt = _servis([({"status": "200"}, '{"items": [{"id": "A"}]}')])
    assert yt.videos().list(part="id", id="A").execute()["items"][0]["id"] == "A"


def test_youtube_auth_kotali_istek_sinifini_kullanir(tmp_path, monkeypatch):
    import youtube_auth
    token = tmp_path / "token.json"
    token.write_text("{}", encoding="utf-8")

    class Kimlik:
        valid = True

    alinan = {}
    monkeypatch.setattr(youtube_auth, "TOKEN_PATH", str(token))
    monkeypatch.setattr(youtube_auth.Credentials, "from_authorized_user_file",
                        staticmethod(lambda *a, **k: Kimlik()))
    monkeypatch.setattr(youtube_auth, "build",
                        lambda *a, **k: alinan.update(k) or "servis")
    assert youtube_auth.get_authenticated_service() == "servis"
    assert alinan["requestBuilder"] is K.KotaliHttpRequest


def test_kaynak_tespiti(monkeypatch):
    import types
    ana = types.ModuleType("__main__")
    ana.__file__ = os.path.join(REPO, "auto_process.py")
    monkeypatch.setitem(sys.modules, "__main__", ana)
    monkeypatch.setattr(sys, "executable", r"C:\Python314\pythonw.exe")
    assert K.kaynak_tespit() == "auto_process"
    monkeypatch.setattr(sys, "executable", r"C:\Python314\python.exe")
    assert K.kaynak_tespit() == "elle:auto_process"
    ana.__file__ = os.path.join(UPLOAD, "ai_beyani_onar.py")
    monkeypatch.setattr(sys, "executable", r"C:\Python314\pythonw.exe")
    assert K.kaynak_tespit() == "elle:ai_beyani_onar"


# --------------------------------------------------------------------------
# 5) TOPLU ELLE İŞ KORUMASI (%60) + --zorla / --gunluk-sinir
# --------------------------------------------------------------------------

def _harca(birim):
    K.kaydet("captions.update", adet=birim // 450, kaynak="elle:test")
    kalan = birim % 450
    if kalan:
        K.kaydet("videos.list", adet=kalan, kaynak="elle:test")


def test_toplu_izin_esikte_durur(defter):
    _harca(5000)
    s = K.toplu_izin(51, 42)
    assert s["durdu"] is True and s["izin"] == (6000 - 5000) // 51
    assert "Bugün en fazla 19 öğe; kalanlar yarın" in s["mesaj"]


def test_toplu_izin_zorla_esigi_asar_ama_yayin_rezervini_asamaz(defter):
    _harca(5000)
    s = K.toplu_izin(51, 42, zorla=True)
    assert s["durdu"] is False and s["izin"] == 42
    s = K.toplu_izin(51, 200, zorla=True)
    assert s["durdu"] is True
    assert s["izin"] == (10000 - K.yayin_rezervi() - 5000) // 51


def test_toplu_izin_gunluk_sinir(defter):
    _harca(5000)
    s = K.toplu_izin(51, 42, gunluk_sinir=5)
    assert s["durdu"] is False and s["izin"] == 5


def test_yayin_rezervi_config_ten():
    import config
    assert K.yayin_rezervi() == config.YOUTUBE_KOTA_YAYIN_REZERVI == 950


def test_ai_beyani_onar_main_esikte_durur_zorla_gecer(defter, monkeypatch):
    import ai_beyani_onar as A
    _harca(5000)
    sahte = [{"proje": "p", "ad": "p", "etiket": "uzun", "video_id": "V%d" % i}
             for i in range(42)]
    monkeypatch.setattr(A, "hedef_videolar", lambda *a, **k: sahte)
    monkeypatch.setattr(A, "_durum_oku", lambda *a, **k: {})
    cagrilar = []
    monkeypatch.setattr(A, "onar", lambda **kw: cagrilar.append(kw) or {})

    assert A.main(["--uygula", "--limit", "42"]) == 3
    assert cagrilar == [], "eşik aşılınca API'ye hiç gidilmemeli"

    assert A.main(["--uygula", "--limit", "42", "--zorla"]) == 0
    assert cagrilar[-1]["limit"] == 42

    assert A.main(["--uygula", "--limit", "42", "--gunluk-sinir", "5"]) == 0
    assert cagrilar[-1]["limit"] == 5


def test_set_privacy_main_esikte_durur_zorla_gecer(defter, monkeypatch):
    import set_privacy as S
    _harca(5990)
    yazilan = []
    monkeypatch.setattr(S, "set_privacy", lambda v, p: yazilan.append((v, p)))
    idler = ["-CQ7MmUygTQ", "AAA", "BBB"]
    assert S.main(idler + ["unlisted"]) == 3
    assert yazilan == []
    assert S.main(idler + ["unlisted", "--zorla"]) == 0
    assert yazilan == [(v, "unlisted") for v in idler]


def test_set_privacy_tek_video_eski_kullanim(defter, monkeypatch):
    import set_privacy as S
    yazilan = []
    monkeypatch.setattr(S, "set_privacy", lambda v, p: yazilan.append((v, p)))
    assert S.main(["-CQ7MmUygTQ", "public"]) == 0
    assert yazilan == [("-CQ7MmUygTQ", "public")]


# --------------------------------------------------------------------------
# 6) SAATLİK HAT ENGELLENMEZ
# --------------------------------------------------------------------------

def test_saatlik_hat_kota_bitmisken_engellenmez(defter):
    _harca(10000)
    assert K.kalan() == 0
    yt = _servis([({"status": "200"}, '{"items": []}')])
    yt.thumbnails().set(videoId="V").execute()   # engellenmeden AĞA gider
    satir = K.saglik_satiri()
    assert satir.startswith("YouTube kota: bugün 10050/10000 (insert 0/100), sıfırlanma ")
    assert "UYARI" in satir


def _auto_process_son_try():
    kaynak = open(os.path.join(REPO, "auto_process.py"), encoding="utf-8").read()
    agac = ast.parse(kaynak)
    main = next(n for n in agac.body
                if isinstance(n, ast.FunctionDef) and n.name == "main")
    dis_try = next(n for n in main.body if isinstance(n, ast.Try) and n.finalbody)
    return kaynak, dis_try.finalbody[-1]


def test_auto_process_kosu_sonu_bagli():
    _, son = _auto_process_son_try()
    assert "kosu_sonu" in ast.unparse(son)


def test_auto_process_finally_sonunda_kendi_try_inda():
    kaynak, son = _auto_process_son_try()
    assert isinstance(son, ast.Try), "kota satırı finally'nin EN SONUNDA, kendi try'ında olmalı"
    metin = ast.unparse(son)
    assert "saglik_satiri" in metin or "kosu_sonu" in metin
    assert son.handlers, "kendi except'i olmalı"
    # Saatlik hat ENGELLEYİCİ bir kota fonksiyonu çağırmıyor.
    for yasak in ("toplu_izin", "yeterli_mi"):
        assert yasak not in kaynak, yasak


# --------------------------------------------------------------------------
# 7) CLI — cp1254 konsolda çökmez, --json ASCII
# --------------------------------------------------------------------------

def _cli(defter, *argv):
    ortam = dict(os.environ)
    ortam["PYTHONIOENCODING"] = "cp1254"
    ortam[K.ORTAM_DEGISKENI] = defter
    return subprocess.run([sys.executable, os.path.join(UPLOAD, "youtube_kota.py")] + list(argv),
                          capture_output=True, env=ortam, timeout=60)


def test_cli_cp1254_cokmez(defter):
    K.kaydet("videos.update", kaynak="elle:🎧→deneme")
    for argv in (["ozet"], ["son", "--adet", "5"], ["ozet", "--json"]):
        r = _cli(defter, *argv)
        assert r.returncode == 0, (argv, r.stderr.decode("utf-8", "replace"))
    veri = json.loads(r.stdout.decode("ascii"))
    assert veri["ortak"]["harcanan"] == 50
    assert veri["insert"]["limit"] == 100
    assert "elle:🎧→deneme" in veri["kaynaklar"]
    assert veri["metodlar"]["videos.update"]["birim"] == 50
    K.studio_bekleyen_ekle("Yeniden Doğacağım 🎧", "V1", "kapak", "uzun → kapak")
    for argv in (["studio-bekleyenler"], ["studio-bekleyenler", "--json"]):
        r2 = _cli(defter, *argv)
        assert r2.returncode == 0, (argv, r2.stderr.decode("utf-8", "replace"))
    assert json.loads(r2.stdout.decode("ascii"))[0]["video_id"] == "V1"


# --------------------------------------------------------------------------
# 8) STUDIO BEKLEYEN İŞLERİ — kota bitince yarım kalan, KENDİNİ DENEMEYEN adımlar
# --------------------------------------------------------------------------

@pytest.fixture
def proje_sahte(monkeypatch):
    monkeypatch.setattr(K, "_proje_bul",
                        lambda vid: ("Sabah Senin", "/sahte/Sabah Senin", vid.startswith("S")))


def test_quota_thumbnails_set_studio_isine_yazilir_tekrar_eklenmez(defter, proje_sahte):
    from googleapiclient.errors import HttpError
    for _ in range(2):
        yt = _servis([({"status": "403"}, KOTA_403)])
        with pytest.raises(HttpError):
            yt.thumbnails().set(videoId="V1").execute()
    (is_,) = K.studio_bekleyenler()
    assert is_["is_turu"] == "kapak" and is_["video_id"] == "V1"
    assert is_["proje"] == "Sabah Senin" and is_["dikey"] is False
    assert is_["id"].startswith("SB-")


def test_kendini_deneyen_adimlar_yazilmaz(defter, proje_sahte, monkeypatch):
    from googleapiclient.errors import HttpError
    monkeypatch.setattr(K, "kaynak_tespit", lambda: "auto_process")
    yt = _servis([({"status": "403"}, KOTA_403)] * 4)
    istekler = [
        # playlist: sync_project/ekle proje pending kaldıkça her koşuda yeniden dener
        yt.playlistItems().insert(part="snippet", body={"snippet": {"playlistId": "PL"}}),
        yt.captions().list(part="snippet", videoId="V1"),
        # saatlik hat: görünürlük planı / dj_tarama bir sonraki koşuda yeniden dener
        yt.videos().update(part="status", body={"id": "V1", "status": {"privacyStatus": "public"}}),
    ]
    for req in istekler:
        with pytest.raises(HttpError):
            req.execute()
    monkeypatch.setattr(K, "kaynak_tespit", lambda: "elle:ai_beyani_onar")
    with pytest.raises(HttpError):
        yt.videos().update(part="status", body={"id": "V1", "status": {}}).execute()
    assert K.studio_bekleyenler() == []


def test_elle_gizlilik_ve_aciklama_isi_yazilir(defter, proje_sahte, monkeypatch):
    from googleapiclient.errors import HttpError
    monkeypatch.setattr(K, "kaynak_tespit", lambda: "elle:set_privacy")
    yt = _servis([({"status": "403"}, KOTA_403)] * 2)
    with pytest.raises(HttpError):
        yt.videos().update(part="status", body={
            "id": "V9", "status": {"privacyStatus": "unlisted"}}).execute()
    with pytest.raises(HttpError):
        yt.videos().update(part="snippet", body={"id": "V9", "snippet": {}}).execute()
    isler = {i["is_turu"]: i for i in K.studio_bekleyenler()}
    assert set(isler) == {"gizlilik", "video_update"}
    assert "unlisted" in isler["gizlilik"]["ayrinti"]


GUN1 = _utc(2026, 9, 13, 6, 0)    # Pasifik 09-12 (TR 09:00)
GUN2 = _utc(2026, 9, 13, 8, 0)    # Pasifik 09-13 (TR 11:00)


def test_bildirim_gunde_tek_mesaj(defter):
    giden = []
    gonder = lambda baslik, metin: giden.append((baslik, metin)) or True
    K.studio_bekleyen_ekle("Sabah Senin", "V1", "kapak", "uzun format kapağı", simdi=GUN1)
    assert K.studio_bildirimi(simdi=GUN1, gonder=gonder) == "gonderildi"
    assert K.studio_bildirimi(simdi=GUN1 + timedelta(minutes=50), gonder=gonder) is None
    K.studio_bekleyen_ekle("Kader Ortakları", "V2", "kapak", "Shorts kapağı",
                           simdi=GUN1 + timedelta(minutes=55))
    assert K.studio_bildirimi(simdi=GUN1 + timedelta(minutes=58), gonder=gonder) is None
    assert len(giden) == 1
    _, metin = giden[0]
    assert metin.startswith("YouTube kotası bitti. Studio'dan tamamlanabilecek 1 iş:")
    assert "Sabah Senin — kapak" in metin
    assert "Studio işlerini Chrome'dan tamamla" in metin
    assert "Kota TR 10:00'da sıfırlanır" in metin
    # Ertesi Pasifik günü kota hatası YOKSA mesaj yok; yeniden görülürse tek mesaj.
    assert K.studio_bildirimi(simdi=GUN2, gonder=gonder) is None
    K.studio_bekleyen_ekle("Sabah Senin", "V1", "kapak", "uzun format kapağı", simdi=GUN2)
    assert K.studio_bildirimi(simdi=GUN2, gonder=gonder) == "gonderildi"
    assert len(giden) == 2


def test_bildirim_gonderilemezse_damgalanmaz(defter):
    K.studio_bekleyen_ekle("Sabah Senin", "V1", "kapak", "x", simdi=GUN1)
    assert K.studio_bildirimi(simdi=GUN1, gonder=lambda b, m: False) == "gonderilemedi"
    giden = []
    assert K.studio_bildirimi(simdi=GUN1, gonder=lambda b, m: giden.append(m) or True) == "gonderildi"
    assert len(giden) == 1


def test_bildirim_varsayilani_notify_send(defter, monkeypatch):
    import notify
    giden = []
    monkeypatch.setattr(notify, "send", lambda b, m: giden.append(m) or True)
    K.studio_bekleyen_ekle("Sabah Senin", "V1", "kapak", "x", simdi=GUN1)
    assert K.studio_bildirimi(simdi=GUN1) == "gonderildi" and len(giden) == 1


def test_tamamlama_ve_cli(defter, capsys):
    kimlik, yeni = K.studio_bekleyen_ekle("Sabah Senin", "V1", "kapak", "x", simdi=GUN1)
    assert yeni is True
    assert K.studio_bekleyen_ekle("Sabah Senin", "V1", "kapak", "x", simdi=GUN1) == (kimlik, False)
    assert K.main(["studio-tamamla", kimlik, "--kaynak", "claude"]) == 0
    cikti = capsys.readouterr().out
    assert 'elle_islem.py ekle --platform youtube --proje "Sabah Senin"' in cikti
    assert "--islem kapak_degistirdi" in cikti and "--kaynak claude" in cikti
    assert K.studio_bekleyenler() == []
    assert K.studio_bekleyen_tamamla(kimlik, "claude") is False
    assert K.studio_bekleyen_tamamla("SB-yok", "claude") is False
    with pytest.raises(ValueError):
        K.studio_bekleyen_ekle("p", "v", "altyazi", "x")


def _kapak_isleri(adet, simdi=GUN1):
    for i in range(adet):
        K.studio_bekleyen_ekle("P%d" % i, "V%d" % i, "kapak", "x",
                               proje_yol="/sahte/P%d" % i, dikey=False, simdi=simdi)


def test_kapak_telafisi_sifirlanmadan_once_denemez(defter):
    _kapak_isleri(2)
    cagri = []
    s = K.kapak_telafisi(simdi=GUN1 + timedelta(minutes=30), servis=object(),
                         yukle=lambda *a, **k: cagri.append(a))
    assert cagri == [] and s["denenen"] == 0


def test_kapak_telafisi_sifirlaninca_gunde_en_fazla_3(defter):
    _kapak_isleri(5)
    cagri = []
    yukle = lambda yt, vid, yol, vertical=False: cagri.append((vid, yol, vertical))
    s = K.kapak_telafisi(simdi=GUN2, servis=object(), yukle=yukle)
    assert s["denenen"] == 3 and s["tamamlanan"] == 3 and len(cagri) == 3
    assert cagri[0] == ("V0", "/sahte/P0", False)
    assert len(K.studio_bekleyenler()) == 2
    s = K.kapak_telafisi(simdi=GUN2 + timedelta(hours=1), servis=object(), yukle=yukle)
    assert s["denenen"] == 0 and len(cagri) == 3, "günlük 3 sınırı"
    s = K.kapak_telafisi(simdi=GUN2 + timedelta(days=1), servis=object(), yukle=yukle)
    assert s["tamamlanan"] == 2 and K.studio_bekleyenler() == []


def test_kapak_telafisi_kota_yetersizse_ve_hata_olursa(defter):
    _kapak_isleri(2)
    K.kaydet("captions.update", adet=23, simdi=GUN2)          # 10350 > 10000
    s = K.kapak_telafisi(simdi=GUN2, servis=object(), yukle=lambda *a, **k: None)
    assert s["denenen"] == 0 and "kota" in s["sebep"]
    gun3 = GUN2 + timedelta(days=1)

    def patla(*a, **k):
        raise RuntimeError("kapak dosyası yok")
    s = K.kapak_telafisi(simdi=gun3, servis=object(), yukle=patla)
    assert s["denenen"] == 2 and s["tamamlanan"] == 0
    assert len(K.studio_bekleyenler()) == 2, "başarısız iş KAPANMAZ"


def test_kosu_sonu_asla_patlamaz_ve_kota_satirini_yazar(defter, monkeypatch):
    def patla(*a, **k):
        raise RuntimeError("bozuk")
    monkeypatch.setattr(K, "kapak_telafisi", patla)
    monkeypatch.setattr(K, "studio_bildirimi", patla)
    satirlar = []
    K.kosu_sonu(log=satirlar.append)
    assert satirlar[-1].startswith("YouTube kota: bugün ")
