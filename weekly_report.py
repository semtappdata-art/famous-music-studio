# -*- coding: utf-8 -*-
"""Katalogun YouTube istatistiklerini (uzun format + Shorts) tazeleyip özet bir
tablo basar — haftalık takip için. Ayrıca izlenme SÜRESİ (watch-time) özetini
ekler ve Instagram token'ının süresi yaklaşıyorsa uyarır.

Kullanım:
    python weekly_report.py                 # projects + dj_sets + derlemeler
    python weekly_report.py --base projects # tek kök
    python weekly_report.py --izlenme       # sadece izlenme süresi raporu (elle)

İki ayrı giriş noktası var:

1. `main()` — ELLE çalıştırılan tam rapor (tablo + izlenme süresi).
2. `izlenme_raporu()` — saatlik `auto_process` koşusundan çağrılmak üzere
   yazılmış, HAFTADA BİR gerçekten çalışan izlenme süresi kontrolü. Neden:
   bu dosya hiçbir Görev Zamanlayıcı görevine bağlı değil (bkz.
   `saglik_kontrol.py` docstring'i, madde 2) — yani içine yazılan her ölçüm
   pratikte hiç çalışmıyor. `saglik_kontrol` bu sorunu "korumaları saatlik
   hatta bağla, bildirimi günde bire indir" deseniyle çözdü; burada aynı desen
   GÜNLÜK damgadan HAFTALIK damgaya genelleştiriliyor (izlenme raporu haftalık
   bir şey, saatlik değil).
"""

import argparse
import datetime
import json
import os
import sys
import time

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "upload"))

from youtube_stats import get_stats_batch, KOKLER

INSTAGRAM_TOKEN_PATH = os.path.join(REPO, "upload", "instagram_token.json")
INSTAGRAM_WARN_DAYS = 10  # bu kadar gün kala uyar (60 günlük token için makul bir tampon)

# saglik_kontrol.py ile AYNI durum dosyası — damgalar tek yerde toplansın,
# iki ayrı "en son ne zaman bildirdim" defteri tutulmasın.
DURUM_DOSYASI = os.path.join(REPO, "upload", "saglik_durum.json")

HAFTA_ANAHTARI = "izlenme_rapor_hafta"        # rapor bu hafta çalıştı mı
BOS_ANAHTARI = "izlenme_rapor_bos_gun"        # veri gelmedi -> bugün tekrar deneme
TOKEN_ANAHTARI = "izlenme_token_bildirim_hafta"
RAPOR_BILDIRIM = "izlenme_rapor_bildirim_hafta"

AUTH_KOMUTU = "python upload/youtube_analytics.py --auth"


