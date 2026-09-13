// Suno A/B olcum motoru - INDIRMEDEN karsilastirir.
//
// NEDEN VAR: Suno'nun indirme kotasi "Unlock & Download" tikinda dusuyor
// (sayac 27 -> 26 tam o anda degisti), CALMA bedava. 2026-09-12'de iki
// alternatifi karsilastirmak icin ikisi de indirildi ve 2 kilit bosa gitti.
// Bu dosya o hatanin tekrarlanmamasi icin.
//
// NEDEN WEB AUDIO, NEDEN BAYT DEGIL: Suno oynaticisi sesi MediaSource ile
// besliyor, yani <audio>.src bir blob: URL ama arkasinda Blob YOK -
// fetch(blobUrl) "Failed to fetch" verir. CDN'e dogrudan fetch de CORS'a
// takilir (cdn1/cdn2/cdn-o hepsi denendi). Geriye kalan tek yol: sesi
// calarken AudioContext grafigine baglayip gercek ornekleri olcmek.
//
// SESSIZ CALISIR: olcum gain dugumunden ONCE aliniyor, gain 0 -> hoparlorden
// ses cikmaz ama toplayici gercek dalga formunu gorur.
//
// DOGRULANDI (2026-09-12, Sabah Senin A/B): ayni iki parca hem bu yontemle
// hem indirilmis WAV'dan ffmpeg+numpy ile olculdu. Kapanistaki dususun
// basladigi an IKISINDE DE 269,75 sn cikti ve kazanan ayni. Mutlak RMS
// degerleri ~%20 farkli (akis kod cozumu ile WAV farki + pencereleme) - bu
// yuzden esikler MUTLAK degere degil, iki varyant ARASINDAKI ORANA bakmali.
//
// GIZLI SEKME (2026-09-13): ilk surum ornekleri ana is parcaciginda bir
// ZAMANLAYICI ile (40 ms'de bir analizor okumasi) topluyordu. Sekme arka
// planda kalinca tarayici zamanlayicilari kisitliyor: B varyantinda 14 sn'de
// 15 ornek toplandi, olcum gecersizdi. Artik ornekler SES IS PARCACIGINDA
// toplaniyor: once AudioWorklet (blob: modulu), olmazsa ScriptProcessor
// yedegi. Ikisinde de her ~43 ms'lik blok (2048 kare) kayit oluyor ve
// pencere suresi duvar saatiyle degil TOPLANAN KARE SAYISIYLA olculuyor.
// Bekleme adimlari da zamanlayici degil olay ('seeked', 'ended') bekliyor.
//
// KULLANIM (Chrome'da suno.com/create acikken, bir parca CALARKEN):
//   1. Asagidaki kodu yapistir -> motor kurulur (bir kez yeter)
//   2. await kur()  -> grafigi baglar, hangi toplayicinin kuruldugunu soyler
//   3. Her varyant icin: satirina tikla (calmaya bassin), sonra await olc(ad)
//      Nakaratin geldigi ani kulakla biliyorsan: olc(ad, {nakarat_sn: 42})
//      ya da dinlerken nakarat basladigi an isaretle(ad)
//   4. karsilastir() -> ozet + varyant_farki
//   5. SADECE kazanani indir.
//
// Node testi icin saf hesap fonksiyonlari en altta module.exports ile
// disari veriliyor (tests/test_suno_ab_olcum_js.py). Tarayicida module yok,
// o satir calismaz.

var _G = (typeof window !== 'undefined') ? window : globalThis;
_G.__ab = _G.__ab || {};

// Ornek tepe esigi: -0,1 dBFS. Akis kod cozumu tepeyi yuvarladigi icin bu
// kesin true-peak olcumu DEGIL; iki varyant arasinda siralama icin.
var KIRPILMA_ESIK = Math.pow(10, -0.1 / 20);
var NAKARAT_PENCERE_SN = 60;
var BLOK_KARE = 2048;

// ---------------------------------------------------------------------------
// SAF HESAPLAR (Web Audio'ya dokunmaz; Node'da test ediliyor)
// Kayit satiri: [t_sn, mid_rms, yan_rms, tepe_mutlak]. Eski 14 sn'lik
// kayitlarda tepe yok ([t, mid, yan]); fonksiyonlar buna dayanikli.
// ---------------------------------------------------------------------------

