# -*- coding: utf-8 -*-
"""TikTok ELLE yayın planı politika kapısından geçiyor mu?

NEDEN VAR (2026-09-12): `uyumluluk.kontrol()` bu depoda İKİ yerde otomatik
çalışıyor — render'dan önce (`render.py` → `validate_project.py`) ve
yüklemeden önce (`auto_process.py` / `dj_famous_process.py`). TikTok yayını
ise TASARIM GEREĞİ o hattın dışında: boru hattı videoyu yalnızca TASLAK olarak
gelen kutusuna yüklüyor, canlıya çıkaran adım ELLE yapılıyor ve metinleri
`upload/tiktok_publish_plan.py` üretiyor. Yani kapı, yayına çıkmadan önce
hiçbir yerden kontrol edilmeyen TEK yolu kapsamıyordu.

Bedeli 2026-09-12 kuru taramasında ölçüldü — bekleyen 20 taslağın ikisi
`hazir: True` diyordu ve ikisi de yayınlanmamalıydı:
  * `dj_sets/City Pulse Set` — state.json'ında `telif_eser`
    ("Bring Me To Life - Tiesto, FORS") ve 4 `telif_araliklari` kayıtlı;
    `uyumluluk.kontrol(..., "yukleme")` bu proje için HATA veriyor.
  * `projects/Küllerimden Geç` — `Yeniden Doğacağım` ile `audio.wav` md5'i
    eşit; YouTube'da bilerek liste dışı, ama TikTok'ta İKİSİ de taslakta.
    `buyume_kontrol_listesi.md` A4 "20 taslağı yayınla" diyor; "ikisi aynı
    ses" uyarısı yalnızca düz metin olarak orada duruyordu.

Bu dosya iki kapıyı da DAVRANIŞ olarak doğruluyor (çağrının varlığını değil):
uydurma bir katalog kurup `build_plan()`'in gerçekten `hazir=False` dediğini
kontrol ediyor. Yanlış pozitif de aynı derecede önemli — temiz bir projenin
hâlâ `hazir=True` kalması ayrı bir testte.
"""

import json
import os
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_UPLOAD = os.path.join(_REPO, "upload")
for _yol in (_REPO, _UPLOAD):
    if _yol not in sys.path:
        sys.path.insert(0, _yol)

import tiktok_publish_plan as TPP
import uyumluluk


def _proje(kok, ad, durum=None, meta=None, ses=b"ayni-ses-baytlari",
           video=True):
    """Diskte minimal ama GERÇEKÇİ bir proje klasörü kurar."""
    p = kok / ad
    p.mkdir(parents=True, exist_ok=True)
    (p / "state.json").write_text(
        json.dumps(durum or {}, ensure_ascii=False), encoding="utf-8")
    (p / "meta.json").write_text(
        json.dumps(meta or {"title": ad, "theme": "pop"}, ensure_ascii=False),
        encoding="utf-8")
    if ses is not None:
        (p / "audio.wav").write_bytes(ses)
    if video:
        cikti = p / "output"
        cikti.mkdir(exist_ok=True)
        (cikti / TPP.VIDEO_ADI).write_bytes(b"sahte-mp4")
    return str(p)


@pytest.fixture
def kok(tmp_path, monkeypatch):
    """Kapının taradığı içerik kökünü geçici klasöre çeker.

    `uyumluluk.KOKLER` MUTLAK yollar tutuyor (göreli olsaydı yanlış cwd'de
    `os.path.isdir` False döner ve kapı kendiliğinden AÇILIRDI — bkz.
    CLAUDE.md). Burada da mutlak yol veriliyor, yani test gerçek katalogdan
    tamamen izole.
    """
    k = tmp_path / "projects"
    k.mkdir()
    monkeypatch.setattr(uyumluluk, "KOKLER", (str(k),))
    return k


# --- 1. Telif kaydı olan bir taslak yayınlanmamalı -------------------------

