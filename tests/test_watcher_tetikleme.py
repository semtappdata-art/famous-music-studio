# -*- coding: utf-8 -*-
"""`watch_projects.py`'nin ÜÇ arızası için koruma testleri (2026-09-12).

Üçü ayrı ayrı değil, TEK BİR ZİNCİR olarak ölçüldü:

  1. Her tarama 84 saniye sürüyordu. Sebep tek satırlık bir AD LİSTESİ eksiği:
     `COVER_NAMES` `cover_vertical.png`'yi tanımıyordu, oysa kapak İKİ ayrı
     oranda üretiliyor (CLAUDE.md, `generate_cover.py`). Boru hattının kendi
     ürettiği 21 dosya her koşuda "sahipsiz görsel" sayılıyor, her biri için
     `_is_stable()` 3 saniye uyuyordu. Buna `dj_sets/_arda` (proje OLMAYAN,
     `_` ön ekli ham fotoğraf klasörü) taranmaya devam ettiği için 8 dosya
     daha ekleniyordu.
  2. İzleyici görevinin `ExecutionTimeLimit`'i bugün 2 saatten 5 DAKİKAya
     çekildi ("tarama saniyeler sürer" varsayımıyla).
  3. `_trigger_script()` ENGELLİYORDU (`subprocess.run`): tetiklenen
     `auto_process.py` bitene kadar bekliyordu, ve tek bir şarkının render'ı
     tek başına 2 dk 26 sn ölçüldü.

Yani watcher yeni bir parça görüp tetiklediği anda koşu 5. dakikada
`TerminateProcess` ile ÖLDÜRÜLÜYORDU: kilit ortada kalıyor (saatlik hat 4 saat
duruyor), yarım mp4'ler diskte "var" görünüyor, sarmalayıcı izinde BAŞLADI var
BİTTİ yok.

Bu dosya bu üç düzeltmenin HER BİRİNİ, ve ikisinin yan etkilerini kilitliyor.
"""

import os
import subprocess
import sys

import pytest

import watch_projects as wp


# ---------------------------------------------------------------------------
# A — "sahipsiz görsel" kuralı: DESEN, liste değil
# ---------------------------------------------------------------------------

def test_dikey_kapak_artik_sahipsiz_sayilmiyor(tmp_path):
    """ASIL ARIZA: `cover_vertical.png` boru hattının KENDİ ürettiği dosya.

    Sabit ad listesinde olmadığı için 21 projenin 21'inde de sahipsiz
    sayılıyordu -> 21 x 3 sn uyku, her koşuda."""
    (tmp_path / "cover.png").write_bytes(b"x")
    (tmp_path / "cover_vertical.png").write_bytes(b"x")
    (tmp_path / "art.jpg").write_bytes(b"x")

    assert wp._find_stray_images(str(tmp_path)) == []


def test_desen_yarin_eklenecek_varyantlari_da_kapsiyor(tmp_path):
    """DESEN SEÇİMİNİN GEREKÇESİ: sabit liste `cover_square.png` eklendiği gün
    yine bayatlardı — ve bayatladığında HATA VERMEZ, sessizce yavaşlar."""
    for ad in ("cover_square.png", "cover_vertical.jpg", "art_kare.png",
               "art_blur.jpeg", "cover.jpeg"):
        (tmp_path / ad).write_bytes(b"x")

    assert wp._find_stray_images(str(tmp_path)) == []


def test_gercek_sahipsiz_gorsel_HALA_yakalaniyor(tmp_path):
    """DESENİN DAR OLDUĞUNUN KANITI — fazla geniş bir desen (`cover*` gibi
    serbest bir önek) bu script'in var olma sebebini yok ederdi: kullanıcının
    Pixlr'dan indirdiği kapak bir daha hiç yerleştirilmezdi."""
    beklenen = [
        "arda_02_arac_onden.jpg",   # gerçek örnek, dj_sets/_arda
        "coverim.png",              # "cover" GEÇİYOR ama rol adı değil
        "kapak_tasarimi.png",
        "kart_art_gorseli.png",     # "art" GEÇİYOR ama rol adı değil
        "pixlr_export_1234.png",
        "sahne_art_final.jpg",
    ]
    for ad in beklenen:
        (tmp_path / ad).write_bytes(b"x")

    bulunan = sorted(os.path.basename(p) for p in wp._find_stray_images(str(tmp_path)))
    assert bulunan == sorted(beklenen)


