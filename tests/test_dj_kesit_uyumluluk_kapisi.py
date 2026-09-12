# -*- coding: utf-8 -*-
"""DJ kesit yayın hattının İKİ BAĞLANTI BOŞLUĞU (2026-09-12 denetimi).

Her ikisi de bu deponun en pahalı hata sınıfı: kod kendi içinde doğru, ama
hattın DIŞINDA (bkz. CLAUDE.md, "BAĞLANTI seviyesindeki sessiz arıza").

BOŞLUK 1 — POLİTİKA KAPISI KESİT YOLUNU KAPSAMIYORDU.
    `uyumluluk.kontrol(..., "yukleme")` `dj_famous_process.process_set` içinde
    çağrılıyor. Kesit yayını ise `main()`'in `finally` bloğundan koşuyor
    (`_kesit_yayini` -> `dj_clips.supur` -> `kesit_yayinla` ->
    `youtube_upload.upload_clip`) ve o çağrıya HİÇ uğramıyor. Yani telif
    eşleşmesi işaretli / aynı md5'i taşıyan / `ai_beyani=False` yazılmış bir
    setin KESİDİ hiçbir kontrolden geçmeden yayınlanabilirdi. Birebir aynısı
    aynı gün `upload/tiktok_publish_plan.py`'de bulunup düzeltildi — o yolda
    kapatıldı, bu yolda açık kalmıştı.

    FAIL-CLOSED şart: `uyumluluk.KOKLER` göreli yolken kapı kendiliğinden
    AÇILIYORDU (`os.path.isdir` False -> `hata=0`). Kapının ÇÖKMESİ "temiz"
    anlamına gelemez.

BOŞLUK 2 — KESİT HİÇBİR PLAYLIST'E GİRMİYORDU.
    `upload/youtube_playlists.py` `youtube_clip_video_id`'yi bilmiyordu ve
    `kesit_yayinla` `sync_project`i hiç çağırmıyordu. CLAUDE.md'deki 20
    Shorts vakasının aynısı — ve oradaki ders şu: çağrının VARLIĞI değil
    SIRASI kritik. `sync_project` planını `state.json`'dan türetiyor; kimlik
    yazılmadan önce çağrılırsa SESSİZCE hiçbir şey yapmaz. Bu yüzden aşağıda
    sıra hem `ast` ile hem davranışsal olarak doğrulanıyor.

AĞA HİÇ ÇIKILMIYOR: `upload_clip` ve playlist senkronu tamamen monkeypatch.
"""

import ast
import io
import json
import os
import sys
import time

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "upload"))

import dj_clips
import uyumluluk
import youtube_upload


META = {"title": "Sim Set", "theme": "dj"}


def _hazir_set(tmp_path, ad="Sim Set", state_ek=None, kesitler=("clip_01.mp4",)):
    """Kesit yayınına HER AÇIDAN hazır bir set (uyumluluk dışında)."""
    d = os.path.join(str(tmp_path), ad)
    os.makedirs(os.path.join(d, "output"))
    with io.open(os.path.join(d, "meta.json"), "w", encoding="utf-8") as f:
        f.write(json.dumps(META, ensure_ascii=False))
    st = {
        "youtube_video_id": "TAMSET",
        "youtube_shorts_video_id": "SHORT1",
        "youtube_shorts_uploaded_at": time.strftime(
            "%Y-%m-%dT%H:%M:%S",
            time.localtime(time.time() - dj_clips.KESIT_MIN_ARA_SN - 3600)),
        "dj_tarama_temiz": True,
        "dj_clips": [{"dosya": n, "bas": 100.0 * i, "son": 100.0 * i + 45.0,
                      "enerji": i}
                     for i, n in enumerate(kesitler, 1)],
    }
    st.update(state_ek or {})
    with io.open(os.path.join(d, "state.json"), "w", encoding="utf-8") as f:
        f.write(json.dumps(st, ensure_ascii=False))
    for n in kesitler:
        with open(os.path.join(d, "output", n), "wb") as f:
            f.write(b"x")
    return d


