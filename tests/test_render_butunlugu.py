# -*- coding: utf-8 -*-
"""Yarım render'ın "hazır" sayılmasına karşı koruma (2026-09-12).

ARIZA: `_is_rendered()` bir videonun hazır olup olmadığını YALNIZCA
`os.path.isfile` ile belirliyordu (`auto_process.py`, `dj_famous_process.py`).
ffmpeg `-y` ile DOĞRUDAN nihai dosyaya yazdığı için yarıda kesilen bir render
diskte "yarım ama VAR" bir .mp4 bırakıyor: `isfile` True diyor, bir sonraki
koşu render'ı ATLIYOR ve BOZUK videoyu altı platforma yüklüyor. Log'da yalnızca
"Zaten render edilmiş" yazdığı için arıza SESSİZ.

Tetikleyicilerden biri (izleyicinin 5 dakikada süreci öldürmesi) 2026-09-12'de
`watch_projects.py`'de kapatıldı; SEBEP ise iki ayrı yerde kapatıldı ve bu dosya
ikisini birden kilitliyor:

  (a) `render.video_butun_mu()` — 0 bayt kapısı + ffprobe süre doğrulaması,
      ffprobe çalıştırılamıyorsa zarif düşüş. DİSKTE ŞU AN duran (atomik
      yazımdan ÖNCE üretilmiş) yarım dosyaları da yakalayan tek taraf.
  (b) `render.render_one()` — çıktı geçici ada yazılıp `os.replace` ile
      taşınıyor (state_io.py deseni). Yarım dosya nihai adla HİÇ var olmuyor.

(a) ve (b) birbirinin yerine geçmiyor: (b) yalnızca ileriye dönük, (a) ise
`os.replace`'in kapsamadığı her şeyi (eski çıktılar, sonradan bozulma, elle
kopyalama) kapsıyor.
"""

import os
import shutil
import subprocess

import pytest

import auto_process
import dj_famous_process
import render


# ---------------------------------------------------------------------------
# Fikstürler — gerçek bir mp4 üretiliyor, taklit değil
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def saglam_mp4(tmp_path_factory):
    """GERÇEK, ffprobe ile okunabilen küçük bir mp4 (1 sn, 128x72).

    Taklit bayt dizisi YETMEZ: bu dosyanın işi, bozuk vakaların TÜREDİĞİ
    sağlam kaynağı sağlamak — yarım dosya bunun ilk N baytı olarak üretiliyor.
    """
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("ffmpeg/ffprobe bu makinede yok")
    yol = tmp_path_factory.mktemp("render_butunlugu") / "saglam.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y",
         "-f", "lavfi", "-i", "testsrc=duration=1:size=128x72:rate=10",
         "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
         "-t", "1", "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-c:a", "aac", str(yol)],
        check=True, capture_output=True)
    assert yol.stat().st_size > 0
    return str(yol)


@pytest.fixture
def yarim_mp4(saglam_mp4, tmp_path):
    """Sağlam mp4'ün ilk %40'ı — ÖLDÜRÜLMÜŞ bir render'ın diskte bıraktığı şey.

    Neden bu güvenilir bir ölçüt: ffmpeg `moov` atom'unu dosyanın SONUNA
    yazıyor, yani kesik bir mp4'te o atom ASLA bulunmuyor ve ffprobe
    `moov atom not found` ile rc=1 dönüyor (%1/%10/%50/%90 kesme oranlarıyla
    ölçüldü, dördü de rc=1).
    """
    ham = open(saglam_mp4, "rb").read()
    yol = tmp_path / "yarim.mp4"
    yol.write_bytes(ham[:int(len(ham) * 0.4)])
    return str(yol)


def _cikti_kur(proje_dir, kaynaklar):
    """`<proje>/output/` altına RENDER_OUTPUTS adlarıyla dosya yerleştirir.

    `kaynaklar`: her çıktı adı için ya bayt dizisi ya da kopyalanacak dosya yolu.
    """
    out = os.path.join(str(proje_dir), "output")
    os.makedirs(out, exist_ok=True)
    for ad, kaynak in zip(auto_process.RENDER_OUTPUTS, kaynaklar):
        hedef = os.path.join(out, ad)
        if isinstance(kaynak, bytes):
            open(hedef, "wb").write(kaynak)
        else:
            shutil.copyfile(kaynak, hedef)
    return str(proje_dir)


# ---------------------------------------------------------------------------
# A — video_butun_mu(): tek dosya düzeyindeki ölçüt
# ---------------------------------------------------------------------------

