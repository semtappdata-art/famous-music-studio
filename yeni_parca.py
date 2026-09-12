# -*- coding: utf-8 -*-
"""Yeni bir şarkının ELLE yapılan kurulum adımını (üretim akışının 2. adımı) tek
komuta indirir: proje klasörü + `meta.json` + repo kökünde `<slug>_sozler.md`
ŞABLONU + stil etiketi TASLAĞI.

NEDEN VAR — bu adımın ölçülmüş bedelleri (haftalik_is_akisi.md §2, B bölümü):

  * `meta.json`'da `theme` yoksa parça SESSİZCE `config.DEFAULT_THEME`
    (= "hiphop") olur: kapak, kart rengi, Pexels sorgusu ve caption dili yanlış
    tarzdan gelir ve HİÇBİR yerde hata görünmez. Bu komut tam da bunu kapatıyor:
    `--tema` ZORUNLU ve `config.THEMES`'te yoksa DURUR — varsayılana DÜŞMEZ.
  * `title` yoksa YouTube başlığı KLASÖR ADI olur.
  * Sözler dosyası repo KÖKÜNDE ve adı `<slug>_sozler.md` olmalı; slug kuralı
    `stock_art._slugify` (burada o fonksiyon İÇE AKTARILIYOR, yeniden
    yazılmıyor — iki ayrı slug kuralı sessizce ayrışırdı ve altyazı/görsel
    eşleşmesi yanlış şarkıya kayardı).
  * "Temiz Sözler" bölümü ZORUNLU (`caption_align` 0,25 eşleşme eşiğiyle
    okuyor) — şablon o başlığı ZATEN İÇERİYOR ki unutulmasın.

CANLI SİSTEM NOTU: `watch_projects.py` dakikada bir `projects/` altını tarıyor
ama YALNIZCA bir SES dosyası görürse hattı tetikliyor. Bu komut ses YAZMAZ;
oluşturduğu klasör `auto_process.find_pending_projects()` için "bekleyen" bile
sayılmaz (ses şartı) ve `validate_project.validate()` ses olmadan "audio
bulunamadı" HATASI verdiği için render'a hiç girilmez. Yani yazma işlemi canlı
hattı tetiklemez.

ÜÇ SORU (CLAUDE.md):
  1. Kim çağıracak? — OPERATÖR, elle; `haftalik_is_akisi.md` §2'nin 4./5. adımı
     bu komuta bağlandı. Otomatik bir çağıran YOK ve OLMAMALI: hangi tarzın/
     vokalin sırada olduğu bir YARGI kararı (bkz. `ses_ve_tarz_takibi.md`).
  2. Hangi zamanlayıcı görevinden? — HİÇBİRİNDEN, bilerek. `saglik_kontrol.
     uretim_kuyrugu_bos()` zaten "kuyruk boş, şu tarzı üret" bildirimini
     gönderiyor; bu komut o bildirimin CEVABI, kendisi bir nöbetçi değil.
  3. Çalışmadığını nasıl anlarız? — çıktısı ekrana basılıyor ve dosyalar
     diskte GÖRÜNÜR; ayrıca sessiz bir arıza yolu yok: geçersiz tema, var olan
     proje ve var olan sözler dosyası ÜÇÜ de sıfırdan farklı çıkış koduyla
     DURDURUYOR. Kilit: `tests/test_yeni_parca.py`.
"""

import argparse
import json
import os
import re
import sys

import config
from stock_art import _slugify        # slug kuralının TEK kaynağı (bkz. yukarısı)

REPO = os.path.dirname(os.path.abspath(__file__))

# Satır sonları ÖLÇÜLDÜ (2026-09-12, diskteki tüm dosyalar sayıldı), tahmin
# değil: `projects/*/meta.json` 19 dosyanın 15'i LF; `*_sozler.md` 20 dosyanın
# 12'si CRLF ve EN YENİSİ (vardiya_sozler.md, akışın referans şablonu) da CRLF.
# Ters eğik çizgili kaçış dizisi yerine chr() kullanılıyor: CLAUDE.md'deki
# "dosya YAZARKEN ters eğik çizgi yutuluyor" tuzağı bu depoda beş kez gerçekleşti.
LF = chr(10)
CRLF = chr(13) + chr(10)