@pytest.fixture(autouse=True)
def _sessiz_uyari(monkeypatch):
    """`_kapi_uyar` satırları toplanıyor: "atlama SESSİZ olmasın" garantisi
    test edilebilir olsun, ama gerçek log dosyasına/stderr'e gitmesin."""
    satirlar = []
    monkeypatch.setattr(dj_clips, "_kapi_uyar",
                        lambda anahtar, mesaj: satirlar.append((anahtar, mesaj)))
    return satirlar


@pytest.fixture
def uyari_satirlari(_sessiz_uyari):
    return _sessiz_uyari


@pytest.fixture
def sahte_upload(monkeypatch):
    """Gerçek yükleyici yerine kayıt tutan bir sahte (ağ/token YOK)."""
    cagri = []

    def sahte(project_dir, clip_name, full_video_id=None, bas_sn=0.0,
              gun_ertele=0, privacy="public"):
        cagri.append(dict(project_dir=project_dir, clip_name=clip_name))
        return "YENIVID", "2026-09-15T15:00:00Z"

    monkeypatch.setattr(youtube_upload, "upload_clip", sahte)
    return cagri


@pytest.fixture
def sahte_playlist(monkeypatch):
    """`_playlist_senkronu` çağrıldığı ANDAKİ state.json fotoğrafını saklar.

    Sıra testinin davranışsal yarısı bu: kimlik state'e yazılmadan önce
    çağrılsaydı fotoğrafta `youtube_clip_video_id` OLMAZDI — ve gerçek
    `sync_project` de tam o sebeple sessizce hiçbir şey yapmazdı.
    """
    fotograflar = []

    def sahte(set_dir, log=print):
        yol = os.path.join(set_dir, "state.json")
        with io.open(yol, encoding="utf-8") as f:
            fotograflar.append(json.load(f))

    monkeypatch.setattr(dj_clips, "_playlist_senkronu", sahte)
    return fotograflar


# ===========================================================================
# BOŞLUK 1 — politika kapısı
# ===========================================================================


def test_a_uyumluluk_HATA_veren_set_kesit_yayinlamiyor(tmp_path, monkeypatch,
                                                       sahte_upload, uyari_satirlari):
    """(a) HATA -> o kesit yayınlanmaz, ve sebep operatöre GÖRÜNÜR."""
    _hazir_set(tmp_path)
    monkeypatch.setattr(uyumluluk, "kontrol",
                        lambda proje, asama="render": (["telif eşleşmesi kayıtlı (X)"], []))

    sonuc = dj_clips.supur(str(tmp_path), log=lambda *a: None)

    assert sonuc["yayinlanan"] == 0
    assert sahte_upload == [], "uyumluluk HATA verirken YouTube'a gidildi"
    assert any("uyumluluk" in a["sebep"].lower() for a in sonuc["atlanan"])
    assert any("telif" in m for _k, m in uyari_satirlari), \
        "atlama SESSİZ — log satırı bırakılmamış"


def test_a_telif_araliklari_gercek_state_ile_de_bloklaniyor(tmp_path, sahte_upload):
    """Aynı kapı MONKEYPATCH'SİZ, gerçek `uyumluluk.kontrol` ile de tutmalı:
    `telif_araliklari` kayıtlı bir set (City Pulse'un gerçek şekli)."""
    _hazir_set(tmp_path, state_ek={"telif_eser": "Bring Me To Life",
                                   "telif_araliklari": [[10.0, 20.0]]})
    sonuc = dj_clips.supur(str(tmp_path), log=lambda *a: None)
    assert sonuc["yayinlanan"] == 0 and sahte_upload == []


def test_b_temiz_set_normal_akiyor(tmp_path, monkeypatch, sahte_upload,
                                   sahte_playlist):
    """(b) Kapı temizse hat DEĞİŞMEDEN akıyor — kapı bir kilit değil, bir
    süzgeç. (Regresyon: fail-closed'ı fazla geniş yazıp her şeyi durdurmak.)"""
    _hazir_set(tmp_path)
    monkeypatch.setattr(uyumluluk, "kontrol", lambda proje, asama="render": ([], []))

    sonuc = dj_clips.supur(str(tmp_path), log=lambda *a: None)

    assert sonuc["yayinlanan"] == 1
    assert len(sahte_upload) == 1 and sahte_upload[0]["clip_name"] == "clip_01.mp4"


