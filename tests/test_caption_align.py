"""caption_align.py testleri — gerçek ASR/YouTube API'sine dokunmadan, sentetik
SRT + sözler metniyle çalışır.

Kritik davranışlar:
1. Aynı gerçek söz satırı (nakarat tekrarı) ASR'de birden fazla kez geçtiğinde
   her tekrar KENDİ ASR anındaki zamanı almalı (eski oransal yöntemin
   çözemediği, bu yüzden align_v2'nin difflib'e geçme sebebi).
2. ASR'nin KAÇIRDIĞI şarkı başı/sonu kelimeleri TEK bir ortak zamana
   çökmemeli (Kumdan Denize'nin elle düzeltilen sıfır-süreli ilk cue'sunun
   kök nedeniydi, bkz. modüldeki not).
3. _merge_degenerate_cues her koşulda (neden sıfır/çok kısa süreli bir cue
   üretilmiş olursa olsun) onu komşusuyla birleştirmeli — otomasyon bunu
   insan gözden geçirmesi olmadan yayınlayacağı için bu son bir güvenlik ağı.

NOT: fixture metinleri kasıtlı olarak ASCII (Türkçe aksansız) — ASR ve gerçek
sözler arasında YAZIM birebir aynı olmalı ki test, hizalama mantığını
(kelime eşleşmesi/enterpolasyon) test etsin, tesadüfi bir noktalama/aksan
farkını değil. (_norm_word noktalamayı temizler ama ı/ş/ğ gibi harfleri
ASCII'ye çevirmez — gerçek ASR çıktısı bu harfleri doğru üretiyor, bkz.
2026-09-06 elle inceleme, bu yüzden algoritmada bir transliterasyon adımına
gerek yok.)
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import caption_align


def _write(tmp_path, name, content):
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return str(path)


def _lyrics_md(clean_lyrics: str) -> str:
    return f"## Temiz Sözler\n```\n{clean_lyrics}\n```\n"


# --- temel eşleşme ---

def test_matched_word_uses_asr_time(tmp_path):
    asr = (
        "1\n00:00:01,000 --> 00:00:03,000\nmerhaba dunya\n\n"
        "2\n00:00:03,000 --> 00:00:05,000\niyi gunler\n"
    )
    asr_path = _write(tmp_path, "asr.srt", asr)
    lyrics_path = _write(tmp_path, "l.md", _lyrics_md("merhaba dunya, iyi gunler"))

    cues = caption_align.align(asr_path, lyrics_path, video_duration=10)
    assert len(cues) == 2
    assert cues[0][2] == "merhaba dunya"
    assert cues[0][0] == 1.0
    assert cues[1][2] == "iyi gunler"
    assert cues[1][0] > cues[0][0]


def test_repeated_chorus_lines_get_distinct_asr_times(tmp_path):
    """Aynı 2 kelimelik nakarat ("kumdan denize") iki kez geçiyor — ama her
    tekrarın ETRAFINDAKİ satırlar farklı (gece başlar/güneş batar), bu yüzden
    difflib'in tüm şarkıyı TEK bir bütün olarak eşlemesi her tekrarı KENDİ
    kronolojik ASR anına bağlamaya zorlanıyor. (Etraf bağlamı olmadan, iki
    kelimelik saf bir tekrarın hangi ASR oluşumuna denk geldiği difflib için
    doğası gereği belirsizdir — bu test o dejenere durumu değil, gerçek
    şarkılardaki gibi bağlamla ayrışan durumu hedefliyor.)"""
    asr = (
        "1\n00:00:01,000 --> 00:00:02,000\ngece baslar\n\n"
        "2\n00:00:04,000 --> 00:00:06,000\nkumdan denize\n\n"
        "3\n00:00:20,000 --> 00:00:21,000\ngunes batar\n\n"
        "4\n00:00:40,000 --> 00:00:42,000\nkumdan denize\n\n"
        "5\n00:00:50,000 --> 00:00:51,000\nyildiz duser\n"
    )
    asr_path = _write(tmp_path, "asr.srt", asr)
    lyrics_path = _write(
        tmp_path, "l.md",
        _lyrics_md("gece baslar, kumdan denize, gunes batar, kumdan denize, yildiz duser"),
    )

    cues = caption_align.align(asr_path, lyrics_path, video_duration=60)
    assert len(cues) == 5
    kumdan_cues = [c for c in cues if c[2] == "kumdan denize"]
    assert len(kumdan_cues) == 2
    # iki tekrar da BİRBİRİNDEN farklı ve doğru sırada (ilki ~20s'lik
    # "gunes batar" satırından önce, ikincisi ~50s'lik "yildiz duser"
    # satırından önce) — eski oransal yöntem ikisini de tek bir ortak
    # zamana/yanlış sıraya düşürebiliyordu.
    assert kumdan_cues[0][0] < kumdan_cues[1][0]
    assert kumdan_cues[1][0] - kumdan_cues[0][0] > 10


# --- şarkı başı/sonu eşleşmeyen kelimeler (sanal çapa) ---

def test_leading_unmatched_words_do_not_collapse_to_same_time(tmp_path):
    """ASR ilk satırı hiç duymamışsa (kaçırmış), gerçek sözlerin ilk
    cue'sundaki kelimeler videonun başından itibaren orantılı yayılmalı —
    hepsi next_i'nin zamanına çökmemeli (Kumdan Denize'nin elle düzeltilen
    sıfır-süreli ilk cue'sunun kök nedeni buydu)."""
    asr = (
        "1\n00:00:18,000 --> 00:00:20,000\nsehir uyanir\n\n"
        "2\n00:00:23,000 --> 00:00:25,000\nkumda izler\n"
    )
    asr_path = _write(tmp_path, "asr.srt", asr)
    # "motor susar" ASR'de hiç yok (kaçırılmış) — gerçek sözlerde ilk cue.
    lyrics_path = _write(tmp_path, "l.md", _lyrics_md("motor susar, sehir uyanir, kumda izler"))

    cues = caption_align.align(asr_path, lyrics_path, video_duration=30)
    assert len(cues) == 3
    assert cues[0][2] == "motor susar"
    assert cues[1][2] == "sehir uyanir"
    # "motor susar", "sehir uyanir"den ÖNCE ve FARKLI bir zaman almalı — eski
    # kodda ikisi de next_i'nin (sehir uyanir'in ilk bilinen ASR anı) aynı
    # zamanına çöküyordu.
    assert cues[0][0] < cues[1][0]
    # iki cue'nun süresi de sıfır/negatif olmamalı.
    assert cues[0][1] - cues[0][0] > 0
    assert cues[1][1] - cues[1][0] > 0


