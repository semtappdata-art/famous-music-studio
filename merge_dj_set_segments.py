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

KESİNTİSİZ GEÇİŞ KURALI (2026-09-14, kullanıcı kararı — bu kural BU SETE ÖZGÜ
DEĞİL, bundan sonraki TÜM DJ seti birleştirmelerinde GEÇERLİ):
  1. Her parçanın baş/kuyruk dijital sessizliği before crossfade KIRPILIR
     (`_kenar_sessizlik` + `atrim`). Suno parçaları kenarlarda 0.06-0.81 sn
     sessizlik taşıyor; düz `tri` crossfade o sessizlik üstüne bindiğinde
     "müzik → sessizlik → müzik" gibi fark edilir bir boşluk üretiyordu.
     Kırpılmadan önce crossfade iki tarafındaki "müzik" aslında kısmen
     dijital sessizlikti. Kırpınca overlap iki yanda da GERÇEK ses içine
     düşüyor — geçiş algılanmıyor.
  2. Eğri `tri` (linear) değil `qsin` (quarter-sine, equal-power). Linear
     crossfade'ın orta noktasında iki taraf da %50'deyken sonuç gücü eşit
     güçte değildir → ~3 dB'lik fark edilir bir DİP oluşur. `qsin/qsin`
     toplam gücü sabit tutar, geçiş sırasında müzik seviyesi oynamaz.
  3. İlk parçanın baş sessizliği de kırpılır (set müzikle AÇILIR); SON parçanın
     kuyruk sessizliği KORUNUR (set doğal bitişle sönümlenir — SUNO.md
     kapanış kuralı).
  4. Crossfade, kırpılmış en kısa parçanın yarısını AŞAMAZ (ffmpeg overlap
     için iki tarafta da süre ister); tavanlanırsa log'a düşer.
  5. Bir parça kırpma sonucu 1 sn'den kısaysa (veya sessizliği ölçülemezse)
     O PARÇA için kırpma YAPILMAZ — bozuk ölçüm müziği kesmemeli.
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
_PARANTEZ_ADI_RE = re.compile(r"\(([^()]*)\)")

BOLUM_DOSYASI = "bolumler.json"

# Konfigürasyon: aynı eşik render'ın önünde de kullanılıyor (ffmpeg_utils.
# bastaki_sessizlik) — iki yer ayrı eşik tutarsa davranış ayrışır. Buradan
# config import etmek yerine değeri kopyaladık; config.py'ye bağımlılık
# eklemek test tarafında yük yaratıyor. Değer değiştirilirse İKİ YERDE.
_SESSIZLIK_ESIGI = "-50dB"
_KIRP_PAYI = 0.05          # sessizliği birebir değil, ucundan 0.05 sn içeriden kes
_CROSSFADE_EGRI = "qsin"   # equal-power eğri — ortada dip YOK


