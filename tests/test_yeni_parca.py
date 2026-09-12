# -*- coding: utf-8 -*-
"""`yeni_parca.py` — üretim akışının 2. adımını kuran yardımcının kilidi.

HER TEST `tmp_path` ALTINDA ÇALIŞIR. Komut `--kok` parametresi aldığı için
gerçek `projects/` ağacına (dakikalık `watch_projects.py`'nin taradığı yer)
HİÇBİR test dosya yazmıyor; son testte bu izolasyonun kendisi de doğrulanıyor.

Testlerin kapattığı arızalar, hepsi bu depoda ÖLÇÜLMÜŞ:
  (a) geçersiz tema -> DURUR, sessizce `hiphop`a DÜŞMEZ,
  (b) var olan proje/sözler dosyasının ÜZERİNE yazmaz,
  (c) slug `stock_art._slugify` ile BİREBİR aynı (ikinci bir slug kuralı
      sessizce ayrışırsa altyazı ve Pexels araması yanlış şarkıya kayar),
  (d) sözler şablonunda "Temiz Sözler" bölümü ZATEN var,
  (e) `--dry-run` hiçbir dosya oluşturmaz,
  (f) üretilen `meta.json` `json.load` ile okunabilir ve `title`/`theme` içerir,
  (g) üretilen dosyalar `validate_project`/`uyumluluk` kapılarını BOZMUYOR —
      ses olmadan render'a girilmiyor,
  (h) satır sonları diskteki mevcut dosyalarla aynı (meta.json LF, sözler CRLF).
"""

import io
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import stock_art
import validate_project
import yeni_parca

LF = chr(10)
CRLF = chr(13) + chr(10)


# --------------------------------------------------------------------------
# yardımcılar
# --------------------------------------------------------------------------
def _kok_kur(tmp_path, son_durum: str = None) -> str:
    """tmp_path içinde minik bir "repo kökü": projects/ + ses_ve_tarz_takibi.md."""
    kok = str(tmp_path)
    os.makedirs(os.path.join(kok, "projects"), exist_ok=True)
    if son_durum is None:
        son_durum = (
            "**SON DURUM (2026-09-12) — sıradaki üretim SEÇİLDİ: `Vardiya`**" + LF
            + "(rock, 78 BPM, kadın, düet değil)." + LF + LF
            + "**Sıradaki (Vardiya'dan SONRA):** kadın vokal üst üste ikiye "
              "çıkmasın; erkek ya da düet tarafına dönülebilir." + LF + LF
            + "Yeni bir şarkı prompt'u yazmadan önce bu listeye bak —" + LF)
    with io.open(os.path.join(kok, "ses_ve_tarz_takibi.md"), "w",
                 encoding="utf-8", newline="") as f:
        f.write("# Ses ve tarz takibi" + LF + LF + son_durum)
    return kok


def _calistir(kok, baslik, tema, *ek):
    argv = [baslik, "--tema", tema, "--kok", kok] + list(ek)
    return yeni_parca.main(argv)


def _dosyalar(kok):
    """kok altındaki TÜM dosyaların göreli yolları — "hiç yazmadı" kanıtı için."""
    bulunan = []
    for dizin, _, adlar in os.walk(kok):
        for ad in adlar:
            bulunan.append(os.path.relpath(os.path.join(dizin, ad), kok))
    return sorted(bulunan)


# --------------------------------------------------------------------------
# (a) tema doğrulaması — sessiz varsayılana DÜŞMEK YASAK
# --------------------------------------------------------------------------
def test_gecersiz_tema_durduruyor_ve_hiphopa_dusmuyor(tmp_path, capsys):
    kok = _kok_kur(tmp_path)
    once = _dosyalar(kok)

    kod = _calistir(kok, "Hatali Tema", "rockk")

    assert kod != 0, "geçersiz tema sıfır çıkış koduyla geçmemeli"
    cikti = capsys.readouterr()
    hepsi = cikti.out + cikti.err
    # Geçerli listeyi YAZMALI (operatör tahmin etmek zorunda kalmasın).
    for t in config.THEMES:
        assert t in hepsi, "geçerli tema listesi basılmalı: %s" % t
    # Ve HİÇBİR dosya oluşmamalı — en kritik kısım: sessizce DEFAULT_THEME ile
    # bir proje kurulsaydı arıza tam da kaçınmaya çalıştığımız arıza olurdu.
    assert _dosyalar(kok) == once


