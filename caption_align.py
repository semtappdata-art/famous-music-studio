"""YouTube'un otomatik (ASR) altyazısının ZAMANLAMASINI, gerçek sözler
dosyasının (`<slug>_sozler.md`) doğru METNİYLE birleştirir.

NEDEN: YouTube'un "Otomatik altyazılar"ı ses tanımaya dayalı zamanlaması
konusunda güvenilir ama METNİ kendi duyduğu gibi yazıyor — sık sık yanlış
kelime, eksik noktalama (bkz. Gece Sürüşü/Sessiz Mektup/Kumdan Denize/Beni
Bırakma'nın 2026-09-06'daki elle incelemesi: "güllerimden" yerine
"küllerimden", "alar" yerine "ağlar" gibi onlarca örnek). Bu modül ASR'nin
kelime zamanlarını `difflib.SequenceMatcher` ile gerçek sözlerin kelime
dizisiyle eşleştirip, eşleşen kelimeler için ASR'nin GERÇEK zamanını
kullanıyor, eşleşmeyen (ASR'nin kaçırdığı/yanlış duyduğu) kelimeler için
komşu eşleşmelerden ARADEĞER (interpolation) üretiyor.

Bu modül `upload/youtube_captions.py` tarafından auto_process.py'nin bir
parçası olarak çağrılıyor — SADECE bir `*_sozler.md` dosyası olan projeler
için (bkz. o modülün docstring'i: sözler yoksa ASR metnini "düzeltilmiş"
gibi otomatik yayınlamak güvenli değil, insan gözden geçirmesi gerekir).
"""
import re
import sys
import difflib


def parse_srt_cues(srt_text: str):
    """SRT metnini (start_saniye, metin) çiftlerine ayırır — bitiş zamanı
    kasıtlı olarak atlanıyor, ASR'nin overlapping/rolling cue'ları bitiş
    zamanını anlamsız kılıyor (bir sonraki cue'nun başlangıcı daha güvenilir
    bir sınır)."""
    blocks = re.split(r"\n\s*\n", srt_text.strip())
    cues = []
    for block in blocks:
        lines = block.strip().splitlines()
        if len(lines) < 2:
            continue
        m = re.match(r"(\d\d):(\d\d):(\d\d),(\d\d\d)\s*-->", lines[1])
        if not m:
            continue
        h, mi, s, ms = map(int, m.groups())
        start = h * 3600 + mi * 60 + s + ms / 1000
        text = " ".join(lines[2:])
        cues.append((start, text))
    return cues


def clean_text(text: str) -> str:
    text = re.sub(r"\[.*?\]", "", text)
    return re.sub(r"\s+", " ", text).strip()


class LyricsNotReady(RuntimeError):
    """Söz dosyası var ama "## Temiz Sözler" bölümü henüz YAZILMAMIŞ.

    Gerçek bir arızadan (bozuk dosya, eksik ASR vs.) ayrı tutuluyor: bu durum
    insanın sözleri tamamlamasını bekleyen normal bir iş, her koşuda "HATA"
    olarak raporlanınca durum panelinde kalıcı bir alarma dönüşüyordu.
    """


class LyricsMismatch(RuntimeError):
    """ASR ile sözler dosyası BİRBİRİNİ TUTMUYOR — muhtemelen YANLIŞ şarkının
    sözleri eşleşti.

    NEDEN AYRI BİR KAPI VAR: `align()` eskiden yalnızca eşleşme SIFIR olduğunda
    hata atıyordu. Ama iki farklı Türkçe şarkı bile ortak kelimeler ("bir",
    "beni", "gece") yüzünden hiçbir zaman sıfırda kalmıyor — bu katalogda
    ölçüldü: YANLIŞ eşlenmiş 19 şarkının en yüksek "eşleşme" oranı 0,146,
    DOĞRU eşlenmişlerin en düşüğü (gerçekçi %25 ASR bozulmasıyla) 0,303.
    Yani aradaki boşluk geniş ve sessiz yanlış yayın tam ortasından geçiyordu:
    başka bir şarkının sözleri, aradeğerle uydurulmuş zamanlarla videoya
    yazılırdı — izleyici görür, biz görmeyiz.
    """


def lyrics_marked_incomplete(md_content: str) -> bool:
    """Söz dosyası kendini "eksik" diye işaretlemiş mi.

    Bu projede eksik dosyalar başlıklarında açıkça belirtiliyor, ör.:
        ## Sözler (ekran görüntülerinden yakalanan parçalar — EKSİK, tamamlanmalı)
    """
    for satir in md_content.splitlines():
        if not satir.lstrip().startswith("#"):
            continue
        d = satir.lower()
        if "eksik" in d or "tamamlanmalı" in d or "tam olmayabilir" in d:
            return True
    return False


