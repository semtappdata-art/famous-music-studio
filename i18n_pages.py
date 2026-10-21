# -*- coding: utf-8 -*-
"""privacy.html ve epk/bio.html sayfalarini TR/EN iki dilli yapar (Madde 31)."""
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def uygula(dosya, ciftler, baslik_cifti=None, aciklama_cifti=None):
    with open(dosya, encoding="utf-8") as f:
        c = f.read()
    say = 0
    for eski, yeni in ciftler:
        if eski in c:
            c = c.replace(eski, yeni, 1)
            say += 1
        else:
            print("    BULUNAMADI: %s" % eski[:60].replace("\n", " "))
    if baslik_cifti:
        c = c.replace(baslik_cifti[0], baslik_cifti[1], 1)
        say += 1
    if aciklama_cifti:
        c = c.replace(aciklama_cifti[0], aciklama_cifti[1], 1)
        say += 1
    if 'src="i18n.js"' not in c:
        c = c.replace("</head>", '  <script src="i18n.js" defer></script>\n</head>', 1)
        say += 1
    c = c.replace('<html lang="tr">', '<html lang="tr">', 1)
    with open(dosya, "w", encoding="utf-8") as f:
        f.write(c)
    print("  %s: %d nitelik eklendi" % (dosya, say))
    return say


