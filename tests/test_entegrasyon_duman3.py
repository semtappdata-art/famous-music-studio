# -*- coding: utf-8 -*-
"""ÜÇÜNCÜ entegrasyon duman testi — ikinci duman koşusundan (2026-09-11 ~19:10)
SONRA değişen 14 alanın modüller ARASINDAKİ sözleşmeleri.

NEDEN AYRI BİR DOSYA: `tests/test_entegrasyon_duman.py` ve `..._duman2.py`
kendi koşularının bulduğu kırıkları koruyor ve DEĞİŞTİRİLMEDİ. Onlardan sonra
60'tan fazla ajan çalıştı ve şu alanlar değişti; hiçbiri BİRLİKTE
doğrulanmamıştı (2026-09-12 gece kapanış koşusu):

  1. `upload/ag_yeniden_deneme.py` (yeni) — ağ istisnası sınıflandırması;
     Telegram/Bluesky/Facebook yükleyicileri + iki süpürge buna bağlandı.
     Buradaki testler yükleyici ile süpürgeyi AYNI projede, art arda koşturur:
     "işaretli proje süpürgede aday olmuyor VE yükleyici tek istek atmıyor".
  2. `upload/tiktok_publish_plan.py` — politika kapısı + ikiz kapısı +
     `--yayinlandi-hepsi --dry-run` + cp1254 konsol (alt süreçte).
  3. `saglik_kontrol.kontrol_et()` — SEKİZ adım birlikte (Instagram token,
     Netlify, görev tanımları, ses takibi, git senkronu, yayın durgunluğu,
     üretim kuyruğu, kaçan koşu); görev
     tanımı verisi bu makineden 2026-09-12 01:00'de SALT OKUMA ile alınan
     GERÇEK şekil (bozuk). `kacan_kosu` (2026-09-12) bu fikstürde ilk koşudur —
     durum dosyası tmp'de ve boş, yani damga yok: sessizce damgalar, bildirim
     göndermez (kendi testleri: tests/test_kacan_kosu.py). `git_senkron`
     (2026-09-12) da aynı sebeple bu fikstürde bildirim göndermez: damgası yok,
     yani "ilk gözlem" (kendi testleri:
     tests/test_git_senkron_uyarisi.py).
  4. `gorev_sarmalayici.py` — üç damga sözleşmesi.
  5. `dj_clips.supur(dry_run=True)` — gerçek üç setin durum şekli + bir uygun set.
  6. `upload/youtube_playlists.durum()` — eksik / yanlış üyelik / mükerrer.
  7. `stock_art.find_lyrics_file` — ön-ek uzunluk koruması ("Neon" -> None).
  8. `caption_align` — `İ` normalizasyonu + `LyricsMismatch` eşiği.
  9. `olcum_temel_cizgi --dry-run` — 14 bölüm, hiçbir dosya yazılmaz.
 10. `subprocess` kodlaması — kaynak taraması + bilerek başarısız ffmpeg.
 11. `derleme.adaylar()` — md5 kopya eleme (privacy filtresi bypass edilse bile).
 12. `gizli_maskele` — `token` anahtarı + `nfp_` deseni.

AĞA ÇIKMIYOR, hiçbir platforma yükleme yapmıyor, gerçek `projects/`,
`dj_sets/`, `derlemeler/` klasörlerine YAZMIYOR (salt okuma olan iki test —
stock_art ve olcum dry-run — gerçek kataloğu yalnızca OKUR). `os.path.isfile`
sahtelenmiyor: bu makinede gerçek token dosyaları duruyor.
"""

import ast
import hashlib
import io
import json
import os
import subprocess
import sys
import time

import pytest

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_UPLOAD = os.path.join(_KOK, "upload")
for _yol in (_KOK, _UPLOAD):
    if _yol not in sys.path:
        sys.path.insert(0, _yol)

import requests   # noqa: E402
import urllib3    # noqa: E402

import ag_yeniden_deneme as ag   # noqa: E402
import uyumluluk                 # noqa: E402


# ===========================================================================
# ortak yardımcılar
# ===========================================================================

def _proje(kok, ad, durum=None, meta=None, ses=b"ses-baytlari",
           videolar=("output/youtube_16x9.mp4", "output/shorts_9x16.mp4")):
    """Diskte minimal ama gerçekçi bir proje klasörü."""
    p = kok / ad
    p.mkdir(parents=True, exist_ok=True)
    (p / "state.json").write_text(json.dumps(durum or {}, ensure_ascii=False),
                                  encoding="utf-8")
    (p / "meta.json").write_text(
        json.dumps(meta or {"title": ad, "theme": "pop"}, ensure_ascii=False),
        encoding="utf-8")
    if ses is not None:
        (p / "audio.wav").write_bytes(ses)
    for rel in videolar:
        h = p / rel
        h.parent.mkdir(parents=True, exist_ok=True)
        h.write_bytes(b"0" * 1024)
    return str(p)


