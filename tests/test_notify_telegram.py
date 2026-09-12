"""notify.py'nin TELEGRAM arka ucu — SAHTE bir HTTP katmanıyla.

NEDEN (2026-09-12): sekiz sağlık kontrolünün tamamı
(`saglik_kontrol.kontrol_et` -> `_bildir` -> `notify.send`) tek bir bildirim
hattına bağlıydı ve o hat (ntfy.sh) bugüne kadar TEK BİR teslim kaydı
bırakmadı — `notify_config.json` uzun süre hiç yoktu, yani `notify.py`
yazıldığından beri doğrulanmış bir push yok. Telegram hattı ise ÜRETİMDE
KANITLI (`auto_process.log`, 2026-09-12 06:48: "Telegram: tamam — 8").
Emniyet ağı kanıtlanmamış değil, kanıtlanmış kanaldan geçmeli.

BU TESTLERİN ÇİVİLEDİĞİ YEDİ ŞEY:
  (a) Telegram yapılandırılmışsa bildirim ORAYA gidiyor (doğru URL/gövde),
  (b) yapılandırılmamışsa ntfy YEDEĞİNE düşüyor (eski yol SİLİNMEDİ),
  (c) bildirim chat id'si YAYIN chat id'sine eşitse HİÇBİR istek atılmıyor
      + koşu başına bir log satırı (yayın akışına operatör uyarısı karışmasın),
  (d) Türkçe başlık (ı İ ş ğ) sorunsuz gidiyor — latin-1 katı katmandan geçiyor,
  (e) `send()` sözleşmesi (imza + bool dönüş + çağrı noktaları) korunuyor,
  (f) `parse_mode` GÖNDERİLMİYOR,
  (g) hata yolunda ntfy'ye SESSİZCE kaçılmıyor: log + False (damga atılmaz,
      bir sonraki koşu yeniden dener).

GERÇEK BİLDİRİM GÖNDERİLMİYOR — ne Telegram'a ne ntfy'ye. `requests.post` her
testte sahtesiyle değiştiriliyor; sahte katman kurulmadan bir istek denenirse
test bilerek patlar. Gerçek `notify_config.json` ve gerçek
`upload/telegram_client_secrets.json` HİÇ OKUNMUYOR — iki yol da tmp_path'e
yönlendiriliyor, testteki token uydurma.
"""

import ast
import io
import json
import os
import sys
import types

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)
sys.path.insert(0, os.path.join(_REPO, "upload"))

import notify

# Uydurma token — gerçek bir bot token'ı DEĞİL, hiçbir yere gitmiyor.
SAHTE_TOKEN = "1234567890:TEST-SAHTE-TOKEN-hicbir-yere-gitmez"
YAYIN_CHAT = "-1004337174284"      # yükleme hattının kullandığı kanal (örnek biçim)
OPERATOR_CHAT = "987654321"        # kullanıcının kişisel DM chat id'si (örnek biçim)


class _SahteYanit:
    def __init__(self, kod=200, govde=None):
        self.status_code = kod
        self._govde = govde if govde is not None else {"ok": True, "result": {"message_id": 8}}

    def json(self):
        return self._govde

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("HTTP %s" % self.status_code)


def _latin1_kati_post(kayit, yanit=None):
    """http.client'ın GERÇEK davranışını taklit eden sahte taşıma katmanı.

    `tests/test_notify_turkce_baslik.py`'deki katmanın aynısı: HTTP başlığı
    latin-1'e, istek satırı ascii'ye kodlanmaya ÇALIŞILIYOR. Yani "bu istek
    telden geçebilir" iddiası varsayım değil ÖLÇÜM. Telegram yolunda da
    başlığa değişken metin konmadığının kanıtı bu."""
    def _post(url, data=None, headers=None, timeout=None, **kw):
        url.encode("ascii")
        for ad, deger in (headers or {}).items():
            ad.encode("latin-1")
            str(deger).encode("latin-1")
        assert isinstance(data, bytes), "gövde ham byte olarak gitmeli"
        kayit.append({"url": url, "data": data, "headers": dict(headers or {}),
                      "timeout": timeout})
        return yanit if yanit is not None else _SahteYanit(200)
    return _post


