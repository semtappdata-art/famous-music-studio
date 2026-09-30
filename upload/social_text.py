"""Instagram/TikTok paylaşım metinleri (caption) için ortak şablon.

YouTube açıklamasından farklı olarak burada linkler yerine hashtag ağırlıklı,
kısa bir caption üretilir — Instagram/TikTok'ta caption içindeki linkler zaten
tıklanabilir değildir.

Özellikler
----------
* Deterministik havuzdan üretilen başlangıç metinleri (`build_caption`).
* Opsiyonel LLM‑enhancement katmanı (`_call_llm_for_caption` ve `ai_caption`).
* Güvenli loglama (`_safe_log`) – log hataları ana iş akışını kesmez.
* Tüm f‑string ifadeleri, JSON şablonundaki süslü parantezler için
  `{{` ve `}}` ile kaçıştırılmıştır; bu sayfada “unterminated f‑string”
  hatası üretmez.

Not
---
Prompt içinde JSON süslü parantezleri iki kez yazılması gerekir,
çünkü f‑string içinde `{` ve `}` ifade yerine geçirmek için ayrılmıştır.
Literal bir `{` veya `}` üretmek istiyorsak `{{` ya da `}}` kullanmalıyız.

"""

import collections
import difflib
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger("fms.social_text")

import config

# Sözler dosyası adı ile şarkı başlığının slug'ı arasında istenen en düşük
# benzerlik — `upload/youtube_captions.SLUG_BENZERLIK_ESIGI` ile AYNI değer ve
# AYNI gerekçe. O modülden İÇE AKTARILMIYOR, bilerek: `youtube_captions`
# googleapiclient/OAuth bağımlılıklarını çekiyor ve bu dosya (social_text) her
# platform yükleyicisinin ilk import'u — oraya OAuth bağımlılığı taşımak, ağ
# anahtarı olmayan bir ortamda caption üretimini bile kırardı. Eşiğin kendisi
# üç satırlık bir süzgeç; kopyalanan şey mantık değil, bir sayı.
SOZ_SLUG_BENZERLIK_ESIGI = 0.85

# Açıklamaya alınacak ardışık söz satırı sayısı. İki satır bir "beyit" —
# tek satır çoğu zaman bağlamsız ("Yine aynı yol"), üç satır açıklamanın
# üst kısmını blok metne çeviriyor.
SOZ_ALINTI_SATIR_SAYISI = 2
# Alıntı olarak KULLANILABİLİR bir söz satırının uzunluk aralığı (karakter):
# çok kısa satır ("Ah...") alıntı olarak bir şey anlatmıyor, çok uzun satır
# açıklamanın ilk ekranını dolduruyor.
SOZ_ALINTI_MIN_UZUNLUK = 10
SOZ_ALINTI_MAKS_UZUNLUK = 70
# Düet şarkılarında (CLAUDE.md: `arabesk` teması SABİT olarak düet) "Temiz
# Sözler" bölümündeki satırlar KİMİN söylediğini baştaki bir parantezle
# taşıyor: "(Kadın) Bir yara açtın...", "(Erkek) ...", "(İkisi) ...". Bu,
# `[Verse - Kadın]` etiketinin parantezli hâli — açıklamadaki bir alıntının
# başında "(Erkek)" yazması tam da CLAUDE.md'nin "etiket açıklamaya sızmasın"
# kararının kapatmak istediği görüntü. ÖLÇÜLDÜ: süzgeç yokken 19 şarkının
# 2'sinin alıntısı bu işaretle çıkıyordu (Yürek Yarası, Kader Ortakları).
# Uzunluk sınırı dar tutuldu: satır ORTASINDAKİ parantezler (geri vokal, ör.
# "...bırakma (bırakma)") sözün parçası, onlara dokunulmuyor.
SOZ_KONUSMACI_ISARETI = re.compile(r"^\([^()]{1,20}\)\s*")


# =============================================================================
# SAFE LOGGER - Prevents silent failures
# =============================================================================
def _safe_log(msg: str) -> None:
    """Logs messages safely - never raises exceptions that break main flow."""
    try:
        line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
        # cp1254 cannot print Unicode (emoji, Turkish chars) - replace errors
        try:
            print(line, flush=True)
        except UnicodeEncodeError:
            print(line.encode('utf-8', errors='replace').decode('utf-8'), flush=True)
        # Try to write to log file, but don't let failures break anything
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "social_text_llm.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        # If logging fails, we still want the main application to work
        pass

# =============================================================================
# LLM ENHANCEMENT HELPERS
# =============================================================================
def _call_llm_for_caption(meta: dict) -> str | None:
    """
    Safely calls LLM for caption enhancement.
    Returns None on any failure (triggering fallback).
    Never raises exceptions that break the main flow.
    """
    start_time = time.time()

    # Check if LLM enhancement is enabled via environment variable
    if os.environ.get("FAMOUS_MUSIC_USE_LLM_CAPTIONS", "").lower() not in ("1", "true", "yes"):
        _safe_log("LLM CAPTION SKIPPED: Feature disabled via env var")
        return None

    # Prepare LLM prompt
    title = meta.get("title", "Untitled")
    theme_key = meta.get("theme", config.DEFAULT_THEME)
    theme = config.THEMES.get(theme_key, config.THEMES[config.DEFAULT_THEME])

    # NOTE: JSON süslü parantezleri f‑string içinde literal olarak üretmek
    # için iki kez yazılmalıdır ({{ ve }}). Aksi takdirde Python
    # "unterminated f-string" hatası verir.
    prompt = f"""
You are a social media expert for Turkish music content.
Generate an engaging, platform-optimized caption for this Turkish song.

SONG INFORMATION:
- Title: {title}
- Theme/Genre: {theme.get('label', 'Unknown')} ({theme_key})
- Related Tags: {', '.join(theme.get('related', []))}

PLATFORM REQUIREMENTS (Generic Social Media):
- Create an engaging, authentic caption for Turkish music audience
- Character limit: Assume up to 2,200 characters (safe for most platforms)
- Must NOT contain clickable links (some platforms don't support them in captions)
- Should include relevant hashtags but not spammy (3-10 is ideal)
- Should feel authentic and engaging for Turkish music audience
- Ask questions or include calls-to-action when appropriate
- If unsure, fall back to safe, generic Turkish music caption

OUTPUT FORMAT (JSON ONLY):
Return ONLY a JSON object. Do NOT include any other text, markdown, or explanation.
{{
    "caption": "[The complete caption text]",
    "reasoning": "[Brief explanation]"
}}
""".strip()


    try:
        # Call Ollama with timeout
        result = subprocess.run(
            ["ollama", "run", "gemma2:2b", prompt],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60  # Local LLM can be slow on first call
        )

        duration_ms = (time.time() - start_time) * 1000

        # Check for successful response
        if result.returncode != 0:
            _safe_log(f"LLM CAPTION ERROR: {result.returncode} exit code after {duration_ms:.0f}ms")
            if result.stderr:
                _safe_log(f"  STDERR: {result.stderr[:100]}")
            return None

        response_text = result.stdout.strip()
        if not response_text:
            _safe_log(f"LLM CAPTION ERROR: Empty response after {duration_ms:.0f}ms")
            return None

        # Strip ANSI escape codes (Ollama terminal output)
        response_text = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', response_text)

        # Try to parse JSON response
        try:
            # Find JSON in response (in case there's extra text)
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_text = response_text[json_start:json_end]
            else:
                json_text = response_text
            # Sanitize: Ollama outputs raw newlines inside JSON strings
            # which are invalid JSON. Replace control chars inside strings
            # with spaces (outside strings, only remove problematic ones).
            sanitized = []
            in_string = False
            i = 0
            while i < len(json_text):
                ch = json_text[i]
                code = ord(ch)
                if ch == '"' and (i == 0 or json_text[i-1] != '\\'):
                    in_string = not in_string
                    sanitized.append(ch)
                elif in_string and code < 0x20:
                    sanitized.append(' ')
                elif in_string and code == 0x7f:
                    sanitized.append(' ')
                elif not in_string and code < 0x20 and ch not in ('\n', '\r', '\t'):
                    sanitized.append(' ')
                else:
                    sanitized.append(ch)
                i += 1
            json_text = ''.join(sanitized)
            parsed = json.loads(json_text)

            caption = parsed.get("caption", "").strip()
            if not caption:
                _safe_log("LLM CAPTION WARNING: Empty caption in response")
                return None

            # Validate caption looks reasonable (basic sanity check)
            if len(caption) < 10 or len(caption) > 5000:  # Reasonable bounds
                _safe_log(f"LLM CAPTION WARNING: Caption length ({len(caption)}) outside reasonable bounds")
                return None

            _safe_log(f"LLM CAPTION SUCCESS: Generated caption ({len(caption)} chars) in {duration_ms:.0f}ms")
            return caption

        except (json.JSONDecodeError, KeyError) as e:
            _safe_log(f"LLM CAPTION ERROR: Failed to parse JSON response: {e}")
            return None

    except subprocess.TimeoutExpired:
        _safe_log("LLM CAPTION ERROR: Request timed out after 12s")
        return None
    except Exception as e:
        _safe_log(f"LLM CAPTION ERROR: Unexpected error: {e}")
        return None