def test_alt_cizgili_ic_dosyalar_hala_eleniyor(tmp_path):
    """Render'ın ürettiği `_backdrop_pan_*.png` dosyaları (her projede 2 tane)
    eskiden de eleniyordu, desen değişikliği bunu bozmamalı."""
    (tmp_path / "_backdrop_pan_1920x1080.png").write_bytes(b"x")
    (tmp_path / "_bg_base_tmp.png").write_bytes(b"x")

    assert wp._find_stray_images(str(tmp_path)) == []


def test_alt_cizgi_on_ekli_KLASOR_hic_taranmiyor(tmp_path, monkeypatch):
    """`dj_sets/_arda` PROJE DEĞİL (audio/meta/state yok, ham portreler).

    Bu bir varsayım değil, GERÇEKLEŞMİŞ arıza: 2026-09-11 09:14'te izleyici
    oradaki `arda_01_ic_mekan.jpg`'yi `cover.jpg` yaptı (watch_projects.log).
    Kalan 8 fotoğraf da her koşuda 3'er saniye harcatıyordu."""
    monkeypatch.setattr(wp, "STABILITY_WAIT_SECONDS", 0)
    arda = tmp_path / "_arda"
    arda.mkdir()
    (arda / "arda_02_arac_onden.jpg").write_bytes(b"x" * 100)
    gecici = tmp_path / ".tmp-Yarim Derleme"
    gecici.mkdir()
    (gecici / "indirilen.wav").write_bytes(b"x" * 100)

    tetiklenen = []
    monkeypatch.setattr(wp, "_trigger_script", lambda s: tetiklenen.append(s))

    wp._scan_dir(str(tmp_path), "dj_famous_process.py")

    assert (arda / "arda_02_arac_onden.jpg").exists()   # DOKUNULMADI
    assert not (arda / "cover.jpg").exists()
    assert not (gecici / "audio.wav").exists()          # yarım derleme tetiklemez
    assert tetiklenen == []


def test_gercek_proje_klasoru_hala_isleniyor(tmp_path, monkeypatch):
    """Klasör filtresi bir KAYIP yaratmıyor — sınır testi."""
    monkeypatch.setattr(wp, "STABILITY_WAIT_SECONDS", 0)
    proje = tmp_path / "Gercek Sarki"
    proje.mkdir()
    (proje / "indirilen.wav").write_bytes(b"x" * 100)
    (proje / "pixlr_kapak.png").write_bytes(b"x" * 100)

    tetiklenen = []
    monkeypatch.setattr(wp, "_trigger_script", lambda s: tetiklenen.append(s))

    wp._scan_dir(str(tmp_path), "auto_process.py")

    assert (proje / "audio.wav").is_file()
    assert (proje / "cover.png").is_file()
    assert tetiklenen == ["auto_process.py"]


# ---------------------------------------------------------------------------
# B — tetikleme ENGELLEMEMELİ, ve Windows'ta job'dan KOPMALI
# ---------------------------------------------------------------------------

class _SahtePopen:
    """`subprocess.Popen` taklidi — çağrıyı kaydeder, hiçbir şey başlatmaz."""

    def __init__(self, kayit, hata=None, hata_bayragi=None):
        self.kayit = kayit
        self._hata = hata
        self._hata_bayragi = hata_bayragi

    def __call__(self, cmd, **kwargs):
        bayraklar = kwargs.get("creationflags", 0)
        self.kayit.append((cmd, kwargs))
        if self._hata is not None and (self._hata_bayragi is None
                                       or bayraklar & self._hata_bayragi):
            raise self._hata
        return object()          # wait()/communicate() ÇAĞRILMAMALI


