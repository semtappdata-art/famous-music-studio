# -*- coding: utf-8 -*-
"""`saglik_kontrol.uretim_kuyrugu_bos()` — üretim kuyruğu boş nöbetçisi.

NEDEN VAR (2026-09-12): yedinci adım (`yayin_durgunlugu`) "iş var ama akmıyor"
diyebilmek için "bekleyen proje varsa" muafiyetine MECBUR — katalog bitmişse
sessizlik normaldir ve orada çalan bir alarm her hafta tekrar ederdi. Ama tam
o muafiyetin İÇİ kör noktaydı: kuyruk boşaldığında
  - `yayin_durgunlugu` susar (muafiyet),
  - `kacan_kosu` susar (koşular yapılıyor),
  - `git_senkron` susar (yayın olmayınca yerel/canlı fark büyümez),
  - kalan dört adım ön koşullara bakıyor,
yani kanal yeni malzeme bitince SESSİZCE durur ve sistemin tamamı "her şey
yolunda" der.

EN ÖNEMLİ TEST BURADA DA "ALARM ÇALIYOR MU" DEĞİL:
`test_iki_nobetci_ayni_anda_alarm_vermez` — iki nöbetçinin mantıkları
birbirini dışlamak ZORUNDA. Dışlama eşiklerden değil, "bekleyen proje"
listesinin TEK bir kaynaktan (`_yayin_taramasi`) okunmasından geliyor; hem
davranış matrisiyle hem `ast` muhafızıyla kilitli.

BU TESTLERDE GERÇEK BİR ŞEY ÇALIŞMIYOR: `notify`, saat (`time.time`), durum
dosyası ve repo kökü (`SK.REPO`, markdown belgeleri için) monkeypatch'li;
katalog kökü `tmp_path`e çekiliyor (`uyumluluk.KOKLER`), yani gerçek
`projects/`, `dj_sets/`, `derlemeler/` klasörlerine ne yazılıyor ne bakılıyor.
Hiçbir ağ çağrısı, hiçbir PowerShell süreci, hiçbir git komutu yok.
"""

import ast
import json
import os
import sys
import time
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "upload"))

import pytest

import saglik_kontrol as SK

SAAT = 3600.0
T0 = 1_760_000_000.0          # sabit bir "şimdi" çapası

# Dört ana platform anahtarı dolu = bu proje `pending`den düşmüş demek.
TAM = {
    "youtube_video_id": "yt1",
    "youtube_shorts_video_id": "sh1",
    "tiktok_publish_id": "tk1",
    "instagram_media_id": "ig1",
}

_KAYNAK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "saglik_kontrol.py")

# Diskteki GERÇEK belgelerde duran süs karakterleri (2026-09-12 ölçümü):
# sağ ok U+2192 her iki belgede de var, uyarı işareti U+26A0
# `haftalik_is_akisi.md`de. Testlerde bilerek kullanılıyorlar — mesaja
# SIZMAMALARI gereken şey tam olarak bunlar.
OK = "→"
UYARI_ISARETI = "⚠"


def _damga(t: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t))


@pytest.fixture
def ortam(tmp_path, monkeypatch):
    """Durum dosyası tmp'de, notify sahte, katalog kökü ve repo kökü tmp'de."""
    monkeypatch.setattr(SK, "DURUM_DOSYASI", str(tmp_path / "saglik_durum.json"))
    # `_belge_oku` buradan okuyor: gerçek ses_ve_tarz_takibi.md /
    # haftalik_is_akisi.md testleri etkilemesin (ikisi de paralel değişiyor).
    monkeypatch.setattr(SK, "REPO", str(tmp_path))

    import uyumluluk
    kok = tmp_path / "projects"        # ad ÖNEMLİ: _ana_katalog_koku "projects" arıyor
    kok.mkdir()
    monkeypatch.setattr(uyumluluk, "KOKLER", (str(kok),))

    gonderilen = []
    m = types.ModuleType("notify")
    m.send = lambda baslik, mesaj, *a, **k: (gonderilen.append((baslik, mesaj)), True)[1]
    monkeypatch.setitem(sys.modules, "notify", m)

    monkeypatch.setattr(SK.time, "time", lambda: T0)
    return types.SimpleNamespace(kok=kok, repo=tmp_path, gonderilen=gonderilen,
                                 monkeypatch=monkeypatch)


def _proje(ortam, ad, state=None, ses=True, meta=None, ek_dosyalar=()):
    d = ortam.kok / ad
    d.mkdir()
    if ses:
        (d / "audio.wav").write_bytes(b"RIFF0000")
    if state is not None:
        (d / "state.json").write_text(json.dumps(state), encoding="utf-8")
    if meta is not None:
        (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False),
                                     encoding="utf-8")
    for dosya in ek_dosyalar:
        (d / dosya).write_bytes(b"ham-ses")
    return d


