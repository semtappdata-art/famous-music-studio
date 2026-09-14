# -*- coding: utf-8 -*-
"""YouTube UZUN FORMAT açıklamalarının şarkılar arası ÖZGÜNLÜĞÜ.

NEDEN BU TESTLER VAR (2026-09-12, özgünlük denetimi):
`youtube_upload.build_snippet()` ile 18+ şarkının açıklaması GERÇEKTEN
üretilip ölçüldü (ağa çıkmadan, fonksiyonu çağırarak):

    açıklama başına ortak kelime payı .......... %62,5
    sekiz dolu satırın DÖRDÜ ................... tüm videolarda BİREBİR aynı
    ikili benzerlik ortalaması ................. 0,79  (en yüksek çift 0,97)
    10'lu keşfet hashtag bloğu ................. 19/19 videoda aynı sırayla
    benzersiz hook ............................. 19 şarkıda 10 tane

Aynı ölçüm KISA format caption'da (`social_text.build_caption`, aynı
deterministik seçim mekanizması): ortak satır 0, ortalama 0,17. Yani sorun
mekanizmada değil — uzun format havuzları KULLANMIYORDU.

Bunun neden kritik olduğu CLAUDE.md'de yazılı: kanalın en büyük tekil riski
telif değil, "toplu üretilmiş / özgün olmayan AI içerik" politikası. Her
videonun altında neredeyse aynı metin, o desenin en kolay görülen imzası.

DÜZELTMEDEN SONRA (aynı ölçüm, aynı katalog): ortak kelime payı %29,9;
birebir aynı satır yalnızca 3 (üçü de link bloğu, BİLEREK sabit); ikili
benzerlik ortalaması 0,46; hashtag bloğu 18/19 farklı; hook 19/19 benzersiz.

Testler DAVRANIŞI çiviliyor, sayıyı değil: eşikler ölçülen değerlerin
üstünde/altında geniş bir payla duruyor ki havuzlara satır eklemek testi
düşürmesin — ama mekanizmanın biri (custom_hooks okuma, FOLLOW_LINES havuzu,
pick_subset'li hashtag, sözlerden alıntı) sessizce geri alınırsa düşsün.
"""

import itertools
import json
import os
import sys
import difflib

import pytest

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _KOK)
sys.path.insert(0, os.path.join(_KOK, "upload"))

import config  # noqa: E402
import social_text  # noqa: E402
from youtube_upload import build_snippet, load_meta  # noqa: E402

_PROJE_KOK = os.path.join(_KOK, "projects")

# Açıklamalarda ASLA görünmemesi gereken AI-vurgulu ibareler (CLAUDE.md,
# kullanıcı kararı 2026-09-05). ZORUNLU AI beyanı bundan AYRI ve dokunulmadı
# (containsSyntheticMedia bayrağı, TikTok uygulama-içi etiket hatırlatması) —
# burada aranan sadece marka/keşfet amaçlı "AI ile yapıldı" vurgusu.
AI_VURGULU = ("aimusic", "sunoai", "yapayzeka", "yapay zeka", "#ai",
              "aigenerated", "ai music", "aicover")


def _katalog_metalari():
    """projects/ altındaki GERÇEK meta.json'lar — fikstür uydurmuyoruz.

    Ölçümün anlamı tam olarak burada: açıklamaların birbirine benzeyip
    benzemediği ancak GERÇEK katalogda görülür, iki uydurma şarkıda değil.
    """
    if not os.path.isdir(_PROJE_KOK):
        return []
    cikti = []
    for ad in sorted(os.listdir(_PROJE_KOK)):
        yol = os.path.join(_PROJE_KOK, ad)
        if not os.path.isdir(yol):
            continue
        meta = load_meta(yol)
        if meta.get("title"):
            cikti.append((ad, meta))
    return cikti


def _aciklamalar():
    return {ad: build_snippet(meta)["description"] for ad, meta in _katalog_metalari()}


def _ikili_benzerlik(metinler: dict):
    adlar = list(metinler)
    return [(difflib.SequenceMatcher(None, metinler[a], metinler[b]).ratio(), a, b)
            for a, b in itertools.combinations(adlar, 2)]


