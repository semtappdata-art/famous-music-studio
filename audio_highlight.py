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
def find_highlights(audio_path: str, target_duration: float, count: int = 3,
                    min_gap: float = 30.0) -> list[tuple[float, float]]:
    """En yoğun `count` adet, BİRBİRİYLE ÇAKIŞMAYAN pencereyi döner.

    Neden gerekli: find_highlight tek pencere veriyor, yani 81 dakikalık bir
    DJ setinden tek bir 45 saniyelik kesit çıkıyor. Oysa setin içinde birbirine
    benzemeyen onlarca an var; aynı üretimden birden fazla Shorts çıkarmak
    Suno tavanına takılmadan içerik çoğaltmanın en ucuz yolu.

    Seçim yöntemi find_highlight ile AYNI (RMS kayan ortalaması) — tutarlılık
    için yeniden yazılmadı, aynı enerji eğrisi kullanılıyor. Fark: en yüksek
    pencereyi seçtikten sonra çevresi (pencere + min_gap) bastırılıp bir
    sonraki tepe aranıyor. Bastırma olmadan üç pencere de aynı nakaratın
    birkaç saniye kaymış hâlleri çıkardı.

    Şarkı kısaysa veya yeterli ayrı bölge yoksa BULUNABİLDİĞİ kadarını döner —
    çağıran taraf len() ile kontrol etmeli.
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

    enerji = np.convolve(rms, np.ones(window_frames), mode="valid") / window_frames
    enerji = enerji.copy()
    bastir = int(round((target_duration + min_gap) / frame_duration))

    sonuc = []
    for _ in range(max(1, count)):
        if not np.isfinite(enerji).any() or np.nanmax(enerji) <= -np.inf:
            break
        tepe = int(np.nanargmax(enerji))
        if enerji[tepe] == -np.inf:
            break
        bas = tepe * frame_duration
        son = min(bas + target_duration, total_duration)
        sonuc.append((round(bas, 2), round(son, 2)))
        # Seçilen tepenin çevresini ele — bir sonraki arama başka bir bölgeden
        # gelsin. -inf ile bastırmak, sıfırlamaktan güvenli: sıfır da bir
        # "sessiz ama geçerli" pencere gibi seçilebilirdi.
        enerji[max(0, tepe - bastir): tepe + bastir] = -np.inf

    # ENERJİ SIRASINDA dönüyor, zaman sırasında değil: ilk eleman daima
    # find_highlight()'ın seçeceği pencere. Çağıran taraf "ana Shorts zaten
    # o pencereyi kullanıyor" diyerek ilkini atabilsin diye bu sıra korunuyor.
    # Zaman sırası isteyen sorted() çağırır.
    return sonuc