def _durum(proje):
    with open(os.path.join(proje, "state.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def _md5(yol):
    with open(yol, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


class SahteYanit:
    def __init__(self, status_code=200, govde=None, text=""):
        self.status_code = status_code
        self._govde = {} if govde is None else govde
        self.text = text or json.dumps(self._govde)

    def json(self):
        return self._govde

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError("HTTP %d" % self.status_code)


class SahteHTTP:
    """Sıraya dizilmiş sonuçlar; liste biterse SON eleman tekrarlanır.
    Boş kuyrukta çağrı = HATA: "hiç istek çıkmamalı" iddiası böyle kanıtlanıyor."""

    exceptions = requests.exceptions

    def __init__(self, post=None, get=None):
        self._post = list(post or [])
        self._get = list(get or [])
        self.post_cagrilari = []
        self.get_cagrilari = []

    @staticmethod
    def _ver(kuyruk):
        if not kuyruk:
            raise AssertionError("sahte HTTP: beklenmeyen çağrı — hiç istek çıkmamalıydı")
        oge = kuyruk.pop(0) if len(kuyruk) > 1 else kuyruk[0]
        if isinstance(oge, BaseException):
            raise oge
        return oge

    def post(self, url, **kw):
        self.post_cagrilari.append((url, kw))
        return self._ver(self._post)

    def get(self, url, **kw):
        self.get_cagrilari.append((url, kw))
        return self._ver(self._get)


def baglanti_kurulamadi():
    """requests'in GERÇEK şekli: ConnectionError(MaxRetryError(reason=NewConnectionError))."""
    return requests.exceptions.ConnectionError(
        urllib3.exceptions.MaxRetryError(
            pool=None, url="https://ornek/x",
            reason=urllib3.exceptions.NewConnectionError(None, "DNS yok")))


def govdeden_sonra_koptu():
    return requests.exceptions.ReadTimeout("yanıt gelmedi")


@pytest.fixture(autouse=True)
def _beklemeden(monkeypatch):
    """Geri çekilme beklemeleri (2 sn + 4 sn) testte sıfır."""
    monkeypatch.setattr(ag, "TABAN_BEKLEME", 0)


@pytest.fixture
def katalog(tmp_path, monkeypatch):
    """Tek bir `projects/` kökü; kanonik liste ve İKİ süpürge de ona bakıyor.

    `facebook_backfill.BASE` / `ek_platform_backfill.BASE` import ANINDA
    `uyumluluk.KOKLER`'den kopyalanıyor (bkz. duman2), o yüzden üçü ayrı ayrı
    yönlendiriliyor — biri unutulursa süpürge GERÇEK kataloğu tarar.
    """
    kok = tmp_path / "projects"
    kok.mkdir()
    import ek_platform_backfill
    import facebook_backfill
    monkeypatch.setattr(uyumluluk, "KOKLER", (str(kok),))
    monkeypatch.setattr(ek_platform_backfill, "BASE", (str(kok),))
    monkeypatch.setattr(facebook_backfill, "BASE", (str(kok),))
    return kok


YAYINDA = {"youtube_video_id": "vidA", "youtube_uploaded_at": "2026-09-10T12:00:00",
           "youtube_privacy": "public"}


# ===========================================================================
# 1. YENİDEN DENEME YARDIMCISI — yükleyici + süpürge, üç platform
# ===========================================================================

@pytest.fixture
def telegram(monkeypatch):
    import telegram_upload as tg
    monkeypatch.setattr(tg, "_load_credentials",
                        lambda: {"bot_token": "111:SAHTE", "chat_id": "@sahtekanal"})
    monkeypatch.setattr(tg, "_probe_dimensions", lambda p: (1920, 1080))
    monkeypatch.setattr(tg, "_probe_duration", lambda p: 42)

    class _Zaman:
        sleep = staticmethod(lambda sn: None)
        strftime = staticmethod(time.strftime)

    monkeypatch.setattr(tg, "time", _Zaman)
    return tg


TG_BASARI = SahteYanit(200, {"ok": True, "result": {"message_id": 4242}})


def test_telegram_connecttimeout_yeniden_denenir(telegram, katalog, monkeypatch):
    p = _proje(katalog, "Sarki", durum=dict(YAYINDA))
    http = SahteHTTP(post=[requests.exceptions.ConnectTimeout("x"), TG_BASARI])
    monkeypatch.setattr(telegram, "requests", http)
    assert telegram.upload_video(p, kind="uzun") == 4242
    assert len(http.post_cagrilari) == 2
    assert ag.ISARET_ALANI not in _durum(p)


def test_telegram_readtimeout_denenmez_isaret_supurge_ve_yukleyici_kapali(
        telegram, katalog, monkeypatch):
    """Tek projede ZİNCİR: belirsiz kalır -> süpürge aday saymaz -> yükleyici
    hiç istek atmaz -> operatör temizler -> yeniden yüklenebilir."""
    import ek_platform_backfill as EPB
    p = _proje(katalog, "Sarki", durum=dict(YAYINDA))
    telegram_video = os.path.join("output", "youtube_16x9.mp4")

    # Başlangıçta süpürge bu projeyi ADAY görüyor (kontrol grubu).
    assert EPB.eksik_projeler("telegram_message_id", telegram_video) == [p]

    http = SahteHTTP(post=[govdeden_sonra_koptu()])
    monkeypatch.setattr(telegram, "requests", http)
    with pytest.raises(ag.BelirsizSonuc):
        telegram.upload_video(p, kind="uzun")
    assert len(http.post_cagrilari) == 1, "gövde gittikten sonra İKİNCİ sendVideo yok"
    st = _durum(p)
    assert "telegram_message_id" not in st
    assert st[ag.ISARET_ALANI]["telegram_message_id"]["istisna"] == "ReadTimeout"

    # SÜPÜRGE: işaretli proje aday listesine HİÇ girmiyor.
    assert EPB.eksik_projeler("telegram_message_id", telegram_video) == [], (
        "belirsiz işaretli proje süpürgede aday olmamalı — yoksa limit=1'lik "
        "slot her koşuda bu projeye takılır")

    # YÜKLEYİCİ: kim çağırırsa çağırsın tek bir istek bile çıkmıyor.
    monkeypatch.setattr(telegram, "requests", SahteHTTP())     # boş kuyruk = çağrı patlar
    with pytest.raises(ag.BelirsizSonuc):
        telegram.upload_video(p, kind="uzun")

    # Operatör kanala bakıp "gönderi yok" dedi: temizle -> yeniden aday + yüklenir.
    assert ag.belirsizi_temizle(p, "telegram_message_id") is True
    assert EPB.eksik_projeler("telegram_message_id", telegram_video) == [p]
    monkeypatch.setattr(telegram, "requests", SahteHTTP(post=[TG_BASARI]))
    assert telegram.upload_video(p, kind="uzun") == 4242


def test_bluesky_connecttimeout_denenir_readtimeout_dogrulanamazsa_isaret(
        katalog, monkeypatch):
    """Bluesky'ın send_post sarmalayıcısıyla BİREBİR aynı sözleşme
    (cagri=send_post, dogrula=_gonderi_zaten_var_mi)."""
    import bluesky_upload as bs
    p = _proje(katalog, "Sarki", durum=dict(YAYINDA))

    class _Gonderi:
        uri = "at://did:plc:x/app.bsky.feed.post/yeni"
        cid = "bafyeni"

    def _kos(hatalar, get_kuyrugu):
        monkeypatch.setattr(bs, "requests", SahteHTTP(get=get_kuyrugu))
        sayac = {"n": 0}

        def _send_post():
            sayac["n"] += 1
            h = hatalar[sayac["n"] - 1] if sayac["n"] <= len(hatalar) else None
            if h:
                raise h
            return _Gonderi()

        sonuc = ag.guvenli_istek(
            _send_post, ne="Bluesky createRecord (send_post)",
            dogrula=lambda: bs._gonderi_zaten_var_mi("https://pds", "did:plc:x", "m"),
            proje=p, anahtar="bluesky_post_uri", platform="Bluesky",
            log=lambda *a, **k: None)
        return sonuc, sayac["n"]

    # bağlantı kurulamadı -> yeniden denendi
    sonuc, n = _kos([requests.exceptions.ConnectTimeout("x"), None], [])
    assert n == 2 and sonuc.uri.endswith("/yeni")
    assert ag.ISARET_ALANI not in _durum(p)

    # gövdeden sonra koptu + doğrulama okunamadı -> DENENMEDİ, işaret
    with pytest.raises(ag.BelirsizSonuc):
        _kos([govdeden_sonra_koptu()], [requests.exceptions.ConnectionError("ağ yok")])
    st = _durum(p)
    assert "bluesky_post_uri" not in st
    assert st[ag.ISARET_ALANI]["bluesky_post_uri"]["platform"] == "Bluesky"


def test_bluesky_isaretli_proje_supurgede_yok_ve_yukleyici_istek_atmiyor(
        katalog, monkeypatch):
    import bluesky_upload as bs
    import ek_platform_backfill as EPB
    p = _proje(katalog, "Sarki", durum=dict(YAYINDA))
    bluesky_video = os.path.join("output", "shorts_9x16.mp4")
    assert EPB.eksik_projeler("bluesky_post_uri", bluesky_video) == [p]

    ag.belirsiz_isaretle(p, "bluesky_post_uri", "Bluesky", "send_post",
                         "ReadTimeout", log=lambda *a: None)
    assert EPB.eksik_projeler("bluesky_post_uri", bluesky_video) == []
    monkeypatch.setattr(bs, "requests", SahteHTTP())
    with pytest.raises(ag.BelirsizSonuc):
        bs.upload_video(p)      # kapı ffprobe'dan ve atproto'dan ÖNCE


@pytest.fixture
def facebook(monkeypatch):
    import facebook_upload as fb
    monkeypatch.setattr(fb, "get_access_token",
                        lambda: {"page_id": "SAHTEPAGE",
                                 "page_access_token": "SAHTE_PAGE_TOKEN"})
    return fb


def test_facebook_uzun_connecttimeout_denenir_readtimeout_dogrulanamazsa_isaret(
        facebook, katalog, monkeypatch):
    p = _proje(katalog, "Sarki", durum=dict(YAYINDA))
    # Kuyruk: [ConnectTimeout, /videos başarı, YouTube-linki yorumu başarı].
    # `upload_long` yüklemeden SONRA bir de yorum POST'u atıyor; sayım
    # yalnızca /videos uç noktasına bakıyor.
    http = SahteHTTP(post=[requests.exceptions.ConnectTimeout("x"),
                           SahteYanit(200, {"id": "V_UZUN"}),
                           SahteYanit(200, {"id": "YORUM"})])
    monkeypatch.setattr(facebook, "requests", http)
    assert facebook.upload_long(p, schedule=False) == "V_UZUN"
    video_postlari = [u for u, _ in http.post_cagrilari if u.endswith("/videos")]
    assert len(video_postlari) == 2, "bağlantı kurulamadı -> /videos bir kez yeniden denenmeli"

    p2 = _proje(katalog, "Sarki2", durum=dict(YAYINDA))
    http = SahteHTTP(post=[govdeden_sonra_koptu()],
                     get=[requests.exceptions.ConnectionError("ağ yok")])
    monkeypatch.setattr(facebook, "requests", http)
    with pytest.raises(ag.BelirsizSonuc):
        facebook.upload_long(p2, schedule=False)
    assert len(http.post_cagrilari) == 1
    assert ag.belirsiz_mi(p2, "facebook_video_id") is not None


def test_facebook_isaretli_proje_supurgede_yok_ve_reels_istek_atmiyor(
        facebook, katalog, monkeypatch):
    import facebook_backfill as FB
    p = _proje(katalog, "Sarki", durum=dict(YAYINDA))
    assert FB.eksik_projeler() == [p]

    ag.belirsiz_isaretle(p, "facebook_reels_id", "Facebook",
                         "Facebook Reels faz 3 (finish)", "ReadTimeout",
                         log=lambda *a: None)
    assert FB.eksik_projeler() == []
    monkeypatch.setattr(facebook, "requests", SahteHTTP())
    with pytest.raises(ag.BelirsizSonuc):
        facebook.upload_reels(p, schedule=False)


# ===========================================================================
# 2. TİKTOK PLANI — kapılar + toplu kuru mod + cp1254 alt süreç
# ===========================================================================

def _tiktok_katalogu(kok):
    """Gerçek kataloğun sadeleştirilmiş şekli: ikiz çift + telifli set + temiz."""
    ayni_ses = b"ayni-ses-baytlari-0123456789"
    orijinal = _proje(kok, "Orijinal", ses=ayni_ses, durum={
        "youtube_video_id": "aaa", "youtube_privacy": "public",
        "tiktok_publish_id": "v_inbox~orijinal", "kopya_notu": "aynı kaydın iki ismi"})
    kopya = _proje(kok, "Kopya", ses=ayni_ses, durum={
        "youtube_video_id": "bbb", "youtube_privacy": "unlisted",
        "tiktok_publish_id": "v_inbox~kopya", "kopya_notu": "aynı kaydın iki ismi"})
    telifli = _proje(kok, "Telifli Set", ses=b"telifli-ses", durum={
        "youtube_video_id": "ccc", "youtube_privacy": "public",
        "tiktok_publish_id": "v_inbox~telif",
        "telif_eser": "Bring Me To Life - Tiesto, FORS", "telif_araliklari": [[10, 20]]})
    temiz = _proje(kok, "Temiz", ses=b"temiz-ses", durum={
        "youtube_video_id": "ddd", "youtube_privacy": "public",
        "tiktok_publish_id": "v_inbox~temiz"})
    return orijinal, kopya, telifli, temiz


def test_tiktok_toplu_kuru_mod_kapilari_uyguluyor_ve_hicbir_sey_yazmiyor(
        katalog, monkeypatch, capsys):
    import tiktok_publish_plan as TPP
    orijinal, kopya, telifli, temiz = _tiktok_katalogu(katalog)
    once = {p: _md5(os.path.join(p, "state.json")) for p in (orijinal, kopya, telifli, temiz)}

    planlar = dict((os.path.basename(p), plan) for p, plan in TPP._bekleyenleri_listele())
    assert planlar["Kopya"]["hazir"] is False and "Orijinal" in planlar["Kopya"]["engel"]
    assert planlar["Telifli Set"]["hazir"] is False and "telif" in planlar["Telifli Set"]["engel"].lower()
    assert planlar["Temiz"]["hazir"] is True
    assert planlar["Orijinal"]["hazir"] is True
    assert any("Kopya" in u for u in planlar["Orijinal"]["uyumluluk_uyarilari"])

    # Etkileşimsiz kabuk + --dry-run: liste basılır, HİÇBİR şey yazılmaz.
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    assert TPP._toplu_isaretle(dry_run=True) == 0
    cikti = capsys.readouterr().out
    assert "hazir=False" in cikti
    assert {p: _md5(os.path.join(p, "state.json")) for p in once} == once, (
        "--dry-run state.json'a dokundu")


def _tiktok_alt_surec(kok, argv):
    """Modülün main()'ini cp1254 konsol koşulunda, SAHTE kökle alt süreçte koşturur.

    Gerçek kataloğa DOKUNMAZ: `uyumluluk.KOKLER` alt süreçte tmp köke çekiliyor.
    stdin kapalı (etkileşimsiz) — üretimde `< NUL` ile aynı koşul."""
    kod = (
        "import sys\n"
        "sys.path.insert(0, %r); sys.path.insert(0, %r)\n"
        "import uyumluluk; uyumluluk.KOKLER = (%r,)\n"
        "import tiktok_publish_plan as T\n"
        "sys.argv = ['tiktok_publish_plan.py'] + %r\n"
        "T.main()\n"
    ) % (_KOK, _UPLOAD, str(kok), list(argv))
    ortam = dict(os.environ, PYTHONIOENCODING="cp1254")
    return subprocess.run([sys.executable, "-c", kod], capture_output=True,
                          stdin=subprocess.DEVNULL, env=ortam, timeout=120)


def test_tiktok_cp1254_alt_surecte_toplu_kuru_ve_emoji_caption_cokmuyor(katalog):
    orijinal, kopya, telifli, temiz = _tiktok_katalogu(katalog)

    p = _tiktok_alt_surec(katalog, ["--yayinlandi-hepsi", "--dry-run"])
    err = p.stderr.decode("utf-8", "replace")
    assert p.returncode == 0, err
    assert "UnicodeEncodeError" not in err
    out = p.stdout.decode("utf-8", "replace")
    assert "hazir=False" in out and "Telifli Set" in out
    assert "HİÇBİR ŞEY yazılmadı" in out

    # --project: caption'ın (emoji taşıyan) TAMAMI basılabilmeli.
    import tiktok_publish_plan as TPP
    beklenen = TPP.build_plan(temiz)["caption"].splitlines()[0]
    p = _tiktok_alt_surec(katalog, ["--project", temiz])
    err = p.stderr.decode("utf-8", "replace")
    assert p.returncode == 0, err
    out = p.stdout.decode("utf-8", "replace")
    assert "--- caption ---" in out
    assert beklenen in out, "caption ilk satırı (emoji dahil) birebir basılmalı"


# ===========================================================================
# 3. SAĞLIK KONTROLÜ — dört adım birlikte, gerçek görev tanımı şekliyle
# ===========================================================================

# Bu makineden 2026-09-12 01:00'de `saglik_kontrol._gorev_tanimlarini_oku()`
# (Get-ScheduledTask, salt okuma) ile alınan GERÇEK çıktı. Üç görev de eski
# tanımda: sarmalayıcı yok, pil bayrakları varsayılanda. Kullanıcı ps1'i henüz
# çalıştırmadı — "bozuk" raporlanması BEKLENEN sonuç.
GERCEK_GOREV_TANIMI_2026_09_12 = [
    {"ad": "FamousMusicStudio-AutoProcess", "arg": "auto_process.py",
     "pilde_baslamasin": True, "pilde_dursun": True},
    {"ad": "FamousMusicStudio-DjFamousProcess", "arg": "dj_famous_process.py",
     "pilde_baslamasin": True, "pilde_dursun": True},
    {"ad": "FamousMusicStudio-Watcher", "arg": "watch_projects.py",
     "pilde_baslamasin": True, "pilde_dursun": True},
]


@pytest.fixture
def saglik(tmp_path, monkeypatch):
    """Ağ yok, PowerShell yok, gerçek durum/token/takip dosyası yok."""
    import types
    import saglik_kontrol as SK
    import ses_takip_denetimi as STD
    import notify

    # `netlify_kontrol` GERÇEK modül olarak İMPORT EDİLMİYOR — stub. Kalan tek
    # sebep: `main()` ağa çıkıyor. (İkinci bir sebep vardı ve 2026-09-12'de
    # kapatıldı: modül import anında `sys.stdout`'u `TextIOWrapper` ile
    # değiştiriyordu, pytest yakalamasında o sarmalayıcı GC edilince ortak tampon
    # kapanıyor ve sonraki her test "I/O operation on closed file" alıyordu — bu
    # dosyanın ilk koşusunda 32 ERROR. Artık `_cikti_utf8()` yalnız `main()`
    # içinde `reconfigure` yapıyor; koruma: tests/test_netlify_kontrol_cikti.py.)
    stub = types.ModuleType("netlify_kontrol")
    stub.main = lambda: 0
    monkeypatch.setitem(sys.modules, "netlify_kontrol", stub)

    monkeypatch.setattr(SK, "DURUM_DOSYASI", str(tmp_path / "saglik_durum.json"))
    token = tmp_path / "instagram_token.json"
    token.write_text(json.dumps({"access_token": "SAHTE", "expires_in": 30 * 86400}),
                     encoding="utf-8")
    monkeypatch.setattr(SK, "INSTAGRAM_TOKEN", str(token))
    monkeypatch.setattr(SK, "_gorev_tanimlarini_oku",
                        lambda: [dict(k) for k in GERCEK_GOREV_TANIMI_2026_09_12])
    if os.name != "nt":
        monkeypatch.setattr(os, "name", "nt")   # gorev_tanimlari'nin Windows kapısı

    # Ses takibi: tmp katalogda iki proje, tabloda yalnızca biri -> UYARI.
    kok = tmp_path / "projects"
    kok.mkdir()
    _proje(kok, "Tabloda Var", meta={"title": "Tabloda Var", "theme": "pop"}, videolar=())
    _proje(kok, "Tabloda Yok", meta={"title": "Tabloda Yok", "theme": "rock"}, videolar=())
    takip = tmp_path / "ses_ve_tarz_takibi.md"
    takip.write_text("# Takip\n\n| Şarkı | Tema | Vokal |\n|---|---|---|\n"
                     "| Tabloda Var | pop | kadın |\n"
                     "| Neon Kalp **(üretilmedi)** | pop | - |\n", encoding="utf-8")
    monkeypatch.setattr(STD, "TAKIP_DOSYASI", str(takip))
    monkeypatch.setattr(STD, "_projects_koku", lambda: str(kok))

    gonderilen = []
    monkeypatch.setattr(notify, "send",
                        lambda baslik, mesaj, *a, **k: (gonderilen.append(baslik), True)[1])
    return SK, gonderilen


def test_kontrol_et_sekiz_adimi_da_donduruyor_ve_gercek_gorev_tanimi_bozuk(
        saglik, monkeypatch):
    SK, gonderilen = saglik
    # YEDİNCİ ADIM (2026-09-12, yayin_durgunlugu) GERÇEK kataloğu okuyor
    # (`uyumluluk.proje_klasorleri()`); bu fikstürde onu sabitlemek ŞART, aksi
    # halde test makinenin o günkü yayın geçmişine göre bazen bildirim
    # gönderir ve aşağıdaki bildirim kümesi rastgele kırılırdı. Adımın kendi
    # davranışı tests/test_yayin_durgunlugu.py'de kilitli; burada denetlenen
    # tek şey `kontrol_et()`in ADIM KÜMESİ.
    monkeypatch.setattr(SK, "_yayin_taramasi", lambda: {
        "son_ts": SK.time.time(), "son_kaynak": "Sahte/youtube_uploaded_at",
        "bekleyen": ["Sahte"], "proje": 1,
    })
    loglar = []
    sonuc = SK.kontrol_et(log=loglar.append)

    assert set(sonuc) == {"instagram_token", "netlify", "gorev_tanimlari",
                          "ses_takibi", "git_senkron", "yayin_durgunlugu",
                          "uretim_kuyrugu", "kacan_kosu"}
    # Yedinci adım: taze damga -> sessiz (yanlış alarm yok).
    assert sonuc["yayin_durgunlugu"]["durum"] == "tamam"
    # SEKİZİNCİ ADIM (2026-09-12, uretim_kuyrugu_bos) yedincinin
    # TAMAMLAYICISI: ikisi aynı `_yayin_taramasi()` sonucunu okuyor ve yukarıda
    # sabitlenen fikstürde "bekleyen" DOLU (["Sahte"]) — yani kuyrukta iş var,
    # bu adım susuyor. Karşılıklı dışlamanın `kontrol_et` seviyesindeki
    # görünümü budur (adımın kendi matrisi: tests/test_uretim_kuyrugu_bos.py).
    assert sonuc["uretim_kuyrugu"]["durum"] == "kuyrukta_is_var"
    # Beşinci adım (2026-09-12): bu fikstürde damga yok -> ilk koşu, sessiz.
    assert sonuc["kacan_kosu"]["durum"] == "ilk_kosu"
    # Altıncı adım (2026-09-12, git_senkron): damgası da yok -> en fazla
    # "ilk gözlem"; bu fikstürde telefon ÇALMAMALI (aşağıdaki bildirim
    # kümesi bunu zaten kilitliyor).
    assert sonuc["git_senkron"]["durum"] in {
        "tamam", "dal_farkli", "geride_yeni", "atlandi"}
    assert sonuc["instagram_token"]["durum"] == "tamam"
    assert 28 < sonuc["instagram_token"]["kalan_gun"] <= 30
    assert sonuc["netlify"] == {"durum": "tamam"}

    g = sonuc["gorev_tanimlari"]
    assert g["durum"] == "bozuk", "gerçek tanım hâlâ eski — bozuk raporlanmalı"
    assert g["eksik"] == []
    assert len(g["sorunlar"]) == 9, "3 görev x (sarmalayıcı yok + 2 pil bayrağı)"
    for ad in SK.GOREV_BETIKLERI:
        assert g["gorevler"][ad]["sarmalayici"] is False
        assert g["gorevler"][ad]["pil_tamam"] is False
    assert any("setup_task_scheduler.ps1" in s or "sarmalayıcı" in s for s in g["sorunlar"])

    s = sonuc["ses_takibi"]
    assert s["durum"] == "uyari"
    assert s["eksik_satir"] == ["Tabloda Yok"]
    assert s["hayalet_satir"] == [], "(üretilmedi) satırı hayalet sayılmamalı"

    # Bildirimler: iki ayrı anahtar, ikisi de bir kez; log'a da düştü.
    assert sorted(gonderilen) == ["Gorev tanimlari bozuk", "Ses/tarz takibi eskimiş"]
    assert sum("gorev tanimi" in l for l in loglar) == 9
    assert any("ses/tarz takibi" in l for l in loglar)

    # Günde bir: aynı gün ikinci koşu telefonu bir daha titretmez.
    gonderilen.clear()
    SK.kontrol_et(log=lambda *a: None)
    assert gonderilen == []


def test_netlify_kontrol_import_aninda_stdoutu_degistirmemeli():
    """KIRIK (2026-09-12, üçüncü duman koşusu): `netlify_kontrol.py` modül
    düzeyinde `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, ...)` yapıyor.
    Bir kütüphane modülünün import anında süreç-genelinde `sys.stdout`'u
    değiştirmesi; `saglik_kontrol.netlify_araci()` bu modülü SAATLİK hattın
    içinde (`auto_process.main()` finally bloğu) import ediyor, yani her koşuda
    çağıranın stdout'u yerinden ediliyor. `pythonw.exe` altında `sys.stdout`
    None olduğu için üretimde bugün SESSİZ; ama pytest/konsol altında eski
    sarmalayıcı GC edilince ortak tampon kapanıyor (bu dosyanın ilk koşusunda
    32 ERROR). Doğru desen `tiktok_publish_plan._cikti_utf8()`: `reconfigure()`
    ve SADECE `main()` içinde. Kanıt alt süreçte, pytest'i bozmadan."""
    kod = (
        "import sys, io, gc\n"
        "sys.path.insert(0, %r)\n"
        "tampon = io.BytesIO(); sahte = io.TextIOWrapper(tampon, encoding='utf-8')\n"
        "gercek = sys.stdout; sys.stdout = sahte\n"
        "import netlify_kontrol\n"
        "degisti = sys.stdout is not sahte\n"
        "sys.stdout = gercek; gc.collect()\n"
        "print(degisti, tampon.closed)\n"
    ) % _KOK
    p = subprocess.run([sys.executable, "-c", kod], capture_output=True, timeout=60)
    assert p.returncode == 0, p.stderr.decode("utf-8", "replace")
    assert p.stdout.decode().split() == ["False", "False"], (
        "import sys.stdout'u değiştirdi ve/veya eski tamponu kapattı: %s" % p.stdout)


def test_gorev_tanimi_okunamazsa_sessizce_atlanir_ama_diger_adimlar_calisir(saglik, monkeypatch):
    SK, _ = saglik
    monkeypatch.setattr(SK, "_gorev_tanimlarini_oku", lambda: None)
    sonuc = SK.kontrol_et(log=lambda *a: None)
    assert sonuc["gorev_tanimlari"]["durum"] == "atlandi"
    assert sonuc["ses_takibi"]["durum"] == "uyari"


# ===========================================================================
# 4. GÖREV SARMALAYICI — üç damga
# ===========================================================================

@pytest.fixture
def izler(tmp_path, monkeypatch):
    import gorev_sarmalayici as GS
    d = tmp_path / "izler"
    monkeypatch.setattr(GS, "IZ_DIZIN", str(d))
    eski_argv, eski_path = list(sys.argv), list(sys.path)
    yield GS, d
    sys.argv[:] = eski_argv
    sys.path[:] = eski_path


def test_sarmalayici_import_hatasi_ve_olmayan_betik_uclu_damga(izler, tmp_path):
    GS, d = izler
    assert "gorev_izleri" not in GS.IZ_DIZIN
    cokuk = tmp_path / "cokuk.py"
    cokuk.write_text("import olmayan_modul_xyz\n", encoding="utf-8")

    assert GS.calistir(["gorev_sarmalayici.py", str(cokuk)]) == 1
    iz = open(GS.iz_yolu(str(cokuk)), encoding="utf-8").read()
    assert iz.count("BAŞLADI") == 1 and "ÇÖKTÜ" in iz and iz.count("BİTTİ") == 1
    assert "ModuleNotFoundError" in iz and "rc=1" in iz

    yok = str(tmp_path / "yok_boyle_betik.py")
    assert GS.calistir(["gorev_sarmalayici.py", yok]) == 2
    iz2 = open(GS.iz_yolu(yok), encoding="utf-8").read()
    assert "BAŞLADI" in iz2 and "betik bulunamadı" in iz2
    assert "BİTTİ" in iz2 and "rc=2" in iz2, (
        "betik yokken BİTTİ atlanırsa üretimde 'süreç asıldı' diye yanlış okunur")


# ===========================================================================
# 5. DJ KESİT SÜPÜRGESİ — kuru mod, gerçek üç setin durum şekli
# ===========================================================================

def _set(kok, ad, durum, kesit_dosyalari=()):
    p = kok / ad
    (p / "output").mkdir(parents=True)
    (p / "state.json").write_text(json.dumps(durum, ensure_ascii=False), encoding="utf-8")
    (p / "meta.json").write_text(json.dumps({"title": ad, "theme": "dj"}), encoding="utf-8")
    for k in kesit_dosyalari:
        (p / "output" / k).write_bytes(b"0" * 2048)
    return str(p)


@pytest.fixture
def dj_base(tmp_path):
    """2026-09-12'deki gerçek dj_sets/ şekli + BİR uygun set."""
    kok = tmp_path / "dj_sets"
    kok.mkdir()
    uc_gun_once = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() - 3 * 86400))
    _set(kok, "City Pulse Set", {"youtube_shorts_video_id": "kg2", "telif_eser": "x",
                                 "telif_araliklari": [[10, 20]],
                                 "youtube_shorts_uploaded_at": "2026-09-04T06:43:43"})
    _set(kok, "Just Relax", {"youtube_shorts_video_id": "257",
                             "youtube_shorts_uploaded_at": "2026-09-07T16:18:57",
                             "dj_clips": [{"dosya": "clip_01.mp4", "bas": 332.5, "son": 377.5, "enerji": 1}]},
         kesit_dosyalari=("clip_01.mp4",))
    _set(kok, "Night Drive", {"youtube_shorts_video_id": "nd1",
                              "youtube_shorts_uploaded_at": "2026-09-01T10:00:00"})
    _set(kok, "Uygun Set", {"youtube_shorts_video_id": "uy1", "dj_tarama_temiz": True,
                            "youtube_shorts_uploaded_at": uc_gun_once,
                            "dj_clips": [{"dosya": "clip_01.mp4", "bas": 10.0, "son": 55.0, "enerji": 2},
                                         {"dosya": "clip_02.mp4", "bas": 100.0, "son": 145.0, "enerji": 1}]},
         kesit_dosyalari=("clip_01.mp4", "clip_02.mp4"))
    return kok


def test_dj_supur_kuru_dort_sete_bakar_sebepler_ayri_yukleme_yok(dj_base, monkeypatch):
    import dj_clips
    import config
    monkeypatch.setattr(config, "DJ_ON_TARAMA", True)
    monkeypatch.setattr(dj_clips, "kesit_yayinla",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("kuru modda yükleme çağrıldı")))
    loglar = []
    s = dj_clips.supur(str(dj_base), log=loglar.append, dry_run=True)
    assert s["bakilan"] == 4
    sebepler = {a["set"]: a["sebep"] for a in s["atlanan"]}
    assert sebepler["City Pulse Set"] == "üretilmiş kesit yok"
    assert sebepler["Night Drive"] == "üretilmiş kesit yok"
    assert "Content ID taraması henüz temiz değil" in sebepler["Just Relax"]
    assert "dj_tarama_temiz" in sebepler["Just Relax"], "operatör düzeltmeyi sebepten okumalı"
    assert s["yayinlanan"] == 1 and s["kuru"]["set"] == "Uygun Set"
    assert s["kuru"]["kesit"]["dosya"] == "clip_02.mp4", "en yüksek enerjili (enerji=1) önce"
    assert any("kuru" in l for l in loglar)
    # kuru koşu state.json'a yazmadı
    assert "youtube_clip_video_id" not in json.load(
        open(os.path.join(str(dj_base), "Uygun Set", "state.json"), encoding="utf-8"))


