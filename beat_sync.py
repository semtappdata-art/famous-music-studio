# -*- coding: utf-8 -*-
"""BEAT SYNC — YouTube Shorts müzik efektleri için ritim tespiti.

NEDEN VAR
----------
YouTube Shorts'ta "müzikle uyumlu" görsel, platformun en belirgin özelliği.
Cercle / Boiler Room / HÖR referans videolarının tamamı görselleri ritme
bağlı keser. Depoda şu an tek bir görsel (art.jpg) pan + hue ile
dönüyor — ritme bağlı DEĞİL. Bu modül müziğin ritmini (beat) bulur ve
ffmpeg'e "her beat'te şunu yap" talimatı verir.

YOUTUBE'E ÖZGÜ EFEKTLER (buradaki karşılıkları)
----------------------------------------------
1. **Beat sync (Otomatik ritim)** — YouTube Shorts düzenleyicisinin
   "Beat sync" özelliği. Görseller ritme göre kesilir. Burada: her beat'te
   parlaklık flaşı + renk (hue) sıçraması + pan itmesi.
2. **Speed ramp (Hız rampası)** — YouTube'un "speed ramp" özelliği:
   yavaş başlar, beat drop'ta hızlıya geçer. `setpts` + `atempo` ile.
3. **Beat clock (ritim saati)** — düzgün ritimde sabit periyotla
   çalışan ifade; renk/pan nabzı beat'e kilitlenir.

KOTA / PERFORMANS
-----------------
librosa beat tespiti bir WAV'i 22050 Hz'e indirip 1-3 saniyede işler.
Sonuç `<proje>/.beat_cache.json` içine yazılır (ses dosyasının boyut +
mtime ile etiketlenir) → ikinci render'da anında gelir.

BAĞIMLILIK
----------
librosa/numpy/scipy yoksa modül SESSİZCE devre dışı kalır (beat_times
None döner) — render yine de çalışır. Kural: kütüphane eksikliği
boru hattını DÜŞÜRMEMELİ.
"""

import json
import os
import sys

# --- ayarlar ---------------------------------------------------------------

CACHE_DOSYA_ADI = ".beat_cache.json"
ANALIZ_SR = 22050          # librosa analiz örnekleme hızı
HOP_LENGTH = 512
ONERI_HOP = 512
MIN_BEAT_ARALIK_SN = 0.18  # 333 BPM üstü sanılsın diye üst sınır
MAX_BEAT_ARALIK_SN = 1.20  # 50 BPM altı sanılsın diye alt sınır
LOG_YOL = "librosa.log"


def _log(msg: str) -> None:
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"))


# --- önbellek --------------------------------------------------------------


def _cache_yolu(audio_path: str) -> str:
    return os.path.join(os.path.dirname(os.path.abspath(audio_path)),
                        CACHE_DOSYA_ADI)


def _ses_etiketi(audio_path: str) -> dict:
    try:
        st = os.stat(audio_path)
        return {"boyut": st.st_size, "mtime": int(st.st_mtime)}
    except OSError:
        return {"boyut": 0, "mtime": 0}


def _cache_oku(audio_path: str) -> dict | None:
    yol = _cache_yolu(audio_path)
    if not os.path.isfile(yol):
        return None
    try:
        with open(yol, "r", encoding="utf-8") as f:
            veri = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(veri, dict):
        return None
    if veri.get("etiket") != _ses_etiketi(audio_path):
        return None          # ses değişmiş -> cache geçersiz
    return veri


def _cache_uygun(veri: dict, start: float | None, end: float | None) -> bool:
    """Cache araligi istenen kirpmayla eslesiyor mu?

    NEDEN: aynı ses için "ilk 30sn" ve "30-60sn" analizleri FARKLI beat
    listeleri verir (beat tespiti pencereleme duyarlı). Tek bir cache
    slotu tutmak yanlış sonuc verirdi.
    """
    kayit = veri.get("aralik") or [None, None]
    istenen = [start, end]
    if (kayit[0] is None) == (istenen[0] is None):
        if kayit[0] is None:
            return True
        if abs(float(kayit[0]) - float(istenen[0])) < 0.01:
            if kayit[1] is None and istenen[1] is None:
                return True
            if kayit[1] is not None and istenen[1] is not None:
                return abs(float(kayit[1]) - float(istenen[1])) < 0.01
    return False


def _cache_yaz(audio_path: str, veri: dict) -> None:
    yol = _cache_yolu(audio_path)
    try:
        import state_io
        state_io._atomik_yaz(yol, veri)
    except Exception:                                        # noqa: BLE001
        try:
            with open(yol, "w", encoding="utf-8") as f:
                json.dump(veri, f, ensure_ascii=False)
        except OSError:
            pass


