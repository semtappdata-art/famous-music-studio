"""Yüklenen videoları YouTube playlist'lerine otomatik ekler — DÖRT katmanlı yapı.

    1. TARZ playlist'leri (`config.THEMES`): "Pop Şarkılar", "Arabesk Şarkılar"…
       Kanal içinde tarz alanları oluşturur. (Bu katman eskiden TEK katmandı.)
    2. `_tum_sarkilar` — ana kataloğun TÜM uzun format şarkıları TEK akışta,
       enerji eğrisine göre sıralı.
    3. `_shorts` — tüm dikey kısa kesitler; uzun formatın dinleme zincirinden AYRI.
    4. `_derlemeler` — çok parçalı derlemeler (`derlemeler/`). Kendi rafları.

NEDEN DÖRDÜNCÜ KATMAN (2026-09-11, "Gece Seansı Vol. 1" canlı olarak yanlış
listeye girdikten sonra): derlemenin TÜRÜ `build_snippet` içinde parçaların
ÇOĞUNLUK temasından türetiliyor (`youtube_upload._derleme_tur_bilgisi`);
çoğunluk yarıyı geçmiyorsa tür "Müzik", yani KARMA. "Gece Seansı Vol. 1"de en
kalabalık tema 13 parçanın 5'i, dolayısıyla başlık doğru şekilde "13 Şarkılık
Türkçe Müzik Derlemesi" oldu — AMA playlist seçimi hâlâ `meta["theme"]`e
bakıyordu ve o alan (derleme.py'nin `_baskin_tema` düşüşü) "hiphop" diyordu.
Sonuç: karma bir derleme Hip-Hop playlist'inde. Aynı karar İKİ ayrı yerde İKİ
ayrı kuralla veriliyordu; arıza bu ayrışmanın kendisiydi. Artık tek kural var:
başlıkta hangi tür yazıyorsa playlist de o — `derleme_tarz_anahtari()` o
fonksiyonu YENİDEN YAZMADAN çağırıyor. Karma derlemenin tarz playlist'i YOK,
bu yüzden derlemelerin kendi rafı gerekiyordu: aksi hâlde karma bir derleme
HİÇBİR listede kalmazdı (kanalın en uzun, izlenme süresi en yüksek varlığı).

NEDEN İKİNCİ KATMAN (2026-09-11, kanalın kendi Analytics verisiyle):
PLAYLIST yüzeyi kanalın en verimli yüzeyi — izlenme başına 3,7 dakika üretiyor
(kanal ortalaması 0,84) ve `averageTimeInPlaylist` 8,2 dakika. Ama 20 uzun
formatı 6 tarz kovasına bölmek zincir uzunluğunu EN AZA indiriyordu: Rock
playlist'inde TEK video var, yani "sonraki video" diye bir şey yok. Bir
playlist'in ürettiği izlenme süresinin üst sınırı, o an izlenen videodan SONRA
kaç video geldiğidir. Tarz playlist'leri (keşif/kimlik için) duruyor, üstüne
tüm kataloğu tek zincirde toplayan bir liste eklendi.

NEDEN ÜÇÜNCÜ KATMAN AYRI (Shorts uzun formatla AYNI listede DEĞİL):
(a) Shorts kanal izlenmesinin %41'ini ama izlenme süresinin sadece %4'ünü
    üretiyor — 4 dakikalık şarkıların arasına 30 saniyelik kesitler koymak tam
    da playlist'i değerli kılan `averageTimeInPlaylist`'i aşağı çeker.
(b) Daha da belirleyicisi: her Short, AYNI şarkının dikey kesiti. İkisi aynı
    listede olsaydı dinleyici aynı şarkıyı arka arkaya iki kez duyardı.

DJ İKİNCİ DALGA KESİTLERİ (`youtube_clip_video_id`, bkz. `dj_clips.py`) de
`_shorts` rafına giriyor — madde (b)'ye RAĞMEN değil, ona uyduğu için: kesit
setin kendi Shorts'undan FARKLI bir aralıktan kesiliyor (en yüksek enerjili
pencere bilerek atılıyor, pencereler arası en az 60 sn). Gerekçenin tamamı
`beklenen_anahtarlar()` içindeki yorumda.

KULLANIM:
    python upload/youtube_playlists.py --durum
        SALT OKUMA. Hangi video hangi playlist'te değil, onu listeler
        (playlist başına 1 birim kota). Değişiklik yapmaz.

    python upload/youtube_playlists.py --sync-all
        Yüklenmiş TÜM projeleri tarar; uzun formatı tarz playlist'ine +
        ana zincire, Shorts'u Shorts listesine ekler. Eksik playlist'i
        oluşturur. Geriye dönük çalışır.

    python upload/youtube_playlists.py --kur-zincir
        `_tum_sarkilar` zincirini ENERJİ EĞRİSİNE göre sıralı kurar
        (sakin açılış → yükselen orta → dinlendirici kapanış). Sadece
        HENÜZ listede olmayanları ekler; mevcut sırayı bozmaz.

    python upload/youtube_playlists.py --project "projects/sarki-adi"
        Tek bir projeyi senkronlar.

    Hepsine `--dry-run` eklenebilir: ne yapacağını yazar, API'ye yazmaz.

KOTA: `playlists.insert` ve `playlistItems.insert` 50'şer birim; okuma
(`playlistItems.list`) 1 birim. Bu yüzden "zaten ekli mi" kontrolü YouTube'dan
okunarak yapılıyor — 1 birimlik okuma, 50 birimlik gereksiz yazımı önlüyor.

Playlist ID'leri upload/playlist_ids.json'da (anahtar -> playlist_id)
önbelleğe alınır — secret DEĞİL (sadece kanalın kendi playlist ID'leri), bu
yüzden repoya commit edilir. Aynı playlist'in iki kez oluşturulmasını önler
(bu GERÇEKTEN oldu: kanalda önbelleğe girmemiş, aynı adlı İKİNCİ bir "DJ Set
Şarkılar" playlist'i duruyor).
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import state_io
import uyumluluk
from youtube_auth import get_authenticated_service

UPLOAD_DIR = os.path.dirname(os.path.abspath(__file__))
PLAYLIST_IDS_PATH = os.path.join(UPLOAD_DIR, "playlist_ids.json")

# Tarz-DIŞI playlist'ler. Anahtarların başındaki "_" bilinçli: playlist_ids.json
# tek bir düz sözlük ve `config.THEMES` anahtarlarıyla ÇAKIŞMAMALI — tema
# anahtarları hiçbir zaman "_" ile başlamıyor.
ZINCIR_ANAHTARI = "_tum_sarkilar"
SHORTS_ANAHTARI = "_shorts"
DERLEME_ANAHTARI = "_derlemeler"

KOLEKSIYONLAR = {
    ZINCIR_ANAHTARI: {
        "title": f"Türkçe Şarkılar — Kesintisiz Dinle | {config.STATIC_LABEL_TEXT}",
        "description": (
            f"{config.STATIC_LABEL_TEXT} kanalının tüm Türkçe şarkıları tek akışta.\n\n"
            "Sıralama rastgele değil: sakin bir açılıştan yükselen bir ortaya, "
            "oradan dinlendirici bir kapanışa göre kurgulandı — arka planda "
            "kesintisiz dinlemek için.\n\n"
            "Tarza göre ayrı listeler de var (Pop, Rock, Arabesk, Hip-Hop, "
            "Elektronik, Akustik)."
        ),
    },
    SHORTS_ANAHTARI: {
        "title": f"Kısa Kesitler — {config.STATIC_LABEL_TEXT}",
        "description": (
            f"{config.STATIC_LABEL_TEXT} kanalının dikey kısa kesitleri.\n\n"
            "Şarkıların TAM sürümleri ayrı bir listede: "
            "\"Türkçe Şarkılar — Kesintisiz Dinle\"."
        ),
    },
    DERLEME_ANAHTARI: {
        "title": f"Derlemeler — Uzun Çalma Listeleri | {config.STATIC_LABEL_TEXT}",
        "description": (
            f"{config.STATIC_LABEL_TEXT} kanalının çok parçalı derlemeleri: her biri "
            "kanalın kendi şarkılarından, enerji eğrisine göre sıralanmış, "
            "parçalar arasında gerçek geçişlerle kurulmuş kesintisiz akışlar.\n\n"
            "Tek tek şarkılar ayrı listelerde: "
            "\"Türkçe Şarkılar — Kesintisiz Dinle\" ve tarz listeleri "
            "(Pop, Rock, Arabesk, Hip-Hop, Elektronik, Akustik)."
        ),
    },
}

# playlist_id -> o listedeki video ID'lerinin kümesi. Süreç ömrü boyunca
# geçerli; her playlist için YouTube'a EN FAZLA BİR okuma yapılmasını sağlıyor
# (`auto_process.py` her projede sync_project'i ayrı ayrı çağırıyor).
_UYE_ONBELLEK: dict = {}

# playlist_id -> o listedeki ÖĞELER, SIRAYLA ve TEKRARLARIYLA:
# (video_id, başlık, gizlilik) üçlüleri.
#
# NEDEN AYRI BİR ÖNBELLEK (2026-09-11): `_UYE_ONBELLEK` bir KÜME ve küme,
# aynı videonun listeye İKİ KEZ eklenmiş olduğunu SESSİZCE yutuyor — kanalda
# bunun canlı örneği var (Arabesk listesinde `Yeniden Doğacağım` iki kez ekli).
# Başlık/gizlilik de burada: kataloğa bağlanamayan bir öğeyi ("Deleted video")
# sadece ID'siyle raporlamak okunamaz bir satır demek.
# EK KOTA YOK: `playlistItems.list` kaç `part` istenirse istensin 1 birim.
_OGE_ONBELLEK: dict = {}


def _load_playlist_ids() -> dict:
    if os.path.isfile(PLAYLIST_IDS_PATH):
        with open(PLAYLIST_IDS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_playlist_ids(ids: dict) -> None:
    # NEDEN state_io: bu dosya yarım yazılırsa `_load_playlist_ids` JSONDecodeError
    # atar ve playlist adımı komple durur; daha kötüsü, elle onarılırken bir ID
    # kaybolursa aynı playlist İKİNCİ kez oluşturulur (kanalda bunun bir örneği var).
    state_io._atomik_yaz(PLAYLIST_IDS_PATH, ids)


def _load_meta(project_dir: str) -> dict:
    meta_path = os.path.join(project_dir, "meta.json")
    if os.path.isfile(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _load_state(project_dir: str) -> dict:
    state_path = os.path.join(project_dir, "state.json")
    if os.path.isfile(state_path):
        with open(state_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _update_state(project_dir: str, fields: dict) -> None:
    # NEDEN state_io (2026-09-11): burası `open(state_path, "w")` ile HEDEFİN
    # ÜSTÜNE yazıyordu. `open` dosyayı önce sıfırlıyor; yarıda kesilen bir yazım
    # diskte yarım JSON bırakıyor. Bunun bedeli bugün büyüdü: `uyumluluk._durum()`
    # sertleştirildi, bozuk state.json artık DurumBozuk -> HATA üretip o projeyi
    # tamamen yayın dışı bırakıyor. Kendi atomik kopyanı yazma, bu modülü kullan.
    state = _load_state(project_dir)
    state.update(fields)
    state_io.durum_yaz(project_dir, state)


def get_theme_key(meta: dict) -> str:
    theme_key = meta.get("theme", config.DEFAULT_THEME)
    return theme_key if theme_key in config.THEMES else config.DEFAULT_THEME


def derleme_tarz_anahtari(meta: dict):
    """Bir DERLEMENİN gireceği tarz playlist'inin anahtarı — karma ise None.

    NEDEN `meta["theme"]` DEĞİL: derlemenin meta.json'ındaki tek `theme` alanı
    derlemeyi ANLATMIYOR. `derleme.py` orayı `_baskin_tema()` ile dolduruyor,
    çünkü kapak rengi / validate_project / resolve_language geçerli bir tema
    anahtarı istiyor — yani o alan bir SUNUM zorunluluğu, tür beyanı değil.
    "Gece Seansı Vol. 1"de 13 parçanın yalnızca 5'i hiphop olduğu hâlde alan
    "hiphop" yazıyordu ve video Hip-Hop playlist'ine bu yüzden girdi.

    NEDEN `_derleme_tur_bilgisi` ÇAĞRILIYOR, kural burada YENİDEN YAZILMIYOR:
    "çoğunluk yarıyı geçiyor mu" eşiği YouTube BAŞLIĞINI da belirliyor
    (`youtube_upload.build_snippet`). İki yerde iki kopya olsaydı, biri
    değiştiğinde başlık "Müzik Derlemesi" derken video yine bir tarz
    listesinde durabilirdi — arızanın bugünkü hâli tam olarak buydu. Tek kural,
    tek kaynak: başlıkta hangi tür yazıyorsa playlist de o.

    Etiket -> anahtar ters çevrimi bilinçli: `_derleme_tur_bilgisi` dışarıya
    ETİKET veriyor ("Hip-Hop") ve karma durumda "Müzik" diyor — "Müzik" hiçbir
    config.THEMES etiketi değil, dolayısıyla ters çevrim kendiliğinden None
    üretiyor. Eşik sayısı bu dosyada hiç geçmiyor.

    İçe aktarma GEÇ ve korumalı (`enerji_sirasi`deki `derleme._enerji` ile aynı
    desen): `youtube_upload` ağır bir modül ve tür bilgisi okunamazsa doğru
    davranış otomasyonu durdurmak değil, tarz playlist'ini ATLAMAK — video yine
    derlemeler rafına giriyor, sadece keşif katmanı eksik kalıyor.
    """
    try:
        from youtube_upload import _derleme_tur_bilgisi
    except Exception as e:                        # modül/bağımlılık yoksa
        print(f"  derleme türü okunamadı ({e}) — tarz playlist'i atlanıyor")
        return None
    tur, _etiketler = _derleme_tur_bilgisi(meta)
    for anahtar, tanim in config.THEMES.items():
        if tanim.get("label") == tur:
            return anahtar
    return None                                   # "Müzik" => KARMA derleme


def _kok_adi(project_dir: str) -> str:
    """Projenin hangi katalogda olduğu: "projects" / "dj_sets" / "derlemeler"."""
    return os.path.basename(os.path.dirname(os.path.abspath(project_dir)))


# --- playlist oluşturma / bulma ------------------------------------------


def _olustur(youtube, anahtar: str, title: str, description: str,
             dry_run: bool = False) -> str:
    if dry_run:
        # NEDEN: `playlists.insert` 50 birim VE geri alınamaz (silme bu modülde
        # yok). --dry-run'ın tek anlamı "hiçbir şey yazma" olduğu için burada
        # da durmak zorunda; sahte ID sonraki adımların akışını bozmuyor.
        print(f"  [dry-run] playlist oluşturulacak: {title!r}")
        sahte = f"DRYRUN_{anahtar}"
        _UYE_ONBELLEK[sahte] = set()
        _OGE_ONBELLEK[sahte] = []
        return sahte
    body = {
        "snippet": {"title": title, "description": description},
        "status": {"privacyStatus": "public"},
    }
    response = youtube.playlists().insert(part="snippet,status", body=body).execute()
    playlist_id = response["id"]
    print(f"  playlist oluşturuldu: {title!r} ({playlist_id})")

    ids = _load_playlist_ids()
    ids[anahtar] = playlist_id
    _save_playlist_ids(ids)
    _UYE_ONBELLEK[playlist_id] = set()   # yeni liste boş, okumaya gerek yok
    _OGE_ONBELLEK[playlist_id] = []
    return playlist_id


def get_or_create_playlist(youtube, theme_key: str, dry_run: bool = False) -> str:
    """theme_key'e karşılık gelen TARZ playlist'inin ID'si — yoksa oluşturur."""
    ids = _load_playlist_ids()
    if theme_key in ids:
        return ids[theme_key]

    theme = config.THEMES.get(theme_key, config.THEMES[config.DEFAULT_THEME])
    return _olustur(
        youtube,
        theme_key,
        f"{theme['label']} Şarkılar — {config.STATIC_LABEL_TEXT}",
        f"{config.STATIC_LABEL_TEXT} kanalının {theme['label'].lower()} "
        f"tarzındaki AI-üretimi şarkıları.",
        dry_run,
    )