def test_b_uyari_yayini_DURDURMUYOR_ama_loglaniyor(tmp_path, monkeypatch,
                                                   sahte_upload, sahte_playlist,
                                                   uyari_satirlari):
    """`uyumluluk`'un genel kuralı: HATA = devam edilmez, uyarı = loglanır."""
    _hazir_set(tmp_path)
    monkeypatch.setattr(
        uyumluluk, "kontrol",
        lambda proje, asama="render": ([], ["bugün zaten 3 yükleme yapıldı"]))

    sonuc = dj_clips.supur(str(tmp_path), log=lambda *a: None)

    assert sonuc["yayinlanan"] == 1 and len(sahte_upload) == 1
    assert any("3 yükleme" in m for _k, m in uyari_satirlari)


def test_c_kontrol_istisna_firlatirsa_FAIL_CLOSED(tmp_path, monkeypatch,
                                                  sahte_upload, uyari_satirlari):
    """(c) Kapı çökerse kesit YAYINLANMAZ.

    Bu depoda fail-open'ın bedeli ödendi: `uyumluluk.KOKLER` göreli yolken
    `kontrol()` `hata=0` diyordu ve kapı kendiliğinden açılıyordu. "Bilmiyorum"
    ile "temiz" aynı şey değil."""
    _hazir_set(tmp_path)

    def patla(proje, asama="render"):
        raise RuntimeError("KOKLER okunamadı")

    monkeypatch.setattr(uyumluluk, "kontrol", patla)

    sonuc = dj_clips.supur(str(tmp_path), log=lambda *a: None)

    assert sonuc["yayinlanan"] == 0
    assert sahte_upload == []
    assert any("fail-closed" in a["sebep"] for a in sonuc["atlanan"])
    assert any("ÇÖKTÜ" in m for _k, m in uyari_satirlari)


def test_c_kuru_kosu_da_kapiya_TABI(tmp_path, monkeypatch):
    """`--yayin-kuru` operatöre "ne yayınlanabilirdi" diyor; kapıyı atlarsa
    yanlış bir söz verir."""
    _hazir_set(tmp_path)
    monkeypatch.setattr(uyumluluk, "kontrol",
                        lambda proje, asama="render": (["ai_beyani=False"], []))
    sonuc = dj_clips.supur(str(tmp_path), log=lambda *a: None, dry_run=True)
    assert sonuc["yayinlanan"] == 0 and "kuru" not in sonuc


def test_c_kesit_yayinla_DOGRUDAN_cagrilsa_da_kapi_var(tmp_path, monkeypatch,
                                                       sahte_upload):
    """İkinci kemer: `kesit_yayinla` dışarıya açık bir giriş noktası ve
    `yayina_uygun_mu`'dan geçmek ZORUNDA değil. Sessiz `return` değil `raise`:
    sessiz atlama, çağıranın "yayınlandı" sanmasına yol açardı."""
    set_dir = _hazir_set(tmp_path)
    kesit = {"dosya": "clip_01.mp4", "bas": 100.0, "son": 145.0, "enerji": 1}
    monkeypatch.setattr(uyumluluk, "kontrol",
                        lambda proje, asama="render": (["telif eşleşmesi kayıtlı"], []))

    with pytest.raises(RuntimeError) as e:
        dj_clips.kesit_yayinla(set_dir, kesit, log=lambda *a: None)

    assert "uyumluluk" in str(e.value)
    assert sahte_upload == []
    st = json.load(io.open(os.path.join(set_dir, "state.json"), encoding="utf-8"))
    assert "youtube_clip_video_id" not in st


def test_kapi_yukleme_asamasiyla_cagriliyor(tmp_path, monkeypatch, sahte_upload,
                                            sahte_playlist):
    """Aşama "render" değil "yukleme" olmalı: günlük yığılma kontrolü
    (`GUNLUK_YUKLEME_UYARI`) SADECE yükleme aşamasında çalışıyor."""
    _hazir_set(tmp_path)
    asamalar = []

    def izle(proje, asama="render"):
        asamalar.append(asama)
        return [], []

    monkeypatch.setattr(uyumluluk, "kontrol", izle)
    dj_clips.supur(str(tmp_path), log=lambda *a: None)

    assert asamalar and set(asamalar) == {"yukleme"}