# suno_prompt_hazirlik.md, "Kapanış (Outro) kuralı" — SABİT eşleme.
YUMUSAK_TEMALAR = ("pop", "akustik", "arabesk")
KAPANIS_YUMUSAK = "gentle fade-out ending"
KAPANIS_SERT = "strong final hit ending, no abrupt cutoff"

# config.THEMES[...]["language"] -> stil etiketindeki vokal dili sıfatı.
DIL_SIFATI = {"tr": "Turkish", "en": "English"}

# Stil etiketinin doldurulacak yerleri. Sözleri/etiketi UYDURMUYORUZ — bunlar
# operatörün (ya da prompt'u yazan ajanın) dolduracağı yer tutucular.
Y_MOOD = "<MOOD: ör. slow-burning and defiant>"
Y_DOKU = "<DOKU: ör. smoky husky low-register>"
Y_ENS1 = "<ENSTRÜMAN 1: ör. clean electric guitar arpeggio>"
Y_ENS2 = "<ENSTRÜMAN 2: ör. baglama saz accent over live drums>"
Y_BPM = "<BPM>"
Y_VOKAL = ("<VOKAL: ses_ve_tarz_takibi.md'nin SON DURUM satırından ÇIKARILAMADI "
           "— dosyayı elle oku ve doldur>")

TAKIP_DOSYASI = "ses_ve_tarz_takibi.md"

# Bir yan cümlede bunlardan biri geçiyorsa o cümledeki vokal sözcükleri
# ÖNERİ değil KAÇINILACAK sayılır ("kadın vokal üst üste ikiye çıkmasın").
_OLUMSUZ_ISARET = ("çıkmasın", "olmasın", "tekrarlanmasın", "kullanılmasın",
                   "dönülmesin", "girmesin", "değil", "yok")
_VOKAL_SOZCUK = (("kadın", "female"), ("erkek", "male"), ("düet", "duet"))


# --------------------------------------------------------------------------
# ses_ve_tarz_takibi.md — SON DURUM okuma
# --------------------------------------------------------------------------
def son_durum_blogu(kok: str) -> str:
    """`ses_ve_tarz_takibi.md`'nin SON DURUM bölümünü HAM metin olarak döndürür.

    Dosya yoksa/okunamazsa boş string — ÇÖKMEZ, ama çağıran yer tutucuya düşer
    (sessizce bir vokal UYDURMAZ; bu komutun tüm gerekçesi sessiz varsayılanı
    ortadan kaldırmak).
    """
    yol = os.path.join(kok, TAKIP_DOSYASI)
    try:
        with open(yol, "r", encoding="utf-8") as f:
            metin = f.read()
    except OSError:
        return ""
    satirlar = metin.splitlines()
    bas = None
    for i, s in enumerate(satirlar):
        if s.lstrip("*# ").startswith("SON DURUM"):
            bas = i
            break
    if bas is None:
        return ""
    son = len(satirlar)
    for j in range(bas + 1, len(satirlar)):
        s = satirlar[j]
        # Blok, tablo başlığında ya da bir sonraki başlıkta biter.
        if s.startswith("|") or s.startswith("#") or s.startswith("Yeni bir şarkı"):
            son = j
            break
    return LF.join(satirlar[bas:son]).strip()


