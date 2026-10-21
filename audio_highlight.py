"""Bir ses dosyasının en yoğun/enerjik bölümünü bulur — kısa (Shorts/Reels/TikTok)
video kırpması için "highlight" aralığı üretir.

Yöntem: RMS enerjisinin kayan ortalamasını hesaplayıp, hedef süre uzunluğundaki
en yüksek ortalama enerjiye sahip pencereyi seçer. Bu genelde şarkının en
"kalabalık" (tüm enstrümanların aktif olduğu, nakarat/drop gibi) anına denk
gelir — kesin bir "viral an" garantisi değildir, ama basit ve bağımsız bir
tahmin sağlar.
"""

import librosa
import numpy as np


def find_highlight(audio_path: str, target_duration: float) -> tuple[float, float]:
    """(start_seconds, end_seconds) döner. Şarkı target_duration'dan kısaysa
    baştan sona tüm şarkıyı döner."""
    y, sr = librosa.load(audio_path, sr=22050, mono=True)
    total_duration = len(y) / sr

    if total_duration <= target_duration:
        return 0.0, total_duration

    hop_length = 512
    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
    frame_duration = hop_length / sr

    window_frames = max(1, int(round(target_duration / frame_duration)))
    if window_frames >= len(rms):
        return 0.0, total_duration

    window_energy = np.convolve(rms, np.ones(window_frames), mode="valid") / window_frames
    best_frame = int(np.argmax(window_energy))

    start_time = best_frame * frame_duration
    end_time = start_time + target_duration
    return round(start_time, 2), round(min(end_time, total_duration), 2)


def find_highlights(audio_path: str, target_duration: float, count: int = 1,
                    min_gap: float = 0.0) -> list:
    """En yüksek enerjili `count` pencereyi ENERJİ SIRASINDA döner.

    NEDEN (2026-10-21): `dj_clips.py` (kesit üretimi) bir setten birden fazla
    kesit üretmek için çoklu pencere istiyordu. Bu modül tek pencere sunuyordu;
    `dj_clips` import'u patlıyordu. Eklenen bu sürüm:
      - enerji sırasında döner (ilk eleman EN enerjili),
      - `min_gap` sn ile pencerelerin birbirine GİRMESİNİ garanti eder,
      - `count=1` iken `find_highlight()` ile AYNI sonucu verir.

    `min_gap=0` → pencereler bitişik olabilir ama çakışmaz.
    """
    y, sr = librosa.load(audio_path, sr=22050, mono=True)
    total_duration = len(y) / sr

    if total_duration <= target_duration:
        return [(0.0, round(total_duration, 2))]

    hop_length = 512
    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
    frame_duration = hop_length / sr

    window_frames = max(1, int(round(target_duration / frame_duration)))
    if window_frames >= len(rms):
        return [(0.0, round(total_duration, 2))]

    window_energy = np.convolve(rms, np.ones(window_frames), mode="valid") / window_frames
    # ENERJİ SIRASI: en yüksekten başa
    sira = np.argsort(window_energy)[::-1]

    secilecek = max(1, int(count))
    secilen = []
    for frame in sira:
        bas = float(frame) * frame_duration
        bit = bas + target_duration
        if bit > total_duration:
            bit = total_duration
        # min_gap: once secilenlerden en az min_gap kadar uzakta mi?
        cakisiyor = False
        for (b2, s2) in secilen:
            if bas < s2 + min_gap and b2 < bit + min_gap:
                cakisiyor = True
                break
        if cakisiyor:
            continue
        secilen.append((round(bas, 2), round(bit, 2)))
        if len(secilen) >= secilecek:
            break

    if not secilen:
        return [(0.0, round(total_duration, 2))]
    return secilen
