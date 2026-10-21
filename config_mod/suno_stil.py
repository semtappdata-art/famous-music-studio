import hashlib
import json
import os
import sys
import unicodedata
from typing import Optional

# MCP wrapper (opsiyonel, style optimize için)
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from suno_mcp_wrapper import SunoMCP
    _MCP_AVAILABLE = True
except Exception:
    _MCP_AVAILABLE = False

# --- Suno stil tarifi: mix / vokal / düzenleme ifadeleri havuzu (2026-09-13) --
# `suno_kalite_onerileri.md` §2 ve §7: mix cümlesi her şarkıya birebir
# kopyalanırsa bütün katalogda aynı dizi tekrarlanır (şablon izi, "inauthentic
# content" riski). Seçim `suno_stil.py --proje "<ad>"` ile: proje adının
# sha1'inden DETERMİNİSTİK, her şarkıda farklı alt küme ve sıra.
# KURALLAR (tests/test_suno_stil.py kilitli): sanatçı adı, "Suno" ya da AI
# vurgusu YOK; yalnız küçük harf ASCII; `wide vocal` YOK (vokal merkezde
# kalmalı, A/B betiğinin merkez/yan ölçütünü bozar). Suno'nun bu ifadelere
# tepkisi resmî olarak belgelenmiş değil [YAYGIN].
# DJ setleri kapsam dışı: onların tarifi `SET_STILLERI` içinde.
STIL_MIX_ADET = 3
STIL_IFADE_HAVUZU = {
    "pop": {
        "mix": ["polished radio mix", "smooth controlled highs", "punchy tight drums",
                "modern mastered sound", "warm balanced low end", "clean glossy synths"],
        "vokal": ["clear upfront lead vocal", "intelligible turkish diction",
                  "crisp vocal consonants", "natural vocal presence with light reverb"],
        "duzenleme": ["concise radio-length arrangement", "no long instrumental breaks",
                      "quick hook within the first verse", "dynamic lift into the chorus"],
    },
    "rock": {
        "mix": ["wide stereo guitars", "live drum kit", "no harsh cymbals",
                "warm analog mix", "punchy tight drums", "controlled guitar distortion"],
        "vokal": ["clear upfront lead vocal", "intelligible turkish diction",
                  "vocal sits above the guitars", "dry intimate vocal in the verses"],
        "duzenleme": ["concise radio-length arrangement", "no long guitar solos",
                      "short instrumental intro", "dynamic build into the final chorus"],
    },
    "elektronik": {
        "mix": ["smooth controlled highs", "tight sidechained low end", "clean punchy kick",
                "wide stereo synth pads", "modern mastered sound", "no harsh hi-hats"],
        "vokal": ["clear upfront lead vocal", "intelligible turkish diction",
                  "airy but centered vocal", "crisp vocal consonants"],
        "duzenleme": ["concise radio-length arrangement", "no long instrumental breaks",
                      "short build before the drop", "vocal hook returns after the drop"],
    },
    "akustik": {
        "mix": ["warm analog mix", "natural room ambience", "smooth controlled highs",
                "close-miked acoustic guitar", "gentle dynamic range", "soft rounded low end"],
        "vokal": ["dry intimate vocal", "intelligible turkish diction",
                  "clear upfront lead vocal", "breath and texture kept natural"],
        "duzenleme": ["concise radio-length arrangement", "no long instrumental breaks",
                      "sparse verses, fuller chorus", "gentle build into the last chorus"],
    },
    "hiphop": {
        "mix": ["punchy tight drums", "deep clean 808", "modern mastered sound",
                "smooth controlled highs", "crisp snare", "uncluttered low mids"],
        "vokal": ["clear upfront lead vocal", "intelligible turkish diction",
                  "dry upfront rap delivery", "crisp vocal consonants"],
        "duzenleme": ["concise radio-length arrangement", "no long instrumental breaks",
                      "hook arrives early", "beat switch kept short"],
    },
    "arabesk": {
        "mix": ["warm analog mix", "lush strings in the background", "smooth controlled highs",
                "clear darbuka groove", "no harsh cymbals", "reverb kept on strings, not vocal"],
        "vokal": ["clear upfront lead vocal", "intelligible turkish diction",
                  "expressive but controlled vibrato", "dry intimate vocal in the verses"],
        "duzenleme": ["concise radio-length arrangement", "no long instrumental breaks",
                      "short string intro", "emotional lift into the chorus"],
    },
}

# Görünürlük planı geri okuma yarışı (2026-09-13, Küllerimden Geç Shorts): videos.update
# 200 döndü ama hemen ardından okunan status ESKİ değeri verdi (YouTube yayılma gecikmesi)
# → sahte HATA + 3 sa retry. Geri okuma DENEME kez, arada BEKLEME sn.
GORUNURLUK_GERI_OKUMA_DENEME = 2
GORUNURLUK_GERI_OKUMA_BEKLEME_SN = 5