// Ardisik kirpilma: |ornek| >= esik olan EN AZ 2 ardisik ornek bir olay.
// Tek bir tepe ornegi kirpilma degil (normal bir tepe de esige degebilir).
// durum bloklar arasinda tasinir: bir dizi blok sinirinda kopmaz.
function kirpilmaSay(ornekler, esik, durum) {
  var d = durum || { akis: 0, olay: 0, ornek: 0, en_uzun: 0 };
  var e = (esik == null) ? KIRPILMA_ESIK : esik;
  for (var i = 0; i < ornekler.length; i++) {
    if (Math.abs(ornekler[i]) >= e) {
      d.akis++;
      if (d.akis > d.en_uzun) d.en_uzun = d.akis;
    } else if (d.akis) {
      if (d.akis >= 2) { d.olay++; d.ornek += d.akis; }
      d.akis = 0;
    }
  }
  return d;
}

function kirpilmaBitir(d) {
  if (!d) return { olay: 0, ornek: 0, en_uzun: 0 };
  if (d.akis >= 2) { d.olay++; d.ornek += d.akis; }
  d.akis = 0;
  return { olay: d.olay, ornek: d.ornek, en_uzun: d.en_uzun };
}

function _seviye2(x) { return x[1] * x[1] + (x[2] || 0) * (x[2] || 0); }

// Kayitlari `kova` sn'lik kovalara boler: [[kova_basi, rms], ...] (zaman sirali).
function _kovala(kayit, kova, kare) {
  var m = new Map();
  for (var i = 0; i < kayit.length; i++) {
    var k = Math.floor(kayit[i][0] / kova + 1e-9) * kova;
    k = +k.toFixed(3);
    if (!m.has(k)) m.set(k, []);
    m.get(k).push(kare(kayit[i]));
  }
  return Array.from(m.entries()).sort(function (a, b) { return a[0] - b[0]; })
    .map(function (e) {
      var s = 0;
      for (var j = 0; j < e[1].length; j++) s += e[1][j];
      return [e[0], Math.sqrt(s / e[1].length)];
    });
}

function _ortanca(dizi) {
  if (!dizi.length) return null;
  var s = dizi.slice().sort(function (a, b) { return a - b; });
  return s[Math.floor(s.length / 2)];
}

// NAKARAT (enerji vekili): ilk 60 sn 0,5 sn'lik kovalara bolunur. Referans =
// en yuksek %20 kovanin ortancasi ("tepe ortancasi"; tek bir sivri tepeye
// dayanmasin diye). Seviyesi referansin %70'ini ARDISIK 3 kova (1,5 sn)
// boyunca asan ILK kovanin basi donulur. Sozun kendisini bilmez: "sarkinin
// ilk kez tam enerjiye ciktigi an"dir; genelde nakarat, bazen yuksek bir
// Pre-Chorus. Kullanici isareti varsa o oncelikli (ozetle).
function nakaratTespit(kayit, secenek) {
  var s = secenek || {};
  var kova = s.kova || 0.5, oran = s.oran || 0.7, surekli = s.surekli || 3;
  var bitis = (s.bitis == null) ? NAKARAT_PENCERE_SN : s.bitis;
  if (!kayit || !kayit.length) return null;
  var k = _kovala(kayit.filter(function (x) { return x[0] < bitis; }), kova, _seviye2);
  if (k.length < surekli) return null;
  var degerler = k.map(function (x) { return x[1]; }).sort(function (a, b) { return a - b; });
  var ust = degerler.slice(Math.floor(degerler.length * 0.8));
  var ref = ust[Math.floor(ust.length / 2)];
  if (!(ref > 0)) return null;
  for (var i = 0; i + surekli <= k.length; i++) {
    var tamam = true;
    for (var j = 0; j < surekli; j++) {
      if (k[i + j][1] < ref * oran) { tamam = false; break; }
    }
    if (tamam) return +k[i][0].toFixed(2);
  }
  return null;
}

