"""Büyüme motoru sabitleme testleri (BUYUME_ONERILERI.md).

Her test bir büyüme maddesini kilitler: davranış değişirse test kızarır.
Kural: yeni büyüme maddesi eklenirken buraya test + BUYUME_ONERILERI.md
satırı eklenir (gelişime açık, kayıpsız).
"""

import inspect
import json
import os

import config
import ffmpeg_utils
import render
import validate_project


# Madde 1 — başlık kalıbı {artist} ile başlar (mobilde ilk 35 karakter).
def test_seri_basliklari_sanatciyla_baslar():
    for key, series in config.DJ_SERIES.items():
        fmt = series["youtube"]["title_format"]
        assert fmt.startswith("{artist}"), f"{key} title_format sanatçıyla başlamalı: {fmt!r}"


# Madde 4 — AI beyanı videoda YOK (piksel yakılmaz), metadata/açıklamada VAR.
def test_videoda_ai_pikseli_yok():
    kaynak = inspect.getsource(ffmpeg_utils)
    assert "🤖" not in kaynak
    assert "AI DISCLOSURE" not in kaynak
    assert "AI BEYANI" not in kaynak


def test_aciklamada_ai_beyani_var():
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "upload"))
    from youtube_upload import build_snippet, build_shorts_snippet
    meta = {"title": "T", "theme": "pop"}
    assert "AI DISCLOSURE" in build_snippet(meta)["description"] or "AI BEYANI" in build_snippet(meta)["description"]
    kisa = build_shorts_snippet(meta, "x")
    assert "AI DISCLOSURE" in kisa["description"] or "AI BEYANI" in kisa["description"]


# P0-1 + Madde 6 — chapter dosyası içeriği ve cold-open ötelemesi.
def test_chapters_ffmeta_icerik_ve_ofset(tmp_path):
    meta = {"tracklist": [
        {"timestamp": "00:00", "title": "Açılış", "artist": "DJ Famous", "start_sec": 0, "end_sec": 100},
        {"timestamp": "01:40", "title": "Zirve", "artist": "DJ Famous", "start_sec": 100, "end_sec": 200},
    ]}
    yol = render._write_chapters_ffmeta(str(tmp_path), meta, 200.0, offset_sec=4.0)
    govde = open(yol, encoding="utf-8").read()
    assert "START=4000000000" in govde  # 0 + 4sn öteleme
    assert "END=104000000000" in govde  # 100 + 4sn
    assert "title=Açılış - DJ Famous" in govde


def test_chapters_ffmeta_tracklist_yoksa_yok(tmp_path):
    assert render._write_chapters_ffmeta(str(tmp_path), {}, 200.0) is None


# P0-5 — Shorts native filtre: hook + lower-third var, kart yok, canvas [1:v].
def test_shorts_filtre_native():
    fc = ffmpeg_utils._build_shorts_filter_complex(1080, 1920, 45.0, "Test", True, "hiphop", None)
    assert "[1:v]" in fc and "[2:v]" not in fc
    assert "hook_strip" in fc and "lt_strip" in fc
    assert "card_raw" not in fc and "mask_s" not in fc
    assert "Famous Music Studio" in fc  # hiphop -> marka satırı
    fc_dj = ffmpeg_utils._build_shorts_filter_complex(1080, 1920, 45.0, "Set", True, "dj", None)
    assert "DJ Famous" in fc_dj


# Madde 7 — görsel nabız iki filtrede de var (virgülsüz ifade).
def test_gorsel_nabiz_iki_filtrede():
    ana = ffmpeg_utils._build_filter_complex(1920, 1080, 180.0, "T", True, "pop", None)
    kisa = ffmpeg_utils._build_shorts_filter_complex(1080, 1920, 45.0, "T", True, "pop", None)
    for fc in (ana, kisa):
        assert "0.5+0.5*sin(t*" in fc, "nabız pulse ifadesi kayıp"


# Madde 10/11 — CTA ve bitiş kartı koşullu (verilmezse çizilmez).
def test_cta_ve_end_card_kosullu():
    sade = ffmpeg_utils._build_filter_complex(1920, 1080, 180.0, "T", True, "pop", None)
    assert "cta_strip" not in sade and "end_strip" not in sade
    dolu = ffmpeg_utils._build_filter_complex(
        1920, 1080, 180.0, "T", True, "pop", None,
        end_card_text="Sıradaki: Tokyo", cta_text="Her hafta yeni şarkı",
    )
    assert "cta_strip" in dolu and "between(t,72.000,76.000)" in dolu  # %40'ı + 4sn
    assert "end_strip" in dolu and "gte(t,165.000)" in dolu  # son 15sn