# --------------------------------------------------------------------------
# Damga/bildirim yardımcıları — saglik_kontrol._durum/_kaydet/_bildir deseni,
# tek farkla: damga "gün" olmak zorunda değil, dışarıdan veriliyor (hafta).
# Kopya (import yerine) bilerek: saglik_kontrol'ün özel isimlerine bağlanmak
# o dosya değiştiğinde bu hattı sessizce kırardı.
# --------------------------------------------------------------------------
def _durum(yol: str | None = None) -> dict:
    try:
        with open(yol or DURUM_DOSYASI, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _kaydet(g: dict, yol: str | None = None) -> None:
    """Damgalari birlestirip ATOMIK yazar (bkz. state_io).

    NEDEN state_io: duz `open(..., "w")` hedefi ONCE SIFIRLIYOR; `json.dump`
    bitmeden surec olurse diskte YARIM bir JSON kaliyor. Burada ek bir sebep
    var: bu dosya (`upload/saglik_durum.json`) `saglik_kontrol.py` ile
    PAYLASILIYOR — biri gunluk saglik damgalarini, digeri haftalik izlenme
    damgalarini yaziyor. Yarim bir yazim iki modulun damgalarini BIRLIKTE
    sifirlardi.
    """
    yol = yol or DURUM_DOSYASI
    d = _durum(yol)
    d.update(g)
    try:
        import state_io
        state_io._atomik_yaz(yol, d)
    except OSError:
        pass


def _bildir(baslik: str, mesaj: str, anahtar: str, damga: str,
            yol: str | None = None) -> bool:
    """Aynı anahtar için DÖNEM BAŞINA bir bildirim gönderir. Gönderildiyse True.

    saglik_kontrol._bildir'in genelleştirilmişi: orada damga sabit olarak gün
    ("%Y-%m-%d"), burada çağıran belirliyor — izlenme raporunda ISO hafta.
    Saatlik koşuda her seferinde telefon çalması uyarıyı değersizleştirir.

    DAMGA SADECE BAŞARIDA ATILIYOR (2026-09-11, `saglik_kontrol._bildir` ile
    AYNI düzeltme — bilerek birebir aynı desen). Eskiden `notify.send`in dönüş
    değeri YOK SAYILIYOR, istisnası da `except Exception: pass` ile yutuluyor,
    damga yine atılıyordu. Pratik etkisi `TOKEN_ANAHTARI`nda gerçek: "Analytics
    izni hiç alınmamış" hatırlatması gönderilemese bile hafta damgalanıp uyarı
    bir HAFTA susuyordu. İzlenme ölçümü bugüne kadar zaten hiç çalışmamıştı;
    bozulduğunu haber verecek TEK mekanizma bu bildirim.

    İSTİSNA YAKALAMAK YETMİYOR: `notify.send` üç başarısızlık yolunun da
    (kanal kurulu değil / HTTP hatası / ağ hatası) hiçbirinde PATLAMIYOR,
    sessizce `False` dönüyor (bkz. notify.py). Yani bu arızayı yakalamanın tek
    yolu DÖNÜŞ DEĞERİNE bakmak.

    Fazladan susturma YOK: başarısızlıkta damga atılmadığı için bir sonraki
    saatlik koşu yeniden dener, ama log kirlenmiyor — gürültü kontrolü zaten
    `notify.py`nin içinde (`uyar_bir_kez`, süreç başına anahtar başına tek
    satır).
    """
    if _durum(yol).get(anahtar) == damga:
        return False
    try:
        import notify
        gonderildi = notify.send(baslik, mesaj)
    except Exception as e:
        print("  bildirim gönderilemedi (%s): %s" % (baslik, str(e)[:150]))
        return False
    if not gonderildi:
        # Damga YOK -> bir sonraki saatlik koşu yeniden dener. Sebebi
        # notify.uyar_bir_kez() koşu başına bir kez zaten yazdı.
        return False
    _kaydet({anahtar: damga}, yol)
    return True


def _hafta(t: float | None = None) -> str:
    """ISO yıl-hafta damgası ("2026-W37").

    time.strftime("%G-W%V") Windows'ta güvenilir değil (platform C
    kütüphanesine bağlı) — isocalendar() her yerde aynı sonucu veriyor.
    """
    y, w, _ = datetime.date.fromtimestamp(t if t is not None else time.time()).isocalendar()
    return "%d-W%02d" % (y, w)


def _kok_adi(kok: str) -> str:
    """Kök için kısa ad ("projects"), TAM YOL değil.

    youtube_analytics.KOKLER mutlak yollardan oluşuyor (bilerek — göreli
    bırakılınca yanlış cwd'de sessizce boş sonuç veriyordu). O yüzden özetin
    anahtarı `C:\\Users\\...\\projects` gelebiliyor ve tabloyu taşırıyor.
    basename her iki durumda da doğru: kısa ad verilirse kendisini döner.
    """
    return os.path.basename(str(kok).rstrip("\\/")) or str(kok)


# --------------------------------------------------------------------------
def _check_instagram_token_expiry() -> None:
    """Instagram token'ının kalan ömrü (elle koşuda bilgi amaçlı).

    NOT: bu kontrolün OTOMATİK hattı artık `saglik_kontrol.instagram_token_suresi()`
    (saatlik auto_process koşusundan çalışıyor). Burada duruyor çünkü elle
    `python weekly_report.py` çalıştıran kullanıcı da bu bilgiyi görmeli.
    """
    if not os.path.isfile(INSTAGRAM_TOKEN_PATH):
        return  # Instagram hiç bağlanmamış, kontrol edecek bir şey yok
    try:
        with open(INSTAGRAM_TOKEN_PATH, "r", encoding="utf-8") as f:
            token = json.load(f)
        expires_in = token.get("expires_in")
        if not expires_in:
            return
        # expires_in, dosyanın en son YAZILDIĞI ana göre (exchange_code veya
        # refresh_access_token) göreli saniye — dosyanın mtime'ını o an olarak kabul
        # ediyoruz (kesin değil ama makul bir yaklaşım).
        issued_at = os.path.getmtime(INSTAGRAM_TOKEN_PATH)
        expires_at = issued_at + expires_in
        days_left = (expires_at - time.time()) / 86400
        if days_left < 0:
            print(f"⚠️  Instagram token'ının süresi DOLMUŞ görünüyor (~{-days_left:.0f} gün önce) — "
                  f"upload/instagram_upload.py 401 vermeye başlamış olabilir. "
                  f"Yeniden yetkilendir: python upload/instagram_auth.py --print-url")
        elif days_left < INSTAGRAM_WARN_DAYS:
            print(f"⚠️  Instagram token'ının süresi ~{days_left:.0f} gün içinde doluyor — "
                  f"yakında yeniden yetkilendirmen gerekecek: python upload/instagram_auth.py --print-url")
    except (json.JSONDecodeError, OSError, KeyError):
        pass  # sağlık kontrolü, ana raporu bozmasın


def _load_state(project_dir: str) -> dict:
    state_path = os.path.join(project_dir, "state.json")
    if os.path.isfile(state_path):
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}
    return {}