def hashtag(text: str) -> str:
    """Metinden hashtag: harf/rakam dışı her şey düşer, "&" -> "n".

    "&" DÜZELTMESİ (2026-09-13, HER platform): eskiden "&" de siliniyordu ve
    `pop` temasının ilişkili türü "R&B" `#RB` diye anlamsız bir etikete
    dönüşüyordu (Instagram/Shorts/TikTok/YouTube açıklamalarında). "R&B"nin
    yaygın hashtag yazımı `#RnB`. Başka hiçbir çıktı değişmedi — koruma:
    tests/test_social_text_hashtag.py (değişiklik öncesi arşivle karşılaştırma).
    """
    return "#" + "".join(ch for ch in str(text).replace("&", "n") if ch.isalnum())


def pick_deterministic(title: str, options: list, salt: int = 0) -> str:
    """Şarkı başlığına (+ salt) göre deterministik bir satır seçer — aynı şarkı hep
    aynı satırı alır, farklı şarkılar arasında çeşitlilik olur. salt, aynı başlıktan
    türeyen birden fazla seçimin (hook + engagement question gibi) her zaman aynı
    ikilide eşleşmemesi için kullanılıyor. Public (youtube_upload.build_snippet de
    aynı hook/soru havuzlarından aynı mantıkla seçim yapmak için kullanıyor)."""
    index = (sum(ord(ch) for ch in title) + salt) % len(options)
    return options[index]


def pick_subset(title: str, options: list, count: int, salt: int = 0) -> list:
    """Havuzdan `count` tane seçer — şarkı başlığına göre DETERMİNİSTİK.

    Aynı şarkı her koşuda aynı seti alır (yeniden üretim arşivi bozmasın),
    şarkılar arasında set değişir. Adım da başlığa göre kayıyor; sabit adımda
    havuzun hep aynı üçlüsü seçiliyordu.
    """
    n = len(options)
    if n == 0:
        return []
    count = min(count, n)
    seed = int(hashlib.sha256((title + str(salt)).encode("utf-8")).hexdigest()[:8], 16)
    adim = 1 if n < 2 else 1 + seed % (n - 1)
    secilen, i = [], 0
    while len(secilen) < count and i < n * 3:
        aday = options[(seed + i * adim) % n]
        if aday not in secilen:
            secilen.append(aday)
        i += 1
    return secilen


def dogrulanmis_sozler_yolu(title: str) -> str | None:
    """Başlığa GERÇEKTEN ait olduğu doğrulanmış `<slug>_sozler.md` (yoksa None).

    `stock_art.find_lyrics_file()` BULANIK eşleşiyor (ön-ek + difflib 0,85) ve
    orada yanlış eşleşmenin bedeli alakasız bir Pexels arama terimi. BURADA
    bedeli BAŞKA BİR ŞARKININ SÖZLERİNİ yayındaki açıklamaya yazmak — izleyici
    görür, biz görmeyiz. Bu yüzden sonuç ikinci kez süzülüyor
    (`upload/youtube_captions._sozler_dosyasi` ile AYNI desen, aynı eşik).

    `stock_art` TEMBEL import ediliyor: modül `requests` çekiyor ve bu dosya
    her platform yükleyicisinin ilk import'u; söz alıntısı bir SÜS, yokluğu
    yüklemeyi durdurmamalı.
    """
    if not title:
        return None
    try:
        import stock_art
    except Exception:
        return None
    try:
        yol = stock_art.find_lyrics_file(title)
        if not yol:
            return None
        slug = stock_art._slugify(title)
    except Exception:
        return None
    stem = os.path.basename(yol)[: -len("_sozler.md")]
    if stem == slug:
        return yol
    oran = difflib.SequenceMatcher(None, slug, stem).ratio()
    return yol if oran >= SOZ_SLUG_BENZERLIK_ESIGI else None