def _yayinlanmis(ortam, ad, saat_once, **kw):
    """Dört anahtarı da dolu, `saat_once` saat önce yayınlanmış proje."""
    st = dict(TAM)
    st["youtube_uploaded_at"] = _damga(T0 - saat_once * SAAT)
    return _proje(ortam, ad, st, **kw)


# ===========================================================================
# (a) kuyruk BOŞ + eşik aşıldı -> BİLDİRİM
# ===========================================================================

def test_kuyruk_bos_ve_esik_asilmissa_bildirim_gonderir(ortam):
    """104 saat = 2 x 52 saatlik yayın tabanı: iki yayın slotu boş geçti."""
    _yayinlanmis(ortam, "Yayinda 1", saat_once=120, meta={"theme": "pop"})
    _yayinlanmis(ortam, "Yayinda 2", saat_once=300, meta={"theme": "rock"})

    satirlar = []
    s = SK.uretim_kuyrugu_bos(log=satirlar.append)

    assert s["durum"] == "bos"
    assert s["bekleyen"] == 0 and s["ham_ses"] == 0
    assert s["proje"] == 2
    assert s["bildirildi"] is True
    assert 119 * SAAT < s["sessizlik_sn"] < 121 * SAAT

    assert len(ortam.gonderilen) == 1
    baslik, mesaj = ortam.gonderilen[0]
    assert baslik == "Üretim kuyruğu boş"
    # Eyleme dönük olmak ZORUNDA: neden çaldı, ne kadar oldu, ne üretmeli.
    assert "52 saat" in mesaj and "104 saat" in mesaj
    assert "2 proje" in mesaj
    assert "watch_projects" in mesaj            # akış: dosyayı nereye koyacak
    assert "En uzun boşta tarz: rock" in mesaj  # meta.json dağılımından TÜRETİLDİ
    assert any("üretim kuyruğu BOŞ" in l for l in satirlar)


def test_esik_tam_sinirinda_bildirim_gider(ortam):
    """104 saat = eşik; `<` karşılaştırması olduğu için tam sınırda ALARM."""
    _yayinlanmis(ortam, "Yayinda", saat_once=104)
    s = SK.uretim_kuyrugu_bos(log=lambda *a: None)
    assert s["durum"] == "bos"
    assert len(ortam.gonderilen) == 1


# ===========================================================================
# (b) kuyruk BOŞ + eşik ALTINDA -> SESSİZ
# ===========================================================================

@pytest.mark.parametrize("saat", [0.5, 3.4, 52.0, 78.0, 90.0, 103.9])
def test_esigin_altinda_sessiz_kalir(ortam, saat):
    """Kuyruk boşalır boşalmaz uyarmak GÜRÜLTÜ — burada acele yok.

    3.4 saat bu deponun 2026-09-12 öğleden sonraki gerçek ölçümüdür;
    52 saat yayın tabanının kendisi (birinci slot daha yeni geldi);
    78 saat YEDİNCİ adımın eşiği (bu adım orada hâlâ susmalı);
    103.9 eşiğin bir tık altı.
    """
    _yayinlanmis(ortam, "Yayinda", saat_once=saat)

    satirlar = []
    s = SK.uretim_kuyrugu_bos(log=satirlar.append)

    assert s["durum"] == "tamam"
    assert s["bekleyen"] == 0 and s["ham_ses"] == 0
    assert ortam.gonderilen == []
    assert satirlar == []


# ===========================================================================
# (c) kuyrukta İŞ VAR -> bu adım SESSİZ (o `yayin_durgunlugu`'nun işi)
# ===========================================================================

@pytest.mark.parametrize("eksik", sorted(SK.ANA_PLATFORM_ANAHTARLARI))
def test_bekleyen_proje_varken_uzun_sessizlikte_bile_sessiz(ortam, eksik):
    """Dört anahtarın HANGİSİ eksik olursa olsun kuyruk dolu sayılır."""
    _yayinlanmis(ortam, "Yayinda", saat_once=300)
    _proje(ortam, "Bekleyen", {k: "x" for k in SK.ANA_PLATFORM_ANAHTARLARI
                               if k != eksik})

    satirlar = []
    s = SK.uretim_kuyrugu_bos(log=satirlar.append)

    assert s["durum"] == "kuyrukta_is_var"
    assert s["bekleyen"] == 1
    assert ortam.gonderilen == []
    assert satirlar == [], "iki nöbetçi aynı olayı iki kez anlatmaz"


