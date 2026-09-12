"""Türkçe BAŞLIKLI bildirimler gerçekten gidiyor mu? (2026-09-11 canlı arızası)

ARIZA: `notify.send()` başlığı `headers={"Title": title}` ile gönderiyordu.
`requests` -> `http.client` HTTP başlıklarını LATIN-1 ile kodluyor; Türkçenin
ı(U+0131) İ(U+0130) ş(U+015F) ğ(U+011F) harfleri latin-1'de YOK. Sonuç
`UnicodeEncodeError` -> send() içinde yakalanıp sessizce False. Yani başlığında
bu harflerden biri geçen HER bildirim ölüydü. `auto_process.log`'da iki kez
gerçekleşti (15:13 "Haftalık izlenme süresi", 18:13 "DJ set yayında").

ç ö ü Ç Ö Ü latin-1'DE VAR — bu yüzden arıza tüm Türkçe başlıklarda değil
sadece bir kısmında görünüyordu ve tam olarak bu yüzden gözden kaçtı.

BU TESTLERİN YÖNTEMİ — neden düz bir "mock çağrıldı mı" testi DEĞİL:
sahte `requests.post` katmanı `http.client`'ın gerçek kısıtını TAKLİT EDİYOR
(`_latin1_kati_post`): her header adı/değeri latin-1'e kodlanmaya ÇALIŞILIYOR ve
sığmazsa gerçek hayattaki gibi patlıyor. Yani bu testler "fonksiyon çağrıldı"
demiyor, "bu istek TELDEN GEÇEBİLİR" diyor. Eski kod bu katmanda patlardı.

GERÇEK BİLDİRİM GÖNDERİLMİYOR — hiçbir testte gerçek ağ çağrısı yok; sahte
katman kurulmadan istek denenirse test bilerek patlar.
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

import notify

# Bugün log'a düşen iki gerçek başlık — arızanın kanıtı ve regresyon çapası.
BUGUN_KAYBOLAN_BASLIKLAR = ("Haftalık izlenme süresi", "DJ set yayında")


class _SahteYanit:
    def __init__(self, kod=200):
        self.status_code = kod

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("HTTP %s" % self.status_code)


def _latin1_kati_post(kayit, kod=200):
    """http.client'ın GERÇEK davranışını taklit eden sahte taşıma katmanı.

    CPython `http.client.putheader()` header adını ve değerini latin-1 ile
    kodluyor, `putrequest()` de istek satırını ascii ile. Burada da aynısı
    yapılıyor: sığmayan bir karakter varsa test tam da üretimdeki hatayla
    (UnicodeEncodeError) patlar — yani "başlık latin-1'e sığıyor mu" iddiası
    varsayım değil, ÖLÇÜM."""
    def _post(url, data=None, headers=None, timeout=None, **kw):
        url.encode("ascii")                      # istek satırı
        for ad, deger in (headers or {}).items():
            ad.encode("latin-1")
            str(deger).encode("latin-1")         # <- eski kod TAM BURADA patlıyordu
        assert isinstance(data, bytes), "gövde ham byte olarak gitmeli"
        kayit.append({"url": url, "data": data, "headers": dict(headers or {}),
                      "timeout": timeout})
        return _SahteYanit(kod)
    return _post


@pytest.fixture(autouse=True)
def _temiz_kosu(monkeypatch):
    """Her test ayrı bir 'koşu': uyar_bir_kez hafızası sıfır, ağ yasak."""
    notify._uyarilanlar.clear()

    def _yasak(*a, **k):
        raise AssertionError("GERÇEK HTTP isteği denendi — sahte katman kullanılmalı")

    monkeypatch.setattr(notify.requests, "post", _yasak)
    yield
    notify._uyarilanlar.clear()


def _kanal_kur(monkeypatch, tmp_path, topic="fms-test-konusu-123"):
    p = tmp_path / "notify_config.json"
    p.write_text(json.dumps({"ntfy_topic": topic}), encoding="utf-8")
    monkeypatch.setattr(notify, "_CONFIG_PATH", str(p))
    return topic


def _sahte_main_log(monkeypatch, tmp_path):
    """Çalışan scriptin LOG_PATH'ini taklit et (auto_process.py deseni).
    GERÇEK auto_process.log'a ASLA yazılmıyor."""
    log_path = tmp_path / "auto_process.log"
    sahte_main = types.ModuleType("__main__")
    sahte_main.LOG_PATH = str(log_path)
    monkeypatch.setitem(sys.modules, "__main__", sahte_main)
    return log_path


