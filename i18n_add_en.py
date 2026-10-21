# -*- coding: utf-8 -*-
"""site/i18n.js — privacy/epk/404 sayfalari icin EN cevirilerini ekler (Madde 31)."""
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

YOL = "site/i18n.js"

# Anahtar -> (TR, EN)
YENI = {
    # ---------------- 404 ----------------
    "h404.h1": ("Bu sayfa bulunamadı", "Page not found"),
    "h404.p": ("Aradığınız sayfa taşınmış ya da hiç var olmamış olabilir. Aşağıdan devam edebilirsiniz.",
               "The page you're looking for may have moved or never existed. Continue below."),
    "h404.ana": ("Ana sayfa", "Home"),
    "h404.youtube": ("YouTube kanalı", "YouTube channel"),
    "h404.gizlilik": ("Gizlilik", "Privacy"),
    "h404.epk": ("Press Kit", "Press Kit"),

    # ---------------- privacy ----------------
    "prv.h1": ("Gizlilik Politikası", "Privacy Policy"),
    "prv.sub": ("Famous Music Studio · Son güncelleme: 21 Ekim 2026",
                 "Famous Music Studio · Last updated: October 21, 2026"),
    "prv.ozet1": ("<strong>Kısa özet:</strong> Bu sitede <strong>çerez kullanılmaz</strong>,",
                   "<strong>In short:</strong> This site uses <strong>no cookies</strong>,"),
    "prv.ozet2": ("<strong>reklam takibi yapılmaz</strong>, <strong>fingerprint oluşturulmaz</strong>",
                   "<strong>no ad tracking</strong>, and <strong>no fingerprinting</strong>"),
    "prv.ozet3": ("ve <strong>üçüncü taraf analitik yüklenmez</strong>. Ziyaretçileri",
                   "<strong>no third-party analytics</strong>. No data that directly"),
    "prv.ozet4": ("doğrudan tanımlayan hiçbir veri toplanmaz. Yalnızca topluluk listesine",
                   "identifies visitors is collected. Only an email address,"),
    "prv.ozet5": ("<strong>isteğe bağlı olarak</strong> e-posta adresi eklenebilir.</span>",
                   "<strong>optionally</strong> added to our community list.</span>"),
    "prv.h2_1": ("1. Toplanan Veriler", "1. Data We Collect"),
    "prv.h3_1a": ("Site ziyaret analitiği (otomatik, her ziyarette)",
                   "Site visit analytics (automatic, on every visit)"),
    "prv.h3_1b": ("Topluluk listesi (yalnızca siz kaydolursanız)",
                   "Community list (only if you sign up)"),
    "prv.h2_2": ("2. Çerez ve Yerel Depolama", "2. Cookies and Local Storage"),
    "prv.h2_3": ("3. Üçüncü Taraf İçerikler", "3. Third-Party Content"),
    "prv.h2_4": ("4. Verilerin Kullanımı", "4. How Data Is Used"),
    "prv.h2_5": ("5. Saklama Süresi", "5. Retention"),
    "prv.h2_6": ("6. Haklarınız (KVKK / GDPR)", "6. Your Rights (GDPR / KVKK)"),
    "prv.h2_7": ("7. Üçüncü Taraf Servisler", "7. Third-Party Services"),
    "prv.h2_8": ("8. Değişiklikler", "8. Changes"),
    "prv.h2_9": ("9. İletişim", "9. Contact"),
    "prv.p_1a": ("<p>Bu sitede <strong>çerez kullanılmaz</strong>,",
                 "<p>No <strong>cookies</strong> are used on this site,"),
    "prv.p_1b": ("<p>Bu veriler <strong>kendi sunucumuzda</strong>",
                 "<p>These data are stored <strong>on our own server</strong>"),
    "prv.p_3": ("<p>Sayfada YouTube gömülü oynatıcılar bulunur. Bu gömülü içerikler",
                 "<p>The page embeds YouTube players. These embedded players"),
    "prv.p_6": ("<p>KVKK (Madde 11) ve GDPR (Madde 15-21) kapsamında:</p>",
                 "<p>Under GDPR (Articles 15-21) and KVKK (Article 11):</p>"),
    "prv.p_6b": ("<p><strong>Nasıl başvurulur?</strong><br>",
                 "<p><strong>How to reach us?</strong><br>"),
    "prv.p_8": ("<p>Bu politika değişirse sayfadaki \"Son güncelleme\" tarihi güncellenir.",
                "<p>If this policy changes, the \"last updated\" date on this page is updated."),
    "prv.p_9": ("<p>Famous Music Studio · <a href=\"mailto:hello@famousmusicstudio.com\">hello@famousmusicstudio.com</a><br>",
                "<p>Famous Music Studio · <a href=\"mailto:hello@famousmusicstudio.com\">hello@famousmusicstudio.com</a><br>"),
    "prv.th_2a": ("Mekanizma", "Mechanism"),
    "prv.th_2b": ("Kullanılıyor mu?", "Used?"),
    "prv.th_2c": ("Açıklama", "Notes"),
    "prv.th_7a": ("Servis", "Service"),
    "prv.th_7b": ("Amaç", "Purpose"),
    "prv.th_7c": ("Kapsam", "Scope"),
    "prv.li_1a": ("Ziyaret zamanı", "Visit time"),
    "prv.li_1b": ("Sayfa yolu (URL sorgu dizesi hariç)", "Page path (URL query string excluded)"),
    "prv.li_1c": ("Referrer site adresi", "Referrer site host"),
    "prv.li_1d": ("Cihaz tipi (masaüstü / mobil / tablet)", "Device type (desktop / mobile / tablet)"),
    "prv.li_1e": ("Tarayıcı dili ve saat dilimi", "Browser language and time zone"),
    "prv.li_1f": ("Kaba viewport boyutu", "Coarse viewport size"),
    "prv.li_1g": ("E-posta adresi", "Email address"),
    "prv.li_1h": ("Kayıt zamanı ve kaynak (site / CLI)", "Signup time and source (site / CLI)"),
    "prv.hayir": ("Hayır", "No"),
    "prv.evet": ("Evet", "Yes"),
    "prv.f_ana": ("← Ana sayfa", "← Home"),
    "prv.f_epk": ("Press Kit", "Press Kit"),

    # ---------------- EPK ----------------
    "epk.h1": ("Press Kit (EPK)", "Press Kit (EPK)"),
    "epk.sub": ("Medya, promosör ve işbirliği ortakları için kaynaklar",
                 "Resources for media, promoters and collaborators"),
    "epk.sub2": ("Famous Music Studio · Medya, promosör ve işbirliği için kaynaklar",
                 "Famous Music Studio · Resources for media, promoters and collaborators"),
    "epk.h2_bio": ("Kısa Biyografi", "Short Biography"),
    "epk.h2_fact": ("Olgu Dosyası (Fact Sheet)", "Fact Sheet"),
    "epk.h2_tracks": ("Öne Çıkan Parçalar", "Featured Tracks"),
    "epk.h2_dj": ("DJ Set Serisi (DJ Famous)", "DJ Set Series (DJ Famous)"),
    "epk.h2_files": ("Kaynak Dosyalar", "Source Files"),
    "epk.h2_contact": ("İletişim", "Contact"),
    "epk.bio_p1": ("<p><strong>Famous Music Studio</strong>, Türkiye merkezli; yapay zekâ destekli",
                   "<p><strong>Famous Music Studio</strong> is a Turkey-based,"),
    "epk.bio_p2": ("müzik üretimine odaklanan bir müzik stüdyosudur. Türkçe Pop, R&amp;B, Trap,",
                   "AI-assisted music production studio focused on Turkish Pop, R&amp;B, Trap,"),
    "epk.bio_p3": ("Arabesk, Elektronik ve Melodic Techno türlerinde özgün parçalar ve DJ setleri",
                   "Arabesk, Electronic and Melodic Techno — original tracks and DJ mixes."),
    "epk.bio_p4": ("üretir. İlk albümü <strong>Gece Masalları</strong> (2026) bu çeşitliliği",
                   "Its debut album <strong>Gece Masalları</strong> (2026) brings this variety"),
    "epk.bio_p5": ("bir araya getirir: nostaljik arabesk melodileri, modern trap prodüksiyonu ve",
                   "together: nostalgic Arabesk melodies, modern trap production and"),
    "epk.bio_p6": ("sinematik melodic techno akışları aynı proje içinde buluşur.</span></p>",
                   "cinematic Melodic Techno flows meet in one project.</span></p>"),
    "epk.bio_p7": ("<p>Prodüksiyonda yapay zekâ araçları kullanılır; ancak her parçanın söz",
                   "<p>AI tools are used in production, but every track's lyrics,"),
    "epk.bio_p8": ("yazımı, tema kurgusu ve mix kararları stüdyo tarafından elden alınır.</span>",
                   "thematic direction and mix decisions are made by hand in the studio.</span>"),
    "epk.bio_p9": ("<p>Kanal haftalık yeni parça ve DJ setleriyle büyür; <em>DJ Famous</em>",
                   "<p>The channel grows with weekly new tracks and DJ sets; <em>DJ Famous</em>"),
    "epk.bio_p10": ("kimliğiyle Cuma geceleri yeni şehir konseptli setler yayımlar.</span></p>",
                    "releases a new-city concept set every Friday night.</span></p>"),
    "epk.k_bio": ("Biyografi &amp; Olgu Dosyası", "Bio &amp; Fact Sheet"),
    "epk.k_bio_p": ("Bu sayfadaki metin, <code>bio.md</code> ve <code>bio.json</code> dosyalarıyla aynıdır.",
                     "The text here matches the <code>bio.md</code> and <code>bio.json</code> files."),
    "epk.k_photo": ("Fotoğraf Rehberi", "Photo Guide"),
    "epk.k_photo_p": ("Çözünürlük, isimlendirme ve kullanım hakları rehberi.",
                      "Resolution, naming and usage-rights guide."),
    "epk.k_music": ("Müzik Varlıkları", "Music Assets"),
    "epk.k_music_p": ("Stem, instrumental, MIDI ve lisans koşulları.",
                       "Stems, instrumentals, MIDI and licence terms."),
    "epk.k_booking": ("Booking &amp; İşbirliği", "Booking &amp; Collabs"),
    "epk.k_booking_p": ("DJ booking, remix, sync lisans ve form şablonu.",
                        "DJ booking, remix, sync licence and form template."),
    "epk.not": ("Not:", "Note:"),
    "epk.not_p": ("Basın görselleri ve ses dosyaları için",
                  "For press photos and audio files,"),
    "epk.not_p2": ("adresine yazın. Talebe 48 saat içinde yanıt verilir.",
                    "email us. Requests are answered within 48 hours."),
    "epk.f_ana": ("← Ana sayfa", "← Home"),
    "epk.f_privacy": ("Gizlilik", "Privacy"),
}


def main():
    with open(YOL, encoding="utf-8") as f:
        js = f.read()

    eklenen = 0
    for anahtar, (tr, en) in YENI.items():
        satir_tr = "      '%s': '%s'," % (anahtar, tr.replace("'", "\\'"))
        satir_en = "      '%s': '%s'," % (anahtar, en.replace("'", "\\'"))
        if satir_tr in js and satir_en in js:
            continue
        # TR blokuna ekle
        i = js.find("\n    tr: {\n")
        if i < 0:
            print("HATA: tr blogu bulunamadi")
            return 1
        giris = i + len("\n    tr: {\n")
        js = js[:giris] + satir_tr + "\n" + js[giris:]
        # EN blokuna ekle
        i = js.find("\n    en: {\n")
        if i < 0:
            print("HATA: en blogu bulunamadi")
            return 1
        giris = i + len("\n    en: {\n")
        js = js[:giris] + satir_en + "\n" + js[giris:]
        eklenen += 1

    with open(YOL, "w", encoding="utf-8") as f:
        f.write(js)
    print("  i18n.js: %d anahtar eklendi" % eklenen)
    return 0


if __name__ == "__main__":
    sys.exit(main())