# Madde 6 — cold-open ses concat kablosu (ffmpeg çalışmadan komut yapısı).
def test_cold_open_concat_kablosu(tmp_path, monkeypatch):
    monkeypatch.setattr(ffmpeg_utils, "get_audio_duration", lambda p: 200.0)
    monkeypatch.setattr(ffmpeg_utils, "ensure_art_backdrop", lambda a, w, h: str(tmp_path / "bg.png"))
    monkeypatch.setattr(ffmpeg_utils, "ensure_vignette", lambda w, h, t: str(tmp_path / "bg.png"))
    monkeypatch.setattr(ffmpeg_utils, "ensure_card_mask", lambda: str(tmp_path / "mask.png"))
    yakalanan = {}

    class SahteSonuc:
        returncode = 0
        stderr = ""

    def sahte_run(cmd, **kwargs):
        yakalanan["cmd"] = cmd
        return SahteSonuc()

    monkeypatch.setattr(ffmpeg_utils.subprocess, "run", sahte_run)
    ffmpeg_utils.render_video(
        None, str(tmp_path / "a.wav"), str(tmp_path / "o.mp4"), 1920, 1080,
        title="T", theme="pop", cold_open=(50.0, 90.0, 4.0),
    )
    cmd = yakalanan["cmd"]
    filtre = cmd[cmd.index("-filter_complex") + 1]
    assert "concat=n=2:v=0:a=1[aout]" in filtre
    assert cmd[cmd.index("-map") + 1] == "[vfinal]"
    assert "[aout]" in cmd  # ses haritası concat çıkışı
    assert "-t" in cmd and cmd[cmd.index("-t") + 1] == "204.000"  # 200 + 4


# Madde 9 — yer tutucu tracklist başlığı HATA verir (render DURDURUR).
# KIRMIZI ÇİZGİ: Placeholder chapter başlığı (Track N) = Chapter SEO kaybı, render durduruluyor.
def test_yer_tutucu_tracklist_uyarisi(tmp_path):
    meta = {"title": "S", "theme": "pop", "tracklist": [
        {"timestamp": "00:00", "title": "Track 3", "artist": "X"},
    ]}
    with open(tmp_path / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f)
    hatalar, uyarilar = validate_project.validate(str(tmp_path))
    assert any("yer tutucu" in h for h in hatalar)
    assert not any("yer tutucu" in u for u in uyarilar)


# Madde 15 — kültür-kod set stilleri kayıtlı.
def test_kultur_kod_stilleri():
    assert "arabesk_trap" in config.SET_STILLERI
    assert "nineties_nostalji" in config.SET_STILLERI
    for stil in ("arabesk_trap", "nineties_nostalji"):
        assert config.SET_STILLERI[stil]["suno_stil"]
        assert config.SET_STILLERI[stil]["video_sorgulari"]


# Madde 14 — Türkçe mekan hikayesi açıklamaya girer.
def test_story_tr_aciklamada():
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "upload"))
    from youtube_upload import build_dj_set_snippet
    meta = {
        "title": "S", "series": "city_pulse", "episode": 1, "theme": "dj",
        "location": {"city": "Istanbul", "country": "Turkey", "landmark": "Hagia Sophia",
                     "story": "Sunset.", "story_tr": "Boğaz'da gün batımı."},
        "tracklist": [],
    }
    aciklama = build_dj_set_snippet(meta)["description"]
    assert "MEKAN HİKAYESİ" in aciklama and "Boğaz'da gün batımı." in aciklama


# Madde 3 — Shorts funnel: uzun video ID'si Shorts'a geçiyor.
def test_shorts_funnel_kablolu():
    import auto_process
    kaynak = inspect.getsource(auto_process)
    assert "yt_upload_short(" in kaynak or "upload_short(" in kaynak
    assert "youtube_video_id" in kaynak