def _run_yasak(*a, **k):
    raise AssertionError("subprocess.run çağrıldı — tetikleme yine ENGELLİYOR")


def test_tetikleme_engellemez_ve_job_dan_kopar(monkeypatch):
    """En kritik davranış: `subprocess.run` YOK (beklemiyoruz) ve Windows'ta
    `CREATE_BREAKAWAY_FROM_JOB` VAR (yoksa Görev Zamanlayıcı'nın job'u koşuyu
    5. dakikada yine öldürür — düz `Popen` TEK BAŞINA yetmez)."""
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(subprocess, "run", _run_yasak)
    kayit = []
    monkeypatch.setattr(subprocess, "Popen", _SahtePopen(kayit))
    wp._TETIKLENENLER.clear()

    assert wp._trigger_script("auto_process.py") is True

    assert len(kayit) == 1
    cmd, kwargs = kayit[0]
    assert os.path.basename(cmd[1]) == "gorev_sarmalayici.py"   # sarmalayıcı KORUNDU
    assert cmd[2] == "auto_process.py"
    bayraklar = kwargs["creationflags"]
    assert bayraklar & subprocess.CREATE_BREAKAWAY_FROM_JOB
    assert bayraklar & subprocess.DETACHED_PROCESS
    # std akışları YÖNLENDİRİLMEMELİ: sarmalayıcı `sys.stderr is None` koşuluna
    # bakıp kendi iz dosyasına yönlendiriyor; DEVNULL o koşulu bozar ve çökme
    # traceback'lerini sessizce yutardı.
    assert "stderr" not in kwargs and "stdout" not in kwargs


def test_breakaway_reddedilirse_sessiz_kalinmiyor_ve_yedek_yol_var(monkeypatch):
    """`CREATE_BREAKAWAY_FROM_JOB`, job `JOB_OBJECT_LIMIT_BREAKAWAY_OK`
    vermiyorsa CreateProcess'i ERROR_ACCESS_DENIED ile düşürür. O durumda:
    (a) log'a sebep yazılır, (b) breakaway'siz — ama YİNE DE engellemeyen —
    ikinci bir deneme yapılır. Beklemeye GERİ DÜŞÜLMEZ."""
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(subprocess, "run", _run_yasak)
    kayit = []
    monkeypatch.setattr(subprocess, "Popen", _SahtePopen(
        kayit, hata=PermissionError(5, "Access is denied"),
        hata_bayragi=subprocess.CREATE_BREAKAWAY_FROM_JOB))
    satirlar = []
    monkeypatch.setattr(wp, "log", satirlar.append)
    wp._TETIKLENENLER.clear()

    assert wp._trigger_script("auto_process.py") is True

    assert len(kayit) == 2
    assert not (kayit[1][1]["creationflags"] & subprocess.CREATE_BREAKAWAY_FROM_JOB)
    assert kayit[1][1]["creationflags"] & subprocess.DETACHED_PROCESS
    assert any("kopma reddedildi" in s for s in satirlar)


def test_her_iki_deneme_de_basarisizsa_False_ve_log(monkeypatch):
    """Sessizce `True` dönen bir tetikleyici, olmayan tetikleyiciden kötüdür."""
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(subprocess, "run", _run_yasak)
    kayit = []
    monkeypatch.setattr(subprocess, "Popen", _SahtePopen(
        kayit, hata=OSError("CreateProcess başarısız")))
    satirlar = []
    monkeypatch.setattr(wp, "log", satirlar.append)
    wp._TETIKLENENLER.clear()

    assert wp._trigger_script("auto_process.py") is False
    assert len(kayit) == 2
    assert any("tetiklenemedi" in s for s in satirlar)


