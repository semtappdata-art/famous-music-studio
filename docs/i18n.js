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

  // ---------------------------------------------------------------- uygula
  function uygula(d) {
    aktifDil = (d === 'en' || d === 'tr') ? d : DIL_VARSAYILAN;
    var tablo = S[aktifDil] || S[DIL_VARSAYILAN];

    // textContent
    document.querySelectorAll('[data-i18n]').forEach(function (el) {
      var v = tablo[el.getAttribute('data-i18n')];
      if (v !== undefined) el.textContent = v;
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