def get_or_create_koleksiyon(youtube, anahtar: str, dry_run: bool = False) -> str:
    """Tarz-dışı playlist'in (ana zincir / Shorts) ID'si — yoksa oluşturur."""
    ids = _load_playlist_ids()
    if anahtar in ids:
        return ids[anahtar]
    tanim = KOLEKSIYONLAR[anahtar]
    return _olustur(youtube, anahtar, tanim["title"], tanim["description"], dry_run)


# --- üyelik ---------------------------------------------------------------


def playlist_ogeleri(youtube, playlist_id: str) -> list:
    """Playlist'in ÖĞELERİ: (video_id, başlık, gizlilik) — SIRAYLA, TEKRARLARIYLA.

    NEDEN KÜME DEĞİL LİSTE: `playlist_videolari`nin döndürdüğü küme iki şeyi
    sessizce kaybediyor ve ikisi de bugün kanalda CANLI:
      * aynı videonun AYNI listeye İKİ kez eklenmiş olması (`Yeniden Doğacağım`,
        Arabesk listesinde) — küme bunu tekilleştirip yok ediyor;
      * kataloğa bağlanamayan öğeler ("Deleted video"), ki başlıkları olmadan
        rapor satırı okunamaz.
    `part` genişledi ama KOTA DEĞİŞMEDİ: `playlistItems.list` istenen part
    sayısından bağımsız olarak 1 birim (sayfa başına).
    """
    if playlist_id in _OGE_ONBELLEK:
        return _OGE_ONBELLEK[playlist_id]
    ogeler = []
    req = youtube.playlistItems().list(
        part="contentDetails,snippet,status", playlistId=playlist_id,
        maxResults=50
    )
    while req is not None:
        r = req.execute()
        for item in r.get("items", []):
            ogeler.append((
                item["contentDetails"]["videoId"],
                (item.get("snippet") or {}).get("title") or "",
                (item.get("status") or {}).get("privacyStatus") or "",
            ))
        req = youtube.playlistItems().list_next(req, r)
    _OGE_ONBELLEK[playlist_id] = ogeler
    return ogeler


