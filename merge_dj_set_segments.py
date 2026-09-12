"""dj_sets/<set-adı>/_segments/ altındaki, Suno'da tek tek indirilmiş ayrı
parçaları (ör. "City Pulse Se 1.wav" ... "City Pulse Se 16.wav") dosya adındaki
sıra numarasına göre sıralayıp kısa crossfade'lerle TEK, kesintisiz bir
audio.wav'da birleştirir.

Kullanım:
    python merge_dj_set_segments.py "dj_sets/City Pulse Set"
    python merge_dj_set_segments.py "dj_sets/City Pulse Set" --crossfade 3

NEDEN: Suno'nun tek bir üretimde/extend'de üretebildiği süre sınırlı (~4-8 dk),
saatlik bir DJ seti onlarca ayrı parçaya (Extend zinciri) bölünüp üretiliyor.
Suno'nun kendi "birleştirme" özelliği bu ortamda güvenilir bulunamadı, bu yüzden
her parça ayrı ayrı indirilip burada ffmpeg'in acrossfade filtresiyle (sert
kesme yerine yumuşak geçiş) birleştiriliyor.
"""

import argparse
import os
import re
import subprocess
import sys

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

_NUM_RE = re.compile(r"(\d+)\.wav$", re.IGNORECASE)


def _sorted_segments(segments_dir: str) -> list[str]:
    files = [f for f in os.listdir(segments_dir) if f.lower().endswith(".wav")]
    numbered = []
    for f in files:
        m = _NUM_RE.search(f)
        if not m:
            print(f"UYARI: '{f}' dosya adında sıra numarası bulunamadı, atlanıyor.")
            continue
        numbered.append((int(m.group(1)), f))
    numbered.sort(key=lambda x: x[0])
    if len(numbered) != len(set(n for n, _ in numbered)):
        raise RuntimeError("Birden fazla dosyada AYNI sıra numarası bulundu — dosya adlarını kontrol et.")
    return [os.path.join(segments_dir, f) for _, f in numbered]


def _probe_format(path: str) -> tuple[str, str, str]:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0",
         "-show_entries", "stream=sample_rate,channels,codec_name",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    parts = result.stdout.strip().splitlines()
    if len(parts) < 3:
        raise RuntimeError(f"{path}: ffprobe formatı okunamadı ({result.stderr.strip()})")
    return tuple(parts[:3])  # codec_name, sample_rate, channels (ffprobe -show_entries sırası)


def merge(set_dir: str, crossfade: float = 3.0) -> str:
    segments_dir = os.path.join(set_dir, "_segments")
    if not os.path.isdir(segments_dir):
        raise FileNotFoundError(f"{segments_dir} bulunamadı.")

    files = _sorted_segments(segments_dir)
    if len(files) < 2:
        raise RuntimeError(f"En az 2 parça gerekiyor, {len(files)} bulundu.")

    print(f"{len(files)} parça bulundu, sırayla:")
    for i, f in enumerate(files, 1):
        print(f"  {i}. {os.path.basename(f)}")

    # Preflight: hepsi aynı sample_rate/kanal/codec'te mi (acrossfade bunu gerektiriyor)
    formats = {f: _probe_format(f) for f in files}
    distinct = set(formats.values())
    if len(distinct) > 1:
        lines = "\n".join(f"  {os.path.basename(f)}: {fmt}" for f, fmt in formats.items())
        raise RuntimeError(f"Parçalar arasında format uyuşmazlığı var (codec, sample_rate, kanal):\n{lines}")

    output_path = os.path.join(set_dir, "audio.wav")

    cmd = ["ffmpeg", "-y"]
    for f in files:
        cmd += ["-i", f]

    filter_parts = []
    prev_label = "0:a"
    for i in range(1, len(files)):
        out_label = f"a{i}" if i < len(files) - 1 else "aout"
        filter_parts.append(f"[{prev_label}][{i}:a]acrossfade=d={crossfade}:c1=tri:c2=tri[{out_label}]")
        prev_label = out_label
    filter_complex = ";".join(filter_parts)

    cmd += ["-filter_complex", filter_complex, "-map", "[aout]", output_path]

    print(f"\nffmpeg ile birleştiriliyor (crossfade={crossfade}s, {len(files)} parça)...")
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        print(result.stderr[-4000:])
        raise RuntimeError("ffmpeg birleştirme başarısız oldu.")

    print(f"\nTamam: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="DJ Famous set parçalarını crossfade'li birleştirir.")
    parser.add_argument("set_dir", help='Set klasörü, ör. "dj_sets/City Pulse Set"')
    parser.add_argument("--crossfade", type=float, default=3.0, help="Geçiş süresi (saniye, varsayılan: 3)")
    args = parser.parse_args()

    output_path = merge(args.set_dir, args.crossfade)

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", output_path],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    duration = float(probe.stdout.strip())
    minutes = int(duration // 60)
    seconds = int(duration % 60)
    print(f"Toplam süre: {minutes}:{seconds:02d}")


if __name__ == "__main__":
    main()