def test_kapi_ucuz_kapilardan_SONRA_kosuyor(tmp_path, monkeypatch):
    """Sıra: `uyumluluk.kontrol` diskteki TÜM kökleri geziyor. Süpürge her
    koşuda her sete bakıyor — kapı başa konsaydı hazır olmayan setler için de
    boşuna koşardı. Üstelik "üretilmiş kesit yok" gibi somut sebepler
    uyumluluk mesajının altında kaybolurdu (gerçek vaka: City Pulse Set)."""
    d = os.path.join(str(tmp_path), "Kesitsiz Set")
    os.makedirs(os.path.join(d, "output"))
    with io.open(os.path.join(d, "meta.json"), "w", encoding="utf-8") as f:
        f.write(json.dumps(META, ensure_ascii=False))
    with io.open(os.path.join(d, "state.json"), "w", encoding="utf-8") as f:
        f.write(json.dumps({"telif_araliklari": [[1, 2]]}))

    cagri = []
    monkeypatch.setattr(uyumluluk, "kontrol",
                        lambda proje, asama="render": (cagri.append(proje), ([], []))[1])

    kesit, sebep = dj_clips.yayina_uygun_mu(d)
    assert kesit is None and sebep == "üretilmiş kesit yok"
    assert cagri == [], "uyumluluk kapısı gereksiz yere çalıştı"


def test_f_dj_tarama_temiz_yoksa_hicbir_sey_yayinlanmiyor(tmp_path, monkeypatch,
                                                          sahte_upload):
    """(f) `Just Relax` seti Content ID karantina kapısından ÖNCE yayınlandı,
    `dj_tarama_temiz` işareti state'inde YOK. Bu işaret ELLE konur (operatör
    Studio'da telif sekmesine bakar) — kod onu ASLA kendiliğinden yazmamalı."""
    import config
    monkeypatch.setattr(config, "DJ_ON_TARAMA", True)
    set_dir = _hazir_set(tmp_path)
    st = json.load(io.open(os.path.join(set_dir, "state.json"), encoding="utf-8"))
    st.pop("dj_tarama_temiz")
    with io.open(os.path.join(set_dir, "state.json"), "w", encoding="utf-8") as f:
        f.write(json.dumps(st, ensure_ascii=False))

    sonuc = dj_clips.supur(str(tmp_path), log=lambda *a: None)

    assert sonuc["yayinlanan"] == 0 and sahte_upload == []
    assert any("tarama" in a["sebep"].lower() for a in sonuc["atlanan"])
    # Kod işareti KENDİ KOYMADI.
    yeni = json.load(io.open(os.path.join(set_dir, "state.json"), encoding="utf-8"))
    assert "dj_tarama_temiz" not in yeni


# ===========================================================================
# BOŞLUK 2 — playlist senkronu (SIRA)
# ===========================================================================


def _cagri_satirlari(fonksiyon_adi, isimler, dosya="dj_clips.py"):
    """`<dosya>.<fonksiyon>` içindeki verilen çağrıların satır numaraları."""
    agac = ast.parse(io.open(os.path.join(REPO, dosya), encoding="utf-8").read())
    fn = next(d for d in ast.walk(agac)
              if isinstance(d, ast.FunctionDef) and d.name == fonksiyon_adi)
    bulunan = {ad: [] for ad in isimler}
    for d in ast.walk(fn):
        if isinstance(d, ast.Call) and isinstance(d.func, ast.Name) \
                and d.func.id in bulunan:
            bulunan[d.func.id].append(d.lineno)
    return bulunan


