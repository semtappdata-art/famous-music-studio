# -*- coding: utf-8 -*-
"""Ağ hatasında yeniden deneme: SINIFLANDIRMA + kopya kapısı KURU KANITI.

Bu dosya, `upload/ag_yeniden_deneme.py`nin üç yükleyicide (Telegram, Bluesky,
Facebook) ürettiği davranışı SAHTE bir HTTP katmanıyla gösteriyor — hiçbir
gerçek ağ çağrısı, hiçbir gerçek kimlik dosyası okunmuyor.

Kanıtlanan dört senaryo (her platform için):
  1. bağlantı KURULAMADI (ConnectTimeout / DNS)  -> yeniden DENENDİ
  2. yanıt okunurken KOPTU (ReadTimeout)         -> yeniden DENENMEDİ
                                                    (ya da DOĞRULANARAK denendi)
  3. 429 (rate limit)                            -> mevcut davranış KORUNDU
  4. başarı                                      -> TEK istek

Ayrıca: belirsiz işareti bırakılan bir proje bir sonraki koşuda YÜKLENMİYOR —
kopya kapısı (`ag.kapi`), bu değişikliğin asıl varlık sebebi.

GÜVENLİK NOTU: hiçbir gerçek token değeri bu dosyada YOK; sahte kimlik
bilgileri açıkça sahte ("111:SAHTE"). `os.path.isfile` monkeypatch'LENMİYOR —
testler gerçek geçici dosyalar oluşturuyor, böylece gerçek token dosyalarının
varlığı/yokluğu testin sonucunu etkilemiyor.
"""

import json
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD = os.path.join(REPO, "upload")
for _yol in (UPLOAD, REPO):
    if _yol not in sys.path:
        sys.path.insert(0, _yol)

import requests
import urllib3

import ag_yeniden_deneme as ag


# ---------------------------------------------------------------------------
# sahte HTTP katmanı
# ---------------------------------------------------------------------------

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
    """Sıraya dizilmiş sonuçları döndüren `requests` yerine geçen nesne.

    Her eleman ya bir SahteYanit ya da fırlatılacak bir istisna. Liste
    biterse SON eleman tekrarlanır — "hep aynı hatayı veren ağ" senaryosu
    böyle kuruluyor.
    """

    exceptions = requests.exceptions

    def __init__(self, post=None, get=None):
        self._post = list(post or [])
        self._get = list(get or [])
        self.post_cagrilari = []
        self.get_cagrilari = []

    @staticmethod
    def _ver(kuyruk):
        if not kuyruk:
            raise AssertionError("sahte HTTP: beklenmeyen ek çağrı")
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
    """GERÇEK şekliyle bir "bağlantı hiç kurulamadı" hatası.

    requests bunu `ConnectionError(MaxRetryError(reason=NewConnectionError))`
    olarak sarıyor ve ayrımı taşıyan bilgi `reason` özniteliğinde — düz
    `ConnectionError('...')` üretmek bu testi sahte kolaylaştırırdı.
    """
    return requests.exceptions.ConnectionError(
        urllib3.exceptions.MaxRetryError(
            pool=None, url="https://ornek/x",
            reason=urllib3.exceptions.NewConnectionError(None, "DNS yok")))


def govdeden_sonra_koptu():
    """Gövde gönderildikten SONRA yanıt beklenirken kopma."""
    return requests.exceptions.ReadTimeout("yanıt gelmedi")


@pytest.fixture(autouse=True)
def _beklemeden(monkeypatch):
    """Testler GERÇEKTEN beklemesin (2 sn + 4 sn geri çekilme)."""
    monkeypatch.setattr(ag, "TABAN_BEKLEME", 0)