def test_olmayan_dosya_butun_degil(tmp_path):
    assert render.video_butun_mu(str(tmp_path / "yok.mp4")) is False


def test_sifir_bayt_dosya_ffprobe_calismadan_reddediliyor(tmp_path, monkeypatch):
    """0 bayt EN SIK vaka (süreç muxer'ı açar açmaz ölmüşse dosya boştur) ve
    ffprobe'a hiç girmeden reddedilmeli — boşuna süreç başlatmak yok."""
    yol = tmp_path / "bos.mp4"
    yol.write_bytes(b"")

    cagri = []
    monkeypatch.setattr(render.ffmpeg_utils, "get_audio_duration",
                        lambda p: cagri.append(p))

    assert render.video_butun_mu(str(yol)) is False
    assert cagri == []


def test_yarim_dosya_butun_degil(yarim_mp4):
    assert render.video_butun_mu(yarim_mp4) is False


def test_saglam_dosya_butun(saglam_mp4):
    assert render.video_butun_mu(saglam_mp4) is True


def test_ortak_ffprobe_yardimcisi_kullaniliyor(saglam_mp4, monkeypatch):
    """Mantık KOPYALANMADI: ffprobe çağrısı `ffmpeg_utils.get_audio_duration`.

    Bu depoda ikinci bir ffprobe kopyası açmak belgelenmiş hata sınıfı; testin
    işi o bağın koda gömülü kalması."""
    cagri = []

    def sahte(path):
        cagri.append(path)
        return 12.5

    monkeypatch.setattr(render.ffmpeg_utils, "get_audio_duration", sahte)
    assert render.video_butun_mu(saglam_mp4) is True
    assert cagri == [saglam_mp4]


def test_sifir_sure_butun_sayilmiyor(saglam_mp4, monkeypatch):
    """Dosya açılıyor ama içi yok: ffprobe 0 süre veriyorsa çıktı kullanılamaz."""
    monkeypatch.setattr(render.ffmpeg_utils, "get_audio_duration", lambda p: 0.0)
    assert render.video_butun_mu(saglam_mp4) is False


# ---------------------------------------------------------------------------
# B — _is_rendered(): iki üretim girişinde de aynı ölçüt
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("modul", [auto_process, dj_famous_process],
                         ids=["auto_process", "dj_famous_process"])
def test_sifir_baytlik_ciktilar_hazir_sayilmiyor(modul, tmp_path):
    proje = _cikti_kur(tmp_path, [b"", b""])
    assert modul._is_rendered(proje) is False


@pytest.mark.parametrize("modul", [auto_process, dj_famous_process],
                         ids=["auto_process", "dj_famous_process"])
def test_yarim_ciktilar_hazir_sayilmiyor(modul, tmp_path, yarim_mp4):
    proje = _cikti_kur(tmp_path, [yarim_mp4, yarim_mp4])
    assert modul._is_rendered(proje) is False


@pytest.mark.parametrize("modul", [auto_process, dj_famous_process],
                         ids=["auto_process", "dj_famous_process"])
def test_saglam_ciktilar_hazir_sayiliyor(modul, tmp_path, saglam_mp4):
    proje = _cikti_kur(tmp_path, [saglam_mp4, saglam_mp4])
    assert modul._is_rendered(proje) is True


@pytest.mark.parametrize("modul", [auto_process, dj_famous_process],
                         ids=["auto_process", "dj_famous_process"])
def test_tek_bozuk_cikti_tum_projeyi_dusuruyor(modul, tmp_path, saglam_mp4, yarim_mp4):
    """`MAX_PARALLEL_RENDERS=2` ile ÖLDÜRÜLEN bir koşunun tipik izi: biri
    tamamlanmış, öbürü yarım. Yükleme altı platforma gittiği için "yarısı
    sağlam" diye bir hâl YOK."""
    proje = _cikti_kur(tmp_path, [saglam_mp4, yarim_mp4])
    assert modul._is_rendered(proje) is False


def test_ilk_bozuk_ciktida_kisa_devre(tmp_path, yarim_mp4, saglam_mp4, monkeypatch):
    """`all()` kısa devre yapıyor: ilk çıktı bozuksa ikinci ffprobe koşmuyor."""
    proje = _cikti_kur(tmp_path, [yarim_mp4, saglam_mp4])
    sayac = []
    gercek = render.ffmpeg_utils.get_audio_duration

    def sayan(path):
        sayac.append(path)
        return gercek(path)

    monkeypatch.setattr(render.ffmpeg_utils, "get_audio_duration", sayan)
    assert auto_process._is_rendered(proje) is False
    assert len(sayac) == 1