def sozlerden_alinti(meta: dict) -> str:
    """Şarkının KENDİ sözlerinden deterministik seçilmiş tek satırlık alıntı
    (bulunamazsa boş string).

    NEDEN VAR: YouTube uzun format açıklamalarının şarkıya özel TEK parçası
    başlıktı — 18 açıklamanın sekiz dolu satırından dördü birebir aynıydı ve
    açıklama başına ortak kelime payı %62,5 ölçüldü. Kanalın en büyük riski
    telif değil "toplu üretilmiş / özgün olmayan AI içerik" politikası; her
    videonun altında neredeyse aynı metin bunun en kolay görülen imzası.
    Havuzdan seçilen bir şablon satırı çeşitlilik sayısını iyileştirir ama
    açıklamaya GERÇEK bir içerik katmaz — şarkının kendi sözünden bir beyit
    katar.

    KAYNAK "## Temiz Sözler" BÖLÜMÜ, etiketli Suno sürümü DEĞİL: CLAUDE.md
    kararı gereği `[Verse 1]`/`[Chorus]` gibi köşeli parantez etiketleri
    açıklamaya SIZMAMALI (amatör görünüyordu, kullanıcı geri bildirimi) ve o
    bölüm tam bunun için var. `caption_align.extract_clean_lyrics()` İÇE
    AKTARILIYOR, kopyalanmıyor — aynı bölümü iki ayrı regex'le okumak, birinin
    sessizce bayatlaması demek. Yine de etiket taşıyan satırlar ayrıca
    süzülüyor: bir söz dosyasında "Temiz Sözler" bölümü elle yazılıyor ve
    etiket unutulabilir; süzgeç YOKSA o etiket doğrudan yayına çıkar.

    DETERMİNİSTİK: aynı şarkı her zaman aynı beyti alır (arşiv tutarlılığı —
    bir projeyi yeniden işlemek yayındaki açıklamadan farklı bir metin
    üretmemeli). Rastgelelik YOK.
    """
    if meta.get("derleme"):
        # Derlemenin KENDİ sözü yok; 13 ayrı şarkının sözü var. Birini seçip
        # derlemenin açıklamasına koymak izleyiciyi yanlış beklentiyle getirir
        # (bkz. başlıktaki "(Sözleri)" ekinin derlemelerde neden kaldırıldığı).
        return ""
    title = meta.get("title") or ""
    yol = dogrulanmis_sozler_yolu(title)
    if not yol:
        return ""
    try:
        with open(yol, encoding="utf-8") as f:
            icerik = f.read()
    except OSError:
        return ""
    try:
        import caption_align
    except Exception:
        return ""
    # Kendini "EKSİK / tamamlanmalı" diye işaretlemiş dosyadan alıntı yapılmaz:
    # o metin henüz insan onayından geçmemiş, yarım bir dize olabilir.
    if caption_align.lyrics_marked_incomplete(icerik):
        return ""
    temiz = caption_align.extract_clean_lyrics(icerik)
    if not temiz:
        return ""

    satirlar = []
    for ham in temiz.splitlines():
        s = ham.strip()
        if not s:
            continue
        if "[" in s or "]" in s:
            continue  # etiket sızıntısına karşı ikinci süzgeç (bkz. docstring)
        s = SOZ_KONUSMACI_ISARETI.sub("", s).strip()
        if not (SOZ_ALINTI_MIN_UZUNLUK <= len(s) <= SOZ_ALINTI_MAKS_UZUNLUK):
            continue
        satirlar.append(s)
    if len(satirlar) < SOZ_ALINTI_SATIR_SAYISI:
        return ""

    beyitler = []
    for i in range(len(satirlar) - SOZ_ALINTI_SATIR_SAYISI + 1):
        beyit = " / ".join(satirlar[i:i + SOZ_ALINTI_SATIR_SAYISI])
        if beyit not in beyitler:
            # Nakarat birebir tekrarlandığı için aynı beyit birden çok kez
            # aday oluyor; tekrarları elemek seçimi havuzun geneline yayıyor.
            beyitler.append(beyit)
    if not beyitler:
        return ""
    # Dış tırnak TİPOGRAFİK (“ ”), düz " DEĞİL: söz satırlarının kendisi düz
    # tırnak taşıyabiliyor (ör. Kırık Zincir: Bana "yapamazsın" dediler hep) —
    # düz tırnakla sarmak alıntının nerede bittiğini okunamaz hâle getiriyordu.
    return "“%s”" % pick_deterministic(title, beyitler, salt=29)


def resolve_language(meta: dict) -> str:
    """Paylaşım metinlerinin dilini belirler: meta.json'da açık bir "language"
    varsa o öncelikli (istisna/override için), yoksa Suno'da üretilen müziğin
    STİLİNE (theme) göre varsayılana düşülür (config.THEMES[...]["language"]) —
    kullanıcı isteği: dil hazırlığı stile göre otomatik olsun, her projede elle
    yazmaya gerek kalmasın. Hiçbiri yoksa "tr"."""
    if meta.get("language"):
        return meta["language"]
    theme_key = meta.get("theme", config.DEFAULT_THEME)
    return config.THEMES.get(theme_key, {}).get("language", "tr")


def stil_etiketleri(meta: dict) -> list:
    """DJ setinin muzik stiline ozel etiketler (config.SET_STILLERI).

    Tema etiketlerine EK olarak donuyor, onlarin yerine degil: "DJ Set"/"Mix"
    marka sinyali olarak kalmali, stil etiketleri ise seti kendi kitlesine
    tasiyor. meta.json'da `set_style` yoksa bos liste - eski setler etkilenmez.
    """
    stil = config.set_stili(meta)
    return list(stil["etiketler"]) if stil else []


def mekan_etiketleri(meta: dict) -> list:
    """DJ setinin çekim mekânı etiketleri (meta.json'daki `mekan`).

    Örn. `mekan: "Eiffel Nights"` → `["Eiffel Nights"]`; çağıran hashtag()
    ile `#EiffelNights` yapar ya da tags alanına düz yazar. Alan yoksa/boşsa
    boş liste — eski setler (mekan alanı olmayan meta.json'lar) bayt bayt
    eski çıktıyı üretir. TEK kaynak: YouTube görünür hashtag bloğu, görünmez
    tags, Shorts tags, kesit tags, build_caption ve TikTok kit hepsi buradan
    beslenir; yeni bir çıktı eklenirse o da buraya bağlanır."""
    mekan = (meta.get("mekan") or "").strip()
    return [mekan] if mekan else []


def _derleme_temalari(meta: dict) -> list:
    """Derlemedeki her parçanın tema anahtarı (çoklu, seçim sırasıyla).

    (2026-09-13'te `upload/youtube_upload.py`'den BURAYA TAŞINDI — kopyalanmadı;
    youtube_upload aynı adla buradan içe aktarıyor. Sebep: TikTok kit açıklaması
    da derleme türünü istiyor ve bu modül OAuth bağımlılığı çekmemeli.)

    Birincil kaynak `meta["derleme_temalari"]` — derleme.py bunu yazıyor.
    GERİYE DÖNÜK YOL: bu alan eklenmeden ÖNCE üretilmiş derlemelerde (ör. bu
    değişiklik yazılırken render'da olan "Gece Seansı Vol. 1") alan yok; o
    durumda temalar `derleme_liste`'deki parça adlarından kaynak projelerin
    meta.json'ına bakılarak okunuyor. Aksi hâlde tür bilgisi hiç bulunamaz ve
    derleme, meta'daki tek `theme` alanına (karma bir derlemede yanıltıcı)
    geri düşerdi. Okuma hatası yutuluyor: eksik tür etiketi yüklemeyi
    durdurmaya değmez.
    """
    temalar = [t for t in (meta.get("derleme_temalari") or []) if t]
    if temalar:
        return temalar
    kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for parca in meta.get("derleme_liste") or []:
        yol = os.path.join(kok, "projects", str(parca.get("ad", "")), "meta.json")
        try:
            with open(yol, encoding="utf-8") as f:
                tema = json.load(f).get("theme")
        except (OSError, ValueError):
            continue
        if tema:
            temalar.append(tema)
    return temalar


