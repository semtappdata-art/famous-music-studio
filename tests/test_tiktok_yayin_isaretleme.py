# -*- coding: utf-8 -*-
"""TikTok'ta ELLE yapılan yayının depoya bildirilmesi — okuyan/yazan döngüsü.

NEDEN VAR (2026-09-12): `upload/tiktok_publish_plan.py::build_plan()` iki state
alanını OKUYOR — `tiktok_published_at` ve `tiktok_dogrulandi` — ama depoda bu
alanları YAZAN hiçbir kod yoktu ve 22 proje klasörünün hiçbirinde ikisi de
mevcut değildi. CLAUDE.md'deki "BAĞLANTI seviyesindeki sessiz arıza" sınıfının
tam örneği: fonksiyonlar kendi içinde doğru, arıza bağlantıda.

Bedeli ÖLÇÜLEBİLİR bir kapı kaybıydı: `_tiktok_ikiz_kapisi`'nın EN AĞIR kuralı
("ikizi TikTok'ta ZATEN yayınlanmış → ENGEL") hiçbir kayıt "yayınlandı"
demediği için PRATİKTE HİÇ ATEŞLENEMİYORDU. Bu dosyadaki
`test_isaretleme_ikiz_kapisini_gercekten_ateslıyor` tam olarak o döngüyü
doğruluyor: işaretle → `build_plan`'in kararı DEĞİŞSİN.

İki alan BİLEREK ayrı yazılıyor ve bu ayrım da test ediliyor
(`test_yayinlandi_dogrulandi_bayragini_YAZMAZ`): `--yayinlandi` toplu
kullanılan bir komut, `tiktok_dogrulandi` ise kanalın TAMAMI için
`PUBLIC_TO_EVERYONE` önerisini açıyor. İkisini birleştirmek, tek bir toplu
hareketin denetlenmemiş herkese-açık yayın önerisi üretmesi demekti.

Bu testler HİÇBİR ağ çağrısı yapmaz ve gerçek `projects/` klasörüne DOKUNMAZ:
katalog kökü her testte `tmp_path`'e çekiliyor (`uyumluluk.KOKLER`).
"""

import json
import os
import subprocess
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_UPLOAD = os.path.join(_REPO, "upload")
for _yol in (_REPO, _UPLOAD):
    if _yol not in sys.path:
        sys.path.insert(0, _yol)

import state_io
import tiktok_publish_plan as TPP
import uyumluluk


# --------------------------------------------------------------------------
# Fikstürler
# --------------------------------------------------------------------------

def _proje(kok, ad, durum=None, ses=b"ayni-ses-baytlari", video=True):
    """Diskte minimal ama gerçekçi bir proje klasörü kurar."""
    p = kok / ad
    p.mkdir(parents=True, exist_ok=True)
    (p / "state.json").write_text(
        json.dumps(durum or {}, ensure_ascii=False), encoding="utf-8")
    (p / "meta.json").write_text(
        json.dumps({"title": ad, "theme": "pop"}, ensure_ascii=False),
        encoding="utf-8")
    (p / "audio.wav").write_bytes(ses)
    if video:
        (p / "output").mkdir(exist_ok=True)
        (p / "output" / TPP.VIDEO_ADI).write_bytes(b"sahte-mp4")
    return str(p)


