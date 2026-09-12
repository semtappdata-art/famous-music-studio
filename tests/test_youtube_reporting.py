# -*- coding: utf-8 -*-
"""`upload/youtube_reporting.py` muhafızları — HİÇBİRİ AĞA ÇIKMAZ.

NEDEN VAR: bu modül hayatı boyunca birkaç kez çalışacak ve ilk çalıştırması
GERİ ALINAMAZ. Reporting API'de rapor üretimi bir **job** oluşturulunca
başlıyor ve YouTube geriye dönük olarak yalnızca job'dan ÖNCEKİ 30 günü
dolduruyor (`buyume_kontrol_listesi.md`, B1 — son tarih 2026-10-11). Yani
burada bir hata "bir dahaki sefere düzeltiriz" ile kapanmıyor: yanlış bir tip
adına açılmış bir job, o 30 günlük pencereyi BOŞ bir dosyaya harcar.

Dört şey korunuyor:
  1. **İDEMPOTENTLİK** — aynı rapor tipi için ikinci bir job AÇILMAZ. API
     ikincisini reddetmiyor, sessizce kabul ediyor; yani koruma bizde olmak
     zorunda.
  2. **TİP ADI TAHMİN EDİLMEZ** — `kur()` önce `reportTypes().list` ile
     API'nin KENDİ sözlüğüne bakıyor; listede olmayan bir tip için
     `jobs().create` ÇAĞRILMIYOR. (`reportTypes` boş dönerse hiç job
     açılmıyor — boş listeye güvenip devam etmek tahminin ta kendisi olurdu.)
  3. **İZİN (scope) HATASI SESSİZ KALMAZ** — `{}` / `None` dönmüyor,
     `ReportingHatasi` yükseliyor ve mesaj "ne yapılacağını" + `token.json`'a
     DOKUNMA uyarısını taşıyor.
  4. **LOG MASKELENİYOR** — modülde çıplak `print` YOK; tek çıkış `_log`
     (CLAUDE.md: "bir yorum bir GARANTİ ifade ediyorsa, onu doğrulayan bir
     test olmadan yazma").

Tüm servis nesneleri SAHTEDİR; `googleapiclient` hiç kurulmuyor.
"""

import ast
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "upload"))

import youtube_reporting as yr


# --- Sahte API iskeleti -----------------------------------------------------

class _Istek:
    def __init__(self, sonuc):
        self._sonuc = sonuc

    def execute(self):
        if isinstance(self._sonuc, Exception):
            raise self._sonuc
        return self._sonuc


class _Raporlar:
    def __init__(self, veri):
        self._veri = veri

    def list(self, jobId=None, createdAfter=None, pageToken=None):
        return _Istek({"reports": self._veri.get(jobId, [])})


class _Joblar:
    def __init__(self, joblar, olusturulanlar, raporlar=None, liste_hatasi=None):
        self._joblar = joblar
        self.olusturulanlar = olusturulanlar
        self._raporlar = raporlar or {}
        self._liste_hatasi = liste_hatasi

    def list(self, pageToken=None, includeSystemManaged=None):
        if self._liste_hatasi is not None:
            return _Istek(self._liste_hatasi)
        return _Istek({"jobs": list(self._joblar)})

    def create(self, body=None):
        self.olusturulanlar.append(dict(body or {}))
        yeni = {
            "id": "job-%d" % len(self.olusturulanlar),
            "name": (body or {}).get("name"),
            "reportTypeId": (body or {}).get("reportTypeId"),
            "createTime": "2026-09-12T00:00:00Z",
        }
        self._joblar.append(yeni)
        return _Istek(yeni)

    def reports(self):
        return _Raporlar(self._raporlar)


class _Tipler:
    def __init__(self, tipler):
        self._tipler = tipler

    def list(self, pageToken=None, includeSystemManaged=None):
        return _Istek({"reportTypes": self._tipler})


class SahteServis:
    def __init__(self, tipler=None, joblar=None, raporlar=None, job_liste_hatasi=None):
        self.olusturulanlar = []
        self._tipler = _Tipler(tipler if tipler is not None else [
            {"id": "channel_reach_basic_a1", "name": "Reach basic"},
            {"id": "channel_reach_combined_a1", "name": "Reach combined"},
            {"id": "channel_basic_a2", "name": "Basic"},
        ])
        self._joblar = _Joblar(list(joblar or []), self.olusturulanlar,
                               raporlar, job_liste_hatasi)

    def reportTypes(self):
        return self._tipler

    def jobs(self):
        return self._joblar


# --- 1) İdempotentlik -------------------------------------------------------

def test_kur_sifirdan_iki_job_acar():
    s = SahteServis()
    sonuc = yr.kur(servis=s)
    acilan = sorted(b["reportTypeId"] for b in s.olusturulanlar)
    assert acilan == ["channel_reach_basic_a1", "channel_reach_combined_a1"]
    assert all(sonuc["joblar"][t]["yeni"] for t in acilan)