# --------------------------------------------------------------------------
# 1. Arızanın kendisi: bu başlıklar gerçekten latin-1'e sığmıyor
# --------------------------------------------------------------------------

def test_arizanin_kaniti_bu_basliklar_latin1e_sigmiyor():
    """Önce hastalığı çivile: aksi hâlde "düzeltme" neyi düzelttiğini
    kanıtlayamaz. ç/ö/ü'nün SIĞDIĞINI da gösteriyor — arızanın neden sadece
    bazı Türkçe başlıklarda göründüğünün açıklaması bu."""
    for baslik in BUGUN_KAYBOLAN_BASLIKLAR:
        with pytest.raises(UnicodeEncodeError):
            baslik.encode("latin-1")
    assert notify._gonderilemeyen_karakterler("Haftalık izlenme süresi") == "ı"
    assert notify._gonderilemeyen_karakterler("DJ set ENGELLENDİ") == "İ"
    # Bu harfler latin-1'de VAR — sorunlu olanlar sadece ı İ ş Ş ğ Ğ
    assert notify._gonderilemeyen_karakterler("İzlenme ölçümü kapalı") == "İı"
    assert notify._gonderilemeyen_karakterler("Netlify/Instagram hattı arızalı") == "ı"


# --------------------------------------------------------------------------
# 2. Düzeltme: Türkçe başlık + Türkçe gövde telden geçiyor
# --------------------------------------------------------------------------

def test_turkce_baslik_ve_govde_latin1_katmanindan_geciyor(monkeypatch, tmp_path):
    topic = _kanal_kur(monkeypatch, tmp_path)
    kayit = []
    monkeypatch.setattr(notify.requests, "post", _latin1_kati_post(kayit))

    baslik = "DJ set yayında"
    mesaj = "'Gece Seansı Vol. 1' temiz çıktı — yayına açıldı, İyi şanslar! ğüşıöç"
    assert notify.send(baslik, mesaj) is True

    assert len(kayit) == 1
    c = kayit[0]

    # (a) Konu adı URL'de DEĞİL — ntfy'nin JSON publish şartı.
    assert c["url"] == "https://ntfy.sh/"
    assert topic not in c["url"]

    # (b) Başlıkta ARTIK değişken metin yok; hepsi latin-1'e sığıyor.
    #     (_latin1_kati_post zaten ölçtü; burada sabit olduğunu da çiviliyoruz.)
    assert c["headers"] == {"Content-Type": "application/json"}
    for ad, deger in c["headers"].items():
        ad.encode("latin-1")
        deger.encode("latin-1")

    # (c) GÖVDE UTF-8 ve TÜRKÇE — kaçış dizisi değil, ham Türkçe baytlar.
    assert "yayında".encode("utf-8") in c["data"]
    assert "Gece Seansı".encode("utf-8") in c["data"]
    assert "ğüşıöç".encode("utf-8") in c["data"]
    assert b"\\u" not in c["data"], "gövde \\uXXXX kaçışlı değil, ham UTF-8 olmalı"

    # (d) Gövde geçerli JSON ve alanlar bozulmadan karşı tarafa gidiyor.
    govde = json.loads(c["data"].decode("utf-8"))
    assert govde["topic"] == topic
    assert govde["title"] == baslik      # başlık TÜRKÇE kaldı, katlanmadı
    assert govde["message"] == mesaj     # gövde TÜRKÇE kaldı
    assert govde["priority"] == 3        # eski Priority: "default" karşılığı

    assert c["timeout"] == (5, 10)


def test_eski_yontem_ayni_katmanda_patliyordu():
    """Kontrol grubu: eski `headers={"Title": title}` deseni aynı sahte
    katmanda patlıyor. Düzeltmenin gerçekten kısıtı kaldırdığını gösterir —
    yoksa test sadece kendi taklidini doğrulamış olurdu."""
    kayit = []
    post = _latin1_kati_post(kayit)
    with pytest.raises(UnicodeEncodeError):
        post("https://ntfy.sh/fms-test",
             data=b"govde",
             headers={"Title": "DJ set yayında", "Priority": "default"},
             timeout=(5, 10))
    assert kayit == []


