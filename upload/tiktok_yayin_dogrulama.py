# -*- coding: utf-8 -*-
"""TikTok taslağı yayınlandı mı? — TikTok API'sinden SALT OKUNUR doğrulama.

NEDEN VAR (2026-09-13): boru hattı TikTok'a yalnız TASLAK yüklüyor (inbox akışı,
`video.upload` izni); yayını kullanıcı uygulamadan ELLE yapıyor ve depo bunu
bilmiyordu. Birinci katman Telegram onayı (`tiktok_yayin_onayi.py`, kullanıcı
"yayınladım <ad>" yazar). Bu modül İKİNCİ katman: kullanıcı yazmayı unutsa bile
`POST /v2/post/publish/status/fetch/` ile her taslağın durumu okunur.

RESMÎ DOKÜMAN (developers.tiktok.com, "Get Post Status", 2026-09-13 okundu):
  * Scope: "video.upload/video.publish" — bizim token'da `video.upload` var.
  * Durumlar: PROCESSING_UPLOAD, PROCESSING_DOWNLOAD, SEND_TO_USER_INBOX,
    PUBLISH_COMPLETE ("user completed draft via editing flow" dahil), FAILED.
  * `publicaly_available_post_id` (yazım API'deki gibi): YALNIZ herkese açık ve
    moderasyondan geçmiş gönderide dolu.
  * Hız sınırı: "Each user access_token is limited to 30 requests per minute".
  * publish_id'nin ne kadar süre sorgulanabildiği BELGELENMEMİŞ. API yayın
    ZAMANINI döndürmüyor.

KARARLAR:
  * EŞLEŞTİRME publish_id ile — başlıkla DEĞİL (TikTok başlıkları içerikle
    uyuşmuyor, 2026-09-12 ölçüldü).
  * İŞARET `PUBLISH_COMPLETE` TEK BAŞINA (KARAR DEĞİŞTİ, 2026-09-13). Eski
    kural "PUBLISH_COMPLETE + dolu post id" idi; gerekçesi "Sadece ben"/moderasyon
    gönderisinin post id vermemesiydi. ÖLÇÜM bunu boşa çıkardı: kullanıcının
    yayınladığı `Gece Sürüşü` PUBLISH_COMPLETE döndü ve post id alanı yanıtta
    HİÇ yoktu — eski kural bu hesapta hiç tetiklenmezdi. İşaretin amacı İKİNCİ
    PAYLAŞIMI ÖNLEMEK; "Sadece ben" yapılmış bir yayın da taslağı tüketir.
    Görünürlük bilinmediği için kaynak metni bunu açıkça söyler ("görünürlük
    bilinmiyor"). Post id gelirse `tiktok_post_ids` yine yazılır. Bu işaret
    TikTok yayın kitini de besler: yayında bulunan taslağa kit gitmez.
  * `tiktok_published_at` = TESPİT ANI (API zaman vermiyor); kaynak alanı bunu
    açıkça "yaklaşık, tespit anı" diye söylüyor.
  * `build_plan()` `hazir=False` ise (yayin_beklet, uyumluluk HATA, ikiz kapısı)
    İŞARET YOK — Telegram onayıyla aynı kural. Sorgu yine yapılır (salt okunur),
    durum ve engel metni yazılır: "yayında ama plan engelli" görünür kalsın.
  * Yazan tek fonksiyon `tiktok_publish_plan.isaretle_yayinlandi(kaynak=...)`.
    Durum alanları ondan ÖNCE ayrı bir atomik yazımla gidiyor; aradaki süreç
    ölümünde en kötü sonuç "durum var, işaret yok" — sonraki gün aday yeniden
    sorgulanıp işaretlenir (idempotent).
  * Hata: projeye özgü hata → 24 saat soğuma + sayaç; `invalid_publish_id` gibi
    kalıcı kodlarda 3, diğerlerinde 7 ardışık hatada `tiktok_status_denenmez`
    (sessizce sonsuza kadar sorgu YOK). `FAILED` durumu hemen denenmez.
    Genel hata (token geçersiz, izin yok, hız sınırı, süren taşıma hatası) →
    koşu DURUR, projelere hata yazılmaz, günlük damga ATILMAZ.

ÜÇ SORU (CLAUDE.md):
  1. Kim çağırıyor? `auto_process.main()` `finally` → `_tiktok_yayin_dogrulama()`
     → `gunluk_dogrulama()`. `_is_fully_done()`'a EKLENMEDİ.
  2. Hangi görev? Saatlik `auto_process.py`; YENİ zamanlayıcı görevi yok. Günde
     bir: `upload/saglik_durum.json` → `tiktok_yayin_dogrulama_gun`, yalnız
     koşu tamamlanınca atılır.
  3. Çalışmadığını nasıl anlarız? Her gerçek koşuda özet log satırı ("aday yok"
     dahil); token yok/geçersizse `notify.uyar_bir_kez` satırı.

AĞ: TikTok'a YAZAN hiçbir çağrı yok — tek uç `status/fetch` (okuma). Token
yenileme mevcut `tiktok_auth.get_access_token()` ile, koşu başına bir kez ve
yalnız aday varken. Token değeri hiçbir log/bildirim/state metnine girmez.
"""