def test_dj_clips_yayin_kuru_cli_json_basar(dj_base):
    p = subprocess.run([sys.executable, os.path.join(_KOK, "dj_clips.py"),
                        "--yayin-kuru", "--base", str(dj_base)],
                       capture_output=True, env=dict(os.environ, PYTHONIOENCODING="utf-8"),
                       timeout=120)
    assert p.returncode == 0, p.stderr.decode("utf-8", "replace")
    out = p.stdout.decode("utf-8")
    # NOT: uygun bir set varsa `supur()` (varsayılan `log=print`) JSON'dan ÖNCE
    # "  DJ kesit (kuru): ..." satırını basıyor — çıktı saf JSON değil, insan
    # için. JSON ilk '{'den itibaren okunuyor.
    assert "DJ kesit (kuru): Uygun Set" in out
    veri = json.loads(out[out.index("{"):])
    assert veri["bakilan"] == 4 and len(veri["atlanan"]) == 3
    # Sebepler AYRI satırlarda okunabilir (indent=2).
    assert out.count('"sebep":') == 3


# ===========================================================================
# 6. PLAYLIST DURUM RAPORU — eksik / yanlış üyelik / mükerrer
# ===========================================================================

class _SahtePlaylistServisi:
    def __init__(self, icerik):
        self.icerik = icerik        # playlist_id -> [video_id, ...] (tekrarlı)

    def playlistItems(self):
        return self

    def list(self, **kw):
        self._pid = kw["playlistId"]
        return self

    def execute(self):
        return {"items": [{"contentDetails": {"videoId": v}, "snippet": {"title": v},
                           "status": {"privacyStatus": "public"}}
                          for v in self.icerik.get(self._pid, [])]}

    def list_next(self, req, r):
        return None