@pytest.fixture(autouse=True)
def _temiz_kosu(monkeypatch):
    """Her test ayrı bir 'koşu': uyarı hafızası sıfır, gerçek ağ YASAK."""
    notify._uyarilanlar.clear()

    def _yasak(*a, **k):
        raise AssertionError("GERÇEK HTTP isteği denendi — sahte katman kullanılmalı")

    monkeypatch.setattr(notify.requests, "post", _yasak)
    yield
    notify._uyarilanlar.clear()


def _kur(monkeypatch, tmp_path, config=None, sirlar=None):
    """notify_config.json + upload/telegram_client_secrets.json taklidi.

    İkisi de tmp_path'te — gerçek dosyalara HİÇ dokunulmuyor."""
    c = tmp_path / "notify_config.json"
    c.write_text(json.dumps(config or {}), encoding="utf-8")
    monkeypatch.setattr(notify, "_CONFIG_PATH", str(c))

    s = tmp_path / "telegram_client_secrets.json"
    if sirlar is None:
        monkeypatch.setattr(notify, "_TELEGRAM_SECRETS_PATH", str(tmp_path / "yok.json"))
    else:
        s.write_text(json.dumps(sirlar), encoding="utf-8")
        monkeypatch.setattr(notify, "_TELEGRAM_SECRETS_PATH", str(s))


def _sahte_main_log(monkeypatch, tmp_path):
    """Çalışan scriptin LOG_PATH'ini taklit et (auto_process.py deseni).
    GERÇEK auto_process.log'a ASLA yazılmıyor."""
    log_path = tmp_path / "auto_process.log"
    sahte_main = types.ModuleType("__main__")
    sahte_main.LOG_PATH = str(log_path)
    monkeypatch.setitem(sys.modules, "__main__", sahte_main)
    return log_path


def _satirlar(log_path):
    return [s for s in io.open(log_path, encoding="utf-8").read().splitlines() if s.strip()]


# --------------------------------------------------------------------------
# (a) Telegram yapılandırılmışsa bildirim ORAYA gidiyor
# --------------------------------------------------------------------------

def test_telegram_yapilandirildiysa_oraya_gidiyor(monkeypatch, tmp_path):
    _kur(monkeypatch, tmp_path,
         config={"ntfy_topic": "fms-yedek", "telegram_chat_id": OPERATOR_CHAT},
         sirlar={"bot_token": SAHTE_TOKEN, "chat_id": YAYIN_CHAT})
    kayit = []
    monkeypatch.setattr(notify.requests, "post", _latin1_kati_post(kayit))

    assert notify.send("TikTok", "'Gece Sürüşü' taslak bekliyor — yayınla.") is True

    assert len(kayit) == 1
    c = kayit[0]
    assert c["url"] == "https://api.telegram.org/bot%s/sendMessage" % SAHTE_TOKEN
    # ntfy'ye HİÇ gidilmedi — öncelik Telegram'da.
    assert "ntfy.sh" not in c["url"]

    govde = json.loads(c["data"].decode("utf-8"))
    assert govde["chat_id"] == OPERATOR_CHAT
    # Başlık ve mesaj tek metinde, aralarında boş satır.
    assert govde["text"] == "TikTok" + chr(10) + chr(10) + \
        "'Gece Sürüşü' taslak bekliyor — yayınla."
    assert c["headers"] == {"Content-Type": "application/json"}
    assert c["timeout"] == (5, 10)