import argparse
import json
import os
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import notify
import state_io
import tiktok_publish_plan as TPP
import uyumluluk
from tiktok_web import web_aktif
from gizli_maskele import maskele

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"

# Damga dosyası saglik_kontrol/weekly_report ile ORTAK (conftest bu adı
# testlerde geçici klasöre yönlendiriyor — `KORUNAN_YOL_ADLARI`).
DURUM_DOSYASI = os.path.join(REPO, "upload", "saglik_durum.json")
GUN_DAMGASI = "tiktok_yayin_dogrulama_gun"

KOSU_TAVANI = 10
# 30 istek/dakika (resmî) = 2 sn/istek; payla 2.5 sn. Tavan 10 → ~25 sn.
ISTEK_ARALIGI_SN = 2.5
SOGUMA_SN = 24 * 60 * 60
TASIMA_DENEME = 3

KALICI_HATA_KODLARI = ("invalid_publish_id",
                       "token_not_authorized_for_specified_publish_id")
KALICI_HATA_TAVANI = 3
GECICI_HATA_TAVANI = 7
# Tek bir projeye değil TÜM koşuya ait hatalar: sonraki adayı denemek anlamsız.
GENEL_HATA_KODLARI = ("access_token_invalid", "scope_not_authorized",
                      "rate_limit_exceeded")

KAYNAK_ETIKETI = "TikTok API PUBLISH_COMPLETE (otomatik)"
_ZAMAN = "%Y-%m-%dT%H:%M:%S"
_HATA_ALANLARI = ("tiktok_status_hata", "tiktok_status_hata_sayisi",
                  "tiktok_status_sonraki_deneme")


class _GenelHata(Exception):
    """Koşunun tamamını durduran hata (token/izin/hız sınırı/taşıma)."""


# --------------------------------------------------------------------------
# Damga defteri (saglik_kontrol._durum/_kaydet ile aynı desen)
# --------------------------------------------------------------------------

def _durum() -> dict:
    try:
        with open(DURUM_DOSYASI, "r", encoding="utf-8") as f:
            veri = json.load(f)
        return veri if isinstance(veri, dict) else {}
    except (OSError, ValueError):
        return {}


def _kaydet(g: dict) -> None:
    d = _durum()
    d.update(g)
    try:
        state_io._atomik_yaz(DURUM_DOSYASI, d)
    except OSError:
        pass


# --------------------------------------------------------------------------
# Yardımcılar
# --------------------------------------------------------------------------

def _damga(ts: float) -> str:
    return time.strftime(_ZAMAN, time.localtime(ts))


def _ts(metin):
    try:
        return time.mktime(time.strptime(str(metin), _ZAMAN))
    except (TypeError, ValueError, OverflowError):
        return None