@pytest.fixture
def playlist_ortami(tmp_path, monkeypatch):
    import youtube_playlists as YP
    kok = tmp_path / "projects"           # `_kok_adi` klasör adına bakıyor
    kok.mkdir()
    ids = {"pop": "PLpop", "_tum_sarkilar": "PLzincir", "_shorts": "PLshorts"}
    yol = tmp_path / "playlist_ids.json"
    yol.write_text(json.dumps(ids), encoding="utf-8")
    monkeypatch.setattr(YP, "PLAYLIST_IDS_PATH", str(yol))
    monkeypatch.setattr(YP, "_UYE_ONBELLEK", {})
    monkeypatch.setattr(YP, "_OGE_ONBELLEK", {})
    _proje(kok, "A", durum={"youtube_video_id": "V1", "youtube_privacy": "public",
                            "youtube_shorts_video_id": "S1", "youtube_shorts_privacy": "public"},
           videolar=())
    _proje(kok, "B", durum={"youtube_video_id": "V2", "youtube_privacy": "public"}, videolar=())
    return YP, kok


def _durum_raporu(YP, kok, icerik, monkeypatch, capsys):
    monkeypatch.setattr(YP, "get_authenticated_service", lambda: _SahtePlaylistServisi(icerik))
    YP.durum(base_list=(str(kok),))
    return capsys.readouterr().out