def test_telegram_kuruluysa_is_configured_true(monkeypatch, tmp_path):
    """ntfy_topic HİÇ yokken bile kanal kurulu sayılmalı — çağıranlar
    (ör. tiktok_upload.notify_pending_publish) buna bakıyor."""
    _kur(monkeypatch, tmp_path,
         config={"telegram_chat_id": OPERATOR_CHAT},
         sirlar={"bot_token": SAHTE_TOKEN, "chat_id": YAYIN_CHAT})
    assert notify.is_configured() is True


# --------------------------------------------------------------------------
# (b) Telegram yoksa ntfy YEDEĞİ — eski yol silinmedi
# --------------------------------------------------------------------------

def test_telegram_yoksa_ntfyye_dusuyor(monkeypatch, tmp_path):
    _kur(monkeypatch, tmp_path, config={"ntfy_topic": "fms-test-konusu-123"},
         sirlar={"bot_token": SAHTE_TOKEN, "chat_id": YAYIN_CHAT})
    kayit = []
    monkeypatch.setattr(notify.requests, "post", _latin1_kati_post(kayit))

    assert notify.send("DJ set yayında", "gövde") is True
    assert len(kayit) == 1
    assert kayit[0]["url"] == "https://ntfy.sh/"
    govde = json.loads(kayit[0]["data"].decode("utf-8"))
    assert govde["topic"] == "fms-test-konusu-123"
    assert govde["title"] == "DJ set yayında"


def test_bot_token_okunamazsa_ntfyye_dusuyor_ve_sessiz_kalmiyor(monkeypatch, tmp_path):
    """telegram_chat_id VAR ama secrets dosyası yok: yapılandırma EKSİK —
    yapısal bir durum, gönderim hatası değil. Yedek devreye girer, ama
    eksiklik log'a düşer (sessiz düşüş bu deponun belgelenmiş hatası)."""
    _kur(monkeypatch, tmp_path,
         config={"ntfy_topic": "fms-yedek", "telegram_chat_id": OPERATOR_CHAT},
         sirlar=None)
    log_path = _sahte_main_log(monkeypatch, tmp_path)
    kayit = []
    monkeypatch.setattr(notify.requests, "post", _latin1_kati_post(kayit))

    assert notify.send("TikTok", "mesaj") is True
    assert kayit[0]["url"] == "https://ntfy.sh/"
    assert "bot token'i" in _satirlar(log_path)[0]


def test_iki_kanal_da_yoksa_eski_davranis(monkeypatch, tmp_path):
    """Mevcut sözleşme: koşu başına TEK log satırı + False."""
    _kur(monkeypatch, tmp_path, config={}, sirlar=None)
    log_path = _sahte_main_log(monkeypatch, tmp_path)

    assert notify.is_configured() is False
    for _ in range(17):
        assert notify.send("TikTok", "mesaj") is False

    satirlar = _satirlar(log_path)
    assert len(satirlar) == 1, satirlar
    assert "kanali kurulu DEGIL" in satirlar[0]


# --------------------------------------------------------------------------
# (c) YAYIN KANALINA YAZMA KAPISI
# --------------------------------------------------------------------------

def test_bildirim_chat_id_yayin_chat_idye_esitse_GONDERMIYOR(monkeypatch, tmp_path):
    """EN KRİTİK KISIT: operatör uyarıları yayın akışına karışmamalı.

    Kapı olmasaydı tek bir kopyala-yapıştır hatası ("chat_id'yi aynen aldım")
    alarm akışını yayın akışının içine boşaltırdı ve geri alınamazdı."""
    _kur(monkeypatch, tmp_path,
         config={"telegram_chat_id": YAYIN_CHAT},          # <- AYNI id
         sirlar={"bot_token": SAHTE_TOKEN, "chat_id": YAYIN_CHAT})
    log_path = _sahte_main_log(monkeypatch, tmp_path)

    # requests.post autouse fixture'da YASAK — çağrılırsa test patlar.
    assert notify.send("Uyumluluk kapısı çöktü", "3 gündür yayın yok") is False

    satirlar = _satirlar(log_path)
    # İKİ satır, İKİ AYRI anahtar: (1) kapı kapandı, (2) geriye kullanılabilir
    # hiçbir kanal kalmadı. İkincisi susturulmamalı — "bildirim gitmedi"nin
    # sebebi kapı, ama SONUCU "bu koşuda hiçbir uyarı ulaşmadı".
    assert len(satirlar) == 2, satirlar
    assert "KALICI" in satirlar[0]
    assert "yayin chat id" in satirlar[0]
    assert "hicbir istek atilmadi" in satirlar[0].casefold()
    assert "kanali kurulu DEGIL" in satirlar[1]
    # Kapı kapalıyken kanal "kurulu" sayılmamalı (ntfy yedeği de yok).
    assert notify.is_configured() is False