@pytest.fixture(scope="module")
def aciklamalar():
    d = _aciklamalar()
    if len(d) < 5:
        pytest.skip("katalogda ölçüme yetecek kadar proje yok")
    return d


# --------------------------------------------------------------------------
# (a) DETERMİNİSTİK: aynı şarkı HER ZAMAN aynı açıklamayı üretir.
# --------------------------------------------------------------------------

def test_ayni_sarki_her_zaman_ayni_aciklamayi_uretir():
    """Arşiv tutarlılığı (CLAUDE.md kararı): bir projeyi yeniden işlemek
    yayındaki açıklamadan FARKLI bir metin üretmemeli. Rastgelelik YOK."""
    metalar = _katalog_metalari()
    if not metalar:
        pytest.skip("projects/ boş")
    for ad, meta in metalar:
        ilk = build_snippet(meta)["description"]
        for _ in range(5):
            assert build_snippet(meta)["description"] == ilk, \
                f"{ad}: aynı meta iki farklı açıklama üretti (rastgelelik sızmış)"


def test_sozlerden_alinti_deterministik():
    """Alıntı seçimi de deterministik — sözler dosyası değişmedikçe aynı beyit."""
    metalar = _katalog_metalari()
    if not metalar:
        pytest.skip("projects/ boş")
    for ad, meta in metalar:
        ilk = social_text.sozlerden_alinti(meta)
        for _ in range(3):
            assert social_text.sozlerden_alinti(meta) == ilk, f"{ad}: alıntı oynuyor"


# --------------------------------------------------------------------------
# (b) ÇEŞİTLİLİK: farklı şarkılar farklı açıklama üretir.
# --------------------------------------------------------------------------

def test_ikili_benzerlik_esigin_altinda(aciklamalar):
    """Düzeltmeden ÖNCE: ortalama 0,79 / en yüksek çift 0,97.
    SONRA: ortalama 0,46 / en yüksek 0,63. Eşikler arada."""
    skorlar = _ikili_benzerlik(aciklamalar)
    ortalama = sum(s for s, _a, _b in skorlar) / len(skorlar)
    en_yuksek, a, b = max(skorlar)
    assert ortalama < 0.60, (
        "açıklamalar şarkılar arasında fazla benziyor (ortalama %.3f) — "
        "havuzlardan biri devre dışı kalmış olabilir" % ortalama)
    assert en_yuksek < 0.80, (
        "en benzer çift %.3f: %s | %s" % (en_yuksek, a, b))


def test_her_aciklamada_birebir_ayni_satir_SADECE_marka_bloku(aciklamalar):
    """TÜM videolarda birebir tekrar eden satırlar yalnızca BİLEREK sabit
    tutulanlar olmalı (link bloğu). Dördüncü bir satır listeye girerse
    (ör. yine hardcoded bir takip cümlesi) bu test düşer."""
    kumeler = [set(s for s in v.split("\n") if s.strip()) for v in aciklamalar.values()]
    ortak = set.intersection(*kumeler)
    links = config.SOCIAL_LINKS
    beklenen = {
        f"📷 Instagram: {links['instagram']}",
        f"🎵 TikTok: {links['tiktok']}",
        f"🌐 Website: {links['website']}",
    }
    assert ortak == beklenen, (
        "her açıklamada tekrar eden satır kümesi beklenenden farklı:\n"
        "  fazladan: %s\n  eksik: %s" % (sorted(ortak - beklenen), sorted(beklenen - ortak)))


def test_hook_satiri_sarkiya_gore_degisiyor(aciklamalar):
    """İlk satır (hook). ÖNCE 19 şarkıda 10 benzersiz hook vardı, çünkü uzun
    format `meta["custom_hooks"]`'u (şarkının KENDİ sözlerinden türetilmiş
    satırlar) hiç okumuyordu — build_caption okuyor."""
    ilkler = [v.split("\n")[0] for v in aciklamalar.values()]
    assert len(set(ilkler)) >= int(len(ilkler) * 0.9), \
        "hook satırı yeterince çeşitlenmiyor: %d/%d benzersiz" % (len(set(ilkler)), len(ilkler))