def vokal_onerisi(blok: str) -> tuple:
    """(öneriler, kaçınılacaklar, dayanak_cümle) — SON DURUM metninden.

    YÖNTEM: metin "Sıradaki" paragrafı varsa ONDAN, yoksa bloğun tamamından
    alınır; yan cümlelere (`;` `.` `—`) bölünür ve her yan cümle KENDİ
    olumsuzluk işaretiyle değerlendirilir. Örnek (bugünkü dosya):
      "kadın vokal üst üste ikiye çıkmasın; erkek ya da düet tarafına dönülebilir"
      -> kaçınılacak {female}, öneri {male, duet}
    Çıkarılamazsa BOŞ döner ve çağıran yer tutucu basar — YANLIŞ bir vokali
    sessizce etikete yazmaktansa operatöre sormak doğru olan.
    """
    if not blok:
        return set(), set(), ""
    kaynak = blok
    for parca in blok.split(LF + LF):
        if "Sıradaki" in parca:
            kaynak = parca
            break
    duz = " ".join(kaynak.replace("*", " ").split())
    oneri, kacin = set(), set()
    for cumle in re.split(r"[;.—:]", duz):
        kucuk = cumle.lower()
        olumsuz = any(i in kucuk for i in _OLUMSUZ_ISARET)
        for tr, en in _VOKAL_SOZCUK:
            if tr in kucuk:
                (kacin if olumsuz else oneri).add(en)
    return oneri - kacin, kacin, duz


# --------------------------------------------------------------------------
# Stil etiketi taslağı
# --------------------------------------------------------------------------
def kapanis_tanimi(tema: str) -> str:
    """suno_prompt_hazirlik.md, 'Kapanış (Outro) kuralı' — SABİT."""
    return KAPANIS_YUMUSAK if tema in YUMUSAK_TEMALAR else KAPANIS_SERT


def vokal_ifadesi(tema: str, oneri: set, dil_sifati: str) -> str:
    """Stil etiketinin vokal tanımlayıcısı."""
    if "male" in oneri:
        cins = "male"
    elif "female" in oneri:
        cins = "female"
    elif "duet" in oneri:
        # Sadece "düet" önerildiyse taraflar hâlâ seçilmemiş demektir.
        return ("%s %s vocals in a two-part duet (taraflar: <TARAF 1> / <TARAF 2>)"
                % (Y_DOKU, dil_sifati))
    else:
        return Y_VOKAL
    if tema == "arabesk":
        # CLAUDE.md: arabesk SABİT olarak düet — kombinasyon serbest.
        return ("%s %s %s vocals alternating with <İKİNCİ TARAF> (arabesk = DÜET "
                "ZORUNLU)" % (Y_DOKU, dil_sifati, cins))
    return "%s %s %s vocals" % (Y_DOKU, dil_sifati, cins)


def stil_etiketi_taslagi(tema: str, oneri: set, bpm=None) -> str:
    """config.THEMES[tema] (dil + mood) + SON DURUM (vokal) + Outro kuralı.

    7 tanımlayıcı + kapanış — suno_prompt_hazirlik.md'deki "Örnek Stil Etiketi"
    ile aynı düzen: genre+mood önde, sonra vokal/enstrüman, SONA kapanış.
    """
    t = config.THEMES[tema]
    dil = DIL_SIFATI.get(t.get("language", "tr"), "Turkish")
    tur = "%s %s" % (dil, str(t.get("label", tema)).lower())
    parcalar = [
        tur,
        Y_MOOD,
        vokal_ifadesi(tema, oneri, dil),
        Y_ENS1,
        Y_ENS2,
        "%s atmosphere" % t.get("art_mood", "").strip(),
        "%s BPM" % (bpm if bpm else Y_BPM),
        kapanis_tanimi(tema),
    ]
    return ", ".join(p for p in parcalar if p and p != " atmosphere")


