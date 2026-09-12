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
// ses cikmaz ama analizor gercek dalga formunu gorur.
//
// DOGRULANDI (2026-09-12, Sabah Senin A/B): ayni iki parca hem bu yontemle
// hem indirilmis WAV'dan ffmpeg+numpy ile olculdu. Kapanistaki dususun
// basladigi an IKISINDE DE 269,75 sn cikti ve kazanan ayni. Mutlak RMS
// degerleri ~%20 farkli (akis kod cozumu ile WAV farki + analizor
// pencerelemesi) - bu yuzden esikler MUTLAK degere degil, iki varyant
// ARASINDAKI ORANA bakmali.
//
// KULLANIM (Chrome'da suno.com/create acikken, bir parca CALARKEN):
//   1. Asagidaki kodu yapistir -> motor kurulur (bir kez yeter)
//   2. kur() ile grafigi bagla
//   3. Her varyant icin: satirina tikla (calmaya bassin), sonra olc(ad)
//   4. karsilastir() -> ozet tablo
//   5. SADECE kazanani indir.

window.__ab = window.__ab || {};

function kur() {
  if (window.__ab.kurulu) return 'zaten kurulu';
  const el = [...document.querySelectorAll('audio')]
    .find(e => (e.currentSrc || '').startsWith('blob:'));
  if (!el) throw new Error('calan audio elementi yok - once bir parcaya tikla');
  const ctx = new (window.AudioContext || window.webkitAudioContext)();
  const src = ctx.createMediaElementSource(el);
  // stereo girdi analizorde otomatik mono'ya iner = MERKEZ (mid)
  const aMid = ctx.createAnalyser(); aMid.fftSize = 2048; aMid.smoothingTimeConstant = 0;
  const sp = ctx.createChannelSplitter(2);
  const aL = ctx.createAnalyser(); aL.fftSize = 2048; aL.smoothingTimeConstant = 0;
  const aR = ctx.createAnalyser(); aR.fftSize = 2048; aR.smoothingTimeConstant = 0;
  src.connect(aMid);
  src.connect(sp); sp.connect(aL, 0); sp.connect(aR, 1);
  const g = ctx.createGain(); g.gain.value = 0;   // sessiz
  src.connect(g); g.connect(ctx.destination);
  window.__ab = { kurulu: true, el, ctx, aMid, aL, aR, g, sonuc: {} };
  return 'kuruldu, sampleRate=' + ctx.sampleRate;
}

function _topla(sure) {
  const A = window.__ab;
  return new Promise(res => {
    const tL = new Float32Array(A.aL.fftSize), tR = new Float32Array(A.aR.fftSize);
    const kayit = [], bit = performance.now() + sure * 1000;
    const id = setInterval(() => {
      A.aL.getFloatTimeDomainData(tL); A.aR.getFloatTimeDomainData(tR);
      let m = 0, y = 0;
      for (let i = 0; i < tL.length; i++) {
        const mm = (tL[i] + tR[i]) / 2, yy = (tL[i] - tR[i]) / 2;
        m += mm * mm; y += yy * yy;
      }
      kayit.push([+A.el.currentTime.toFixed(2),
                  +Math.sqrt(m / tL.length).toFixed(5),
                  +Math.sqrt(y / tL.length).toFixed(5)]);
      if (performance.now() > bit) { clearInterval(id); res(kayit); }
    }, 40);
  });
}

// Bir varyanti olcer. ~21 sn surer: ilk 14 sn + son 6,5 sn.
// TUM parcayi dinlemeye gerek yok - ayirt eden iki pencere bunlar.
async function olc(ad) {
  const A = window.__ab;
  A.calisiyor = true;
  A.el.currentTime = 0;
  if (A.el.paused) await A.el.play();
  await new Promise(r => setTimeout(r, 300));
  const bas = await _topla(14);
  A.el.currentTime = Math.max(0, A.el.duration - 6.5);
  await new Promise(r => setTimeout(r, 400));
  const son = await _topla(6);
  A.sonuc[ad] = { bas, son, sure: A.el.duration };
  A.calisiyor = false;
  return ad + ' olculdu (' + A.el.duration.toFixed(1) + ' sn)';
}

function _ozet(r) {
  const kov = new Map();
  for (const [t, mid, yan] of r.bas) {
    const k = Math.floor(t * 2) / 2;
    if (!kov.has(k)) kov.set(k, []);
    kov.get(k).push([mid, yan]);
  }
  const oranlar = [...kov.entries()].sort((a, b) => a[0] - b[0])
    .filter(([k]) => k >= 3)          // ilk 3 sn acilis gecisi, disarida
    .map(([, v]) => {
      const n = v.length;
      const mm = Math.sqrt(v.reduce((s, x) => s + x[0] * x[0], 0) / n);
      const yy = Math.sqrt(v.reduce((s, x) => s + x[1] * x[1], 0) / n);
      return mm / (yy + 1e-9);
    });
  const tepeBas = Math.max(...r.bas.map(x => x[1]));
  const ilkSes = r.bas.find(x => x[1] > tepeBas * 0.02);
  const k2 = new Map();
  for (const [t, mid] of r.son) {
    const k = Math.floor(t * 4) / 4;
    if (!k2.has(k)) k2.set(k, []);
    k2.get(k).push(mid);
  }
  const ku = [...k2.entries()].sort((a, b) => a[0] - b[0])
    .map(([k, v]) => [k, Math.sqrt(v.reduce((s, x) => s + x * x, 0) / v.length)]);
  const tp = Math.max(...ku.map(x => x[1]));
  const dusus = ku.find(x => x[1] < tp * 0.75);
  const s = [...oranlar].sort((a, b) => a - b);
  return {
    sure: +r.sure.toFixed(1),
    ilk_ses_sn: ilkSes ? ilkSes[0] : null,
    MY_ortanca: +s[Math.floor(s.length / 2)].toFixed(2),
    MY_max: +Math.max(...oranlar).toFixed(2),
    sustain_sn: dusus ? +(dusus[0] - ku[0][0]).toFixed(2) : null,
    son_tepe_orani: +(ku[ku.length - 1][1] / tp).toFixed(3),
  };
}

function karsilastir() {
  const A = window.__ab;
  const o = {};
  for (const ad of Object.keys(A.sonuc)) o[ad] = _ozet(A.sonuc[ad]);
  return o;
}

// NASIL OKUNUR (olcut -> ne demek):
//  ilk_ses_sn      : "opens cold on the vocal" kurali icin. 0'a yakin olmali.
//                    1 sn'yi gecerse enstrumantal intro var demektir.
//  MY_ortanca/max  : merkez/yan enerji orani. Vokal Suno miksinde merkeze,
//                    gitar-davul yanlara oturur. YUKSEK = vokal enstrumanlarin
//                    ONUNDE. Mutlak esik YOK - iki varyanti KARSILASTIR.
//  sustain_sn      : son akorun tam seviyede durdugu sure. UZUN = "strong
//                    final hit ending"; kisa = bastan kademeli fade.
//  son_tepe_orani  : parcanin son degeri / kuyrugun tepesi. 0,35 ustu ANI
//                    KESME demektir ("no abrupt cutoff" kurali dusuyor).
//
// SINIR: bu olcum vokal TONUNU, sozlerin dogru soylenip soylenmedigini,
// akort/entonasyon hatasini ya da parcanin "guzel" olup olmadigini OLCMEZ.
// Bunlar icin insan kulagi sart. Olcum yalnizca stil etiketindeki YAPISAL
// vaatlerin tutup tutmadigini soyler.
