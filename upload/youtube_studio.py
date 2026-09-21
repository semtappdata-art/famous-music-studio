# -*- coding: utf-8 -*-
"""YouTube STUDIO PLANLI YÜKLEME — Studio web + "Planla" akışının KOD tarafı.

    python upload/youtube_studio.py plan-oner [--gun 10] [--json]
    python upload/youtube_studio.py paket --proje "Bu Gece Kazandık" [--uzun-id ID] [--an ISO]
        [--kapaksiz] [--json]
    python upload/youtube_studio.py isaretle --proje "Bu Gece Kazandık" --video-id ID \
        [--shorts-id ID] --an 2026-09-15T18:00:00+03:00 --sha1 <paketteki aciklama_sha1> \
        [--shorts-an ISO] [--shorts-sha1 S] [--yuklendi ISO] [--playlistler-eklendi] [--kaynak claude]
    python upload/youtube_studio.py durum [--json]

NEDEN VAR (kullanıcı kararı 2026-09-13): "YouTube'da bu ve buna benzer bekleme durumlarında
Chrome Studio'dan sıra bekletme yap." Tempo tabanı (52 sa) yüzünden bekleyen, render'ı hazır
bir şarkı YouTube Studio web'den ŞİMDİ yüklenir ve Gizli + "Planla" ile tempo kuralının izin
verdiği EN ERKEN public anına kurulur. YouTube videoyu o an kendisi açar: makine kapalı olsa
da çalışır, API yükleme kotası (videos.insert 1600 birim) harcanmaz. Örnek:
`upload/tiktok_web.py` (TikTok Studio web "Planla").

TEMPO EZİLMEZ: bu akış yalnız YÜKLEME anını öne alır; izleyicinin gördüğü PUBLIC an tempo
kurallarına tabidir (`_kural_ihlalleri` TEK kural yeri; `isaretle` kural dışı anı REDDEDER).
Karşılığı `auto_process`'te: Studio planlı projede tempo sayacı YÜKLEME damgasını değil PUBLIC
anını okur (`STUDIO_PLAN_ALANI`, `_last_upload_time`, `_son_yeni_yayin_ani`), proje public
anına kadar kuyrukta seçilmez (`_studio_planli_bekleyenleri_ayir`) ve `process_project`
Instagram/TikTok/Facebook adımına geçmez.

STATE (proje state.json, atomik `state_io`) — `isaretle` yazar:
  youtube_video_id, youtube_publish_at (UTC "...Z", `_compute_publish_at` biçimi),
  youtube_uploaded_at (gerçek yükleme anı, yerel "%Y-%m-%dT%H:%M:%S"),
  youtube_privacy = "public"  <- BİLİNÇLİ: API'nin zamanlanmış yüklemesiyle AYNI sözleşme
      (`upload_video(privacy="public")` YouTube'da private + publishAt kurar ama state'e
      "public" yazar). "private" yazılsaydı `ek_platform_backfill` / `facebook_backfill`
      (`youtube_privacy in (unlisted, private)` -> liste dışı) projeyi public olduktan sonra
      da KALICI olarak dışlardı. Studio'daki gerçek ayar kayıtta: `gorunurluk_studio`.
  youtube_studio_planli = {an, kaynak: "YouTube Studio (Chrome)", sha1, gorunurluk_studio,
      yuklendi_at, shorts_an, shorts_sha1, kaynak_kisi, isaretlendi_at, surum}
  varsa youtube_shorts_video_id / _publish_at / _uploaded_at / _privacy;
  `--playlistler-eklendi` ise youtube_playlists / youtube_playlist_id /
  youtube_shorts_playlist_id / youtube_playlists_kaynak (yoksa API senkronu sonra tamamlar).
  Deftere (`elle_islem`, `planladi`) uzun ve Shorts için birer satır.

PLANLAMA KURALLARI (`_kural_ihlalleri`):
  * golden-hour içinde (`config.GOLDEN_HOURS`, 15 dk adım), en az `MIN_DAKIKA` ileride;
  * ana katalog (projects/) yeni yayınları arası >= `auto_process.MIN_YAYIN_ARALIGI_SN` (52 sa;
    yayın anı = auto_process ile aynı türetme, `yeni_yayin_ani`);
  * DJ seti / derleme public anı ile >= `SET_SARKI_ARA_SAAT` (ozgunluk_plani R1, 48 sa);
  * aynı TR gününde başka uzun format YouTube public anı yok (tempo dışı geçişler dahil) —
    52/48 sa zaten bunu çoğunlukla sağlar; tempo dışı görünürlük planları için ek kapı;
  * Shorts: `_shorts_saat()` > 0 ise (ozgunluk_plani R3 kodlandığında) uzun formattan o kadar
    sonra, değilse aynı an (bugünkü API yolu da aynı anda yüklüyor).
  Aday: projects/ altında, render hazır, `youtube_video_id` ve Studio kaydı yok, `yayin_beklet`
  yok, uyumluluk (yukleme) temiz VE saatlik hattın bir sonraki API anı tempo tabanına takılıyor.

ToS: YouTube Hizmet Şartları otomatik erişimi yasaklıyor — zamanlanmış tarayıcı otomasyonu YOK;
bu modül tarayıcı AÇMAZ, API çağırmaz. Studio işini kullanıcı başlatınca Claude Code yapar.

ÜÇ SORU:
  1. Kim çağırıyor? Plan/paket/işaret: kullanıcı başlattığında Claude oturumu (CLI).
     Bildirim + özet satırı: `auto_process.main()` finally -> `_youtube_studio_sirasi()` ->
     `plan_bildirimi(log)`.
  2. Hangi görev? Saatlik AutoProcess; yeni görev YOK; `_is_fully_done`'a EKLENMEDİ (kalıp B).
  3. Çalışmadığını nasıl anlarız? Her koşuda tek "  YouTube Studio planı:" log satırı;
     `tests/test_youtube_studio.py`.

YAZIM KORUMASI: `PYTEST_CURRENT_TEST` ortamında GERÇEK köklerin altındaki state'e yazma
REDDEDİLİR; bildirim test ortamında gerçek kataloğu okumaz, göndermez.
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unicodedata

_UPLOAD = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(_UPLOAD)
for _y in (REPO, _UPLOAD):
    if _y not in sys.path:
        sys.path.insert(0, _y)

import config        # noqa: E402
import state_io      # noqa: E402
import uyumluluk     # noqa: E402

# NOT: youtube_upload / youtube_playlists / elle_islem / notify fonksiyon İÇİNDE import
# ediliyor — auto_process bu modülü saatlik koşuda yüklüyor; OAuth zinciri gereksiz yere
# çekilmesin ve import döngüsü kurulmasın.

TR = config.TR_TZ
SAAT = 3600
GUN_SN = 24 * SAAT
SURUM = 1
ALAN = "youtube_studio_planli"          # auto_process.STUDIO_PLAN_ALANI aynası (testle kilitli)
KAYNAK = "YouTube Studio (Chrome)"
GORUNURLUK_STUDIO = "Gizli + Planla"
ADIM_DAKIKA = 15
MIN_DAKIKA = 60
KAPAK_MAX_BAYT = 2 * 1024 * 1024
_TABAN_VARSAYILAN_SN = 52 * SAAT        # auto_process.MIN_YAYIN_ARALIGI_SN (testle kilitli)
GERCEK_KOKLER = tuple(uyumluluk.KOKLER)
DURUM_DOSYASI = os.path.join(REPO, "upload", "saglik_durum.json")
BILDIRIM_GUN_DAMGASI = "youtube_studio_plan_bildirim_gun"
VIDEO_UZUN = "youtube_16x9.mp4"
VIDEO_KISA = "shorts_9x16.mp4"
_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_DIL_ADLARI = {"tr": "Türkçe", "en": "İngilizce"}


class YoutubeStudioHatasi(Exception):
    """İşaretleme/doğrulama reddi — hiçbir şey yazılmadı."""


# --------------------------------------------------------------------------
# Eşikler (config'ten, çağrı anında)
# --------------------------------------------------------------------------

def _taban_sn():
    ap = sys.modules.get("auto_process")
    return float(getattr(ap, "MIN_YAYIN_ARALIGI_SN", _TABAN_VARSAYILAN_SN))


def _ritim():
    """`yayin_ritmi` (ozgunluk_plani Aşama 1, kanal geneli ritim kuralları) — varsa TEK kaynak.
    Yoksa aynı config adlarına aynı varsayılanlarla düşülür (import zinciri kırılmasın)."""
    try:
        import yayin_ritmi
        return yayin_ritmi
    except Exception:                                        # noqa: BLE001
        return None


def _set_ara_sn():
    r = _ritim()
    if r is not None and hasattr(r, "set_sarki_ara_sn"):
        return float(r.set_sarki_ara_sn())
    return float(getattr(config, "YAYIN_RITMI_SET_SARKI_ARA_SAAT", 48)) * SAAT


def _shorts_saat():
    """R3a (Shorts uzun formatın public anından 24 sa sonra) şalteri AÇIKSA o süre, değilse 0
    (aynı an — bugünkü API yolu da uzun formatla aynı anda yüklüyor)."""
    r = _ritim()
    if r is not None and hasattr(r, "shorts_gecikmeli_mi"):
        return float(r.shorts_gecikme_sn()) / SAAT if r.shorts_gecikmeli_mi() else 0.0
    if getattr(config, "YAYIN_RITMI_SHORTS_GECIKMELI", False):
        return float(getattr(config, "YAYIN_RITMI_SHORTS_GECIKME_SAAT", 24))
    return 0.0


def _min_dakika():
    return float(getattr(config, "YOUTUBE_STUDIO_MIN_DAKIKA", MIN_DAKIKA))


# --------------------------------------------------------------------------
# Zaman
# --------------------------------------------------------------------------

def _dt(ts):
    return datetime.datetime.fromtimestamp(ts, TR)


def _iso(ts):
    return _dt(ts).replace(microsecond=0).isoformat()


def _utc_z(ts):
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).replace(microsecond=0) \
        .isoformat().replace("+00:00", "Z")


def _yerel_damga(ts):
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(ts))


def _ts(deger):
    """ISO (Z'li / ofsetli / ofsetsiz=TR) -> epoch; bozuksa None."""
    if not isinstance(deger, str) or not deger.strip():
        return None
    try:
        an = datetime.datetime.fromisoformat(deger.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if an.tzinfo is None:
        an = an.replace(tzinfo=TR)
    return an.timestamp()


def _ts_tzli(deger):
    """auto_process ile aynı hoşgörü: saat dilimsiz publish_at yok sayılır."""
    if not isinstance(deger, str) or not deger:
        return None
    try:
        an = datetime.datetime.fromisoformat(deger.replace("Z", "+00:00"))
    except ValueError:
        return None
    return an.timestamp() if an.tzinfo is not None else None


def _yerel_ts(deger):
    if not isinstance(deger, str):
        return None
    try:
        return time.mktime(time.strptime(deger, "%Y-%m-%dT%H:%M:%S"))
    except (ValueError, OverflowError):
        return None


def _golden_icinde(ts):
    s = _dt(ts).hour
    return any(b <= s < e for b, e in config.GOLDEN_HOURS)


def _grid(bas, bit):
    """[bas, bit] içindeki golden-hour anları (15 dk adım), artan."""
    gun = _dt(bas).date()
    son = _dt(bit).date()
    while gun <= son:
        for b, e in config.GOLDEN_HOURS:
            for dk in range(b * 60, e * 60, ADIM_DAKIKA):
                ts = datetime.datetime(gun.year, gun.month, gun.day, dk // 60, dk % 60,
                                       tzinfo=TR).timestamp()
                if bas <= ts <= bit:
                    yield ts
        gun += datetime.timedelta(days=1)


def _api_ani(simdi):
    """Saatlik hattın API ile yükleyeceği public an: golden-hour içindeyse şimdi, değilse
    bir sonraki pencere başı (`config.next_golden_publish_time`)."""
    sonraki = config.next_golden_publish_time(_dt(simdi))
    return simdi if sonraki is None else sonraki.timestamp()


def sha1(metin):
    return hashlib.sha1(str(metin).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# State / katalog
# --------------------------------------------------------------------------

def studio_kaydi(st):
    v = (st or {}).get(ALAN)
    return v if isinstance(v, dict) else None


def yeni_yayin_ani(st):
    """Tempo tabanının okuduğu yayın anı — `auto_process._son_yeni_yayin_ani` ile AYNI türetme.

    Normal proje: max(youtube_uploaded_at, youtube_publish_at). Studio planlı proje: YALNIZ
    public anı (publish_at, okunamazsa kayıttaki `an`) — yükleme damgası tempo değildir."""
    if not (st or {}).get("youtube_video_id"):
        return None
    kayit = studio_kaydi(st)
    anlar = []
    if kayit is None and ALAN not in (st or {}):
        y = _yerel_ts(st.get("youtube_uploaded_at"))
        if y is not None:
            anlar.append(y)
    p = _ts_tzli(st.get("youtube_publish_at"))
    if p is not None:
        anlar.append(p)
    elif kayit is not None:
        a = _ts(kayit.get("an"))
        if a is not None:
            anlar.append(a)
    return max(anlar) if anlar else None


def _ad(proje):
    return unicodedata.normalize("NFC", os.path.basename(os.path.normpath(proje)))


def _kok_adi(proje):
    return os.path.basename(os.path.dirname(os.path.normpath(os.path.abspath(proje))))


def _durum_oku(proje):
    yol = os.path.join(proje, "state.json")
    if not os.path.isfile(yol):
        return {}
    try:
        with open(yol, "r", encoding="utf-8") as f:
            v = json.load(f)
    except (OSError, ValueError):
        return None
    return v if isinstance(v, dict) else None


def _durum_oku_kesin(proje):
    """Yazmadan önce: okunamıyorsa YAZMA (bozuk state'e {} yazmak kaydı siler)."""
    if not os.path.isdir(proje):
        raise YoutubeStudioHatasi("proje klasörü yok: %s" % proje)
    yol = os.path.join(proje, "state.json")
    if not os.path.isfile(yol):
        return {}
    try:
        with open(yol, "r", encoding="utf-8") as f:
            v = json.load(f)
    except (OSError, ValueError) as e:
        raise YoutubeStudioHatasi("state.json okunamadı (%s) — yazılmadı" % type(e).__name__)
    if not isinstance(v, dict):
        raise YoutubeStudioHatasi("state.json sözlük değil — yazılmadı")
    return v


def _klasorler(klasorler=None):
    return list(uyumluluk.proje_klasorleri() if klasorler is None else klasorler)


def _katalog(klasorler=None):
    iyi, bozuk = [], []
    for p in _klasorler(klasorler):
        st = _durum_oku(p)
        if st is None:
            bozuk.append(_ad(p))
            continue
        iyi.append((p, _ad(p), _kok_adi(p), st))
    return iyi, bozuk


def proje_bul(deger, klasorler=None):
    if not deger or not str(deger).strip():
        raise YoutubeStudioHatasi("proje adı boş")
    hedef = unicodedata.normalize("NFC", str(deger).strip())
    adaylar = _klasorler(klasorler)
    if os.path.isdir(hedef):
        mutlak = os.path.normcase(os.path.abspath(hedef))
        for p in adaylar:
            if os.path.normcase(os.path.abspath(p)) == mutlak:
                return p
    bulunan = [p for p in adaylar if _ad(p) == hedef] or \
              [p for p in adaylar if _ad(p).casefold() == hedef.casefold()]
    if len(bulunan) == 1:
        return bulunan[0]
    if not bulunan:
        raise YoutubeStudioHatasi("proje bulunamadı: %r" % deger)
    raise YoutubeStudioHatasi("belirsiz proje adı: %r (%d eşleşme)" % (deger, len(bulunan)))


def _testte_gercek_yol(yol):
    if not os.environ.get("PYTEST_CURRENT_TEST"):
        return False
    y = os.path.normcase(os.path.abspath(yol))
    for kok in GERCEK_KOKLER:
        k = os.path.normcase(os.path.abspath(kok))
        if y == k or y.startswith(k + os.sep):
            return True
    return False


def _yazim_kapisi(proje):
    if _testte_gercek_yol(proje):
        raise YoutubeStudioHatasi("test sırasında GERÇEK state'e yazma reddedildi: %s" % proje)


def _render_hazir(proje):
    for ad in (VIDEO_UZUN, VIDEO_KISA):
        yol = os.path.join(proje, "output", ad)
        if not os.path.isfile(yol) or os.path.getsize(yol) <= 0:
            return False
    return True


def _uyumluluk_hatalari(proje):
    """uyumluluk.kontrol(yukleme) HATALARI. Kapı çökerse FAIL-CLOSED (hata sayılır)."""
    try:
        hatalar, _ = uyumluluk.kontrol(proje, "yukleme")
    except Exception as e:                                   # noqa: BLE001
        return ["uyumluluk kapısı çöktü (%s) — fail-closed" % type(e).__name__]
    return [str(h) for h in hatalar]


# --------------------------------------------------------------------------
# Kurallar
# --------------------------------------------------------------------------

def _baglam(katalog):
    """Tempo bağlamı: [(ts, ad, kok)] yeni yayın anları ve [(ts, ad)] tüm uzun format public
    anları (aynı gün kapısı; tempo dışı geçişler dahil)."""
    yayinlar, gunluk = [], []
    for p, ad, kok, st in katalog:
        t = yeni_yayin_ani(st)
        if t is not None:
            yayinlar.append((t, ad, kok))
            gunluk.append((t, ad))
        td = _ts_tzli(st.get("youtube_public_ani_tempo_disi"))
        if td is not None:
            gunluk.append((td, ad))
    return {"katalog": katalog, "yayinlar": yayinlar, "gunluk": gunluk}


def _tempo_ihlalleri(an, ad, baglam, ek_anlar=()):
    """Tempo tabanı (52 sa şarkı / 48 sa set-derleme) ihlalleri — auto_process'in uyguladığı
    kural + ozgunluk_plani R1."""
    ihlal = []
    taban, set_ara = _taban_sn(), _set_ara_sn()
    for t, bad, kok in list(baglam["yayinlar"]) + [(t, a, "projects") for t, a in ek_anlar]:
        if bad == ad:
            continue
        ara = taban if kok == "projects" else set_ara
        if abs(an - t) < ara:
            ihlal.append("yeni yayın tabanı %g sa (%s %s)" % (ara / SAAT, bad, _iso(t)))
            break
    return ihlal


def _kural_ihlalleri(an, ad, baglam, simdi, ek_anlar=(), min_dakika=None):
    """Kurala uymayan her şeyin listesi (boş = uygun). TEK kural yeri."""
    ihlal = []
    lead = (_min_dakika() if min_dakika is None else min_dakika) * 60
    if an <= simdi + lead:
        ihlal.append("an geçmiş ya da çok yakın (en az %d dk ileride olmalı)" % (lead // 60))
    if not _golden_icinde(an):
        ihlal.append("golden-hour dışında (%s, TR)" % ", ".join(
            "%02d-%02d" % g for g in config.GOLDEN_HOURS))
    ihlal.extend(_tempo_ihlalleri(an, ad, baglam, ek_anlar))
    gun = _dt(an).date()
    for t, bad in list(baglam["gunluk"]) + list(ek_anlar):
        if bad != ad and _dt(t).date() == gun:
            ihlal.append("aynı gün başka YouTube yayını (%s %s)" % (bad, _iso(t)))
            break
    return ihlal


def _shorts_ihlalleri(shorts_an, uzun_an, simdi):
    ihlal = []
    gerekli = _shorts_saat() * SAAT
    if shorts_an < uzun_an + gerekli:
        ihlal.append("Shorts uzun formattan en az %g sa sonra olmalı (en erken %s)"
                     % (gerekli / SAAT, _iso(uzun_an + gerekli)))
    if shorts_an <= simdi:
        ihlal.append("Shorts anı geçmiş")
    if gerekli and not _golden_icinde(shorts_an):
        ihlal.append("Shorts anı golden-hour dışında")
    return ihlal


def ilk_uygun_an(ad, baglam, simdi, gun=10, ek_anlar=()):
    for ts in _grid(simdi, simdi + float(gun) * GUN_SN):
        if not _kural_ihlalleri(ts, ad, baglam, simdi, ek_anlar):
            return ts
    return None


def aday_degerlendir(proje, st, baglam, simdi):
    """("aday"|"degil", sebep). Pahalı uyumluluk kontrolü EN SONDA."""
    ad = _ad(proje)
    if st is None:
        return "degil", "state.json okunamadı"
    if _kok_adi(proje) != "projects":
        return "degil", "ana katalog dışı (DJ/derleme kendi hattında)"
    if ALAN in st:
        return "degil", "Studio planı zaten kayıtlı"
    if st.get("youtube_video_id"):
        return "degil", "YouTube'a zaten yüklü (%s)" % st["youtube_video_id"]
    if st.get(uyumluluk.BEKLETME_ALANI):
        return "degil", "yayin_beklet dolu — bekletme kaldırılmadan planlanmaz"
    if not _render_hazir(proje):
        return "degil", "render hazır değil (output/%s + %s)" % (VIDEO_UZUN, VIDEO_KISA)
    tempo = _tempo_ihlalleri(_api_ani(simdi), ad, baglam)
    if not tempo:
        return "degil", "tempo engeli yok — saatlik hat API ile yükler"
    hatalar = _uyumluluk_hatalari(proje)
    if hatalar:
        return "degil", "uyumluluk hatası: %s" % "; ".join(hatalar)[:200]
    return "aday", "tempo nedeniyle bekliyor: %s" % tempo[0]


# --------------------------------------------------------------------------
# Paket
# --------------------------------------------------------------------------

def metin_denetimi(metin):
    """Kamuya açık metin kuralları (config.AI_BEYAN_SATIRLARI notu): üretim aracının adı yok,
    "yapay zeka" değil "AI destekli", AI satırı varsa config'teki metnin ta kendisi."""
    sorun = []
    k = str(metin).casefold()
    if "suno" in k:
        sorun.append("üretim aracının adı (Suno) geçiyor")
    if "yapay zeka" in k:
        sorun.append("'yapay zeka' ifadesi (kural: 'AI destekli')")
    izinli = {s for dil in config.AI_BEYAN_SATIRLARI.values() for s in dil.values()}
    for satir in str(metin).splitlines():
        if ("AI destekli" in satir or "AI-assisted" in satir) and satir.strip() not in izinli:
            sorun.append("AI satırı config dışı: %r" % satir.strip()[:80])
    return sorun


def kapak_jpeg(kaynak, hedef, calistir=None):
    """Kapağı Studio "Küçük resim" için <= 2 MB JPEG'e çevirir (ffmpeg; kalite kademeli)."""
    calistir = calistir or subprocess.run
    os.makedirs(os.path.dirname(hedef), exist_ok=True)
    for q in (2, 4, 7, 11, 16):
        r = calistir(["ffmpeg", "-y", "-loglevel", "error", "-i", kaynak, "-q:v", str(q), hedef],
                     capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            raise YoutubeStudioHatasi("kapak JPEG'e çevrilemedi: %s" % str(r.stderr)[-300:])
        bayt = os.path.getsize(hedef)
        if bayt <= KAPAK_MAX_BAYT:
            return {"yol": hedef, "bayt": bayt, "kalite": q}
    raise YoutubeStudioHatasi("kapak 2 MB altına indirilemedi: %s" % kaynak)


def _playlistler(proje, meta, an_ts):
    """youtube_playlists.beklenen_anahtarlar ile (yayında sayılan sanal state) -> uzun/kısa."""
    import youtube_playlists as YP
    z = _utc_z(an_ts if an_ts is not None else time.time())
    sanal = {"youtube_video_id": "__UZUN__", "youtube_privacy": "public", "youtube_publish_at": z,
             "youtube_shorts_video_id": "__KISA__", "youtube_shorts_privacy": "public",
             "youtube_shorts_publish_at": z}
    plan = YP.beklenen_anahtarlar(proje, state=sanal, meta=meta)
    ids = YP._load_playlist_ids()

    def _ad_bul(anahtar):
        if anahtar in YP.KOLEKSIYONLAR:
            return YP.KOLEKSIYONLAR[anahtar]["title"]
        tema = config.THEMES.get(anahtar, config.THEMES[config.DEFAULT_THEME])
        # get_or_create_playlist'in başlık kalıbı; kimlik (id) de veriliyor — Studio'da
        # ada ek olarak kimlikle doğrulanabilsin.
        return "%s Şarkılar — %s" % (tema["label"], config.STATIC_LABEL_TEXT)

    def _liste(vid):
        return [{"anahtar": a, "ad": _ad_bul(a), "id": ids.get(a)} for a in plan.get(vid, [])]
    return _liste("__UZUN__"), _liste("__KISA__")


def _studio_alanlari(dil, an, shorts_an):
    return [
        {"alan": "Başlık (zorunlu)", "deger": "paketteki `baslik`"},
        {"alan": "Açıklama", "deger": "paketteki `aciklama` metnini olduğu gibi yapıştır"},
        {"alan": "Küçük resim", "deger": "Dosya yükle -> paketteki `kapak` (<= 2 MB JPEG)"},
        {"alan": "Oynatma listeleri", "deger": "paketteki `playlistler` (ad + id)"},
        {"alan": "Kitle", "deger": "Hayır, çocuklara özel değil"},
        {"alan": "Değiştirilmiş içerik", "deger": "Evet"},
        {"alan": "Etiketler", "deger": "paketteki `etiketler` (virgülle)"},
        {"alan": "Video dili", "deger": _DIL_ADLARI.get(dil, dil)},
        {"alan": "Kategori", "deger": "Müzik"},
        {"alan": "Video öğeleri", "deger": "atla"},
        {"alan": "Kontroller", "deger": "tamamlanmasını bekle (telif/uygunluk)"},
        {"alan": "Görünürlük", "deger": "Planla -> %s (GMT+03:00 İstanbul); Shorts: %s" % (
            _iso(an) if an is not None else "önerilen an yok",
            _iso(shorts_an) if shorts_an is not None else "-")},
    ]


def paket(proje, an=None, simdi=None, uzun_id=None, klasorler=None, baglam=None,
          kapak_hazirla=True, kapak_dizini=None, calistir=None):
    """Tek projenin Studio paketi — state YAZMAZ, GÖNDERMEZ. Metinler `build_snippet` /
    `build_shorts_snippet` ÇAĞRILARAK üretilir (kopya yok)."""
    import youtube_upload as YU

    t = time.time() if simdi is None else simdi
    if baglam is None:
        katalog, _ = _katalog(klasorler)
        baglam = _baglam(katalog)
    st = _durum_oku(proje)
    sinif, sebep = aday_degerlendir(proje, st, baglam, t)
    ad = _ad(proje)
    if an is None and sinif == "aday":
        an = ilk_uygun_an(ad, baglam, t)
    shorts_an = an + _shorts_saat() * SAAT if an is not None else None
    meta = YU.load_meta(proje)
    uzun = YU.build_snippet(meta)
    kisa = YU.build_shorts_snippet(meta, uzun_id)
    uyarilar = []
    if not uzun_id:
        uyarilar.append("Shorts açıklamasındaki tam sürüm linki uzun videonun kimliğini "
                        "istiyor: uzun video Studio'ya yüklenince paketi --uzun-id ile yeniden al.")
    for bolum, sn in (("uzun", uzun), ("Shorts", kisa)):
        for s in metin_denetimi("\n".join([sn["title"], sn["description"]] + list(sn["tags"]))):
            uyarilar.append("%s: %s" % (bolum, s))
    uzun_pl, kisa_pl = _playlistler(proje, meta, an)
    kapaklar = {"uzun": YU._find_cover(proje), "kisa": YU._find_cover_vertical(proje)}
    if kapak_hazirla:
        dizin = kapak_dizini or os.path.join(tempfile.gettempdir(), "ilkprojem_ytstudio", "kapak",
                                             sha1(ad)[:10])
        for k, kaynak in list(kapaklar.items()):
            if kaynak:
                try:
                    kapaklar[k] = kapak_jpeg(kaynak, os.path.join(dizin, "%s.jpg" % k),
                                             calistir)["yol"]
                except (OSError, YoutubeStudioHatasi) as e:
                    uyarilar.append("kapak (%s) hazırlanamadı: %s" % (k, str(e)[:150]))
    dil = uzun.get("defaultLanguage")
    ozet = sha1(uzun["description"])
    kisa_ozet = sha1(kisa["description"]) if uzun_id else None

    def _bolum(sn, video, kapak, pl):
        yol = os.path.abspath(os.path.join(proje, "output", video))
        return {"video": yol, "video_var": os.path.isfile(yol), "baslik": sn["title"],
                "aciklama": sn["description"], "etiketler": list(sn["tags"]),
                "kategori_id": sn["categoryId"], "kategori": "Müzik", "dil": dil,
                "kapak": os.path.abspath(kapak) if kapak else None, "playlistler": pl}
    return {
        "surum": SURUM, "proje": ad, "proje_yolu": os.path.abspath(proje),
        "aday": sinif == "aday", "sinif": sinif, "sebep": sebep,
        "onerilen_an": _iso(an) if an is not None else None,
        "onerilen_an_utc": _utc_z(an) if an is not None else None,
        "shorts_onerilen_an": _iso(shorts_an) if shorts_an is not None else None,
        "degistirilmis_icerik": "Evet", "kitle": "Çocuklara özel değil",
        "uzun": _bolum(uzun, VIDEO_UZUN, kapaklar["uzun"], uzun_pl),
        "kisa": _bolum(kisa, VIDEO_KISA, kapaklar["kisa"], kisa_pl),
        "aciklama_sha1": ozet, "shorts_aciklama_sha1": kisa_ozet,
        "studio_alanlari": _studio_alanlari(dil, an, shorts_an),
        "uyarilar": uyarilar,
        "isaretle_komutu": ('python upload/youtube_studio.py isaretle --proje "%s" --video-id <ID> '
                            '--shorts-id <ID> --an %s --sha1 %s' % (
                                ad, _iso(an) if an is not None else "<ISO>", ozet)),
    }


def plan_oner(gun=10, simdi=None, klasorler=None):
    """Deterministik öneri listesi — HİÇBİR ŞEY YAZMAZ. Adaylar zincirlenir (her önerinin anı
    sonrakine yayın anı sayılır)."""
    t = time.time() if simdi is None else simdi
    katalog, bozuk = _katalog(klasorler)
    baglam = _baglam(katalog)
    oneriler, sigmayan, degil, ek = [], [], [], []
    for p, ad, kok, st in katalog:
        sinif, sebep = aday_degerlendir(p, st, baglam, t)
        if sinif != "aday":
            if kok == "projects" and not st.get("youtube_video_id") and ALAN not in st:
                degil.append({"proje": ad, "sebep": sebep})
            continue
        an = ilk_uygun_an(ad, baglam, t, gun, ek_anlar=ek)
        if an is None:
            sigmayan.append({"proje": ad, "sebep": "önümüzdeki %g günde kurala uyan an yok" % gun})
            continue
        ek.append((an, ad))
        shorts_an = an + _shorts_saat() * SAAT
        oneriler.append({"proje": ad, "proje_yolu": os.path.abspath(p), "sebep": sebep,
                         "onerilen_an": _iso(an), "onerilen_an_utc": _utc_z(an),
                         "shorts_onerilen_an": _iso(shorts_an)})
    return {"surum": SURUM, "uretildi_at": _iso(t), "gun": gun, "oneriler": oneriler,
            "sigmayan": sigmayan, "aday_degil": degil, "okunamayan": bozuk,
            "kurallar": _kurallar()}


def _kurallar():
    return {"golden_hours": [list(g) for g in config.GOLDEN_HOURS], "adim_dakika": ADIM_DAKIKA,
            "taban_saat": _taban_sn() / SAAT, "set_sarki_saat": _set_ara_sn() / SAAT,
            "shorts_saat": _shorts_saat(), "min_dakika": _min_dakika(),
            "ayni_gun_tek_youtube_yayini": True}


# --------------------------------------------------------------------------
# İşaretleme
# --------------------------------------------------------------------------

def _video_id(deger, ad="video kimliği"):
    if not isinstance(deger, str) or not _VIDEO_ID_RE.match(deger):
        raise YoutubeStudioHatasi("geçersiz %s: %r (11 karakter, Studio URL'sindeki)" % (ad, deger))
    return deger


def isaretle(proje, video_id, an, sha1_beklenen, shorts_id=None, shorts_an=None,
             shorts_sha1=None, yuklendi=None, playlistler_eklendi=False, kaynak="claude",
             simdi=None, klasorler=None, defter_yol=None):
    """Studio'da planlama bittikten sonra: doğrular, state'e yazar, deftere ekler.
    Red -> YoutubeStudioHatasi (HİÇBİR ŞEY yazılmaz)."""
    import elle_islem
    import youtube_upload as YU

    t = time.time() if simdi is None else simdi
    _yazim_kapisi(proje)
    _video_id(video_id)
    if shorts_id is not None:
        _video_id(shorts_id, "Shorts video kimliği")
    if kaynak not in elle_islem.KAYNAKLAR:
        raise YoutubeStudioHatasi("geçersiz kaynak: %r" % kaynak)
    an_ts = _ts(an) if isinstance(an, str) else (float(an) if an is not None else None)
    if an_ts is None:
        raise YoutubeStudioHatasi("an okunamadı: %r (ISO, ör. 2026-09-15T18:00:00+03:00)" % (an,))
    y_ts = t if yuklendi is None else (_ts(yuklendi) if isinstance(yuklendi, str) else float(yuklendi))
    if y_ts is None or y_ts > t + 300:
        raise YoutubeStudioHatasi("yükleme anı okunamadı ya da gelecekte: %r" % (yuklendi,))
    st = _durum_oku_kesin(proje)
    ad = _ad(proje)
    mevcut = studio_kaydi(st)
    if st.get("youtube_video_id"):
        if (st["youtube_video_id"] == video_id and mevcut
                and _ts(mevcut.get("an")) == an_ts):
            return {"durum": "zaten", "proje": ad, "kayit": mevcut, "defter": ""}
        raise YoutubeStudioHatasi("REDDEDİLDİ: '%s' zaten YouTube'a yüklü (%s)"
                                  % (ad, st["youtube_video_id"]))
    if st.get(uyumluluk.BEKLETME_ALANI):
        raise YoutubeStudioHatasi("REDDEDİLDİ: '%s' yayin_beklet dolu" % ad)
    hatalar = _uyumluluk_hatalari(proje)
    if hatalar:
        raise YoutubeStudioHatasi("REDDEDİLDİ: uyumluluk hatası — %s" % "; ".join(hatalar)[:300])
    meta = YU.load_meta(proje)
    ozet = sha1(YU.build_snippet(meta)["description"])
    if sha1_beklenen != ozet:
        raise YoutubeStudioHatasi("REDDEDİLDİ: açıklama sha1 uyuşmuyor (%s != güncel %s) — "
                                  "paketi yeniden al" % (sha1_beklenen, ozet))
    katalog, _ = _katalog(klasorler)
    baglam = _baglam(katalog)
    ihlal = _kural_ihlalleri(an_ts, ad, baglam, t, min_dakika=5)
    if ihlal:
        raise YoutubeStudioHatasi("REDDEDİLDİ: %s kurala uymuyor — %s" % (_iso(an_ts), "; ".join(ihlal)))
    s_ts = None
    kisa_ozet = None
    if shorts_id is not None:
        s_ts = an_ts + _shorts_saat() * SAAT if shorts_an is None else _ts(shorts_an)
        if s_ts is None:
            raise YoutubeStudioHatasi("Shorts anı okunamadı: %r" % (shorts_an,))
        s_ihlal = _shorts_ihlalleri(s_ts, an_ts, t)
        if s_ihlal:
            raise YoutubeStudioHatasi("REDDEDİLDİ: Shorts %s — %s" % (_iso(s_ts), "; ".join(s_ihlal)))
        kisa_ozet = sha1(YU.build_shorts_snippet(meta, video_id)["description"])
        if shorts_sha1 and shorts_sha1 != kisa_ozet:
            raise YoutubeStudioHatasi("REDDEDİLDİ: Shorts açıklama sha1 uyuşmuyor (%s != %s)"
                                      % (shorts_sha1, kisa_ozet))
    kayit = {"an": _iso(an_ts), "kaynak": KAYNAK, "sha1": ozet,
             "gorunurluk_studio": GORUNURLUK_STUDIO, "yuklendi_at": _iso(y_ts),
             "shorts_an": _iso(s_ts) if s_ts is not None else None, "shorts_sha1": kisa_ozet,
             "kaynak_kisi": kaynak, "isaretlendi_at": _iso(t), "surum": SURUM}
    st.update({"youtube_video_id": video_id, "youtube_publish_at": _utc_z(an_ts),
               "youtube_uploaded_at": _yerel_damga(y_ts), "youtube_privacy": "public", ALAN: kayit})
    if shorts_id is not None:
        st.update({"youtube_shorts_video_id": shorts_id, "youtube_shorts_publish_at": _utc_z(s_ts),
                   "youtube_shorts_uploaded_at": _yerel_damga(y_ts),
                   "youtube_shorts_privacy": "public"})
    if playlistler_eklendi:
        uzun_pl, kisa_pl = _playlistler(proje, meta, an_ts)
        uzun_ids = [x["id"] for x in uzun_pl if x["id"]]
        kisa_ids = [x["id"] for x in kisa_pl if x["id"]] if shorts_id else []
        if uzun_ids or kisa_ids:
            st["youtube_playlists"] = uzun_ids + kisa_ids
            if uzun_ids:
                st["youtube_playlist_id"] = uzun_ids[0]
            if kisa_ids:
                st["youtube_shorts_playlist_id"] = kisa_ids[0]
            st["youtube_playlists_kaynak"] = "%s, %s" % (KAYNAK, _iso(t))
    state_io.durum_yaz(proje, st)
    defter = []
    satirlar = [("youtube", video_id, "uzun format '%s' yüklendi, Gizli + Planla %s"
                 % (ad, _iso(an_ts)))]
    if shorts_id is not None:
        satirlar.append(("youtube_shorts", shorts_id, "Shorts '%s' yüklendi, Gizli + Planla %s"
                         % (ad, _iso(s_ts))))
    for platform, kanit, ayrinti in satirlar:
        try:
            sonuc = elle_islem.ekle(platform, "planladi", "YouTube Studio (Chrome): " + ayrinti,
                                    proje=ad, zaman=_iso(y_ts), kaynak=kaynak, kanit=kanit,
                                    yol=defter_yol, state_yansit=False, state_etkisi=ALAN,
                                    proje_klasorleri=klasorler, simdi=t)
            defter.append(sonuc.get("mesaj", ""))
        except Exception as e:                               # noqa: BLE001
            defter.append("UYARI: deftere yazılamadı (%s: %s)" % (type(e).__name__, str(e)[:150]))
    return {"durum": "planlandi", "proje": ad, "kayit": kayit, "defter": " | ".join(defter)}


# --------------------------------------------------------------------------
# Görünürlük + bildirim (kalıp B)
# --------------------------------------------------------------------------

def durum(simdi=None, klasorler=None):
    t = time.time() if simdi is None else simdi
    katalog, bozuk = _katalog(klasorler)
    planli = []
    for p, ad, kok, st in katalog:
        k = studio_kaydi(st)
        if ALAN not in st:
            continue
        an = _ts((k or {}).get("an"))
        planli.append({"proje": ad, "video_id": st.get("youtube_video_id"),
                       "shorts_id": st.get("youtube_shorts_video_id"),
                       "an": (k or {}).get("an"), "shorts_an": (k or {}).get("shorts_an"),
                       "an_gecti": an is not None and an <= t, "bozuk": k is None})
    planli.sort(key=lambda x: (str(x["an"]), x["proje"]))
    return {"surum": SURUM, "uretildi_at": _iso(t), "planli": planli, "okunamayan": bozuk}


def _gun_damgasi_oku():
    try:
        with open(DURUM_DOSYASI, "r", encoding="utf-8") as f:
            v = json.load(f)
        return v if isinstance(v, dict) else {}
    except (OSError, ValueError):
        return {}


def _gun_damgasi_yaz(gun):
    d = _gun_damgasi_oku()
    d[BILDIRIM_GUN_DAMGASI] = gun
    try:
        state_io._atomik_yaz(DURUM_DOSYASI, d)
    except OSError:
        pass


def bildirim_metni(proje, an_ts):
    return ("YouTube: %s tempo nedeniyle bekliyor; Studio'dan %s'a planlanabilir. "
            "Claude Code'da 'YouTube Studio'dan planla' yaz." % (proje, _dt(an_ts).strftime("%d.%m %H:%M")))


def plan_bildirimi(log=print, simdi=None, klasorler=None, gonder=None):
    """Tempo yüzünden bekleyen Studio adayı varsa GÜNDE EN FAZLA 1 Telegram satırı.
    Hiçbir hata yukarı çıkmaz; her koşuda tek "  YouTube Studio planı:" satırı."""
    sonuc = {"gonderilen": None, "sebep": ""}
    t = time.time() if simdi is None else simdi
    if klasorler is None and gonder is None and os.environ.get("PYTEST_CURRENT_TEST"):
        sonuc["sebep"] = "test ortamı — gerçek katalog okunmaz, bildirim yok"
        return sonuc
    try:
        oneri = plan_oner(simdi=t, klasorler=klasorler)
    except Exception as e:                                   # noqa: BLE001
        sonuc["sebep"] = "plan hesaplanamadı (%s)" % type(e).__name__
        log("  YouTube Studio planı: %s" % sonuc["sebep"])
        return sonuc
    if not oneri["oneriler"]:
        sonuc["sebep"] = "aday yok"
        log("  YouTube Studio planı: aday yok")
        return sonuc
    ilk = oneri["oneriler"][0]
    ozet = "%d aday; ilk: %s -> %s" % (len(oneri["oneriler"]), ilk["proje"], ilk["onerilen_an"])
    bugun = _dt(t).date().isoformat()
    if not getattr(config, "YOUTUBE_STUDIO_PLAN_BILDIRIM", True):
        sonuc["sebep"] = "bildirim kapalı (config)"
    elif _gun_damgasi_oku().get(BILDIRIM_GUN_DAMGASI) == bugun:
        sonuc["sebep"] = "bugün zaten bildirildi"
    else:
        if gonder is None:
            import notify
            gonder = notify.send
        try:
            ok = gonder("YouTube Studio planı", bildirim_metni(ilk["proje"], _ts(ilk["onerilen_an"]))) is True
        except Exception:                                    # noqa: BLE001
            ok = False
        if ok:
            _gun_damgasi_yaz(bugun)
            sonuc["gonderilen"] = ilk["proje"]
            sonuc["sebep"] = "bildirim gönderildi"
        else:
            sonuc["sebep"] = "bildirim gönderilemedi"
    log("  YouTube Studio planı: %s; bildirim: %s" % (ozet, sonuc["sebep"]))
    return sonuc


def public_oncesi_mi(st, simdi=None):
    """Studio planlı ve public anı henüz gelmemiş mi (diğer platform kapısı)."""
    if ALAN not in (st or {}):
        return False
    t = time.time() if simdi is None else simdi
    an = yeni_yayin_ani(st)
    return an is None or an > t


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _cikti_utf8():
    for akis in (sys.stdout, sys.stderr):
        try:
            if (getattr(akis, "encoding", "") or "").lower().replace("-", "") != "utf8":
                akis.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


def _json_bas(veri):
    print(json.dumps(veri, ensure_ascii=False, indent=2))


def main(argv=None):
    _cikti_utf8()
    ap = argparse.ArgumentParser(description="YouTube Studio planlı yükleme yardımcıları "
                                             "(tarayıcı AÇMAZ, API çağırmaz).")
    alt = ap.add_subparsers(dest="komut", required=True)
    a = alt.add_parser("plan-oner", help="Öneri listesi (KURU, yazmaz)")
    a.add_argument("--gun", type=float, default=10)
    a.add_argument("--json", action="store_true")
    a = alt.add_parser("paket", help="Tek projenin Studio paketi (state yazmaz)")
    a.add_argument("--proje", required=True)
    a.add_argument("--an", default=None)
    a.add_argument("--uzun-id", default=None)
    a.add_argument("--kapaksiz", action="store_true", help="JPEG kapak hazırlama")
    a.add_argument("--json", action="store_true")
    a = alt.add_parser("isaretle", help="Studio'da planlandı: doğrula + state + defter")
    a.add_argument("--proje", required=True)
    a.add_argument("--video-id", required=True)
    a.add_argument("--shorts-id", default=None)
    a.add_argument("--an", required=True)
    a.add_argument("--sha1", required=True)
    a.add_argument("--shorts-an", default=None)
    a.add_argument("--shorts-sha1", default=None)
    a.add_argument("--yuklendi", default=None)
    a.add_argument("--playlistler-eklendi", action="store_true")
    a.add_argument("--kaynak", default="claude")
    a = alt.add_parser("durum", help="Studio planlı projeler")
    a.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    try:
        if args.komut == "plan-oner":
            s = plan_oner(gun=args.gun)
            if args.json:
                _json_bas(s)
            else:
                print("YouTube Studio planı önerisi (%s, %g gün) — KURU" % (s["uretildi_at"], s["gun"]))
                for o in s["oneriler"]:
                    print("  %s (Shorts %s)  %s — %s" % (o["onerilen_an"], o["shorts_onerilen_an"],
                                                        o["proje"], o["sebep"]))
                for x in s["sigmayan"] + s["aday_degil"]:
                    print("  aday değil: %s — %s" % (x["proje"], x["sebep"]))
            return 0
        if args.komut == "paket":
            an = None
            if args.an:
                an = _ts(args.an)
                if an is None:
                    raise YoutubeStudioHatasi("an okunamadı: %r" % args.an)
            s = paket(proje_bul(args.proje), an=an, uzun_id=args.uzun_id,
                      kapak_hazirla=not args.kapaksiz)
            if args.json:
                _json_bas(s)
            else:
                print("%s — aday: %s (%s); public an: %s; Shorts: %s" % (
                    s["proje"], s["aday"], s["sebep"], s["onerilen_an"], s["shorts_onerilen_an"]))
                for bolum in ("uzun", "kisa"):
                    b = s[bolum]
                    print("--- %s ---\nvideo: %s\nkapak: %s\nbaşlık: %s\nplaylist: %s\n%s" % (
                        bolum, b["video"], b["kapak"], b["baslik"],
                        ", ".join("%s (%s)" % (x["ad"], x["id"]) for x in b["playlistler"]),
                        b["aciklama"]))
                print("sha1: %s  shorts sha1: %s" % (s["aciklama_sha1"], s["shorts_aciklama_sha1"]))
                for x in s["studio_alanlari"]:
                    print("  %s -> %s" % (x["alan"], x["deger"]))
                for u in s["uyarilar"]:
                    print("  UYARI: %s" % u)
            return 0
        if args.komut == "isaretle":
            s = isaretle(proje_bul(args.proje), args.video_id, args.an, args.sha1,
                         shorts_id=args.shorts_id, shorts_an=args.shorts_an,
                         shorts_sha1=args.shorts_sha1, yuklendi=args.yuklendi,
                         playlistler_eklendi=args.playlistler_eklendi, kaynak=args.kaynak)
            print("TAMAM: '%s' %s — public %s. %s" % (s["proje"], s["durum"], s["kayit"]["an"],
                                                      s["defter"]))
            return 0
        if args.komut == "durum":
            s = durum()
            if args.json:
                _json_bas(s)
            else:
                for x in s["planli"] or [{"proje": "Studio planlı proje yok", "an": ""}]:
                    print("%s %s" % (x["proje"], x["an"]))
            return 0
    except YoutubeStudioHatasi as e:
        print(str(e))
        return 2
    return 2


if __name__ == "__main__":
    sys.exit(main())