def _derleme_tur_bilgisi(meta: dict) -> tuple:
    """(başlıkta kullanılacak tür adı, etiket listesi) — derlemedeki parçalardan.

    (2026-09-13'te `upload/youtube_upload.py`'den BURAYA TAŞINDI, bkz.
    `_derleme_temalari`.)

    NEDEN: derlemenin meta.json'ındaki tek `theme` alanı derlemeyi anlatmıyor
    (eskiden --en-iyi ile tema verilmediği için config.DEFAULT_THEME'e düşüyor
    ve 13 parçalık karma bir derleme "Türkçe Hip-Hop Şarkısı" diye
    yayınlanıyordu). Tür artık parçaların temalarından türetiliyor.

    Baskın tema parçaların YARISINDAN fazlasını kapsıyorsa başlıkta o türün adı
    kullanılıyor; kapsamıyorsa derleme gerçekten KARMA demektir ve "Müzik"
    deniyor — "Gece Seansı Vol. 1"de en kalabalık tema 13 parçanın 5'i; buna
    "Hip-Hop derlemesi" demek ilk sürümdeki yanlışın daha yumuşak bir hâli
    olurdu. Etiketler (tags) yine TÜM temaları içeriyor: orada çoğulluk
    yanıltıcı değil, arama sinyali.
    """
    temalar = _derleme_temalari(meta)
    sayac = collections.Counter(temalar)
    etiketler = []
    for anahtar, _ in sayac.most_common():
        etiket = config.THEMES.get(anahtar, {}).get("label")
        if etiket and etiket not in etiketler:
            etiketler.append(etiket)
    tur = "Müzik"
    if sayac:
        baskin, adet = sayac.most_common(1)[0]
        if adet * 2 > len(temalar):
            tur = config.THEMES.get(baskin, {}).get("label") or "Müzik"
    return tur, etiketler


def _dil_havuzlari(meta: dict) -> dict:
    """Paylaşım metni havuzları, dile göre — `build_caption` ile TikTok kiti ORTAK."""
    if resolve_language(meta) == "en":
        return {"kesif": config.DISCOVERY_HASHTAGS_EN, "hook": config.HOOK_LINES_EN,
                "soru": config.ENGAGEMENT_QUESTIONS_EN, "kullan": config.USE_LINES_EN,
                "takip": config.FOLLOW_LINES_EN}
    return {"kesif": config.DISCOVERY_HASHTAGS, "hook": config.HOOK_LINES,
            "soru": config.ENGAGEMENT_QUESTIONS, "kullan": config.USE_LINES,
            "takip": config.FOLLOW_LINES}


def _govde_satirlari(meta: dict, hook_havuzu: list = None, soru_havuzu: list = None) -> tuple:
    """(hook, kullanım satırı, takip satırı, etkileşim sorusu) — deterministik.

    `build_caption` ile TikTok kit açıklamasının ORTAK gövdesi (kopya yok).
    `hook_havuzu`/`soru_havuzu` verilirse şarkıya özel `custom_*` ve genel havuz
    YERİNE o kullanılır — set ve derlemelerin şarkı hook'u almaması için.
    Tuzlar (salt) `build_caption`'ın tarihsel değerleri: aynı şarkı aynı satırları
    almaya devam ediyor.
    """
    title = meta.get("title", "Untitled")
    h = _dil_havuzlari(meta)
    hook = pick_deterministic(title, hook_havuzu or meta.get("custom_hooks") or h["hook"])
    soru = pick_deterministic(
        title, soru_havuzu or meta.get("custom_questions") or h["soru"], salt=7)
    kullan = pick_deterministic(title, h["kullan"], salt=3)
    takip = pick_deterministic(title, h["takip"], salt=11)
    return hook, kullan, takip, soru


_STIL_BOLUMU = re.compile(r"## Stil Etiketi.*?```\n(.*?)```", re.DOTALL)
# Yalnız AÇIK vokalsizlik ifadeleri. "instrumental" TEK BAŞINA DEĞİL: Sabah Senin'in
# stili "no instrumental intro" diyor (vokalli), Kumdan Denize'de `[Instrumental]`
# bir ara bölüm etiketi — ikisi de vokalli şarkı.
_VOKALSIZ_STIL = re.compile(r"\bno vocals?\b|\binstrumental only\b", re.IGNORECASE)


def ai_beyan_turu(meta: dict) -> str:
    """"dj" | "vokalli" | "vokalsiz" — `config.AI_BEYAN_SATIRLARI` anahtarı.

    VERİ (yeni bir tespit YAZILMADI, mevcut alanlar):
      * DJ seti (`tiktok_kit_turu` -> "set", yani meta `theme == "dj"`) -> "dj".
      * Derleme (`meta["derleme"]`) -> "vokalli" (kullanıcı kararı).
      * Şarkı: başlığa DOĞRULANMIŞ `*_sozler.md` (`dogrulanmis_sozler_yolu`).
        - "## Stil Etiketi" kod bloğunda "no vocals" / "instrumental only" -> "vokalsiz";
        - "## Temiz Sözler" bloğu VAR ama BOŞ (`caption_align.extract_clean_lyrics`
          boş dize) -> "vokalsiz".
    BELİRSİZSE "vokalli" (beyan eksik kalmasın): sözler dosyası yok (ilk şarkıların
    dosyası hiç yazılmadı ama vokalliler), dosya "EKSİK" işaretli, bölüm hiç yok,
    okunamıyor. Yanlış "vokalsiz", vokal AI'ı beyan etmemek olurdu.
    """
    tur = tiktok_kit_turu(meta)
    if tur == "set":
        return "dj"
    if tur == "derleme":
        return "vokalli"
    yol = dogrulanmis_sozler_yolu(meta.get("title") or "")
    if not yol:
        return "vokalli"
    try:
        with open(yol, encoding="utf-8") as f:
            icerik = f.read()
    except OSError:
        return "vokalli"
    stil = _STIL_BOLUMU.search(icerik)
    if stil and _VOKALSIZ_STIL.search(stil.group(1)):
        return "vokalsiz"
    try:
        import caption_align
    except Exception:
        return "vokalli"
    if caption_align.lyrics_marked_incomplete(icerik):
        return "vokalli"
    temiz = caption_align.extract_clean_lyrics(icerik)
    if temiz is not None and not temiz.strip():
        return "vokalsiz"
    return "vokalli"