def playlist_videolari(youtube, playlist_id: str) -> set:
    """Playlist'te GERÇEKTEN bulunan video ID'leri (YouTube'dan, 1 birim/sayfa)."""
    if playlist_id in _UYE_ONBELLEK:
        return _UYE_ONBELLEK[playlist_id]
    idler = {vid for vid, _b, _g in playlist_ogeleri(youtube, playlist_id)}
    _UYE_ONBELLEK[playlist_id] = idler
    return idler


def ekle(youtube, playlist_id: str, video_id: str, dry_run: bool = False) -> bool:
    """video_id'yi playlist'e ekler. Zaten ekliyse hiçbir şey yapmaz.

    NEDEN state.json'a DEĞİL YouTube'a bakıyor: eski sürüm `state.json`daki
    `youtube_playlist_id` alanını kapı olarak kullanıyordu — yani YEREL bir
    iddiayı. "Beton Krallığı" bunun canlı örneği: state'inde
    `youtube_playlist_id: PLamU8IEtNO2k` yazıyor ama video o listede DEĞİL
    (eski video silinip yeniden yüklendi, yeni ID hiç eklenmedi ve yerel alan
    dolu olduğu için bir daha DENENMEDİ de). Kapının kaynağı artık tek
    doğru kaynak: playlist'in kendisi. Maliyeti playlist başına 1 birim,
    önlediği hata 50 birimlik gereksiz yazım VE sessiz kapsam boşluğu."""
    if video_id in playlist_videolari(youtube, playlist_id):
        return False
    if dry_run:
        print(f"  [dry-run] eklenecek: {video_id} -> {playlist_id}")
        return True
    youtube.playlistItems().insert(
        part="snippet",
        body={
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {"kind": "youtube#video", "videoId": video_id},
            }
        },
    ).execute()
    print(f"  playlist'e eklendi: {video_id} -> {playlist_id}")
    _UYE_ONBELLEK[playlist_id].add(video_id)
    # İKİ önbellek de tazeleniyor: biri güncellenip diğeri kalsaydı aynı süreç
    # içinde çalışan bir rapor, az önce eklediğimiz videoyu "eksik" ya da
    # (tersi durumda) "tekrar" sayardı.
    if playlist_id in _OGE_ONBELLEK:
        _OGE_ONBELLEK[playlist_id].append((video_id, "", ""))
    return True