def test_d_playlist_senkronu_state_YAZILDIKTAN_SONRA_cagriliyor_ast():
    """CLAUDE.md'nin Shorts dersi: çağrının VARLIĞI değil SIRASI.

    `sync_project` planını `state.json`'dan türetiyor; `youtube_clip_video_id`
    yazılmadan önce çağrılırsa SESSİZCE hiçbir şey yapmaz — ve süpürge o seti
    bir daha hiç seçmediği için (set başına EN FAZLA BİR kesit) bir daha
    denenmez. 20 Shorts'un hiçbirinin playlist'e girmemesinin sebebi tam olarak
    buydu."""
    s = _cagri_satirlari("kesit_yayinla", ("_durum_yaz", "_playlist_senkronu"))
    assert s["_durum_yaz"], "kesit_yayinla state'e yazmıyor"
    assert s["_playlist_senkronu"], \
        "kesit_yayinla playlist senkronunu HİÇ çağırmıyor (Boşluk 2 geri geldi)"
    assert min(s["_playlist_senkronu"]) > max(s["_durum_yaz"]), (
        "playlist senkronu state yazımından ÖNCE çağrılıyor — o an "
        "youtube_clip_video_id state'te yok, kesit hiçbir listeye girmez")


def test_d_playlist_senkronu_kimligi_DISKTE_goruyor(tmp_path, sahte_upload,
                                                    sahte_playlist, monkeypatch):
    """Sıranın davranışsal yarısı: senkron çağrıldığı anda kimlik DİSKTE."""
    monkeypatch.setattr(uyumluluk, "kontrol", lambda proje, asama="render": ([], []))
    set_dir = _hazir_set(tmp_path)
    dj_clips.kesit_yayinla(set_dir, dj_clips.kesit_sec(set_dir),
                           log=lambda *a: None)

    assert len(sahte_playlist) == 1, "playlist senkronu çağrılmadı"
    assert sahte_playlist[0]["youtube_clip_video_id"] == "YENIVID"
    assert sahte_playlist[0]["youtube_clip_dosya"] == "clip_01.mp4"


def test_d_playlist_hatasi_yayini_geri_ALMIYOR(tmp_path, monkeypatch, sahte_upload):
    """Video bu noktada zaten YouTube'da ve state'e yazılmış; playlist hatası
    (kota/ağ/token) yüklemeyi geri almaz — ama SESSİZ de değil."""
    monkeypatch.setattr(uyumluluk, "kontrol", lambda proje, asama="render": ([], []))
    set_dir = _hazir_set(tmp_path)

    def patlayan_sync(youtube, project_dir, dry_run=False):
        raise RuntimeError("quotaExceeded")

    sahte_modul = type(sys)("youtube_playlists")
    sahte_modul.sync_project = patlayan_sync
    sahte_modul.get_authenticated_service = lambda: object()
    monkeypatch.setitem(sys.modules, "youtube_playlists", sahte_modul)

    loglar = []
    vid = dj_clips.kesit_yayinla(set_dir, dj_clips.kesit_sec(set_dir),
                                 log=loglar.append)

    assert vid == "YENIVID"
    st = json.load(io.open(os.path.join(set_dir, "state.json"), encoding="utf-8"))
    assert st["youtube_clip_video_id"] == "YENIVID"
    assert any("playlist" in l.lower() for l in loglar)


def test_d_kesit_shorts_rafina_giriyor(tmp_path):
    """Kesidin gireceği liste: `_shorts`.

    KARAR GEREKÇESİ (bkz. `beklenen_anahtarlar` yorumu): `_shorts`'un uzun
    format zincirinden ayrılma gerekçesi "her Short AYNI şarkının kesiti" —
    bu kural DJ kesidi için GEÇERLİ DEĞİL, çünkü `clip_uret` setin kendi
    Shorts'unun penceresini (en yüksek enerjili) bilerek ATIYOR ve pencereler
    arasında en az 60 sn boşluk zorunlu. Kesit, setin BAŞKA bir anı."""
    import youtube_playlists as YP
    d = _hazir_set(tmp_path)
    st = json.load(io.open(os.path.join(d, "state.json"), encoding="utf-8"))
    st.update({"youtube_clip_video_id": "KESIT1",
               "youtube_clip_privacy": "public",
               "youtube_clip_publish_at": "2026-09-15T15:00:00Z"})

    plan = YP.beklenen_anahtarlar(d, st, META)

    assert plan["KESIT1"] == [YP.SHORTS_ANAHTARI]
    # Setin kendi Shorts'u ve kesidi AYRI iki kayıt (biri diğerini ezmiyor).
    assert plan["SHORT1"] == [YP.SHORTS_ANAHTARI]
    # Uzun format zinciri dj_sets'e KAPALI kalmalı (regresyon).
    assert YP.ZINCIR_ANAHTARI not in plan.get("TAMSET", [])