def _temiz(metin, token=None, sinir=200) -> str:
    """Log/state'e girecek dış metin: maskele + token'ı açıkça çıkar + kırp."""
    s = maskele(metin)
    if token:
        s = s.replace(token, "***")
    return " ".join(s.split())[:sinir]


def _ad(proje: str) -> str:
    try:
        baslik = TPP._load_meta(proje).get("title")
    except Exception:                                        # noqa: BLE001
        baslik = None
    return baslik or os.path.basename(os.path.abspath(proje))


def _token_al() -> dict:
    from tiktok_auth import get_access_token
    return get_access_token()


def adaylari_bul(simdi_ts: float) -> list:
    """[(proje, ad, publish_id)] — en uzun süredir sorgulanmayan önce.

    Aday: `tiktok_publish_id` VAR, `tiktok_published_at` YOK, denenmez değil,
    soğumada değil. Kökler `uyumluluk.proje_klasorleri()` (tek kanonik liste).
    Sıralama sayesinde tavan (10) 17+ bekleyen taslakta da hepsini döndürür.
    """
    liste = []
    for proje in uyumluluk.proje_klasorleri():
        d = TPP._durum_oku(proje)
        pid = d.get("tiktok_publish_id")
        if (not pid or d.get("tiktok_published_at") or d.get("tiktok_status_denenmez")
                or web_aktif(d)):
            continue                                 # web planlı (tiktok_web.py): sorgu yok
        sonraki = _ts(d.get("tiktok_status_sonraki_deneme"))
        if sonraki is not None and sonraki > simdi_ts:
            continue
        liste.append((str(d.get("tiktok_status_checked_at") or ""),
                      os.path.basename(os.path.abspath(proje)), proje, str(pid)))
    liste.sort()
    return [(p, _ad(p), pid) for _, _, p, pid in liste]


def _guncelle(proje: str, pid: str, degistir) -> bool:
    """state.json'u YAZIMDAN HEMEN ÖNCE taze okuyup `degistir(durum)` uygular.

    `_durum_oku_kesin`: bozuk state.json'da `{}` okuyup üstüne yazmak kaydın
    tamamını silerdi — okuyamıyorsak yazmıyoruz. publish_id bu arada değiştiyse
    (proje yeniden yüklendi) eski taslağın sonucu yeni kayda YAZILMAZ.
    """
    durum = TPP._durum_oku_kesin(proje)
    if str(durum.get("tiktok_publish_id")) != pid:
        return False
    degistir(durum)
    state_io.durum_yaz(proje, durum)
    return True


def _sorgula(token: str, pid: str, post, uyku):
    """Tek status/fetch. Taşıma hatasında YENİDEN DENER.

    NEDEN yeniden deneme güvenli: bu uç SALT OKUNUR ve idempotent — aynı
    publish_id'yi iki kez sormak TikTok'ta hiçbir şey değiştirmez (yükleme
    çağrılarının tersine; orada belirsiz bir yeniden deneme ikinci taslak
    demekti, bkz. `tiktok_upload.upload_video`). Her deneme hız sınırına
    sayılıyor; 3 deneme 30/dk sınırının çok altında.
    """
    son = None
    for deneme in range(TASIMA_DENEME):
        try:
            return post(API_URL,
                        headers={"Authorization": "Bearer " + token,
                                 "Content-Type": "application/json; charset=UTF-8"},
                        json={"publish_id": pid}, timeout=(10, 30))
        except requests.exceptions.RequestException as e:
            son = e
            if deneme + 1 < TASIMA_DENEME:
                uyku(5.0 * (deneme + 1))
    raise _GenelHata("taşıma hatası (%d deneme): %s"
                     % (TASIMA_DENEME, _temiz(type(son).__name__ + ": " + str(son), token)))