def test_win32_disinda_windows_bayraklari_KULLANILMIYOR(monkeypatch):
    """`creationflags` POSIX'te `ValueError` verir — bayraklar platforma
    bağlı olmak ZORUNDA."""
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(subprocess, "run", _run_yasak)
    kayit = []
    monkeypatch.setattr(subprocess, "Popen", _SahtePopen(kayit))
    wp._TETIKLENENLER.clear()

    assert wp._trigger_script("auto_process.py") is True

    _cmd, kwargs = kayit[0]
    assert "creationflags" not in kwargs
    assert kwargs["start_new_session"] is True


def test_kaynakta_subprocess_run_kalmadi():
    """Kaynak seviyesinde çapa: `_trigger_script` yarın tekrar `subprocess.run`a
    dönerse (ör. "çıkış kodunu görelim" diye) arıza zinciri AYNEN geri gelir."""
    import ast
    yol = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "watch_projects.py")
    with open(yol, "r", encoding="utf-8") as f:
        agac = ast.parse(f.read(), filename=yol)
    cagrilar = [d for d in ast.walk(agac)
                if isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
                and d.func.attr == "run"
                and isinstance(d.func.value, ast.Name) and d.func.value.id == "subprocess"]
    assert cagrilar == []


# ---------------------------------------------------------------------------
# B (ikinci yarı) — TRIGGER_LOCKS ve çift tetikleme
# ---------------------------------------------------------------------------

def test_taze_kilit_tetiklemeyi_VE_adlandirmayi_hala_erteliyor(tmp_path, monkeypatch):
    """`TRIGGER_LOCKS`/`_is_running` ön elemesi bozulmamış olmalı: hedef betik
    koşarken ne yeniden adlandırma ne tetikleme yapılır (adlandırma da
    ertelenmeli, yoksa `_has_audio()` True dönüp proje bir daha HİÇ
    tetiklenmezdi)."""
    monkeypatch.setattr(wp, "STABILITY_WAIT_SECONDS", 0)
    kilit = tmp_path / ".auto_process.lock"
    kilit.write_text("pid", encoding="utf-8")
    monkeypatch.setattr(wp, "TRIGGER_LOCKS", {"auto_process.py": str(kilit)})

    proje = tmp_path / "Yeni Sarki"
    proje.mkdir()
    (proje / "indirilen.wav").write_bytes(b"x" * 100)

    tetiklenen = []
    monkeypatch.setattr(wp, "_trigger_script", lambda s: tetiklenen.append(s))

    assert wp._is_running("auto_process.py") is True
    wp._scan_dir(str(tmp_path), "auto_process.py")

    assert (proje / "indirilen.wav").exists()
    assert not (proje / "audio.wav").exists()
    assert tetiklenen == []


def test_ayni_taramada_ayni_betik_IKI_KEZ_tetiklenmiyor(monkeypatch):
    """ENGELLEMEYEN TETİKLEMENİN YENİ RİSKİ: `subprocess.run` döndüğü için
    ikinci projeye sıra geldiğinde `_is_running()` kilidi TAZE görüyordu.
    Kopmuş süreçte kilit henüz oluşmamış olabilir (TOCTOU) — yani aynı
    taramada iki yeni parça varsa AYNI betik iki kez başlardı."""
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(subprocess, "run", _run_yasak)
    kayit = []
    monkeypatch.setattr(subprocess, "Popen", _SahtePopen(kayit))
    satirlar = []
    monkeypatch.setattr(wp, "log", satirlar.append)
    wp._TETIKLENENLER.clear()

    assert wp._trigger_script("auto_process.py") is True
    assert wp._trigger_script("auto_process.py") is False
    # FARKLI betik engellenmiyor (projects/ ve dj_sets/ aynı taramada)
    assert wp._trigger_script("dj_famous_process.py") is True

    assert [c[0][2] for c in kayit] == ["auto_process.py", "dj_famous_process.py"]
    assert any("ikinci tetikleme atlandi" in s for s in satirlar)