def ensure_in_playlist(youtube, project_dir: str, video_id: str, theme_key: str) -> None:
    """Geriye dönük uyumluluk: videoyu SADECE kendi tarz playlist'ine ekler.
    Tam senkron için `sync_project` kullan.

    DERLEMELER İÇİN KULLANMA: burada tarz anahtarı dışarıdan geliyor ve
    derlemenin `meta["theme"]` alanı türünü ANLATMIYOR — karma bir derlemeyi
    yanlış tarz rafına koyan arıza tam olarak buydu (bkz. sync_project'teki
    derleme dalı). Bu fonksiyonun bugün hiç çağıranı yok."""
    playlist_id = get_or_create_playlist(youtube, theme_key)
    if ekle(youtube, playlist_id, video_id):
        _update_state(project_dir, {"youtube_playlist_id": playlist_id})


# --- enerji eğrisi --------------------------------------------------------


def enerji_sirasi(project_dirs: list) -> list:
    """Proje klasörlerini DİNLEME EĞRİSİNE göre sıralar.

    `derleme.sec()`in eğrisiyle AYNI şekil (sakin açılış → yükselen orta →
    dinlendirici kapanış) ve aynı gerekçe: bir playlist de bir dinleme
    oturumudur, izlenme sırasına göre dizilmiş bir liste 144 BPM'den 86'ya,
    oradan 161'e atlar. Ayrıca sıralamanın kendisi bir KÜRATÖRLÜK kararı —
    YouTube'un "Generic or Repetitive Content" kuralının aradığı şey bu.

    `derleme._enerji` YENİDEN YAZILMADI, olduğu yerden içe aktarılıyor: bu
    depoda aynı yardımcının kopyalanması daha önce `state_io`ya yol açan
    sorunun ta kendisiydi. librosa yoksa (ya da ses dosyası yoksa) sıra
    OLDUĞU GİBİ bırakılır — otomasyon durmaz."""
    try:
        from derleme import _enerji as _rms
    except Exception as e:                       # librosa/derleme yoksa sessizce geç
        print(f"  enerji eğrisi atlandı ({e}) — verilen sıra korunuyor")
        return list(project_dirs)

    olculen = []
    for p in project_dirs:
        ses = os.path.join(p, "audio.wav")
        olculen.append((_rms(ses) if os.path.isfile(ses) else 0.0, p))
    if not any(e for e, _ in olculen):
        print("  enerji ölçülemedi — verilen sıra korunuyor")
        return list(project_dirs)

    e = [p for _, p in sorted(olculen, key=lambda x: x[0])]
    if len(e) < 5:
        return e                                 # eğri kurmak için çok kısa
    acilis = e[1:2]                              # ikinci en sakin: giriş
    inis = e[0:1] + e[2:4]                       # en sakinler sona
    kenar = set(acilis + inis)
    orta = [p for p in e if p not in kenar]
    return acilis + orta + list(reversed(inis))


# --- BEKLENEN ÜYELİK: TEK KURAL KAYNAĞI -----------------------------------


def _playlist_id(youtube, anahtar: str, dry_run: bool = False) -> str:
    """Anahtar -> playlist ID (yoksa oluşturur).

    Anahtarın başındaki "_" koleksiyon (tarz-DIŞI) demek; bu ayrımı her çağıran
    kendi `if`iyle yazmak yerine tek yerde yapıyoruz."""
    if anahtar in KOLEKSIYONLAR:
        return get_or_create_koleksiyon(youtube, anahtar, dry_run)
    return get_or_create_playlist(youtube, anahtar, dry_run)


