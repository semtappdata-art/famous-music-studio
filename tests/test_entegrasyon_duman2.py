# -*- coding: utf-8 -*-
"""İKİNCİ entegrasyon duman testi — ilk duman koşusundan (2026-09-11 ~18:00)
SONRA değişen iki alanın modüller ARASINDAKİ sözleşmeleri.

NEDEN AYRI BİR DOSYA: `tests/test_entegrasyon_duman.py` ilk koşunun bulduğu üç
arızayı koruyor ve DEĞİŞTİRİLMEDİ. Ondan sonra iki büyük değişiklik geldi ve
ikisi de tam olarak bu deponun "bağlantı seviyesinde sessiz arıza" sınıfından:

  1. AÇILIŞ (config.INTRO_KAPAK): render'a YENİ BİR GİRDİ eklendi. ffmpeg'in
     girdi indeksleri POZİSYONEL — `render_video()` `intro_index`'i kendi
     aritmetiğiyle hesaplıyor (`hud_index + 1`, ya da `4 if has_art else 3`),
     `cmd` listesini ise AYRI bir yerde kuruyor. İkisi ayrışırsa filtre grafiği
     YANLIŞ akışı okur: ya "Cannot find a matching stream" ile patlar, ya da
     — daha kötüsü — sessizce yanlış görseli gösterir. Mevcut
     `tests/test_acilis_intro.py` filtre grafiğinin KENDİ iç tutarlılığını
     doğruluyor; burada grafik ile `-i` SIRASI karşılaştırılıyor (dört dalın
     dördünde de).
  2. KÖK LİSTELERİ (uyumluluk.KOK_ADLARI / KOKLER / proje_klasorleri): kanonik
     kaynak kuruldu ve modüller ona bağlandı. `tests/test_kok_listesi_muhafizi.py`
     kaynak taramasını + üç düzeltilmiş fonksiyonun davranışını koruyor; burada
     geri doldurma / doğrulama / ölçüm hattındaki DÖRT modülün sahte bir
     `derlemeler/` projesini gerçekten GÖRDÜĞÜ doğrulanıyor.

AĞA ÇIKMIYOR, hiçbir platforma yükleme yapmıyor, gerçek `projects/`,
`dj_sets/`, `derlemeler/` klasörlerine DOKUNMUYOR.
"""

import ast
import json
import os
import shutil
import subprocess
import sys

import pytest

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _KOK)
sys.path.insert(0, os.path.join(_KOK, "upload"))

import config          # noqa: E402
import ffmpeg_utils    # noqa: E402
import uyumluluk       # noqa: E402


# ===========================================================================
# 1. AÇILIŞ — filtre grafiğindeki girdi indeksi ile gerçek `-i` sırası
# ===========================================================================

def _komutu_yakala(monkeypatch, _sure=180.0, **kw):
    """render_video()'yu ffmpeg'i ÇALIŞTIRMADAN koşturur; `cmd`'yi döndürür.

    `get_audio_duration`/`bastaki_sessizlik` de sahteleniyor — bu test girdi
    SIRASINI doğruluyor, ses çözümlemesini değil."""
    yakalanan = {}

    class _Sonuc:
        returncode = 0
        stderr = ""

    def sahte_run(cmd, *a, **kwargs):
        yakalanan["cmd"] = list(cmd)
        return _Sonuc()

    monkeypatch.setattr(ffmpeg_utils.subprocess, "run", sahte_run)
    monkeypatch.setattr(ffmpeg_utils, "get_audio_duration", lambda p: _sure)
    monkeypatch.setattr(ffmpeg_utils, "bastaki_sessizlik", lambda p: 0.0)
    # Önbellek üreten yardımcılar diske/ffmpeg'e gitmesin.
    monkeypatch.setattr(ffmpeg_utils, "ensure_card_mask", lambda: "assets/m.png")
    monkeypatch.setattr(ffmpeg_utils, "ensure_art_backdrop",
                        lambda a, w, h: "assets/bd.png")
    monkeypatch.setattr(ffmpeg_utils, "ensure_vignette",
                        lambda w, h, t: "assets/vg.png")
    # DİKKAT: `os.path.isfile` GENEL olarak True'ya sabitlenmiyor. Bu makinede
    # gerçek token dosyaları duruyor ve "her yol var" diyen bir sahte, başka bir
    # modülde (yükleyiciler) yanlış bir dala girebilir. Sadece bu testin verdiği
    # sahte yollar True dönüyor, geri kalan her şey GERÇEK diske soruluyor.
    _gercek_isfile = os.path.isfile
    _sahte_yollar = {"proje/art.jpg", "proje/audio.wav", "proje/cover.png",
                     "proje/backdrop.mp4", "assets/hud.png", "assets/m.png",
                     "assets/bd.png", "assets/vg.png",
                     "c.png", "h.png", "b.mp4"}
    monkeypatch.setattr(os.path, "isfile",
                        lambda p: str(p) in _sahte_yollar or _gercek_isfile(p))

    varsayilan = dict(art_path="proje/art.jpg", audio_path="proje/audio.wav",
                      output_path="out.mp4", width=1920, height=1080,
                      title="Test", theme=config.DEFAULT_THEME)
    varsayilan.update(kw)
    ffmpeg_utils.render_video(**varsayilan)
    return yakalanan["cmd"]