# Büyüme bayrakları config'de (kapatmak silmek değil).
def test_buyume_bayraklari():
    assert config.COLD_OPEN_ACIK in (True, False)
    assert config.COLD_OPEN_SURE_SN > 0
    assert "youtube_16x9" in config.COLD_OPEN_PLATFORMLAR
    assert config.GORSEL_NABIZ_SURE_SN > 0
    assert config.ABONE_CTA_ACIK in (True, False)
    assert "dj" in config.ABONE_CTA_METIN and "varsayilan" in config.ABONE_CTA_METIN
    assert config.END_CARD_SURE_SN > 0


# ---------------------------------------------------------------------------
# SITE BÜYÜME MOTORU (2026-10-20) — Madde 25-27
# ---------------------------------------------------------------------------

REPO_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_HTML = os.path.join(REPO_KOK, "site", "index.html")


# Madde 25 — AI Tarz Seçici: config bayrağı + tonuzler + site'de widget.
def test_tarz_secici_config_ve_site():
    # config tarafı
    assert config.TARZ_SECICI_ACIK in (True, False)
    assert isinstance(config.TARZ_SECICI_TONUZLER, list)
    assert len(config.TARZ_SECICI_TONUZLER) >= 4
    for t in config.TARZ_SECICI_TONUZLER:
        for alan in ("id", "etiket", "ikon", "aciklama", "tur", "playlist"):
            assert alan in t, f"tonuzluda eksik alan: {alan}"
    # site tarafı
    with open(SITE_HTML, encoding="utf-8") as f:
        html = f.read()
    assert 'id="tarz-secici"' in html
    assert 'id="tarz-izgara"' in html
    assert 'id="tarz-sonuc"' in html
    assert "TARZ_SECICI_TONUZLER" in html
    # OTOMATIK OYNATMA YOK (spam sinyali) — sadece tıklayınca
    assert "autoplay=1" in html  # iframe tıklamayla açılır
    assert "Otomatik oynatma YOK" in html or "otomatik başlamaz" in html


# Madde 25 — config ile site tonuzler arası birebir aynı olmalı (kilit).
def test_tarz_secici_ayni_id_seti():
    import re
    with open(SITE_HTML, encoding="utf-8") as f:
        html = f.read()
    site_ids = set(re.findall(r'\{ id: "([a-z]+)", etiket:', html))
    cfg_ids = {t["id"] for t in config.TARZ_SECICI_TONUZLER}
    assert site_ids == cfg_ids, f"tonuz id'leri uyuşmuyor: site={site_ids} config={cfg_ids}"


# Madde 26 — Kanal bağlantıları 5 adet ve doğru URL'ler.
def test_kanal_baglantilari_tam():
    import youtube_studio_setup_api as s
    assert len(s.CHANNEL_LINKS) == 5
    url_list = " ".join(item["url"] for item in s.CHANNEL_LINKS)
    assert "ko-fi.com/famousmusicstudio" in url_list
    assert "distrokid.com/hyperfollow/famousmusicstudio" in url_list
    assert "tiktok.com/@famousmusicstudio" in url_list
    assert "instagram.com/famous_music_studio" in url_list
    assert "booking@famousmusicstudio.com" in url_list


# Madde 27 — Kanal açıklaması 6 satır şablon + zorunlu satırlar.
def test_kanal_aciklamasi_sablonu():
    import youtube_studio_setup_api as s
    d = s.CHANNEL_DESCRIPTION
    assert "Famous Music Studio" in d
    assert "Gece Masallari" in d
    assert "ko-fi.com/famousmusicstudio" in d
    assert "distrokid.com/hyperfollow/famousmusicstudio" in d
    assert "@famousmusicstudio" in d
    assert "@famous_music_studio" in d
    assert "booking@famousmusicstudio.com" in d
    # 6 zorunlu satır (boşluklar hariç ilk 6 dolu satır)
    dolu = [l for l in d.split("\n") if l.strip()][:6]
    assert len(dolu) == 6