# ===========================================================================
# (d) KARŞILIKLI DIŞLAMA — iki nöbetçi asla aynı anda çalmaz
# ===========================================================================

def _senaryo_kur(ortam, ad):
    if ad == "bekleyen_var_uzun_sessizlik":
        _yayinlanmis(ortam, "Yayinda", saat_once=300)
        _proje(ortam, "Bekleyen", {"youtube_video_id": "yt9"})
    elif ad == "kuyruk_bos_uzun_sessizlik":
        _yayinlanmis(ortam, "Yayinda", saat_once=300)
    elif ad == "bekleyen_var_kisa_sessizlik":
        _yayinlanmis(ortam, "Yayinda", saat_once=2)
        _proje(ortam, "Bekleyen", {})
    elif ad == "kuyruk_bos_kisa_sessizlik":
        _yayinlanmis(ortam, "Yayinda", saat_once=2)
    elif ad == "ham_ses_uzun_sessizlik":
        _yayinlanmis(ortam, "Yayinda", saat_once=300)
        _proje(ortam, "Ham Ses", state=None, ses=False,
               ek_dosyalar=("Suno Indirme 01.mp3",))
    elif ad == "esik_arasi_78_ile_104":
        # İki eşiğin ARASI: yedinci adım çalar (bekleyen varsa), sekizinci
        # susar. Aynı anda çalma ihtimalinin en yüksek olduğu aralık.
        _yayinlanmis(ortam, "Yayinda", saat_once=90)
        _proje(ortam, "Bekleyen", {})
    elif ad == "damga_yok":
        _proje(ortam, "Bekleyen", {})
    else:                                       # pragma: no cover
        raise AssertionError("bilinmeyen senaryo: %s" % ad)


SENARYOLAR = [
    "bekleyen_var_uzun_sessizlik",
    "kuyruk_bos_uzun_sessizlik",
    "bekleyen_var_kisa_sessizlik",
    "kuyruk_bos_kisa_sessizlik",
    "ham_ses_uzun_sessizlik",
    "esik_arasi_78_ile_104",
    "damga_yok",
]


@pytest.mark.parametrize("senaryo", SENARYOLAR)
def test_iki_nobetci_ayni_anda_alarm_vermez(ortam, senaryo):
    """DAVRANIŞ MATRİSİ — yedi katalog durumunda ikisi birden ASLA çalmaz.

    `yayin_durgunlugu` "iş var ama akmıyor", `uretim_kuyrugu_bos` "akacak iş
    kalmadı" diyor. İkisi aynı anda doğru olamaz; ikisi aynı anda çalarsa
    telefonda çelişkili iki uyarı olur ve ikisi de değersizleşir.
    """
    _senaryo_kur(ortam, senaryo)

    yedinci = SK.yayin_durgunlugu(log=lambda *a: None)
    sekizinci = SK.uretim_kuyrugu_bos(log=lambda *a: None)

    alarmlar = {b for b, _ in ortam.gonderilen}
    assert not ({"Yayın durdu"} <= alarmlar and {"Üretim kuyruğu boş"} <= alarmlar), (
        "iki nöbetçi aynı anda alarm verdi: %s (yedinci=%s, sekizinci=%s)"
        % (alarmlar, yedinci["durum"], sekizinci["durum"]))
    assert not (yedinci["durum"] == "durgun" and sekizinci["durum"] == "bos")
    assert len(alarmlar) <= 1


def test_matris_beklenen_alarmlari_gercekten_uretiyor(ortam):
    """Matris testi "hiçbir zaman alarm çalmasın" diye geçmesin diye.

    İki senaryoda alarmın GERÇEKTEN çaldığı ayrıca kanıtlanıyor; aksi hâlde
    yukarıdaki dışlama testi, kodu tamamen sessizleştiren bir hatada da yeşil
    kalırdı (bu deponun klasik "sessizce False dönen koruma" tuzağı).
    """
    _senaryo_kur(ortam, "bekleyen_var_uzun_sessizlik")
    SK.yayin_durgunlugu(log=lambda *a: None)
    SK.uretim_kuyrugu_bos(log=lambda *a: None)
    assert [b for b, _ in ortam.gonderilen] == ["Yayın durdu"]


def test_kuyruk_bos_senaryosunda_yalniz_sekizinci_calar(ortam):
    _senaryo_kur(ortam, "kuyruk_bos_uzun_sessizlik")
    yedinci = SK.yayin_durgunlugu(log=lambda *a: None)
    SK.uretim_kuyrugu_bos(log=lambda *a: None)
    assert yedinci["durum"] == "bekleyen_yok"
    assert [b for b, _ in ortam.gonderilen] == ["Üretim kuyruğu boş"]