def _durum(proje):
    with open(os.path.join(proje, "state.json"), "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def kok(tmp_path, monkeypatch):
    """Katalog kökünü geçici klasöre çeker — gerçek `projects/` DOKUNULMAZ.

    Mutlak yol veriliyor: göreli olsaydı yanlış cwd'de `os.path.isdir` False
    döner ve taramalar SESSİZCE boş sonuç üretirdi (CLAUDE.md).
    """
    k = tmp_path / "projects"
    k.mkdir()
    monkeypatch.setattr(uyumluluk, "KOKLER", (str(k),))
    return k


class _SahteTTY:
    """`--yayinlandi-hepsi` etkileşimli terminal şartını taklit eder."""

    def isatty(self):
        return True


# --------------------------------------------------------------------------
# 1. Tek proje işaretleme
# --------------------------------------------------------------------------

def test_yayinlandi_damgasi_yaziliyor(kok):
    p = _proje(kok, "Sarki", {"tiktok_publish_id": "v_inbox~1"})
    oldu, mesaj = TPP.isaretle_yayinlandi(p, zaman="2026-09-12T19:30:00")
    assert oldu is True
    assert "2026-09-12T19:30:00" in mesaj
    assert _durum(p)["tiktok_published_at"] == "2026-09-12T19:30:00"


def test_var_olan_alanlar_KORUNUYOR(kok):
    """İşaretleme kaydın geri kalanını silmemeli.

    `kopya_notu` özellikle kritik: `uyumluluk`'un md5 muafiyetini besleyen
    alan, kaybolması sessizce bir KAPIYI değiştirirdi.
    """
    p = _proje(kok, "Sarki", {
        "tiktok_publish_id": "v_inbox~1", "youtube_video_id": "abc",
        "kopya_notu": "aynı kaydın iki ismi", "tiktok_cover_hint": "cover.png"})
    TPP.isaretle_yayinlandi(p)
    d = _durum(p)
    assert d["youtube_video_id"] == "abc"
    assert d["kopya_notu"] == "aynı kaydın iki ismi"
    assert d["tiktok_cover_hint"] == "cover.png"


def test_yazim_state_io_uzerinden_atomik(kok, monkeypatch):
    """CLAUDE.md'nin açık kuralı: state.json'ı elle yazan YENİ kod eklenmez.

    Çağrının VARLIĞI doğrulanıyor (davranış değil): `state_io.durum_yaz`
    devre dışı bırakıldığında diske hiçbir şey düşmemeli — yani modülde
    ikinci, elle yazan bir yol YOK.
    """
    p = _proje(kok, "Sarki", {"tiktok_publish_id": "v_inbox~1"})
    cagrildi = []
    monkeypatch.setattr(TPP.state_io, "durum_yaz",
                        lambda proje, veri: cagrildi.append((proje, veri)))
    TPP.isaretle_yayinlandi(p)
    assert len(cagrildi) == 1, "yazım TEK atomik yazıcıdan geçmeli"
    assert cagrildi[0][1]["tiktok_published_at"]
    assert "tiktok_published_at" not in _durum(p), (
        "modülde state.json'a doğrudan yazan İKİNCİ bir yol var")
    assert TPP.state_io is state_io


def test_idempotent_ve_SESSIZ_DEGIL(kok):
    """Tekrar işaretlemek zararsız olmalı — ama kullanıcıya söylemeli."""
    p = _proje(kok, "Sarki", {"tiktok_publish_id": "v_inbox~1"})
    TPP.isaretle_yayinlandi(p, zaman="2026-09-12T19:30:00")
    oldu, mesaj = TPP.isaretle_yayinlandi(p, zaman="2026-09-13T09:00:00")
    assert oldu is False
    assert "ZATEN" in mesaj
    assert _durum(p)["tiktok_published_at"] == "2026-09-12T19:30:00", (
        "ilk damga KORUNMALI — gerçek yayın anı odur")


def test_dry_run_diske_dokunmuyor(kok):
    p = _proje(kok, "Sarki", {"tiktok_publish_id": "v_inbox~1"})
    oldu, mesaj = TPP.isaretle_yayinlandi(p, dry_run=True)
    assert oldu is False
    assert "kuru" in mesaj.lower()
    assert "tiktok_published_at" not in _durum(p)


# --------------------------------------------------------------------------
# 2. Hatalar SESSİZCE geçilmiyor
# --------------------------------------------------------------------------

def test_olmayan_proje_net_hata(kok):
    with pytest.raises(TPP.IsaretlemeHatasi) as e:
        TPP.isaretle_yayinlandi(str(kok / "Yok Boyle"))
    assert "klasörü yok" in str(e.value)


def test_tiktoka_hic_yuklenmemis_proje_net_hata(kok):
    """`tiktok_publish_id` yoksa taslak da yok — yayınlanmış olamaz."""
    p = _proje(kok, "Yuklenmedi", {"youtube_video_id": "abc"})
    with pytest.raises(TPP.IsaretlemeHatasi) as e:
        TPP.isaretle_yayinlandi(p)
    assert "hiç yüklenmemiş" in str(e.value)
    assert "tiktok_upload.py" in str(e.value), "çıkış yolu da söylenmeli"


def test_bozuk_state_json_USTUNE_YAZILMIYOR(kok):
    """Okuma tarafı hata yutuyor (plan basılsın diye); YAZMA tarafı YUTMAMALI.

    `_durum_oku` bozuk dosyada `{}` dönüyor — o `{}`'ın üstüne yazmak projenin
    TÜM kaydını silerdi. İşaretleme yolu bu yüzden kendi katı okuyucusunu
    (`_durum_oku_kesin`) kullanıyor.
    """
    p = _proje(kok, "Bozuk", {"tiktok_publish_id": "v~1"})
    (kok / "Bozuk" / "state.json").write_text('{"yarim": ', encoding="utf-8")
    with pytest.raises(TPP.IsaretlemeHatasi) as e:
        TPP.isaretle_yayinlandi(p)
    assert "OKUNAMADI" in str(e.value)
    assert (kok / "Bozuk" / "state.json").read_text(encoding="utf-8") == '{"yarim": ', (
        "bozuk dosya DEĞİŞTİRİLMEMELİ")


# --------------------------------------------------------------------------
# 3. DÖNGÜ: işaretleme -> build_plan'in kararı değişiyor
# --------------------------------------------------------------------------

def _ikiz_katalog(kok):
    """Küllerimden Geç / Yeniden Doğacağım ikilisinin sadeleştirilmiş hâli."""
    orijinal = _proje(kok, "Orijinal", {
        "youtube_video_id": "aaa", "youtube_privacy": "public",
        "tiktok_publish_id": "v_inbox~orijinal", "kopya_notu": "aynı kayıt"})
    kopya = _proje(kok, "Kopya", {
        "youtube_video_id": "bbb", "youtube_privacy": "unlisted",
        "tiktok_publish_id": "v_inbox~kopya", "kopya_notu": "aynı kayıt"})
    return orijinal, kopya


def test_isaretleme_ikiz_kapisini_gercekten_atesliyor(kok):
    """BU DOSYANIN ASIL SEBEBİ — kapının en ağır kuralı hiç ateşlenemiyordu.

    `_tiktok_ikiz_kapisi` kural 1: "ikiz TikTok'ta ZATEN yayınlanmışsa ENGEL".
    `tiktok_published_at`'ı yazan kod olmadığı için bu dal ölü koddu.
    """
    orijinal, kopya = _ikiz_katalog(kok)

    once = TPP.build_plan(kopya)
    assert not any("ZATEN yayınlanmış" in h for h in once["uyumluluk_hatalari"])

    TPP.isaretle_yayinlandi(orijinal, zaman="2026-09-12T19:30:00")

    sonra = TPP.build_plan(kopya)
    assert sonra["hazir"] is False
    assert any("ZATEN yayınlanmış" in h and "Orijinal" in h
               for h in sonra["uyumluluk_hatalari"]), (
        "işaretleme ikiz kapısının EN AĞIR kuralını beslemeli")
    assert "2026-09-12T19:30:00" in sonra["engel"]


def test_isaretlenen_proje_kendisi_de_tekrar_yayinlanmaz(kok):
    p = _proje(kok, "Sarki", {"tiktok_publish_id": "v_inbox~1",
                              "youtube_privacy": "public"},
               ses=b"tek-basina-bir-ses")
    assert TPP.build_plan(p)["hazir"] is True
    TPP.isaretle_yayinlandi(p, zaman="2026-09-12T19:30:00")
    plan = TPP.build_plan(p)
    assert plan["hazir"] is False
    assert "zaten yayınlanmış" in plan["engel"]


def test_bekleyen_taslaklar_isaretlenince_listeden_dusuyor(kok):
    a = _proje(kok, "A", {"tiktok_publish_id": "v~a"}, ses=b"ses-a")
    _proje(kok, "B", {"tiktok_publish_id": "v~b"}, ses=b"ses-b")
    _proje(kok, "C", {"youtube_video_id": "c"}, ses=b"ses-c")  # TikTok'ta yok
    assert sorted(os.path.basename(x) for x in TPP.bekleyen_taslaklar()) == ["A", "B"]
    TPP.isaretle_yayinlandi(a)
    assert [os.path.basename(x) for x in TPP.bekleyen_taslaklar()] == ["B"]


def test_bekleyen_taslaklar_KANONIK_kok_listesini_kullaniyor():
    """`derlemeler/` elle sayan her yerde atlanmıştı — tarama merkezi olmalı."""
    import inspect
    kaynak = inspect.getsource(TPP.bekleyen_taslaklar)
    assert "uyumluluk.proje_klasorleri" in kaynak, (
        "kök listesi elle sayılmamalı (uyumluluk.KOK_ADLARI tek kanonik liste)")


# --------------------------------------------------------------------------
# 4. İki alan AYRI: yayınlamak doğrulamak değildir
# --------------------------------------------------------------------------

def test_yayinlandi_dogrulandi_bayragini_YAZMAZ(kok):
    """Yanlış işaretlemenin "yeşil ışık" riskini sınırlayan ayrım.

    `tiktok_dogrulandi` kanalın TAMAMI için `PUBLIC_TO_EVERYONE` önerisini
    açıyor. `--yayinlandi` toplu kullanılan bir komut; ikisi birleşseydi tek
    bir toplu hareket denetlenmemiş herkese-açık yayın önerisi üretirdi.
    """
    p = _proje(kok, "Sarki", {"tiktok_publish_id": "v_inbox~1"})
    TPP.isaretle_yayinlandi(p)
    assert "tiktok_dogrulandi" not in _durum(p)


def test_dogrulama_yayinlanmamis_projede_reddediliyor(kok):
    p = _proje(kok, "Sarki", {"tiktok_publish_id": "v_inbox~1"})
    with pytest.raises(TPP.IsaretlemeHatasi) as e:
        TPP.isaretle_dogrulandi(p)
    assert "--yayinlandi" in str(e.value)


def test_dogrulama_KANAL_seviyesinde_okunuyor(kok):
    """Bayrak proje bazlı okunsaydı İSPATEN ölü olurdu.

    `onerilen_gizlilik` yalnızca HENÜZ yayınlanmamış bir proje için anlamlı;
    ama bir projenin kendi `tiktok_dogrulandi`si ancak yayınlandıktan sonra
    doğru olabilir — ve o anda plan zaten "zaten yayınlanmış" diyor. Yani
    proje bazlı okumada hiçbir yeni şarkı asla PUBLIC_TO_EVERYONE önerisi
    alamazdı: kanal sonsuza kadar kendi kendine yayın yapardı.
    """
    dogrulanan = _proje(kok, "Ilk Gonderi", {"tiktok_publish_id": "v~1"},
                        ses=b"ses-1")
    yeni = _proje(kok, "Yeni Sarki", {"tiktok_publish_id": "v~2"}, ses=b"ses-2")

    assert TPP.build_plan(yeni)["onerilen_gizlilik"] == "SELF_ONLY"
    assert TPP.build_plan(yeni)["dogrulandi"] is False

    TPP.isaretle_yayinlandi(dogrulanan)
    oldu, _ = TPP.isaretle_dogrulandi(dogrulanan)
    assert oldu is True

    plan = TPP.build_plan(yeni)
    assert plan["onerilen_gizlilik"] == "PUBLIC_TO_EVERYONE"
    assert plan["dogrulandi"] is True


def test_dogrulama_idempotent(kok):
    p = _proje(kok, "Sarki", {"tiktok_publish_id": "v~1",
                              "tiktok_published_at": "2026-09-12T19:30:00"})
    assert TPP.isaretle_dogrulandi(p)[0] is True
    oldu, mesaj = TPP.isaretle_dogrulandi(p)
    assert oldu is False and "ZATEN" in mesaj


def test_dogrulama_taramasi_cokerse_GUVENLI_tarafa_dusuyor(kok, monkeypatch):
    """Sessizce PUBLIC'e açılan bir öneri kabul edilemez (DIRECT_POST geri alınamaz)."""
    p = _proje(kok, "Sarki", {"tiktok_publish_id": "v~1"})

    def patlat(*a, **k):
        raise RuntimeError("tarama bozuk")

    monkeypatch.setattr(TPP, "_kanal_dogrulandi", patlat)
    plan = TPP.build_plan(p)
    assert plan["onerilen_gizlilik"] == "SELF_ONLY"
    assert plan["dogrulandi"] is False


# --------------------------------------------------------------------------
# 5. Toplu mod — körü körüne işaretleme YOK
# --------------------------------------------------------------------------

def test_toplu_mod_sadece_ONAY_verileni_isaretliyor(kok, monkeypatch, capsys):
    _proje(kok, "A", {"tiktok_publish_id": "v~a", "youtube_privacy": "public"},
           ses=b"ses-a")
    _proje(kok, "B", {"tiktok_publish_id": "v~b", "youtube_privacy": "public"},
           ses=b"ses-b")
    _proje(kok, "C", {"tiktok_publish_id": "v~c", "youtube_privacy": "public"},
           ses=b"ses-c")
    monkeypatch.setattr(sys, "stdin", _SahteTTY())
    cevaplar = iter(["e", "", "e"])          # A evet, B boş (hayır), C evet

    yazilan = TPP._toplu_isaretle(girdi=lambda: next(cevaplar))
    assert yazilan == 2
    assert "tiktok_published_at" in _durum(str(kok / "A"))
    assert "tiktok_published_at" not in _durum(str(kok / "B")), (
        "varsayılan cevap HAYIR olmalı")
    assert "tiktok_published_at" in _durum(str(kok / "C"))


def test_toplu_modda_ENGELLI_proje_icin_duz_e_YETMIYOR(kok, monkeypatch):
    """Sürtünme riskle orantılı: plan "yayınlanmamalı" diyorsa 'EVET' gerekiyor.

    Kopya bir sesi yanlışlıkla "yayınlandı" işaretlemek, gerçekte yayınlanmamış
    kaydı kanalın canlı kaydı yapar ve ikiz kapısını TERS çalıştırır.
    """
    _proje(kok, "Orijinal", {"youtube_privacy": "public",
                             "tiktok_publish_id": "v~o"})
    _proje(kok, "Kopya", {"youtube_privacy": "unlisted",
                          "tiktok_publish_id": "v~k"})
    monkeypatch.setattr(sys, "stdin", _SahteTTY())

    # İki aday da engelli değil/engelli olabilir; sırayla düz "e" veriyoruz.
    yazilan = TPP._toplu_isaretle(girdi=lambda: "e")
    kopya = _durum(str(kok / "Kopya"))
    assert "tiktok_published_at" not in kopya, (
        "plan 'yayınlanmamalı' derken düz 'e' ile işaretlenmemeli")

    # Açık onayla işaretlenebiliyor (gerçekten yayınlanmışsa doğru kayıt bu).
    TPP._toplu_isaretle(girdi=lambda: "EVET")
    assert "tiktok_published_at" in _durum(str(kok / "Kopya"))
    assert yazilan >= 0


def test_toplu_mod_dry_run_hicbir_seyi_yazmiyor(kok, monkeypatch):
    _proje(kok, "A", {"tiktok_publish_id": "v~a", "youtube_privacy": "public"},
           ses=b"ses-a")
    monkeypatch.setattr(sys, "stdin", _SahteTTY())
    TPP._toplu_isaretle(dry_run=True, girdi=lambda: "e")
    assert "tiktok_published_at" not in _durum(str(kok / "A"))


def test_toplu_mod_etkilesimsiz_kabukta_YAZMAYI_REDDEDIYOR(kok, monkeypatch):
    """Etkileşimsiz koşu, kaçınmak istediğimiz "körü körüne hepsi"nin ta kendisi."""
    _proje(kok, "A", {"tiktok_publish_id": "v~a"}, ses=b"ses-a")

    class _Boru:
        def isatty(self):
            return False

    monkeypatch.setattr(sys, "stdin", _Boru())
    with pytest.raises(TPP.IsaretlemeHatasi) as e:
        TPP._toplu_isaretle()
    assert "--dry-run" in str(e.value)
    assert "tiktok_published_at" not in _durum(str(kok / "A"))


def test_toplu_mod_etkilesimsiz_KURU_modda_sadece_listeliyor(kok, monkeypatch,
                                                             capsys):
    """Boruya/betiğe yönlendirilmiş kuru koşu: özet basılır, hiçbir şey yazılmaz."""
    _proje(kok, "A", {"tiktok_publish_id": "v~a", "youtube_privacy": "public"},
           ses=b"ses-a")

    class _Boru:
        def isatty(self):
            return False

    monkeypatch.setattr(sys, "stdin", _Boru())
    assert TPP._toplu_isaretle(dry_run=True) == 0
    assert "A" in capsys.readouterr().out
    assert "tiktok_published_at" not in _durum(str(kok / "A"))


def test_toplu_mod_ONCE_TUM_listeyi_basiyor(kok, monkeypatch, capsys):
    """Operatör ilk soruya cevap vermeden önce bütünü görmeli.

    Hangi taslakların yayınlanmaması gerektiği (kopya/telif) ancak liste
    bütün hâlinde görününce fark ediliyor.
    """
    for ad in ("A", "B", "C"):
        _proje(kok, ad, {"tiktok_publish_id": "v~" + ad,
                         "youtube_privacy": "public"},
               ses=("ses-" + ad).encode())
    monkeypatch.setattr(sys, "stdin", _SahteTTY())
    TPP._toplu_isaretle(girdi=lambda: "q")
    cikti = capsys.readouterr().out
    ozet = cikti.split("[1/3]")[0]
    for ad in ("A", "B", "C"):
        assert ad in ozet, "ilk soru sorulmadan ÖNCE tüm liste basılmalı"


def test_toplu_mod_q_ile_cikiliyor(kok, monkeypatch):
    for ad in ("A", "B"):
        _proje(kok, ad, {"tiktok_publish_id": "v~" + ad,
                         "youtube_privacy": "public"},
               ses=("ses-" + ad).encode())
    monkeypatch.setattr(sys, "stdin", _SahteTTY())
    cevaplar = iter(["e", "q"])
    yazilan = TPP._toplu_isaretle(girdi=lambda: next(cevaplar))
    assert yazilan == 1
    assert "tiktok_published_at" not in _durum(str(kok / "B"))


# --------------------------------------------------------------------------
# 6. Hiçbir ağ çağrısı yok + Windows kod sayfası tuzağı
# --------------------------------------------------------------------------

def test_modul_aga_hic_cikmiyor():
    """İşaretleme TAMAMEN yerel: TikTok'a hiçbir şey gönderilmiyor."""
    import ast
    import io
    kaynak = io.open(os.path.join(_UPLOAD, "tiktok_publish_plan.py"),
                     encoding="utf-8").read()
    agac = ast.parse(kaynak)
    ithal = set()
    for d in ast.walk(agac):
        if isinstance(d, ast.Import):
            ithal.update(a.name.split(".")[0] for a in d.names)
        elif isinstance(d, ast.ImportFrom) and d.module:
            ithal.add(d.module.split(".")[0])
    assert not ithal & {"requests", "urllib", "http", "socket", "httpx"}, (
        "yayın planı/işaretleme salt YEREL olmalı: %s" % (ithal,))


def test_isaretleme_ciktisi_cp1254_konsolda_cokmuyor(tmp_path):
    """Yeni çıktı yolları da `_cikti_utf8()` korumasından geçmeli.

    Windows'ta `sys.stdout.encoding` ANSI kod sayfası (`cp1254`) oluyor;
    işaretleme mesajları Türkçe harf taşıyor ve engel satırları emoji'ye kadar
    uzanabiliyor. `_cikti_utf8()` `main()`'in İLK satırı olmasaydı bu komut
    tam mesaj satırında `UnicodeEncodeError` ile çökerdi — düzeltilen arızanın
    aynısı yeni yolda tekrarlanmasın.
    """
    p = tmp_path / "Şarkı Adı"
    (p / "output").mkdir(parents=True)
    (p / "state.json").write_text(
        json.dumps({"tiktok_publish_id": "v_inbox~1"}, ensure_ascii=False),
        encoding="utf-8")
    ortam = dict(os.environ, PYTHONIOENCODING="cp1254")
    sonuc = subprocess.run(
        [sys.executable, os.path.join(_UPLOAD, "tiktok_publish_plan.py"),
         "--yayinlandi", str(p)],
        capture_output=True, env=ortam, cwd=_REPO)
    assert sonuc.returncode == 0, sonuc.stderr.decode("utf-8", "replace")
    cikti = sonuc.stdout.decode("utf-8", "replace")
    assert "işaretlendi" in cikti, cikti
    with open(p / "state.json", "r", encoding="utf-8") as f:
        assert json.load(f)["tiktok_published_at"]


def test_cli_hatada_sifirdan_farkli_cikis_kodu(tmp_path):
    """Betikten çağrılabilen bir komut, sessizce başarılı görünmemeli."""
    sonuc = subprocess.run(
        [sys.executable, os.path.join(_UPLOAD, "tiktok_publish_plan.py"),
         "--yayinlandi", str(tmp_path / "Yok Boyle Proje")],
        capture_output=True, cwd=_REPO)
    assert sonuc.returncode == 2
    assert b"HATA" in sonuc.stdout