def test_kapi_bosluk_ve_buyuk_kucuk_harf_farkina_ALDANMIYOR(monkeypatch, tmp_path):
    """Kullanıcı adı biçimli id'ler ("@kanaladi") Telegram'da harf duyarsız;
    yapılandırmaya boşlukla yapışan bir değer de gözle AYNI görünür. Kapının
    tek bir boşluk yüzünden açılması, kapının hiç olmamasıyla aynı şey."""
    _kur(monkeypatch, tmp_path,
         config={"telegram_chat_id": "  @Hermes_Famous_Asistan  "},
         sirlar={"bot_token": SAHTE_TOKEN, "chat_id": "@hermes_famous_asistan"})
    log_path = _sahte_main_log(monkeypatch, tmp_path)
    assert notify.send("Uyarı", "mesaj") is False
    assert "KALICI" in _satirlar(log_path)[0]


def test_kapi_kapaninca_ntfy_yedegi_varsa_oradan_gidiyor(monkeypatch, tmp_path):
    """Kapı Telegram'ı kapatır; bildirimi KAYBETMEZ. Telegram'a hiç istek
    atılmadığı için burada yedeğe düşmek 'hatayı gizlemek' değil — üstelik
    kalıcı hata satırı her koşuda log'a düşmeye devam ediyor."""
    _kur(monkeypatch, tmp_path,
         config={"ntfy_topic": "fms-yedek", "telegram_chat_id": YAYIN_CHAT},
         sirlar={"bot_token": SAHTE_TOKEN, "chat_id": YAYIN_CHAT})
    log_path = _sahte_main_log(monkeypatch, tmp_path)
    kayit = []
    monkeypatch.setattr(notify.requests, "post", _latin1_kati_post(kayit))

    assert notify.send("Uyarı", "mesaj") is True
    assert len(kayit) == 1
    assert kayit[0]["url"] == "https://ntfy.sh/"
    # Telegram'a giden TEK bir istek bile yok.
    assert all("api.telegram.org" not in c["url"] for c in kayit)
    assert "KALICI" in _satirlar(log_path)[0]


def test_farkli_chat_idler_kapiya_TAKILMIYOR(monkeypatch, tmp_path):
    """Kapı yalnız eşitlikte kapanmalı — aksi hâlde çalışan hattı öldürürdü."""
    _kur(monkeypatch, tmp_path,
         config={"telegram_chat_id": OPERATOR_CHAT},
         sirlar={"bot_token": SAHTE_TOKEN, "chat_id": YAYIN_CHAT})
    kayit = []
    monkeypatch.setattr(notify.requests, "post", _latin1_kati_post(kayit))
    assert notify.send("Uyarı", "mesaj") is True
    assert "api.telegram.org" in kayit[0]["url"]


# --------------------------------------------------------------------------
# (d) Türkçe karakter — ı İ ş ğ
# --------------------------------------------------------------------------

