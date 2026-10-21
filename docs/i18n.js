/* Famous Music Studio — i18n (Madde 31)
 *
 * TR (varsayilan) / EN. Site `lang="tr"` ile baslar (hedef kitle TR).
 * Secim `localStorage`'da saklanir — bu bir KULLANICI TERCİHİdir, takip
 * değildir (Madde 28 analitik bu veriyi toplamaz).
 *
 * Kullanım:
 *   <span data-i18n="anahtar"></span>            -> textContent
 *   <input data-i18n-ph="anahtar">              -> placeholder
 *   <meta data-i18n-content="anahtar">          -> content
 *   data-i18n-attr="title:anahtar"              -> attribute
 */
(function () {
  'use strict';

  var DIL_VARSAYILAN = 'tr';
  var DIL_ANAHTAR = 'fms_dil';

  var S = {
    tr: {
      'epk.f_privacy': 'Gizlilik',
      'epk.f_ana': '← Ana sayfa',
      'epk.not_p2': 'adresine yazın. Talebe 48 saat içinde yanıt verilir.',
      'epk.not_p': 'Basın görselleri ve ses dosyaları için',
      'epk.not': 'Not:',
      'epk.k_booking_p': 'DJ booking, remix, sync lisans ve form şablonu.',
      'epk.k_booking': 'Booking &amp; İşbirliği',
      'epk.k_music_p': 'Stem, instrumental, MIDI ve lisans koşulları.',
      'epk.k_music': 'Müzik Varlıkları',
      'epk.k_photo_p': 'Çözünürlük, isimlendirme ve kullanım hakları rehberi.',
      'epk.k_photo': 'Fotoğraf Rehberi',
      'epk.k_bio_p': 'Bu sayfadaki metin, <code>bio.md</code> ve <code>bio.json</code> dosyalarıyla aynıdır.',
      'epk.k_bio': 'Biyografi &amp; Olgu Dosyası',
      'epk.bio_p10': 'kimliğiyle Cuma geceleri yeni şehir konseptli setler yayımlar.',
      'epk.bio_p9': 'Kanal haftalık yeni parça ve DJ setleriyle büyür; <em>DJ Famous</em>',
      'epk.bio_p8': 'yazımı, tema kurgusu ve mix kararları stüdyo tarafından elden alınır.',
      'epk.bio_p7': 'Prodüksiyonda yapay zekâ araçları kullanılır; ancak her parçanın söz',
      'epk.bio_p6': 'sinematik melodic techno akışları aynı proje içinde buluşur.',
      'epk.bio_p5': 'bir araya getirir: nostaljik arabesk melodileri, modern trap prodüksiyonu ve',
      'epk.bio_p4': 'üretir. İlk albümü <strong>Gece Masalları</strong> (2026) bu çeşitliliği',
      'epk.bio_p3': 'Arabesk, Elektronik ve Melodic Techno türlerinde özgün parçalar ve DJ setleri',
      'epk.bio_p2': 'müzik üretimine odaklanan bir müzik stüdyosudur. Türkçe Pop, R&amp;B, Trap,',
      'epk.bio_p1': '<strong>Famous Music Studio</strong>, Türkiye merkezli; yapay zekâ destekli',
      'epk.h2_contact': 'İletişim',
      'epk.h2_files': 'Kaynak Dosyalar',
      'epk.h2_dj': 'DJ Set Serisi (DJ Famous)',
      'epk.h2_tracks': 'Öne Çıkan Parçalar',
      'epk.h2_fact': 'Olgu Dosyası (Fact Sheet)',
      'epk.h2_bio': 'Kısa Biyografi',
      'epk.sub2': 'Famous Music Studio · Medya, promosör ve işbirliği için kaynaklar',
      'epk.sub': 'Medya, promosör ve işbirliği ortakları için kaynaklar',
      'epk.h1': 'Press Kit (EPK)',
      'prv.f_epk': 'Press Kit',
      'prv.f_ana': '← Ana sayfa',
      'prv.evet': 'Evet',
      'prv.hayir': 'Hayır',
      'prv.li_1h': 'Kayıt zamanı ve kaynak (site / CLI)',
      'prv.li_1g': 'E-posta adresi',
      'prv.li_1f': 'Kaba viewport boyutu',
      'prv.li_1e': 'Tarayıcı dili ve saat dilimi',
      'prv.li_1d': 'Cihaz tipi (masaüstü / mobil / tablet)',
      'prv.li_1c': 'Referrer site adresi',
      'prv.li_1b': 'Sayfa yolu (URL sorgu dizesi hariç)',
      'prv.li_1a': 'Ziyaret zamanı',
      'prv.th_7c': 'Kapsam',
      'prv.th_7b': 'Amaç',
      'prv.th_7a': 'Servis',
      'prv.th_2c': 'Açıklama',
      'prv.th_2b': 'Kullanılıyor mu?',
      'prv.th_2a': 'Mekanizma',
      'prv.p_9': 'Famous Music Studio · <a href="mailto:hello@famousmusicstudio.com">hello@famousmusicstudio.com</a><br>',
      'prv.p_8': 'Bu politika değişirse sayfadaki "Son güncelleme" tarihi güncellenir.',
      'prv.p_6b': '<strong>Nasıl başvurulur?</strong><br>',
      'prv.p_6': 'KVKK (Madde 11) ve GDPR (Madde 15-21) kapsamında:',
      'prv.p_3': 'Sayfada YouTube gömülü oynatıcılar bulunur. Bu gömülü içerikler',
      'prv.p_1b': 'Bu veriler <strong>kendi sunucumuzda</strong>',
      'prv.p_1a': 'Bu sitede <strong>çerez kullanılmaz</strong>,',
      'prv.h2_9': '9. İletişim',
      'prv.h2_8': '8. Değişiklikler',
      'prv.h2_7': '7. Üçüncü Taraf Servisler',
      'prv.h2_6': '6. Haklarınız (KVKK / GDPR)',
      'prv.h2_5': '5. Saklama Süresi',
      'prv.h2_4': '4. Verilerin Kullanımı',
      'prv.h2_3': '3. Üçüncü Taraf İçerikler',
      'prv.h2_2': '2. Çerez ve Yerel Depolama',
      'prv.h3_1b': 'Topluluk listesi (yalnızca siz kaydolursanız)',
      'prv.h3_1a': 'Site ziyaret analitiği (otomatik, her ziyarette)',
      'prv.h2_1': '1. Toplanan Veriler',
      'prv.ozet5': '<strong>isteğe bağlı olarak</strong> e-posta adresi eklenebilir.',
      'prv.ozet4': 'doğrudan tanımlayan hiçbir veri toplanmaz. Yalnızca topluluk listesine',
      'prv.ozet3': 've <strong>üçüncü taraf analitik yüklenmez</strong>. Ziyaretçileri',
      'prv.ozet2': '<strong>reklam takibi yapılmaz</strong>, <strong>fingerprint oluşturulmaz</strong>',
      'prv.ozet1': '<strong>Kısa özet:</strong> Bu sitede <strong>çerez kullanılmaz</strong>,',
      'prv.sub': 'Famous Music Studio · Son güncelleme: 21 Ekim 2026',
      'prv.h1': 'Gizlilik Politikası',
      'h404.epk': 'Press Kit',
      'h404.gizlilik': 'Gizlilik',
      'h404.youtube': 'YouTube kanalı',
      'h404.ana': 'Ana sayfa',
      'h404.p': 'Aradığınız sayfa taşınmış ya da hiç var olmamış olabilir. Aşağıdan devam edebilirsiniz.',
      'h404.h1': 'Bu sayfa bulunamadı',
      'topluluk.ntfu_red': 'Bildirim izni verilmedi. ntfy sayfasından abone olabilirsin.',
      'topluluk.ntfu_izin': 'Bildirim izni verildi! Abone olmak için ntfy sayfasını aç.',
      'topluluk.ntfy_alt': 'Tek tıkla, telefona push gelsin',
      'topluluk.ntfy': 'Anlık Bildirim',
      'hero.aria': 'Gece Masalları albümü önizlemesini çal',
      'news.aria': 'E-posta adresiniz',
      'topluluk.aria': 'E-posta adresiniz',
      'hero.etkilesim': 'Bir kez tıkla, ses açılsın',
      // --- meta ---
      'meta.title': 'Famous Music Studio — Türkiye’den Yapay Zekâ Destekli Müzik Üretimi',
      'meta.description': 'Famous Music Studio: Türkçe pop, R&B, trap, arabesk, melodik techno ve DJ setleri. Gece Masalları albümü, Night Drive serisi.',

      // --- hero ---
      'hero.tagline': 'Türkiye’den yapay zekâ destekli müzik üretimi.',
      'hero.album': 'Gece Masalları',
      'hero.album_suffix': 'albümü yayında.',
      'hero.badge': 'Yapay Zekâ Destekli Üretim',
      'hero.dinle': '▶ Gece Masalları’nı Dinle',
      'hero.dinle_devam': '▶ Devam Et',
      'hero.duraklat': '⏸ Duraklat',
      'hero.hata': '⚠ Önizleme yüklenemedi',
      'hero.ipucu': '30 sn önizleme · Tam albüm için streaming platformlarını ziyaret edin',
      'hero.kofi': 'Ko-fi ile Destek Ol',

      // --- tarz seçici ---
      'tarz.h2': 'Hangi Ruh Halindesin?',
      'tarz.lead': 'Bir tanesini seç — sana özel bir öneri hazırlayalım.',
      'tarz.dinle': 'Öneriyi Dinle',
      'tarz.caliyor': 'Çalıyor',
      'tarz.not': 'Dinleme otomatik başlamaz — sen istersen çalar.',
      'tarz.oneri': 'Ruh halin {tur} için önerimiz.',
      'tarz.playlist_ac': 'Playlist’i aç →',
      'tarz.yakin': 'Yakında',

      // --- müzik ---
      'muzik.h2': 'Son Çıkanlar',
      'muzik.tumu': 'Tümünü Gör →',
      'muzik.etiket': 'YouTube',

      // --- platformlar ---
      'platform.h2': 'Her Yerde Dinle',
      'platform.distrokid': 'DistroKid',
      'platform.distrokid_alt': 'Spotify · Apple · Deezer · Tümü',
      'platform.youtube': 'YouTube',
      'platform.youtube_alt': 'Müzik Videoları & DJ Setleri',
      'platform.tiktok': 'TikTok',
      'platform.tiktok_alt': 'Shorts & Kesitler',
      'platform.instagram': 'Instagram',
      'platform.instagram_alt': 'Reels & Sahne Arkası',

      // --- newsletter ---
      'news.h2': 'Duyurulardan Haberdar Ol',
      'news.lead': 'Yayınlanmamış demolar, DJ setlerine erken erişim ve prodüksiyon notları. Spam yok, sadece müzik.',
      'news.placeholder': 'e-posta adresiniz',
      'news.buton': 'Abone Ol',
      'news.abone': 'Abone oldunuz!',
      'news.hata': 'Şu an kaydedemiyoruz, sonra dene.',
      'news.onay_metni': 'Abone olarak yeni çıkanlardan haberdar olmayı kabul ediyorsunuz. İstediğiniz zaman abonelikten çıkabilirsiniz.',
      'news.gizlilik': 'Gizlilik',

      // --- topluluk ---
      'topluluk.h2': 'Topluluğa Katıl',
      'topluluk.discord': 'Discord',
      'topluluk.discord_alt': 'Sohbette, demo dinle, set iste',
      'topluluk.telegram': 'Telegram',
      'topluluk.telegram_alt': 'Yeni parça duyuruları, ilk çıkan',
      'topluluk.liste': 'Topluluk Listesi',
      'topluluk.liste_alt': 'E-posta ile haberdar ol',
      'topluluk.katil': 'Katıl',
      'topluluk.eklendi': 'Listeye eklendi! Haber vereceğiz.',
      'topluluk.hata': 'Şu an kaydedemiyoruz, sonra dene.',

      // --- destek ---
      'destek.h2': 'Stüdyoyu Destekle',
      'destek.p': 'Her kahve müziğin akmasını sağlar. Bana bir kahve al veya Ko-fi üyesi ol, özel ayrıcalıklara kavuş.',
      'destek.buton': 'Bana Bir Kahve Al',
      'destek.not': 'Ayrıca: DistroKid telif geliri · Suno yönlendirme kredisi · Otomasyon şablon satışı (yakında)',

      // --- EPK ---
      'epk.h2': 'Basın Kiti (EPK)',
      'epk.p': 'Medya, promosör ve işbirliği ortakları için kaynaklar.',
      'epk.bio': 'Biyografi & Olgu Dosyası',
      'epk.bio_alt': 'Sanatçı geçmişi, tür bilgisi, başarılar ve istatistikler.',
      'epk.bio_buton': 'MD İndir',
      'epk.foto': 'Basın Fotoğrafları',
      'epk.foto_alt': 'Yüksek çözünürlüklü basın fotoğrafları (dikey, yatay, logo varyantları).',
      'epk.foto_buton': 'Rehberi Aç',
      'epk.muzik': 'Müzik Varlıkları',
      'epk.muzik_alt': 'WAV/MP3 stem, instrumental sürümler, remixer için loop’lar.',
      'epk.muzik_buton': 'Rehberi Aç',
      'epk.booking': 'Booking & İşbirliği',
      'epk.booking_alt': 'DJ set, canlı performans, remix talebi, sync lisanslama.',
      'epk.booking_buton': 'Bize Ulaşın',

      // --- footer ---
      'footer.ana': 'Famous Music Studio © 2026 · Türkiye’den yapay zekâ destekli müzik üretimi',
      'footer.destek': 'Destek',
      'footer.iletisim': 'İletişim',
      'footer.epk': 'Basın Kiti',
      'footer.gizlilik': 'Gizlilik',

      // --- dil toggle ---
      'dil.etiket': 'Dil',
      'dil.tr': 'Türkçe',
      'dil.en': 'English',

      // --- tarz seçici tonuzları ---
      'tarz.gece.ad': 'Gece Sürüşü',
      'tarz.gece.ac': 'Melodic Techno & Night Drive mixleri',
      'tarz.arabesk.ad': 'Arabesk & Trap',
      'tarz.arabesk.ac': 'Türkçe arabesk, trap ve R&B',
      'tarz.djset.ad': 'DJ Set',
      'tarz.djset.ac': 'DJ Famous canlı setleri',
      'tarz.chill.ad': 'Chill',
      'tarz.chill.ac': 'Organic House & Deep Focus',
      'tarz.rock.ad': 'Rock',
      'tarz.rock.ac': 'Türkçe Rock & Alternative',
      'tarz.yeni.ad': 'Yeni Çıkanlar',
      'tarz.yeni.ac': 'Bu hafta yayınlananlar',
    },

    en: {
      'epk.f_privacy': 'Privacy',
      'epk.f_ana': '← Home',
      'epk.not_p2': 'email us. Requests are answered within 48 hours.',
      'epk.not_p': 'For press photos and audio files,',
      'epk.not': 'Note:',
      'epk.k_booking_p': 'DJ booking, remix, sync licence and form template.',
      'epk.k_booking': 'Booking &amp; Collabs',
      'epk.k_music_p': 'Stems, instrumentals, MIDI and licence terms.',
      'epk.k_music': 'Music Assets',
      'epk.k_photo_p': 'Resolution, naming and usage-rights guide.',
      'epk.k_photo': 'Photo Guide',
      'epk.k_bio_p': 'The text here matches the <code>bio.md</code> and <code>bio.json</code> files.',
      'epk.k_bio': 'Bio &amp; Fact Sheet',
      'epk.bio_p10': 'releases a new-city concept set every Friday night.',
      'epk.bio_p9': 'The channel grows with weekly new tracks and DJ sets; <em>DJ Famous</em>',
      'epk.bio_p8': 'thematic direction and mix decisions are made by hand in the studio.',
      'epk.bio_p7': 'AI tools are used in production, but every track\'s lyrics,',
      'epk.bio_p6': 'cinematic Melodic Techno flows meet in one project.',
      'epk.bio_p5': 'together: nostalgic Arabesk melodies, modern trap production and',
      'epk.bio_p4': 'Its debut album <strong>Gece Masalları</strong> (2026) brings this variety',
      'epk.bio_p3': 'Arabesk, Electronic and Melodic Techno — original tracks and DJ mixes.',
      'epk.bio_p2': 'AI-assisted music production studio focused on Turkish Pop, R&amp;B, Trap,',
      'epk.bio_p1': '<strong>Famous Music Studio</strong> is a Turkey-based,',
      'epk.h2_contact': 'Contact',
      'epk.h2_files': 'Source Files',
      'epk.h2_dj': 'DJ Set Series (DJ Famous)',
      'epk.h2_tracks': 'Featured Tracks',
      'epk.h2_fact': 'Fact Sheet',
      'epk.h2_bio': 'Short Biography',
      'epk.sub2': 'Famous Music Studio · Resources for media, promoters and collaborators',
      'epk.sub': 'Resources for media, promoters and collaborators',
      'epk.h1': 'Press Kit (EPK)',
      'prv.f_epk': 'Press Kit',
      'prv.f_ana': '← Home',
      'prv.evet': 'Yes',
      'prv.hayir': 'No',
      'prv.li_1h': 'Signup time and source (site / CLI)',
      'prv.li_1g': 'Email address',
      'prv.li_1f': 'Coarse viewport size',
      'prv.li_1e': 'Browser language and time zone',
      'prv.li_1d': 'Device type (desktop / mobile / tablet)',
      'prv.li_1c': 'Referrer site host',
      'prv.li_1b': 'Page path (URL query string excluded)',
      'prv.li_1a': 'Visit time',
      'prv.th_7c': 'Scope',
      'prv.th_7b': 'Purpose',
      'prv.th_7a': 'Service',
      'prv.th_2c': 'Notes',
      'prv.th_2b': 'Used?',
      'prv.th_2a': 'Mechanism',
      'prv.p_9': 'Famous Music Studio · <a href="mailto:hello@famousmusicstudio.com">hello@famousmusicstudio.com</a><br>',
      'prv.p_8': 'If this policy changes, the "last updated" date on this page is updated.',
      'prv.p_6b': '<strong>How to reach us?</strong><br>',
      'prv.p_6': 'Under GDPR (Articles 15-21) and KVKK (Article 11):',
      'prv.p_3': 'The page embeds YouTube players. These embedded players',
      'prv.p_1b': 'These data are stored <strong>on our own server</strong>',
      'prv.p_1a': 'No <strong>cookies</strong> are used on this site,',
      'prv.h2_9': '9. Contact',
      'prv.h2_8': '8. Changes',
      'prv.h2_7': '7. Third-Party Services',
      'prv.h2_6': '6. Your Rights (GDPR / KVKK)',
      'prv.h2_5': '5. Retention',
      'prv.h2_4': '4. How Data Is Used',
      'prv.h2_3': '3. Third-Party Content',
      'prv.h2_2': '2. Cookies and Local Storage',
      'prv.h3_1b': 'Community list (only if you sign up)',
      'prv.h3_1a': 'Site visit analytics (automatic, on every visit)',
      'prv.h2_1': '1. Data We Collect',
      'prv.ozet5': '<strong>optionally</strong> added to our community list.',
      'prv.ozet4': 'identifies visitors is collected. Only an email address,',
      'prv.ozet3': '<strong>no third-party analytics</strong>. No data that directly',
      'prv.ozet2': '<strong>no ad tracking</strong>, and <strong>no fingerprinting</strong>',
      'prv.ozet1': '<strong>In short:</strong> This site uses <strong>no cookies</strong>,',
      'prv.sub': 'Famous Music Studio · Last updated: October 21, 2026',
      'prv.h1': 'Privacy Policy',
      'h404.epk': 'Press Kit',
      'h404.gizlilik': 'Privacy',
      'h404.youtube': 'YouTube channel',
      'h404.ana': 'Home',
      'h404.p': 'The page you\'re looking for may have moved or never existed. Continue below.',
      'h404.h1': 'Page not found',
      'topluluk.ntfu_red': 'Notifications not allowed. You can subscribe on the ntfy page.',
      'topluluk.ntfu_izin': 'Notifications allowed! Open the ntfy page to subscribe.',
      'topluluk.ntfy_alt': 'One click, push to your phone',
      'topluluk.ntfy': 'Instant Alerts',
      'hero.aria': 'Play the Gece Masalları album preview',
      'news.aria': 'Your email address',
      'topluluk.aria': 'Your email address',
      'hero.etkilesim': 'Click once to enable sound',
      'meta.title': 'Famous Music Studio — AI-Assisted Music Production from Turkey',
      'meta.description': 'Famous Music Studio: Turkish Pop, R&B, trap, arabesk, melodic techno and DJ sets. Gece Masalları album, Night Drive series.',

      'hero.tagline': 'AI-assisted music production from Turkey.',
      'hero.album': 'Gece Masalları',
      'hero.album_suffix': 'album out now.',
      'hero.badge': 'AI-Assisted Production',
      'hero.dinle': '▶ Listen to Gece Masalları',
      'hero.dinle_devam': '▶ Continue',
      'hero.duraklat': '⏸ Pause',
      'hero.hata': '⚠ Preview could not be loaded',
      'hero.ipucu': '30 sec preview · Visit streaming platforms for the full album',
      'hero.kofi': 'Support on Ko-fi',

      'tarz.h2': 'What’s Your Mood?',
      'tarz.lead': 'Pick one — we’ll prepare a recommendation for you.',
      'tarz.dinle': 'Listen to Recommendation',
      'tarz.caliyor': 'Playing',
      'tarz.not': 'Playback doesn’t start automatically — it plays when you press play.',
      'tarz.oneri': 'For your {tur} mood, we recommend.',
      'tarz.playlist_ac': 'Open playlist →',
      'tarz.yakin': 'Coming soon',

      'muzik.h2': 'Latest Releases',
      'muzik.tumu': 'See all →',
      'muzik.etiket': 'YouTube',

      'platform.h2': 'Listen Everywhere',
      'platform.distrokid': 'DistroKid',
      'platform.distrokid_alt': 'Spotify · Apple · Deezer · All',
      'platform.youtube': 'YouTube',
      'platform.youtube_alt': 'Music Videos & DJ Sets',
      'platform.tiktok': 'TikTok',
      'platform.tiktok_alt': 'Shorts & Clips',
      'platform.instagram': 'Instagram',
      'platform.instagram_alt': 'Reels & Behind Scenes',

      'news.h2': 'Stay in the Loop',
      'news.lead': 'Unreleased demos, early access to DJ sets, and production insights. No spam, just music.',
      'news.placeholder': 'you@email.com',
      'news.buton': 'Subscribe',
      'news.abone': 'Subscribed!',
      'news.hata': 'We can’t save it right now, try again later.',
      'news.onay_metni': 'By subscribing you agree to receive emails from Famous Music Studio. Unsubscribe anytime.',
      'news.gizlilik': 'Privacy',

      'topluluk.h2': 'Join the Community',
      'topluluk.discord': 'Discord',
      'topluluk.discord_alt': 'Chat, hear demos, request sets',
      'topluluk.telegram': 'Telegram',
      'topluluk.telegram_alt': 'New track alerts, first listens',
      'topluluk.liste': 'Mailing List',
      'topluluk.liste_alt': 'Get notified by email',
      'topluluk.katil': 'Join',
      'topluluk.eklendi': 'Added to the list! We’ll keep you posted.',
      'topluluk.hata': 'We can’t save it right now, try again later.',

      'destek.h2': 'Support the Studio',
      'destek.p': 'Every coffee keeps the music flowing. Buy me a coffee or become a Ko-fi member for exclusive perks.',
      'destek.buton': 'Buy Me a Coffee',
      'destek.not': 'Also: DistroKid royalties · Suno referral credits · Automation template sales (coming soon)',

      'epk.h2': 'Press Kit (EPK)',
      'epk.p': 'Resources for media, promoters, and collaborators.',
      'epk.bio': 'Bio & Fact Sheet',
      'epk.bio_alt': 'Artist background, genre info, key achievements, and stats.',
      'epk.bio_buton': 'Download MD',
      'epk.foto': 'Press Photos',
      'epk.foto_alt': 'High-res press photos (portrait, landscape, logo variations).',
      'epk.foto_buton': 'View Guide',
      'epk.muzik': 'Music Assets',
      'epk.muzik_alt': 'WAV/MP3 stems, instrumental versions, loops for remixers.',
      'epk.muzik_buton': 'View Guide',
      'epk.booking': 'Booking & Collabs',
      'epk.booking_alt': 'DJ sets, live performances, remix requests, sync licensing.',
      'epk.booking_buton': 'Contact Us',

      'footer.ana': 'Famous Music Studio © 2026 · AI-assisted music production from Turkey',
      'footer.destek': 'Support',
      'footer.iletisim': 'Contact',
      'footer.epk': 'Press Kit',
      'footer.gizlilik': 'Privacy',

      'dil.etiket': 'Language',
      'dil.tr': 'Türkçe',
      'dil.en': 'English',

      'tarz.gece.ad': 'Night Drive',
      'tarz.gece.ac': 'Melodic Techno & Night Drive mixes',
      'tarz.arabesk.ad': 'Arabesk & Trap',
      'tarz.arabesk.ac': 'Turkish arabesk, trap and R&B',
      'tarz.djset.ad': 'DJ Set',
      'tarz.djset.ac': 'DJ Famous live mixes',
      'tarz.chill.ad': 'Chill',
      'tarz.chill.ac': 'Organic House & Deep Focus',
      'tarz.rock.ad': 'Rock',
      'tarz.rock.ac': 'Turkish Rock & Alternative',
      'tarz.yeni.ad': 'New Releases',
      'tarz.yeni.ac': 'Published this week',
    }
  };

  // ---------------------------------------------------------------- durum
  var aktifDil = DIL_VARSAYILAN;

  function dilOku() {
    try {
      var d = localStorage.getItem(DIL_ANAHTAR);
      if (d === 'tr' || d === 'en') return d;
      var nav = (navigator.language || '').slice(0, 2).toLowerCase();
      if (nav === 'en') return 'en';
    } catch (e) { /* localStorage yoksa varsayilan */ }
    return DIL_VARSAYILAN;
  }

  function dilYaz(d) {
    try { localStorage.setItem(DIL_ANAHTAR, d); } catch (e) { /* yoksay */ }
  }

  function metin(anahtar, d) {
    var tablo = S[d] || S[DIL_VARSAYILAN];
    return tablo[anahtar] !== undefined ? tablo[anahtar] : anahtar;
  }

  // ------------------------------------------------- guvenli HTML yazimi
  // SORUN (Madde 31): textContent kullanildiginda
  //   (a) degerdeki <strong>/<br>/<a> gibi etiketler EKRANDA metin olarak
  //       gorunuyordu,
  //   (b) `&amp;` gibi HTML entity'leri cozulmeyip literal kaliyordu.
  // COZUM: entity veya etiket iceren degerler icerik-temizlikten gecirilip
  // innerHTML ile yazilir. Tehlikeli etiketler, on* event attribute'leri ve
  // javascript: URL'leri silinir (defans katmani).
  var TEHLIKELI_ETIKET = new RegExp(
    '<\\s*\\/?\\s*(script|style|iframe|object|embed|link|meta|base|form|input|button|svg|math)\\b[^>]*>', 'gi');
  var OLAY_ATTR = new RegExp('\\s+on[a-z]+\\s*=\\s*("[^"]*"|\'[^\']*\'|[^\\s>]+)', 'gi');
  var TEHLIKELI_URL = new RegExp('(href|src)\\s*=\\s*("|\')\\s*javascript:[^"\']*\\2', 'gi');

  function htmlTemizle(v) {
    return String(v)
      .replace(TEHLIKELI_ETIKET, '')
      .replace(OLAY_ATTR, '')
      .replace(TEHLIKELI_URL, '');
  }

  function metinYaz(el, v) {
    if (!/[<&]/.test(v)) { el.textContent = v; return; }
    el.innerHTML = htmlTemizle(v);
  }

  // ---------------------------------------------------------------- uygula
  function uygula(d) {
    aktifDil = (d === 'en' || d === 'tr') ? d : DIL_VARSAYILAN;
    var tablo = S[aktifDil] || S[DIL_VARSAYILAN];

    // textContent / guvenli HTML
    document.querySelectorAll('[data-i18n]').forEach(function (el) {
      var v = tablo[el.getAttribute('data-i18n')];
      if (v !== undefined) metinYaz(el, v);
    });

    // placeholder
    document.querySelectorAll('[data-i18n-ph]').forEach(function (el) {
      var v = tablo[el.getAttribute('data-i18n-ph')];
      if (v !== undefined) el.setAttribute('placeholder', v);
    });

    // meta content
    document.querySelectorAll('[data-i18n-content]').forEach(function (el) {
      var v = tablo[el.getAttribute('data-i18n-content')];
      if (v !== undefined) el.setAttribute('content', v);
    });

    // attribute: "attr:key"
    document.querySelectorAll('[data-i18n-attr]').forEach(function (el) {
      el.getAttribute('data-i18n-attr').split('|').forEach(function (parca) {
        var p = parca.split(':');
        if (p.length < 2) return;
        var v = tablo[p[1].trim()];
        if (v !== undefined) el.setAttribute(p[0].trim(), v);
      });
    });

    // html lang
    document.documentElement.setAttribute('lang', aktifDil);

    // toggle butonlari
    document.querySelectorAll('[data-dil-btn]').forEach(function (b) {
      var aktif = b.getAttribute('data-dil-btn') === aktifDil;
      b.setAttribute('aria-pressed', aktif ? 'true' : 'false');
      b.classList.toggle('aktif', aktif);
    });

    // olaylar (dinamik metinler)
    document.dispatchEvent(new CustomEvent('dil:degisti', { detail: { dil: aktifDil } }));
  }

  // ---------------------------------------------------------------- toggle
  function dugmeyeBagla() {
    document.querySelectorAll('[data-dil-btn]').forEach(function (b) {
      b.addEventListener('click', function () {
        var d = b.getAttribute('data-dil-btn');
        dilYaz(d);
        uygula(d);
      });
    });
  }

  // ---------------------------------------------------------------- baslat
  function baslat() {
    dugmeyeBagla();
    uygula(dilOku());
  }

  // DIŞA AÇIK API — `baslat()` ÇAĞRILMADAN ÖNCE atanmalı.
  // NEDEN (2026-10-21): `uygula()` sonunda 'dil:degisti' olayı yoluyor;
  // index.html'in dinleyicisi bu olayda `T()` ile DİNAMİK metinleri
  // (hero butonu, tarz secici) yeniliyor. API atanmazsa `T()` fallback'e
  // dusuyor ve butona anahtar adi ("hero.dinle") yaziliyordu.
  window.FMS_I18N = {
    metin: metin,
    uygula: uygula,
    dil: function () { return aktifDil; },
    setDil: function (d) { dilYaz(d); uygula(d); }
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', baslat);
  } else {
    baslat();
  }
})();