def _proj_hash(proje: str, seed: str) -> int:
    """Proje adından deterministik hash (pyhashseed etkilenmez)."""
    import unicodedata
    norm = proje.strip()
    # Unicode normalization (NFD) to handle different encodings of same character
    norm = unicodedata.normalize('NFD', norm)
    # Case folding - for now use lower() which works for most cases
    # Note: Proper Turkish case folding would require locale settings,
    # but for determinism we just need consistent results
    norm = norm.lower()
    # Ek entropy: seed + norm + length + sample of char codes
    extra = str(len(norm)) + ''.join(str(ord(c)) for c in norm[:10])
    return int(hashlib.sha1((seed + norm + extra).encode('utf-8')).hexdigest(), 16)


def _secim(havuz: list, k: int, proje: str, seed: str) -> list:
    """Havuzdan deterministik k eleman seç."""
    # Use SHA256 for better entropy
    norm = proje.strip().lower()
    # Unicode normalization (NFD) to handle different encodings of same character
    norm = unicodedata.normalize('NFD', norm)
    hash_input = (seed + norm).encode('utf-8')
    hash_digest = hashlib.sha256(hash_input).hexdigest()
    # Convert to integer
    h = int(hash_digest, 16)
    # Fisher-Yates shuffle deterministically seeded by hash
    items = list(range(len(havuz)))
    for i in range(len(items) - 1, 0, -1):
        # Generate deterministic "random" index from 0 to i
        h = (h * 1103515245 + 12345) & 0x7fffffff
        j = h % (i + 1)
        items[i], items[j] = items[j], items[i]
    return [havuz[items[i]] for i in range(k)]


def stil_ifadeleri(proje: str, tur: str) -> dict:
    """Proje ve tür için deterministik stil ifadeleri seç.
    
    Dönüş: {"mix": [...], "vokal": [...], "duzenleme": [...], "cumle": "..."}
    """
    if tur not in STIL_IFADE_HAVUZU:
        raise ValueError(f"Bilinmeyen tur: {tur}. Geçerli: {list(STIL_IFADE_HAVUZU.keys())}")
    
    havuz = STIL_IFADE_HAVUZU[tur]
    mix = _secim(havuz["mix"], STIL_MIX_ADET, proje, "mix")
    vokal = _secim(havuz["vokal"], 1, proje, "vokal")
    duzenleme = _secim(havuz["duzenleme"], 1, proje, "duzenleme")
    
    tum = mix + vokal + duzenleme
    return {
        "mix": mix,
        "vokal": vokal,
        "duzenleme": duzenleme,
        "cumle": ", ".join(tum),
    }


def optimize_style_mcp(raw_prompt: str) -> Optional[str]:
    """MCP ile ham style prompt'unu optimize et.
    
    Returns: Optimize edilmiş style string, MCP yoksa None.
    """
    if not _MCP_AVAILABLE:
        return None
    
    try:
        mcp = SunoMCP()
        # Async fonksiyonu sync bağlamda çalıştır
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(mcp.optimize_style(raw_prompt))
        finally:
            loop.close()
    except Exception:
        return None


def stil_ifadeleri_optimized(proje: str, tur: str, raw_prompt: str = "") -> dict:
    """Stil ifadeleri + MCP optimize (varsa)."""
    base = stil_ifadeleri(proje, tur)
    
    if raw_prompt:
        optimized = optimize_style_mcp(raw_prompt)
        if optimized:
            # MCP sonucunu base cumle'ye ekle
            base["cumle"] = base["cumle"] + ", " + optimized
            base["optimized"] = optimized
    
    return base


def turu_bul(proje: str, kokler: str = ".") -> Optional[str]:
    """Proje klasöründen meta.json okuyarak tur bul."""
    try:
        import json
        meta_path = os.path.join(kokler, proje, "meta.json")
        if os.path.exists(meta_path):
            with open(meta_path, encoding="utf-8") as f:
                meta = json.load(f)
                return meta.get("theme")
    except Exception:
        pass
    return None


if __name__ == "__main__":
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="Suno stil ifadeleri seçici")
    parser.add_argument("--proje", required=True, help="Proje adı (klasör adı)")
    parser.add_argument("--tur", help="Tür (pop, rock, elektronik, akustik, hiphop, arabesk)")
    parser.add_argument("--json", action="store_true", help="JSON çıktısı")
    parser.add_argument("--raw-prompt", help="Ham style prompt (MCP optimize için)")
    
    args = parser.parse_args()
    
    if args.tur:
        tur = args.tur
    else:
        tur = turu_bul(args.proje)
        if not tur:
            print("HATA: --tur belirtilmeli veya proje klasöründe meta.json olmalı", file=sys.stderr)
            sys.exit(1)
    
    result = stil_ifadeleri_optimized(args.proje, tur, args.raw_prompt or "")
    
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
    else:
        print("Mix:", " | ".join(result["mix"]))
        print("Vokal:", result["vokal"][0])
        print("Düzenleme:", result["duzenleme"][0])
        print("\nCümle:")
        print(result["cumle"])
        if "optimized" in result:
            print("\n[MCP Optimized]:", result["optimized"])