@pytest.mark.parametrize("baslik", [
    "Haftalık izlenme süresi",
    "DJ set yayında",
    "DJ set ENGELLENDİ",
    "İzlenme ölçümü kapalı",
    "Netlify/Instagram hattı arızalı",
])
def test_turkce_baslik_telegramdan_sorunsuz_gidiyor(monkeypatch, tmp_path, baslik):
    """Bu başlıkların hepsi latin-1'e SIĞMIYOR (ntfy'nin eski HTTP başlığı
    tuzağı tam buydu). Telegram yolunda gövde UTF-8 JSON, başlıkta değişken
    metin YOK — yani tuzak burada hiç kurulmuyor; test bunu ÖLÇÜYOR."""
    with pytest.raises(UnicodeEncodeError):
        baslik.encode("latin-1")

    _kur(monkeypatch, tmp_path,
         config={"telegram_chat_id": OPERATOR_CHAT},
         sirlar={"bot_token": SAHTE_TOKEN, "chat_id": YAYIN_CHAT})
    kayit = []
    monkeypatch.setattr(notify.requests, "post", _latin1_kati_post(kayit))

    mesaj = "Türkçe gövde: ışığı söndürdüğünde ağladı. İYİ ŞANSLAR ğüşıöç"
    assert notify.send(baslik, mesaj) is True

    c = kayit[0]
    # Gövde HAM UTF-8 — \\uXXXX kaçışı değil (telde gerçekten Türkçe).
    assert baslik.encode("utf-8") in c["data"]
    assert "ışığı söndürdüğünde".encode("utf-8") in c["data"]
    assert b"\\u" not in c["data"], "gövde \\uXXXX kaçışlı değil, ham UTF-8 olmalı"
    govde = json.loads(c["data"].decode("utf-8"))
    assert govde["text"].startswith(baslik)     # başlık katlanmadı/bozulmadı
    assert mesaj in govde["text"]


# --------------------------------------------------------------------------
# (e) send() SÖZLEŞMESİ — sekiz emniyet ağı buna bağlı
# --------------------------------------------------------------------------

def test_send_imzasi_degismedi():
    """`send(baslik, mesaj) -> bool`. İmza bozulursa sekiz çağrı noktası
    (saglik_kontrol._bildir, weekly_report, watch_projects, tiktok_upload,
    dj_tarama_kontrol, auto_process, ...) birden kırılır."""
    import inspect
    p = list(inspect.signature(notify.send).parameters.values())
    assert [x.name for x in p] == ["title", "message"]
    assert all(x.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD for x in p)
    assert all(x.default is inspect.Parameter.empty for x in p)


def test_her_yolda_gercek_bool_donuyor(monkeypatch, tmp_path):
    """`_bildir`/`weekly_report` damgayı SADECE True'da atıyor; truthy bir
    nesne (ör. Response) dönmek damgayı yanlışlıkla attırırdı."""
    # 1) Telegram başarı
    _kur(monkeypatch, tmp_path,
         config={"telegram_chat_id": OPERATOR_CHAT},
         sirlar={"bot_token": SAHTE_TOKEN, "chat_id": YAYIN_CHAT})
    monkeypatch.setattr(notify.requests, "post", _latin1_kati_post([]))
    assert notify.send("X", "y") is True
    # 2) Telegram 4xx
    notify._uyarilanlar.clear()
    _sahte_main_log(monkeypatch, tmp_path)
    monkeypatch.setattr(notify.requests, "post", _latin1_kati_post(
        [], _SahteYanit(400, {"ok": False, "error_code": 400,
                              "description": "Bad Request: chat not found"})))
    assert notify.send("X", "y") is False
    # 3) Kanal yok
    notify._uyarilanlar.clear()
    _kur(monkeypatch, tmp_path, config={}, sirlar=None)
    assert notify.send("X", "y") is False