def _girdi_yollari(cmd):
    """`-i <yol>` çiftlerini SIRAYLA döndürür — ffmpeg'in girdi indeksleri
    tam olarak bu listenin indeksleri."""
    return [cmd[i + 1] for i, a in enumerate(cmd) if a == "-i"]


@pytest.mark.parametrize("etiket, kw, beklenen_sira", [
    # (art var, HUD yok) — ana kataloğun uzun formatı
    ("art+intro", dict(intro_cover="proje/cover.png"),
     ["proje/audio.wav", "assets/m.png", "assets/bd.png", "proje/art.jpg",
      "proje/cover.png"]),
    # (art var, HUD var) — kart + HUD + video backdrop (DJ, kart AÇIK)
    ("art+hud+intro", dict(intro_cover="proje/cover.png",
                           hud_path="assets/hud.png",
                           backdrop_video="proje/backdrop.mp4"),
     ["proje/audio.wav", "assets/m.png", "proje/backdrop.mp4", "proje/art.jpg",
      "assets/hud.png", "proje/cover.png"]),
    # (kart KAPALI -> has_art False, HUD var) — DJ sahne modu
    ("sahne+hud+intro", dict(intro_cover="proje/cover.png",
                             hud_path="assets/hud.png",
                             backdrop_video="proje/backdrop.mp4",
                             kart_goster=False),
     ["proje/audio.wav", "assets/m.png", "proje/backdrop.mp4", "assets/hud.png",
      "proje/cover.png"]),
    # (art YOK, HUD yok) — kart tek başına, vignette fallback
    ("artsiz+intro", dict(art_path=None, intro_cover="proje/cover.png"),
     ["proje/audio.wav", "assets/m.png", "assets/vg.png", "proje/cover.png"]),
])
def test_intro_girdi_indeksi_gercek_i_sirasiyla_ayni(etiket, kw, beklenen_sira,
                                                     monkeypatch):
    """ASIL RİSK: `intro_index` aritmetiği (`hud_index + 1` / `4 if has_art`)
    ile `cmd` kurulumu AYRI iki yerde. Ayrışırlarsa filtre grafiği yanlış
    akışı okur."""
    cmd = _komutu_yakala(monkeypatch, **kw)
    yollar = _girdi_yollari(cmd)
    assert yollar == beklenen_sira, "%s: girdi sırası beklenenden farklı" % etiket

    fc = cmd[cmd.index("-filter_complex") + 1]
    intro_idx = yollar.index("proje/cover.png")
    assert "[%d:v]" % intro_idx in fc, (
        "%s: açılış girdisi %d. sırada ama grafik [%d:v] okumuyor — "
        "ffmpeg 'Cannot find a matching stream' verir ya da YANLIŞ akışı çizer"
        % (etiket, intro_idx, intro_idx))
    if "assets/hud.png" in yollar:
        hud_idx = yollar.index("assets/hud.png")
        assert "[%d:v]scale=" % hud_idx in fc, (
            "%s: HUD girdisi %d. sırada ama grafik onu okumuyor" % (etiket, hud_idx))
    # Kapak dalı ile HUD dalı AYNI indeksi okumamalı.
    assert intro_idx != (yollar.index("assets/hud.png")
                         if "assets/hud.png" in yollar else -1)


def test_intro_girdisi_her_zaman_EN_SONDA(monkeypatch):
    """Açılış girdisi araya girerse HUD'un indeksini kaydırır (kodun kendi
    notu). Bu iddia dördü de kapsayan tek satırlık muhafız."""
    for kw in (dict(intro_cover="c.png"),
               dict(intro_cover="c.png", hud_path="h.png",
                    backdrop_video="b.mp4"),
               dict(intro_cover="c.png", hud_path="h.png",
                    backdrop_video="b.mp4", kart_goster=False),
               dict(intro_cover="c.png", art_path=None)):
        yollar = _girdi_yollari(_komutu_yakala(monkeypatch, **kw))
        assert yollar[-1] == "c.png", "açılış girdisi sonda değil: %s" % yollar