def ai_beyan_satiri(meta: dict) -> str:
    """İçeriğe ve dile göre ZORUNLU AI beyan satırı (`config.AI_BEYAN_SATIRLARI`).
    Dil `resolve_language` ("en" -> İngilizce, diğer her şey Türkçe)."""
    dil = "en" if resolve_language(meta) == "en" else "tr"
    return config.AI_BEYAN_SATIRLARI[dil][ai_beyan_turu(meta)]


def build_story_overlay(title: str, versiyon: int, dil: str, meta: dict = None, onceki_sarki: str = "") -> str:
    """Instagram hikaye overlay metni (versiyona gore) — caption STORY overlay ile
    sinyal verir (API'de hikaye container'ina 'caption' parametresi support edilebilir).

    V1 (yayin +2-6 saat): yeni şarki duyuru + bio link yönlendirme
    V2 (yayin +24 saat): kaçirmayi kurtar + bio link
    V3 (yayin +3-4 gun): fragman + onceki şarkı atfı

    dil: "tr" veya "en". title: şarki adi. onceki_sarki: baglanti atan odaya
    gosterilecek önceki şarkı (mutlak değil, bos olabilir).
    """
    if dil == "en":
        if versiyon == 1:
            return (f"New track just landed 🎵\\n\\n{title}\\n\\n"
                    f"Full version in bio link 🎧")
        elif versiyon == 2:
            return (f"Missed this? {title} — full version in bio 🎵")
        else:  # versiyon == 3
            return (f"A clip from {title} 🎵\\n"
                    f"Previous track: {onceki_sarki} — in bio")
    # varsayilan: Türkçe
    if versiyon == 1:
        return (f"Yeni şarki cıktı 🎵\\n\\n{title}\\n\\n"
                f"Tam versiyon bio'daki linkte 🎧")
    elif versiyon == 2:
        return (f"Bunu kağırdıysan — {title} tam versiyon bio'da 🎵")
    else:  # versiyon == 3
        return (f"Bir fragman: {title} 🎵\\n"
                f"Bir önceki şarkı: {onceki_sarki} — bio'da")


def ai_caption(meta: dict, hook: str = None, *, force: bool = False) -> str:
    """LLM router ile şarkıya özel AI caption üret (opsiyonel).

    `meta["ai_caption"]` True değilse boş string döner — kapalı.
    Router tüm sağlayıcısız/bağlantısızsa sessizce boş string,
    hata yakalanır, caption deterministik havuzdan gelir (zaten
    `build_caption`'ın davranışı).

    Kullanım: upload/<platform>_upload.py içinde caption üretimi
    öncesine koyulabilir; mevcut `build_caption` yolu değişmez.
    """
    if not force and not meta.get("ai_caption"):
        return ""
    try:
        from _llm_cache import caption_cache as _caption_cache
        from _llm_router import llm_chat
    except Exception:
        return ""
    title = meta.get("title", "şarkı")
    theme = meta.get("theme", "")
    lyric_path = dogrulanmis_sozler_yolu(title)
    lyrics = ""
    if lyric_path:
        try:
            with open(lyric_path, encoding="utf-8") as f:
                lyrics = f.read()[:800]
        except Exception:
            pass
    user_msg = (
        f"Şarkı: {title}\nTema: {theme}\n"
        f"Sözler (kırpılmış):\n{lyrics}\n\n"
        f"Bu şarkı için Instagram/TikTok paylaşım caption'ı üret. "
        f"Hook cümlesi, kısa açıklama, 3-5 hashtag. "
        f"Türkçe cevap ver. Link yoksun. AI beyanı yok."
    )
    if hook:
        user_msg += f"\nMevcut hook: {hook}"

    def _call():
        return llm_chat([{"role": "user", "content": user_msg}],
                          model="smart", temperature=0.3, max_tokens=400)

    return _caption_cache(meta, _call, force=force)


def build_caption(meta: dict, ai_beyani: bool = False, platform: str = "instagram") -> str:
    """Şarkıya ÖZEL metin varsa genel havuzun önüne geçer (2026-09-10):
    meta.json içindeki `custom_hooks` / `custom_questions`, o şarkının
    SÖZLERİNDEN türetilmiş satırlardır ("Masada iki tabak, biri hep boş" gibi).
    Yoksa config.py'deki genel havuza düşülür — söz dosyası olmayan ilk üç
    şarkı (Gece Sürüşü, Beni Bırakma, Yeniden Doğacağım) o yolda kalır.

    Platform optimizasyonu:
    - Instagram: Tam caption, hashtag yoğun
    - TikTok: Kısa caption, fazla hashtag
    - YouTube: Uzun açıklama, link eklenebilir
    - Twitter/X: Karakter sınırlı, minimal hashtag
    """
    # =============================================================================
    # SAFE LLM ENHANCEMENT LAYER - OPTIONAL WITH FALLBACK
    # =============================================================================
    try:
        # Attempt LLM enhancement
        enhanced_caption = _call_llm_for_caption(meta)

        # If we got a valid enhancement, use it
        if enhanced_caption is not None:
            return enhanced_caption

    except Exception:
        # Any unexpected error in LLM layer - fall back to original
        pass
    # Platform doğrulama ve ayarlama
    platform = platform.lower().strip() if platform else "instagram"
    valid_platforms = ["instagram", "tiktok", "youtube", "facebook", "twitter", "x", "bluesky", "telegram"]
    if platform not in valid_platforms:
        platform = "instagram"  # Varsayılan

    title = meta.get("title", "Untitled")
    theme_key = meta.get("theme", config.DEFAULT_THEME)
    theme = config.THEMES.get(theme_key, config.THEMES[config.DEFAULT_THEME])
    genre_hashtags = ([hashtag(theme["label"])]
                      + [hashtag(t) for t in theme.get("related", [])]
                      + [hashtag(t) for t in stil_etiketleri(meta)]
                      + [hashtag(t) for t in mekan_etiketleri(meta)])

    # Gövde ve havuzlar TikTok kitiyle ORTAK (`_govde_satirlari`, `_dil_havuzlari`)
    # — 2026-09-13'te iki dil dalının kopyası tek yola indirildi. Çıktı önceki
    # hâliyle bayt bayt aynı (tek fark `hashtag()` düzeltmesi: #RB -> #RnB);
    # koruma: tests/test_social_text_hashtag.py (arşiv karşılaştırması).
    discovery_hashtags = pick_subset(title, _dil_havuzlari(meta)["kesif"],
                                     config.DISCOVERY_HASHTAG_COUNT, salt=13)
    hashtags = " ".join(config.BRAND_HASHTAGS + discovery_hashtags + genre_hashtags)
    hook, use_line, follow_line, engagement_question = _govde_satirlari(meta)

    # ai_beyani=True YALNIZ Instagram ve Facebook çağrı noktalarında (2026-09-13
    # kullanıcı kararı; Meta kuralı gerçekçi AI ses için beyan istiyor, API'de etiket
    # alanı yok). Satır hashtag bloğundan HEMEN ÖNCE — TikTok kitiyle aynı konum.
    # Shorts/Telegram/Bluesky/TikTok planı varsayılanla (False) aynen kalıyor.
    # ai_caption: meta["ai_caption"] True ise LLM router'dan
    # özel hook üret ( Sağlayıcı kapalıysa hook yine de deterministic ).
    ai_cap = ""
    if meta.get("ai_caption"):
        try:
            ai_cap = ai_caption(meta)
        except Exception:
            pass

    beyan = f"{ai_beyan_satiri(meta)}\n\n" if ai_beyani else ""

    hook = ai_cap if ai_cap else pick_deterministic(
        title, meta.get("custom_hooks") or _dil_havuzlari(meta)["hook"])

    # Platform-spesifik uyarlamalar
    if platform in ["twitter", "x"]:
        # Twitter/X: Karakter sınırı 280, minimal hashtag
        hashtags = " ".join(config.BRAND_HASHTAGS + pick_subset(title, discovery_hashtags, 2, salt=13))
    elif platform == "tiktok":
        # TikTok: Daha fazla hashtag allowance ama kısa caption tercih
        pass  # Mevcut yapı zaten TikTok için uygun
    elif platform == "youtube":
        # YouTube: Uzun açıklama, ek link eklenebilir (upload tarafında)
        pass  # Mevcut yapı zaten YouTube için uygun

    # Temel caption yapısı (tüm platformlar için ortak)
    caption = (
        f"{hook}\n\n{title} 🎵\n\n"
        f"{use_line}\n\n"
        f"{follow_line}\n\n"
        f"{engagement_question}\n\n{beyan}{hashtags}"
    )

    # Platform-spesifik son düzenleme
    if platform in ["twitter", "x"] and len(caption) > 280:
        # Twitter için kısaltma yap
        caption = caption[:277] + "..."

    return caption