# ---------------------------------------------------------------------------
# C — ffprobe yoksa ZARİF DÜŞÜŞ + koşu başına TEK log satırı
# ---------------------------------------------------------------------------

def _ffprobe_yok(path):
    raise FileNotFoundError(2, "The system cannot find the file specified", "ffprobe")


def test_ffprobe_yoksa_eski_isfile_davranisina_dusuluyor(tmp_path, yarim_mp4, monkeypatch):
    """Sessizce SERTLEŞMEK de kötü: ffprobe'suz bir makinede her koşuda yeniden
    render etmek boru hattını sonsuz render'a sokardı. "Çalıştıramadım" ile
    "çalıştırdım, dosya bozuk" AYRI şeyler."""
    monkeypatch.setattr(render, "_FFPROBE_YOK_UYARILDI", False)
    monkeypatch.setattr(render.ffmpeg_utils, "get_audio_duration", _ffprobe_yok)
    proje = _cikti_kur(tmp_path, [yarim_mp4, yarim_mp4])

    assert auto_process._is_rendered(proje) is True


def test_ffprobe_yoksa_kosu_basina_TEK_log_satiri(tmp_path, yarim_mp4, monkeypatch):
    """Sessizce GEVŞEMEK de kötü: zarif düşüş görünür olmalı, ama koşu başına
    BİR kez (dört çıktı = dört satır, log'u dolduran gürültü demekti)."""
    monkeypatch.setattr(render, "_FFPROBE_YOK_UYARILDI", False)
    monkeypatch.setattr(render.ffmpeg_utils, "get_audio_duration", _ffprobe_yok)
    satirlar = []
    monkeypatch.setattr(auto_process, "log", satirlar.append)
    proje = _cikti_kur(tmp_path, [yarim_mp4, yarim_mp4])

    assert auto_process._is_rendered(proje) is True   # iki dosya
    assert auto_process._is_rendered(proje) is True   # ikinci proje/koşu-içi tekrar

    uyarilar = [s for s in satirlar if "ffprobe" in s]
    assert len(uyarilar) == 1, satirlar
    assert "DOĞRULANAMIYOR" in uyarilar[0]


def test_ffprobe_hatasi_bozuklukla_karistirilmiyor(saglam_mp4, monkeypatch):
    """ffprobe ÇALIŞTI ve süre veremedi (RuntimeError) -> bozukluk KANITI,
    zarif düşüş dalına GİRMEZ."""
    monkeypatch.setattr(render, "_FFPROBE_YOK_UYARILDI", False)

    def calisti_ama_okuyamadi(path):
        raise RuntimeError("ffprobe süre okuyamadı: moov atom not found")

    monkeypatch.setattr(render.ffmpeg_utils, "get_audio_duration", calisti_ama_okuyamadi)
    assert render.video_butun_mu(saglam_mp4) is False
    assert render._FFPROBE_YOK_UYARILDI is False


# ---------------------------------------------------------------------------
# D — ÖNBELLEK YOK: sonuç her çağrıda diskten
# ---------------------------------------------------------------------------

def test_sonuc_onbelleklenmiyor_dosya_duzelince_taze_okunuyor(tmp_path, yarim_mp4, saglam_mp4):
    """Önbellek EKLENMEDİ (gerekçe `video_butun_mu` docstring'inde: koşu başına
    ~0,15 sn). Bu test kararı kilitliyor: aynı süreç içinde dosya düzeldiğinde
    sonuç DERHAL tazeleniyor. Bir gün önbellek eklenirse (mtime+boyut
    anahtarıyla) bu test onun tazeleme testi olur."""
    proje = _cikti_kur(tmp_path, [yarim_mp4, yarim_mp4])
    assert auto_process._is_rendered(proje) is False

    # Render yeniden koştu, çıktılar artık bütün.
    _cikti_kur(tmp_path, [saglam_mp4, saglam_mp4])
    assert auto_process._is_rendered(proje) is True

    # Ve ters yön de anında görülüyor (dosya sonradan bozulursa).
    _cikti_kur(tmp_path, [saglam_mp4, yarim_mp4])
    assert auto_process._is_rendered(proje) is False


# ---------------------------------------------------------------------------
# E — render.py: geçici ada yaz, os.replace ile taşı
# ---------------------------------------------------------------------------