def test_repodaki_tum_cagri_noktalari_iki_konumsal_argumanla_cagiriyor():
    """AST ile TÜM `notify.send(...)` çağrılarını tarar.

    NEDEN elle liste değil: yarın eklenecek dokuzuncu çağrı noktası listeye
    yazılmazdı (CLAUDE.md'deki "unutulacak liste" tuzağı). NEDEN grep değil:
    çağrılar çok satıra yayılıyor, grep metni değil satırı yakalıyor."""
    bulunan = []
    for klasor in (_REPO, os.path.join(_REPO, "upload")):
        for ad in sorted(os.listdir(klasor)):
            if not ad.endswith(".py"):
                continue
            yol = os.path.join(klasor, ad)
            try:
                agac = ast.parse(io.open(yol, encoding="utf-8").read(), filename=yol)
            except (OSError, SyntaxError):
                continue
            for d in ast.walk(agac):
                if not isinstance(d, ast.Call):
                    continue
                f = d.func
                if not (isinstance(f, ast.Attribute) and f.attr == "send"
                        and isinstance(f.value, ast.Name) and f.value.id == "notify"):
                    continue
                yer = "%s:%d" % (os.path.relpath(yol, _REPO), d.lineno)
                bulunan.append(yer)
                assert len(d.args) == 2, (yer, "send(baslik, mesaj) bekleniyor")
                assert not d.keywords, (yer, "send() anahtar kelimeli argüman almıyor")
                assert not any(isinstance(a, ast.Starred) for a in d.args), yer
    # Tarayıcı bozulursa boş kümede dolanıp SESSİZCE geçerdi.
    assert len(bulunan) >= 5, bulunan


# --------------------------------------------------------------------------
# (f) parse_mode GÖNDERİLMİYOR
# --------------------------------------------------------------------------

def test_parse_mode_gonderilmiyor(monkeypatch, tmp_path):
    """upload/telegram_upload.py ile AYNI karar: caption/metinde tırnak, alt
    çizgi, köşeli parantez, emoji ve dosya yolu geçiyor; Markdown/HTML modunda
    kaçırılmamış TEK bir karakter "can't parse entities" ile TÜM gönderimi
    düşürür. Bir alarm kanalında bu, "uyarı metninde alt çizgi olduğu için
    uyarı hiç ulaşmadı" demek olurdu."""
    _kur(monkeypatch, tmp_path,
         config={"telegram_chat_id": OPERATOR_CHAT},
         sirlar={"bot_token": SAHTE_TOKEN, "chat_id": YAYIN_CHAT})
    kayit = []
    monkeypatch.setattr(notify.requests, "post", _latin1_kati_post(kayit))

    # Markdown'da kaçırılması gereken karakterlerin hepsi bir arada.
    mesaj = "state.json *bozuk*: _auto_process.log_ [satır 3400] `x` (a) ~b~ 100% 🔔"
    assert notify.send("Uyarı", mesaj) is True

    govde = json.loads(kayit[0]["data"].decode("utf-8"))
    assert "parse_mode" not in govde
    assert govde["text"].endswith(mesaj)    # metin AYNEN gidiyor, kaçırılmadan


def test_cok_uzun_metin_kirpiliyor(monkeypatch, tmp_path):
    """4096 karakter sınırı aşılırsa Telegram TÜM mesajı reddeder — sessiz
    kayıp yerine kırp."""
    _kur(monkeypatch, tmp_path,
         config={"telegram_chat_id": OPERATOR_CHAT},
         sirlar={"bot_token": SAHTE_TOKEN, "chat_id": YAYIN_CHAT})
    kayit = []
    monkeypatch.setattr(notify.requests, "post", _latin1_kati_post(kayit))
    assert notify.send("Başlık", "ş" * 6000) is True
    govde = json.loads(kayit[0]["data"].decode("utf-8"))
    assert len(govde["text"]) == notify._TELEGRAM_MAX_CHARS


# --------------------------------------------------------------------------
# (g) HATA YOLU — ntfy'ye SESSİZCE kaçılmıyor
# --------------------------------------------------------------------------