# --------------------------------------------------------------------------
# TikTok YAYIN KİTİ açıklaması (upload/tiktok_yayin_kiti.py) — YALNIZ TikTok.
# Instagram/Shorts/Telegram/Bluesky/Facebook `build_caption()` ile aynen kalıyor.
# --------------------------------------------------------------------------

AI_BEYANI_MODLARI = ("etiket", "aciklama", "etiket+aciklama")
_KESIF_YASAK = re.compile(r"^#(fyp|foryou|foryoupage|viral)", re.IGNORECASE)


def ai_beyani_modu(deger: str = None) -> tuple:
    """(mod, gecerli). `deger` yoksa `config.TIKTOK_AI_BEYANI` çağrı anında okunur.
    Tanınmayan değer FAIL-CLOSED: "etiket+aciklama" (beyan hiçbir yerde
    kaybolmasın); "beyan yok" modu bilerek yok."""
    mod = config.TIKTOK_AI_BEYANI if deger is None else deger
    if mod in AI_BEYANI_MODLARI:
        return mod, True
    return "etiket+aciklama", False


def tiktok_kit_turu(meta: dict) -> str:
    """"derleme" | "set" | "sarki"."""
    if meta.get("derleme"):
        return "derleme"
    if meta.get("theme") == "dj":
        return "set"
    return "sarki"


def _etiket_sec(zorunlu: list, havuz: list, sonuna: list = ()) -> list:
    """Sıralı, tekrarsız (büyük/küçük harf duyarsız) en fazla
    `config.TIKTOK_KIT_ETIKET_SAYISI` etiket. #fyp/#foryou/#viral asla; #keşfet*
    en fazla bir. `sonuna` her zaman sona yer ayrılarak eklenir."""
    hedef = config.TIKTOK_KIT_ETIKET_SAYISI
    secilen, gorulen = [], set()
    kesfet = [0]

    def _ekle(e):
        k = str(e).casefold()
        if len(k) < 2 or k in gorulen or _KESIF_YASAK.match(e):
            return
        if k.startswith("#keşfet"):
            if kesfet[0]:
                return
            kesfet[0] += 1
        gorulen.add(k)
        secilen.append(e)

    for e in zorunlu:
        _ekle(e)
    son = [e for e in sonuna if str(e).casefold() not in gorulen]
    for e in havuz:
        if len(secilen) >= hedef - len(son):
            break
        _ekle(e)
    for e in son:
        _ekle(e)
    return secilen


def tiktok_kit_hashtagleri(meta: dict) -> list:
    """TikTok kit açıklamasının hashtag'leri — DETERMİNİSTİK, 5-6 tane.

    Şarkı: marka + şarkı adı + tür + tema bazlı TÜRKÇE keşif etiketleri
    (`config.TEMA_KESIF_ETIKETLERI`). DJ seti: marka + ad + #DJSet + stil
    etiketleri + İngilizce set etiketleri. Derleme: marka + ad + parçaların tür
    etiketleri + #Derleme. Genel keşif havuzu (#fyp/#viral...) YOK.
    """
    title = meta.get("title", "Untitled")
    zorunlu = list(config.BRAND_HASHTAGS) + [hashtag(title)]
    tur = tiktok_kit_turu(meta)
    if tur == "set":
        havuz = ([hashtag(t) for t in stil_etiketleri(meta)]
                 + pick_subset(title, config.TIKTOK_SET_ETIKETLERI_EN,
                               len(config.TIKTOK_SET_ETIKETLERI_EN), salt=19))
        return _etiket_sec(zorunlu + ["#DJSet"]
                            + [hashtag(t) for t in mekan_etiketleri(meta)], havuz)
    if tur == "derleme":
        _tur, turler = _derleme_tur_bilgisi(meta)
        kesif = config.TEMA_KESIF_ETIKETLERI["derleme"]
        havuz = ([hashtag(t) for t in turler]
                 + pick_subset(title, kesif, len(kesif), salt=17))
        return _etiket_sec(zorunlu, havuz, sonuna=["#Derleme"])
    theme_key = meta.get("theme", config.DEFAULT_THEME)
    theme = config.THEMES.get(theme_key, config.THEMES[config.DEFAULT_THEME])
    kesif = (config.TEMA_KESIF_ETIKETLERI.get(theme_key)
             or config.TEMA_KESIF_ETIKETLERI["_varsayilan"])
    return _etiket_sec(zorunlu + [hashtag(theme["label"])],
                       pick_subset(title, kesif, len(kesif), salt=17))