def _sayi(state: dict, *alanlar) -> int:
    """Birden fazla alanın toplamı; None/eksik değerler 0 sayılır."""
    t = 0
    for a in alanlar:
        try:
            t += int(state.get(a) or 0)
        except (TypeError, ValueError):
            pass
    return t


# --------------------------------------------------------------------------
# İzlenme süresi (watch-time)
# --------------------------------------------------------------------------
def _ozet_satirlari(ozet: dict) -> list:
    """youtube_analytics.rapor()["ozet"] -> basılacak satırlar.

    Tek yerde: hem elle koşu (`main`) hem saatlik hat (`izlenme_raporu`)
    aynı biçimi kullansın. Kök adı burada kısaltılıyor (bkz. _kok_adi).
    """
    satirlar = ["İZLENME SÜRESİ (uzun format)",
                "%-12s %6s %9s %11s %9s" % ("kök", "video", "izlenme", "toplam dk", "ort sn")]
    for kok, o in sorted(ozet.items(), key=lambda kv: _kok_adi(kv[0])):
        satirlar.append("%-12s %6d %9d %11d %9d"
                        % (_kok_adi(kok), o["video"], o["izlenme"], o["dakika"],
                           o["ort_izlenme_sn"]))
    satirlar.append("")
    # Asıl karşılaştırma: BİR videonun ürettiği ortalama izlenme dakikası.
    # Toplamı karşılaştırmak katalog lehine yanıltıcı olurdu — orada 18,
    # setlerde 2 video var.
    for kok, o in sorted(ozet.items(), key=lambda kv: _kok_adi(kv[0])):
        if o["video"]:
            satirlar.append("  %s: video başına %.0f dakika izlenme"
                            % (_kok_adi(kok), o["dakika"] / o["video"]))
    return satirlar


def _bildirim_metni(ozet: dict) -> str:
    parcalar = []
    for kok, o in sorted(ozet.items(), key=lambda kv: _kok_adi(kv[0])):
        if o["video"]:
            parcalar.append("%s: video başına %.0f dk (%d video)"
                            % (_kok_adi(kok), o["dakika"] / o["video"], o["video"]))
    return " | ".join(parcalar) or "veri yok"