// DINAMIK: 1 sn'lik pencerelerde 20*log10(tepe / rms) ortancasi (dB).
// ~6 dB ve alti ezilmis mix; varyantlar arasi 3 dB'yi asan fark anlamli.
function crestDb(kayit, pencere) {
  var p = pencere || 1;
  var kovalar = new Map();
  for (var i = 0; i < (kayit || []).length; i++) {
    var x = kayit[i];
    if (x.length < 4 || x[3] == null) continue;
    var k = Math.floor(x[0] / p + 1e-9);
    if (!kovalar.has(k)) kovalar.set(k, { tepe: 0, s: 0, n: 0 });
    var o = kovalar.get(k);
    if (x[3] > o.tepe) o.tepe = x[3];
    o.s += _seviye2(x); o.n++;
  }
  var crestler = [];
  kovalar.forEach(function (o) {
    var rms = Math.sqrt(o.s / o.n);
    if (o.tepe > 0 && rms > 0) crestler.push(20 * Math.log10(o.tepe / rms));
  });
  var m = _ortanca(crestler);
  return (m == null) ? null : +m.toFixed(2);
}

// SONDAKI SESSIZLIK: son penceredeki en yuksek seviyenin %2'sini asan SON
// kayittan parcanin sonuna kadar gecen sure. 2 sn'den uzunsa bos kuyruk var.
function sonSessizlik(kayit, sure, oran) {
  var o = (oran == null) ? 0.02 : oran;
  if (!kayit || !kayit.length || !(sure > 0)) return null;
  var tp = 0, i;
  for (i = 0; i < kayit.length; i++) tp = Math.max(tp, Math.sqrt(_seviye2(kayit[i])));
  if (!(tp > 0)) return null;
  var sonGur = null;
  for (i = 0; i < kayit.length; i++) {
    if (Math.sqrt(_seviye2(kayit[i])) >= tp * o) sonGur = kayit[i][0];
  }
  if (sonGur == null) return null;
  return +Math.max(0, sure - sonGur).toFixed(2);
}

// ERKEN SONME: parcanin %40 ve %80 noktalarinda 2'ser sn olculen seviye.
// %80'deki, %40'takinin yarisindan azsa sarki erken soner.
function erkenSonme(noktalar) {
  if (!noktalar || !(noktalar[40] > 0) || noktalar[80] == null) return null;
  var oran = noktalar[80] / noktalar[40];
  return { oran: +oran.toFixed(3), erken_sonme: oran < 0.5,
           n40: noktalar[40], n60: (noktalar[60] == null ? null : noktalar[60]), n80: noktalar[80] };
}

// VARYANT FARKI: ortak olculerin olceklenmis farklari. Her olcut icin 1,0 =
// "anlamli fark" esigi: MY_ortanca %20 goreli, nakarat 15 sn, crest 3 dB,
// sure 60 sn, son sessizlik 2 sn. Hicbiri 1'e ulasmiyorsa karar
// "esit_dinleyerek_sec": olcum esit diyorsa kazanan UYDURULMAZ, kulak secer.
var FARK_OLCEKLERI = { MY_ortanca: 'goreli', nakarat_sn: 15, crest_db: 3, sure: 60, son_sessizlik_sn: 2 };

function varyantFarki(a, b) {
  var farklar = {}, toplam = 0, n = 0, enBuyuk = 0;
  Object.keys(FARK_OLCEKLERI).forEach(function (anahtar) {
    var x = a ? a[anahtar] : null, y = b ? b[anahtar] : null;
    if (typeof x !== 'number' || typeof y !== 'number') return;
    var olcek = FARK_OLCEKLERI[anahtar];
    var olcekli = (olcek === 'goreli')
      ? Math.abs(y - x) / Math.max(Math.abs(x), Math.abs(y), 1e-9) / 0.2
      : Math.abs(y - x) / olcek;
    farklar[anahtar] = { a: x, b: y, fark: +(y - x).toFixed(2), olcekli: +olcekli.toFixed(2) };
    toplam += olcekli; n++;
    if (olcekli > enBuyuk) enBuyuk = olcekli;
  });
  return {
    skor: n ? +(toplam / n).toFixed(2) : 0,
    karar: (enBuyuk >= 1) ? 'belirgin' : 'esit_dinleyerek_sec',
    farklar: farklar,
  };
}