# --- analiz ----------------------------------------------------------------


def analiz_et(audio_path: str, kullan_cache: bool = True,
              start: float | None = None, end: float | None = None) -> dict:
    """Beat'leri tespit eder.

    Dönüş: {"bpm": float, "beats": [saniye], "period": float,
            "basari": bool}
    `basari` False ise beat bulunamadı (kütüphane yok / sessiz ses).

    `start`/`end`: sadece bu aralık analiz edilir (Shorts kırpma).
    Beat'ler dosyanın BAŞINDAN itibaren döner (mutlak zaman) — kırpma
    ofseti render tarafında uygulanır.
    """
    if not audio_path or not os.path.isfile(audio_path):
        return {"bpm": 0.0, "beats": [], "period": 0.0, "basari": False}

    if kullan_cache:
        onbellek = _cache_oku(audio_path)
        if onbellek is not None and _cache_uygun(onbellek, start, end):
            return onbellek

    sonuc = {"bpm": 0.0, "beats": [], "period": 0.0, "basari": False}
    try:
        import librosa
        import numpy as np
    except ImportError as e:
        _log(f"  [beat_sync] librosa yok — beat efekti devre disi ({e})")
        return sonuc

    try:
        # NEDEN offset/duration: Shorts kirkirmasi genelde 30-60sn ama ses
        # dosyasi 3-4 dakika. Tum dosyayi yuklemek 30sn suruyordu; sadece
        # kirpilan araligi yuklemek 10-20x hizli.
        y, sr = librosa.load(audio_path, sr=ANALIZ_SR, mono=True,
                             offset=start or 0.0,
                             duration=(end - start) if (start is not None
                                                      and end is not None) else None)
        if y is None or len(y) < sr // 4:
            return sonuc
        tempo, beat_frames = librosa.beat.beat_track(
            y=y, sr=sr, hop_length=HOP_LENGTH, units="time")
        # NEDEN start ekleniyor: librosa `offset=start` ile yuklediginde
        # beat zamanlari KIRPILAN SEGMENTE gore relative doner. Biz mutlak
        # (dosya basindan) zaman istiyoruz — kirpma ofseti render'da
        # uygulanacak (beat_sync.kirp_beatler(offset=...)).
        ofs = float(start or 0.0)
        beats = [float(b) + ofs for b in np.atleast_1d(beat_frames)]
        bpm = float(np.atleast_1d(tempo)[0]) if tempo is not None else 0.0
        # BPM makul degilse vuruş araligindan turet
        if not (40.0 <= bpm <= 220.0):
            araliklar = [beats[i + 1] - beats[i] for i in range(len(beats) - 1)]
            if araliklar:
                aralik = float(np.median(araliklar))
                if MIN_BEAT_ARALIK_SN <= aralik <= MAX_BEAT_ARALIK_SN:
                    bpm = 60.0 / aralik
        # son beat'ler kirpma disinda kalmasin
        sonuc = {
            "bpm": round(bpm, 2),
            "beats": [round(b, 3) for b in beats],
            "period": round(60.0 / bpm, 4) if bpm > 0 else 0.0,
            "basari": bool(beats),
            "etiket": _ses_etiketi(audio_path),
            "aralik": [start, end],
        }
    except Exception as e:                                   # noqa: BLE001
        _log(f"  [beat_sync] analiz hatasi: {type(e).__name__}: {str(e)[:120]}")
        return sonuc

    if sonuc.get("basari"):
        _cache_yaz(audio_path, sonuc)
    return sonuc


# --- ffmpeg icin yardimcilar ----------------------------------------------


def kirp_beatler(beats: list, offset: float = 0.0, duration: float | None = None
                 ) -> list:
    """Beat listesini kirpmaya uygun hale getirir.

    `offset`: sesin kesildigi yer (Shorts kirkirmasinda baslangic).
    `duration`: sona kisilacak saniye (yoksa hepsi).
    """
    kirp = []
    for b in beats or []:
        t = float(b) - float(offset)
        if t < -0.05:
            continue
        if duration is not None and t > duration + 0.05:
            break
        kirp.append(round(max(0.0, t), 3))
    return kirp


def flash_enable_ifadesi(beats: list, sure_sn: float = 0.12,
                         on_tolerance: float = 0.03) -> str:
    """Her beat icin `between()` toplami olan FFmpeg `enable` ifadesi.

    NEDEN TEK FILTRE: 30 saniyelik bir Short'ta 60-120 beat var. Her beat
    icin ayri overlay filtresi koymak filter_complex'i patlatir. Toplam
    ifade TEK overlay'a girer.

    NEDEN `+` toplami: `enable` ifadesi sifir disi degerde truthy kabul
    edilir; 0 ise falsy. Toplam, o anda en az bir beat penceresi acik
    oldugunda >0 olur.
    """
    parcalar = []
    for b in beats or []:
        bas = float(b) - on_tolerance
        bit = float(b) + sure_sn
        parcalar.append(f"between(t,{bas:.3f},{bit:.3f})")
    if not parcalar:
        return "0"
    return "+".join(parcalar)