# --------------------------------------------------------------------------
# Dosya içerikleri
# --------------------------------------------------------------------------
def meta_icerigi(baslik: str, tema: str) -> str:
    """`meta.json` metni — LF satır sonu, 2 boşluk girinti, Türkçe karakterler HAM.

    SADECE `title` + `theme` yazılıyor. `custom_hooks`/`custom_questions`
    BİLEREK YOK (mevcut 19 meta.json'un 13'ünde var olsalar da):
      * İkisi de o şarkının SÖZLERİNDEN türetiliyor (ör. Vardiya'nın
        "Servisin camında buz tutmuş bir nefes 🚌") — sözler daha YAZILMADAN
        doldurulamazlar.
      * Yer tutucu metin koymak GERÇEK bir arıza olurdu: `social_text.
        build_caption()` bu listeleri olduğu gibi caption'a basıyor, yani
        "<kanca 1>" TikTok/Instagram'da YAYINLANIRDI.
      * Boş liste de gereksiz: `meta.get("custom_hooks") or config.HOOK_LINES`
        — alan YOKKEN de BOŞKEN de aynı, çalışan genel havuza düşülüyor. Yani
        alanın yokluğu sessiz bir arıza DEĞİL, belgelenmiş ve doğru davranış
        (`theme`in yokluğundan farkı tam olarak bu).
    Sözler yazıldıktan sonra eklenmesi için komut sonundaki adım listesine
    hatırlatma konuyor.
    """
    return json.dumps({"title": baslik, "theme": tema},
                      ensure_ascii=False, indent=2) + LF


def sozler_sablonu(baslik: str, tema: str, stil: str, son_durum: str) -> str:
    """`<slug>_sozler.md` ŞABLONU — CRLF satır sonu.

    Yapı `vardiya_sozler.md` ile birebir aynı (haftalik_is_akisi.md o dosyayı
    "şablon" ilan ediyor): başlık + üç ZORUNLU bölüm (`## Stil Etiketi`,
    `## Sözler`, `## Temiz Sözler`) + `## Notlar`.
    SÖZLER UYDURULMUYOR — yer tutucular var.
    """
    etiketli = [
        "[Intro]",
        "<DOLDUR: 2 satır — İLK SATIR temayı DOĞRUDAN ADLANDIRMAZ; somut bir",
        "an/mekân/duyu imgesiyle açar (suno_prompt_hazirlik.md, 'Intro kuralı')>",
        "",
        "[Verse 1]",
        "<DOLDUR: 4 satır>",
        "",
        "[Pre-Chorus]",
        "<DOLDUR: 4 satır>",
        "",
        "[Chorus]",
        "<DOLDUR: 4 satır — şarkının çengeli>",
        "",
        "[Verse 2]",
        "<DOLDUR: 4 satır>",
        "",
        "[Chorus]",
        "<DOLDUR: yukarıdaki Chorus'un BİREBİR aynısı>",
        "",
        "[Bridge]",
        "<DOLDUR: 4 satır>",
        "",
        "[Outro]",
        "<DOLDUR: İKİ TAM, BİTMİŞ cümle — '...' YOK",
        "(suno_prompt_hazirlik.md, 'Kapanış (Outro) kuralı')>",
    ]
    # "Temiz Sözler" = etiketli bölümün BİREBİR aynısı, köşeli parantez
    # etiketleri çıkarılmış. Şablon bunu PROGRAMATİK olarak türetiyor ki iki
    # bölüm daha ilk günden sapmasın (caption_align 0,25 eşleşme eşiğiyle
    # okuyor; bugün iki dosyada noktalama sapması bulundu).
    temiz = [s for s in etiketli if not re.match(r"^\[.*\]$", s)]
    while temiz and temiz[0] == "":
        temiz.pop(0)

    duet_notu = ""
    if tema == "arabesk":
        duet_notu = (
            "> ⚠ `arabesk` = DÜET ZORUNLU (CLAUDE.md). Bölüm etiketlerini "
            "karşılıklı yaz:" + CRLF
            + "> `[Verse - Kadın]`/`[Verse - Erkek]` ya da "
              "`[Verse - Baba]`/`[Verse - Oğul]`." + CRLF + CRLF)

    satirlar = [
        "# %s — Orijinal Sözler (%s)" % (baslik, config.THEMES[tema]["label"]),
        "",
        "Suno'nun Lyrics kutusuna aynen yapıştırılabilir.",
        "",
        "> Yeni bir şarkı prompt'u yazmadan önce `ses_ve_tarz_takibi.md`'ye bak —",
        "> vokal cinsiyeti/dokusu art arda tekrarlanmasın.",
        "",
    ]
    govde = CRLF.join(satirlar) + CRLF + duet_notu
    govde += CRLF.join([
        "**Neden bu tema:** <DOLDUR: `%s` neden seçildi — en az kullanılan slot mu,"
        % tema,
        "hangi vokal/tempo boşluğunu dolduruyor? Dayanağı `ses_ve_tarz_takibi.md`>",
        "",
        "**Konu:** <DOLDUR: katalogdaki diğer `*_sozler.md` dosyalarıyla ÇAKIŞMAYAN",
        "bir konu — anahtar kelimeyle ara, işlenmiş temayı ikinci kez yazma>",
        "",
        "## Stil Etiketi (Suno Style kutusuna yapıştır)",
        "",
        "```",
        stil,
        "```",
        "",
        "<TASLAK — yer tutucuları doldur. Kapanış tanımı (`%s`)" % kapanis_tanimi(tema),
        "SABİT kuraldan geliyor, SİLME. BPM'i etikete YAZ (son iki şarkıda unutuldu).>",
        "",
        "## Sözler (Suno Lyrics kutusuna yapıştır)",
        "",
        "```",
    ]) + CRLF
    govde += CRLF.join(etiketli) + CRLF
    govde += CRLF.join([
        "```",
        "",
        "## Temiz Sözler (YouTube açıklaması için kopyala-yapıştır)",
        "",
        "⚠ Bu bölüm ZORUNLU ve yukarıdaki etiketli metinle **birebir** aynı satır",
        "listesi olmalı (sadece `[...]` etiketleri çıkarılmış). `caption_align` 0,25",
        "eşleşme eşiğiyle burayı okuyor — noktalama sapması bile altyazıyı bozuyor.",
        "",
        "```",
    ]) + CRLF
    govde += CRLF.join(temiz) + CRLF
    govde += CRLF.join([
        "```",
        "",
        "## Notlar",
        "",
        "- Vokal dili: <DOLDUR> (stil etiketindeki vokal tanımı + Türkçe sözler).",
        "- Vokal cinsiyeti/dokusu: <DOLDUR — `ses_ve_tarz_takibi.md` SON DURUM'a göre>.",
        "- Tema: `%s`. `meta.json`: `{\"title\": \"%s\", \"theme\": \"%s\"}`."
        % (tema, baslik, tema),
        "- Kapanış: stil etiketinde `%s` var; Outro İKİ TAM cümle, `...` yok."
        % kapanis_tanimi(tema),
        "- Intro kuralı: ilk satır temayı doğrudan adlandırmıyor mu? Yazdıktan sonra",
        "  bir kez daha oku.",
        "",
        "### Üretim anındaki SON DURUM (ses_ve_tarz_takibi.md'den kopyalandı)",
        "",
    ]) + CRLF
    if son_durum:
        govde += CRLF.join("> " + s if s else ">"
                           for s in son_durum.split(LF)) + CRLF
    else:
        govde += ("> (ses_ve_tarz_takibi.md okunamadı — SON DURUM satırını ELLE "
                  "kontrol et.)" + CRLF)
    return govde