def extract_clean_lyrics(md_content: str):
    """`*_sozler.md`'deki "## Temiz Sözler" bölümünü (köşeli parantez
    etiketsiz, doğrudan kullanılabilir sürüm) çeker — bkz. CLAUDE.md'deki
    "Her *_sozler.md'de Temiz Sözler bölümü SABİT" kararı."""
    match = re.search(r"## Temiz Sözler.*?```\n(.*?)```", md_content, re.DOTALL)
    if not match:
        return None
    return match.group(1).strip()


def split_into_cues(lyrics: str):
    cues = []
    for raw_line in lyrics.splitlines():
        raw_line = raw_line.strip()
        raw_line = re.sub(r"^\([^)]*\)\s*", "", raw_line)
        if not raw_line:
            continue
        for part in raw_line.split(","):
            part = part.strip()
            if part:
                cues.append(part)
    return cues


# Türkçe büyük harf tuzağı: Python'un genel `str.lower()`'ı "İ"yi TEK bir
# harfe değil, "i" + U+0307 (birleşen nokta) ÇİFTİNE çeviriyor, "I"yı da "ı"
# yerine "i" yapıyor. ASR çıktısı küçük harf yazdığı için gerçek sözlerdeki
# "İçimde" ASR'nin "içimde"siyle ASLA eşleşmiyordu — eşleşmeyen her kelime
# aradeğere düşüyor, yani zamanı komşularından TAHMİN ediliyor. Katalogda
# ölçüldü: 19 sözler dosyasında 14 kelime (9 şarkı) tam bu yüzden kaybediliyordu
# ("İçimde taş kesilir gece" gibi SATIR BAŞI kelimeler — hizalamanın en çok
# çapaya ihtiyaç duyduğu yer). Türkçe doğru eşleme İ->i, I->ı; `lower()`'dan
# ÖNCE uygulanıyor.
_TR_KUCUK = str.maketrans({"İ": "i", "I": "ı"})


def _norm_word(w: str) -> str:
    return re.sub(r"[^\wçğıöşüÇĞİÖŞÜ]", "", w.translate(_TR_KUCUK)).lower()