function _noktaSeviyesi(kayit) {
  if (!kayit || !kayit.length) return null;
  var s = 0;
  for (var i = 0; i < kayit.length; i++) s += _seviye2(kayit[i]);
  return Math.sqrt(s / kayit.length);
}

function ozetle(r) {
  var bas14 = (r.bas || []).filter(function (x) { return x[0] < 14; });
  var kov = new Map();
  bas14.forEach(function (x) {
    var k = Math.floor(x[0] * 2) / 2;
    if (!kov.has(k)) kov.set(k, []);
    kov.get(k).push([x[1], x[2]]);
  });
  var oranlar = Array.from(kov.entries()).sort(function (a, b) { return a[0] - b[0]; })
    .filter(function (e) { return e[0] >= 3; })          // ilk 3 sn acilis gecisi, disarida
    .map(function (e) {
      var v = e[1], nn = v.length, mm = 0, yy = 0;
      for (var i = 0; i < nn; i++) { mm += v[i][0] * v[i][0]; yy += v[i][1] * v[i][1]; }
      return Math.sqrt(mm / nn) / (Math.sqrt(yy / nn) + 1e-9);
    });
  var tepeBas = 0;
  bas14.forEach(function (x) { tepeBas = Math.max(tepeBas, x[1]); });
  var ilkSes = bas14.find(function (x) { return x[1] > tepeBas * 0.02; });

  var k2 = new Map();
  (r.son || []).forEach(function (x) {
    var k = Math.floor(x[0] * 4) / 4;
    if (!k2.has(k)) k2.set(k, []);
    k2.get(k).push(x[1]);
  });
  var ku = Array.from(k2.entries()).sort(function (a, b) { return a[0] - b[0]; })
    .map(function (e) {
      var s = 0;
      for (var i = 0; i < e[1].length; i++) s += e[1][i] * e[1][i];
      return [e[0], Math.sqrt(s / e[1].length)];
    });
  var tp = 0;
  ku.forEach(function (x) { tp = Math.max(tp, x[1]); });
  var dusus = ku.find(function (x) { return x[1] < tp * 0.75; });
  var sirali = oranlar.slice().sort(function (a, b) { return a - b; });

  var nakaratSn = null, nakaratYontem = null;
  if (typeof r.nakarat_isaret === 'number') {
    nakaratSn = r.nakarat_isaret; nakaratYontem = 'isaret';
  } else {
    nakaratSn = nakaratTespit(r.bas || []);
    if (nakaratSn != null) nakaratYontem = 'enerji';
  }

  var tepeMutlak = null;
  [r.bas, r.son].concat(r.noktalar ? [r.noktalar[40], r.noktalar[60], r.noktalar[80]] : [])
    .forEach(function (kayit) {
      (kayit || []).forEach(function (x) {
        if (x.length >= 4 && x[3] != null) tepeMutlak = Math.max(tepeMutlak || 0, x[3]);
      });
    });

  var sonme = r.noktalar ? erkenSonme({
    40: _noktaSeviyesi(r.noktalar[40]),
    60: _noktaSeviyesi(r.noktalar[60]),
    80: _noktaSeviyesi(r.noktalar[80]),
  }) : null;

  return {
    sure: +(+r.sure).toFixed(1),
    sure_asimi: r.sure > 240,
    ilk_ses_sn: ilkSes ? ilkSes[0] : null,
    MY_ortanca: sirali.length ? +sirali[Math.floor(sirali.length / 2)].toFixed(2) : null,
    MY_max: sirali.length ? +Math.max.apply(null, oranlar).toFixed(2) : null,
    sustain_sn: (dusus && ku.length) ? +(dusus[0] - ku[0][0]).toFixed(2) : null,
    son_tepe_orani: (ku.length && tp > 0) ? +(ku[ku.length - 1][1] / tp).toFixed(3) : null,
    nakarat_sn: nakaratSn,
    nakarat_yontem: nakaratYontem,
    tepe_dbfs: (tepeMutlak > 0) ? +(20 * Math.log10(tepeMutlak)).toFixed(1) : null,
    kirpilma_olay: r.kirpilma ? r.kirpilma.olay : null,
    kirpilma_ornek: r.kirpilma ? r.kirpilma.ornek : null,
    kirpilma_en_uzun: r.kirpilma ? r.kirpilma.en_uzun : null,
    crest_db: crestDb(r.bas || []),
    son_sessizlik_sn: sonSessizlik(r.son || [], r.sure),
    erken_sonme: sonme ? sonme.erken_sonme : null,
    erken_sonme_orani: sonme ? sonme.oran : null,
  };
}