# ---------------------------------------------------------------------------
# Kapaksız proje: SESSİZCE eski davranışa düşmeli (çökmemeli)
# ---------------------------------------------------------------------------

def test_kapak_dosyasi_YOKKEN_intro_sessizce_atlaniyor(monkeypatch):
    """`intro_cover` verilmiş ama dosya diskte yoksa (ör. cover.png silinmiş /
    henüz üretilmemiş) render DURMAMALI — açılışsız eski kompozisyona düşmeli."""
    gercek_isfile = os.path.isfile

    def sahte_isfile(p):
        if str(p).endswith("cover.png"):
            return False
        return True

    yakalanan = {}

    class _Sonuc:
        returncode = 0
        stderr = ""

    monkeypatch.setattr(ffmpeg_utils.subprocess, "run",
                        lambda cmd, *a, **k: (yakalanan.update(cmd=list(cmd)), _Sonuc())[1])
    monkeypatch.setattr(ffmpeg_utils, "get_audio_duration", lambda p: 180.0)
    monkeypatch.setattr(ffmpeg_utils, "bastaki_sessizlik", lambda p: 0.0)
    monkeypatch.setattr(ffmpeg_utils, "ensure_card_mask", lambda: "assets/m.png")
    monkeypatch.setattr(ffmpeg_utils, "ensure_art_backdrop",
                        lambda a, w, h: "assets/bd.png")
    monkeypatch.setattr(os.path, "isfile", sahte_isfile)

    ffmpeg_utils.render_video("proje/art.jpg", "proje/audio.wav", "out.mp4",
                              1920, 1080, title="T", theme=config.DEFAULT_THEME,
                              intro_cover="proje/cover.png")
    cmd = yakalanan["cmd"]
    assert "proje/cover.png" not in _girdi_yollari(cmd)
    fc = cmd[cmd.index("-filter_complex") + 1]
    assert "[intro]" not in fc and "vpre" not in fc
    assert fc.count("[vfinal]") == 1
    assert gercek_isfile(os.path.join(_KOK, "ffmpeg_utils.py"))   # monkeypatch geri alındı mı


def test_kapaksiz_projede_find_intro_cover_None(tmp_path):
    """render.py tarafı: kapak hiç yoksa None — ve YATAY kapak varken DİKEY
    istendiğinde de None (bilerek geri düşmüyor; Shorts zaten açılış
    kullanmıyor)."""
    import render
    assert render.find_intro_cover(str(tmp_path), 1920, 1080) is None
    assert render.find_intro_cover(str(tmp_path), 1080, 1920) is None
    (tmp_path / "cover.png").write_bytes(b"x")
    assert render.find_intro_cover(str(tmp_path), 1920, 1080) == \
        str(tmp_path / "cover.png")
    assert render.find_intro_cover(str(tmp_path), 1080, 1920) is None


def test_shorts_platformu_acilisa_HIC_girmiyor():
    """Açılış yalnızca uzun formatta. Bu küme genişlerse dikey kapak yolunun
    da test edilmesi gerekir — o yüzden sözleşme burada sabitleniyor."""
    assert config.INTRO_KAPAK_PLATFORMLAR == {"youtube_16x9"}
    assert "shorts_9x16" in config.PLATFORMS
    assert "shorts_9x16" not in config.INTRO_KAPAK_PLATFORMLAR


# ---------------------------------------------------------------------------
# Çok kısa parça: atlama SINIRI (>= 2x) — sınırın TAM ÜSTÜ de dahil
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("sure, beklenen", [
    (4.79, False),   # sınırın hemen ALTI  -> açılış YOK
    (4.80, True),    # TAM sınır (>=)      -> açılış VAR
    (4.81, True),
])
def test_kisa_parca_siniri_tam_olarak_iki_kati(sure, beklenen, monkeypatch):
    toplam = config.INTRO_KAPAK_BEKLEME + config.INTRO_KAPAK_COZULME
    assert abs(toplam * 2 - 4.8) < 1e-9, "sınır config'den geliyor; sabitler değişmiş"
    cmd = _komutu_yakala(monkeypatch, _sure=sure, intro_cover="proje/cover.png")
    var = "proje/cover.png" in _girdi_yollari(cmd)
    assert var is beklenen, "süre %.2f sn: açılış %s olmalıydı" % (
        sure, "VAR" if beklenen else "YOK")