def test_playlist_durum_tutarli_katalogda_uc_sayac_sifir(playlist_ortami, monkeypatch, capsys):
    YP, kok = playlist_ortami
    out = _durum_raporu(YP, kok, {"PLpop": ["V1", "V2"], "PLzincir": ["V1", "V2"],
                                  "PLshorts": ["S1"]}, monkeypatch, capsys)
    assert "toplam eksik: 0" in out and "toplam fazla: 0" in out and "toplam mükerrer: 0" in out


def test_playlist_durum_eksik_yanlis_uyelik_ve_mukerreri_ayri_sayiyor(
        playlist_ortami, monkeypatch, capsys):
    YP, kok = playlist_ortami
    out = _durum_raporu(YP, kok, {"PLpop": ["V1", "V1"],          # mükerrer
                                  "PLzincir": ["V1"],
                                  "PLshorts": ["S1", "V1"]},      # V1 Shorts listesinde: YANLIŞ
                        monkeypatch, capsys)                       # V2 hiçbir listede: EKSİK
    assert "toplam eksik: 1" in out and "V2" in out
    assert "toplam fazla: 1" in out and "-> _shorts" in out
    assert "toplam mükerrer: 1" in out and "x2" in out


# ===========================================================================
# 7. SÖZLER DOSYASI EŞLEŞMESİ — ön-ek uzunluk koruması
# ===========================================================================