def _yorumla(resp, token: str) -> tuple:
    """("durum", status, post_ids, fail_reason) ya da ("hata", kod, mesaj).

    Genel hatalarda `_GenelHata` atar."""
    http = getattr(resp, "status_code", 0)
    try:
        govde = resp.json()
    except ValueError:
        govde = None
    if not isinstance(govde, dict):
        if http in (401, 429):
            raise _GenelHata("HTTP %d (JSON olmayan yanıt)" % http)
        return ("hata", "http_%d" % http, "JSON olmayan yanıt")
    err = govde.get("error") if isinstance(govde.get("error"), dict) else {}
    kod = str(err.get("code") or "")
    data = govde.get("data") if isinstance(govde.get("data"), dict) else {}
    if (kod and kod != "ok") or http >= 400:
        kod = kod if kod and kod != "ok" else "http_%d" % http
        mesaj = _temiz(err.get("message") or "", token)
        if kod in GENEL_HATA_KODLARI or http in (401, 429):
            raise _GenelHata("%s (HTTP %d) %s" % (kod, http, mesaj))
        return ("hata", kod, mesaj)
    status = str(data.get("status") or "")
    if not status:
        return ("hata", "durum_alani_yok", "yanıtta data.status yok")
    ids = data.get("publicaly_available_post_id")
    if ids is None:                     # belgelenmiş yazım yukarıdaki; olası düzeltmeye tolerans
        ids = data.get("publicly_available_post_id")
    if not isinstance(ids, list):
        ids = [ids] if ids else []
    ids = [str(x) for x in ids if str(x or "").strip()]
    return ("durum", status, ids, _temiz(data.get("fail_reason") or "", token, 120))


# --------------------------------------------------------------------------
# Koşu
# --------------------------------------------------------------------------

def dogrula(log=print, post=None, token_al=None, uyku=None, simdi=None) -> dict:
    """Adayları sorgular, sonuçları yazar, yeni işaretler için TEK bildirim.

    `tamamlandi` True ise günlük damga atılabilir. Hiçbir hata yukarı çıkmaz.
    """
    post = post or requests.post
    token_al = token_al or _token_al
    uyku = uyku or time.sleep
    t = time.time() if simdi is None else simdi
    sonuc = {"tamamlandi": False, "sorgulanan": 0, "isaretlenen": [],
             "yalniz_durum": [], "engellenen": [], "hatalar": [], "denenmez": []}

    adaylar = adaylari_bul(t)
    if not adaylar:
        log("  TikTok yayın doğrulama: aday yok (bekleyen taslak yok ya da "
            "hepsi soğumada/denenmez).")
        sonuc["tamamlandi"] = True
        return sonuc

    try:
        token = (token_al() or {}).get("access_token")
        sebep = None if token else "token dosyasında access_token yok"
    except Exception as e:                                   # noqa: BLE001
        token = None
        # Mesaj BİLEREK yazılmıyor: yenileme hatası TikTok yanıt gövdesini
        # taşıyor ve maskeleyicinin tanımadığı bir sır içerebilir.
        sebep = "token alınamadı (%s)" % type(e).__name__
    if not token:
        mesaj = ("UYARI: TikTok yayın doğrulama ÇALIŞMADI — %s. %d taslak "
                 "doğrulanamıyor. Gerekirse: python upload/tiktok_auth.py --print-url"
                 % (sebep, len(adaylar)))
        log("  " + mesaj)
        notify.uyar_bir_kez("tiktok-yayin-dogrulama-token", mesaj)
        return sonuc

    damga = _damga(t)
    try:
        for i, (proje, ad, pid) in enumerate(adaylar[:KOSU_TAVANI]):
            if i:
                uyku(ISTEK_ARALIGI_SN)
            sonuc["sorgulanan"] += 1
            try:
                _isle(proje, ad, pid, token, post, uyku, t, damga, log, sonuc)
            except TPP.IsaretlemeHatasi as e:
                sonuc["hatalar"].append(ad)
                log("  TikTok doğrulama: '%s' yazılamadı — %s" % (ad, _temiz(e, token)))
    except _GenelHata as e:
        mesaj = ("UYARI: TikTok yayın doğrulama yarıda kesildi — %s. Günlük damga "
                 "atılmadı, sonraki koşu yeniden dener." % _temiz(e, token, 300))
        log("  " + mesaj)
        notify.uyar_bir_kez("tiktok-yayin-dogrulama-genel", mesaj)
    else:
        sonuc["tamamlandi"] = True

    _bildir(sonuc, log)
    kalan = max(0, len(adaylar) - KOSU_TAVANI)
    log("  TikTok yayın doğrulama: %d sorgu%s — işaretlenen: %s; yalnız durum: %d; "
        "plan engeli: %s; hata: %d; denenmez: %s"
        % (sonuc["sorgulanan"], (" (%d aday sonraki güne)" % kalan) if kalan else "",
           ", ".join(sonuc["isaretlenen"]) or "yok", len(sonuc["yalniz_durum"]),
           ", ".join(sonuc["engellenen"]) or "yok", len(sonuc["hatalar"]),
           ", ".join(sonuc["denenmez"]) or "yok"))
    return sonuc