def _yayinda_mi(state: dict, kisa: bool = False, kesit: bool = False) -> bool:
    """Bu KAYIT playlist'lerde durmalı mı — YouTube'da yayından çekilmemiş mi?

    KURAL BURADA YENİDEN YAZILMIYOR: `uyumluluk._yayindan_cekilmis()`
    çağrılıyor. O fonksiyon iki YANLIŞ POZİTİFİ zaten eliyor ve ikisi de bu
    kanalda gerçek: golden-hour'a zamanlanmış private bir video (YouTube onu
    kendisi public yapacak) ve Content ID karantinasında bekleyen bir DJ seti
    "çekilmiş" SAYILMAZ. Kuralı buraya kopyalasaydım, bir sonraki koşuda
    zamanlanmış her yeni video playlist'siz kalırdı.

    `kisa=True`: Shorts'un KENDİ gizlilik alanları var
    (`youtube_shorts_privacy` / `youtube_shorts_publish_at`) — kuralı
    kopyalamak yerine alanlar kuralın beklediği adlara ÇEVRİLİP aynı fonksiyona
    veriliyor. `Küllerimden Geç`te ikisi de "unlisted" (uzun format VE Shorts).

    `kesit=True`: DJ kesidinin (`dj_clips.py`, ikinci dalga) alanları
    (`youtube_clip_privacy` / `youtube_clip_publish_at`). Kesit HER ZAMAN
    `publishAt` ile 3 gün sonraya zamanlanmış private olarak yükleniyor
    (`dj_clips.KESIT_ERTELEME_GUN`) — yani `youtube_clip_publish_at` dolu
    olduğu sürece `_yayindan_cekilmis` onu doğru şekilde "çekilmemiş" sayıyor.
    Alan adlarını çevirmek yerine kuralı buraya kopyalasaydım, zamanlanmış her
    kesit playlist'siz kalırdı (Shorts'ta aynı tuzak bir kez kuruldu).
    """
    if kisa or kesit:
        onek = "youtube_clip" if kesit else "youtube_shorts"
        state = {
            "youtube_privacy": state.get(onek + "_privacy"),
            "youtube_publish_at": state.get(onek + "_publish_at"),
            "dj_tarama_bekliyor": state.get("dj_tarama_bekliyor"),
        }
    return not uyumluluk._yayindan_cekilmis(state or {})


def beklenen_anahtarlar(project_dir: str, state: dict = None,
                        meta: dict = None) -> dict:
    """Bu projenin HANGİ videosunun HANGİ playlist anahtarlarında OLMASI gerektiği.

    {video_id: [anahtar, ...]} — SIRALI.

    NEDEN AYRI BİR FONKSİYON (2026-09-11): `sync_project` (YAZAN taraf) ve
    `durum()` (OKUYAN/denetleyen taraf) aynı kuralı kullanmak ZORUNDA. Bu
    depoda kopyalanan bir kural defalarca ayrıştı; en tazesi bugün: derlemenin
    TÜRÜ başlıkta `_derleme_tur_bilgisi`'nden, playlist'te `meta["theme"]`den
    karar veriliyordu ve karma bir derleme Hip-Hop rafına girdi. Eğer `durum()`
    "yanlış üyelik"in tanımını `sync_project`ten BAĞIMSIZ üretseydi iki taraf da
    kendi içinde tutarlı, birbirine göre yanlış olurdu — yani teşhis aracı tam
    da aramaya çıktığı arızaya kör kalırdı.

    SIRA DAVRANIŞIN PARÇASI: önce uzun format (tarz -> derleme rafı -> ana
    zincir), sonra Shorts. `sync_project` eski `youtube_playlist_id` alanına
    listenin İLK öğesini yazıyor ve o alanı başka modüller/raporlar okuyor.

    YAYINDAN ÇEKİLMİŞ KAYIT HİÇBİR LİSTEYE GİRMEZ (bkz. `_yayinda_mi`): bu,
    `derleme.py` / `latest_release.py` / `upload/ek_platform_backfill.py`
    üçünün "unlisted = kopya, dışla" kararının playlist tarafındaki karşılığı.
    `Küllerimden Geç` bugün Arabesk rafında VE ana dinleme zincirinde duruyor;
    zincir sırayla çalan bir liste olduğu için dinleyici aynı kaydı iki kez
    (`Yeniden Doğacağım` + kopyası) duyuyor — kanalın en büyük riski olan
    "tekrar içerik / toplu üretilmiş AI içerik" tarifinin merkezi.
    """
    state = _load_state(project_dir) if state is None else state
    meta = _load_meta(project_dir) if meta is None else meta
    # Kaynak KLASÖR değil, meta'daki bayrak: derleme.py'nin ürettiği her
    # derlemede `derleme: true` var ve `build_snippet` de tür kararını bu
    # bayrağa bakarak veriyor — iki tarafın aynı kapıya bakması şart.
    derleme = bool(meta.get("derleme"))
    kok = _kok_adi(project_dir)
    plan = {}

    uzun = state.get("youtube_video_id")
    kisa = state.get("youtube_shorts_video_id")

    if uzun and _yayinda_mi(state):
        anahtarlar = []
        # DERLEME DALI (2026-09-11): tarz seçimi başlıkla AYNI kuraldan
        # türetiliyor (bkz. derleme_tarz_anahtari). Baskın tema parçaların
        # yarısından fazlasıysa video o tarz listesine de girer — başlık zaten
        # "Türkçe <Tarz> Derlemesi" diyordur. Baskın tema yoksa (KARMA) hiçbir
        # tarz listesine girmez: 13 parçanın 5'i hiphop olan bir derlemeyi
        # Hip-Hop rafına koymak, o rafa gelen dinleyiciye 39 dakikanın büyük
        # kısmında BAŞKA tarzları dinletmek demek.
        #
        # TÜM temaların listelerine ekleme SEÇENEĞİ ELENDİ: 13 parçalık bir
        # derleme 5 tarz listesine girerdi; her biri 50 birim (250 birim/derleme)
        # ve her tarz rafında tekrar — üstelik o rafta parçaların TEKİ zaten ayrı
        # bir video olarak duruyor, dinleyici aynı şarkıyı iki kez duyardı.
        # Bu, Shorts'un ana zincirden ayrılma gerekçesinin (yukarıdaki modül
        # notu, madde b) aynısı.
        tarz_anahtari = derleme_tarz_anahtari(meta) if derleme else get_theme_key(meta)
        if tarz_anahtari:
            anahtarlar.append(tarz_anahtari)
        if derleme:
            # Derlemelerin KENDİ rafı. Karma bir derlemenin tarz listesi yok;
            # bu raf olmasaydı hiçbir listede kalmazdı. Ayrıca raf tek başına
            # bir KÜRATÖRLÜK sinyali: "toplu üretilmiş AI içerik" politikasına
            # karşı kanalın en güçlü varlıkları burada bir arada duruyor.
            anahtarlar.append(DERLEME_ANAHTARI)
        # Ana dinleme zinciri SADECE ana katalog (projects/) şarkıları için:
        # dj_sets/ İngilizce ve 40-79 dakikalık setler, derlemeler/ ise zaten
        # aynı şarkıların birleşimi — ikisi de bu zincirde tekrara yol açar.
        # `not derleme` kemer+askı: kapı artık KÖK adına DEĞİL, meta bayrağına
        # da bakıyor — bir derleme yanlışlıkla projects/ altında dursaydı eski
        # kontrol onu zincire sokardı ve dinleyici 39 dakika boyunca zincirdeki
        # şarkıların yarısını İKİNCİ kez duyardı.
        if kok == "projects" and not derleme:
            anahtarlar.append(ZINCIR_ANAHTARI)
        if anahtarlar:
            plan[uzun] = anahtarlar

    if kisa and _yayinda_mi(state, kisa=True):
        plan[kisa] = [SHORTS_ANAHTARI]

    # --- DJ KESİDİ (ikinci dalga, `dj_clips.py`) --------------------------
    # KARAR: kesit de `_shorts` rafına giriyor — setin KENDİ Shorts'uyla AYNI
    # listeye. Bu, üçüncü katmanın ayrılma gerekçesine RAĞMEN değil, TAM OLARAK
    # o gerekçeye uyduğu için:
    #   * (a) "Shorts uzun formatın dinleme zincirine girmez, çünkü 4 dakikalık
    #     şarkıların arasına 30 saniyelik kesit koymak averageTimeInPlaylist'i
    #     düşürür" — kesit 45 saniyelik dikey bir video, yani zaten `_shorts`
    #     rafının TANIMI ("tüm dikey kısa kesitler"). Ayrı bir raf açmak, tek
    #     üyeli Rock playlist'inin (zincir uzunluğu = 1) tekrarı olurdu.
    #   * (b) "her Short AYNI şarkının dikey kesiti; ikisi aynı listede olsaydı
    #     dinleyici aynı şarkıyı arka arkaya İKİ KEZ duyardı" — BU KURAL DJ
    #     KESİDİ İÇİN GEÇERLİ DEĞİL, ve sebebi yapısal: `dj_clips.clip_uret`
    #     `count+1` pencere isteyip EN YÜKSEK enerjili olanı ATIYOR (o pencereyi
    #     setin kendi `shorts_9x16.mp4`'ü kullanıyor) ve pencereler arasında en
    #     az `dj_clips.MIN_ARA_SN` (60 sn) boşluk zorunlu. Yani kesit, setin
    #     Shorts'uyla ÖRTÜŞMEYEN bir aralıktan geliyor — 40-80 dakikalık bir
    #     setin BAŞKA bir anı. Dinleyici aynı sesi iki kez duymuyor. Madde (b)
    #     ana katalog hakkında: orada Short, zincirde TAM hâli duran şarkının
    #     kesiti; burada zincirde duran bir şey YOK (dj_sets `_tum_sarkilar`a
    #     zaten girmiyor).
    # Kesidin kendi başlığı da ayrışıyor (`build_clip_snippet` dakika damgası
    # koyuyor, bkz. tests/test_dj_kesit_yayin_hatti.py), yani rafta iki satır
    # birbirinin kopyası gibi görünmüyor.
    # Set başına EN FAZLA BİR kesit yayınlandığı için (kural YAPISAL, bkz.
    # dj_clips.py) bu raf set başına en fazla 2 öğe alır.
    kesit = state.get("youtube_clip_video_id")
    if kesit and kesit != kisa and _yayinda_mi(state, kesit=True):
        plan[kesit] = [SHORTS_ANAHTARI]
    return plan