# --------------------------------------------------------------------------
# Ana akış
# --------------------------------------------------------------------------
def _guvenli(metin: str) -> str:
    """Konsolun kodlayamadığı karakterleri ZARARSIZLAŞTIRIR.

    NEDEN VAR (bu komutu yazarken CANLI olarak yakalandı): Windows konsolu bu
    makinede **cp1254**; `print()` kodlanamayan bir karaktere çarpınca
    `UnicodeEncodeError` ile ÇÖKÜYOR — ilk sürüm çıktının ortasında, "⚠" ve "▶"
    yüzünden tam da SIRADAKİ ADIMLAR listesinin ortasında öldü. Aynı sınıftan
    bir tuzak `saglik_kontrol._cp1254_guvenli()`de zaten belgeli.
    Metnin KENDİSİNDEN de temizlendi (artık düz "UYARI:"/"(play)" yazıyor); bu
    fonksiyon, yarın eklenecek bir satır yine emoji getirirse komutun ÇÖKMEMESİ
    için ikinci katman.
    """
    kod = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        metin.encode(kod)
        return metin
    except (UnicodeEncodeError, LookupError):
        return metin.encode(kod, "replace").decode(kod, "replace")


def _bas(metin: str = "") -> None:
    print(_guvenli(metin))


def _hata(mesaj: str) -> None:
    sys.stderr.write(_guvenli("HATA: %s%s" % (mesaj, LF)))


