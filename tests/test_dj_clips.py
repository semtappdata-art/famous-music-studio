"""dj_clips — kesit üretimi (telif elemesi, enerji sırası) ve İKİNCİ DALGA
yayın kısıtları.

Neden bu testler var: `dj_clips.py` 2026-09-11'e kadar TAMAMEN ÖLÜ koddu —
`clip_uret()` hiçbir yerden çağrılmıyordu ve üretilen `clip_*.mp4` dosyalarını
tüketen bir yükleyici yoktu. Bağlanırken asıl risk telif değil, YouTube'un
"inauthentic content" politikası: set başına 3 kesidi körü körüne yayınlamak
haftada +9 yükleme ve birbirine benzeyen içerik demekti. Buradaki testler o
kısıtların (set başına 1, setin kendi Shorts'uyla aynı gün değil, küresel
haftada 1) sessizce gevşemesini engelliyor.
"""

import json
import os
import time

import dj_clips


def _set_kur(tmp_path, ad="Test Set", state=None, kesit_dosyalari=()):
    d = tmp_path / ad
    (d / "output").mkdir(parents=True)
    (d / "audio.wav").write_bytes(b"")
    (d / "meta.json").write_text(json.dumps({"title": ad, "theme": "dj"}),
                                 encoding="utf-8")
    if state is not None:
        (d / "state.json").write_text(json.dumps(state, ensure_ascii=False),
                                      encoding="utf-8")
    for n in kesit_dosyalari:
        (d / "output" / n).write_bytes(b"x")
    return str(d)


# --- Üretim: telif elemesi + enerji sırası --------------------------------


def test_telifli_araliga_degen_pencere_eleniyor(tmp_path, monkeypatch):
    """City Pulse Set'in gerçek senaryosu: yerel audio.wav telifli bölümleri
    HÂLÂ içeriyor (YouTube sürümünden elle çıkarıldı). Kesit üreticisi tam o
    bölümden kesip yeniden yayınlamamalı."""
    set_dir = _set_kur(tmp_path, state={"telif_araliklari": [[100.0, 200.0]]})

    # [0] ana Shorts'un penceresi (her zaman atılıyor), kalan ikisinden biri
    # telifli aralığa değiyor.
    monkeypatch.setattr(dj_clips, "find_highlights",
                        lambda *a, **k: [(500.0, 545.0), (150.0, 195.0), (900.0, 945.0)])

    sonuc = dj_clips.clip_uret(set_dir, count=2, dry_run=True)
    pencereler = [(p["bas"], p["son"]) for p in sonuc["pencereler"]]
    assert pencereler == [(900.0, 945.0)]


def test_telifli_aralik_sadece_dokunuyorsa_elenmiyor(tmp_path, monkeypatch):
    """Sınır bitişikliği çakışma DEĞİL: 100-200 telifliyken 200-245 penceresi
    telifli tek bir örnek bile içermiyor, elenmemeli (aksi hâlde uzun bir
    setten gereksiz yere bütün bölgeler düşerdi)."""
    set_dir = _set_kur(tmp_path, state={"telif_araliklari": [[100.0, 200.0]]})
    monkeypatch.setattr(dj_clips, "find_highlights",
                        lambda *a, **k: [(500.0, 545.0), (200.0, 245.0)])

    sonuc = dj_clips.clip_uret(set_dir, count=1, dry_run=True)
    assert [(p["bas"], p["son"]) for p in sonuc["pencereler"]] == [(200.0, 245.0)]


def test_enerji_sirasi_korunuyor(tmp_path, monkeypatch):
    """find_highlights ENERJİ sırasında dönüyor, dosyalar ZAMAN sırasında
    yazılıyor. Aradaki eşleşme kaybolursa yayın adımı "en enerjili kesit"
    kuralını uygulayamaz — bu test o köprüyü koruyor."""
    set_dir = _set_kur(tmp_path)
    monkeypatch.setattr(dj_clips, "find_highlights",
                        lambda *a, **k: [(10.0, 55.0), (900.0, 945.0), (200.0, 245.0)])

    sonuc = dj_clips.clip_uret(set_dir, count=2, dry_run=True)
    # zaman sırası: 200 önce, 900 sonra — ama enerjide 900 daha güçlü (1).
    assert [(p["bas"], p["enerji"]) for p in sonuc["pencereler"]] == [(200.0, 2), (900.0, 1)]


# --- Seçim kuralı ----------------------------------------------------------


def test_kesit_sec_en_yuksek_enerjiyi_seciyor(tmp_path):
    st = {"dj_clips": [
        {"dosya": "clip_01.mp4", "bas": 200.0, "son": 245.0, "enerji": 2},
        {"dosya": "clip_02.mp4", "bas": 900.0, "son": 945.0, "enerji": 1},
        {"dosya": "clip_03.mp4", "bas": 1500.0, "son": 1545.0, "enerji": 3},
    ]}
    set_dir = _set_kur(tmp_path, state=st,
                       kesit_dosyalari=("clip_01.mp4", "clip_02.mp4", "clip_03.mp4"))
    assert dj_clips.kesit_sec(set_dir)["dosya"] == "clip_02.mp4"


def test_kesit_sec_hatali_ve_diskte_olmayan_kesitleri_atliyor(tmp_path):
    st = {"dj_clips": [
        {"dosya": "clip_01.mp4", "enerji": 1, "hata": "render patladı"},
        {"dosya": "clip_02.mp4", "enerji": 2},          # diskte YOK
        {"dosya": "clip_03.mp4", "enerji": 3},
    ]}
    set_dir = _set_kur(tmp_path, state=st, kesit_dosyalari=("clip_01.mp4", "clip_03.mp4"))
    assert dj_clips.kesit_sec(set_dir)["dosya"] == "clip_03.mp4"