def test_kur_var_olan_job_icin_IKINCISINI_ACMAZ():
    """Asıl koruma: API ikinci job'ı reddetmiyor, biz engelliyoruz."""
    s = SahteServis(joblar=[
        {"id": "eski-1", "reportTypeId": "channel_reach_basic_a1",
         "name": "fms_channel_reach_basic_a1", "createTime": "2026-09-01T00:00:00Z"},
    ])
    sonuc = yr.kur(servis=s)
    acilan = [b["reportTypeId"] for b in s.olusturulanlar]
    assert "channel_reach_basic_a1" not in acilan, "AYNI TİP İÇİN İKİNCİ JOB AÇILDI"
    assert acilan == ["channel_reach_combined_a1"]
    assert sonuc["joblar"]["channel_reach_basic_a1"]["id"] == "eski-1"
    assert sonuc["joblar"]["channel_reach_basic_a1"]["yeni"] is False


def test_kur_iki_kez_calisinca_yeni_job_acmaz():
    """Gerçek kullanım deseni: script yanlışlıkla iki kez çalıştırılıyor."""
    s = SahteServis()
    yr.kur(servis=s)
    ilk = len(s.olusturulanlar)
    yr.kur(servis=s)
    assert len(s.olusturulanlar) == ilk, "İkinci koşu yeni job açtı (idempotent DEĞİL)"


def test_ayni_kosuda_tekrarlanan_tip_iki_kez_acilmaz():
    """`kur()` içindeki yerel liste güncellenmezse aynı koşuda çift açılırdı."""
    s = SahteServis()
    yr.kur(istenen=("channel_reach_basic_a1", "channel_reach_basic_a1"), servis=s)
    assert len(s.olusturulanlar) == 1


def test_kuru_kosu_hicbir_sey_OLUSTURMAZ():
    s = SahteServis()
    sonuc = yr.kur(servis=s, kuru=True)
    assert s.olusturulanlar == []
    assert sonuc["joblar"]["channel_reach_basic_a1"]["yeni"] is True
    assert sonuc["joblar"]["channel_reach_basic_a1"]["id"] is None


# --- 2) Rapor tipi TAHMİN EDİLMEZ ------------------------------------------

def test_api_sunmayan_tip_icin_job_ACILMAZ():
    """Uydurma/eski bir tip adı sessizce job'a dönüşmemeli."""
    s = SahteServis(tipler=[{"id": "channel_reach_basic_a1", "name": "Reach"}])
    sonuc = yr.kur(servis=s)
    acilan = [b["reportTypeId"] for b in s.olusturulanlar]
    assert acilan == ["channel_reach_basic_a1"]
    assert "channel_reach_combined_a1" in sonuc["atlanan"]
    assert "SUNMUYOR" in sonuc["atlanan"]["channel_reach_combined_a1"]


def test_bos_tip_listesi_JOB_ACMAZ_ve_yukseltir():
    """Boş listeye güvenip devam etmek, tip adını tahmin etmenin ta kendisi."""
    s = SahteServis(tipler=[])
    with pytest.raises(yr.ReportingHatasi) as h:
        yr.kur(servis=s)
    assert s.olusturulanlar == []
    assert "TAHMIN" in str(h.value).upper() or "TAHMİN" in str(h.value).upper()


def test_kullanimdan_kaldirilan_tipe_job_acilmaz():
    s = SahteServis(tipler=[
        {"id": "channel_reach_basic_a1", "name": "Reach",
         "deprecateTime": "2026-12-01T00:00:00Z"},
        {"id": "channel_reach_combined_a1", "name": "Reach combined"},
    ])
    sonuc = yr.kur(servis=s)
    assert [b["reportTypeId"] for b in s.olusturulanlar] == ["channel_reach_combined_a1"]
    assert "channel_reach_basic_a1" in sonuc["atlanan"]


def test_istenen_tipler_hedef_metrikleri_tasiyan_raporlar():
    """B1'in gerekçesi: CTR sadece bu iki raporda var (buyume_kontrol_listesi)."""
    assert yr.ISTENEN_RAPOR_TIPLERI == (
        "channel_reach_basic_a1", "channel_reach_combined_a1")


# --- 3) İzin (scope) hatası SESSİZ KALMAZ ----------------------------------

class _SahteKimlik:
    def __init__(self, scopes):
        self.scopes = scopes
        self.valid = True
        self.expired = False
        self.refresh_token = None


def test_yetersiz_scope_YUKSELTIR_sessizce_gecmez():
    with pytest.raises(yr.ReportingHatasi) as h:
        yr._scope_dogrula(_SahteKimlik([
            "https://www.googleapis.com/auth/youtube.upload"]))
    metin = str(h.value)
    assert "yt-analytics.readonly" in metin
    assert "--auth" in metin


def test_scope_hatasi_token_json_uyarisini_TASIR():
    """CLAUDE.md'nin en pahalı uyarısı mesajın İÇİNDE olmalı: operatör
    'kolay yol' diye token.json'a scope eklerse saatlik hat DURUR."""
    with pytest.raises(yr.ReportingHatasi) as h:
        yr._scope_dogrula(_SahteKimlik([]))
    metin = str(h.value)
    assert "token.json" in metin
    assert "DURUR" in metin