# --------------------------------------------------------------------------
# 3. Deseni kapat: deponun GERÇEKTEN kullandığı TÜM başlıklar
# --------------------------------------------------------------------------

def _repo_bildirim_basliklari():
    """Depodaki `notify.send(...)` ve `_bildir(...)` çağrılarının İLK argümanı
    (başlık) olan sabit metinleri AST ile toplar.

    NEDEN grep değil AST: `_bildir("DJ set ENGELLENDİ", mesaj)` gibi çağrılar
    çok satıra yayılıyor ve grep'in yakaladığı şey metin değil satır oluyor.
    NEDEN elle yazılmış bir liste değil: CLAUDE.md'deki "unutulacak bir liste"
    tuzağı — yarın eklenecek 13. başlık bu listeye yazılmazdı. Bu fonksiyon
    kaynağı tarıyor, yani YENİ başlıklar teste kendiliğinden dahil oluyor."""
    hedef_klasorler = (_REPO, os.path.join(_REPO, "upload"))
    basliklar = {}
    for klasor in hedef_klasorler:
        for ad in sorted(os.listdir(klasor)):
            if not ad.endswith(".py"):
                continue
            yol = os.path.join(klasor, ad)
            try:
                agac = ast.parse(io.open(yol, encoding="utf-8").read(), filename=yol)
            except (OSError, SyntaxError):
                continue
            for dugum in ast.walk(agac):
                if not isinstance(dugum, ast.Call) or not dugum.args:
                    continue
                f = dugum.func
                notify_send = (isinstance(f, ast.Attribute) and f.attr == "send"
                               and isinstance(f.value, ast.Name)
                               and f.value.id == "notify")
                bildir_sarmalayici = (isinstance(f, ast.Name)
                                      and f.id in ("_bildir", "bildir"))
                if not (notify_send or bildir_sarmalayici):
                    continue
                ilk = dugum.args[0]
                if isinstance(ilk, ast.Constant) and isinstance(ilk.value, str):
                    basliklar.setdefault(ilk.value, []).append(
                        "%s:%d" % (os.path.relpath(yol, _REPO), dugum.lineno))
    return basliklar


def test_repo_basliklari_bulunabiliyor():
    """Tarayıcı bozulursa (ör. çağrı şekli değişirse) bir sonraki test
    boş kümede dolanıp SESSİZCE geçerdi — tam da bu deponun tipik arızası."""
    basliklar = _repo_bildirim_basliklari()
    assert len(basliklar) >= 10, basliklar
    for beklenen in BUGUN_KAYBOLAN_BASLIKLAR:
        assert beklenen in basliklar, (beklenen, sorted(basliklar))


def test_repodaki_her_baslik_gercekten_gonderilebiliyor(monkeypatch, tmp_path):
    """Kanalın kullandığı HER başlık, latin-1 katı katmandan geçerek gidiyor mu?

    Bu testin eski kodda DÜŞECEĞİ başlıklar (bugün ölü olanlar):
    "DJ set ENGELLENDİ", "DJ set yayında", "Netlify/Instagram hattı arızalı",
    "İzlenme ölçümü kapalı", "Haftalık izlenme süresi"."""
    _kanal_kur(monkeypatch, tmp_path)
    basliklar = _repo_bildirim_basliklari()
    kayit = []
    monkeypatch.setattr(notify.requests, "post", _latin1_kati_post(kayit))

    for baslik in sorted(basliklar):
        notify._uyarilanlar.clear()
        sonuc = notify.send(baslik, "Türkçe gövde: ışığı söndürdüğünde ağladı.")
        assert sonuc is True, (baslik, basliklar[baslik])

    assert len(kayit) == len(basliklar)
    for c, baslik in zip(kayit, sorted(basliklar)):
        govde = json.loads(c["data"].decode("utf-8"))
        assert govde["title"] == baslik            # hiçbir başlık katlanmadı
        assert "ışığı söndürdüğünde" in govde["message"]