// Eski ad (2026-09-12 surumu) - geriye uyumluluk.
function _ozet(r) { return ozetle(r); }

// ---------------------------------------------------------------------------
// TARAYICI TARAFI
// ---------------------------------------------------------------------------

// AudioWorklet islemcisi: 2048 karelik L/R bloklarini ana is parcacigina
// aktarir (kopyasiz transfer). Hesap ana tarafta, ScriptProcessor yedegiyle
// AYNI kod yolunda (_blokIsle) yapiliyor ki iki yontem ayni sayilari versin.
var _ISLEMCI_KODU = [
  'class AbToplayici extends AudioWorkletProcessor {',
  '  constructor() { super(); this.N = ' + BLOK_KARE + '; this.L = new Float32Array(this.N); this.R = new Float32Array(this.N); this.i = 0; }',
  '  process(girdiler) {',
  '    const g = girdiler[0];',
  '    if (g && g.length) {',
  '      const l = g[0], r = g[1] || g[0];',
  '      for (let k = 0; k < l.length; k++) {',
  '        this.L[this.i] = l[k]; this.R[this.i] = r[k]; this.i++;',
  '        if (this.i === this.N) {',
  '          this.port.postMessage({ L: this.L, R: this.R }, [this.L.buffer, this.R.buffer]);',
  '          this.L = new Float32Array(this.N); this.R = new Float32Array(this.N); this.i = 0;',
  '        }',
  '      }',
  '    }',
  '    return true;',
  '  }',
  '}',
  "registerProcessor('ab-toplayici', AbToplayici);",
].join(String.fromCharCode(10));

function _blokIsle(L, R) {
  var A = _G.__ab, T = A.toplayici;
  if (!T) return;
  var n = L.length, m = 0, y = 0, tepe = 0;
  for (var i = 0; i < n; i++) {
    var mm = (L[i] + R[i]) / 2, yy = (L[i] - R[i]) / 2;
    m += mm * mm; y += yy * yy;
    var a = Math.abs(L[i]), b = Math.abs(R[i]);
    if (a > tepe) tepe = a;
    if (b > tepe) tepe = b;
  }
  A.kirpL = kirpilmaSay(L, KIRPILMA_ESIK, A.kirpL);
  A.kirpR = kirpilmaSay(R, KIRPILMA_ESIK, A.kirpR);
  T.kayit.push([+A.el.currentTime.toFixed(3), +Math.sqrt(m / n).toFixed(5),
                +Math.sqrt(y / n).toFixed(5), +tepe.toFixed(5)]);
  T.kare += n;
  if (T.kare >= T.hedef) T.bitir();
}