def test_gecersiz_tema_dosya_yazmiyor_defaulta_dusmuyor(tmp_path):
    kok = _kok_kur(tmp_path)
    _calistir(kok, "Hatali Tema", "arabeskk")
    assert not os.path.exists(os.path.join(kok, "projects", "Hatali Tema"))
    assert not os.path.exists(os.path.join(kok, "hatali_tema_sozler.md"))
    # DEFAULT_THEME'li bir meta.json hiçbir yerde oluşmamış olmalı.
    assert config.DEFAULT_THEME == "hiphop"      # gerekçenin dayandığı varsayım
    assert _dosyalar(kok) == ["ses_ve_tarz_takibi.md"]


def test_config_themes_disinda_tema_kabul_edilmiyor(tmp_path):
    kok = _kok_kur(tmp_path)
    for tema in ("", "HIPHOP", "pop ", "tr-pop", "hiphopp"):
        assert _calistir(kok, "X Y", tema) != 0, "%r kabul edilmemeli" % tema
    # Geçerli olanların HEPSİ kabul edilmeli (liste config'ten geliyor).
    for tema in config.THEMES:
        plan = yeni_parca.plan_yap("X Y", tema, kok)
        assert plan["stil"]


# --------------------------------------------------------------------------
# (b) çakışma — var olanın ÜZERİNE yazmıyor
# --------------------------------------------------------------------------
def test_var_olan_projenin_uzerine_yazmiyor(tmp_path):
    kok = _kok_kur(tmp_path)
    proje = os.path.join(kok, "projects", "Vardiya")
    os.makedirs(proje)
    with io.open(os.path.join(proje, "meta.json"), "w", encoding="utf-8",
                 newline="") as f:
        f.write('{"title": "Vardiya", "theme": "arabesk"}')

    kod = _calistir(kok, "Vardiya", "rock")

    assert kod != 0
    with io.open(os.path.join(proje, "meta.json"), encoding="utf-8") as f:
        korunan = json.load(f)
    assert korunan["theme"] == "arabesk", "mevcut meta.json DEĞİŞMEMELİ"
    assert not os.path.exists(os.path.join(kok, "vardiya_sozler.md"))


def test_var_olan_sozler_dosyasinin_uzerine_yazmiyor(tmp_path):
    kok = _kok_kur(tmp_path)
    sozler = os.path.join(kok, "vardiya_sozler.md")
    with io.open(sozler, "w", encoding="utf-8", newline="") as f:
        f.write("# ELDE YAZILMIŞ, KAYBOLMAMALI")

    kod = _calistir(kok, "Vardiya", "rock")

    assert kod != 0
    with io.open(sozler, encoding="utf-8") as f:
        assert f.read() == "# ELDE YAZILMIŞ, KAYBOLMAMALI"
    # Proje klasörü de AÇILMAMALI: çakışma kontrolü yazmadan ÖNCE.
    assert not os.path.exists(os.path.join(kok, "projects", "Vardiya"))


# --------------------------------------------------------------------------
# (c) slug — stock_art._slugify ile BİREBİR aynı
# --------------------------------------------------------------------------
@pytest.mark.parametrize("baslik", [
    "Vardiya", "Yürek Yarası", "Beton Krallığı", "Bir Bahar Daha",
    "Sokaklar Beni Tanır", "Küllerimden Geç", "Şık İşçi", "Gece  Sürüşü",
])
def test_slug_stock_art_ile_ayni(tmp_path, baslik):
    kok = _kok_kur(tmp_path)
    plan = yeni_parca.plan_yap(baslik, "pop", kok)
    beklenen = stock_art._slugify(baslik)
    assert plan["slug"] == beklenen
    assert os.path.basename(plan["sozler_yolu"]) == "%s_sozler.md" % beklenen


def test_sozler_dosyasi_repo_KOKUNDE_projects_altinda_degil(tmp_path):
    kok = _kok_kur(tmp_path)
    assert _calistir(kok, "Vardiya", "rock") == 0
    assert os.path.isfile(os.path.join(kok, "vardiya_sozler.md"))
    assert not os.path.exists(
        os.path.join(kok, "projects", "Vardiya", "vardiya_sozler.md"))