def _sure(path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        raise RuntimeError(f"{path}: süre okunamadı ({result.stderr.strip()})")


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


def _bolum_adi(dosya_yolu: str) -> str:
    """Bölüm adı dosya adındaki parantezden gelir ("Deep Medusa (Dive) 04.wav"
    -> "Dive"); parantez yoksa uzantısız dosya adı. YouTube chapter satırında
    görünen ad budur."""
    ad = os.path.splitext(os.path.basename(dosya_yolu))[0]
    parantezler = _PARANTEZ_ADI_RE.findall(ad)
    if parantezler:
        return parantezler[-1].strip()
    return re.sub(r"\s*\d+\s*$", "", ad).strip() or ad


def _mmss(sn: float) -> str:
    """123.4 -> "2:03" (YouTube chapter damgası; derleme._mmss ile aynı kural,
    tek sahip BURASI — derleme modülü kendi kopyasını tutuyor, iki yönde de
    import yok)."""
    sn = int(sn)
    if sn < 3600:
        return "%d:%02d" % (sn // 60, sn % 60)
    return "%d:%02d:%02d" % (sn // 3600, (sn % 3600) // 60, sn % 60)


def bolum_baslangiclari(kesimler: list[tuple[float, float]], crossfade: float) -> list[float]:
    """Kırpılmış [(bas, son)] listesi + crossfade -> her parçanın BİRLEŞİK
    sesteki başlangıç saniyesi. acrossfade her birleşmede `crossfade` kadar
    overlap yediği için i+1'in başı i'nin kırpılmış süresinden o kadar erkene
    çekilir (derleme.zaman_damgalari ile aynı aritmetik, aynı gerekçe)."""
    baslar, t = [], 0.0
    for i, (s, e) in enumerate(kesimler):
        baslar.append(round(t, 1))
        if i < len(kesimler) - 1:
            t += (e - s) - crossfade
    return baslar


def _atomik_json_yaz(yol: str, veri: dict) -> None:
    """state_io.durum_yaz ile aynı desen (.tmp + fsync + os.replace) ama
    rastgele bir dosya için — bolumler.json yarım yazılırsa açıklama hattı
    bozuk damga basar."""
    tmp = yol + ".tmp"
    import json as _json
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(_json.dumps(veri, ensure_ascii=False, indent=1))
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, yol)


def _kenar_sessizlik(path: str) -> tuple[float, float]:
    """(bas_sessizlik_sn, son_sessizlik_sn) — silеnce'detect ile ölçülür.

    Ölçülemeyen/hatalı dosyada (0.0, 0.0) döner: bu fonksiyonun arızası asla
    müziği kesmemeli. Ucundan `_KIRP_PAYI` kadarı içeriden alınır; atağın ilk
    milisaniyesi (seste yükselme ZATEN silence_end'de başlar) korunur.
    """
    toplam = _sure(path)
    cmd = [
        "ffmpeg", "-hide_banner", "-nostats", "-i", path,
        "-af", f"silencedetect=noise={_SESSIZLIK_ESIGI}:d=0.06",
        "-f", "null", "-",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    except OSError:
        return 0.0, 0.0
    if result.returncode != 0:
        return 0.0, 0.0

    bloklar = []  # (start, end)
    simdiki = None
    for line in result.stderr.splitlines():
        if "silence_start:" in line:
            try:
                simdiki = float(line.split("silence_start:")[1].split("|")[0].strip())
            except (ValueError, IndexError):
                simdiki = None
        elif simdiki is not None and "silence_end:" in line:
            try:
                bitis = float(line.split("silence_end:")[1].split("|")[0].strip())
            except (ValueError, IndexError):
                bitis = None
            if bitis is not None:
                bloklar.append((simdiki, bitis))
                simdiki = None

    if not bloklar:
        return 0.0, 0.0

    bas = bob_son = 0.0
    son = son_bas = 0.0
    if bloklar[0][0] <= 0.05:
        bas = max(0.0, bloklar[0][1] - _KIRP_PAYI)
    if bloklar[-1][1] >= toplam - 0.05:
        son = max(0.0, toplam - bloklar[-1][0] - _KIRP_PAYI)
    return min(bas, toplam), min(son, toplam)


def _kesimler(bilgiler: list[tuple[float, float, float]]) -> list[tuple[float, float]]:
    """[(bas_sessizlik, son_sessizlik, toplam)] -> [(atrim_start, atrim_end)]

    İlk parçanın başı ve SON parçanın sonu koruma mantığı BURADA:
    - her parçanın baş sessizliği kırpılır (set müzikle açılır);
    - SON parçanın kuyruğu hariç, parça uçlarındaki sessizlik kırpılır;
    - kırpma sonucu 1 sn'den kısa kalan parça HIÇ kırpılmaz.
    """
    n = len(bilgiler)
    sonuclar = []
    for i, (bas_sil, son_sil, toplam) in enumerate(bilgiler):
        start = min(bas_sil, toplam)
        end = toplam
        if i < n - 1:
            end = max(0.0, toplam - son_sil)
        if end - start < 1.0:   # ölçüm bozuksa/gereksizse: kırpma yok
            start, end = 0.0, toplam
        else:
            start, end = round(start, 3), round(end, 3)
        sonuclar.append((start, end))
    return sonuclar


def _filtre_grafigi(kesimler: list[tuple[float, float]], crossfade: float) -> str:
    """Per-parça `atrim` + `acrossfade` zincirini kurar.

    Eğri `_CROSSFADE_EGRI` (equal-power qsin) — bkz. modül docstring'i.
    """
    parcalar = []
    for i, (s, e) in enumerate(kesimler):
        parcalar.append(f"[{i}:a]atrim=start={s:.3f}:end={e:.3f},asetpts=PTS-STARTPTS[a{i}]")
    onceki = "a0"
    for i in range(1, len(kesimler)):
        etiket = "aout" if i == len(kesimler) - 1 else f"b{i}"
        parcalar.append(
            f"[{onceki}][a{i}]acrossfade=d={crossfade:.2f}:c1={_CROSSFADE_EGRI}:c2={_CROSSFADE_EGRI}[{etiket}]"
        )
        onceki = etiket
    return ";".join(parcalar)


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

    # Kenar sessizliği ölç + kırpma sınırlarını hesapla
    bilgiler = []
    for f in files:
        bas, son = _kenar_sessizlik(f)
        bilgiler.append((bas, son, _sure(f)))
    kesimler = _kesimler(bilgiler)
    print("Kenar sessizlik kırpma:")
    for (bas, son, toplam), f, (s, e) in zip(bilgiler, files, kesimler):
        print(f"  {os.path.basename(f)}: toplam {toplam:.1f}s, baş-sessizlik {bas:.2f}s, "
              f"son-sessizlik {son:.2f}s -> atrim [{s:.2f}, {e:.2f}]")

    # Crossfade'i en kısa (kırpılmış) parçayla tavanla
    min_sure = min(e - s for s, e in kesimler)
    if crossfade > min_sure / 2:
        eski = crossfade
        crossfade = max(0.5, min_sure / 2)
        print(f"UYARI: crossfade {eski}s en kısa kırpılmış parçaya sığmıyor "
              f"({min_sure:.1f}s) -> {crossfade}s'e tavanlandı.")

    output_path = os.path.join(set_dir, "audio.wav")
    cmd = ["ffmpeg", "-y"]
    for f in files:
        cmd += ["-i", f]
    filter_complex = _filtre_grafigi(kesimler, crossfade)
    cmd += ["-filter_complex", filter_complex, "-map", "[aout]", output_path]

    print(f"\nffmpeg ile birleştiriliyor (crossfade={crossfade}s, {_CROSSFADE_EGRI}/{_CROSSFADE_EGRI}, "
          f"{len(files)} parça)...")
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        print(result.stderr[-4000:])
        raise RuntimeError("ffmpeg birleştirme başarısız oldu.")

    print(f"\nTamam: {output_path}")

    # BÖLÜM DAMGALARI (2026-09-14): kırpma + crossfade düşülmüş GERÇEK
    # başlangıçlar `bolumler.json`'a yazılıyor; upload/youtube_upload.py
    # buradan okuyup açıklamaya YouTube chapter bloğu basıyor. Merge
    # ARİTMETİĞİNİN TEK SAHİBİ burası — damgayı render/upload tarafında
    # yeniden hesaplamak ikinci bir saat demek (sessiz kayma tuzağı).
    baslar = bolum_baslangiclari(kesimler, crossfade)
    parcalar = [
        {"sira": i + 1, "ad": _bolum_adi(f), "bas": b, "zaman": _mmss(b)}
        for i, (f, b) in enumerate(zip(files, baslar))
    ]
    import time as _time
    _atomik_json_yaz(
        os.path.join(set_dir, BOLUM_DOSYASI),
        {"uredi_at": _time.strftime("%Y-%m-%dT%H:%M:%S"),
         "crossfade_sn": crossfade, "parcalar": parcalar},
    )
    print(f"Bölüm damgaları: {BOLUM_DOSYASI} ({len(parcalar)} parça, "
          f"ilk 3: {', '.join(p['zaman'] + ' ' + p['ad'] for p in parcalar[:3])}...)")
    return output_path


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


def main():
    parser = argparse.ArgumentParser(
        description="DJ Famous set parçalarını KESİNTİSİZ crossfade'li birleştirir "
                    "(kenar sessizlik kırpma + equal-power qsin eğri).")
    parser.add_argument("set_dir", help='Set klasörü, ör. "dj_sets/City Pulse Set"')
    parser.add_argument("--crossfade", type=float, default=3.0, help="Geçiş süresi (saniye, varsayılan: 3)")
    args = parser.parse_args()

    output_path = merge(args.set_dir, args.crossfade)

    duration = _sure(output_path)
    minutes = int(duration // 60)
    seconds = int(duration % 60)
    print(f"Toplam süre: {minutes}:{seconds:02d}")


if __name__ == "__main__":
    main()