def test_telif_kaydi_olan_proje_engelleniyor(kok):
    """City Pulse Set'in canlı karşılığı: `uyumluluk` HATA diyor, plan da demeli."""
    p = _proje(kok, "Telifli Set", durum={
        "telif_eser": "Bring Me To Life - Tiesto, FORS",
        "telif_araliklari": [[10, 20]],
        "tiktok_publish_id": "v_inbox~1",
        "youtube_video_id": "abc123",
        "youtube_privacy": "public",
    })
    plan = TPP.build_plan(p)
    assert plan["hazir"] is False
    assert "telif" in (plan["engel"] or "").lower()
    assert plan["uyumluluk_hatalari"], "hata listesi plana da yazılmalı"


# --- 2. Aynı sesin iki taslağı: sadece meşru taraf yayınlanabilir ----------

def _ikiz_katalog(kok):
    """Küllerimden Geç / Yeniden Doğacağım ikilisinin sadeleştirilmiş hâli."""
    orijinal = _proje(kok, "Orijinal", durum={
        "youtube_video_id": "aaa", "youtube_privacy": "public",
        "tiktok_publish_id": "v_inbox~orijinal",
        "kopya_notu": "aynı kaydın iki ismi",
    })
    kopya = _proje(kok, "Kopya", durum={
        "youtube_video_id": "bbb", "youtube_privacy": "unlisted",
        "tiktok_publish_id": "v_inbox~kopya",
        "kopya_notu": "aynı kaydın iki ismi",
    })
    return orijinal, kopya


def test_public_olmayan_taraf_engelleniyor(kok):
    orijinal, kopya = _ikiz_katalog(kok)
    plan = TPP.build_plan(kopya)
    assert plan["hazir"] is False
    assert "Orijinal" in plan["engel"]


def test_public_taraf_hazir_ama_ikizi_isimle_uyariliyor(kok):
    """Meşru taraf DURDURULMAMALI — yoksa kapı doğru olanı da kilitler."""
    orijinal, kopya = _ikiz_katalog(kok)
    plan = TPP.build_plan(orijinal)
    assert plan["hazir"] is True
    assert any("Kopya" in u and "TASLAKTA KALMALI" in u
               for u in plan["uyumluluk_uyarilari"]), (
        "operatör hangi taslağın yayınlanmayacağını ADIYLA görmeli")


def test_ikisi_de_public_degilse_ikisi_de_engelleniyor(kok):
    """`uyumluluk`'un aynı durumdaki davranışı: operatör ayırt edene kadar dur."""
    a = _proje(kok, "A", durum={"youtube_privacy": "unlisted",
                                "tiktok_publish_id": "v_inbox~a"})
    b = _proje(kok, "B", durum={"youtube_privacy": "unlisted",
                                "tiktok_publish_id": "v_inbox~b"})
    assert TPP.build_plan(a)["hazir"] is False
    assert TPP.build_plan(b)["hazir"] is False


def test_ikiz_tiktokta_zaten_yayinlanmissa_engel(kok):
    """En ağır durum: aynı ses TikTok'ta CANLI, ikincisi yayına girmemeli."""
    _proje(kok, "Canli", durum={"youtube_privacy": "public",
                                "tiktok_publish_id": "v_inbox~canli",
                                "tiktok_published_at": "2026-09-01T10:00:00"})
    ikinci = _proje(kok, "Ikinci", durum={"youtube_privacy": "public",
                                          "tiktok_publish_id": "v_inbox~2"})
    plan = TPP.build_plan(ikinci)
    assert plan["hazir"] is False
    # `engel` bu kurguda `uyumluluk`'un md5 HATA'sı oluyor (iki taraf da
    # işaretsiz) — TikTok kapısının kendi cümlesi listede aranıyor, çünkü
    # test edilen şey "hangi cümle ilk sırada" değil, kapının ÇALIŞMASI.
    assert any("ZATEN yayınlanmış" in h for h in plan["uyumluluk_hatalari"])


def test_ikiz_tiktoka_hic_yuklenmemisse_engel_yok(kok):
    """Aynı ses diskte duruyor ama TikTok'ta hiç taslağı yok: çakışma da yok.

    Yanlış pozitif koruması — `uyumluluk` bu durumu zaten kendi kuralıyla
    değerlendiriyor, TikTok kapısının ayrıca kilitlemesi için sebep yok.
    """
    _proje(kok, "Arsiv", durum={"youtube_privacy": "unlisted",
                                "kopya_notu": "bilinen kopya"})
    canli = _proje(kok, "Canli", durum={"youtube_video_id": "aaa",
                                        "youtube_privacy": "public",
                                        "kopya_notu": "bilinen kopya",
                                        "tiktok_publish_id": "v_inbox~canli"})
    plan = TPP.build_plan(canli)
    ikiz_engelleri = [h for h in plan["uyumluluk_hatalari"] if "md5" in h]
    assert not ikiz_engelleri