def izlenme_raporu(log=print, zorla: bool = False, durum_dosyasi: str | None = None,
                   rapor_fn=None, token_yolu: str | None = None) -> dict:
    """HAFTADA BİR izlenme süresi raporu — saatlik auto_process koşusundan.

    NEDEN BURADA: `upload/youtube_analytics.py` doğru yazıldı ama tek çağıranı
    bu dosyaydı ve bu dosya hiçbir zamanlayıcı görevine bağlı değil — yani
    ölçüm pratikte HİÇ çalışmıyordu. `saglik_kontrol.py` bugün tam bu sebeple
    yazıldı: zamanlayıcıya bağlı olmayan korumaları saatlik hatta bağlamak
    için. Aynı deseni izliyoruz, tek farkla: damga günlük değil HAFTALIK.

    Üç ayrı damga var ve üçü de aynı amaca hizmet ediyor — saatlik koşuda
    gürültü yapmamak:
      * HAFTA_ANAHTARI — rapor bu hafta çalıştıysa bir daha çalışma.
      * BOS_ANAHTARI   — Analytics veri döndürmediyse (yeni video, henüz
                         işlenmemiş) bugün tekrar deneme, yarın dene. Haftayı
                         damgalamıyoruz, yoksa tek boş sonuç yüzünden rapor
                         bir hafta kaybolurdu.
      * TOKEN_ANAHTARI — izin hiç alınmamışsa haftada bir hatırlat.

    Hiçbir hata otomasyonu durdurmaz.
    """
    yol = durum_dosyasi or DURUM_DOSYASI
    hafta = _hafta()
    bugun = time.strftime("%Y-%m-%d")
    d = _durum(yol)
    if not zorla:
        if d.get(HAFTA_ANAHTARI) == hafta:
            return {"durum": "atlandi", "neden": "bu hafta çalıştı", "hafta": hafta}
        if d.get(BOS_ANAHTARI) == bugun:
            return {"durum": "atlandi", "neden": "bugün veri gelmedi", "gun": bugun}

    token = token_yolu
    if rapor_fn is None:
        try:
            from youtube_analytics import rapor as _rapor, TOKEN_PATH
        except Exception as e:
            log("  İzlenme raporu: youtube_analytics yüklenemedi (%s)" % str(e)[:120])
            _kaydet({BOS_ANAHTARI: bugun}, yol)
            return {"durum": "modul_yok", "hata": str(e)[:120]}
        rapor_fn = _rapor
        if token is None:
            token = TOKEN_PATH

    # ÖN KOŞUL: analytics ayrı bir token kullanıyor (yükleme token'ını
    # geçersiz kılmamak için, bkz. youtube_analytics modül notu). Kullanıcı
    # OAuth akışını hiç çalıştırmadıysa ölçüm sessizce boş döner ve KİMSE
    # FARK ETMEZ — bugün altı kez görülen desenin ta kendisi. Haftada bir,
    # gürültüsüz bir hatırlatma bırakıyoruz.
    if token and not os.path.isfile(token):
        mesaj = ("İzlenme süresi ölçümü çalışmıyor: YouTube Analytics izni hiç "
                 "alınmamış. Bir kereye mahsus: " + AUTH_KOMUTU)
        log("  UYARI: " + mesaj)
        gonderildi = _bildir("İzlenme ölçümü kapalı", mesaj, TOKEN_ANAHTARI, hafta, yol)
        return {"durum": "token_yok", "bildirim": gonderildi, "komut": AUTH_KOMUTU}

    try:
        r = rapor_fn() or {}
    except Exception as e:
        log("  İzlenme raporu HATA: %s" % str(e)[:150])
        _kaydet({BOS_ANAHTARI: bugun}, yol)
        return {"durum": "hata", "hata": str(e)[:150]}

    ozet = r.get("ozet") or {}
    if not ozet:
        log("  İzlenme raporu: Analytics'ten veri gelmedi — bugün tekrar denenmeyecek.")
        _kaydet({BOS_ANAHTARI: bugun}, yol)
        return {"durum": "veri_yok"}

    for satir in _ozet_satirlari(ozet):
        log(satir)
    # Hafta damgalanıyor: bir sonraki koşularda tekrar API'ye gitmesin.
    # BOS_ANAHTARI temizleniyor ki yeni haftada eski gün damgası engel olmasın.
    _kaydet({HAFTA_ANAHTARI: hafta, BOS_ANAHTARI: ""}, yol)
    _bildir("Haftalık izlenme süresi", _bildirim_metni(ozet), RAPOR_BILDIRIM, hafta, yol)
    return {"durum": "tamam", "hafta": hafta, "ozet": ozet}


def _watch_time_ozeti() -> None:
    """Elle koşuda izlenme süresi bölümü — damgaya bakmadan, her zaman basar."""
    try:
        from youtube_analytics import rapor, TOKEN_PATH
        if not os.path.isfile(TOKEN_PATH):
            print()
            print("İzlenme süresi ölçümü kapalı (analytics izni yok). Bir kereye mahsus: "
                  + AUTH_KOMUTU)
            return
        ozet = (rapor() or {}).get("ozet") or {}
        if not ozet:
            return
        print()
        for satir in _ozet_satirlari(ozet):
            print(satir)
    except Exception as e:
        print("  İzlenme süresi alınamadı: %s" % str(e)[:120])