def test_bekleyen_tanimi_TEK_kaynakta(ortam):
    """`ast` MUHAFIZI: iki adım "bekleyen proje"yi aynı yerden okuyor.

    Karşılıklı dışlama eşiklerden değil MANTIKTAN geliyor; bu ancak ikinci bir
    "bekleyen" tanımı YAZILMAZSA geçerli. İki koşul birden denetleniyor:
      1. `_kuyruk_taramasi` gerçekten `_yayin_taramasi`yi çağırıyor,
      2. `ANA_PLATFORM_ANAHTARLARI` (ölçütün kendisi) modülde BAŞKA hiçbir
         fonksiyonda kullanılmıyor — yani kopyalanmış bir ikinci ölçüt yok.
    """
    agac = ast.parse(open(_KAYNAK, encoding="utf-8").read())

    kuyruk = next(d for d in ast.walk(agac)
                  if isinstance(d, ast.FunctionDef) and d.name == "_kuyruk_taramasi")
    cagrilar = {c.func.id for c in ast.walk(kuyruk)
                if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}
    assert "_yayin_taramasi" in cagrilar

    kullananlar = set()
    for d in ast.walk(agac):
        if not isinstance(d, ast.FunctionDef):
            continue
        for n in ast.walk(d):
            if isinstance(n, ast.Name) and n.id == "ANA_PLATFORM_ANAHTARLARI":
                kullananlar.add(d.name)
    assert kullananlar == {"_yayin_taramasi"}, (
        "'bekleyen proje' ölçütü ikinci bir yere kopyalanmış: %s" % sorted(kullananlar))


# ===========================================================================
# (e) isimlendirilmemiş ham ses -> kuyruk BOŞ SAYILMAZ
# ===========================================================================

@pytest.mark.parametrize("dosya", ["Suno Indirme.mp3", "yeni parca.wav",
                                   "TRACK 02.M4A", "kayit.m4a"])
def test_isimlendirilmemis_ham_ses_kuyrugu_dolu_yapar(ortam, dosya):
    """`audio.*` adına çevrilmemiş ses = HENÜZ işlenmemiş iş.

    Böyle bir klasörde `audio.*` YOKTUR, yani `_yayin_taramasi()` onu ses
    şartından eler ve "bekleyen" saymaz — bu adım onu ayrıca aramazsa kuyruğu
    boş sanıp "üret" der, oysa yapılacak iş tam o dosyadır.
    """
    _yayinlanmis(ortam, "Yayinda", saat_once=300)
    _proje(ortam, "Yeni Parca", state=None, ses=False, ek_dosyalar=(dosya,))

    satirlar = []
    s = SK.uretim_kuyrugu_bos(log=satirlar.append)

    assert s["durum"] == "kuyrukta_is_var"
    assert s["ham_ses"] == 1
    assert s["bekleyen"] == 0, "ham ses 'bekleyen proje' ile KARIŞTIRILMAMALI"
    assert ortam.gonderilen == []
    assert satirlar == []


def test_audio_wav_varken_ikinci_ses_HAM_SAYILMAZ(ortam):
    """`dj_sets/City Pulse Set/audio_telifsiz.wav` vakası (diskte GERÇEK).

    `watch_projects._scan_root` sesi OLAN bir klasöre hiç girmiyor
    (`if _has_audio(project_dir): continue`), yani oradaki ikinci ses dosyası
    ASLA yeniden adlandırılmaz ve hattı TETİKLEMEZ. Ham sayılsaydı o tek dosya
    kuyruğu SONSUZA KADAR "dolu" gösterir ve bu nöbetçi hiç ateşlenmezdi —
    yazıldığı gün ölen bir koruma.
    """
    _yayinlanmis(ortam, "City Pulse Set", saat_once=300,
                 ek_dosyalar=("audio_telifsiz.wav",))

    s = SK.uretim_kuyrugu_bos(log=lambda *a: None)
    assert s["ham_ses"] == 0
    assert s["durum"] == "bos"
    assert len(ortam.gonderilen) == 1


def test_ses_olmayan_bos_klasor_kuyrugu_dolu_YAPMAZ(ortam):
    """`dj_sets/Night Drive` vakası: ne ses ne state — proje de iş de değil."""
    _yayinlanmis(ortam, "Yayinda", saat_once=300)
    _proje(ortam, "Night Drive", state=None, ses=False)

    s = SK.uretim_kuyrugu_bos(log=lambda *a: None)
    assert s["ham_ses"] == 0 and s["bekleyen"] == 0
    assert s["durum"] == "bos"