@pytest.fixture
def proje(tmp_path):
    """Render edilmiş bir projenin minimal taklidi."""
    p = tmp_path / "Sahte Sarki"
    (p / "output").mkdir(parents=True)
    (p / "output" / "youtube_16x9.mp4").write_bytes(b"0" * 1024)
    (p / "output" / "shorts_9x16.mp4").write_bytes(b"0" * 512)
    (p / "meta.json").write_text(
        json.dumps({"title": "Sahte Sarki", "theme": "pop"}, ensure_ascii=False),
        encoding="utf-8")
    (p / "state.json").write_text("{}", encoding="utf-8")
    return str(p)


def _durum(proje):
    with open(os.path.join(proje, "state.json"), "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 1) sınıflandırma tablosu — kararın KAYNAĞI
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("istisna, beklenen", [
    # requests belgesi AYNEN: "Requests that produced this error are safe to retry."
    (requests.exceptions.ConnectTimeout("x"), ag.GUVENLI),
    # Gerçek DNS/bağlantı-reddi şekli (MaxRetryError.reason)
    (baglanti_kurulamadi(), ag.GUVENLI),
    # "the server did not send any data" -> istek ZATEN gönderilmişti
    (requests.exceptions.ReadTimeout("x"), ag.BELIRSIZ),
    # Yanıt aşaması -> istek işlendi
    (requests.exceptions.ChunkedEncodingError("x"), ag.BELIRSIZ),
    # Çıplak ConnectionError iki anlamlı -> TEMKİNLİ taraf
    (requests.exceptions.ConnectionError("x"), ag.BELIRSIZ),
    (requests.exceptions.SSLError("x"), ag.BELIRSIZ),
    # Yanıt ALINDI: sonuç biliniyor, belirsizlik yok
    (requests.exceptions.HTTPError("x"), ag.KALICI),
    # İstek hazırlanamadı: yeniden deneme ASLA düzeltmez
    (requests.exceptions.MissingSchema("x"), ag.KALICI),
    # Bizim kodumuzun hatası
    (KeyError("x"), ag.KALICI),
])
def test_siniflandirma(istisna, beklenen):
    assert ag.sinifla(istisna) == beklenen


def test_urllib3_httperror_adi_kalici_sanilmiyor():
    """AD ÇAKIŞMASI MUHAFIZI (geliştirme sırasında canlı yakalandı).

    `urllib3.exceptions.HTTPError` urllib3'ün TÜM hatalarının taban sınıfı —
    `NewConnectionError` bile ondan türüyor. Çıplak adla eşleştirilirse gerçek
    bir DNS hatası "kalıcı" sayılır ve HİÇ yeniden denenmez; ilk yazımda tam
    olarak bu oldu. `requests.exceptions.HTTPError` ise gerçekten kalıcı.
    """
    assert ag.sinifla(baglanti_kurulamadi()) == ag.GUVENLI
    assert ag.sinifla(urllib3.exceptions.NewConnectionError(None, "x")) == ag.GUVENLI
    assert ag.sinifla(requests.exceptions.HTTPError("x")) == ag.KALICI


# ---------------------------------------------------------------------------
# 2) TELEGRAM — doğrulama YOK (Bot API sohbet geçmişi okutmuyor)
# ---------------------------------------------------------------------------

@pytest.fixture
def telegram(monkeypatch):
    import telegram_upload as tg

    monkeypatch.setattr(tg, "_load_credentials",
                        lambda: {"bot_token": "111:SAHTE", "chat_id": "@sahtekanal"})
    monkeypatch.setattr(tg, "_probe_dimensions", lambda p: (1920, 1080))
    monkeypatch.setattr(tg, "_probe_duration", lambda p: 42)

    class _Zaman:
        sleep = staticmethod(lambda sn: None)      # 429 beklemesi anında geçsin
        strftime = staticmethod(__import__("time").strftime)

    monkeypatch.setattr(tg, "time", _Zaman)
    return tg


TG_BASARI = SahteYanit(200, {"ok": True, "result": {"message_id": 4242}})


def test_telegram_baglanti_kurulamadi_yeniden_denenir(telegram, proje, monkeypatch):
    http = SahteHTTP(post=[baglanti_kurulamadi(), TG_BASARI])
    monkeypatch.setattr(telegram, "requests", http)

    assert telegram.upload_video(proje, kind="uzun") == 4242
    assert len(http.post_cagrilari) == 2, "bağlantı kurulamadı -> yeniden denenmeliydi"
    assert _durum(proje)["telegram_message_id"] == 4242
    assert ag.ISARET_ALANI not in _durum(proje)


def test_telegram_yanit_beklenirken_koptu_yeniden_DENENMEZ(telegram, proje, monkeypatch):
    http = SahteHTTP(post=[govdeden_sonra_koptu()])
    monkeypatch.setattr(telegram, "requests", http)

    with pytest.raises(ag.BelirsizSonuc):
        telegram.upload_video(proje, kind="uzun")

    assert len(http.post_cagrilari) == 1, (
        "gövde gönderildikten sonra koptu -> İKİNCİ bir sendVideo ASLA "
        "gitmemeli (kanalda ikinci video demek)")
    st = _durum(proje)
    assert "telegram_message_id" not in st, "yüklendi diye YAZMAMALI"
    isaret = st[ag.ISARET_ALANI]["telegram_message_id"]
    assert isaret["istisna"] == "ReadTimeout"
    assert isaret["platform"] == "Telegram"


def test_telegram_429_davranisi_korundu(telegram, proje, monkeypatch):
    http = SahteHTTP(post=[
        SahteYanit(429, {"ok": False, "parameters": {"retry_after": 0}}),
        TG_BASARI,
    ])
    monkeypatch.setattr(telegram, "requests", http)

    assert telegram.upload_video(proje, kind="uzun") == 4242
    assert len(http.post_cagrilari) == 2, "429 -> bekle ve tekrar dene (eski davranış)"


def test_telegram_basarida_tek_istek(telegram, proje, monkeypatch):
    http = SahteHTTP(post=[TG_BASARI])
    monkeypatch.setattr(telegram, "requests", http)

    assert telegram.upload_video(proje, kind="uzun") == 4242
    assert len(http.post_cagrilari) == 1


def test_telegram_belirsiz_isaret_ikinci_yuklemeyi_ENGELLER(telegram, proje, monkeypatch):
    """ASIL KAZANIM: süpürge yeniden çağırsa bile kopya ÜRETİLMİYOR.

    `ek_platform_backfill` bu projeyi hâlâ "Telegram'a hiç gitmemiş" görüyor
    (state'te `telegram_message_id` yok) ve bir sonraki koşuda yeniden
    çağırır. Kapı yükleyicinin İÇİNDE olduğu için çağıran kim olursa olsun
    ikinci bir gönderi çıkmıyor.
    """
    ag.belirsiz_isaretle(proje, "telegram_message_id", "Telegram",
                         "Telegram sendVideo", "ReadTimeout", log=lambda *a: None)
    http = SahteHTTP(post=[TG_BASARI])
    monkeypatch.setattr(telegram, "requests", http)

    with pytest.raises(ag.BelirsizSonuc):
        telegram.upload_video(proje, kind="uzun")
    assert http.post_cagrilari == [], "işaret dururken TEK BİR istek bile çıkmamalı"

    # Operatör kanala bakıp "gönderi yok" dedikten sonra işaret temizlenir:
    assert ag.belirsizi_temizle(proje, "telegram_message_id") is True
    assert telegram.upload_video(proje, kind="uzun") == 4242


def test_telegram_ag_hatasi_token_sizdirmiyor(telegram, proje, monkeypatch):
    """Yeniden deneme eklenirken 2026-09-04 sızıntısının kapısı açılmasın.

    Bot token URL'in YOLUNDA; istisna metni tam URL'i taşıyor. Tükenmiş
    yeniden denemelerin ürettiği istisna SADECE tip adını taşımalı.
    """
    http = SahteHTTP(post=[requests.exceptions.ConnectTimeout(
        "HTTPSConnectionPool(host='api.telegram.org'): "
        "/bot111:SAHTEGIZLITOKEN1234567890ABCDEFGHIJKLMNOP/sendVideo")])
    monkeypatch.setattr(telegram, "requests", http)

    with pytest.raises(Exception) as hata:
        telegram.upload_video(proje, kind="uzun")
    metin = str(hata.value)
    assert "SAHTEGIZLITOKEN" not in metin
    assert "ConnectTimeout" in metin
    assert len(http.post_cagrilari) == ag.MAX_DENEME, "güvenli hata -> sonuna kadar denenmeli"


# ---------------------------------------------------------------------------
# 3) BLUESKY — DOĞRULAYARAK yeniden deneme (listRecords auth istemiyor)
# ---------------------------------------------------------------------------

def _kayit(metin, dakika_once=0):
    import datetime
    an = (datetime.datetime.now(datetime.timezone.utc)
          - datetime.timedelta(minutes=dakika_once))
    return {"uri": "at://did:plc:x/app.bsky.feed.post/abc", "cid": "bafy",
            "value": {"text": metin, "createdAt": an.isoformat()}}


def test_bluesky_dogrulama_gonderiyi_buluyor(monkeypatch):
    import bluesky_upload as bs
    http = SahteHTTP(get=[SahteYanit(200, {"records": [_kayit("merhaba")]})])
    monkeypatch.setattr(bs, "requests", http)

    bulunan = bs._gonderi_zaten_var_mi("https://pds", "did:plc:x", "merhaba")
    assert bulunan is not None and bulunan is not ag.BILINMIYOR
    assert bulunan.uri.startswith("at://")


def test_bluesky_dogrulama_eski_kaydi_saymaz(monkeypatch):
    """Aynı metnin AYLAR önceki kopyası "az önce gitti" sayılmamalı."""
    import bluesky_upload as bs
    http = SahteHTTP(get=[SahteYanit(200, {"records": [_kayit("merhaba", 60 * 24)]})])
    monkeypatch.setattr(bs, "requests", http)

    assert bs._gonderi_zaten_var_mi("https://pds", "did:plc:x", "merhaba") is None


def test_bluesky_dogrulama_okunamazsa_BILINMIYOR(monkeypatch):
    import bluesky_upload as bs
    http = SahteHTTP(get=[requests.exceptions.ConnectionError("ağ yok")])
    monkeypatch.setattr(bs, "requests", http)

    assert bs._gonderi_zaten_var_mi("https://pds", "did:plc:x", "merhaba") is ag.BILINMIYOR


def _bluesky_send_post_denemesi(monkeypatch, proje, get_kuyrugu, gonderi_hatasi):
    """`upload_video`in send_post sarmalayıcısıyla BİREBİR aynı bağlantı.

    atproto istemcisinin tamamını taklit etmek yerine, üretimde kurulan
    sözleşme (cagri = send_post, dogrula = _gonderi_zaten_var_mi) aynen
    kuruluyor — test edilen şey tam olarak o bağlantı.
    """
    import bluesky_upload as bs
    monkeypatch.setattr(bs, "requests", SahteHTTP(get=get_kuyrugu))
    sayac = {"n": 0}

    def _send_post():
        sayac["n"] += 1
        if sayac["n"] <= len(gonderi_hatasi) and gonderi_hatasi[sayac["n"] - 1]:
            raise gonderi_hatasi[sayac["n"] - 1]
        return _BasariliGonderi()

    sonuc = ag.guvenli_istek(
        _send_post,
        ne="Bluesky createRecord (send_post)",
        dogrula=lambda: bs._gonderi_zaten_var_mi("https://pds", "did:plc:x", "merhaba"),
        proje=proje, anahtar="bluesky_post_uri", platform="Bluesky",
        log=lambda *a, **k: None,
    )
    return sonuc, sayac["n"]


class _BasariliGonderi:
    uri = "at://did:plc:x/app.bsky.feed.post/yeni"
    cid = "bafyeni"


def test_bluesky_koptu_ve_gonderi_GITMIS_yeniden_gondermez(monkeypatch, proje):
    sonuc, deneme = _bluesky_send_post_denemesi(
        monkeypatch, proje,
        get_kuyrugu=[SahteYanit(200, {"records": [_kayit("merhaba")]})],
        gonderi_hatasi=[govdeden_sonra_koptu()])
    assert deneme == 1, "gönderi zaten gitmişti -> İKİNCİ createRecord YOK"
    assert sonuc.uri.endswith("/abc"), "state'e DOĞRULANMIŞ uri yazılmalı"
    assert ag.ISARET_ALANI not in _durum(proje)


def test_bluesky_koptu_ve_gonderi_GITMEMIS_yeniden_gonderir(monkeypatch, proje):
    sonuc, deneme = _bluesky_send_post_denemesi(
        monkeypatch, proje,
        get_kuyrugu=[SahteYanit(200, {"records": []})],
        gonderi_hatasi=[govdeden_sonra_koptu(), None])
    assert deneme == 2, "kesinlikle gitmemiş -> yeniden denemek GÜVENLİ"
    assert sonuc.uri.endswith("/yeni")


def test_bluesky_koptu_ve_DOGRULANAMADI_isaret_birakir(monkeypatch, proje):
    with pytest.raises(ag.BelirsizSonuc):
        _bluesky_send_post_denemesi(
            monkeypatch, proje,
            get_kuyrugu=[requests.exceptions.ConnectionError("ağ yok")],
            gonderi_hatasi=[govdeden_sonra_koptu()])
    st = _durum(proje)
    assert "bluesky_post_uri" not in st
    assert st[ag.ISARET_ALANI]["bluesky_post_uri"]["platform"] == "Bluesky"


def test_bluesky_belirsiz_isaret_ikinci_gonderiyi_ENGELLER(monkeypatch, proje):
    import bluesky_upload as bs
    ag.belirsiz_isaretle(proje, "bluesky_post_uri", "Bluesky", "send_post",
                         "ReadTimeout", log=lambda *a: None)
    # Ağ katmanı hiç kurulmadan reddedilmeli.
    monkeypatch.setattr(bs, "requests", SahteHTTP())
    with pytest.raises(ag.BelirsizSonuc):
        bs.upload_video(proje)


# ---------------------------------------------------------------------------
# 4) FACEBOOK — Reels yapısı gereği güvenli, uzun format DOĞRULAMA ile
# ---------------------------------------------------------------------------

@pytest.fixture
def facebook(monkeypatch):
    import facebook_upload as fb
    monkeypatch.setattr(fb, "get_access_token",
                        lambda: {"page_id": "SAHTEPAGE",
                                 "page_access_token": "SAHTE_PAGE_TOKEN"})
    return fb


FB_START = SahteYanit(200, {"video_id": "V1", "upload_url": "https://rupload/x"})
FB_UPLOAD_OK = SahteYanit(200, {"success": True})
FB_FINISH_OK = SahteYanit(200, {"success": True})


def test_facebook_reels_binary_koptuysa_yeniden_denenir(facebook, proje, monkeypatch):
    """Reels faz 2, gövdeden sonra kopsa BİLE yeniden denenebilir.

    Gerekçe kodda ve resmî dokümanda: `video_id` faz 1'de sabitlendi, faz 2
    aynı id'ye yazıyor (offset ile devam ettirilebilir) ve gönderi ancak faz
    3'te doğuyor — yani yeniden deneme İKİNCİ bir video ÜRETEMEZ.
    """
    http = SahteHTTP(post=[FB_START, govdeden_sonra_koptu(), FB_UPLOAD_OK,
                           FB_FINISH_OK])
    monkeypatch.setattr(facebook, "requests", http)

    assert facebook.upload_reels(proje, schedule=False) == "V1"
    assert len(http.post_cagrilari) == 4, "faz 2 bir kez yeniden denenmeliydi"
    assert _durum(proje)["facebook_reels_id"] == "V1"
    assert ag.ISARET_ALANI not in _durum(proje)


def test_facebook_reels_basarida_tek_tur(facebook, proje, monkeypatch):
    http = SahteHTTP(post=[FB_START, FB_UPLOAD_OK, FB_FINISH_OK])
    monkeypatch.setattr(facebook, "requests", http)

    assert facebook.upload_reels(proje, schedule=False) == "V1"
    assert len(http.post_cagrilari) == 3, "üç faz, fazla istek YOK"


def test_facebook_reels_baglanti_kurulamadi_yeniden_denenir(facebook, proje, monkeypatch):
    http = SahteHTTP(post=[baglanti_kurulamadi(), FB_START, FB_UPLOAD_OK,
                           FB_FINISH_OK])
    monkeypatch.setattr(facebook, "requests", http)

    assert facebook.upload_reels(proje, schedule=False) == "V1"
    assert len(http.post_cagrilari) == 4


def test_facebook_uzun_koptu_ve_video_GITMIS_yeniden_yuklemez(facebook, proje, monkeypatch):
    """Uzun format idempotent DEĞİL -> önce SOR, sonra karar ver."""
    http = SahteHTTP(
        post=[govdeden_sonra_koptu()],
        get=[SahteYanit(200, {"data": [{"id": "GERCEK_V", "title": "Sahte Sarki",
                                        "created_time": "2026-09-12T00:00:00+0000"}]})])
    monkeypatch.setattr(facebook, "requests", http)
    # created_time eski görünmesin diye damgayı okunamaz kılmak yerine
    # eşleşmeyi başlıkla kanıtlıyoruz: _uzun_video_bul damga okunamazsa
    # (ya da pencere içindeyse) eşleşmeye güveniyor.
    monkeypatch.setattr(facebook, "_uzun_video_bul",
                        lambda *a, **k: "GERCEK_V")

    assert facebook.upload_long(proje, schedule=False) == "GERCEK_V"
    assert len(http.post_cagrilari) == 1, "İKİNCİ bir /videos POST'u ASLA gitmemeli"
    assert _durum(proje)["facebook_video_id"] == "GERCEK_V"


def test_facebook_uzun_koptu_ve_video_YOK_yeniden_yukler(facebook, proje, monkeypatch):
    http = SahteHTTP(
        post=[govdeden_sonra_koptu(), SahteYanit(200, {"id": "YENI_V"})],
        get=[SahteYanit(200, {"data": []})])
    monkeypatch.setattr(facebook, "requests", http)

    assert facebook.upload_long(proje, schedule=False) == "YENI_V"
    assert len(http.post_cagrilari) == 2


def test_facebook_uzun_zamanlanmissa_YOK_cevabina_guvenmez(facebook, proje, monkeypatch):
    """Zamanlanmış (published=false) video listede görünmeyebilir.

    O yüzden "listede yok" cevabı KESİN sayılmıyor: yeniden yükleme YAPILMAZ,
    belirsiz işareti bırakılır. Sessizce ikinci bir video koymaktansa
    operatörü uyandır.
    """
    import datetime
    monkeypatch.setattr(
        facebook.config, "next_golden_publish_time",
        lambda *a, **k: datetime.datetime.now().astimezone()
        + datetime.timedelta(hours=5))
    http = SahteHTTP(post=[govdeden_sonra_koptu()],
                     get=[SahteYanit(200, {"data": []})])
    monkeypatch.setattr(facebook, "requests", http)

    with pytest.raises(ag.BelirsizSonuc):
        facebook.upload_long(proje, schedule=True)
    assert len(http.post_cagrilari) == 1
    st = _durum(proje)
    assert "facebook_video_id" not in st
    assert st[ag.ISARET_ALANI]["facebook_video_id"]["istisna"] == "ReadTimeout"


def test_facebook_uzun_dogrulanamazsa_isaret_birakir(facebook, proje, monkeypatch):
    http = SahteHTTP(post=[govdeden_sonra_koptu()],
                     get=[requests.exceptions.ConnectionError("ağ yok")])
    monkeypatch.setattr(facebook, "requests", http)

    with pytest.raises(ag.BelirsizSonuc):
        facebook.upload_long(proje, schedule=False)
    assert len(http.post_cagrilari) == 1
    assert ag.belirsiz_mi(proje, "facebook_video_id") is not None


def test_facebook_belirsiz_isaret_ikinci_yuklemeyi_ENGELLER(facebook, proje, monkeypatch):
    ag.belirsiz_isaretle(proje, "facebook_reels_id", "Facebook",
                         "Facebook Reels faz 3 (finish)", "ReadTimeout",
                         log=lambda *a: None)
    http = SahteHTTP(post=[FB_START, FB_UPLOAD_OK, FB_FINISH_OK])
    monkeypatch.setattr(facebook, "requests", http)

    with pytest.raises(ag.BelirsizSonuc):
        facebook.upload_reels(proje, schedule=False)
    assert http.post_cagrilari == []


def test_facebook_uzun_dosya_her_denemede_yeniden_aciliyor(facebook, proje, monkeypatch):
    """Yeniden denemede 0 BAYTLIK video gitmesin.

    multipart gövde dosya tutamağını sonuna kadar tüketiyor; aynı tutamakla
    ikinci deneme boş dosya gönderirdi (telegram'daki seek(0) tuzağının
    ikizi, burada iki ayrı dosya olduğu için seek yetmiyor).
    """
    okunanlar = []

    def _post(url, **kw):
        for _ad, (dosya_adi, tutamak, _tip) in (kw.get("files") or {}).items():
            okunanlar.append(len(tutamak.read()))
        if len(okunanlar) == 1:
            raise baglanti_kurulamadi()
        return SahteYanit(200, {"id": "V2"})

    http = SahteHTTP()
    http.post = _post
    monkeypatch.setattr(facebook, "requests", http)

    assert facebook.upload_long(proje, schedule=False) == "V2"
    assert okunanlar == [1024, 1024], "ikinci denemede de TAM dosya gitmeli"


# ---------------------------------------------------------------------------
# 5) işaret yardımcıları
# ---------------------------------------------------------------------------

def test_isaret_state_io_ile_atomik_yaziliyor(proje):
    """`open(..., "w")` DEĞİL — deponun tek atomik yazıcısı kullanılmalı."""
    (open(os.path.join(proje, "state.json"), "w", encoding="utf-8")
     .write(json.dumps({"youtube_video_id": "abc"})))
    ag.belirsiz_isaretle(proje, "telegram_message_id", "Telegram", "sendVideo",
                         "ReadTimeout", log=lambda *a: None)
    st = _durum(proje)
    assert st["youtube_video_id"] == "abc", "mevcut alanlar KORUNMALI"
    assert ag.belirsiz_mi(st, "telegram_message_id")["istisna"] == "ReadTimeout"
    assert ag.belirsiz_mi(st, "bluesky_post_uri") is None
    assert not os.path.exists(os.path.join(proje, "state.json.tmp"))


def test_isaret_temizlenince_alan_da_gidiyor(proje):
    ag.belirsiz_isaretle(proje, "telegram_message_id", "Telegram", "sendVideo",
                         "ReadTimeout", log=lambda *a: None)
    assert ag.belirsizi_temizle(proje, "telegram_message_id") is True
    assert ag.ISARET_ALANI not in _durum(proje)
    assert ag.belirsizi_temizle(proje, "telegram_message_id") is False