# --- senkron --------------------------------------------------------------


def sync_project(youtube, project_dir: str, dry_run: bool = False) -> list:
    """Projenin uzun formatını VE Shorts'unu ait oldukları playlist'lere ekler.

    İmza `auto_process.py`/`dj_famous_process.py`'nin çağırdığı hâliyle AYNI
    kaldı (`sync_project(youtube, project_dir)`), böylece dört katman da o iki
    dosyaya dokunmadan devreye giriyor — derleme davranışı dahil.

    HANGİ LİSTEYE gireceği artık burada DEĞİL `beklenen_anahtarlar()`ta
    kararlaştırılıyor; bu fonksiyon o kararı UYGULUYOR. Gerekçe orada."""
    state = _load_state(project_dir)
    meta = _load_meta(project_dir)
    ad = os.path.basename(os.path.abspath(project_dir))

    uzun = state.get("youtube_video_id")
    kisa = state.get("youtube_shorts_video_id")
    # `kesit` de erken-çıkış kapısına dahil: teoride uzun/kısa olmadan kesit
    # olamaz (kesit kapısı setin kendi Shorts'unu şart koşuyor), ama kapıyı
    # eksik bırakmak "ileride bir yol açılırsa sessizce hiçbir şey yapmaz"
    # sınıfından bir tuzak olurdu.
    kesit = state.get("youtube_clip_video_id")
    if not uzun and not kisa and not kesit:
        print(f"  {ad}: henüz YouTube'a yüklenmemiş, atlanıyor")
        return []

    plan = beklenen_anahtarlar(project_dir, state, meta)
    if not plan:
        # SESSİZ ÇIKMA YOK: yayından çekilmiş (unlisted) bir kopyanın hiçbir
        # listeye girmemesi bir KARAR, kaza değil — log'da GÖRÜNSÜN. Sessizce
        # boş liste dönen bir koruma, olmayan korumadan kötüdür (CLAUDE.md).
        print(f"  {ad}: YouTube'da yayından çekilmiş (unlisted/private) — "
              f"playlist'e girmiyor")
        return []

    listeler = []
    kisalar = None
    kesit_listesi = None
    for video_id, anahtarlar in plan.items():
        for anahtar in anahtarlar:
            pid = _playlist_id(youtube, anahtar, dry_run)
            ekle(youtube, pid, video_id, dry_run)
            listeler.append(pid)
            if anahtar == SHORTS_ANAHTARI:
                # Kesit ile setin KENDİ Shorts'u aynı rafta; hangi state
                # alanına yazılacağı VIDEO KİMLİĞİNDEN ayırt ediliyor. Tek bir
                # `kisalar` değişkeni olsaydı kesidin pid'i Shorts'unkinin
                # üstüne yazılırdı — aynı değeri taşıdıkları için zararsız
                # görünür, ama "kesit senkronlandı mı" sorusu cevapsız kalırdı.
                if kesit and video_id == kesit:
                    kesit_listesi = pid
                else:
                    kisalar = pid

    if not dry_run:
        alanlar = {"youtube_playlists": listeler}
        if plan.get(uzun):
            # Eski alan adı KORUNUYOR: başka modüller/raporlar okuyor.
            # `plan.get(uzun)` kapısı ŞART: uzun format çekilmiş ama Shorts
            # yayındaysa listeler[0] Shorts rafı olurdu ve bu alan sessizce
            # yanlış bir listeyi işaret ederdi.
            alanlar["youtube_playlist_id"] = listeler[0]
        if kisalar:
            alanlar["youtube_shorts_playlist_id"] = kisalar
        if kesit_listesi:
            alanlar["youtube_clip_playlist_id"] = kesit_listesi
        if any(state.get(k) != v for k, v in alanlar.items()):
            _update_state(project_dir, alanlar)
    return listeler