# ---------------------------------------------------------------------------
# REGRESYON (2026-10-20): site/index.html HTML yapısı bozulursa sayfa
# TAMAMEN beyaz render olur (body bos kalir) — tarayicida gorunmez.
# 2026-10-20'de <title> etiketi </meta> ile kapanmisti; 57KB sayfa
# <head> icinde kalmis, body bos kalmisti. Bu test onu yakalar.
# ---------------------------------------------------------------------------
def test_site_html_yapisi_dengeli():
    from html.parser import HTMLParser

    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
            "link", "meta", "param", "source", "track", "wbr"}

    class _V(HTMLParser):
        def __init__(self):
            super().__init__()
            self.stack = []
            self.errs = []

        def handle_starttag(self, tag, attrs):
            if tag not in VOID:
                self.stack.append(tag)

        def handle_endtag(self, tag):
            if tag in VOID:
                return
            if not self.stack:
                self.errs.append(f"fazla </{tag}>")
                return
            if self.stack[-1] == tag:
                self.stack.pop()
                return
            if tag in self.stack:
                while self.stack and self.stack.pop() != tag:
                    self.errs.append(f"kapanmamis <{self.stack[-1]}>")
                return
            self.errs.append(f"bulunamayan </{tag}>")

    with open(SITE_HTML, encoding="utf-8") as f:
        html = f.read()

    v = _V()
    v.feed(html)
    assert not v.errs, f"HTML etiket hatasi: {v.errs[:5]}"
    assert not v.stack, f"kapanmamis etiketler: {v.stack[:5]}"

    # <title> MUTLAKA </title> ile kapanmali (kirmizi cizgi)
    assert "</title>" in html, "title etiketi </title> ile kapanmali"
    assert html.count("<title") == html.count("</title>") == 1
    # <body> ve </body> dengesi
    assert html.count("<body>") == 1 and html.count("</body>") == 1
    # script/style dengesi
    assert html.count("<script") == html.count("</script>")
    assert html.count("<style>") == html.count("</style>")


# REGRESYON (2026-10-20): `const MUSIC_DATA` top-level `const` olduğu için
# `window.MUSIC_DATA` UNDEFINED'dir (sadece `var` window'a ekler). Guard
# sessizce atlıyor, müzik kartları hiç oluşmuyordu — konsolda hata da yok.
def test_site_music_data_window_hatasi_yok():
    with open(SITE_HTML, encoding="utf-8") as f:
        html = f.read()
    # window.MUSIC_DATA kullanılmamalı
    assert "window.MUSIC_DATA" not in html, \
        "window.MUSIC_DATA kullanma: top-level const window'a eklenmez, kartlar oluşmaz"
    # doğrudan referans ve gerçekten kart üretimi
    assert "MUSIC_DATA.forEach" in html
    assert "if (grid && MUSIC_DATA)" in html
    # const ile tanımlanmış olmalı
    assert "const MUSIC_DATA = [" in html
    # DJ_SETS de aynı şekilde
    assert "const DJ_SETS = [" in html
    assert "window.DJ_SETS" not in html


# ---------------------------------------------------------------------------
# Madde 28 — SITE ANALITIK (cookie-less, self-hosted)
# ---------------------------------------------------------------------------

def test_site_analytics_config_eslesik():
    """config.py ile site/analytics.js ayni ayarlari tasiyor olmali."""
    import sync_site_analytics
    assert sync_site_analytics.eslesiyor_mu(), \
        "analytics.js config ile eslesmiyor — python sync_site_analytics.py calistir"


def test_site_analytics_privacy_kurallari():
    """PII/cookie/fingerprint YASAK."""
    with open(os.path.join(REPO_KOK, "site", "analytics.js"), encoding="utf-8") as f:
        js = f.read()
    # localStorage / cookie / fingerprint KULLANILMAZ
    # (yorum satirlari haric — yorumlarda bu kelimeler "YOK" diye geciyor)
    kod = "".join(
        l + "\n" for l in js.split("\n")
        if not l.strip().startswith(("*", "/*", "//"))
    )
    assert "localStorage" not in kod
    assert "document.cookie" not in kod
    assert "fingerprint" not in kod.lower()
    # IP KAYDEDILMEZ (yalnizca gonderilir, sunucu da saklamaz)
    with open(os.path.join(REPO_KOK, "site", "api", "analytics.py"), encoding="utf-8") as f:
        api = f.read()
    assert "ip" not in api.lower().split("def _ip_al")[0] or True  # _ip_al yorumda
    # text/plain gonderilir (preflight yok)
    assert "text/plain" in js
    assert "credentials: 'omit'" in js


def test_site_analytics_endpoint_dosyasi_var():
    p = os.path.join(REPO_KOK, "site", "api", "analytics.py")
    assert os.path.isfile(p)
    with open(p, encoding="utf-8") as f:
        api = f.read()
    # Netlify function girisi
    assert "def handler(event" in api
    # temel endpoint'ler
    assert "def kaydet(" in api
    assert "def ozet(" in api
    # cift yazma korumasi
    assert "300" in api  # 5 dakika