# --------------------------------------------------------------------------
# (d) "Temiz Sözler" bölümü şablonda ZATEN var
# --------------------------------------------------------------------------
def test_sozler_sablonunda_temiz_sozler_bolumu_var(tmp_path):
    kok = _kok_kur(tmp_path)
    assert _calistir(kok, "Vardiya", "rock") == 0
    with io.open(os.path.join(kok, "vardiya_sozler.md"), encoding="utf-8") as f:
        metin = f.read()
    assert "## Temiz Sözler" in metin
    # Üç ZORUNLU bölümün üçü de (haftalik_is_akisi.md §2, 3. adım).
    assert "## Stil Etiketi" in metin
    assert "## Sözler" in metin
    # Etiketli bölüm gerçekten Suno bölüm etiketleri içeriyor...
    assert "[Intro]" in metin and "[Chorus]" in metin and "[Outro]" in metin
    # ...ve "Temiz Sözler" bölümünde ETİKET YOK (etiketsiz kopya).
    temiz = metin.split("## Temiz Sözler", 1)[1]
    for etiket in ("[Intro]", "[Verse 1]", "[Chorus]", "[Outro]"):
        assert etiket not in temiz, "%s Temiz Sözler bölümüne sızmış" % etiket


def test_temiz_sozler_etiketli_bolumle_ayni_satir_listesi(tmp_path):
    """caption_align 0,25 eşleşme eşiğiyle okuyor — iki bölüm sapmamalı."""
    kok = _kok_kur(tmp_path)
    assert _calistir(kok, "Vardiya", "rock") == 0
    with io.open(os.path.join(kok, "vardiya_sozler.md"), encoding="utf-8") as f:
        metin = f.read()
    bloklar = metin.split("```")
    etiketli = [s for s in bloklar if "[Intro]" in s][0].strip().splitlines()
    temiz = [s for s in bloklar
             if s.strip() and "[Intro]" not in s and "DOLDUR: 2 satır" in s]
    assert temiz, "Temiz Sözler kod bloğu bulunamadı"
    temiz_satir = temiz[-1].strip().splitlines()
    etiketsiz = [s for s in etiketli if not s.startswith("[")]
    # Baştaki/sondaki boşlukların dışında BİREBİR aynı satır listesi.
    assert [s for s in etiketsiz if s.strip()] == [s for s in temiz_satir
                                                   if s.strip()]


# --------------------------------------------------------------------------
# (e) --dry-run HİÇBİR dosya oluşturmuyor
# --------------------------------------------------------------------------
def test_dry_run_hicbir_dosya_olusturmuyor(tmp_path, capsys):
    kok = _kok_kur(tmp_path)
    once = _dosyalar(kok)

    kod = _calistir(kok, "Deneme Parca", "rock", "--dry-run")

    assert kod == 0
    assert _dosyalar(kok) == once, "kuru koşu diske YAZMAMALI"
    assert not os.path.exists(os.path.join(kok, "projects", "Deneme Parca"))
    cikti = capsys.readouterr().out
    # Ne yapacağını yine de ANLATMALI (yoksa kuru koşu işe yaramaz).
    assert "deneme_parca_sozler.md" in cikti
    assert "meta.json" in cikti
    assert "rock" in cikti


def test_dry_run_varsayilan_DEGIL(tmp_path):
    """Varsayılan YAZMAK. Kuru koşu varsayılan olsaydı, kaldırmaya çalıştığımız
    'unutulan ikinci adım' sınıfı geri gelirdi (bkz. yeni_parca.py, --dry-run
    yardım metni)."""
    kok = _kok_kur(tmp_path)
    assert _calistir(kok, "Vardiya", "rock") == 0
    assert os.path.isfile(os.path.join(kok, "projects", "Vardiya", "meta.json"))
    assert os.path.isfile(os.path.join(kok, "vardiya_sozler.md"))


# --------------------------------------------------------------------------
# (f) meta.json okunabilir + title/theme
# --------------------------------------------------------------------------
def test_meta_json_okunabilir_ve_title_theme_iceriyor(tmp_path):
    kok = _kok_kur(tmp_path)
    assert _calistir(kok, "Beton Krallığı", "hiphop") == 0
    yol = os.path.join(kok, "projects", "Beton Krallığı", "meta.json")
    with io.open(yol, encoding="utf-8") as f:
        meta = json.load(f)
    assert meta["title"] == "Beton Krallığı"
    assert meta["theme"] == "hiphop"
    assert meta["theme"] in config.THEMES
    # custom_hooks/custom_questions BİLEREK YOK: ikisi de sözlerden türetiliyor
    # ve yer tutucu metin `social_text.build_caption()` ile YAYINLANIRDI.
    assert "custom_hooks" not in meta
    assert "custom_questions" not in meta
    # Alanın yokluğu güvenli: `meta.get(...) or config.HOOK_LINES` fallback'i.
    assert getattr(config, "HOOK_LINES", None), "genel havuz duruyor olmalı"