def test_kesfet_hashtag_bloku_sarkiya_gore_secilir(aciklamalar):
    """ÖNCE: `DISCOVERY_HASHTAGS` havuzunun TAMAMI, her videoda aynı sırayla.
    SONRA: build_caption ile aynı `pick_subset` — şarkıya göre alt küme."""
    son_satirlar = [v.strip().split("\n")[-1] for v in aciklamalar.values()]
    assert len(set(son_satirlar)) >= int(len(son_satirlar) * 0.8), \
        "hashtag bloğu çeşitlenmiyor: %d/%d benzersiz" % (
            len(set(son_satirlar)), len(son_satirlar))

    havuz = set(config.DISCOVERY_HASHTAGS)
    for ad, metin in aciklamalar.items():
        if social_text.resolve_language(dict(_dict_of(ad))) == "en":
            continue
        son = metin.strip().split("\n")[-1].split()
        kullanilan = [h for h in son if h in havuz]
        assert len(kullanilan) <= config.DISCOVERY_HASHTAG_COUNT, (
            "%s: keşfet hashtag'lerinin tamamı basılmış (%d tane) — "
            "pick_subset devre dışı kalmış" % (ad, len(kullanilan)))


def _dict_of(ad):
    return load_meta(os.path.join(_PROJE_KOK, ad))


# --------------------------------------------------------------------------
# (c) SABİT KALMASI GEREKENLER hâlâ HER açıklamada var.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("parca", [
    "Famous Music Studio",
    "https://instagram.com/famous_music_studio",
    "https://www.tiktok.com/@famousmusicstudio",
    "https://famousmusicstudio.com",
])
def test_marka_ve_link_bloku_her_aciklamada_var(aciklamalar, parca):
    """Çeşitlendirme marka/link bloğunu YEMEMELİ: bu satırların işlevi tam da
    tanınmak ve her videodan aynı yere götürmek. (Dış link YASAĞI
    Instagram/TikTok CAPTION'ı için geçerli — YouTube açıklaması farklı.)"""
    for ad, metin in aciklamalar.items():
        assert parca in metin, f"{ad}: '{parca}' açıklamadan düşmüş"


def test_baslik_ve_marka_satiri_yerinde(aciklamalar):
    for ad, meta in _katalog_metalari():
        if ad not in aciklamalar:
            continue
        assert f"{meta['title']} | {config.STATIC_LABEL_TEXT}" in aciklamalar[ad]


# --------------------------------------------------------------------------
# (d) AI-vurgulu ibare hiçbir çıktıda yok.
# --------------------------------------------------------------------------

def test_hicbir_aciklamada_ai_vurgulu_ibare_yok(aciklamalar):
    for ad, metin in aciklamalar.items():
        duz = metin.lower().replace("ı", "i")
        for yasak in AI_VURGULU:
            assert yasak not in duz, f"{ad}: yasaklı AI-vurgulu ibare '{yasak}'"


def test_havuzlarda_ai_vurgulu_ibare_yok():
    """Açıklamaya giren HER havuz taranıyor — bugün seçilmeyen bir satır
    yarın başka bir başlıkta seçilir."""
    havuzlar = (config.HOOK_LINES + config.HOOK_LINES_EN
                + config.ENGAGEMENT_QUESTIONS + config.ENGAGEMENT_QUESTIONS_EN
                + config.FOLLOW_LINES + config.FOLLOW_LINES_EN
                + config.BRAND_HASHTAGS
                + config.DISCOVERY_HASHTAGS + config.DISCOVERY_HASHTAGS_EN)
    for satir in havuzlar:
        duz = satir.lower().replace("ı", "i")
        for yasak in AI_VURGULU:
            assert yasak not in duz, f"havuzda yasaklı ibare: {satir!r}"


# --------------------------------------------------------------------------
# (e) `[Verse]` etiketi açıklamaya SIZMIYOR.
# --------------------------------------------------------------------------