def build_tiktok_kit_caption(meta: dict, ai_beyani: str = None) -> str:
    """TikTok kit açıklaması: `build_caption` gövdesi + TikTok'a özel başlık
    satırı ve hashtag bloğu. DIŞ LİNK YOK (ilk yorum ayrı mesaj).

    İLK SATIR şarkı adı + tür kelimesi: TikTok araması açıklamanın başını
    okuyor; eskiden ilk satır genel bir hook'tu ve ad ikinci paragraftaydı.
    Set ve derleme ŞARKI hook'u almaz (ayrı havuzlar, bkz. config).
    `ai_beyani` "aciklama" içeriyorsa hashtag'lerden önce tek satır beyan
    (`ai_beyan_satiri` — içerik türüne ve dile göre) — bir cümle, hashtag değil.
    """
    title = meta.get("title", "Untitled")
    tur = tiktok_kit_turu(meta)
    dil = resolve_language(meta)
    if tur == "set":
        stil = config.set_stili(meta)
        ilk = (f"{title} — {stil['label']} DJ Set 🎧" if stil else f"{title} — DJ Set 🎧")
        hook, kullan, takip, soru = _govde_satirlari(
            meta, config.TIKTOK_SET_HOOKS_EN, config.TIKTOK_SET_SORULARI_EN)
    elif tur == "derleme":
        derleme_turu, _ = _derleme_tur_bilgisi(meta)
        adet = len(meta.get("derleme_liste") or [])
        sayi = f"{adet} şarkılık " if adet else ""
        ilk = f"{title} — {sayi}Türkçe {derleme_turu} derlemesi 🎧"
        hook, kullan, takip, soru = _govde_satirlari(
            meta, config.TIKTOK_DERLEME_HOOKS, config.TIKTOK_DERLEME_SORULARI)
    else:
        theme_key = meta.get("theme", config.DEFAULT_THEME)
        etiket = config.THEMES.get(theme_key, config.THEMES[config.DEFAULT_THEME])["label"]
        ilk = (f"{title} — {etiket} song 🎵" if dil == "en"
               else f"{title} — Türkçe {etiket} şarkısı 🎵")
        hook, kullan, takip, soru = _govde_satirlari(meta)

    parcalar = [ilk, hook, kullan, takip, soru]
    mod, _gecerli = ai_beyani_modu(ai_beyani)
    if "aciklama" in mod:
        parcalar.append(ai_beyan_satiri(meta))
    parcalar.append(" ".join(tiktok_kit_hashtagleri(meta)))
    return "\n\n".join(parcalar)


def build_ilk_yorum(title: str, lang: str = "tr") -> str:
    """YouTube'a atılacak İLK yorum (kanalın kendi yorumu, Studio'dan sabitlenir).

    İki satır: bölüm sorusu + abone çağrısı. `pick_deterministic` (salt 21) —
    aynı video hep aynı metni alır. build_youtube_comment'ten FARKLI: o, BAŞKA
    platformlardaki paylaşıma YouTube linki taşıyan yorum; bu, videonun KENDİ
    sayfasındaki etkileşim çağrısı (link yok, link burada gereksiz)."""
    if lang == "en":
        soru = pick_deterministic(title, config.ILK_YORUM_SORULARI_EN, salt=21)
        return f"{soru}\n{config.ILK_YORUM_ABONE_EN}"
    soru = pick_deterministic(title, config.ILK_YORUM_SORULARI, salt=21)
    return f"{soru}\n{config.ILK_YORUM_ABONE}"


def build_ai_disclosure_line(lang: str = "tr", meta: dict = None) -> str:
    """ZORUNLU AI beyan satırı — geriye dönük uyumlu giriş.

    2026-09-13 (kullanıcı kararı): eski "Bu içerik yapay zeka ile üretilmiştir." /
    "This content was created using artificial intelligence." metinleri KALDIRILDI;
    TEK kaynak `config.AI_BEYAN_SATIRLARI` (içerik türüne göre küçük set, söz kısmı
    önce, "AI destekli"). `meta` verilirse `ai_beyan_satiri(meta)`; verilmezse dilin
    varsayılan (vokalli) satırı. Açıklamalara eklemenin yolu artık
    `build_caption(meta, ai_beyani=True)` — DJ hattı eskiden caption'ın sonuna bu
    fonksiyonla İKİNCİ bir satır ekliyordu; artık tek satır."""
    if meta is not None:
        return ai_beyan_satiri(meta)
    return config.AI_BEYAN_SATIRLARI["en" if lang == "en" else "tr"]["vokalli"]


def build_youtube_comment(youtube_url: str, lang: str = "tr", platform: str = "instagram") -> str:
    """Paylaşımdan SONRA ilk yorum olarak eklenecek kısa metin — caption'ın aksine
    yorumların keşfet dağıtımını etkilediğine dair bir kaygı yok, o yüzden link
    burada güvenle kullanılabiliyor. lang="en" ise İngilizce metin döner (bkz.
    meta.json'daki "language" alanı). platform "instagram" ya da "tiktok" —
    hangi hesabın @handle'ının etiketleneceğini belirler (config.SOCIAL_HANDLES).

    İkinci satır BİLİNÇLİ olarak eklendi (kullanıcı kararı, 2026-09-05):
    Instagram/TikTok yorumlarında düz metin linkler TIKLANAMIYOR (WebSearch ile
    doğrulandı) — youtu.be linki yine de kopyalanabilir metin olarak kalıyor.
    Gerçekten tıklanabilir tek yer profildeki "bio link" — ama caption/yoruma
    düz "profildeki linkten..." yazmak yerine, hesabın kendisini `@handle` ile
    ETİKETLEMEK (mention) caption/yorumda GERÇEKTEN tıklanabilir bir eleman
    oluşturuyor (düz URL'den FARKLI bir mekanizma, WebSearch ile doğrulandı) —
    tıklanınca doğrudan profile açılır, orada bio linki (famousmusicstudio.com/
    latest.html, bkz. latest_release.py) görünür/tıklanabilir. Bio linkinin
    kendisini o adrese bağlamak kullanıcının uygulamadan elle yapması gereken,
    tek seferlik bir profil ayarı."""
    # Facebook'ta @handle satiri YOK ve olmamali. Iki ayri sebep:
    #   1. Ikinci satirin tek varlik sebebi Instagram/TikTok'ta duz linklerin
    #      TIKLANAMAMASI. Facebook yorumundaki link zaten tiklanabilir, yani
    #      satir orada bir sorunu cozmuyor.
    #   2. config.SOCIAL_HANDLES'da "facebook" anahtari yok ve varsayilan
    #      Instagram handle'ina dusuyordu — Facebook yorumuna baska bir
    #      platformun hesap adi, o sayfanin adiymis gibi yaziliyordu.
    #      Sayfanin vanity URL'i de alinmamis durumda (username: None),
    #      yani mention teknik olarak zaten mumkun degil.
    if platform == "facebook":
        if lang == "en":
            return f"🎧 Full track on YouTube: {youtube_url}"
        return f"🎧 Şarkının tamamı YouTube'da: {youtube_url}"

    handle = config.SOCIAL_HANDLES.get(platform, config.SOCIAL_HANDLES["instagram"])
    if lang == "en":
        return f"🎧 Full track on YouTube: {youtube_url}\nTap @{handle} above and check the link in bio 🔗"
    return f"🎧 Şarkının tamamı YouTube'da: {youtube_url}\n@{handle} hesabına dokun, bio'daki linkten de ulaşabilirsin 🔗"


