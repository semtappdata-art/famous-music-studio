"""dj_famous_process — YAYIN KAPILARI ve kuyruk sırası.

Neden bu testler var (üçü de canlı kanıtı olan olaylar):

1. **meta.json'suz klasör yayına giriyordu.** `audio.wav` var / `meta.json` yok
   bir klasör hatta pending sayılıyor, `youtube_upload.build_snippet({})` ile
   video "Untitled (Sözleri) | Türkçe Hip-Hop Şarkısı" başlığıyla CANLI
   yükleniyordu. Bölüm damgaları ve küratörlük notu da meta'dan geldiği için
   derlemenin "inauthentic content"e karşı var oluş sebebi tamamen kayboluyor.
   `uyumluluk.py` bunu yakalıyordu ama sadece UYARI olarak — yükleme devam
   ediyordu.

2. **Kuyruk başı tıkanması.** `find_pending_sets()` ctime'a göre EN ESKİYİ
   veriyor ve `--limit` varsayılanı 1; kalıcı takılmış bir set (Content ID
   ENGELİ almış ya da render'ı sürekli başarısız) arkasındaki yeni setleri
   süresiz bloklayabiliyordu.

3. **Kilit atomik değildi** ve koşu boyunca tazelenmiyordu — iki süreç aynı
   anda "kilit yok" görebiliyor, uzun bir koşuda kilit "bayat" sayılıp aynı
   set paralel yüklenebiliyordu.
"""

import json
import os
import time

import dj_famous_process as djp


def _set_kur(tmp_path, ad, meta=True, audio=True, state=None, gizli=False):
    d = tmp_path / ("." + ad if gizli else ad)
    d.mkdir(parents=True)
    if audio:
        (d / "audio.wav").write_bytes(b"RIFF")
    if meta:
        (d / "meta.json").write_text(json.dumps({"title": ad}), encoding="utf-8")
    if state is not None:
        (d / "state.json").write_text(json.dumps(state, ensure_ascii=False),
                                      encoding="utf-8")
    return str(d)


# --- 1. meta.json kapısı --------------------------------------------------

def test_metasiz_klasor_pending_sayilmiyor(tmp_path, monkeypatch):
    monkeypatch.setattr(djp, "log", lambda m: None)
    _set_kur(tmp_path, "Metasiz Set", meta=False)
    saglam = _set_kur(tmp_path, "Saglam Set")
    assert djp.find_pending_sets(str(tmp_path)) == [saglam]


def test_nokta_ile_baslayan_gecici_klasor_atlaniyor(tmp_path, monkeypatch):
    """derleme.py üretimi `.tmp-<ad>` klasöründe yapıp os.replace ile taşıyor —
    yarım hâldeki o klasör tarayıcıya görünmemeli (meta.json'u olsa bile)."""
    monkeypatch.setattr(djp, "log", lambda m: None)
    _set_kur(tmp_path, "tmp-Yarim Derleme", gizli=True)
    saglam = _set_kur(tmp_path, "Saglam Set")
    assert djp.find_pending_sets(str(tmp_path)) == [saglam]


def test_process_set_metasiz_klasorde_hic_is_yapmiyor(tmp_path, monkeypatch):
    """İKİNCİ EMNİYET KEMERİ: find_pending_sets atlansa/atlanmasa bile
    process_set doğrudan çağrıldığında (dj_tarama_kontrol'ün --base akışı,
    elle onarım koşuları) tek bir adım bile çalışmamalı."""
    monkeypatch.setattr(djp, "log", lambda m: None)
    cagrildi = []
    monkeypatch.setattr(djp.generate_cover, "generate",
                        lambda p: cagrildi.append(p))
    proje = _set_kur(tmp_path, "Metasiz Set", meta=False)
    djp.process_set(proje, "public", schedule=False)
    assert cagrildi == []


def test_metali_klasor_kapilardan_geciyor(tmp_path, monkeypatch):
    """Kapıların SAĞLAM seti engellemediğinin karşı-kanıtı (yoksa test paketi
    'her şeyi bloklayan' bir regresyonu fark etmezdi)."""
    monkeypatch.setattr(djp, "log", lambda m: None)
    monkeypatch.setattr(djp.generate_cover, "generate",
                        lambda p: (_ for _ in ()).throw(RuntimeError("dur")))
    proje = _set_kur(tmp_path, "Saglam Set")
    # generate_cover HATA verince process_set zaten dönüyor; önemli olan
    # meta.json kapısının bu noktaya kadar gelmesine izin vermesi.
    djp.process_set(proje, "public", schedule=False)
    assert djp.find_pending_sets(str(tmp_path)) == [proje]


# --- 2. Kuyruk başı tıkanması ---------------------------------------------

def test_ilerleme_yoksa_deneme_sayaci_artiyor(tmp_path):
    proje = _set_kur(tmp_path, "Takilan Set", state={})
    for beklenen in (1, 2, 3):
        djp._yayin_denemesini_guncelle(proje, set(djp._load_state(proje)))
        assert djp._load_state(proje)["dj_yayin_deneme"] == beklenen


def test_ilerleme_varsa_sayac_sifirlaniyor(tmp_path):
    proje = _set_kur(tmp_path, "Iyilesen Set", state={"dj_yayin_deneme": 2})
    onceki = set(djp._load_state(proje))
    djp._kaydet_durum(proje, {"youtube_video_id": "abc"})
    djp._yayin_denemesini_guncelle(proje, onceki)
    assert djp._load_state(proje)["dj_yayin_deneme"] == 0