def test_4xx_kalici_diye_loglaniyor_ve_ntfyye_KACILMIYOR(monkeypatch, tmp_path):
    """KARAR: Telegram yapılandırılmış ve istek GERÇEKTEN denenmişse,
    başarısızlıkta ntfy'ye kaçmak yanlış olurdu — ntfy 200 dönerse send()
    True döner, `saglik_kontrol._bildir()` günlük damgayı atar ve uyarı 24
    saat bir daha DENENMEZ; üstelik Telegram'ın bozuk olduğu "bildirim gitti"
    görüntüsünün altında gizlenir. Bu yüzden: log + False."""
    _kur(monkeypatch, tmp_path,
         config={"ntfy_topic": "fms-yedek", "telegram_chat_id": OPERATOR_CHAT},
         sirlar={"bot_token": SAHTE_TOKEN, "chat_id": YAYIN_CHAT})
    log_path = _sahte_main_log(monkeypatch, tmp_path)
    kayit = []
    monkeypatch.setattr(notify.requests, "post", _latin1_kati_post(
        kayit, _SahteYanit(400, {"ok": False, "error_code": 400,
                                 "description": "Bad Request: chat not found"})))

    assert notify.send("Uyarı", "mesaj") is False
    assert notify.send("Uyarı", "mesaj") is False        # ikinci kez log'a yazmaz

    # ntfy'ye TEK bir istek bile gitmedi.
    assert all("ntfy.sh" not in c["url"] for c in kayit), kayit
    satirlar = _satirlar(log_path)
    assert len(satirlar) == 1, satirlar
    assert "KALICI" in satirlar[0]
    assert "chat not found" in satirlar[0]
    assert SAHTE_TOKEN not in satirlar[0]                # token log'a düşmüyor


def test_5xx_gecici_diye_loglaniyor_ve_False_donuyor(monkeypatch, tmp_path):
    """Geçici hata AYRI anahtar/AYRI metin: kalıcı bir yapılandırma hatasını
    geçici bir aksaklık gibi göstermek (ve tersi) bu deponun belgelenmiş
    hatası. Damga atılmadığı için bir sonraki saatlik koşu yeniden dener."""
    _kur(monkeypatch, tmp_path,
         config={"ntfy_topic": "fms-yedek", "telegram_chat_id": OPERATOR_CHAT},
         sirlar={"bot_token": SAHTE_TOKEN, "chat_id": YAYIN_CHAT})
    log_path = _sahte_main_log(monkeypatch, tmp_path)
    kayit = []
    monkeypatch.setattr(notify.requests, "post", _latin1_kati_post(
        kayit, _SahteYanit(502, {"ok": False, "description": "Bad Gateway"})))

    assert notify.send("Uyarı", "mesaj") is False
    satirlar = _satirlar(log_path)
    assert len(satirlar) == 1, satirlar
    assert "KALICI" not in satirlar[0]
    assert "Gecici olabilir" in satirlar[0]
    assert all("ntfy.sh" not in c["url"] for c in kayit)


def test_ag_hatasinda_token_LOGA_DUSMUYOR(monkeypatch, tmp_path):
    """requests'in ağ istisnaları mesajlarının içinde TAM istek URL'ini
    taşıyor ve bot token URL'in YOLUNDA. Maskelenmezse token düz metin olarak
    log'a düşer — 2026-09-04'te bir Instagram token'ıyla gerçekten yaşandı."""
    _kur(monkeypatch, tmp_path,
         config={"telegram_chat_id": OPERATOR_CHAT},
         sirlar={"bot_token": SAHTE_TOKEN, "chat_id": YAYIN_CHAT})
    log_path = _sahte_main_log(monkeypatch, tmp_path)

    def _patlayan_post(*a, **k):
        raise OSError(
            "HTTPSConnectionPool: Max retries exceeded with url: "
            "/bot%s/sendMessage" % SAHTE_TOKEN)

    monkeypatch.setattr(notify.requests, "post", _patlayan_post)

    assert notify.send("Uyarı", "mesaj") is False
    metin = io.open(log_path, encoding="utf-8").read()
    assert SAHTE_TOKEN not in metin
    assert "gizli-token" in metin
    assert "Gecici olabilir" in metin