def _proje_klasorleri(base: str) -> list:
    if not os.path.isdir(base):
        return []
    return [
        os.path.join(base, ad)
        for ad in sorted(os.listdir(base))
        if os.path.isdir(os.path.join(base, ad))
    ]


def sync_all(base=None, dry_run: bool = False) -> None:
    """Varsayilan UC KOK. `base` verilirse yalnizca o kok.

    NEDEN degisti (2026-09-11): varsayilan goreli `"projects"` idi, yani
    `--sync-all` `dj_sets/` ve `derlemeler/` kokunu SESSIZCE atliyordu —
    derlemeleri kapsamak icin `--base derlemeler` yazmayi BILMEK gerekiyordu.
    Bu, CLAUDE.md'deki "cagri dogru ama yanlis argumanla" arizasinin ta
    kendisi (ayni hata `youtube_stats.get_stats_batch(base)`'te de yasandi,
    kataloğun yarisi hic olculmuyordu).

    Ayrica goreli yol tuzagi: yanlis cwd'de `_proje_klasorleri` bos liste
    donup "projects bulunamadi" basiyordu. `uyumluluk.KOKLER` mutlak.
    """
    youtube = get_authenticated_service()
    kokler = (base,) if base else uyumluluk.KOKLER
    klasorler = []
    for kok in kokler:
        klasorler.extend(_proje_klasorleri(kok))
    if not klasorler:
        nerede = base if base else ", ".join(uyumluluk.KOK_ADLARI)
        print(f"{nerede} altinda proje bulunamadı.")
        return
    for project_dir in klasorler:
        print(f"=== {os.path.basename(project_dir)} ===")
        sync_project(youtube, project_dir, dry_run)


def kur_zincir(base: str = "projects", dry_run: bool = False) -> None:
    # NOT: burada varsayilan BILEREK tek kok. `_tum_sarkilar` zinciri
    # yalnizca ana katalog sarkilarindan kuruluyor (setler Ingilizce ve
    # 40-79 dk, derlemeler zaten ayni sarkilarin birlesimi; ikisi de
    # zincirde tekrar uretir). Bu, sync_all'daki genisletmenin
    # ISTISNASI — kok listesi degil, icerik karari.
    """`_tum_sarkilar` zincirini enerji eğrisine göre sıralı kurar.

    SADECE EKLER. YouTube'un `playlistItems.insert`'ü `snippet.position`
    verilmediğinde öğeyi SONA ekliyor — yani ekleme SIRASI, listenin sırası
    oluyor. Zaten listede olan videolara dokunulmaz (`ekle` atlar), bu yüzden
    komut tekrar çalıştırılabilir ama mevcut sırayı YENİDEN düzenlemez:
    yeniden sıralamak `playlistItems.delete` gerektirir, o da geri alınamaz
    bir işlem — bilerek bu modülde YOK."""
    youtube = get_authenticated_service()
    adaylar = []
    for project_dir in _proje_klasorleri(base):
        if _load_state(project_dir).get("youtube_video_id"):
            adaylar.append(project_dir)
    if not adaylar:
        print(f"{base} altında yüklenmiş uzun format yok.")
        return

    zincir = get_or_create_koleksiyon(youtube, ZINCIR_ANAHTARI, dry_run)
    mevcut = playlist_videolari(youtube, zincir)
    print(f"zincir {zincir}: {len(mevcut)} video var, {len(adaylar)} aday")
    print("enerji ölçülüyor (librosa, parça başına ~1 sn)…")
    for sira, project_dir in enumerate(enerji_sirasi(adaylar), 1):
        vid = _load_state(project_dir).get("youtube_video_id")
        print(f"  {sira:2d}. {os.path.basename(project_dir)}")
        if ekle(youtube, zincir, vid, dry_run) and not dry_run:
            st = _load_state(project_dir)
            listeler = sorted(set(st.get("youtube_playlists", []) + [zincir]))
            _update_state(project_dir, {"youtube_playlists": listeler})