# --- 3. Yanlış pozitif YOK ------------------------------------------------

def test_temiz_proje_hazir_kalir(kok):
    """Kapı eklendi diye sıradan bir taslak kilitlenmemeli."""
    p = _proje(kok, "Temiz Sarki", durum={
        "youtube_video_id": "xyz", "youtube_privacy": "public",
        "tiktok_publish_id": "v_inbox~temiz",
    }, ses=b"bu-sesin-ikizi-yok")
    plan = TPP.build_plan(p)
    assert plan["hazir"] is True, plan["engel"]
    assert plan["uyumluluk_hatalari"] == []
    assert plan["caption"], "caption üretimi kapı yüzünden bozulmamalı"


# --- 4. Kapı çökerse SESSİZCE AÇILMAMALI ----------------------------------

def test_kapi_coktugunde_yayin_durur(kok, monkeypatch):
    """CLAUDE.md: sessizce False dönen bir koruma, OLMAYAN korumadan KÖTÜDÜR.

    Kapı bir istisnayla çökerse plan yine üretilmeli (operatör caption'ı
    görebilmeli) ama `hazir` kesinlikle False olmalı ve sebebi yazmalı.
    """
    p = _proje(kok, "Temiz Sarki", durum={"youtube_privacy": "public"},
               ses=b"tek-basina")

    def patlat(*a, **k):
        raise RuntimeError("kapı bozuk")

    monkeypatch.setattr(uyumluluk, "kontrol", patlat)
    plan = TPP.build_plan(p)
    assert plan["hazir"] is False
    assert "ÇALIŞTIRILAMADI" in plan["engel"]
    assert plan["caption"], "kapı çökse de plan basılabilmeli"


# --- 5. Caption GERÇEKTEN basılabiliyor mu (Windows kod sayfası tuzağı) ----

def test_emoji_iceren_cikti_cp1254_konsolda_cokmuyor():
    """Bu modülün var olma sebebi caption'ı BASMAK — ve basamıyordu.

    NEDEN VAR (2026-09-12, üretim makinesinde ölçüldü): Windows'ta
    `sys.stdout.encoding` ANSI kod sayfası (`cp1254`) oluyor ve üretilen HER
    caption `config.HOOK_LINES`'tan gelen bir emoji taşıyor. Emoji cp1254'te
    yok, yani hem düz hem `--json` çıktısı tam caption satırında
    `UnicodeEncodeError` ile çöküyordu. Modül "caption'ı uydurma, buradan al"
    demek için var; caption hiç basılamayınca geriye uydurmak kalıyordu.

    Test gerçek konsolu taklit etmek yerine aynı koşulu deterministik olarak
    kuruyor: alt süreçte `PYTHONIOENCODING=cp1254`. `_cikti_utf8()`
    çağrılmazsa bu alt süreç çöker (düzeltmeden ÖNCEKİ davranış).
    """
    import subprocess

    kod = (
        "import sys, os\n"
        "sys.path.insert(0, %r)\n"
        "sys.path.insert(0, %r)\n"
        "import tiktok_publish_plan as T\n"
        "T._cikti_utf8()\n"
        "print('Küllerin altında hâlâ kor var \U0001f525')\n"
    ) % (_REPO, _UPLOAD)
    ortam = dict(os.environ, PYTHONIOENCODING="cp1254")
    p = subprocess.run([sys.executable, "-c", kod], capture_output=True,
                       env=ortam)
    assert p.returncode == 0, p.stderr.decode("utf-8", "replace")
    cikti = p.stdout.decode("utf-8", "replace")
    assert "\U0001f525" in cikti, "emoji kaybolmamalı (caption birebir kopyalanıyor)"
    assert "hâlâ" in cikti, "Türkçe harfler bozulmamalı"