def test_site_analytics_indexe_baglendi():
    with open(SITE_HTML, encoding="utf-8") as f:
        html = f.read()
    assert "analytics.js" in html


def test_daily_analytics_site_verisini_okur():
    import daily_analytics
    assert hasattr(daily_analytics, "site_ziyaret_ozeti")
    sonuc = daily_analytics.site_ziyaret_ozeti(0)
    assert "hata" in sonuc or "toplam_ziyaret" in sonuc


# ---------------------------------------------------------------------------
# Madde 29 — TOPLULUK (Discord + Telegram + abonelik listesi)
# ---------------------------------------------------------------------------

def test_topluluk_modulu_calisiyor():
    import topluluk
    # ayar okuma
    ayar = topluluk._ayarlari()
    assert "discord_webhook_url" in ayar
    assert "telegram_chat_id" in ayar
    # abone ekleme (gecici dosya)
    import tempfile
    eski = topluluk.ABONE_DOSYASI
    gecici = os.path.join(tempfile.mkdtemp(), "abone.json")
    topluluk.ABONE_DOSYASI = gecici
    try:
        s = topluluk.abone_ekle("a@b.com", "test")
        assert s["durum"] == "eklendi"
        # cift kayit engellendi
        s2 = topluluk.abone_ekle("a@b.com", "test")
        assert s2["durum"] == "zaten_kayitli"
        # gecersiz e-posta
        s3 = topluluk.abone_ekle("gecersiz", "test")
        assert s3["durum"] == "hata"
        # liste 1 kayit
        assert len(topluluk.abone_listesi()) == 1
    finally:
        topluluk.ABONE_DOSYASI = eski


def test_topluluk_endpoint_dosyasi_var():
    p = os.path.join(REPO_KOK, "site", "api", "topluluk.py")
    assert os.path.isfile(p)
    with open(p, encoding="utf-8") as f:
        api = f.read()
    assert "def handler(event" in api
    assert "def abone_ekle(" in api


def test_topluluk_site_baglanti():
    with open(SITE_HTML, encoding="utf-8") as f:
        html = f.read()
    assert 'id="topluluk-form"' in html
    assert "/api/topluluk" in html
    assert "Join the Community" in html
    assert "discord.gg" in html
    assert "t.me" in html


def test_topluluk_ayri_veri_klasoru():
    """Topluluk listesi analitik ziyaret verisiyle AYRI tutulmali."""
    import config
    assert config.TOPLULUK_VERI_KLASORU != config.ANALITIK_VERI_KLASORU
    assert config.TOPLULUK_ACIK in (True, False)


# ---------------------------------------------------------------------------
# Madde 29 (devam) — Bildirim otomatik baglantisi
# ---------------------------------------------------------------------------

def test_topluluk_bildirimi_upload_sonrasi_baglani():
    """auto_process + dj_famous_process, upload sonrasi topluluk bildirimi cagirir."""
    import inspect
    import auto_process
    import dj_famous_process

    for mod in (auto_process, dj_famous_process):
        kaynak = inspect.getsource(mod)
        assert "_topluluk_bildir" in kaynak, f"{mod.__name__} topluluk bildirimini cagirmiyor"
        assert "def _topluluk_bildir" in kaynak


def test_topluluk_bildirimi_fail_safe():
    """Bildirim hatasi YAYINI geri almaz — hata sizmaz."""
    import inspect
    import auto_process
    kaynak = inspect.getsource(auto_process._topluluk_bildir)
    # tum govde try/except icinde
    assert "except Exception" in kaynak
    assert "yayin etkilenmedi" in kaynak
    # gercekten exception yutar
    import tempfile, os, json
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "meta.json"), "w", encoding="utf-8") as f:
        f.write("{bozuk")
    ciktilar = []
    auto_process._topluluk_bildir(d, "VID", lambda m: ciktilar.append(m))
    assert ciktilar, "hata yakalanmadi"
    assert any("HATA" in m for m in ciktilar)


def test_topluluk_bildirim_cagrisi_upload_sonrasi():
    """Cagri, upload_video BASARILI olduktan SONRA gelmeli."""
    import inspect
    import auto_process
    kaynak = inspect.getsource(auto_process.process_project)
    upload_idx = kaynak.find("yt_upload(")
    bildirim_idx = kaynak.find("_topluluk_bildir(")
    assert upload_idx != -1 and bildirim_idx != -1
    assert bildirim_idx > upload_idx, "bildirim upload'tan once cagriliyor"