def test_koseli_parantez_etiketi_aciklamaya_sizmiyor(aciklamalar):
    """CLAUDE.md kararı: `[Verse 1]`/`[Chorus]` gibi Suno etiketleri
    açıklamaya kopyalanınca amatör görünüyordu; "## Temiz Sözler" bölümü tam
    bunun için var. Alıntı O bölümden geliyor, ama süzgeç yine de burada
    çivileniyor — söz dosyaları ELLE yazılıyor ve etiket unutulabilir."""
    for ad, metin in aciklamalar.items():
        assert "[" not in metin and "]" not in metin, \
            f"{ad}: açıklamada köşeli parantez var (etiket sızıntısı?)"


def test_etiketli_soz_dosyasindan_alinti_uretilmez(tmp_path, monkeypatch):
    """Doğrudan mekanizma testi: "Temiz Sözler" bölümüne köşeli parantezli bir
    satır sızsa bile o satır alıntı olarak SEÇİLMEZ."""
    md = tmp_path / "sahte_sarki_sozler.md"
    md.write_text(
        "# Sahte Şarkı\n\n## Temiz Sözler\n\n```\n"
        "[Verse 1] Bu satir etiketli ve secilmemeli\n"
        "Gecenin ortasinda bir isik yandi\n"
        "[Chorus] Bu da etiketli, secilmemeli\n"
        "Ve sabaha kadar hic sonmedi durdu\n"
        "```\n", encoding="utf-8")
    monkeypatch.setattr(social_text, "dogrulanmis_sozler_yolu", lambda t: str(md))
    alinti = social_text.sozlerden_alinti({"title": "Sahte Şarkı"})
    assert alinti, "alıntı hiç üretilmedi"
    assert "[" not in alinti and "]" not in alinti
    assert "Gecenin ortasinda" in alinti


def test_duet_konusmaci_isareti_alintiya_girmez(tmp_path, monkeypatch):
    """Arabesk düetlerde satırlar "(Kadın)"/"(Erkek)"/"(İkisi)" ile başlıyor —
    `[Verse - Kadın]` etiketinin parantezli hâli. Açıklamaya girmemeli."""
    md = tmp_path / "duet_sozler.md"
    md.write_text(
        "# Duet\n\n## Temiz Sözler\n\n```\n"
        "(Kadın) Bir yara actin, kapanmadi hic\n"
        "(Erkek) Biliyorum, ben de kaniyorum icimde\n"
        "```\n", encoding="utf-8")
    monkeypatch.setattr(social_text, "dogrulanmis_sozler_yolu", lambda t: str(md))
    alinti = social_text.sozlerden_alinti({"title": "Duet"})
    assert alinti
    assert "(Kadın)" not in alinti and "(Erkek)" not in alinti
    assert "Bir yara actin" in alinti


# --------------------------------------------------------------------------
# Sözler alıntısı — kaynak ve güvenlik kapıları.
# --------------------------------------------------------------------------

def test_alinti_gercekten_sarkinin_kendi_sozunden(aciklamalar):
    """Alıntı UYDURULMUYOR: açıklamaya giren metin, o şarkının kendi
    `*_sozler.md` dosyasının "## Temiz Sözler" bölümünde GERÇEKTEN var."""
    import caption_align
    bulunan = 0
    for ad, meta in _katalog_metalari():
        alinti = social_text.sozlerden_alinti(meta)
        if not alinti:
            continue
        bulunan += 1
        yol = social_text.dogrulanmis_sozler_yolu(meta["title"])
        temiz = caption_align.extract_clean_lyrics(
            open(yol, "r", encoding="utf-8").read())
        for parca in alinti.strip("“”").split(" / "):
            # Konuşmacı işareti kırpıldığı için satır birebir değil, İÇERİLİYOR.
            assert parca in temiz, f"{ad}: '{parca}' sözlerde yok"
        assert alinti in aciklamalar[ad], f"{ad}: alıntı açıklamaya girmemiş"
    assert bulunan >= 5, "katalogda hiç alıntı üretilmedi — mekanizma ölü olabilir"