def test_bugun_kaybolan_iki_baslik_artik_gidiyor(monkeypatch, tmp_path):
    """Somut regresyon çapası: log'daki iki gerçek vaka."""
    _kanal_kur(monkeypatch, tmp_path)
    kayit = []
    monkeypatch.setattr(notify.requests, "post", _latin1_kati_post(kayit))
    for baslik in BUGUN_KAYBOLAN_BASLIKLAR:
        notify._uyarilanlar.clear()
        assert notify.send(baslik, "gövde Türkçe kalıyor") is True
    assert [json.loads(c["data"].decode("utf-8"))["title"] for c in kayit] \
        == list(BUGUN_KAYBOLAN_BASLIKLAR)


# --------------------------------------------------------------------------
# 4. Deseni kapat: kodlama hatası AĞ hatası değil, ayrı anlatılmalı
# --------------------------------------------------------------------------

def test_kodlama_hatasi_agdan_AYRI_ve_KALICI_diye_loglaniyor(monkeypatch, tmp_path):
    """Eski kodda ikisi de aynı "bildirim gonderilemedi" satırına düşüyordu ve
    kalıcı bir kod bug'ı geçici bir ağ aksaklığı gibi görünüyordu. Artık ayrı
    anahtar, ayrı metin — ve aynı koşuda İKİSİ BİRDEN olabilir, biri diğerini
    susturmamalı (uyar_bir_kez anahtar başına çalışıyor)."""
    _kanal_kur(monkeypatch, tmp_path)
    log_path = _sahte_main_log(monkeypatch, tmp_path)

    def _kodlama_patlat(*a, **k):
        "Bir başlık gerçekten latin-1 başlığına konsaydı bu olurdu."
        return "yayında".encode("latin-1")

    monkeypatch.setattr(notify.requests, "post", _kodlama_patlat)
    assert notify.send("DJ set yayında", "gövde") is False
    assert notify.send("DJ set yayında", "gövde") is False   # ikinci kez log'a yazmaz

    def _ag_patlat(*a, **k):
        raise OSError("ağ yok")

    monkeypatch.setattr(notify.requests, "post", _ag_patlat)
    assert notify.send("TikTok", "gövde") is False

    satirlar = [s for s in io.open(log_path, encoding="utf-8").read().splitlines()
                if s.strip()]
    assert len(satirlar) == 2, satirlar          # iki AYRI anahtar, üç çağrı
    kodlama = [s for s in satirlar if "KALICI" in s]
    ag = [s for s in satirlar if "Gecici olabilir" in s]
    assert len(kodlama) == 1 and len(ag) == 1, satirlar
    assert "kod duzeltmesi gerek" in kodlama[0]
    assert "tekrar denemek duzeltmez" in kodlama[0]
    assert "yayında"[3] in kodlama[0]            # sorunlu harfi ('ı') adıyla söylüyor
    assert "KALICI" not in ag[0]                 # ağ hatası kalıcı denmiyor


def test_ag_hatasi_hala_gecici_olarak_anlatiliyor(monkeypatch, tmp_path):
    """Ayrıştırma, mevcut davranışı BOZMADAN yapıldı: ağ hatası hâlâ koşu
    başına tek satır ve hâlâ False dönüyor (saglik_kontrol/weekly_report
    'damga atma, sonraki koşuda tekrar dene' mantığı buna bağlı)."""
    _kanal_kur(monkeypatch, tmp_path)
    log_path = _sahte_main_log(monkeypatch, tmp_path)
    monkeypatch.setattr(notify.requests, "post", lambda *a, **k: _SahteYanit(500))
    assert notify.send("TikTok", "gövde") is False
    assert notify.send("TikTok", "gövde") is False
    satirlar = [s for s in io.open(log_path, encoding="utf-8").read().splitlines()
                if s.strip()]
    assert len(satirlar) == 1, satirlar
    assert "gonderilemedi" in satirlar[0]


def test_kanal_yokken_hic_istek_denenmiyor(monkeypatch, tmp_path):
    """Türkçe başlıkla da olsa: kanal yoksa ağa çıkılmaz, tek satır uyarı."""
    monkeypatch.setattr(notify, "_CONFIG_PATH", str(tmp_path / "yok.json"))
    log_path = _sahte_main_log(monkeypatch, tmp_path)
    assert notify.send("DJ set yayında", "gövde") is False   # _yasak post çağrılmadı
    assert "kanali kurulu DEGIL" in io.open(log_path, encoding="utf-8").read()