def beat_nabzi_ifadesi(period: float, t0: float = 0.0,
                       sertlik: float = 9.0) -> str:
    """Beat'e kilitli nabız ifadesi (FFmpeg `exp` destekler).

    NEDEN: Renk/pan "düzgün ritim" varsayımıyla sürekli bir üçgen dalgası
    yerine, beat'e TIKLANAN bir üstel sönüm kullanıyoruz. Gerçek beat
    listesi (flash) ile birlikte kullanılır: renk değişimi tam beat'te
    zirve yapıp hızla sönümlenir → "snap" hissi.
    """
    if not period or period <= 0:
        return "0"
    return f"exp(-max(0\\,mod(t-{float(t0):.3f}\\,{period:.4f}))*{sertlik:.2f})"


def hiz_rampasi_planla(beats: list, yavas_sure: float = 1.6,
                       yavas_kat: float = 0.55) -> dict | None:
    """YouTube "speed ramp" planı — yavaş başla, BEAT'te hızlan.

    NEDEN: YouTube Shorts düzenleyicisinde "speed ramp" efekti var: klip
    yavaş başlar, müziğin düştüğü anda hızlanır. Bu, izleyicide
    "profesyonel kurgu" izlenimi yaratır.

    NEDEN BEAT'E KİLİT: hızlanma anı rastgele değil, tam bir beat'e
    denk gelmeli — aksi halde efekt "yanlış" hissedilir.

    ZAMAN EŞLEMESİ (video ve ses aynı):
        girdi [0, T_in)  -> çıktı [0, t_snap)  hız = yavas_kat
        girdi [T_in, ..) -> çıktı [t_snap, ..) hız = 1.0

    NEDEN T_in = t_snap * kat: video `setpts='T/kat'` girdi karesini
    çıktı T/kat konumuna koyar; ses `atempo=kat` çıktı süresini
    girdi/kat yapar. İkisi de girdi [0,T_in) -> çıktı [0, T_in/kat)
    verir → T_in/kat = t_snap → T_in = t_snap * kat.

    (Ölçüldü: setpts 'T*kat' + atempo 'kat' ikisi ters yönde
    çalışıyor — video hızlanıyor, ses yavaşlıyordu.)

    Dönüş: {"t_snap": float, "T_in": float, "kat": float, "rest": float}
    veya None (beat yoksa ramp uygulanmaz).
    """
    if not beats or yavas_kat <= 0 or yavas_sure <= 0:
        return None
    # t_snap: yavas_sure'dan sonraki ilk beat
    t_snap = None
    for b in beats:
        if float(b) >= yavas_sure:
            t_snap = float(b)
            break
    if t_snap is None:
        t_snap = float(beats[-1])
    T_in = t_snap * yavas_kat
    return {
        "t_snap": round(t_snap, 4),
        "T_in": round(T_in, 4),
        "kat": round(float(yavas_kat), 4),
    }


def beatleri_zaman_esle(beats: list, plan: dict | None) -> list:
    """Beat'leri hiz rampasi zaman eslemesinden gecirir.

    NEDEN: hiz rampasi video/ses ZAMAN CIZGISINI degistirir. Beat flaşı
    son haliyle (post-ramp) hesaplanir; beat'ler eski (pre-ramp) zamanlarda
    kalirsa flaş müzikten ayrilir — a/v uyumsuzluk.

    Esleme:
        girdi b < T_in   -> çıktı b * kat
        girdi b >= T_in  -> çıktı t_snap + (b - T_in)

    plan None ise beat'ler değişmeden döner.
    """
    if not plan or not beats:
        return list(beats or [])
    T_in = float(plan.get("T_in", 0.0))
    t_snap = float(plan.get("t_snap", 0.0))
    kat = float(plan.get("kat", 1.0)) or 1.0
    kirk = []
    for b in beats:
        b = float(b)
        if b < T_in:
            kirk.append(round(b * kat, 3))
        else:
            kirk.append(round(t_snap + (b - T_in), 3))
    return kirk


def ozet(audio_path: str) -> str:
    """Tek satır özet (log/rapor için)."""
    a = analiz_et(audio_path)
    if not a.get("basari"):
        return f"beat yok (bpm={a.get('bpm', 0):.1f})"
    return (f"bpm={a.get('bpm', 0):.1f} beat={len(a.get('beats', []))} "
            f"periyot={a.get('period', 0):.3f}s")


_ = sys  # noqa: F401