def _render_projesi_kur(tmp_path, monkeypatch, sahte_render):
    """`render_project()`'i GERÇEK ffmpeg olmadan koşturulabilir hâle getirir.

    CANLI RENDER YASAK (saatler sürer), bu yüzden yalnızca `render_video`
    taklit ediliyor — test edilen mantık (`render_one`'ın geçici ad + replace
    akışı) GERÇEK kod olarak koşuyor.
    """
    (tmp_path / "audio.wav").write_bytes(b"RIFF0000WAVE")
    (tmp_path / "cover.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (tmp_path / "meta.json").write_text('{"title": "Test", "theme": "pop"}',
                                        encoding="utf-8")

    monkeypatch.setattr(render.validate_project, "validate", lambda d: ([], []))
    monkeypatch.setattr(render.validate_project, "print_report",
                        lambda d, e, u: None)
    monkeypatch.setattr(render, "find_highlight", lambda a, s: (0.0, 5.0))
    monkeypatch.setattr(render.ffmpeg_utils, "ensure_card_mask", lambda: None)
    monkeypatch.setattr(render.ffmpeg_utils, "ensure_art_backdrop",
                        lambda *a, **k: None)
    monkeypatch.setattr(render.ffmpeg_utils, "ensure_vignette",
                        lambda *a, **k: None)
    monkeypatch.setattr(render.ffmpeg_utils, "render_video", sahte_render)
    return str(tmp_path)


def test_render_gecici_ada_yazip_os_replace_ile_tasiyor(tmp_path, monkeypatch):
    """ffmpeg NİHAİ adı HİÇ görmemeli — gördüğü an yarım dosya o adla diskte
    var olabilir demektir."""
    yazilanlar = []

    def sahte_render(art, audio, output_path, *a, **k):
        yazilanlar.append(output_path)
        # ffmpeg gibi: dosyayı kademeli yaz.
        open(output_path, "wb").write(b"\x00" * 1024)

    proje = _render_projesi_kur(tmp_path, monkeypatch, sahte_render)
    assert render.render_project(proje) is True

    out = tmp_path / "output"
    for ad in auto_process.RENDER_OUTPUTS:
        assert (out / ad).is_file()
    # ffmpeg'e verilen yolların HİÇBİRİ nihai ad değil.
    assert yazilanlar and all(y.endswith(render.PARCALI_SONEK) for y in yazilanlar)
    assert not any(os.path.basename(y) in auto_process.RENDER_OUTPUTS
                   for y in yazilanlar)
    # Geçici dosya geride kalmıyor.
    assert [f for f in os.listdir(out) if f.endswith(render.PARCALI_SONEK)] == []


def test_render_yarida_kesilirse_nihai_ad_hic_olusmuyor(tmp_path, monkeypatch):
    """Arızanın KÖKÜ: eskiden bu senaryo diskte `youtube_16x9.mp4` adıyla
    yarım bir dosya bırakıyordu ve bir sonraki koşu onu "hazır" sayıyordu."""

    def olen_render(art, audio, output_path, *a, **k):
        open(output_path, "wb").write(b"\x00" * 1024)   # yarım çıktı
        raise RuntimeError("render öldürüldü (ExecutionTimeLimit / güç kesintisi)")

    proje = _render_projesi_kur(tmp_path, monkeypatch, olen_render)
    assert render.render_project(proje) is False

    out = tmp_path / "output"
    kalanlar = os.listdir(out)
    assert [f for f in kalanlar if f in auto_process.RENDER_OUTPUTS] == [], kalanlar
    # Geçici dosya da temizlendi (süreç ÖLDÜRÜLSEYDİ kalırdı — ama o zaman da
    # adı nihai ad DEĞİL, yani hiçbir adımı yanıltmaz).
    assert [f for f in kalanlar if f.endswith(render.PARCALI_SONEK)] == [], kalanlar

    # Ve _is_rendered bu projeyi hazır SAYMIYOR.
    assert auto_process._is_rendered(proje) is False


def test_gecici_ad_platform_basina_AYRI(tmp_path, monkeypatch):
    """`MAX_PARALLEL_RENDERS=2`: iki render aynı anda koşuyor, aynı geçici
    dosyaya yazarlarsa ikisi de bozulur."""
    yazilanlar = []

    def sahte_render(art, audio, output_path, *a, **k):
        yazilanlar.append(output_path)
        open(output_path, "wb").write(b"\x00" * 16)

    proje = _render_projesi_kur(tmp_path, monkeypatch, sahte_render)
    assert render.render_project(proje) is True
    assert len(yazilanlar) == len(set(yazilanlar)) >= 2