async function kur() {
  var A = _G.__ab;
  if (A.kurulu) return 'zaten kurulu (' + A.yontem + ')';
  var el = Array.from(document.querySelectorAll('audio'))
    .find(function (e) { return (e.currentSrc || '').startsWith('blob:'); });
  if (!el) throw new Error('calan audio elementi yok - once bir parcaya tikla');
  var ctx = new (window.AudioContext || window.webkitAudioContext)();
  var src = ctx.createMediaElementSource(el);
  var g = ctx.createGain(); g.gain.value = 0;   // sessiz
  g.connect(ctx.destination);
  var dugum, yontem;
  try {
    if (!ctx.audioWorklet) throw new Error('audioWorklet yok');
    var url = URL.createObjectURL(new Blob([_ISLEMCI_KODU], { type: 'application/javascript' }));
    await ctx.audioWorklet.addModule(url);
    dugum = new AudioWorkletNode(ctx, 'ab-toplayici', {
      numberOfInputs: 1, numberOfOutputs: 1, outputChannelCount: [2],
      channelCount: 2, channelCountMode: 'explicit',
    });
    dugum.port.onmessage = function (e) { _blokIsle(e.data.L, e.data.R); };
    yontem = 'AudioWorklet';
  } catch (hata) {
    // Sayfanin CSP'si blob: modulunu engelleyebilir; 2026-09-13'te Suno'da
    // calisan yol ScriptProcessor'du.
    dugum = ctx.createScriptProcessor(BLOK_KARE, 2, 2);
    dugum.onaudioprocess = function (e) {
      var ib = e.inputBuffer;
      _blokIsle(ib.getChannelData(0), ib.numberOfChannels > 1 ? ib.getChannelData(1) : ib.getChannelData(0));
    };
    yontem = 'ScriptProcessor (yedek: ' + (hata && hata.message) + ')';
  }
  src.connect(dugum); dugum.connect(g);
  if (ctx.state === 'suspended') await ctx.resume();
  Object.assign(A, { kurulu: true, el: el, ctx: ctx, src: src, g: g, dugum: dugum, yontem: yontem,
                     sonuc: A.sonuc || {}, isaretler: A.isaretler || {}, toplayici: null });
  return 'kuruldu: ' + yontem + ', sampleRate=' + ctx.sampleRate;
}

// Olay bekler (zamanlayici yok): 'seeked' gelince ya da zaten oradaysa.
function _atla(t) {
  var el = _G.__ab.el;
  return new Promise(function (res) {
    if (Math.abs(el.currentTime - t) < 0.05 && !el.seeking) return res();
    el.addEventListener('seeked', function () { res(); }, { once: true });
    el.currentTime = t;
  });
}

// `sure` sn'lik ses toplar. Bitis KARE SAYISIYLA (ses saati); parca biterse
// ya da duraklatilirsa elde olanla doner.
function _topla(sure) {
  var A = _G.__ab;
  return new Promise(function (res) {
    var T = { kayit: [], kare: 0, hedef: Math.max(1, Math.round(sure * A.ctx.sampleRate)), bitti: false };
    var dur = function () { T.bitir(); };
    T.bitir = function () {
      if (T.bitti) return;
      T.bitti = true;
      A.toplayici = null;
      A.el.removeEventListener('ended', dur);
      A.el.removeEventListener('pause', dur);
      res(T.kayit);
    };
    A.el.addEventListener('ended', dur);
    A.el.addEventListener('pause', dur);
    A.toplayici = T;
  });
}

// Dinlerken nakaratin geldigi an cagir: isaretle('A').
function isaretle(ad) {
  var A = _G.__ab;
  A.isaretler = A.isaretler || {};
  A.isaretler[ad] = +A.el.currentTime.toFixed(2);
  return ad + ' nakarat isareti: ' + A.isaretler[ad] + ' sn';
}

// Bir varyanti olcer. ~75 sn surer: ilk 60 sn + %40/%60/%80 noktalarinda
// 2'ser sn + son 6,5 sn.
async function olc(ad, secenek) {
  var A = _G.__ab;
  if (!A.kurulu) throw new Error('once: await kur()');
  var s = secenek || {};
  A.calisiyor = true;
  A.kirpL = null; A.kirpR = null;
  try {
    await _atla(0);
    if (A.el.paused) await A.el.play();
    var sure = A.el.duration;
    var bas = await _topla(Math.max(1, Math.min(NAKARAT_PENCERE_SN, sure - 8)));
    var noktalar = {};
    var yuzdeler = [40, 60, 80];
    for (var i = 0; i < yuzdeler.length; i++) {
      await _atla(sure * yuzdeler[i] / 100);
      if (A.el.paused) await A.el.play();
      noktalar[yuzdeler[i]] = await _topla(2);
    }
    await _atla(Math.max(0, sure - 6.5));
    if (A.el.paused) await A.el.play();
    var son = await _topla(6.5);
    var kL = kirpilmaBitir(A.kirpL), kR = kirpilmaBitir(A.kirpR);
    var isaret = (typeof s.nakarat_sn === 'number') ? s.nakarat_sn
      : ((A.isaretler && typeof A.isaretler[ad] === 'number') ? A.isaretler[ad] : undefined);
    A.sonuc[ad] = {
      bas: bas, son: son, noktalar: noktalar, sure: sure, yontem: A.yontem,
      kirpilma: { olay: kL.olay + kR.olay, ornek: kL.ornek + kR.ornek, en_uzun: Math.max(kL.en_uzun, kR.en_uzun) },
      nakarat_isaret: isaret,
    };
    return ad + ' olculdu (' + sure.toFixed(1) + ' sn, ' + bas.length + ' blok, ' + A.yontem + ')';
  } finally {
    A.calisiyor = false;
    A.toplayici = null;
  }
}