# --- Yayın kapıları --------------------------------------------------------


def _hazir_state(shorts_yas_sn):
    damga = time.strftime("%Y-%m-%dT%H:%M:%S",
                          time.localtime(time.time() - shorts_yas_sn))
    return {
        "youtube_video_id": "abc",
        "youtube_shorts_video_id": "def",
        "youtube_shorts_uploaded_at": damga,
        "dj_tarama_temiz": True,
        "dj_clips": [{"dosya": "clip_01.mp4", "bas": 900.0, "son": 945.0, "enerji": 1}],
    }


def test_ayni_gun_yayinlanmiyor(tmp_path):
    """Setin kendi Shorts'uyla AYNI GÜN ikinci bir kesit çıkmamalı — kesit
    ek bir yükleme değil, zamana yayılmış ikinci bir dalga."""
    set_dir = _set_kur(tmp_path, state=_hazir_state(60 * 60),
                       kesit_dosyalari=("clip_01.mp4",))
    kesit, sebep = dj_clips.yayina_uygun_mu(set_dir)
    assert kesit is None and "gün" in sebep


def test_bekleme_dolunca_yayinlanabiliyor(tmp_path):
    set_dir = _set_kur(tmp_path, state=_hazir_state(dj_clips.KESIT_MIN_ARA_SN + 3600),
                       kesit_dosyalari=("clip_01.mp4",))
    kesit, sebep = dj_clips.yayina_uygun_mu(set_dir)
    assert kesit is not None and kesit["dosya"] == "clip_01.mp4", sebep


def test_zaten_yayinlanmis_kesit_tekrar_gonderilmiyor(tmp_path):
    st = _hazir_state(dj_clips.KESIT_MIN_ARA_SN + 3600)
    st["youtube_clip_video_id"] = "xyz"
    set_dir = _set_kur(tmp_path, state=st, kesit_dosyalari=("clip_01.mp4",))
    kesit, sebep = dj_clips.yayina_uygun_mu(set_dir)
    assert kesit is None and "zaten" in sebep


def test_content_id_engelli_set_kesit_yayinlamiyor(tmp_path):
    st = _hazir_state(dj_clips.KESIT_MIN_ARA_SN + 3600)
    st["dj_tarama_engelli"] = True
    set_dir = _set_kur(tmp_path, state=st, kesit_dosyalari=("clip_01.mp4",))
    kesit, sebep = dj_clips.yayina_uygun_mu(set_dir)
    assert kesit is None and "engel" in sebep


def test_tarama_temiz_degilse_kesit_yayinlamiyor(tmp_path):
    st = _hazir_state(dj_clips.KESIT_MIN_ARA_SN + 3600)
    st.pop("dj_tarama_temiz")
    set_dir = _set_kur(tmp_path, state=st, kesit_dosyalari=("clip_01.mp4",))
    kesit, sebep = dj_clips.yayina_uygun_mu(set_dir)
    assert kesit is None and "tarama" in sebep.lower()


# --- Süpürge: hacim kısıtı -------------------------------------------------


def test_supurge_kosu_basina_tek_kesit(tmp_path, monkeypatch):
    """İki set birden hazır olsa bile TEK koşuda tek kesit çıkmalı."""
    for ad in ("Set A", "Set B"):
        _set_kur(tmp_path, ad=ad, state=_hazir_state(dj_clips.KESIT_MIN_ARA_SN + 3600),
                 kesit_dosyalari=("clip_01.mp4",))

    cagrilar = []
    monkeypatch.setattr(dj_clips, "kesit_yayinla",
                        lambda set_dir, kesit, **kw: cagrilar.append(set_dir))
    sonuc = dj_clips.supur(str(tmp_path), log=lambda *a: None)

    assert sonuc["yayinlanan"] == 1
    assert len(cagrilar) == 1


def test_supurge_haftalik_kuresel_tempoyu_uyguluyor(tmp_path, monkeypatch):
    """Bir kesit YENİ yayınlandıysa (başka bir sette bile olsa) bu koşuda
    ikincisi çıkmamalı — üst sınır haftada +1 yükleme."""
    dun = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() - 86400))
    st_yeni = _hazir_state(dj_clips.KESIT_MIN_ARA_SN + 3600)
    st_yeni["youtube_clip_video_id"] = "zzz"
    st_yeni["youtube_clip_uploaded_at"] = dun
    _set_kur(tmp_path, ad="Set A", state=st_yeni, kesit_dosyalari=("clip_01.mp4",))
    _set_kur(tmp_path, ad="Set B", state=_hazir_state(dj_clips.KESIT_MIN_ARA_SN + 3600),
             kesit_dosyalari=("clip_01.mp4",))

    cagrilar = []
    monkeypatch.setattr(dj_clips, "kesit_yayinla",
                        lambda set_dir, kesit, **kw: cagrilar.append(set_dir))
    sonuc = dj_clips.supur(str(tmp_path), log=lambda *a: None)

    assert sonuc["yayinlanan"] == 0
    assert cagrilar == []


def test_supurge_alt_cizgili_klasorleri_atliyor(tmp_path):
    """dj_sets/_arda gibi yardımcı klasörler set değil."""
    d = tmp_path / "_arda"
    d.mkdir()
    assert dj_clips._set_klasorleri(str(tmp_path)) == []
    assert os.path.isdir(str(d))