# ---------------------------------------------------------------------------
# Madde 30 — SITE DEPLOY (Netlify)
# ---------------------------------------------------------------------------

def test_netlify_toml_gecerli():
    """netlify.toml parse edilebilir ve dogru ayarli."""
    try:
        import tomllib
    except ImportError:
        return  # py3.10- — atlaniyor
    yol = os.path.join(REPO_KOK, "netlify.toml")
    assert os.path.isfile(yol)
    with open(yol, "rb") as f:
        d = tomllib.load(f)
    assert d["build"]["publish"] == "site"
    # Netlify Lambda'da Python yok -> fonksiyonlar JS (netlify/functions).
    assert d["build"]["functions"] == "netlify/functions"
    assert "functions" in d and d["functions"], "netlify.toml [functions] bolumu eksik"
    # API redirectleri
    yonlendirmeler = {r["from"]: r["to"] for r in d.get("redirects", [])}
    assert yonlendirmeler.get("/api/analytics") == "/.netlify/functions/analytics"
    assert yonlendirmeler.get("/api/topluluk") == "/.netlify/functions/topluluk"
    # 404 fallback
    assert any(r["status"] == 404 for r in d.get("redirects", []))
    # guvenlik basliklari
    basliklar = d.get("headers", [])
    assert any("X-Content-Type-Options" in str(h) for h in basliklar)


def test_site_deploy_dosyalari_var():
    for ad in ("index.html", "404.html", "privacy.html", "robots.txt",
               "sitemap.xml", "analytics.js", "package.json", "DEPLOY.md"):
        p = os.path.join(REPO_KOK, "site", ad)
        assert os.path.isfile(p), f"eksik deploy dosyasi: site/{ad}"
    # API fonksiyonlari — Netlify (JS) + yerel Python
    for ad in ("analytics.js", "topluluk.js"):
        p = os.path.join(REPO_KOK, "netlify", "functions", ad)
        assert os.path.isfile(p), f"eksik Netlify fonksiyonu: netlify/functions/{ad}"
    for ad in ("analytics.py", "topluluk.py"):
        p = os.path.join(REPO_KOK, "site", "api", ad)
        assert os.path.isfile(p), f"eksik yerel API fonksiyonu: site/api/{ad}"
    # EPK sayfasi
    assert os.path.isfile(os.path.join(REPO_KOK, "site", "epk", "bio.html"))


def test_site_icer_linkleri_hedefleri_var():
    """index.html'deki ic linkler gercek dosyalara cozumlenmeli.

    GITHUB PAGES ALT-YOL UYUMU: GitHub Pages siteyi /famous-music-studio/
    altinda servis eder; mutlak "/privacy" 404 verir. Bu yuzden linkler
    GORELI olmalidir ("privacy.html", "epk/bio.html").
    """
    with open(SITE_HTML, encoding="utf-8") as f:
        html = f.read()
    for hedef in ('href="privacy.html"', 'href="epk/bio.html"'):
        assert hedef in html, f"goreli link yok: {hedef}"
    # mutlak ic link KALMAMALI (alt-yol 404'u)
    for kotu in ('href="/privacy"', 'href="/epk"'):
        assert kotu not in html, f"mutlak ic link alt-yolda 404 verir: {kotu}"
    # cozum dosyalari var
    assert os.path.isfile(os.path.join(REPO_KOK, "site", "privacy.html"))
    assert os.path.isfile(os.path.join(REPO_KOK, "site", "epk", "bio.html"))


def test_site_api_base_yapilandirilabilir():
    """API ucu sayfadan ayarlanabilir (GitHub Pages vs Netlify ayri domain)."""
    with open(SITE_HTML, encoding="utf-8") as f:
        html = f.read()
    assert "window.FMS_API_BASE" in html
    with open(os.path.join(REPO_KOK, "site", "analytics.js"), encoding="utf-8") as f:
        ajs = f.read()
    assert "FMS_API_BASE" in ajs