def test_ham_ses_uzantilari_watch_projects_ile_AYNI():
    """SÜRÜKLENME MUHAFIZI: desen `watch_projects.AUDIO_EXT_TO_NAME`den ayrışmasın.

    `saglik_kontrol` o modülü BİLEREK import etmiyor (dakikalık izleyicinin
    modül düzeyi kurulumunu bir tanı adımına taşımak istemiyoruz), ama iki
    kümenin sessizce ayrışması da kabul edilemez: ayrışırsa bu nöbetçi
    Watcher'ın işleyeceği bir dosyayı görmez ve yanlış alarm verir.
    """
    import watch_projects as wp

    assert set(SK.HAM_SES_UZANTILARI) == set(wp.AUDIO_EXT_TO_NAME)
    assert set(SK.SES_DOSYALARI) == set(wp.AUDIO_NAMES)


# ===========================================================================
# (f) damga yok / bozuk -> ÇÖKMEZ
# ===========================================================================

def test_hic_yayin_damgasi_yoksa_atlanir(ortam):
    """Taze checkout: karşılaştırmanın bir tarafı hiç YOK -> iddia da yok."""
    _proje(ortam, "Sadece Ses", dict(TAM))     # yayında ama damgasız
    s = SK.uretim_kuyrugu_bos(log=lambda *a: None)
    assert s["durum"] == "atlandi"
    assert s["sebep"] == "yayin damgasi yok"
    assert ortam.gonderilen == []


def test_hic_klasor_yoksa_cokmez(ortam):
    """Tamamen boş bir katalog: 0 proje, 0 damga -> sessiz, çökme yok."""
    s = SK.uretim_kuyrugu_bos(log=lambda *a: None)
    assert s["durum"] == "atlandi"
    assert s["proje"] == 0
    assert ortam.gonderilen == []


def test_bozuk_state_meta_ve_damga_cokmez(ortam):
    """Yarım JSON, liste JSON, sayı/None damga, bozuk meta — hiçbiri çökmemeli."""
    _yayinlanmis(ortam, "Yayinda", saat_once=300, meta={"theme": "pop"})

    yarim = _proje(ortam, "Yarim JSON", dict(TAM))
    (yarim / "state.json").write_text('{"youtube_video_id": ', encoding="utf-8")

    liste = _proje(ortam, "Liste JSON", dict(TAM))
    (liste / "state.json").write_text("[1, 2, 3]", encoding="utf-8")

    bozuk_meta = _proje(ortam, "Bozuk Meta", dict(TAM))
    (bozuk_meta / "meta.json").write_text("{bu json degil", encoding="utf-8")

    st = dict(TAM)
    st.update({"youtube_uploaded_at": 12345, "tiktok_uploaded_at": None,
               "bluesky_uploaded_at": "dun aksam"})
    _proje(ortam, "Bozuk Damga", st, meta={"theme": ["liste", "olmaz"]})

    satirlar = []
    s = SK.uretim_kuyrugu_bos(log=satirlar.append)

    # Yarım/liste JSON'lu iki proje "bekleyen" sayılır -> kuyruk dolu.
    assert s["durum"] == "kuyrukta_is_var"
    assert s["bekleyen"] == 2
    assert s["proje"] == 5
    assert ortam.gonderilen == []
    assert satirlar == []


def test_damga_gelecekteyse_alarm_yok(ortam):
    """Sistem saati geri alınmış: log'a satır düşer, telefon susar."""
    _yayinlanmis(ortam, "Yayinda", saat_once=-5)     # 5 saat SONRA

    satirlar = []
    s = SK.uretim_kuyrugu_bos(log=satirlar.append)

    assert s["durum"] == "atlandi"
    assert s["sebep"] == "damga gelecekte"
    assert ortam.gonderilen == []
    assert any("gelecekte" in l for l in satirlar)


def test_tarama_patlarsa_sessiz_kalmaz(ortam, monkeypatch):
    """Kontrolün KENDİSİ patlarsa log'a satır düşer — sessizce `{}` dönmez."""
    def _patla():
        raise RuntimeError("disk gitti")

    monkeypatch.setattr(SK, "_kuyruk_taramasi", _patla)
    satirlar = []
    s = SK.uretim_kuyrugu_bos(log=satirlar.append)
    assert s["durum"] == "calistirilamadi"
    assert satirlar and "disk gitti" in satirlar[0]
    assert ortam.gonderilen == []