def test_soz_dosyasi_yoksa_aciklama_yine_de_kuruluyor():
    """Otomasyon ASLA durmaz: sözler dosyası bulunamayan bir başlıkta alıntı
    boş döner ve açıklama eskisi gibi üretilir."""
    meta = {"title": "Hiç Var Olmamış Bir Şarkı Zzz", "theme": "pop"}
    assert social_text.sozlerden_alinti(meta) == ""
    snippet = build_snippet(meta)
    assert config.STATIC_LABEL_TEXT in snippet["description"]
    assert meta["title"] in snippet["description"]


def test_yanlis_sarkinin_sozleri_alinmaz():
    """`stock_art.find_lyrics_file()` BULANIK eşleşiyor; burada bedeli başka
    bir şarkının sözlerini yayına yazmak. İkinci süzgeç (slug benzerliği)
    "Neon"/"Son"/"Bu Gece" gibi kısa başlıkları reddetmeli."""
    for kisa in ("Neon", "Son", "Bu Gece", "Sokaklar"):
        assert social_text.dogrulanmis_sozler_yolu(kisa) is None, \
            f"'{kisa}' başlığı yanlış bir sözler dosyasına eşlendi"


def test_derlemeye_soz_alintisi_konmaz():
    """Derlemenin KENDİ sözü yok; 13 ayrı şarkının sözü var."""
    meta = {"title": "Gece Seansı Vol. 1", "theme": "hiphop", "derleme": True,
            "derleme_liste": [{"ad": "Yeraltı", "zaman": "0:00"},
                              {"ad": "Vardiya", "zaman": "3:00"},
                              {"ad": "Son Kez", "zaman": "6:00"}]}
    assert social_text.sozlerden_alinti(meta) == ""


def test_eksik_isaretli_soz_dosyasindan_alinti_yapilmaz(tmp_path, monkeypatch):
    """Kendini "EKSİK, tamamlanmalı" diye işaretlemiş dosya insan onayından
    geçmemiş demektir — yarım bir dizeyi yayına koymayız."""
    md = tmp_path / "eksik_sozler.md"
    md.write_text(
        "# Eksik\n\n## Sözler (ekran görüntülerinden — EKSİK, tamamlanmalı)\n\n"
        "## Temiz Sözler\n\n```\n"
        "Gecenin ortasinda bir isik yandi\n"
        "Ve sabaha kadar hic sonmedi durdu\n"
        "```\n", encoding="utf-8")
    monkeypatch.setattr(social_text, "dogrulanmis_sozler_yolu", lambda t: str(md))
    assert social_text.sozlerden_alinti({"title": "Eksik"}) == ""


# --------------------------------------------------------------------------
# Regresyon kapısı: uzun format havuzları GERÇEKTEN kullanıyor mu.
# --------------------------------------------------------------------------

def test_takip_satiri_havuzdan_geliyor(aciklamalar):
    """ÖNCE hardcoded tek cümleydi ("Yeni şarkılar için takipte kalın 🎵") ve
    19/19 açıklamada birebir aynıydı; config.FOLLOW_LINES havuzu zaten vardı."""
    havuz = set(config.FOLLOW_LINES)
    gorulen = set()
    for metin in aciklamalar.values():
        gorulen |= (set(s for s in metin.split("\n")) & havuz)
    assert len(gorulen) >= 2, \
        "takip satırı havuzdan seçilmiyor gibi (görülen: %s)" % sorted(gorulen)


def test_custom_hooks_uzun_formatta_da_okunuyor():
    """`meta["custom_hooks"]` şarkının KENDİ sözlerinden türetilmiş satırlar.
    build_caption okuyordu, build_snippet okumuyordu — tam da bu yüzden 19
    şarkı yalnızca 10 farklı hook üretiyordu."""
    meta = {"title": "Test Şarkısı", "theme": "pop",
            "custom_hooks": ["Masada iki tabak, biri hep boş"],
            "custom_questions": ["Sen hangisini tanıdın? 👇"]}
    d = build_snippet(meta)["description"]
    assert d.startswith("Masada iki tabak, biri hep boş")
    assert "Sen hangisini tanıdın? 👇" in d