def format_srt(cues) -> str:
    def ts(t):
        ms_total = max(0, int(round(t * 1000)))
        h, ms_total = divmod(ms_total, 3600000)
        m, ms_total = divmod(ms_total, 60000)
        s, ms = divmod(ms_total, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    parts = []
    for i, (start, end, text) in enumerate(cues, start=1):
        parts.append(f"{i}\n{ts(start)} --> {ts(end)}\n{text}\n")
    return "\n".join(parts)


def _build_word_time_list(asr_cues):
    """(norm_word, orijinal_word, zaman) üçlüleri — bir cue'nun TÜM
    kelimelerine aynı (cue başlangıcı) zamanı vermek yerine, cue'nun kendi
    süresi içinde kelime pozisyonuna göre enterpolasyonla dağıtır. Bu, ASR
    cue'ları birden çok kelime içerdiğinde eşleşme hassasiyetini artırır."""
    out = []
    for i, (start, text) in enumerate(asr_cues):
        text = clean_text(text)
        words = text.split()
        if not words:
            continue
        end = asr_cues[i + 1][0] if i + 1 < len(asr_cues) else start + 2.0 * len(words)
        span = max(end - start, 0.01)
        for j, w in enumerate(words):
            t = start + span * j / len(words)
            out.append((_norm_word(w), w, t))
    return out


# ASR ile sözlerin GERÇEKTEN aynı şarkıya ait sayılması için gereken en düşük
# kelime eşleşme oranı. Katalogda ölçüldü (19 sözler dosyası, tam çapraz):
#   - YANLIŞ şarkı eşlendiğinde (kusursuz ASR ile bile) en yüksek oran 0,146
#   - DOĞRU şarkıda, gerçekçi %25 ASR bozulmasıyla en düşük oran 0,303
# 0,25 bu iki bulutun ORTASINDA duruyor. Yanılma yönü de bilinçli: eşik yanlış
# yere düşerse altyazı YAYINLANMAZ (log'a düşer, insan bakar) — tersi, başka
# bir şarkının sözlerinin sessizce yayınlanması olurdu.
MIN_ESLESME_ORANI = 0.25

MIN_CUE_DUR = 0.15  # bundan kısa bir cue neredeyse kesin bir hizalama hatası


def esleme_istatistigi(asr_norm, real_norm):
    """(eşleşen_bloklar, eşleşen_kelime_sayısı, oran) döner.

    `align()` ile testlerin/denetimlerin AYNI sayıyı görmesi için tek noktada:
    "oran" gerçek sözlerin kaç kelimesinin ASR'de bir karşılık bulduğunu
    söylüyor — geri kalanı ARADEĞERLE (komşulardan tahminle) zaman alıyor."""
    sm = difflib.SequenceMatcher(None, asr_norm, real_norm, autojunk=False)
    blocks = sm.get_matching_blocks()
    eslesen = sum(b.size for b in blocks)
    return blocks, eslesen, (eslesen / len(real_norm) if real_norm else 0.0)


def _merge_degenerate_cues(cues):
    """Süresi MIN_CUE_DUR'dan kısa (sıfıra çok yakın/sıfır) bir cue neredeyse
    her zaman bir hizalama artığıdır (iki bitişik kelimenin aynı ASR-çapa
    zamanına düşmesi gibi) — bir sonraki (yoksa bir önceki) cue'yla
    birleştirilir. Otomasyonun insan gözden geçirmesi OLMADAN yayınlayacağı
    bir çıktı için bu, cue'ların algoritmanın hangi köşesinden geldiğine
    bakmaksızın çalışan bir SON güvenlik ağı (bkz. Kumdan Denize'nin elle
    düzeltilen sıfır-süreli ilk cue'su, 2026-09-06 — o düzeltme elle
    yapılmıştı, otomasyon aynı hatayı insansız da onarabilmeli)."""
    if not cues:
        return cues
    out = [list(cues[0])]
    for s, e, t in cues[1:]:
        if e - s < MIN_CUE_DUR and out:
            out[-1][1] = max(out[-1][1], e)
            out[-1][2] = f"{out[-1][2]} {t}".strip()
        else:
            out.append([s, e, t])
    if len(out) > 1 and out[0][1] - out[0][0] < MIN_CUE_DUR:
        out[1][0] = out[0][0]
        out[1][2] = f"{out[0][2]} {out[1][2]}".strip()
        out = out[1:]
    return [tuple(c) for c in out]


def align(asr_srt_path: str, lyrics_md_path: str, video_duration: float,
          min_esleme_orani: float = MIN_ESLESME_ORANI):
    """ASR SRT dosyası + gerçek sözler (.md) -> [(start, end, text), ...].

    difflib.SequenceMatcher ile ASR'nin normalize kelime dizisi ve gerçek
    sözlerin normalize kelime dizisi arasında GERÇEKTEN eşleşen bloklar
    bulunur. Eşleşen her kelime ASR'nin kendi zamanını alır; eşleşmeyenler
    (ASR'nin kaçırdığı/farklı duyduğu kelimeler) komşu eşleşmeler arasında
    doğrusal aradeğerle zaman kazanır — şarkının BAŞINDA/SONUNDA (henüz/artık
    bir komşu eşleşme yokken) video başlangıcını (0.0) ve ASR'nin son bilinen
    kelime zamanını sanal çapa olarak kullanır (bkz. modül-altı not: bu iki
    sanal çapa olmadan tüm baştaki/sondaki eşleşmeyen kelimeler TEK bir ortak
    zamana çöküyordu — Kumdan Denize'nin ilk iki cue'sunun aynı anda
    başlamasının kök nedeni buydu, 2026-09-06)."""
    asr_cues = parse_srt_cues(open(asr_srt_path, encoding="utf-8").read())
    asr_words = _build_word_time_list(asr_cues)
    asr_norm = [w[0] for w in asr_words]

    md = open(lyrics_md_path, encoding="utf-8").read()
    lyrics = extract_clean_lyrics(md)
    if not lyrics:
        if lyrics_marked_incomplete(md):
            raise LyricsNotReady(
                f"{lyrics_md_path}: sözler henüz tamamlanmamış "
                "(dosya kendini 'eksik' olarak işaretlemiş).")
        raise RuntimeError(f"{lyrics_md_path}: '## Temiz Sözler' bölümü bulunamadı.")
    real_cues = split_into_cues(lyrics)

    real_words = []  # (norm, original, cue_idx)
    for ci, cue in enumerate(real_cues):
        for w in cue.split():
            real_words.append((_norm_word(w), w, ci))
    real_norm = [w[0] for w in real_words]

    blocks, eslesen, oran = esleme_istatistigi(asr_norm, real_norm)
    # YANLIŞ ŞARKI KAPISI — bu fonksiyonun tek sessiz-yanlış-yayın riski burası.
    # `stock_art.find_lyrics_file()` bulanık (ön-ek/difflib) eşleşme yapıyor;
    # yanlış bir dosya seçildiğinde eşleşme SIFIR olmuyor (ortak Türkçe
    # kelimeler) ve eski kod sessizce devam edip BAŞKA bir şarkının sözlerini
    # aradeğerle uydurulmuş zamanlarla yayınlıyordu. Bkz. LyricsMismatch.
    if oran < min_esleme_orani:
        raise LyricsMismatch(
            f"{lyrics_md_path}: ASR ile sözler uyuşmuyor — gerçek sözlerin "
            f"{len(real_words)} kelimesinden yalnızca {eslesen}'i ASR'de "
            f"bulundu (oran {oran:.3f} < {min_esleme_orani:.2f}). "
            "Muhtemelen YANLIŞ şarkının sözler dosyası eşleşti; altyazı "
            "yayınlanmadı.")

    real_time = [None] * len(real_words)
    for asr_start, real_start, size in blocks:
        for k in range(size):
            real_time[real_start + k] = asr_words[asr_start + k][2]

    n = len(real_time)
    known_idx = [i for i, t in enumerate(real_time) if t is not None]
    if not known_idx:
        # Pratikte ERİŞİLMEZ (oran kapısı sıfır eşleşmeyi zaten yakalar) ama
        # kapı `min_esleme_orani=0` ile kapatılabildiği için duruyor.
        raise LyricsMismatch(
            "Hiç eşleşen kelime bulunamadı — sözler dosyası/ASR alakasız olabilir."
        )
    last_asr_time = asr_words[-1][2] if asr_words else 0.0

    for i in range(n):
        if real_time[i] is not None:
            continue
        prev_i = max((k for k in known_idx if k < i), default=None)
        next_i = min((k for k in known_idx if k > i), default=None)
        if prev_i is None and next_i is None:
            real_time[i] = 0.0
        elif prev_i is None:
            # Şarkının başındaki eşleşmeyen kelimeler: video başlangıcı (0.0,
            # sanal -1 indeksi) ile ilk bilinen eşleşme arasında orantılı yay
            # (eskiden hepsine next_i'nin zamanı verilirdi -> hepsi aynı anda
            # başlıyor gibi görünürdü).
            frac = (i + 1) / (next_i + 1)
            real_time[i] = real_time[next_i] * frac
        elif next_i is None:
            # Şarkının sonundaki eşleşmeyen kelimeler: son bilinen eşleşme ile
            # ASR'nin son bilinen kelime zamanı arasında orantılı yay (aynı
            # simetrik düzeltme, ters yönde).
            t0 = real_time[prev_i]
            frac = (i - prev_i) / (n - prev_i)
            real_time[i] = t0 + (last_asr_time - t0) * frac
        else:
            t0, t1 = real_time[prev_i], real_time[next_i]
            frac = (i - prev_i) / (next_i - prev_i)
            real_time[i] = t0 + (t1 - t0) * frac

    cue_word_indices = {}
    for i, (_, _, ci) in enumerate(real_words):
        cue_word_indices.setdefault(ci, []).append(i)

    out_cues = []
    for ci, cue_text in enumerate(real_cues):
        idxs = cue_word_indices.get(ci, [])
        if not idxs:
            continue
        start = real_time[idxs[0]]
        wc = len(idxs)
        if ci + 1 < len(real_cues) and cue_word_indices.get(ci + 1):
            next_start = real_time[cue_word_indices[ci + 1][0]]
        else:
            next_start = real_time[idxs[-1]] + (1.2 + 0.35 * wc)
        end = next_start

        min_dur = 0.6 + 0.15 * wc
        if end < start + min_dur:
            end = start + min_dur
        max_reasonable_dur = 1.2 + 0.7 * wc
        if end - start > max_reasonable_dur:
            start = max(start, end - max_reasonable_dur)

        out_cues.append((start, end, cue_text))

    for i in range(len(out_cues) - 1):
        s, e, t = out_cues[i]
        next_s = out_cues[i + 1][0]
        if e > next_s:
            out_cues[i] = (s, next_s, t)

    out_cues = _merge_degenerate_cues(out_cues)

    if out_cues and video_duration:
        last_start, last_end, last_text = out_cues[-1]
        if last_end > video_duration:
            out_cues[-1] = (last_start, video_duration, last_text)

    return out_cues


if __name__ == "__main__":
    srt_path, lyrics_path, duration, out_path = sys.argv[1:5]
    cues = align(srt_path, lyrics_path, float(duration))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(format_srt(cues))
    print(f"{len(cues)} cue yazıldı -> {out_path}")