# ================================================================
# CONTENT REPURPOSING — Hub-and-Spoke (profesyonel şirket davranışı)
# ================================================================
# Bir video birden fazla formatta yeniden kullanılır:
#   Hub: Uzun video (YouTube uzun format)
#   Spokes: Shorts, carousel, story, tweet, reel
#
# Her spoke, hub'in aynı vaadi tutarlı biçimde farklı açıdan anlatır.
# Bu fonksiyon, bir meta.json'dan TÜM platform caption'larını üretir.

def build_repurposed_captions(meta: dict, youtube_url: str = "") -> dict:
    """Bir video için tüm platform caption'larını üretir (hub-and-spoke).

    Args:
        meta: projenin meta.json verisi
        youtube_url: uzun format video URL'si (opsiyonel)

    Returns:
        {
            "youtube": str,      # uzun açıklama
            "shorts": str,       # Shorts caption
            "tiktok": str,       # TikTok caption
            "instagram": str,    # Instagram caption
            "facebook": str,     # Facebook caption
            "twitter": str,      # Twitter/X caption
            "telegram": str,     # Telegram mesaj
            "bluesky": str,      # Bluesky post
        }
    """
    return {
        "youtube": build_caption(meta, ai_beyani=True, platform="youtube"),
        "shorts": build_caption(meta, ai_beyani=False, platform="tiktok"),
        "tiktok": build_caption(meta, ai_beyani=False, platform="tiktok"),
        "instagram": build_caption(meta, ai_beyani=True, platform="instagram"),
        "facebook": build_caption(meta, ai_beyani=True, platform="facebook"),
        "twitter": build_caption(meta, ai_beyani=False, platform="twitter"),
        "telegram": build_caption(meta, ai_beyani=False, platform="telegram"),
        "bluesky": build_caption(meta, ai_beyani=False, platform="bluesky"),
    }


def build_youtube_description(meta: dict, youtube_url: str = "") -> str:
    """YouTube açıklaması — en uzun, en detaylı.

    Profesyonel şirketler YouTube'yu "depo" olarak kullanır:
    SEO başlık + ana açıklama + linkler + timestamps + playlist referansları.
    Diğer platformlar buradan kesilir (repurposing).
    """
    title = meta.get("title", "Untitled")
    theme = config.THEMES.get(meta.get("theme", config.DEFAULT_THEME), {})
    label = theme.get("label", "Müzik")

    parcalar = [
        title,
        "",
        f"🎵 {label} • AI-assisted production",
        "",
    ]

    # Sözler eklenebilir (varsa)
    sozler_dosya = None
    try:
        import stock_art
        sozler_dosya = stock_art.find_lyrics_file(title)
    except Exception:
        pass

    if sozler_dosya and os.path.isfile(sozler_dosya):
        parcalar.append("📝 Temiz Sözler:")
        parcalar.append("")
        try:
            with open(sozler_dosya, encoding="utf-8") as f:
                icerik = f.read()
            # Temiz Sözler bölümünü bul
            import re
            m = re.search(r"## Temiz Sözler\s*\n(.*?)(?=\n##|\Z)", icerik, re.DOTALL)
            if m:
                parcalar.append(m.group(1).strip())
            else:
                parcalar.append("(Sözler bulunamadı)")
        except Exception:
            parcalar.append("(Sözler okunamadı)")
        parcalar.append("")

    # Linkler
    if youtube_url:
        parcalar.append(f"🔗 YouTube: {youtube_url}")
        parcalar.append(f"🎧 Bio link: famousmusicstudio.com/latest.html")
        parcalar.append("")

    # Playlist referansları
    parcalar.append("🎶 Daha fazla: @FamousMusicStudio")
    parcalar.append("")

    # Hashtagler
    theme = config.THEMES.get(meta.get("theme", config.DEFAULT_THEME), {})
    genre_hashtags = ([hashtag(theme.get("label", "music"))]
                      + [hashtag(t) for t in theme.get("related", [])])
    hashtags = " ".join(config.BRAND_HASHTAGS + genre_hashtags)
    parcalar.append(hashtags)

    return "\n".join(parcalar)


# ================================================================
# AI HYBRID WORKFLOW - Profesyonel shirket davranisi
# ================================================================
# AI uretir, insan onaylar. Tam AI bagimliligi 3-6 ay sonra
# engagement dususu yakar (kaynak: TCISLEM 2026).
# 
# Akis:
#   1. AI caption draft uretir (_call_llm_for_caption)
#   2. Insan onay verir (onayla / reddet / duzenle)
#   3. Onaylanan caption kullanilir
#   4. Reddedilen caption eski havuzden secilir
#   5. Ogrenilen kalip ertesi hafta tekrar kullanilir

def ai_hybrid_caption(meta, ai_beyani=False, platform="instagram", onayli_caption=None):
    """AI hybrid caption: AI draft + insan onayli.
    
    Args:
        meta: projenin meta.json verisi
        ai_beyani: AI beyani satiri eklensin mi
        platform: platform (instagram/tiktok/youtube/...)
        onayli_caption: insanin onayladi captionsi (None => AI draft)
    
    Returns:
        str: onayli ya da AI draft caption
        bool: True => AI uretti, False => insan onayli
    """
    # Insan onayli caption varsa, dogrudan kullan
    if onayli_caption and isinstance(onayli_caption, str) and onayli_caption.strip():
        return onayli_caption.strip(), True
    
    # AI draft uret
    try:
        ai_caption = _call_llm_for_caption(meta)
        if ai_caption and len(ai_caption) > 20:
            # AI capion kullanilabilir mi kontrol et
            if _ai_caption_gecerli_mi(ai_caption, meta):
                return ai_caption, True
    except Exception:
        pass
    
    # AI basarisiz ya da gecersiz => eski havuzden sec
    return build_caption(meta, ai_beyani=ai_beyani, platform=platform), False


def _ai_caption_gecerli_mi(caption, meta):
    """AI caption gecerli mi? Kontroller:
    - Meta title var mi (caption'da olmali)
    - Too short/long degil mi
    - Brand uygunlugu
    """
    title = meta.get("title", "")
    
    # Baslik caption'da olmalı
    if title and title not in caption:
        return False
    
    # Boyut kontrolu
    if len(caption) < 10:
        return False
    if len(caption) > 5000:
        return False
    
    # Gereksiz tekrar kontrolu
    if caption.count("\n\n") > 10:
        return False
    
    return True


def caption_onay_kaydi(proje, platform, caption, kaynak="ai"):
    """Onay kaydi: hangi caption kullanildi, kim onayladi.
    
    Args:
        proje: proje adi
        platform: platform
        caption: kullanilan caption
        kaynak: "ai" | "insan" | "havuz"
    """
    import json
    dosya = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                         "..", "caption_onay.jsonl")
    satir = json.dumps({
        "proje": proje,
        "platform": platform,
        "kaynak": kaynak,
        "caption": caption[:200],  # ilk 200 karakter
        "zaman": datetime.now(timezone.utc).isoformat(),
    }, ensure_ascii=False)
    
    try:
        with open(dosya, "a", encoding="utf-8") as f:
            f.write(satir + "\n")
    except Exception:
        pass