def test_kapida_bekleyen_set_basarisiz_sayilmiyor(tmp_path):
    """dj_tarama_bekliyor / dj_tarama_engelli setlerinde process_set zaten iş
    yapmadan dönüyor; onları 'başarısız' saymak sayacı yanıltırdı."""
    for bayrak in ("dj_tarama_bekliyor", "dj_tarama_engelli"):
        proje = _set_kur(tmp_path, "Kapida " + bayrak, state={bayrak: True})
        djp._yayin_denemesini_guncelle(proje, set(djp._load_state(proje)))
        assert "dj_yayin_deneme" not in djp._load_state(proje)


def test_tavani_dolduran_set_kuyrugun_sonuna_dusuyor(tmp_path):
    """Sıralama mantığının main()'deki hâliyle birebir aynısı: tavanı dolduran
    set geri plana atılıyor, geri kalanlar ctime sırasını koruyor."""
    eski_takilan = _set_kur(tmp_path, "A Takilan",
                            state={"dj_yayin_deneme": djp.DJ_YAYIN_DENEME_TAVANI})
    time.sleep(0.01)
    yeni_saglam = _set_kur(tmp_path, "B Yeni", state={})
    time.sleep(0.01)
    en_yeni = _set_kur(tmp_path, "C Daha Yeni", state={})

    yeniler = [eski_takilan, yeni_saglam, en_yeni]
    yeniler.sort(key=lambda p: 1 if int(
        djp._load_state(p).get("dj_yayin_deneme") or 0) >= djp.DJ_YAYIN_DENEME_TAVANI else 0)
    # Takılan sona düştü, sağlıklı ikisi kendi aralarındaki sırayı korudu.
    assert yeniler == [yeni_saglam, en_yeni, eski_takilan]


# --- 3. Kilit -------------------------------------------------------------

def test_kilit_ikinci_surece_verilmiyor(tmp_path, monkeypatch):
    monkeypatch.setattr(djp, "LOCK_PATH", str(tmp_path / ".lock"))
    monkeypatch.setattr(djp, "_KILIT_BIZDE", False)
    assert djp._acquire_lock() is True
    assert djp._acquire_lock() is False      # taze kilit devralınamaz
    djp._release_lock()
    assert not os.path.isfile(str(tmp_path / ".lock"))


def test_bayat_kilit_devralaniyor(tmp_path, monkeypatch):
    kilit = tmp_path / ".lock"
    monkeypatch.setattr(djp, "LOCK_PATH", str(kilit))
    monkeypatch.setattr(djp, "log", lambda m: None)
    kilit.write_text("999")
    eski = time.time() - djp.LOCK_STALE_SECONDS - 60
    os.utime(str(kilit), (eski, eski))
    assert djp._acquire_lock() is True
    assert kilit.read_text() == str(os.getpid())
    djp._release_lock()


def test_log_kilidi_tazeliyor(tmp_path, monkeypatch):
    """Uzun koşularda kilidin 'bayat' sayılıp aynı setin paralel yüklenmesini
    önleyen nabız — log() her anlamlı adımda çağrıldığı için oraya konuldu."""
    kilit = tmp_path / ".lock"
    monkeypatch.setattr(djp, "LOCK_PATH", str(kilit))
    monkeypatch.setattr(djp, "LOG_PATH", str(tmp_path / "x.log"))
    monkeypatch.setattr(djp, "_KILIT_BIZDE", False)
    assert djp._acquire_lock() is True
    try:
        eski = time.time() - 3600
        os.utime(str(kilit), (eski, eski))
        djp.log("bir adım")
        assert time.time() - os.path.getmtime(str(kilit)) < 60
    finally:
        djp._release_lock()


def test_kilit_bizde_degilken_log_tazelemiyor(tmp_path, monkeypatch):
    """Kilidi ALAMAYAN süreç de log() çağırıyor; rakibin kilidini tazelerse
    gerçekten bayat bir kilit hiç eskimez."""
    kilit = tmp_path / ".lock"
    monkeypatch.setattr(djp, "LOCK_PATH", str(kilit))
    monkeypatch.setattr(djp, "LOG_PATH", str(tmp_path / "x.log"))
    monkeypatch.setattr(djp, "_KILIT_BIZDE", False)
    kilit.write_text("999")
    eski = time.time() - 3600
    os.utime(str(kilit), (eski, eski))
    djp.log("kilit alınamadı")
    assert time.time() - os.path.getmtime(str(kilit)) > 600


# --- İŞ 3: atomik state yazımı -------------------------------------------

def test_kaydet_durum_atomik_yardimciyi_kullaniyor(tmp_path, monkeypatch):
    """Yarım JSON artık uyumluluk.py'de HATA üretip yayını durduruyor; bu
    yazımın state_io'nun tmp+fsync+os.replace deseninden geçtiği garanti."""
    proje = _set_kur(tmp_path, "Atomik Set", state={"a": 1})
    cagrilar = []
    orj = djp.state_io.durum_yaz
    monkeypatch.setattr(djp.state_io, "durum_yaz",
                        lambda p, v: (cagrilar.append((p, dict(v))), orj(p, v))[1])
    djp._kaydet_durum(proje, {"b": 2})
    assert cagrilar and cagrilar[0][1] == {"a": 1, "b": 2}
    assert djp._load_state(proje) == {"a": 1, "b": 2}
    # Geçici dosya arkada bırakılmamalı
    assert not os.path.isfile(os.path.join(proje, "state.json.tmp"))