def _isle(proje, ad, pid, token, post, uyku, t, damga, log, sonuc) -> None:
    sinif = _yorumla(_sorgula(token, pid, post, uyku), token)

    if sinif[0] == "hata":
        _, kod, mesaj = sinif
        tavan = KALICI_HATA_TAVANI if kod in KALICI_HATA_KODLARI else GECICI_HATA_TAVANI
        yeni_denenmez = []

        def _hata(d):
            sayi = int(d.get("tiktok_status_hata_sayisi") or 0) + 1
            d["tiktok_publish_status"] = "HATA"
            d["tiktok_status_checked_at"] = damga
            d["tiktok_status_hata"] = ("%s: %s" % (kod, mesaj)).rstrip(": ")
            d["tiktok_status_hata_sayisi"] = sayi
            d["tiktok_status_sonraki_deneme"] = _damga(t + SOGUMA_SN)
            if sayi >= tavan:
                d["tiktok_status_denenmez"] = "%s (%d ardışık hata, son %s)" % (kod, sayi, damga)
                yeni_denenmez.append(ad)

        _guncelle(proje, pid, _hata)
        sonuc["hatalar"].append(ad)
        sonuc["denenmez"].extend(yeni_denenmez)
        log("  TikTok doğrulama: '%s' sorgu hatası %s — 24 saat soğuma%s"
            % (ad, kod, "; artık DENENMEYECEK" if yeni_denenmez else ""))
        return

    _, status, ids, fail_reason = sinif

    def _temel(d):
        d["tiktok_publish_status"] = status
        d["tiktok_status_checked_at"] = damga
        for alan in _HATA_ALANLARI:
            d.pop(alan, None)
        d.pop("tiktok_status_isaret_engeli", None)

    if status == "FAILED":
        def _failed(d):
            _temel(d)
            d["tiktok_status_denenmez"] = "FAILED: %s (%s)" % (fail_reason or "sebep yok", damga)
        _guncelle(proje, pid, _failed)
        sonuc["denenmez"].append(ad)
        log("  TikTok doğrulama: '%s' FAILED (%s) — artık denenmeyecek"
            % (ad, fail_reason or "sebep yok"))
        return

    if status != "PUBLISH_COMPLETE":
        _guncelle(proje, pid, _temel)
        sonuc["yalniz_durum"].append(ad)
        return

    try:
        plan = TPP.build_plan(proje)
    except Exception as e:                                   # noqa: BLE001
        plan = {"hazir": False, "engel": "plan hesaplanamadı (%s)" % type(e).__name__}
    if not plan.get("hazir"):
        engel = _temiz(plan.get("engel") or "sebep bilinmiyor", token, 300)

        def _engelli(d):
            _temel(d)
            d["tiktok_status_isaret_engeli"] = engel
        _guncelle(proje, pid, _engelli)
        sonuc["engellenen"].append(ad)
        log("  TikTok doğrulama: '%s' TikTok'ta yayında (API) ama işaretlenmedi — "
            "plan engeli: %s" % (ad, engel))
        return

    def _yayinda(d):
        _temel(d)
        if ids:                         # gelmediyse uydurulmaz (bu hesapta hiç gelmedi)
            d["tiktok_post_ids"] = ids
    if not _guncelle(proje, pid, _yayinda):
        return
    # Damga TESPİT ANI (API yayın zamanı vermiyor) ve görünürlük bilinmiyor
    # (herkese açık da "Sadece ben" de aynı durumu veriyor).
    yazildi, _ = TPP.isaretle_yayinlandi(
        proje, zaman=damga,
        kaynak="%s, %s — yaklaşık zaman; görünürlük bilinmiyor"
               % (KAYNAK_ETIKETI, damga))
    if yazildi:
        sonuc["isaretlenen"].append(ad)
    else:
        sonuc["yalniz_durum"].append(ad)       # bu arada Telegram onayı işaretlemiş