def test_oneri_kaynaklari_patlarsa_bildirim_yine_gider(ortam, monkeypatch):
    """Plan kaynağı okunamazsa uyarı KAYBOLMAZ — genel mesajla gider ve söyler."""
    monkeypatch.setattr(SK, "_en_uzun_bosta_tarz",
                        lambda: (_ for _ in ()).throw(RuntimeError("meta gitti")))
    _yayinlanmis(ortam, "Yayinda", saat_once=300)

    s = SK.uretim_kuyrugu_bos(log=lambda *a: None)
    assert s["durum"] == "bos" and s["bildirildi"] is True
    _, mesaj = ortam.gonderilen[0]
    assert "ÇIKARILAMADI" in mesaj, "öneri yoksa bunu AÇIKÇA yazmalı"


# ===========================================================================
# (g) günde bir
# ===========================================================================

def test_ayni_gun_ikinci_bildirim_bastirilir(ortam):
    """`_bildir` mekanizmasının AYNISI: saatlik koşuda telefon bir kez çalar."""
    _yayinlanmis(ortam, "Yayinda", saat_once=300)

    ilk = SK.uretim_kuyrugu_bos(log=lambda *a: None)
    assert ilk["bildirildi"] is True
    assert len(ortam.gonderilen) == 1

    ikinci = SK.uretim_kuyrugu_bos(log=lambda *a: None)
    assert ikinci["durum"] == "bos"             # log'a yine düşer
    assert ikinci["bildirildi"] is False
    assert len(ortam.gonderilen) == 1, "aynı gün ikinci bildirim gitmemeli"


def test_gonderim_basarisizsa_damga_atilmaz(ortam):
    """`notify.send` False dönerse bir sonraki saatlik koşu YENİDEN dener."""
    _yayinlanmis(ortam, "Yayinda", saat_once=300)

    sys.modules["notify"].send = lambda *a, **k: False
    s = SK.uretim_kuyrugu_bos(log=lambda *a: None)
    assert s["bildirildi"] is False
    assert SK._durum().get("uretim_kuyrugu_bildirim_gun") is None


# ===========================================================================
# (h) `kontrol_et`e GERÇEKTEN bağlı mı? (ast muhafızı)
# ===========================================================================

def test_kontrol_et_uretim_kuyrugunu_cagiriyor_ve_SIRASI_dogru():
    """CLAUDE.md'nin birinci dersi: yazıldı ama HİÇBİR YERDEN çağrılmıyor.

    SIRA da kilitleniyor: yedinci adımın hemen ardında (okunurluk: ikisi bir
    çifttir) ve `kacan_kosu`dan ÖNCE — o adım damgayı EN SONDA tazeliyor,
    "saatlik hattın sonuna ulaşıldı" iddiası en sonda doğmalı.
    """
    agac = ast.parse(open(_KAYNAK, encoding="utf-8").read())
    hedef = next(d for d in ast.walk(agac)
                 if isinstance(d, ast.FunctionDef) and d.name == "kontrol_et")
    anahtarlar = [k.value for d in ast.walk(hedef)
                  if isinstance(d, ast.Dict)
                  for k in d.keys
                  if isinstance(k, ast.Constant)]
    assert "uretim_kuyrugu" in anahtarlar
    assert (anahtarlar.index("yayin_durgunlugu")
            < anahtarlar.index("uretim_kuyrugu")
            < anahtarlar.index("kacan_kosu"))


# ===========================================================================
# (i) cp1254 tuzağı
# ===========================================================================

def _cp1254_disi(metin: str) -> str:
    disarida = []
    for ch in metin:
        try:
            ch.encode("cp1254")
        except UnicodeEncodeError:
            if ch not in disarida:
                disarida.append(ch)
    return "".join(disarida)


def test_uretilen_tum_metinler_cp1254e_kodlanabiliyor(ortam):
    """Belgelerdeki süs karakterleri mesaja SIZMAMALI.

    Bu adımın mesajı KODA GÖMÜLÜ DEĞİL — `ses_ve_tarz_takibi.md` ve
    `haftalik_is_akisi.md`den türetiliyor ve ikisi de bugün diskte sağ ok
    (U+2192) / uyarı işareti (U+26A0) taşıyor. Bu makinede konsol cp1254;
    `buyume_kontrol_listesi.md`deki tek bir U+2248 GERÇEK bir çökme üretti.
    Kaynaktaki sabitleri kilitlemek YETMEZ, süzgeç çalışma anında olmalı.
    """
    (ortam.repo / "ses_ve_tarz_takibi.md").write_text(
        "# Takip\n\n**SON DURUM (2026-09-11) %s son üç üretim ERKEK vokal.** "
        "**Sıradaki şarkı: KADIN vokal %s düet DEĞİL.** Devamı.\n" % (OK, OK),
        encoding="utf-8")
    (ortam.repo / "haftalik_is_akisi.md").write_text(
        "# Akış\n\n%s uyarı satırı\n\n### Salı %s üretim vardiyası\n\nİçerik.\n"
        % (UYARI_ISARETI, OK), encoding="utf-8")

    _yayinlanmis(ortam, "Yürek Yarası", saat_once=300, meta={"theme": "arabesk"})

    satirlar = []
    s = SK.uretim_kuyrugu_bos(log=satirlar.append)
    baslik, mesaj = ortam.gonderilen[0]

    assert s["durum"] == "bos"
    for metin in satirlar + [baslik, mesaj]:
        assert not _cp1254_disi(metin), (
            "cp1254'e sığmayan karakter: %r (metin: %s)"
            % (_cp1254_disi(metin), metin[:80]))

    # Öneri gerçekten belgelerden TÜRETİLDİ (koda gömülü değil):
    assert "KADIN vokal" in mesaj
    assert "üretim vardiyası" in mesaj
    assert "haftalik_is_akisi.md" in mesaj