# --------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Katalogun YouTube istatistiklerini tazeleyip özet tablo basar."
    )
    parser.add_argument(
        "--base", default=None,
        help=("Tek bir kök dizin (örn. projects). Verilmezse youtube_stats.KOKLER "
              "— projects + dj_sets + derlemeler — birlikte taranır."),
    )
    parser.add_argument("--izlenme", action="store_true",
                        help="Sadece izlenme süresi raporunu bas (damgayı yok sayar).")
    args = parser.parse_args()

    if args.izlenme:
        sonuc = izlenme_raporu(zorla=True)
        if sonuc.get("durum") == "token_yok":
            print("Analytics izni yok. Çalıştır: " + AUTH_KOMUTU)
        return

    _check_instagram_token_expiry()

    kokler = [os.path.abspath(args.base)] if args.base else list(KOKLER)

    # TEK istek: eskiden her proje için ayrı get_stats() çağrılıyordu
    # (18 proje = 18 istek) ve Shorts hiç ölçülmüyordu. get_stats_batch
    # videos.list'in 50 id sınırını kullanıyor: 18 uzun + 18 Shorts = 1 istek.
    # force=True — haftalık rapor ELLE isteniyor, günlük tazeleme aralığını bekleme.
    try:
        sonuc = get_stats_batch(kokler[0] if args.base else None, force=True)
        if sonuc.get("istek"):
            print("Tazelendi: %d video, %d proje (%d istek)"
                  % (sonuc.get("video", 0), sonuc.get("proje", 0), sonuc["istek"]))
    except Exception as e:
        print("İstatistik tazelenemedi (%s) — kayıtlı son değerlerle devam ediliyor."
              % str(e)[:150])

    rows = []
    for kok in kokler:
        if not os.path.isdir(kok):
            continue
        for name in sorted(os.listdir(kok)):
            project_dir = os.path.join(kok, name)
            if not os.path.isdir(project_dir):
                continue
            state = _load_state(project_dir)
            # Shorts'u da kabul et: bir proje uzun formata hiç yüklenmemiş ama
            # Shorts'a yüklenmiş olabilir — eski sürüm bunları tabloda hiç
            # göstermiyordu.
            if not (state.get("youtube_video_id") or state.get("youtube_shorts_video_id")):
                continue
            rows.append((
                name,
                _kok_adi(kok),
                _sayi(state, "youtube_views"),
                _sayi(state, "youtube_shorts_views"),
                _sayi(state, "youtube_likes", "youtube_shorts_likes"),
                _sayi(state, "youtube_comments", "youtube_shorts_comments"),
                state.get("youtube_privacy", "?"),
            ))

    if not rows:
        print("Henüz YouTube'a yüklenmiş proje yok.")
        return

    rows.sort(key=lambda r: r[2] + r[3], reverse=True)
    name_w = max(max(len(r[0]) for r in rows), 5) + 2
    kok_w = max(max(len(r[1]) for r in rows), 3) + 2
    cizgi = "-" * (name_w + kok_w + 46)
    print(f"{'Şarkı'.ljust(name_w)}{'Kök'.ljust(kok_w)}"
          f"{'İzlenme':>10}{'Shorts':>9}{'Beğeni':>9}{'Yorum':>8}  Görünürlük")
    print("(Beğeni/Yorum = uzun format + Shorts toplamı)")
    print(cizgi)
    t_uzun = t_short = t_like = t_yorum = 0
    for name, kok, views, shorts, likes, comments, privacy in rows:
        print(f"{name.ljust(name_w)}{kok.ljust(kok_w)}"
              f"{views:>10}{shorts:>9}{likes:>9}{comments:>8}  {privacy}")
        t_uzun += views
        t_short += shorts
        t_like += likes
        t_yorum += comments
    print(cizgi)
    print(f"{'Toplam'.ljust(name_w)}{''.ljust(kok_w)}"
          f"{t_uzun:>10}{t_short:>9}{t_like:>9}{t_yorum:>8}")
    print(f"Genel izlenme (uzun + Shorts): {t_uzun + t_short}")

    _watch_time_ozeti()


if __name__ == "__main__":
    main()