def _bildir(sonuc: dict, log) -> None:
    """Yeni işaretlenenler için koşu başına TEK mesaj. İdempotentliği işaretin
    kendisi sağlıyor (işaretli proje bir daha aday olmaz). Gönderim başarısızsa
    işaretler GERİ ALINMAZ — olgu doğru, yalnız haber gitmedi."""
    if not sonuc["isaretlenen"]:
        return
    # Özet TEK mesaj: kaç taslak, adlarıyla. İlk koşularda eski taslakların çoğu
    # (kullanıcının çoktan yayınladıkları) burada toplu çıkacak; kullanıcı neden
    # bunlara kit gelmediğini bu mesajdan anlamalı.
    metin = ("TikTok'ta yayında bulundu (API): %d taslak — %s. Yayınlandı olarak "
             "işaretlendi (zaman yaklaşık, görünürlük bilinmiyor); bu taslaklara yayın "
             "kiti gönderilmeyecek." % (len(sonuc["isaretlenen"]),
                                        ", ".join(sonuc["isaretlenen"])))
    try:
        gitti = notify.send("TikTok yayını doğrulandı", metin)
    except Exception as e:                                   # noqa: BLE001
        gitti = False
        log("  TikTok doğrulama: bildirim gönderilemedi (%s) — işaretler geçerli"
            % type(e).__name__)
    if not gitti:
        log("  TikTok doğrulama: bildirim gitmedi — işaretler geçerli: %s"
            % ", ".join(sonuc["isaretlenen"]))


def gunluk_dogrulama(log=print, simdi=None, **kw) -> dict:
    """Günde bir `dogrula()`. Damga yalnız koşu TAMAMLANINCA atılır."""
    t = time.time() if simdi is None else simdi
    bugun = time.strftime("%Y-%m-%d", time.localtime(t))
    if _durum().get(GUN_DAMGASI) == bugun:
        return {"atlandi": "bugün zaten çalıştı"}
    sonuc = dogrula(log=log, simdi=t, **kw)
    if sonuc.get("tamamlandi"):
        _kaydet({GUN_DAMGASI: bugun})
    return sonuc


# --------------------------------------------------------------------------
# Kayıtlı durumdan işaretleme — API'ye ÇIKMAZ, ELLE çalıştırılır
# --------------------------------------------------------------------------

KAYITLI_KAYNAK_ETIKETI = "TikTok API PUBLISH_COMPLETE (kayıtlı durumdan)"