def test_fonksiyondaki_tum_metin_sabitleri_cp1254_uyumlu():
    """Yalnız bu koşuda üretilenler değil, KAYNAKTAKİ tüm metin sabitleri."""
    agac = ast.parse(open(_KAYNAK, encoding="utf-8").read())
    hedefler = {"uretim_kuyrugu_bos", "_kuyruk_taramasi",
                "_isimlendirilmemis_sesler", "_uretim_onerisi",
                "_en_uzun_bosta_tarz", "_ana_katalog_koku", "_belge_oku",
                "_cp1254_guvenli", "_siradaki_uretim_notu", "_kirp"}
    sabitler = []
    for d in ast.walk(agac):
        if isinstance(d, ast.FunctionDef) and d.name in hedefler:
            sabitler += [x.value for x in ast.walk(d)
                         if isinstance(x, ast.Constant) and isinstance(x.value, str)]
    assert sabitler
    for metin in sabitler:
        assert not _cp1254_disi(metin), "cp1254 dışı sabit: %r" % metin


def test_cp1254_guvenli_bosluklari_da_sadelestiriyor():
    """Düşen bir karakter geriye çift boşluk bırakmamalı."""
    assert SK._cp1254_guvenli("A %s B" % OK) == "A B"
    assert SK._cp1254_guvenli("  tek\n satır  ") == "tek satır"
    assert SK._cp1254_guvenli("ığşİÖÜ") == "ığşİÖÜ"     # Türkçe harfler KALIR
    assert SK._cp1254_guvenli("") == ""


# ===========================================================================
# Eşik / sürüklenme muhafızları
# ===========================================================================

def test_esik_52_saatlik_yayin_tabanindan_TURETILMIS():
    """Eşik, tabanın 2 katı: iki yayın slotu boş geçince çalar.

    `auto_process.MIN_YAYIN_ARALIGI_SN` değişirse bu eşik de KENDİLİĞİNDEN
    değişmeli — elle yazılmış bir sayı olmamalı.
    """
    import auto_process as ap

    assert SK.YAYIN_TABANI_SN == ap.MIN_YAYIN_ARALIGI_SN
    assert SK.URETIM_KUYRUGU_ESIGI_SN == 2 * SK.YAYIN_TABANI_SN
    assert SK.URETIM_KUYRUGU_ESIGI_SN == 104 * 3600
    # Yedinci adımın eşiğinin ÜSTÜNDE: "boru hattı takıldı" daha acil.
    assert SK.YAYIN_DURGUNLUK_ESIGI_SN < SK.URETIM_KUYRUGU_ESIGI_SN
    # Bir haftanın ALTINDA: alarm, bir sonraki haftalık üretim vardiyası
    # gelmeden düşsün (haftalik_is_akisi.md).
    assert SK.URETIM_KUYRUGU_ESIGI_SN < 7 * 24 * 3600


def test_oneri_tarzi_KODA_GOMULU_DEGIL(ortam):
    """Tarz adı kaynakta yazmıyor; `meta.json` dağılımından geliyor.

    Uydurma bir tema adıyla kanıtlanıyor: kodda böyle bir tema yok, yine de
    öneride çıkıyor.
    """
    _yayinlanmis(ortam, "Eski", saat_once=900, meta={"theme": "uydurma-tarz"})
    _yayinlanmis(ortam, "Yeni", saat_once=300, meta={"theme": "pop"})

    s = SK.uretim_kuyrugu_bos(log=lambda *a: None)
    _, mesaj = ortam.gonderilen[0]
    assert s["durum"] == "bos"
    assert "uydurma-tarz" in mesaj, "en uzun boşta tarz seçilmedi"
    assert "uydurma-tarz" not in open(_KAYNAK, encoding="utf-8").read()