function karsilastir() {
  var A = _G.__ab;
  var o = {};
  var adlar = Object.keys(A.sonuc || {});
  adlar.forEach(function (ad) { o[ad] = ozetle(A.sonuc[ad]); });
  if (adlar.length >= 2) {
    o.varyant_farki = {};
    for (var i = 0; i < adlar.length; i++) {
      for (var j = i + 1; j < adlar.length; j++) {
        o.varyant_farki[adlar[i] + '-' + adlar[j]] = varyantFarki(o[adlar[i]], o[adlar[j]]);
      }
    }
  }
  return o;
}

// NASIL OKUNUR (olcut -> ne demek):
//  ilk_ses_sn      : "opens cold on the vocal" kurali icin. 0'a yakin olmali.
//                    1 sn'yi gecerse enstrumantal intro var demektir.
//  MY_ortanca/max  : merkez/yan enerji orani (3-14 sn). Vokal Suno miksinde
//                    merkeze, gitar-davul yanlara oturur. YUKSEK = vokal
//                    enstrumanlarin ONUNDE. Mutlak esik YOK - KARSILASTIR.
//  sustain_sn      : son akorun tam seviyede durdugu sure. UZUN = "strong
//                    final hit ending"; kisa = bastan kademeli fade.
//  son_tepe_orani  : parcanin son degeri / kuyrugun tepesi. 0,35 ustu ANI
//                    KESME demektir ("no abrupt cutoff" kurali dusuyor).
//  nakarat_sn      : nakaratin geldigi an. nakarat_yontem 'isaret' = kulakla
//                    isaretlendi; 'enerji' = ilk tam enerji ani (vekil,
//                    nakaratTespit aciklamasi). Kucuk olan onde; 45 sn'yi
//                    gecmesin (suno_kalite_onerileri.md #1).
//  kirpilma_*      : >= -0,1 dBFS en az 2 ardisik ornek (olay sayisi, toplam
//                    ornek, en uzun dizi). Varyantlar arasi 2 kattan buyuk
//                    fark varsa yuksek olan elenir. Kesin TP degil.
//  tepe_dbfs       : olculen pencerelerdeki en buyuk ornek. Yalniz siralama.
//  crest_db        : dinamik (tepe/RMS, 1 sn pencere ortancasi). <= ~6 dB
//                    ezilmis mix; 3 dB'yi asan fark anlamli.
//  son_sessizlik_sn: sondaki bos kuyruk. 2 sn'den uzunsa izleyici sessizlik
//                    goruyor (render bunu kirpmiyor).
//  erken_sonme     : %80 noktasi seviyesi < %40 noktasininin yarisi.
//  sure_asimi      : 4:00'i asan varyant -1 puan.
//  varyant_farki   : 'esit_dinleyerek_sec' ise kazanani olcum SECMEZ, kulak secer.
//
// SINIR: bu olcum vokal TONUNU, sozlerin dogru soylenip soylenmedigini,
// akort/entonasyon hatasini ya da parcanin "guzel" olup olmadigini OLCMEZ.
// Bunlar icin insan kulagi sart. Olcum yalnizca stil etiketindeki YAPISAL
// vaatlerin tutup tutmadigini soyler.

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    kirpilmaSay: kirpilmaSay, kirpilmaBitir: kirpilmaBitir, nakaratTespit: nakaratTespit,
    crestDb: crestDb, sonSessizlik: sonSessizlik, erkenSonme: erkenSonme,
    varyantFarki: varyantFarki, ozetle: ozetle, _ozet: _ozet,
  };
}