def test_yeterli_scope_sessizce_gecer():
    yr._scope_dogrula(_SahteKimlik([
        "https://www.googleapis.com/auth/yt-analytics.readonly"]))
    yr._scope_dogrula(_SahteKimlik([
        "https://www.googleapis.com/auth/yt-analytics-monetary.readonly"]))


def test_token_dosyasi_yoksa_YUKSELTIR(tmp_path, monkeypatch):
    monkeypatch.setattr(yr, "TOKEN_PATH", str(tmp_path / "yok.json"))
    with pytest.raises(yr.ReportingHatasi) as h:
        yr.kimlik()
    assert "--auth" in str(h.value)


# --- 4) API kapalıyken KONUŞAN hata ---------------------------------------

def test_service_disabled_konusan_mesaja_cevriliyor():
    ham = Exception(
        'YouTube Reporting API has not been used in project 1026223060773 '
        'before or it is disabled. reason: SERVICE_DISABLED')
    s = SahteServis(job_liste_hatasi=ham)
    with pytest.raises(yr.ReportingHatasi) as h:
        yr.joblari_listele(s)
    metin = str(h.value)
    assert "KAPALI" in metin
    assert "ETKINLESTIR" in metin


def test_job_yokken_indir_yukseltir_bos_donmez():
    s = SahteServis(joblar=[])
    with pytest.raises(yr.ReportingHatasi) as h:
        yr.indir(servis=s)
    assert "--kur" in str(h.value)


def test_durum_hicbir_sey_olusturmaz():
    s = SahteServis(joblar=[
        {"id": "j1", "reportTypeId": "channel_reach_basic_a1",
         "name": "fms_x", "createTime": "2026-09-12T00:00:00Z"}])
    d = yr.durum(servis=s)
    assert s.olusturulanlar == []
    assert d["job_sayisi"] == 1
    assert d["joblar"][0]["rapor_sayisi"] == 0


# --- 5) Yapısal muhafızlar -------------------------------------------------

_KAYNAK = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "upload", "youtube_reporting.py")


def _agac():
    with open(_KAYNAK, "r", encoding="utf-8") as f:
        return ast.parse(f.read())


def test_modulde_ciplak_print_YOK_tek_cikis_log():
    """Docstring 'log'a yazılan her metin maskeleyiciden geçiyor' diyor —
    bu bir GARANTİ; `print` eklendiği an yalan olur."""
    agac = _agac()
    printler = [d for d in ast.walk(agac)
                if isinstance(d, ast.Call)
                and isinstance(d.func, ast.Name) and d.func.id == "print"]
    # Tek izinli yer `_log`'un kendisi.
    log_govdesi = [f for f in ast.walk(agac)
                   if isinstance(f, ast.FunctionDef) and f.name == "_log"]
    assert len(log_govdesi) == 1
    icerideki = [d for d in ast.walk(log_govdesi[0])
                 if isinstance(d, ast.Call)
                 and isinstance(d.func, ast.Name) and d.func.id == "print"]
    assert len(printler) == len(icerideki) == 1, (
        "Maskelenmeyen print var: %d" % (len(printler) - len(icerideki)))


def test_yukleme_token_modulu_HIC_IMPORT_EDILMIYOR():
    """`youtube_auth` (yani `upload/token.json`'ın sahibi) buraya girmemeli.

    Metin araması YAPILMIYOR bilerek: modülün docstring'i ve hata mesajları
    o dosyadan UYARI olarak söz ETMEK ZORUNDA (CLAUDE.md'nin en pahalı
    uyarısı). Tehlikeli olan bahsetmek değil, İMPORT etmek."""
    adlar = set()
    for d in ast.walk(_agac()):
        if isinstance(d, ast.Import):
            adlar.update(a.name.split(".")[0] for a in d.names)
        elif isinstance(d, ast.ImportFrom):
            adlar.add((d.module or "").split(".")[0])
    assert "youtube_auth" not in adlar
    assert "youtube_upload" not in adlar
    # Kimlik TEK kaynaktan geliyor: analytics tarafı.
    assert "youtube_analytics" in adlar


def test_scope_listesi_youtube_auth_tan_TURETILMIYOR():
    """Kimlik `analytics_token.json`'dan; yükleme token'ından DEĞİL."""
    import youtube_analytics
    assert yr.TOKEN_PATH.endswith("analytics_token.json")
    # KOPYA DEĞİL, aynı nesne — `uyumluluk.KOKLER` dersi.
    assert yr.TOKEN_PATH is youtube_analytics.TOKEN_PATH


def test_zamanlayici_hattina_BAGLI_DEGIL():
    """Saatlik hat bu modülü çağırmıyor olmalı (CLAUDE.md, ÜÇ SORU / (B))."""
    kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for ad in ("auto_process.py", "dj_famous_process.py", "watch_projects.py"):
        yol = os.path.join(kok, ad)
        if not os.path.isfile(yol):
            continue
        with open(yol, "r", encoding="utf-8") as f:
            assert "youtube_reporting" not in f.read(), (
                "%s bu modülü çağırıyor — kotalı/gecikmeli bir iş saatlik "
                "hatta bağlanmamalı" % ad)