def test_find_lyrics_file_onek_korumasi(tmp_path, monkeypatch):
    import stock_art
    monkeypatch.setattr(stock_art, "BASE_DIR", str(tmp_path))
    for stem in ("neon_kalp", "beton_krallik", "kalbim_oynuyor"):
        (tmp_path / (stem + "_sozler.md")).write_text("# x", encoding="utf-8")
    bul = lambda t: (os.path.basename(stock_art.find_lyrics_file(t) or "") or None)
    assert bul("Neon") is None, "4/9 uzunluk oranı ön-ek dalından geçmemeli"
    assert bul("Neon Kalp") == "neon_kalp_sozler.md"
    assert bul("Kalbim Oynuyo") == "kalbim_oynuyor_sozler.md"     # ön-ek, 13/14
    assert bul("Beton Krallığı") == "beton_krallik_sozler.md"     # difflib (ünsüz yumuşaması)
    assert bul("Bambaşka Bir Şey") is None


@pytest.mark.skipif(not os.path.isdir(os.path.join(_KOK, "projects")), reason="gerçek katalog yok")
def test_find_lyrics_file_gercek_katalog_salt_okuma():
    """18 gerçek proje sözler dosyasını bulmalı; 'Neon' (neon_kalp var) None."""
    import stock_art
    eksik = [ad for ad in sorted(os.listdir(os.path.join(_KOK, "projects")))
             if not ad.startswith((".", "_"))
             and os.path.isdir(os.path.join(_KOK, "projects", ad))
             and stock_art.find_lyrics_file(ad) is None]
    assert eksik == [], "sözler dosyası bulunamayan projeler: %s" % eksik
    if os.path.isfile(os.path.join(_KOK, "neon_kalp_sozler.md")):
        assert stock_art.find_lyrics_file("Neon") is None