def plan_yap(baslik: str, tema: str, kok: str, bpm=None) -> dict:
    """Yazılacak her şeyi hesaplar — HİÇBİR dosyaya dokunmaz."""
    slug = _slugify(baslik)
    proje_dizini = os.path.join(kok, "projects", baslik)
    sozler_yolu = os.path.join(kok, "%s_sozler.md" % slug)
    blok = son_durum_blogu(kok)
    oneri, kacin, dayanak = vokal_onerisi(blok)
    stil = stil_etiketi_taslagi(tema, oneri, bpm)
    return {
        "baslik": baslik, "tema": tema, "slug": slug,
        "proje_dizini": proje_dizini, "sozler_yolu": sozler_yolu,
        "meta_yolu": os.path.join(proje_dizini, "meta.json"),
        "son_durum": blok, "vokal_oneri": oneri, "vokal_kacin": kacin,
        "vokal_dayanak": dayanak, "stil": stil,
        "meta_icerik": meta_icerigi(baslik, tema),
        "sozler_icerik": sozler_sablonu(baslik, tema, stil, blok),
    }


def cakisma_kontrol(plan: dict) -> list:
    """Var olan bir şeyin ÜZERİNE yazma ihtimali varsa gerekçeleri döndürür."""
    engeller = []
    if os.path.exists(plan["proje_dizini"]):
        engeller.append(
            "proje klasörü ZATEN VAR: %s — üzerine yazılmaz. Başka bir ad seç ya "
            "da o klasörü elle incele." % plan["proje_dizini"])
    if os.path.exists(plan["sozler_yolu"]):
        engeller.append(
            "sözler dosyası ZATEN VAR: %s — üzerine yazılmaz (slug '%s' başka bir "
            "şarkıyla çakışıyor olabilir)."
            % (plan["sozler_yolu"], plan["slug"]))
    return engeller


def plani_bas(plan: dict, kuru: bool, yaz=_bas) -> None:
    yaz("")
    yaz("%s  %s (tema: %s)" % ("[KURU KOŞU] " if kuru else "", plan["baslik"],
                               plan["tema"]))
    yaz("  slug (stock_art._slugify): %s" % plan["slug"])
    yaz("")
    yaz("  %s klasör : %s" % ("oluşturulacak" if not kuru else "oluşturulACAKTI",
                              plan["proje_dizini"]))
    yaz("  %s dosya  : %s" % ("yazılacak    " if not kuru else "yazılACAKTI  ",
                              plan["meta_yolu"]))
    yaz("  %s dosya  : %s" % ("yazılacak    " if not kuru else "yazılACAKTI  ",
                              plan["sozler_yolu"]))
    yaz("")
    yaz("  meta.json içeriği:")
    for s in plan["meta_icerik"].rstrip(LF).split(LF):
        yaz("    " + s)
    yaz("")
    yaz("  Stil etiketi TASLAĞI (yer tutucuları doldur):")
    yaz("    " + plan["stil"])
    yaz("")
    if plan["vokal_oneri"]:
        yaz("  Vokal önerisi (SON DURUM'dan): %s%s"
            % (", ".join(sorted(plan["vokal_oneri"])),
               ("  |  kaçınılacak: " + ", ".join(sorted(plan["vokal_kacin"])))
               if plan["vokal_kacin"] else ""))
        yaz("    dayanak: %s" % plan["vokal_dayanak"][:200])
    else:
        yaz("  UYARI: vokal önerisi ses_ve_tarz_takibi.md'den ÇIKARILAMADI — "
            "etikette yer tutucu var, ELLE doldur.")
    yaz("")