def test_d_kesit_yoksa_plan_DEGISMIYOR(tmp_path):
    """Kesidi olmayan (kataloğun tamamı) projeler için hiçbir şey değişmedi."""
    import youtube_playlists as YP
    d = _hazir_set(tmp_path)
    st = json.load(io.open(os.path.join(d, "state.json"), encoding="utf-8"))
    plan = YP.beklenen_anahtarlar(d, st, META)
    assert set(plan) == {"TAMSET", "SHORT1"}


def test_d_durum_raporu_kesitleri_de_sayiyor():
    """"Çalışmadığını nasıl anlarız?" — `--durum` raporu kesit satırını da
    okumalı, yoksa senkron hiç çalışmasa bile "toplam eksik: 0" derdi."""
    import youtube_playlists as YP
    kaynak = io.open(os.path.join(REPO, "upload", "youtube_playlists.py"),
                     encoding="utf-8").read()
    fn = next(d for d in ast.walk(ast.parse(kaynak))
              if isinstance(d, ast.FunctionDef) and d.name == "durum")
    metinler = {n.value for n in ast.walk(fn) if isinstance(n, ast.Constant)
                and isinstance(n.value, str)}
    assert "youtube_clip_video_id" in metinler
    assert hasattr(YP, "beklenen_anahtarlar")


# ===========================================================================
# (e) SET BAŞINA TEK KESİT — sınır DEĞİŞMEDİ
# ===========================================================================


def test_e_set_basina_tek_kesit_sinirlari_duruyor(tmp_path, monkeypatch,
                                                  sahte_upload, sahte_playlist):
    """(e) Kapı eklenirken hacim kuralı gevşememeli: diskte üç kesit olsa da
    set başına EN FAZLA BİR yayın, ve `youtube_clip_video_id` yazıldıktan
    sonra o set bir daha hiç seçilmiyor."""
    monkeypatch.setattr(uyumluluk, "kontrol", lambda proje, asama="render": ([], []))
    kesitler = ("clip_01.mp4", "clip_02.mp4", "clip_03.mp4")
    set_dir = _hazir_set(tmp_path, kesitler=kesitler)

    s1 = dj_clips.supur(str(tmp_path), log=lambda *a: None)
    assert s1["yayinlanan"] == 1 and len(sahte_upload) == 1

    # Küresel tempo kapısını geriye alıp SET kapısının tek başına tuttuğunu gör.
    st = json.load(io.open(os.path.join(set_dir, "state.json"), encoding="utf-8"))
    st["youtube_clip_uploaded_at"] = time.strftime(
        "%Y-%m-%dT%H:%M:%S", time.localtime(time.time() - 30 * 86400))
    with io.open(os.path.join(set_dir, "state.json"), "w", encoding="utf-8") as f:
        f.write(json.dumps(st, ensure_ascii=False))

    s2 = dj_clips.supur(str(tmp_path), log=lambda *a: None)
    assert s2["yayinlanan"] == 0
    assert len(sahte_upload) == 1, "aynı setten İKİNCİ kesit yayınlandı"
    assert any("zaten" in a["sebep"] for a in s2["atlanan"])


def test_e_kosu_basina_tek_kesit_kapi_eklendikten_sonra_da(tmp_path, monkeypatch,
                                                           sahte_upload,
                                                           sahte_playlist):
    """İki set birden hazırken yine TEK kesit çıkmalı."""
    monkeypatch.setattr(uyumluluk, "kontrol", lambda proje, asama="render": ([], []))
    _hazir_set(tmp_path, ad="Set A")
    _hazir_set(tmp_path, ad="Set B")

    sonuc = dj_clips.supur(str(tmp_path), log=lambda *a: None)
    assert sonuc["yayinlanan"] == 1 and len(sahte_upload) == 1