# ===========================================================================
# 8. ALTYAZI HİZALAMASI — İ normalizasyonu + yanlış şarkı kapısı
# ===========================================================================

def test_norm_word_turkce_buyuk_i():
    import caption_align as ca
    assert ca._norm_word("İçimde") == "içimde"
    assert "\u0307" not in ca._norm_word("İçimde"), "İ.lower() birleşen nokta üretir"
    assert ca._norm_word("IŞIK") == "ışık"


def _sozler_md(yol, satirlar):
    yol.write_text("# Şarkı\n\n## Temiz Sözler\n\n```\n" + "\n".join(satirlar) + "\n```\n",
                   encoding="utf-8")
    return str(yol)


def _asr_srt(yol, satirlar):
    parca = []
    for i, s in enumerate(satirlar, 1):
        parca.append("%d\n00:00:%02d,000 --> 00:00:%02d,500\n%s\n" % (i, (i * 3) % 60, (i * 3 + 2) % 60, s.lower()))
    yol.write_text("\n".join(parca), encoding="utf-8")
    return str(yol)


def test_yanlis_sarkinin_sozleri_LyricsMismatch_dogru_sarki_gecer(tmp_path):
    import caption_align as ca
    assert ca.MIN_ESLESME_ORANI == 0.25
    dogru = ["İçimde bir fırtına koptu bu gece", "Kumdan denize yürüdüm yalnız",
             "Dalgalar ismini fısıldadı bana", "Tuz kokan rüzgar saçlarımda kaldı"]
    yanlis = ["Beton duvarlar arasında kaybolan lambalar", "Asfaltın nefesi sırtımda",
              "Çelik köprüler altında uyuyan şehir", "Kırık camlar parlıyor ay ışığında"]
    srt = _asr_srt(tmp_path / "asr.srt", dogru)
    with pytest.raises(ca.LyricsMismatch):
        ca.align(srt, _sozler_md(tmp_path / "yanlis_sozler.md", yanlis), 30.0)
    cues = ca.align(srt, _sozler_md(tmp_path / "dogru_sozler.md", dogru), 30.0)
    assert len(cues) == 4
    assert cues[0][2].startswith("İçimde"), "İ'li kelime eşleşip zamanını ASR'den almalı"


