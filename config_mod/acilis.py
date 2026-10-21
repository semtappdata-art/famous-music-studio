import os

try:
    from tools.config_loader import get
except Exception:

    def get(key, default=None):
        return default


# --- AÇILIŞ (ilk saniyeler) ---
# NEDEN (2026-09-11, olcum_temel_cizgi.json / kitle_tutma_28gun ölçümü):
# 8 uzun videonun kitle tutma eğrisinde kaybın TAMAMI başta toplanıyor —
# videonun %1'inden %3'üne (yani ~2. saniyeden ~6,5. saniyeye) ortalama 25
# puan, oradan %10'a kadar (~22. saniye) sadece ~12 puan daha. Yani sorun
# "düzgün azalma" değil, 2.-7. saniyede bir uçurum.
# O saniyelerde ekranda ÖLÇÜLEN değişim (kare(0) ile kare(11) arası ortalama
# mutlak fark, 0-255 gri): 7,3-8,6 — yani ~%3. Pratikte donmuş bir kare.
# Üstelik ilk karede şarkı adı HİÇBİR YERDE yazmıyor (kayan künye yazısı
# t=0'da şeridin sağ dışında başlıyor) ve kadraj, tıklanan küçük resimle
# uyuşmuyor: küçük resim tam ekran fotoğraf + büyük başlık, video ise aynı
# fotoğrafın ekranın ~%24'ünü kaplayan küçültülmüş kart hâli.
# ÇÖZÜM: video projenin KENDİ cover.png'siyle (birebir YouTube küçük resmi)
# tam ekran açılıyor, kısa bir bekleme sonrası karta çözülüyor (cross-dissolve).
# Tek değişiklikle üç açık birden kapanıyor: tıklama sürekliliği, ilk karede
# başlık, ve tam uçurumun olduğu saniyelerde gerçek hareket.
INTRO_KAPAK = get('INTRO.KAPAK', True)
INTRO_KAPAK_BEKLEME = get('INTRO.KAPAK_BEKLEME', 0.9)   # kapak tam ekran sabit kalma süresi (sn)
INTRO_KAPAK_COZULME = get('INTRO.KAPAK_COZULME', 1.5)   # karta çözülme süresi (sn) — bitiş: bekleme+çözülme
# Sadece uzun formatta. Shorts akışında küçük resim izleyiciye HİÇ gösterilmiyor
# (bkz. buyume_analizi.md Bulgu 3), yani orada tıklama sürekliliği diye bir şey
# yok; 45 saniyelik bir kesitte 2,4 saniyeyi kapak ekranına vermek ise net kayıp.
INTRO_KAPAK_PLATFORMLAR = get('INTRO.KAPAK_PLATFORMLAR', ["youtube_16x9"])

# DİKEY HOOK (2026-10-06): highlight/dikey videonun ilk saniyelerinde üstte
# beliren kisa yazi. Shorts/Reels/TikTok akisinda ilk 1-2 sn tutmayi belirliyor;
# sabit `enable` penceresi CTA deseniyle ayni (bkz. ffmpeg_utils son-kare CTA).
DIKEY_HOOK_METNI = get('DIKEY_HOOK.METNI', "Sesi A\u00e7")
DIKEY_HOOK_SURE_SN = get('DIKEY_HOOK.SURE_SN', 2.5)

# DESTEK (2026-10-06): Ko-fi sayfasi. BOSSA caption/destek satiri uretilmez —
# 2026-10-08: sayfa acildi (famousmusicstudio), URL varsayilan yazildi.
KOFI_URL = get('DESTEK.KOFI_URL', "https://ko-fi.com/famousmusicstudio")

# Suno çıktıları başta dijital sessizlikle geliyor — 18 projede ölçüldü:
# 0,15 sn ile 2,65 sn arası, medyan ~1,1 sn (-99 dB, yani mutlak sessizlik).
# O sürede izleyici ne ses duyuyor ne hareket görüyor. Kırpılıyor.
# DÜRÜST NOT: sessizlik süresi ile açılış tutması arasında ÖLÇÜLEBİLİR bir
# ilişki YOK (n=8, Sessiz Mektup en kısa sessizliğe sahip ve en kötü üçte;
# sıra korelasyonu ~0). Yani bu, veriyle kanıtlanmış bir düzeltme değil —
# "hiçbir şey olmayan saniyeyi at" mantığıyla yapılmış ucuz bir temizlik.
# Kapatmak için: INTRO_SESSIZLIK_KIRP = False.
INTRO_SESSIZLIK_KIRP = get('INTRO.SESSIZLIK_KIRP', True)
INTRO_SESSIZLIK_ESIGI = "-50dB"  # silencedetect eşiği
INTRO_SESSIZLIK_PAY = 0.12       # atağın başı kesilmesin diye bırakılan pay (sn)
INTRO_SESSIZLIK_MAKS = 3.0       # güvenlik tavanı: tespit bozulsa bile şarkıdan
                                 # bundan fazlası ASLA kırpılmaz (sn)