def durum(base_list=uyumluluk.KOKLER) -> None:
    """SALT OKUMA kapsam raporu: hangi video hiçbir playlist'te değil.

    NEDEN VAR: bu modülün sessizce eksik çalışması (Shorts'un hiç eklenmemesi,
    silinip yeniden yüklenmiş bir videonun bir daha denenmemesi) HİÇBİR yerde
    görünmüyordu. Kota maliyeti playlist başına 1 birim.

    Varsayılan artık KANONIK liste (`uyumluluk.KOKLER`): burada üç kök ELLE
    sayılıyordu — içeriği bugün doğruydu ama dördüncü bir kök açıldığında
    sessizce geride kalacak bir KOPYAydı. KOKLER ayrıca MUTLAK yol tutuyor,
    yani bu teşhis komutu artık repo kökünden çalıştırılmak zorunda değil
    (göreli "projects" yanlış cwd'de os.path.isdir'den False alıp raporu
    SESSİZCE boş gösteriyordu — bu deponun en sık arıza sınıfı)."""
    youtube = get_authenticated_service()
    ids = _load_playlist_ids()
    kapsanan = set()
    # video_id -> o videonun BULUNDUĞU anahtarlar. `kapsanan` sadece "bir
    # yerde var mı" sorusunu cevaplıyordu; YANLIŞ üyelik için hangi listede
    # olduğunu da bilmek gerekiyor.
    gercek = {}
    pid_anahtar = {}
    print("PLAYLIST'LER (önbellekteki):")
    for anahtar, pid in ids.items():
        vids = playlist_videolari(youtube, pid)
        kapsanan |= vids
        pid_anahtar[pid] = anahtar
        for v in vids:
            gercek.setdefault(v, set()).add(anahtar)
        print(f"  {anahtar:15s} {pid}  {len(vids)} video")

    print("")
    print("HİÇBİR PLAYLIST'TE OLMAYAN:")
    eksik = 0
    fazla = []
    for kok in base_list:
        # Sütuna KÖK ADI basılıyor, kökün KENDİSİ değil: KOKLER mutlak yol
        # tutuyor, doğrudan basılsaydı 11 karakterlik sütuna TAM Windows yolu
        # (C: ... /ilk-projem/projects) yazılıp rapor okunamaz hâle gelirdi —
        # youtube_analytics._video_haritasi bugün tam bu tuzağa düşmüştü.
        kok_adi = os.path.basename(os.path.normpath(kok))
        # `_proje_klasorleri` mutlak yolla sorunsuz çalışıyor ve BURADA
        # uyumluluk.proje_klasorleri()'ne tercih ediliyor: rapor her projenin
        # HANGİ kökten geldiğini yazıyor, yani kökler tek tek gezilmek zorunda
        # (hepsini tek düz akışta veren kanonik yardımcı bu bilgiyi
        # kaybettirirdi). Kapsanan kök KÜMESİ yine kanonik — base_list.
        for project_dir in _proje_klasorleri(kok):
            state = _load_state(project_dir)
            plan = beklenen_anahtarlar(project_dir, state)
            # "kesit" SATIRI ŞART (2026-09-12): DJ ikinci dalgası ayrı bir
            # state anahtarı (`youtube_clip_video_id`) kullanıyor. Rapor onu
            # saymasaydı, kesit playlist senkronu sessizce çalışmasa bile
            # "toplam eksik: 0" yazardı — teşhis aracının tam da aramaya
            # çıktığı arızaya kör kalması (bkz. YANLIŞ ÜYELİK bölümünün
            # gerekçesi, aynı hata sınıfı).
            for etiket, alan in (("uzun", "youtube_video_id"),
                                 ("shorts", "youtube_shorts_video_id"),
                                 ("kesit", "youtube_clip_video_id")):
                vid = state.get(alan)
                # `plan.get(vid)` kapısı ŞART: "eksik" sayacı eskiden plana HİÇ
                # bakmıyordu, yani plan onu bilerek hiçbir listeye koymasa bile
                # (unlisted kopya → beklenen_anahtarlar() boş döner) videoyu
                # "eksik" sayıyordu. Hemen aşağıdaki FAZLA bloğu planı
                # kullanıyordu, bu blok kullanmıyordu — AYNI KURAL İKİ YERDE İKİ
                # FARKLI ŞEKİLDE, bu deponun en sık arıza deseni. Canlı kanıt:
                # 'Küllerimden Geç' playlist temizliğinden sonra fazla'dan
                # eksik'e geçip yanlış alarm üretti (2026-09-11).
                if vid and vid not in kapsanan and plan.get(vid):
                    eksik += 1
                    print(f"  {kok_adi:11s} {etiket:6s} {vid}  "
                          f"{os.path.basename(project_dir)}")
                if not vid:
                    continue
                # FAZLA üyelik: gerçekte var ama plan onu oraya koymuyor.
                bekleniyor = set(plan.get(vid) or ())
                for a in sorted(gercek.get(vid, set()) - bekleniyor):
                    fazla.append((kok_adi, etiket, vid,
                                  os.path.basename(project_dir), a))
    print("")
    print(f"toplam eksik: {eksik}")

    # ---- YANLIŞ ÜYELİK ----------------------------------------------------
    # NEDEN (2026-09-11): bu rapor yalnızca "hiçbir listede olmayan"ı arıyordu.
    # `Gece Seansı Vol. 1` yanlışlıkla Hip-Hop listesindeyken `durum()`
    # "toplam eksik: 0" diyordu — bir listede OLDUĞU için kapsanmış sayılıyordu.
    # Yani düzeltme yazılmış ama çalışacağı an gelmemiş bir kural, teşhis
    # aracında da GÖRÜNMÜYORDU. Silme hâlâ ELLE (playlistItems.delete bilerek
    # yok); amaç kalıntının bir rapor satırı olarak görünmesi.
    print("")
    print("YANLIŞ LİSTEDE (plan oraya koymuyor — Studio'dan elle çıkar):")
    for kok_adi, etiket, vid, proje, anahtar in fazla:
        print(f"  {kok_adi:11s} {etiket:6s} {vid}  {proje}  -> {anahtar}")
    print(f"toplam fazla: {len(fazla)}")

    # ---- MÜKERRER KAYIT ---------------------------------------------------
    # Aynı video bir listeye İKİ KEZ eklenmişse `playlist_videolari` küme
    # döndürdüğü için yukarıdaki karşılaştırma bunu göremez; ayrı sayılıyor.
    print("")
    print("AYNI LİSTEDE BİRDEN FAZLA KEZ:")
    mukerrer = 0
    for anahtar, pid in ids.items():
        sayac = {}
        for v, _b, _g in playlist_ogeleri(youtube, pid):
            sayac[v] = sayac.get(v, 0) + 1
        for v, n in sorted(sayac.items()):
            if n > 1:
                mukerrer += 1
                print(f"  {anahtar:15s} {v}  x{n}")
    print(f"toplam mükerrer: {mukerrer}")


def main():
    parser = argparse.ArgumentParser(
        description="Videoları tarz / ana zincir / Shorts playlist'lerine ekler."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--sync-all", action="store_true", help="Tüm yüklü projeleri senkronla")
    group.add_argument("--project", help="Tek bir proje klasörü (örn. projects/sarki-adi)")
    group.add_argument("--kur-zincir", action="store_true",
                       help="Ana dinleme zincirini enerji eğrisine göre kur")
    group.add_argument("--durum", action="store_true",
                       help="SALT OKUMA: playlist kapsamı raporu")
    parser.add_argument("--base", default="projects", help="Proje klasörlerinin kök dizini")
    parser.add_argument("--dry-run", action="store_true",
                        help="Hiçbir şey yazma, ne yapacağını söyle")
    args = parser.parse_args()

    if args.durum:
        durum()
    elif args.kur_zincir:
        kur_zincir(args.base, args.dry_run)
    elif args.sync_all:
        sync_all(args.base, args.dry_run)
    else:
        youtube = get_authenticated_service()
        sync_project(youtube, args.project, args.dry_run)


if __name__ == "__main__":
    main()