def test_trailing_unmatched_words_spread_toward_last_known_asr_time(tmp_path):
    asr = (
        "1\n00:00:01,000 --> 00:00:03,000\nmerhaba dunya\n\n"
        "2\n00:00:05,000 --> 00:00:07,000\niyi gunler\n"
    )
    asr_path = _write(tmp_path, "asr.srt", asr)
    # "hosca kal" ASR'de hiç yok (şarkının sonunda kaçırılmış).
    lyrics_path = _write(tmp_path, "l.md", _lyrics_md("merhaba dunya, iyi gunler, hosca kal"))

    cues = caption_align.align(asr_path, lyrics_path, video_duration=20)
    assert len(cues) == 3
    assert cues[2][2] == "hosca kal"
    # son cue, ikinci cue'dan SONRA başlamalı (aynı zamana çökmemeli).
    assert cues[2][0] > cues[1][0]


# --- son güvenlik ağı: dejenere (sıfıra yakın süreli) cue birleştirme ---

def test_merge_degenerate_cues_merges_zero_duration_into_previous():
    cues = [(1.0, 5.0, "önce"), (5.0, 5.0, "sıfır süreli"), (5.0, 9.0, "sonra")]
    merged = caption_align._merge_degenerate_cues(cues)
    assert len(merged) == 2
    assert merged[0] == (1.0, 5.0, "önce sıfır süreli")
    assert merged[1] == (5.0, 9.0, "sonra")


def test_merge_degenerate_cues_handles_degenerate_first_cue():
    cues = [(2.0, 2.0, "sıfır"), (2.0, 6.0, "sonraki")]
    merged = caption_align._merge_degenerate_cues(cues)
    assert len(merged) == 1
    assert merged[0] == (2.0, 6.0, "sıfır sonraki")


def test_no_matching_words_raises_instead_of_silently_misaligning(tmp_path):
    asr_path = _write(
        tmp_path, "asr.srt", "1\n00:00:01,000 --> 00:00:03,000\nalakasiz kelimeler\n"
    )
    lyrics_path = _write(tmp_path, "l.md", _lyrics_md("tamamen farkli bir dil xyzq"))
    with pytest.raises(RuntimeError):
        caption_align.align(asr_path, lyrics_path, video_duration=10)