PROGRESS_BAR_HEIGHT_RATIO = 0.008  # yüksekliğe oran — kalınlaştırıldı, görünürlük için
PROGRESS_BAR_MARGIN_RATIO = 0.08  # kenarlardan içeri, genişliğe oran
PROGRESS_BAR_BOTTOM_RATIO = 0.05  # alttan yukarı, yüksekliğe oran
PROGRESS_BAR_FILLED = 235  # dolu kısım parlaklığı (0-255)
PROGRESS_BAR_EMPTY = 70  # boş kısım parlaklığı (0-255)

# Başlık metni (meta.json'da "title" varsa kullanılır) — kayan, künye/jenerik tarzı
# küçük ve göze batmayan bir yazı (büyük/kalın başlık değil).
def _find_font_path() -> str:
    """İşletim sistemine göre ilk bulunan sistem fontunu döndürür — proje Windows,
    macOS ve Linux'ta çalışabilsin diye (tek sabit Windows yolu yerine). Segoe UI
    (Windows) tercih edilir, bulunamazsa her platformda yaygın bir sans-serif
    alternatife düşülür. Hiçbiri yoksa render.py başlarken açık hata versin diye
    RuntimeError fırlatılır (drawtext sessizce hatalı/eksik yazı üretmesin diye)."""
    candidates = [
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    raise RuntimeError(
        "Sistemde uygun bir font bulunamadı (denenen yollar: "
        + ", ".join(candidates)
        + "). config.FONT_PATH'i elle bir .ttf/.ttc dosyasına ayarlayın."
    )


def _find_bold_font_path() -> str:
    """Kalın font varyantı — sadece cover.png başlığı için (künye yazısı normal
    kalınlıkta kalıyor). Bulunamazsa hata vermez, FONT_PATH'e (normal ağırlık)
    düşer — kalın font kozmetik bir tercih, zorunlu değil."""
    candidates = [
        r"C:\Windows\Fonts\segoeuib.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return FONT_PATH


FONT_PATH = _find_font_path()
FONT_BOLD_PATH = _find_bold_font_path()


def _find_logo_path() -> str | None:
    """Famous Music Studio amblemi (altın sunburst + wordmark, düz siyah zemin
    üzerinde) — cover.png'de metin marka satırı yerine kullanılır. Gitignored
    (upload/assets/*.png, assets/*.png) — üretim makinesinde elle konmuş
    olabilir ama fresh checkout'ta YOK olabilir, bu yüzden bulunamazsa None
    döner ve generate_cover.py sessizce düz metin satırına düşer (hata vermez)."""
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "upload", "assets", "famous_music_studio_logo_v2.png"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "assets", "logo.png"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


LOGO_PATH = _find_logo_path()
FONT_SIZE_RATIO = 0.032  # video yüksekliğine oran — büyütüldü, okunurluk için
FONT_COLOR = "white@0.95"
# Yazi golgesi - SADECE video arka planli render'da (DJ setleri).
# Sabit gorsel arka plan koyu oldugu icin orada golgeye gerek yok.
FONT_SHADOW_COLOR = "black@0.55"
FONT_SHADOW_OFFSET = 2  # künye yazısı net okunsun diye yüksek opaklık
MARQUEE_SEPARATOR = "  •  "
MARQUEE_REPEAT = 6  # metnin geniş ekranlarda da kesintisiz görünmesi için tekrar sayısı
MARQUEE_SPEED_PX_S = 60

# Kayan künye yazısının altında duran SABİT (kaymayan) marka satırı — künye yazısıyla
# AYNI font ve AYNI düz beyaz renk (STATIC_LABEL_FONT_RATIO sadece boyut farkı için).
STATIC_LABEL_TEXT = "Famous Music Studio"
STATIC_LABEL_FONT_RATIO = 0.85  # ana font boyutuna oran — biraz daha küçük
STATIC_LABEL_GAP_RATIO = 0.01  # kayan yazı ile arasındaki boşluk (yüksekliğe oran)

# Paylaşım metinleri (YouTube açıklaması, sosyal medya caption şablonları) için
# tek merkezi marka bilgisi — upload/youtube_upload.py ve ileride
# instagram_upload.py/tiktok_upload.py bu değerleri kullanır.
SOCIAL_LINKS = {
    "instagram": "https://instagram.com/famous_music_studio",
    "tiktok": "https://www.tiktok.com/@famousmusicstudio",
    "website": "https://famousmusicstudio.com",
}

# YouTube kanal handle'ı (@ işaretsiz) — DJ Famous açıklama şablonunda
# "Subscribe ... 👉 @handle" satırı için (bkz. youtube_upload.build_snippet).
YOUTUBE_HANDLE = "Famous_musics_studio"

# @mention handle'ları (SOCIAL_LINKS'teki URL'lerden AYRI tutuluyor) —
# Instagram/TikTok'ta düz metin linkler caption/yorumda TIKLANAMIYOR ama
# "@handle" bir hesabı gerçekten ETİKETLİYORSA (mention) tıklanabilir oluyor
# ve doğrudan o profile açılıyor (WebSearch ile doğrulandı, 2026-09-05) — bkz.
# social_text.build_youtube_comment(). Bu, düz URL'den FARKLI bir mekanizma.
SOCIAL_HANDLES = {
    "instagram": "famous_music_studio",
    "tiktok": "famousmusicstudio",
}
# NOT: "#AIMusic"/"#YapayZekaMüzik"/"#AIMusicChallenge"/"#SunoAI" gibi AI-vurgulu
# ibareler BİLİNÇLİ olarak burada YOK — kullanıcı kuralı: ürettiğimiz hiçbir
# içerikte (caption, YouTube tag, video içi kayan yazı) bu ibareler kullanılmasın.
# AI-üretimi olduğunun ZORUNLU bildirimi (platform politikası gereği) bundan AYRI
# ve hâlâ yerinde: YouTube'da containsSyntheticMedia API bayrağı
# (youtube_upload.py); TikTok kit / Instagram / Facebook açıklamasında hashtag'lerden
# önce tek satır AI_BEYAN_SATIRLARI (2026-09-13 kullanıcı kararı, bkz. dosya sonu) —
# bunlar hashtag/marka etiketi değil, gerçek zorunlu bildirim mekanizmaları.
BRAND_HASHTAGS = ["#FamousMusicStudio"]

# Keşfet/For You dağıtımını hedefleyen genel hashtag'ler — marka hashtag'lerinden
# ayrı tutuluyor çünkü bunlar zamanla değişebilir (trend_hashtag_notlari.md'ye bak).
# 2026-09-10: sabit üçlü yerine HAVUZ. Sebep: her paylaşımda birebir aynı
# hashtag setini tekrarlamak tekdüzelik sinyali; ayrıca caption'ın yarısı zaten
# sabitti. build_caption() bu havuzdan şarkıya göre deterministik 3 tane seçer —
# aynı şarkı hep aynı seti alır (arşiv tutarlılığı), şarkılar arası çeşitlenir.
# AI-vurgulu hashtag KOYMA (bkz. yukarıdaki not, kullanıcı kararı 2026-09-05).
DISCOVERY_HASHTAGS = [
    "#keşfet", "#fyp", "#viral", "#keşfetteyiz", "#müzik",
    "#şarkı", "#yenişarkı", "#türkçemüzik", "#foryou",
]
DISCOVERY_HASHTAG_COUNT = 3

# Caption'ın ilk satırı — kaydırmayı durdurmak için merak uyandıran kısa açılış cümlesi.
# build_caption() şarkı başlığına göre bunlardan birini deterministik seçer (her şarkı
# için hep aynı hook, ama şarkılar arası çeşitlilik olur).
# NOT: burada BİLİNÇLİ olarak "yapay zeka/AI ile yapıldı" gibi görünür bir vurgu YOK
# (kullanıcı kararı, 2026-09-05) — bu içerik hook/etkileşim amaçlı, ZORUNLU bir
# bildirim değil; zorunlu AI-üretimi bildirimi bundan tamamen ayrı ve hâlâ yerinde
# (YouTube containsSyntheticMedia bayrağı; TikTok kit/Instagram/Facebook açıklamasında
# AI_BEYAN_SATIRLARI satırı — hiçbiri buradaki hook/soru metinlerine bağlı değil).
HOOK_LINES = [
    "Bunu ilk sen keşfet 👀🎶",
    "Kulaklığı tak, bu şarkı tam sana göre 🎧",
    "Yeni parça, yeni hikaye 🎵",
    "Bu şarkıyı bitirmeden geçme 👇",
    "İlk on saniye yeter, anlarsın 🎧",
    "Sesi aç, gerisi kendiliğinden gelir 🔊",
    "Bu akşamın şarkısı belli oldu 🌙",
    "Bir dinle, aklından çıkmasın 🎶",
    "Kaydırıp geçme, dönüp geleceksin 👀",
    "Bu ritim seni yakalar 🔥",
    "Yeni parça yayında 🎵",
    "Sessiz izleme, ses şart 🔊",
    "Bunu listene ekleyeceksin, şimdiden söyleyeyim 📲",
    "Bu şarkı gece dinlenir 🌃",
]

# Caption'ın orta bölümü de artık sabit değil (2026-09-10). Önceden
# "Bu sesi edit/kesit videolarında kullanabilirsin 🔥" ve "Yeni şarkılar için
# takipte kalın" satırları HER paylaşımda birebir aynıydı; caption'ın yarısı
# şarkıdan bağımsız tekrar ediyordu.
USE_LINES = [
    "Bu sesi edit/kesit videolarında kullanabilirsin 🔥",
    "Edit'lerinde bu sesi rahatça kullan 🔥",
    "Kesitlerinde kullanmak serbest 🎬",
    "Bu ses senin videolarında da güzel durur 🔥",
    "İstersen edit'ine ekle, sorun değil 🎬",
    "Videolarında kullanmak istersen buyur 🔥",
    "Bu parçayı edit'lerde duymak isterim 🎬",
    "Kesit yaparsan bu ses tam oturur 🔥",
]

# ── PROFESYONELLİK KURALI: CTA generic DEĞİL, BELİRLİ FAYDA ──
# "Takipte kal" yerine izleyiciye ne kazandığını söyleyen cümleler.
# Profesyonel şirketler aboneyi "benefıt subscription" olarak satar,
# "beni follow et" değildir.
FOLLOW_LINES = [
    "Yeni şarkılar için takipte kalın",
    "Yeni parçalar için takip et 🎵",
    "Her hafta yeni şarkı — takipte kal",
    "Devamı gelecek, takipte kal 🎶",
    "Yeni işler için takip etmeyi unutma",
    "Takip et, yenileri kaçırma 🎧",
    "Daha fazlası için takipteyiz 🎵",
    "Sıradaki parça için takipte kal 🔔",
]

# YouTube İLK YORUM (sabitlenecek kanal yorumu, bkz. youtube_ilk_yorum.py).
# Açıklamayı kimse açmıyor; sabit yorum herkesin gördüğü ilk satır. İki cümle:
# bölüm sorusu (setse dakika, şarkıysa kısım) + abone çağrısı. Deterministik
# seçim (salt 21) — aynı video hep aynı yorumu alır, tekrar gönderimde
# çift yorum çıkmaz (state bayrağı da var, ikinci kilit). Yalvarma dili YOK.
ILK_YORUM_SORULARI = [
    "Favori bölümün hangisi? Dakikasıyla yaz 👇",
    "En çok nerede kaldın? Bölümü yaz, konuşalım 💬",
    "Baştan sona mı, bölüm bölüm mü dinliyorsun? 👇",
]
ILK_YORUM_SORULARI_EN = [
    "Which section is your favorite? Drop the timestamp 👇",
    "Where did you stay the longest? Tell us 💬",
    "Full listen or section hopping? 👇",
]
# ── PROFESYONELLİK KURALI: Abone CTA spesifik fayda ──
# Generic "abone ol" yerine izleyiciye ne kazandığını belirten cümle.
ILK_YORUM_ABONE = "Abone ol, her yeni paragraftan önce haberdar ol 🔔"
ILK_YORUM_ABONE_EN = "Subscribe for the next track before it drops 🔔"

# Caption'ın sonunda, hashtag'lerden hemen önce — yorum sayısını artırmayı
# hedefleyen bir soru (yorum, algoritma için güçlü bir etkileşim sinyali).
# HOOK_LINES ile aynı deterministik seçim mantığı ama farklı bir index kullanılır
# (bkz. social_text._pick_hook) — aynı şarkıda hep aynı ikili tekrarlanmasın diye.
ENGAGEMENT_QUESTIONS = [
    "Yorumda hangi türü bir sonraki duymak istersin? 👇",
    "Bu şarkı sana neyi hatırlattı, yorumda yaz 💬",
    "1'den 10'a kadar puanla 👇",
    "Bu şarkıyı kaç kez tekrar dinlersin? Yorumda söyle 🔁",
    "Hangi kısmı tekrar tekrar dinledin? 👇",
    "Bu şarkı hangi anını hatırlattı? 💬",
    "Bunu kime dinletirsin, etiketle 👇",
    "Sözler mi ritim mi? Yorumda söyle 💬",
    "Kaç saniyede kaptırdın kendini? ⏱️",
    "Buna başka bir isim verseydin ne olurdu? 💭",
    "Nakarat mı giriş mi daha iyi? 👇",
    "Bunu listene ekler misin? 📲",
    "Bu şarkı hangi saatte dinlenir? 🌙",
    "Hangi tarzı daha çok yakıştırdın? 🎧",
]

# DJ setlerinde arka planı stok videodan kurmak (bkz. stock_video.py).
# YALNIZCA dj_sets/ için ve yalnızca uzun formatta (16x9) uygulanıyor:
# 4 dakikalık bir şarkıda tek görsel sorun değil, 80 dakikalık bir sette
# hiç değişmeyen bir kare izleyiciyi kaçırıyor. Kapatılırsa setler eski
# bulanık art.jpg arka planına döner — hiçbir şey bozulmaz.
DJ_ARKA_PLAN_VIDEO = True

# DJ Famous sahnesi: Arda'nın tişörtlü buz-mağarası görsellerinden oluşan
# 45 saniyelik backdrop, uzun DJ setlerinde Pexels yerine kullanılır.
# Kapalıysa mevcut stok-video akışı aynen devam eder.
DJ_ARDA_GORSELLERI = True
DJ_ARDA_BACKDROP = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "dj_sets", "_arda", "preview", "arda_tshirt_slideshow_45s.mp4",
)

# DJ setlerinde sci-fi HUD kaplaması (bkz. dj_hud.py). Arka plan videosuyla
# aynı kapsam: YALNIZCA dj_sets/ ve yalnızca uzun formatta. Dikey 45 saniyelik
# kesitte köşe ayraçları kadrajı daraltıyor, orada kapalı.
DJ_HUD = True

# HUD nefes alması: köşe ayraçları render sırasında çok yavaş nabız yapıyor
# (kontrast 1.0 -> 1+DERINLIK -> 1.0, periyot SURE_SN). PNG sabit üretiliyor,
# hareket ffmpeg_utils'taki blend öncesi `eq=...:eval=frame` ile veriliyor:
# kare başına PNG üretmek gerekmez, maliyet ~sıfır. Yön bilerek YUKARI:
# kontrast 1'in altına inseydi YUV pivotu (128) siyah tabanı griye kaldırır
# ve `screen` blend tüm kareye nabızla inip kalkan bir peçe basardı; yukarı
# yönde siyah klipte kalıyor, yalnız çizgiler ışıldıyor. Yalnızca uzun format
# (HUD'un zaten çalıştığı yer); dikeyde HUD kapalı olduğu için etkisiz.
DJ_HUD_NEFES = True
DJ_HUD_NEFES_SURE_SN = 8.0  # aralık: 4-16 (altı telaşlı, üstü donuk)
DJ_HUD_NEFES_DERINLIK = 0.15  # aralık: 0.05-0.30 (üstü gri-peçe bölgesi)

# SAHNE MODU: arka plan artık kartın ARKASINDAKİ dekor değil, kadrajın
# KENDİSİ. Kart kaldırılıyor, görüntü bulanıklaştırılmıyor, HUD onu
# çerçeveliyor - referanstaki ("NOXELUNE HOUSE") düzenin mantığı bu.
#
# Neden ayrı bir mod: mevcut tasarım arka planı BİLEREK bulanık ve koyu
# tutuyor ki ortadaki kart öne çıksın. Aynı kareye hem kart hem net bir
# sahne koymak ikisini de zayıflatıyor - biri diğerini boğuyor. Bu yüzden
# ikisi ayrı düzen, aynı anda açılmıyor.
DJ_SAHNE_MODU = True