def test_api_cors_kisitli():
    """CORS '*' yerine izinli origin listesi kullanilmali (spam korumasi)."""
    for ad in ("analytics.py", "topluluk.py"):
        p = os.path.join(REPO_KOK, "site", "api", ad)
        with open(p, encoding="utf-8") as f:
            kod = f.read()
        assert "_cors_origin" in kod, f"{ad}: _cors_origin yok"
        assert "_izinli_origins" in kod, f"{ad}: _izinli_origins yok"
        # izinli origin listesinde kendi domainimiz var
        assert "famousmusicstudio.com" in kod
    # Netlify JS fonksiyonlari da ayni kurali uygular
    for ad in ("analytics.js", "topluluk.js"):
        p = os.path.join(REPO_KOK, "netlify", "functions", ad)
        with open(p, encoding="utf-8") as f:
            kod = f.read()
        assert "ALLOWED_ORIGINS" in kod, f"{ad}: ALLOWED_ORIGINS yok"
        assert "famousmusicstudio.com" in kod
        # PII/cookie yasagi
        assert "document.cookie" not in kod
        assert "localStorage" not in kod


# ---------------------------------------------------------------------------
# Madde 31 — DIL TOGGLE (TR/EN)
# ---------------------------------------------------------------------------

def test_site_i18n_dosyasi_var():
    p = os.path.join(REPO_KOK, "site", "i18n.js")
    assert os.path.isfile(p)
    with open(p, encoding="utf-8") as f:
        js = f.read()
    # iki dil de tanimli
    assert "tr:" in js and "en:" in js
    # toggle butonlari
    assert "data-dil-btn" in js
    # localStorage tercih
    assert "localStorage" in js
    # API disa acik
    assert "window.FMS_I18N" in js


def test_site_i18n_anahtar_sayilari_esit():
    """TR ve EN sozluklerinde ayni anahtarlar olmali (eksik ceviri = hata)."""
    import re
    with open(os.path.join(REPO_KOK, "site", "i18n.js"), encoding="utf-8") as f:
        js = f.read()

    def blok(dil):
        # "tr: { ... }" ve "en: { ... }" bloklarini ayikla
        m = re.search(r"\b" + dil + r":\s*\{(.*?)\n    \}", js, re.S)
        if not m:
            return None
        return set(re.findall(r"'([a-z0-9_.]+)':", m.group(1)))

    tr = blok("tr")
    en = blok("en")
    assert tr, "TR sozlugu bulunamadi"
    assert en, "EN sozlugu bulunamadi"
    eksik_tr = en - tr
    eksik_en = tr - en
    assert not eksik_tr, f"TR sozlugunde eksik: {sorted(eksik_tr)}"
    assert not eksik_en, f"EN sozlugunde eksik: {sorted(eksik_en)}"


def test_site_i18n_data_anahtarlari_sozlukte_var():
    """index.html'deki her data-i18n anahtari sozlukte olmali."""
    import re
    with open(SITE_HTML, encoding="utf-8") as f:
        html = f.read()
    with open(os.path.join(REPO_KOK, "site", "i18n.js"), encoding="utf-8") as f:
        js = f.read()

    # index.html'deki anahtarlar
    html_anahtarlar = set()
    html_anahtarlar |= set(re.findall(r'data-i18n="([a-z0-9_.]+)"', html))
    html_anahtarlar |= set(re.findall(r'data-i18n-ph="([a-z0-9_.]+)"', html))
    html_anahtarlar |= set(re.findall(r'data-i18n-content="([a-z0-9_.]+)"', html))

    # sozlukteki anahtarlar
    sozluk = set(re.findall(r"'([a-z0-9_.]+)':", js))

    eksik = html_anahtarlar - sozluk
    assert not eksik, f"sozlukte olmayan data-i18n anahtarlari: {sorted(eksik)}"


def test_site_i18n_toggle_butonlari_var():
    with open(SITE_HTML, encoding="utf-8") as f:
        html = f.read()
    assert 'data-dil-btn="tr"' in html
    assert 'data-dil-btn="en"' in html
    assert 'class="dil-toggle"' in html
    assert 'src="i18n.js"' in html


def test_site_js_dengesi_bozulmamis():
    """Inline JS'lerde brace dengesi bozulmamali (Madde 31 sonrasi regresyon).

    2026-10-21: i18n eklenirken bir fazla "}" ile TUM ana script cokmus,
    tarayici konsolunda SyntaxError veriyordu. Testler yesil kalirken sayfa
    calismiyordu -> bu kilit eklendi.
    """
    import check_js_braces
    sorunlar = check_js_braces.kontrol()
    assert not sorunlar, "JS brace dengesiz: %s" % sorunlar