def kayitli_durumdan_isaretle(uygula: bool = False, log=print) -> dict:
    """State'te ZATEN `PUBLISH_COMPLETE` okunmuş taslakları işaretler — İSTEK YOK.

    NEDEN (2026-09-13): 02:23 saatlik koşusu 6 taslakta PUBLISH_COMPLETE okudu ama
    canlı checkout'taki yarım bir düzenleme (modül sürüm karışıklığı -> TypeError)
    yüzünden `build_plan` çöktü; işaret yazılmadı ve günlük damga atıldı. Durum
    state'te doğru duruyor; yeniden sorgulamak gereksiz istek, beklemek de işareti
    günlerce geciktirir (koşu başına 10 aday, en eski okunan önce).

    KURAL `dogrula()` ile AYNI: işaretsiz, denenmez olmayan, `build_plan`
    `hazir=True`. Damga = kayıtlı durum okumasının anı (`tiktok_status_checked_at`,
    yoksa şimdi). Bayat `tiktok_status_isaret_engeli` notu işaretle birlikte silinir.
    Yazan tek fonksiyon yine `tiktok_publish_plan.isaretle_yayinlandi`.

    ÇAĞIRAN: yalnız operatör (CLI, varsayılan KURU). Saatlik hatta BİLEREK bağlı
    değil: kayıtlı bir okumayı otomatik "yayınlandı"ya çevirmek, ölçüm hattının
    kendisinin yaptığı işti — bu yol yalnız o hattın bir kez kaçırdığı kayıtlar için.
    """
    sonuc = {"isaretlenecek": [], "isaretlenen": [], "engellenen": [], "hatalar": []}
    for proje in uyumluluk.proje_klasorleri():
        d = TPP._durum_oku(proje)
        pid = d.get("tiktok_publish_id")
        if (not pid or d.get("tiktok_published_at") or d.get("tiktok_status_denenmez")
                or d.get("tiktok_publish_status") != "PUBLISH_COMPLETE"):
            continue
        ad = _ad(proje)
        try:
            plan = TPP.build_plan(proje)
        except Exception as e:                               # noqa: BLE001
            plan = {"hazir": False, "engel": "plan hesaplanamadı (%s)" % type(e).__name__}
        if not plan.get("hazir"):
            engel = _temiz(plan.get("engel") or "sebep bilinmiyor", sinir=160)
            sonuc["engellenen"].append((ad, engel))
            log("  işaretlenmez (plan engeli): %s — %s" % (ad, engel))
            continue
        okundu = str(d.get("tiktok_status_checked_at") or "")
        damga = okundu if _ts(okundu) is not None else _damga(time.time())
        sonuc["isaretlenecek"].append(ad)
        if not uygula:
            log("  [kuru] işaretlenecek: %s (durum okuması %s)" % (ad, okundu or "zamanı yok"))
            continue
        try:
            _guncelle(proje, str(pid), lambda x: x.pop("tiktok_status_isaret_engeli", None))
            yazildi, _ = TPP.isaretle_yayinlandi(
                proje, zaman=damga,
                kaynak="%s, durum okuması %s — yaklaşık zaman; görünürlük bilinmiyor"
                       % (KAYITLI_KAYNAK_ETIKETI, okundu or damga))
        except TPP.IsaretlemeHatasi as e:
            sonuc["hatalar"].append(ad)
            log("  yazılamadı: %s — %s" % (ad, _temiz(e)))
            continue
        if yazildi:
            sonuc["isaretlenen"].append(ad)
            log("  işaretlendi: %s (%s)" % (ad, damga))
    return sonuc


def main(argv=None) -> int:
    TPP._cikti_utf8()
    ap = argparse.ArgumentParser(
        description="TikTok taslak durumu — API'ye ÇIKMAYAN yardımcılar (günlük sorgu "
                    "auto_process'ten gider).")
    ap.add_argument("--kayitli-durumdan", action="store_true", required=True, dest="kayitli",
                    help="State'te PUBLISH_COMPLETE okunmuş, işaretsiz ve hazir=True "
                         "taslakları işaretle (varsayılan KURU)")
    ap.add_argument("--uygula", action="store_true", help="Gerçekten yaz (yoksa kuru)")
    args = ap.parse_args(argv)
    s = kayitli_durumdan_isaretle(uygula=args.uygula)
    print("Özet: işaretlenecek %d, işaretlenen %d, plan engeli %d, hata %d%s" % (
        len(s["isaretlenecek"]), len(s["isaretlenen"]), len(s["engellenen"]),
        len(s["hatalar"]), "" if args.uygula else " — KURU, hiçbir şey yazılmadı (--uygula ile yaz)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