def main():
    # ======================================================== privacy.html
    print("privacy.html:")
    p = "site/privacy.html"
    ciftler = [
        # header
        ('<h1>Gizlilik Politikası</h1>',
         '<h1 data-i18n="prv.h1">Gizlilik Politikası</h1>'),
        ('<p>Famous Music Studio · Son güncelleme: 21 Ekim 2026</p>',
         '<p data-i18n="prv.sub">Famous Music Studio · Son güncelleme: 21 Ekim 2026</p>'),
        # ozet
        ('<p><strong>Kısa özet:</strong> Bu sitede <strong>çerez kullanılmaz</strong>,',
         '<p data-i18n="prv.ozet1"><strong>Kısa özet:</strong> Bu sitede <strong>çerez kullanılmaz</strong>,'),
        ('<strong>reklam takibi yapılmaz</strong>, <strong>fingerprint oluşturulmaz</strong>',
         '<span data-i18n="prv.ozet2"><strong>reklam takibi yapılmaz</strong>, <strong>fingerprint oluşturulmaz</strong></span>'),
        ('ve <strong>üçüncü taraf analitik yüklenmez</strong>. Ziyaretçileri',
         '<span data-i18n="prv.ozet3">ve <strong>üçüncü taraf analitik yüklenmez</strong>. Ziyaretçileri</span>'),
        ('doğrudan tanımlayan hiçbir veri toplanmaz. Yalnızca topluluk listesine',
         '<span data-i18n="prv.ozet4">doğrudan tanımlayan hiçbir veri toplanmaz. Yalnızca topluluk listesine</span>'),
        ('<strong>isteğe bağlı olarak</strong> e-posta adresi eklenebilir.</p>',
         '<span data-i18n="prv.ozet5"><strong>isteğe bağlı olarak</strong> e-posta adresi eklenebilir.</span></p>'),
        # bolum basliklari
        ('<h2>1. Toplanan Veriler</h2>', '<h2 data-i18n="prv.h2_1">1. Toplanan Veriler</h2>'),
        ('<h3>Site ziyaret analitiği (otomatik, her ziyarette)</h3>',
         '<h3 data-i18n="prv.h3_1a">Site ziyaret analitiği (otomatik, her ziyarette)</h3>'),
        ('<h3>Topluluk listesi (yalnızca siz kaydolursanız)</h3>',
         '<h3 data-i18n="prv.h3_1b">Topluluk listesi (yalnızca siz kaydolursanız)</h3>'),
        ('<h2>2. Çerez ve Yerel Depolama</h2>', '<h2 data-i18n="prv.h2_2">2. Çerez ve Yerel Depolama</h2>'),
        ('<h2>3. Üçüncü Taraf İçerikler</h2>', '<h2 data-i18n="prv.h2_3">3. Üçüncü Taraf İçerikler</h2>'),
        ('<h2>4. Verilerin Kullanımı</h2>', '<h2 data-i18n="prv.h2_4">4. Verilerin Kullanımı</h2>'),
        ('<h2>5. Saklama Süresi</h2>', '<h2 data-i18n="prv.h2_5">5. Saklama Süresi</h2>'),
        ('<h2>6. Haklarınız (KVKK / GDPR)</h2>', '<h2 data-i18n="prv.h2_6">6. Haklarınız (KVKK / GDPR)</h2>'),
        ('<h2>7. Üçüncü Taraf Servisler</h2>', '<h2 data-i18n="prv.h2_7">7. Üçüncü Taraf Servisler</h2>'),
        ('<h2>8. Değişiklikler</h2>', '<h2 data-i18n="prv.h2_8">8. Değişiklikler</h2>'),
        ('<h2>9. İletişim</h2>', '<h2 data-i18n="prv.h2_9">9. İletişim</h2>'),
        # paragraf icerikleri
        ('<p>Bu sitede <strong>çerez kullanılmaz</strong>,',
         '<p data-i18n="prv.p_1a">Bu sitede <strong>çerez kullanılmaz</strong>,'),
        ('<p>Toplanan veriler <strong>kendi sunucumuzda</strong>',
         '<p data-i18n="prv.p_1b">Toplanan veriler <strong>kendi sunucumuzda</strong>'),
        ('<p>Sayfada YouTube gömülü oynatıcılar bulunur. Bu gömülü içerikler',
         '<p data-i18n="prv.p_3">Sayfada YouTube gömülü oynatıcılar bulunur. Bu gömülü içerikler'),
        ('<p>KVKK (Madde 11) ve GDPR (Madde 15-21) kapsamında:</p>',
         '<p data-i18n="prv.p_6">KVKK (Madde 11) ve GDPR (Madde 15-21) kapsamında:</p>'),
        ('<p><strong>Nasıl başvurulur?</strong><br>',
         '<p data-i18n="prv.p_6b"><strong>Nasıl başvurulur?</strong><br>'),
        ('<p>Bu politika değişirse sayfadaki "Son güncelleme" tarihi güncellenir.',
         '<p data-i18n="prv.p_8">Bu politika değişirse sayfadaki "Son güncelleme" tarihi güncellenir.'),
        ('<p>Famous Music Studio · <a href="mailto:hello@famousmusicstudio.com">hello@famousmusicstudio.com</a><br>',
         '<p data-i18n="prv.p_9">Famous Music Studio · <a href="mailto:hello@famousmusicstudio.com">hello@famousmusicstudio.com</a><br>'),
        # tablo basliklari
        ('<th>Mekanizma</th>', '<th data-i18n="prv.th_2a">Mekanizma</th>'),
        ('<th>Kullanılıyor mu?</th>', '<th data-i18n="prv.th_2b">Kullanılıyor mu?</th>'),
        ('<th>Açıklama</th>', '<th data-i18n="prv.th_2c">Açıklama</th>'),
        ('<th>Servis</th>', '<th data-i18n="prv.th_7a">Servis</th>'),
        ('<th>Amaç</th>', '<th data-i18n="prv.th_7b">Amaç</th>'),
        ('<th>Kapsam</th>', '<th data-i18n="prv.th_7c">Kapsam</th>'),
        # liste ogeleri
        ('<li>Ziyaret zamanı</li>', '<li data-i18n="prv.li_1a">Ziyaret zamanı</li>'),
        ('<li>Sayfa yolu (URL sorgu dizesi hariç)</li>', '<li data-i18n="prv.li_1b">Sayfa yolu (URL sorgu dizesi hariç)</li>'),
        ('<li>Referrer site adresi</li>', '<li data-i18n="prv.li_1c">Referrer site adresi</li>'),
        ('<li>Cihaz tipi (masaüstü / mobil / tablet)</li>', '<li data-i18n="prv.li_1d">Cihaz tipi (masaüstü / mobil / tablet)</li>'),
        ('<li>Tarayıcı dili ve saat dilimi</li>', '<li data-i18n="prv.li_1e">Tarayıcı dili ve saat dilimi</li>'),
        ('<li>Kaba viewport boyutu</li>', '<li data-i18n="prv.li_1f">Kaba viewport boyutu</li>'),
        ('<li>E-posta adresi</li>', '<li data-i18n="prv.li_1g">E-posta adresi</li>'),
        ('<li>Kayıt zamanı ve kaynak (site / CLI)</li>', '<li data-i18n="prv.li_1h">Kayıt zamanı ve kaynak (site / CLI)</li>'),
        # tablo huceleri
        ('<td class="no">Hayır</td>', '<td class="no" data-i18n="prv.hayir">Hayır</td>'),
        ('<td class="yes">Evet</td>', '<td class="yes" data-i18n="prv.evet">Evet</td>'),
        # footer
        ('<a href="/">← Ana sayfa</a>', '<a href="/" data-i18n="prv.f_ana">← Ana sayfa</a>'),
        ('<a href="/epk">Press Kit</a>', '<a href="/epk" data-i18n="prv.f_epk">Press Kit</a>'),
    ]
    uygula(p, ciftler)

    # ======================================================== epk/bio.html
    print("epk/bio.html:")
    p2 = "site/epk/bio.html"
    ciftler2 = [
        ('<h1>Press Kit (EPK)</h1>', '<h1 data-i18n="epk.h1">Press Kit (EPK)</h1>'),
        ('<p>Medya, promosör ve işbirliği ortakları için kaynaklar</p>',
         '<p data-i18n="epk.sub">Medya, promosör ve işbirliği ortakları için kaynaklar</p>'),
        ('<h2>Kısa Biyografi</h2>', '<h2 data-i18n="epk.h2_bio">Kısa Biyografi</h2>'),
        ('<h2>Olgu Dosyası (Fact Sheet)</h2>', '<h2 data-i18n="epk.h2_fact">Olgu Dosyası (Fact Sheet)</h2>'),
        ('<h2>Öne Çıkan Parçalar</h2>', '<h2 data-i18n="epk.h2_tracks">Öne Çıkan Parçalar</h2>'),
        ('<h2>DJ Set Serisi (DJ Famous)</h2>', '<h2 data-i18n="epk.h2_dj">DJ Set Serisi (DJ Famous)</h2>'),
        ('<h2>Kaynak Dosyalar</h2>', '<h2 data-i18n="epk.h2_files">Kaynak Dosyalar</h2>'),
        ('<h2>İletişim</h2>', '<h2 data-i18n="epk.h2_contact">İletişim</h2>'),
        ('<p><strong>Famous Music Studio</strong>, Türkiye merkezli; yapay zekâ destekli',
         '<p data-i18n="epk.bio_p1"><strong>Famous Music Studio</strong>, Türkiye merkezli; yapay zekâ destekli'),
        ('müzik üretimine odaklanan bir müzik stüdyosudur. Türkçe Pop, R&amp;B, Trap,',
         '<span data-i18n="epk.bio_p2">müzik üretimine odaklanan bir müzik stüdyosudur. Türkçe Pop, R&amp;B, Trap,</span>'),
        ('Arabesk, Elektronik ve Melodic Techno türlerinde özgün parçalar ve DJ setleri',
         '<span data-i18n="epk.bio_p3">Arabesk, Elektronik ve Melodic Techno türlerinde özgün parçalar ve DJ setleri</span>'),
        ('üretir. İlk albümü <strong>Gece Masalları</strong> (2026) bu çeşitliliği',
         '<span data-i18n="epk.bio_p4">üretir. İlk albümü <strong>Gece Masalları</strong> (2026) bu çeşitliliği</span>'),
        ('bir araya getirir: nostaljik arabesk melodileri, modern trap prodüksiyonu ve',
         '<span data-i18n="epk.bio_p5">bir araya getirir: nostaljik arabesk melodileri, modern trap prodüksiyonu ve</span>'),
        ('sinematik melodic techno akışları aynı proje içinde buluşur.</p>',
         '<span data-i18n="epk.bio_p6">sinematik melodic techno akışları aynı proje içinde buluşur.</span></p>'),
        ('<p>Prodüksiyonda yapay zekâ araçları kullanılır; ancak her parçanın söz',
         '<p data-i18n="epk.bio_p7">Prodüksiyonda yapay zekâ araçları kullanılır; ancak her parçanın söz'),
        ('yazımı, tema kurgusu ve mix kararları stüdyo tarafından elden alınır.',
         '<span data-i18n="epk.bio_p8">yazımı, tema kurgusu ve mix kararları stüdyo tarafından elden alınır.</span>'),
        ('<p>Kanal haftalık yeni parça ve DJ setleriyle büyür; <em>DJ Famous</em>',
         '<p data-i18n="epk.bio_p9">Kanal haftalık yeni parça ve DJ setleriyle büyür; <em>DJ Famous</em>'),
        ('kimliğiyle Cuma geceleri yeni şehir konseptli setler yayımlar.</p>',
         '<span data-i18n="epk.bio_p10">kimliğiyle Cuma geceleri yeni şehir konseptli setler yayımlar.</span></p>'),
        # kart basliklari
        ('<h3>Biyografi & Olgu Dosyası</h3>', '<h3 data-i18n="epk.k_bio">Biyografi & Olgu Dosyası</h3>'),
        ('<p>Bu sayfadaki metin, <code>bio.md</code> ve <code>bio.json</code> dosyalarıyla aynıdır.</p>',
         '<p data-i18n="epk.k_bio_p">Bu sayfadaki metin, <code>bio.md</code> ve <code>bio.json</code> dosyalarıyla aynıdır.</p>'),
        ('<h3>Fotoğraf Rehberi</h3>', '<h3 data-i18n="epk.k_photo">Fotoğraf Rehberi</h3>'),
        ('<p>Çözünürlük, isimlendirme ve kullanım hakları rehberi.</p>',
         '<p data-i18n="epk.k_photo_p">Çözünürlük, isimlendirme ve kullanım hakları rehberi.</p>'),
        ('<h3>Müzik Varlıkları</h3>', '<h3 data-i18n="epk.k_music">Müzik Varlıkları</h3>'),
        ('<p>Stem, instrumental, MIDI ve lisans koşulları.</p>',
         '<p data-i18n="epk.k_music_p">Stem, instrumental, MIDI ve lisans koşulları.</p>'),
        ('<h3>Booking & İşbirliği</h3>', '<h3 data-i18n="epk.k_booking">Booking & İşbirliği</h3>'),
        ('<p>DJ booking, live performans, remix talebi, sync lisanslama.</p>',
         '<p data-i18n="epk.k_booking_p">DJ booking, live performans, remix talebi, sync lisanslama.</p>'),
        ('<h4>Not:</h4>', '<h4 data-i18n="epk.not_h">Not:</h4>'),
        ('<p>Basın görselleri ve ses dosyaları için',
         '<p data-i18n="epk.not_p">Basın görselleri ve ses dosyaları için'),
        ('adresine yazın. Talebe 48 saat içinde yanıt verilir.</p>',
         '<span data-i18n="epk.not_p2">adresine yazın. Talebe 48 saat içinde yanıt verilir.</span></p>'),
        # footer
        ('<a href="/">← Ana sayfa</a>', '<a href="/" data-i18n="epk.f_ana">← Ana sayfa</a>'),
        ('<a href="/privacy">Gizlilik</a>', '<a href="/privacy" data-i18n="epk.f_privacy">Gizlilik</a>'),
    ]
    uygula(p2, ciftler2)


if __name__ == "__main__":
    main()