# ===========================================================================
# 9. ÖLÇÜM PENCERESİ — --dry-run hiçbir şey yazmaz
# ===========================================================================

def test_olcum_dry_run_14_bolum_ve_disk_dokunulmaz(monkeypatch, capsys):
    import olcum_temel_cizgi as OT
    import youtube_analytics
    monkeypatch.setattr(youtube_analytics, "get_service",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("dry-run ağa çıktı")))
    monkeypatch.setattr(OT, "_SORGULAR", [])
    var = os.path.isfile(OT.TEMEL_CIZGI_PATH)
    md5_once = _md5(OT.TEMEL_CIZGI_PATH) if var else None
    dosyalar_once = sorted(f for f in os.listdir(_KOK) if f.startswith("olcum_") and f.endswith(".json"))

    assert OT.main(["--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "üretilecek bölüm sayısı: 14" in out
    assert "eksik bölüm    : yok" in out
    assert len(OT._SORGULAR) >= 14
    assert sorted(f for f in os.listdir(_KOK) if f.startswith("olcum_") and f.endswith(".json")) == dosyalar_once
    if var:
        assert _md5(OT.TEMEL_CIZGI_PATH) == md5_once, "temel çizgi değişti!"


# ===========================================================================
# 10. SUBPROCESS KODLAMASI — kaynak taraması + bilerek başarısız ffmpeg
# ===========================================================================

def _subprocess_cagrilari(dosya):
    agac = ast.parse(open(dosya, encoding="utf-8").read())
    for d in ast.walk(agac):
        if not isinstance(d, ast.Call):
            continue
        f = d.func
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) \
                and f.value.id == "subprocess" and f.attr in ("run", "check_output", "Popen", "call", "check_call"):
            yield d


def test_metin_modlu_her_subprocess_cagrisi_utf8_kodlamali():
    """`text=True` verilip `encoding` verilmezse çıktı ANSI kod sayfasıyla (cp1254)
    çözülür ve ffmpeg/git hata metinleri 'replace' olmadan UnicodeDecodeError'a
    ya da bozuk metne düşer — 2026-09-12'de 37 çağrı bu yüzden düzeltildi."""
    kirik = []
    for dizin in (_KOK, _UPLOAD):
        for ad in sorted(os.listdir(dizin)):
            if not ad.endswith(".py"):
                continue
            yol = os.path.join(dizin, ad)
            for c in _subprocess_cagrilari(yol):
                kw = {k.arg: k.value for k in c.keywords if k.arg}
                metin = any(k in kw for k in ("text", "universal_newlines"))
                if metin and "encoding" not in kw:
                    kirik.append("%s:%d" % (ad, c.lineno))
                if "encoding" in kw and isinstance(kw["encoding"], ast.Constant):
                    assert str(kw["encoding"].value).lower().replace("-", "") == "utf8", (
                        "%s:%d: encoding utf-8 değil" % (ad, c.lineno))
    assert kirik == [], "text=True ama encoding yok: %s" % kirik


def _ffmpeg_var():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=20)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


@pytest.mark.skipif(not _ffmpeg_var(), reason="ffmpeg yok")
def test_generate_cover_basarisiz_ffmpeg_stderr_metni_geliyor(tmp_path):
    """Yazılamayan bir çıktı yolu: RuntimeError'ın kuyruğu GERÇEK stderr metni olmalı,
    boş ya da 'None' değil (eskiden cp1254'te kayboluyordu)."""
    import generate_cover as gc
    with pytest.raises(RuntimeError) as hata:
        gc._radial_background(str(tmp_path / "yok" / "alt" / "x.png"), (10, 20, 30))
    kuyruk = str(hata.value).split("üretilemedi:", 1)[1].strip()
    assert kuyruk and kuyruk != "None"
    assert len(kuyruk) > 20, "stderr metni geldi ama neredeyse boş: %r" % kuyruk


# ===========================================================================
# 11. DERLEME — md5 kopya eleme (privacy konvansiyonu bypass edilse bile)
# ===========================================================================

def test_derleme_adaylar_ayni_sesi_iki_public_projede_tekine_dusuruyor(tmp_path, monkeypatch, capsys):
    import derleme
    kok = tmp_path / "projects"
    kok.mkdir()
    ayni = b"ayni-ses-" * 100
    _proje(kok, "Orijinal", ses=ayni, videolar=(), durum={
        "youtube_video_id": "a", "youtube_privacy": "public",
        "youtube_uploaded_at": "2026-09-01T10:00:00"})
    _proje(kok, "Kopya", ses=ayni, videolar=(), durum={
        "youtube_video_id": "b", "youtube_privacy": "public",      # bypass: unlisted DEĞİL
        "youtube_uploaded_at": "2026-09-07T10:00:00", "youtube_views": 999})
    _proje(kok, "Baska", ses=b"baska-ses-" * 100, videolar=(), durum={
        "youtube_video_id": "c", "youtube_privacy": "public",
        "youtube_uploaded_at": "2026-09-03T10:00:00"})
    monkeypatch.setattr(derleme, "KAYNAK", str(kok))
    monkeypatch.setattr(derleme, "_sure", lambda ses: 180.0)

    adlar = [p["ad"] for p in derleme.adaylar()]
    assert adlar == ["Baska", "Orijinal"], "kopya (ikinci yüklenen, çok izlenen) elenmeli"
    err = capsys.readouterr().err
    assert "Kopya" in err and "ELENDİ" in err and "Orijinal" in err


# ===========================================================================
# 12. MASKELEME — `token` anahtarı + `nfp_` (Netlify) deseni
# ===========================================================================

def test_maskele_token_anahtari_ve_nfp_deseni():
    import gizli_maskele as gm
    ham = ('netlify {"token": "nfp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcd"} '
           "ve access_token=EAAGm0PX4ZCpsBO7SAHTEfakeTOKEN99xyz")
    m = gm.maskele(ham)
    assert "nfp_ABCDEFGHIJ" not in m
    assert "EAAGm0PX4ZCpsBO7" not in m
    assert "netlify" in m and "access_token" in m, "satır tanılanabilir kalmalı"