def test_iki_yeni_parca_tek_taramada_tek_surec_baslatir(tmp_path, monkeypatch):
    """Yukarıdakinin `_scan_dir` üzerinden uçtan uca hâli."""
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(subprocess, "run", _run_yasak)
    monkeypatch.setattr(wp, "STABILITY_WAIT_SECONDS", 0)
    monkeypatch.setattr(wp, "TRIGGER_LOCKS", {"auto_process.py": str(tmp_path / "yok.lock")})
    kayit = []
    monkeypatch.setattr(subprocess, "Popen", _SahtePopen(kayit))
    monkeypatch.setattr(wp, "log", lambda s: None)
    wp._TETIKLENENLER.clear()

    for ad in ("A Sarki", "B Sarki"):
        (tmp_path / ad).mkdir()
        (tmp_path / ad / "indirilen.wav").write_bytes(b"x" * 100)

    wp._scan_dir(str(tmp_path), "auto_process.py")

    assert len(kayit) == 1
    # İkisi de audio.wav oldu; ikincisini koşan süreç ya da saatlik hat alır.
    assert (tmp_path / "A Sarki" / "audio.wav").is_file()


def test_main_her_kosuda_tetikleme_hafizasini_sifirliyor(tmp_path, monkeypatch):
    """Modül düzeyindeki küme KOŞU-İÇİ; `main()` testlerde (ve teorik olarak
    uzun ömürlü bir çağırandan) defalarca çağrılabiliyor."""
    monkeypatch.setattr(wp, "BASE_DIR", str(tmp_path))
    monkeypatch.setattr(wp, "PROJECTS_DIR", str(tmp_path / "projects"))
    monkeypatch.setattr(wp, "DJ_SETS_DIR", str(tmp_path / "dj_sets"))
    monkeypatch.setattr(wp, "LOG_PATH", str(tmp_path / "watch_projects.log"))
    monkeypatch.setattr(wp, "AUTO_PROCESS_LOG_PATH", str(tmp_path / "auto_process.log"))
    monkeypatch.setattr(wp, "DJ_FAMOUS_LOG_PATH", str(tmp_path / "dj_famous_process.log"))
    monkeypatch.setattr(wp, "HEARTBEAT_MARKER_PATH", str(tmp_path / ".watchdog_alerted"))
    wp._TETIKLENENLER.add("auto_process.py")

    wp.main()

    assert wp._TETIKLENENLER == set()


# ---------------------------------------------------------------------------
# C — yarım render "hazır" sayılmamalı  (BU DOSYA SAHİPLİĞİMDE DEĞİL)
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=True, reason=(
    "AÇIK ARIZA, BİLEREK KIRMIZI: `_is_rendered()` `auto_process.py` (:209) ve "
    "`dj_famous_process.py` (:171) içinde ve bu iki dosya bu vardiyada YAZMA "
    "İZNİ DIŞINDA. Düzeltme tarifi rapordadır (ffprobe ile süre doğrulaması, "
    "ffprobe yoksa zarif düşüş). Düzeltme uygulandığında bu test XPASS eder ve "
    "strict=True sayesinde SESSİZ KALMAZ — o gün yapılacak tek şey bu "
    "işaretçiyi kaldırmak."))
def test_is_rendered_yarim_dosyayi_hazir_saymamali(tmp_path):
    """ffmpeg `-y` ile DOĞRUDAN nihai dosyaya yazıyor; `TerminateProcess` ile
    ölen bir render diskte 0 baytlık ya da yarım bir mp4 bırakıyor.
    `os.path.isfile` buna True diyor -> sonraki koşu render'ı ATLAR ve BOZUK
    videoyu yükler. Log'da sadece "Zaten render edilmiş" yazar."""
    import auto_process

    cikti = tmp_path / "output"
    cikti.mkdir()
    for ad in auto_process.RENDER_OUTPUTS:
        (cikti / ad).write_bytes(b"")          # 0 bayt — öldürülmüş render

    assert auto_process._is_rendered(str(tmp_path)) is False
