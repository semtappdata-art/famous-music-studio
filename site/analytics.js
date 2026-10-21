/* Famous Music Studio — Site Analitik İstemcisi (Madde 28)
 *
 * COOKIE-LESS · PII-YOK · FIRST-PARTY
 * - localStorage / cookie YOK
 * - fingerprint YOK
 * - IP kaydedilmez
 *
 * Yapılandırma (config.py ile eşleşir):
 *   ANALITIK_SAGLAYICI = "self_hosted" | "plausible" | "umami" | "yok"
 *   ANALITIK_UYGULAMA_ADI, ANALYTIK_PLAUSIBLE_DOMAIN, ANALYTIK_UMAMI_SCRIPT
 *
 * Bu dosya `site/index.html` tarafından `<script src="analytics.js" defer>`
 * ile yuklenir. Sunucu tarafi: site/api/analytics.py
 */
(function () {
  'use strict';

  var SAGLAYICI = 'self_hosted';
  var UYGULAMA = 'famous-music-studio';
  var PLAUSIBLE_DOMAIN = 'famousmusicstudio.com';
  var UMAMI_SCRIPT = '';
  var ENDPOINT = ((window.FMS_API_BASE || '') + '/api/analytics');
  var ETIKET = 'fms-site';

  // ---- Yonlendirmede sayfa gorunumu (SPA degil, ama geri/ileri butonu) ----
  var gonderildi = false;

  function cihazTipi() {
    var w = window.innerWidth || 0;
    var ua = navigator.userAgent || '';
    if (/iPad|Tablet/i.test(ua) || (w > 640 && /Android/i.test(ua) && !/Mobile/i.test(ua))) return 'tablet';
    if (w <= 640 || /Mobile|Android|iPhone/i.test(ua)) return 'mobil';
    return 'masaustu';
  }

  function dil() {
    return (navigator.language || 'tr').slice(0, 5);
  }

  function referrerHost() {
    try {
      if (!document.referrer) return '-';
      if (document.referrer.indexOf(location.origin) === 0) return '(site)';
      return new URL(document.referrer).host;
    } catch (e) {
      return '-';
    }
  }

  function olustur() {
    // Netlify JS fonksiyonu kendi cihaz tipini hesaplar; burada ham
    // verileri gonderiyoruz (path, ref, ua, vw, lang, tz, vp).
    return {
      path: location.pathname,
      ref: referrerHost(),
      ua: navigator.userAgent || '',
      vw: window.innerWidth || 0,
      lang: dil(),
      tz: (Intl.DateTimeFormat().resolvedOptions().timeZone || 'bilinmiyor'),
      vp: (window.innerWidth || 0) + 'x' + (window.innerHeight || 0),
      app: UYGULAMA
    };
  }

  function gonder() {
    if (gonderildi) return;
    gonderildi = true;
    var veri = JSON.stringify(olustur());
    try {
      // NOT: `text/plain` bilerek secildi — "simple" content type oldugu icin
      // tarayici PREFLIGHT (OPTIONS) yapmaz. `application/json` preflight
      // tetikler, sendBeacon credentials:'include' ile gonderir ve
      // sunucu `Access-Control-Allow-Origin: *` verirse CORS reddedilir.
      // credentials:'omit' + text/plain = preflight yok, CORS basit, PII yok.
      if (navigator.sendBeacon && navigator.sendBeaconSupported) {
        var ok = navigator.sendBeacon(ENDPOINT, new Blob([veri], { type: 'text/plain;charset=UTF-8' }));
        if (ok) return;
      }
      fetch(ENDPOINT, {
        method: 'POST',
        body: veri,
        headers: { 'Content-Type': 'text/plain;charset=UTF-8' },
        credentials: 'omit',
        keepalive: true,
        mode: 'cors'
      }).catch(function () {});
    } catch (e) { /* sessiz — analitik asla sayfayi bozmasin */ }
  }

  function plausibleYukle() {
    var s = document.createElement('script');
    s.defer = true;
    s.setAttribute('data-domain', PLAUSIBLE_DOMAIN);
    s.src = 'https://plausible.io/js/script.js';
    document.head.appendChild(s);
  }

  function umamiYukle() {
    if (!UMAMI_SCRIPT) return;
    var s = document.createElement('script');
    s.defer = true;
    s.src = UMAMI_SCRIPT;
    s.setAttribute('data-website-id', ETIKET);
    document.head.appendChild(s);
  }

  function baslat() {
    if (SAGLAYICI === 'yok') return;
    if (SAGLAYICI === 'plausible') { plausibleYukle(); return; }
    if (SAGLAYICI === 'umami') { umamiYukle(); return; }
    // self_hosted (varsayilan)
    gonder();
    window.addEventListener('popstate', function () { gonderildi = false; gonder(); });
    window.addEventListener('pageshow', function () { gonderildi = false; gonder(); });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', baslat);
  } else {
    baslat();
  }
})();