def sonraki_adimlar(plan: dict, yaz=_bas) -> None:
    """Suno tarafındaki ELLE adımlar + bu deponun bilinen tuzakları."""
    p = plan
    yaz("SIRADAKİ ADIMLAR")
    yaz("  1. `%s` dosyasını doldur: stil etiketindeki <...> yer tutucuları,"
        % os.path.basename(p["sozler_yolu"]))
    yaz("     sözler ve 'Temiz Sözler'. Temiz Sözler etiketli metinle BİREBİR aynı")
    yaz("     satır listesi olmalı (caption_align 0,25 eşleşme eşiği).")
    yaz("  2. `ses_ve_tarz_takibi.md`: tabloya satır ekle (Şarkı | Tema | BPM |")
    yaz("     Vokal) VE 'SON DURUM' satırını güncelle. Bu adım atlanırsa saatlik")
    yaz("     `ses_takip_denetimi.py` denetimi '`projects/%s` diskte VAR ama"
        % p["baslik"])
    yaz("     takip tablosunda YOK' uyarısını vermeye başlar.")
    yaz("  3. Suno.com (https://suno.com) — Custom Mode:")
    yaz("     - UYARI: Chrome'un OTOMATİK ÇEVİRİSİNİ KAPAT (Ayarlar > Diller). Çeviri")
    yaz("       açıkken şarkının ADI bile değişiyor ('Gece Sürüşü' -> 'Gece Gezintü').")
    yaz("     - Style kutusunu TEMİZLE, kendi etiketini yapıştır (Suno alakasız")
    yaz("       bir öneri koyuyor).")
    yaz("     - Sözleri PARÇA PARÇA yapıştır ([Intro], [Verse 1], ...) — tek dev")
    yaz("       blok editörü donduruyor.")
    yaz("     - Üretim bitince oynatma ikonu (play) GÖRÜNENE KADAR bekle; sürenin")
    yaz("       görünmesi tek başına yeterli değil.")
    yaz("     - UYARI: 'Görüntülenen Şarkı Sözleri' bloğunu KOPYALAMA — o Suno'nun")
    yaz("       hizalaması, ORİJİNAL DEĞİL. Dosyaya giren metin Lyrics kutusuna")
    yaz("       SENİN girdiğin metindir.")
    yaz("  4. İndirme: TEK varyant, doğrudan şu klasöre (Suno'nun verdiği adla,")
    yaz("     mp3/wav fark etmez):")
    yaz("       %s" % p["proje_dizini"])
    yaz("     UYARI: İki varyantı AYNI klasöre koyma: aynı md5 artık UYARI değil HATA,")
    yaz("       boru hattını durdurur. İkinciyi repo DIŞINDA sakla.")
    yaz("     Elle `audio.wav` adına çevirmen gerekmez — `watch_projects.py`")
    yaz("     dakikada bir tarıyor ve hattı kendisi tetikliyor.")
    yaz("  5. Tetiklemeyi doğrula (2 dk): `gorev_izleri/watch_projects.log` ->")
    yaz("     BAŞLADI; `auto_process.log` -> projenin adı. 10 dakikada iz yoksa")
    yaz("     klasör adını/konumunu kontrol et.")
    yaz("  6. Sözler yazıldıktan SONRA (opsiyonel ama önerilir): `meta.json`'a")
    yaz("     sözlerden türetilmiş `custom_hooks` / `custom_questions` ekle —")
    yaz("     yoksa caption genel havuzdan (config.HOOK_LINES) seçilir, bozulmaz")
    yaz("     ama şarkıya özel olmaz.")
    yaz("  7. `output/` altındaki iki mp4'ü AÇ ve OYNAT — yarım kalan render")
    yaz("     diskte 'var' görünür ve yüklemeye geçilir.")