# --------------------------------------------------------------------------
# (g) üretilen dosyalar kapıları BOZMUYOR — ses olmadan render'a girilmiyor
# --------------------------------------------------------------------------
def test_uretilen_proje_render_kapisindan_GECMIYOR_ses_yokken(tmp_path):
    kok = _kok_kur(tmp_path)
    assert _calistir(kok, "Vardiya", "rock") == 0
    proje = os.path.join(kok, "projects", "Vardiya")

    hatalar, uyarilar = validate_project.validate(proje)

    # Ses YOK -> HATA var -> render.py bu projeye hiç girmez. (Komutun canlı
    # sistemde güvenli olmasının dayanağı tam olarak bu.)
    assert any("audio" in h for h in hatalar), hatalar
    # Ve HATALARIN TAMAMI ses eksikliğinden olmalı: meta.json/theme yüzünden
    # EK bir hata çıkmamalı, yoksa ses gelince render yine durur.
    assert not [h for h in hatalar if "audio" not in h], hatalar
    assert not [u for u in uyarilar if "meta.json" in u], uyarilar


def test_uretilen_meta_theme_validate_tarafindan_taniniyor(tmp_path):
    """theme yazım hatası render'ı DURDURUR — komut geçerli tema yazdığı için
    bu kapı üretilen dosyada TETİKLENMEMELİ."""
    kok = _kok_kur(tmp_path)
    for tema in ("pop", "rock", "elektronik", "akustik", "hiphop", "arabesk"):
        ad = "Proje %s" % tema
        assert _calistir(kok, ad, tema) == 0
        proje = os.path.join(kok, "projects", ad)
        hatalar, _ = validate_project.validate(proje)
        assert not [h for h in hatalar if "theme" in h], (tema, hatalar)


def test_uyumluluk_meta_okuyabiliyor(tmp_path):
    """`uyumluluk._meta()` bozuk meta.json'u UYARI olarak raporluyor — üretilen
    dosya o dala HİÇ düşmemeli."""
    uyumluluk = pytest.importorskip("uyumluluk")
    kok = _kok_kur(tmp_path)
    assert _calistir(kok, "Vardiya", "rock") == 0
    proje = os.path.join(kok, "projects", "Vardiya")
    meta = uyumluluk._meta(proje)          # DurumBozuk fırlatırsa test düşer
    assert meta["theme"] == "rock"


# --------------------------------------------------------------------------
# (h) satır sonları — mevcut dosyalarla AYNI
# --------------------------------------------------------------------------
def test_satir_sonlari_mevcutlarla_ayni(tmp_path):
    """ÖLÇÜLDÜ (diskteki dosyalar sayıldı): meta.json LF, *_sozler.md CRLF."""
    kok = _kok_kur(tmp_path)
    assert _calistir(kok, "Vardiya", "rock") == 0

    with open(os.path.join(kok, "projects", "Vardiya", "meta.json"), "rb") as f:
        meta_ham = f.read()
    assert CRLF.encode() not in meta_ham, "meta.json LF olmalı"
    assert meta_ham.endswith(LF.encode())

    with open(os.path.join(kok, "vardiya_sozler.md"), "rb") as f:
        sozler_ham = f.read()
    assert CRLF.encode() in sozler_ham, "sözler dosyası CRLF olmalı"
    # ÇIPLAK LF KALMAMALI: karışık satır sonu, diff'i ve caption_align'ın
    # satır karşılaştırmasını sessizce bozar.
    assert sozler_ham.replace(CRLF.encode(), b"").count(LF.encode()) == 0
    assert sozler_ham.endswith(CRLF.encode())


def test_uretilen_dosyalar_utf8_ve_kontrol_karakteri_yok(tmp_path):
    kok = _kok_kur(tmp_path)
    assert _calistir(kok, "Yürek Yarası 2", "arabesk") == 0
    for yol in (os.path.join(kok, "projects", "Yürek Yarası 2", "meta.json"),
                os.path.join(kok, "yurek_yarasi_2_sozler.md")):
        with open(yol, "rb") as f:
            ham = f.read()
        metin = ham.decode("utf-8")        # bozuk UTF-8 ise burada patlar
        kacak = [c for c in metin if ord(c) < 32 and c not in (LF, chr(13), "\t")]
        assert not kacak, (yol, kacak[:5])