# ---------------------------------------------------------------------------
# Sessizlik kırpması: video süresi = ses süresi - (sessizlik - PAY)
# ---------------------------------------------------------------------------

def _ffmpeg_var():
    try:
        subprocess.run(["ffprobe", "-version"], capture_output=True)
        return True
    except OSError:
        return False


@pytest.mark.skipif(not _ffmpeg_var(), reason="ffprobe yok")
def test_sessizlik_kirpmasi_sureyi_TAM_beklenen_kadar_kisaltiyor(tmp_path):
    """Ses süresiyle video süresi BİREBİR AYNI DEĞİL — fark tam olarak
    kırpılan sessizlik kadar olmalı. "Kısa olmuş" demek yetmiyor: yanlış bir
    kırpma (ör. tavanın uygulanmaması) da kısa yapardı."""
    ses = tmp_path / "audio.wav"
    subprocess.run([
        "ffmpeg", "-v", "error", "-y",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=6",
        "-af", "adelay=1500|1500", "-ar", "44100", "-ac", "2", str(ses),
    ], check=True)
    art = tmp_path / "art.jpg"
    kapak = tmp_path / "cover.png"
    for p in (art, kapak):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
                        "-i", "testsrc=size=160x160:duration=1:rate=1",
                        "-frames:v", "1", "-update", "1", str(p)], check=True)

    ses_sn = ffmpeg_utils.get_audio_duration(str(ses))
    kirp = ffmpeg_utils.bastaki_sessizlik(str(ses))
    assert kirp > 0, "sessizlik hiç tespit edilmedi"

    cikti = tmp_path / "out.mp4"
    ffmpeg_utils.render_video(str(art), str(ses), str(cikti), 320, 180,
                              title="T", theme=config.DEFAULT_THEME,
                              intro_cover=str(kapak))
    video_sn = ffmpeg_utils.get_audio_duration(str(cikti))
    beklenen = ses_sn - kirp
    assert abs(video_sn - beklenen) < 0.15, (
        "video %.3f sn; beklenen %.3f sn (ses %.3f - kırpma %.3f)"
        % (video_sn, beklenen, ses_sn, kirp))


# ===========================================================================
# 2. KÖK LİSTELERİ — sahte bir `derlemeler/` projesi görülüyor mu
# ===========================================================================

def _uc_kok(tmp_path, proje_koku="derlemeler", state=None, dosyalar=()):
    """tmp_path altında ÜÇ kökü de kurar; projeyi yalnızca `proje_koku`'ne koyar.

    Böylece "sadece projects/'e bakan" bir fonksiyon boş liste döner ve test
    kırmızı yanar — kök listesinin gerçekten genişlediğini kanıtlar."""
    kokler = []
    for ad in uyumluluk.KOK_ADLARI:
        k = tmp_path / ad
        k.mkdir()
        kokler.append(str(k))
    p = tmp_path / proje_koku / "gece_seansi_vol1"
    p.mkdir()
    (p / "meta.json").write_text(json.dumps({"title": "Gece Seansı Vol. 1",
                                             "theme": "hiphop",
                                             "derleme": True}),
                                 encoding="utf-8")
    (p / "state.json").write_text(json.dumps(state or {}), encoding="utf-8")
    for rel in dosyalar:
        hedef = p / rel
        hedef.parent.mkdir(parents=True, exist_ok=True)
        hedef.write_bytes(b"0" * 2048)
    return tuple(kokler), str(p)


def test_facebook_backfill_varsayilani_kanonik_koke_bagli():
    """`BASE` import ANINDA çözülüyor — bir daha `uyumluluk.KOKLER`'e
    bakılmıyor. O yüzden kimlik (is) doğrulanıyor, kopya değil."""
    import facebook_backfill
    import ek_platform_backfill
    assert facebook_backfill.BASE is uyumluluk.KOKLER
    assert ek_platform_backfill.BASE is uyumluluk.KOKLER
    assert "derlemeler" in uyumluluk.KOK_ADLARI
    assert all(os.path.isabs(k) for k in uyumluluk.KOKLER)


def test_facebook_backfill_derlemeyi_goruyor(tmp_path, monkeypatch):
    import facebook_backfill
    kokler, proje = _uc_kok(
        tmp_path,
        state={"youtube_video_id": "vidD", "youtube_uploaded_at": "2026-09-10"},
        dosyalar=("output/shorts_9x16.mp4",))
    monkeypatch.setattr(facebook_backfill, "BASE", kokler)
    assert facebook_backfill.eksik_projeler() == [proje]