def main(argv=None) -> int:
    ayristirici = argparse.ArgumentParser(
        prog="yeni_parca.py",
        description="Yeni şarkı iskelesi: projects/<Ad>/meta.json + "
                    "<slug>_sozler.md şablonu + stil etiketi taslağı.")
    ayristirici.add_argument("baslik", help='Şarkı adı, ör. "Vardiya". Klasör adı '
                                           've meta.json "title" alanı bu olur.')
    ayristirici.add_argument(
        "--tema", "-t", required=True,
        help="ZORUNLU. config.THEMES'teki bir anahtar (%s). Verilmezse/geçersizse "
             "komut DURUR — sessizce '%s'a DÜŞMEZ."
             % (", ".join(config.THEMES), config.DEFAULT_THEME))
    ayristirici.add_argument("--bpm", help="Stil etiketine yazılacak BPM "
                                          "(verilmezse yer tutucu kalır).")
    ayristirici.add_argument(
        "--dry-run", dest="kuru", action="store_true",
        help="Ne yapacağını yazar, HİÇBİR dosya oluşturmaz. Varsayılan DEĞİL: "
             "bu komutun tek işi 2. adımı kurmak ve iki adımlı bir varsayılan, "
             "kaldırmaya çalıştığımız 'unutulan adım' sınıfının aynısını geri "
             "getirirdi. Emniyet çakışma kontrolünden geliyor: var olan bir "
             "proje/sözler dosyasının ÜZERİNE asla yazılmaz.")
    ayristirici.add_argument("--kok", default=REPO,
                             help="Repo kökü (varsayılan: bu dosyanın klasörü). "
                                  "Testler tmp_path veriyor.")
    a = ayristirici.parse_args(argv)

    baslik = a.baslik.strip()
    if not baslik:
        _hata("şarkı adı boş olamaz.")
        return 2

    # 1) TEMA DOĞRULAMASI — sessiz varsayılan YOK.
    if a.tema not in config.THEMES:
        _hata("tema %r config.THEMES'te YOK." % a.tema)
        sys.stderr.write(_guvenli("Geçerli temalar: %s%s"
                         % (", ".join(config.THEMES), LF)))
        sys.stderr.write(_guvenli(
            "Ana katalog (projects/) için: %s. 'dj' yalnızca dj_sets/ hattına "
            "aittir.%s" % (", ".join(k for k in config.THEMES if k != "dj"), LF)))
        return 2
    if a.tema == "dj":
        sys.stderr.write(_guvenli(
            "UYARI: 'dj' teması DJ Famous hattına (dj_sets/, dj_famous_process.py) "
            "aittir; ana katalog projesi için muhtemelen yanlış seçim.%s" % LF))

    plan = plan_yap(baslik, a.tema, a.kok, a.bpm)

    if not _slugify(baslik):
        _hata("'%s' için slug üretilemedi (harf/rakam içermiyor)." % baslik)
        return 2

    # 6) ÇAKIŞMA KONTROLÜ — kuru koşuda da yapılıyor ki plan gerçeği göstersin.
    engeller = cakisma_kontrol(plan)
    if engeller:
        for e in engeller:
            _hata(e)
        return 2

    plani_bas(plan, a.kuru)

    if a.kuru:
        _bas("[KURU KOŞU] Hiçbir dosya oluşturulmadı. Gerçekten kurmak için "
              "aynı komutu --dry-run OLMADAN çalıştır.")
        _bas("")
        sonraki_adimlar(plan)
        return 0

    os.makedirs(plan["proje_dizini"], exist_ok=False)
    with open(plan["meta_yolu"], "w", encoding="utf-8", newline="") as f:
        f.write(plan["meta_icerik"])
    with open(plan["sozler_yolu"], "w", encoding="utf-8", newline="") as f:
        f.write(plan["sozler_icerik"])

    _bas("OLUŞTURULDU:")
    _bas("  %s" % plan["proje_dizini"])
    _bas("  %s" % plan["meta_yolu"])
    _bas("  %s" % plan["sozler_yolu"])
    _bas("")
    sonraki_adimlar(plan)
    return 0


if __name__ == "__main__":
    sys.exit(main())