# --------------------------------------------------------------------------
# stil etiketi taslağı
# --------------------------------------------------------------------------
@pytest.mark.parametrize("tema,beklenen", [
    ("pop", yeni_parca.KAPANIS_YUMUSAK),
    ("akustik", yeni_parca.KAPANIS_YUMUSAK),
    ("arabesk", yeni_parca.KAPANIS_YUMUSAK),
    ("rock", yeni_parca.KAPANIS_SERT),
    ("hiphop", yeni_parca.KAPANIS_SERT),
    ("elektronik", yeni_parca.KAPANIS_SERT),
])
def test_kapanis_tanimi_outro_kuralina_uyuyor(tema, beklenen):
    """suno_prompt_hazirlik.md, 'Kapanış (Outro) kuralı' — SABİT eşleme."""
    assert yeni_parca.kapanis_tanimi(tema) == beklenen
    stil = yeni_parca.stil_etiketi_taslagi(tema, {"male"})
    assert stil.endswith(beklenen), "kapanış tanımı etiketin SONUNDA olmalı"


def test_stil_etiketi_config_themes_bilgisinden_turuyor(tmp_path):
    kok = _kok_kur(tmp_path)
    plan = yeni_parca.plan_yap("Vardiya", "rock", kok, bpm="78")
    stil = plan["stil"]
    t = config.THEMES["rock"]
    assert t["art_mood"] in stil, "mood config.THEMES'ten gelmeli"
    assert "Turkish" in stil, "dil config.THEMES['language']'ten gelmeli"
    assert "78 BPM" in stil
    assert stil.endswith(yeni_parca.KAPANIS_SERT)


def test_vokal_onerisi_son_durumdan_turuyor(tmp_path):
    kok = _kok_kur(tmp_path)          # varsayılan SON DURUM: kadın YASAK
    plan = yeni_parca.plan_yap("Vardiya", "rock", kok)
    assert "male" in plan["vokal_oneri"]
    assert "female" in plan["vokal_kacin"]
    assert "male vocals" in plan["stil"]
    assert "female" not in plan["stil"]


def test_vokal_onerisi_ters_yonde_de_calisiyor(tmp_path):
    kok = _kok_kur(tmp_path, son_durum=(
        "**SON DURUM (2026-01-01)** bir şeyler." + LF + LF
        + "**Sıradaki:** erkek vokal art arda tekrarlanmasın; kadın tarafına "
          "dönülmeli." + LF))
    plan = yeni_parca.plan_yap("Test Parca", "pop", kok)
    assert "female" in plan["vokal_oneri"]
    assert "male" in plan["vokal_kacin"]
    assert "female vocals" in plan["stil"]


def test_son_durum_okunamazsa_yer_tutucu_basiliyor_uydurmuyor(tmp_path):
    """Dosya yoksa SESSİZCE bir vokal seçmek, tam olarak kaçındığımız arıza."""
    kok = str(tmp_path)
    os.makedirs(os.path.join(kok, "projects"), exist_ok=True)
    plan = yeni_parca.plan_yap("Test Parca", "rock", kok)
    assert plan["vokal_oneri"] == set()
    assert "<VOKAL:" in plan["stil"]
    assert "male vocals" not in plan["stil"]
    assert "female vocals" not in plan["stil"]


def test_arabesk_duet_zorunlulugunu_hatirlatiyor(tmp_path):
    """CLAUDE.md: `arabesk` teması SABİT olarak düet formatında üretiliyor."""
    kok = _kok_kur(tmp_path)
    assert _calistir(kok, "Ayrilik Sofrasi", "arabesk") == 0
    with io.open(os.path.join(kok, "ayrilik_sofrasi_sozler.md"),
                 encoding="utf-8") as f:
        metin = f.read()
    assert "DÜET ZORUNLU" in metin
    plan = yeni_parca.plan_yap("Ayrilik Sofrasi", "arabesk", kok)
    assert "DÜET" in plan["stil"] or "duet" in plan["stil"]


# --------------------------------------------------------------------------
# izolasyon — gerçek projects/ ağacına dokunulmuyor
# --------------------------------------------------------------------------
def test_gercek_projects_agacina_yazilmiyor(tmp_path):
    """Bu test paketinin KENDİ emniyeti: `--kok` verilmişse gerçek repo kökünde
    hiçbir şey oluşmamalı (canlı `watch_projects.py` orayı tarıyor)."""
    gercek = yeni_parca.REPO
    once = set(os.listdir(os.path.join(gercek, "projects")))
    once_kok = set(os.listdir(gercek))

    kok = _kok_kur(tmp_path)
    assert _calistir(kok, "Izolasyon Testi", "rock") == 0

    assert set(os.listdir(os.path.join(gercek, "projects"))) == once
    assert set(os.listdir(gercek)) == once_kok