@pytest.mark.parametrize("paragraf,beklenen", [
    # 2026-09-11 biçimi (ilk sürüm bunu arıyordu):
    ("**SON DURUM (2026-09-11) %s son üç üretim ERKEK vokal.** "
     "**Sıradaki şarkı: KADIN vokal, düet DEĞİL.** Tempo da kümelendi." % OK,
     "KADIN vokal"),
    # 2026-09-12 biçimi (belge AYNI GÜN yeniden yazıldı; ilk kalıp buna kördü):
    ("**SON DURUM (2026-09-12) %s sıradaki üretim SEÇİLDİ ve tabloya girdi: "
     "`Vardiya`**\n(rock, 78 BPM, kadın, düet değil)." % OK,
     "Vardiya"),
    # Yönerge cümlesi hiç yoksa: paragrafın kendisi kullanılır (sessiz kalma).
    ("**SON DURUM (2026-09-20) %s katalog akustiğe kaydı.**" % OK, "akusti"),
])
def test_siradaki_uretim_notu_BICIME_SIKI_BAGLI_DEGIL(ortam, paragraf, beklenen):
    """İlk sürüm tek bir cümle kalıbına bağlıydı ve AYNI GÜN bayatladı.

    `ses_ve_tarz_takibi.md` paralel olarak güncellendi, "Sıradaki şarkı:"
    cümlesi kayboldu ve öneri sessizce boş kaldı — yazıldığı gün kör olan bir
    koruma. Çapa artık belgenin SÖZLEŞMESİ olan "SON DURUM" başlığı.
    """
    (ortam.repo / "ses_ve_tarz_takibi.md").write_text(
        "# Takip\n\n%s\n\n| tablo |\n" % paragraf, encoding="utf-8")

    not_ = SK._siradaki_uretim_notu()
    assert not_ and beklenen in not_
    assert not _cp1254_disi(not_)
    assert "*" not in not_ and "`" not in not_, "markdown süsü temizlenmeli"


def test_takip_dosyasi_yoksa_oneri_ADI_ile_sessizce_duser(ortam):
    """Belge hiç yoksa çökme yok, yalan yok: satır düşer, diğer kaynaklar kalır."""
    assert SK._siradaki_uretim_notu() is None
    _yayinlanmis(ortam, "Yayinda", saat_once=300, meta={"theme": "pop"})
    SK.uretim_kuyrugu_bos(log=lambda *a: None)
    _, mesaj = ortam.gonderilen[0]
    assert "Sıradaki üretim" not in mesaj
    assert "En uzun boşta tarz: pop" in mesaj


def test_hic_yayinlanmamis_tarz_en_basa_gelir(ortam):
    """Damgası olmayan tema "en uzun boşta" sayılır (hiç yayınlanmamış)."""
    _yayinlanmis(ortam, "Damgali", saat_once=300, meta={"theme": "pop"})
    _proje(ortam, "Damgasiz", dict(TAM), meta={"theme": "akustik"})

    SK.uretim_kuyrugu_bos(log=lambda *a: None)
    _, mesaj = ortam.gonderilen[0]
    assert "En uzun boşta tarz: akustik" in mesaj
    assert "hiç yayın damgası yok" in mesaj


def test_dj_setleri_tarz_onerisine_GIRMEZ(ortam, tmp_path, monkeypatch):
    """`dj` bir Suno tarzı değil, ayrı bir üretim hattı (dj_famous_process)."""
    import uyumluluk

    dj = tmp_path / "dj_sets"
    dj.mkdir()
    monkeypatch.setattr(uyumluluk, "KOKLER", (str(ortam.kok), str(dj)))

    _yayinlanmis(ortam, "Sarki", saat_once=300, meta={"theme": "pop"})
    (dj / "Set 1").mkdir()
    (dj / "Set 1" / "audio.wav").write_bytes(b"RIFF")
    (dj / "Set 1" / "meta.json").write_text('{"theme": "dj"}', encoding="utf-8")
    (dj / "Set 1" / "state.json").write_text(
        json.dumps(dict(TAM, youtube_uploaded_at=_damga(T0 - 900 * SAAT))),
        encoding="utf-8")

    s = SK.uretim_kuyrugu_bos(log=lambda *a: None)
    _, mesaj = ortam.gonderilen[0]
    assert s["proje"] == 2, "DJ seti KUYRUK sayımına girer (yayın hattı ortak)"
    assert "En uzun boşta tarz: pop" in mesaj
    assert "tarz: dj" not in mesaj