def test_facebook_gunluk_sayac_derlemeyi_de_sayiyor(tmp_path, monkeypatch):
    import facebook_backfill
    import time as _t
    kokler, _ = _uc_kok(
        tmp_path,
        state={"facebook_uploaded_at": _t.strftime("%Y-%m-%d") + "T10:00:00"})
    monkeypatch.setattr(facebook_backfill, "BASE", kokler)
    assert facebook_backfill.bugun_yuklenen() == 1, (
        "günlük tavan sayacı derlemeleri saymıyor — eksik sayan bir tavan, "
        "olmayan tavandan farksız")


def test_ek_platform_backfill_derlemeyi_goruyor(tmp_path, monkeypatch):
    import ek_platform_backfill
    kokler, proje = _uc_kok(
        tmp_path,
        state={"youtube_video_id": "vidD", "youtube_uploaded_at": "2026-09-10"},
        dosyalar=("output/shorts_9x16.mp4",))
    monkeypatch.setattr(ek_platform_backfill, "BASE", kokler)
    assert ek_platform_backfill.eksik_projeler(
        "telegram_message_id", "output/shorts_9x16.mp4") == [proje]


def test_validate_project_all_derlemeleri_de_tariyor(tmp_path, monkeypatch, capsys):
    """`--all` kanonik `uyumluluk.proje_klasorleri()`'ni ÇAĞIRMA ANINDA
    okuyor (modül düzeyinde kopyalamıyor) — monkeypatch bu yüzden yeterli."""
    import validate_project
    kokler, proje = _uc_kok(tmp_path, state={})
    monkeypatch.setattr(uyumluluk, "KOKLER", kokler)
    monkeypatch.setattr(sys, "argv", ["validate_project.py", "--all"])
    with pytest.raises(SystemExit):
        validate_project.main()
    cikti = capsys.readouterr().out
    assert "gece_seansi_vol1" in cikti, (
        "validate_project --all derlemeleri hiç görmüyor")


def test_youtube_analytics_derlemeyi_kok_adiyla_topluyor(tmp_path, monkeypatch):
    import youtube_analytics
    kokler, _ = _uc_kok(tmp_path, state={"youtube_video_id": "vidD"})
    monkeypatch.setattr(youtube_analytics, "KOKLER", kokler)
    harita = youtube_analytics._video_idler()
    assert "vidD" in harita, "ölçüm hattı derlemeleri hiç görmüyor"
    assert harita["vidD"][0] == "derlemeler", (
        "kök adı tam yol olarak dönüyor — rapor() tablosu bozulur")


# ===========================================================================
# 3. PLAYLIST SIRASI — ana katalog hattında da Shorts'tan SONRA senkron var
# ===========================================================================

def _cagri_satirlari(dosya, fonksiyon_adi, isimler):
    agac = ast.parse(open(os.path.join(_KOK, dosya), encoding="utf-8").read())
    fn = next(d for d in ast.walk(agac)
              if isinstance(d, ast.FunctionDef) and d.name == fonksiyon_adi)
    bulunan = {ad: [] for ad in isimler}
    for d in ast.walk(fn):
        if isinstance(d, ast.Call) and isinstance(d.func, ast.Name) \
                and d.func.id in bulunan:
            bulunan[d.func.id].append(d.lineno)
    return bulunan


def test_auto_process_de_shorts_SONRASI_senkron_var():
    """`tests/test_entegrasyon_duman.py` bunu `dj_famous_process` için
    doğruluyor; ARIZA İKİ DOSYADAYDI (bkz. CLAUDE.md) — ana katalog hattı da
    aynı korumayı hak ediyor. Davranış tarafı:
    tests/test_playlist_shorts_sirasi.py."""
    s = _cagri_satirlari("auto_process.py", "process_project",
                         ("yt_upload_short", "yt_sync_playlist"))
    shorts = s["yt_upload_short"]
    playlist = s["yt_sync_playlist"]
    assert shorts, "process_project içinde Shorts yükleme çağrısı bulunamadı"
    assert len(playlist) >= 2, (
        "process_project içinde %d playlist senkronu var; Shorts ÖNCESİ ve "
        "SONRASI olmak üzere en az iki tane olmalı" % len(playlist))
    assert any(p > max(shorts) for p in playlist), (
        "playlist senkronu yalnızca Shorts yüklemesinden ÖNCE — o an "
        "youtube_shorts_video_id state'te yok, Short listeye girmez")
    assert any(p < min(shorts) for p in playlist), (
        "Shorts ÖNCESİNDEKİ senkron kaybolmuş — Content ID karantinasındaki "
        "uzun format hiçbir listeye girmez")
