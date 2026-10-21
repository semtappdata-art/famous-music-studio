"""Bekleyen (audio.wav hazır) projeleri otomatik render edip YouTube/Shorts'a
yükler ve Distribution Package oluşturur — Windows Görev Zamanlayıcı ile
periyodik çalıştırılmak üzere tasarlandı.

Kullanım:
    python auto_process.py
    python auto_process.py --privacy unlisted
    python auto_process.py --base projects
    python auto_process.py --count 3

Otomatik kademeleme (varsayılan, `--count` verilmezse): kaç proje bekliyorsa
24 saati o sayıya eşit aralıklara böler (ör. 9 proje → ~2.7 saatte bir 1 tane,
2 proje → 12 saatte bir 1 tane) ve son yüklemeden bu hesaplanan aralık kadar
süre geçtiyse SADECE O ZAMAN bir proje işler — aksi halde hiçbir şey yapmadan
çıkar. Amaç: aynı anda birden fazla şarkı paylaşmanın aynı takipçi kitlesinin
aynı taramasında birbiriyle yarışmasını önlemek. Bunun işlemesi için Görev
Zamanlayıcı'yı SIK çalıştır (ör. saatte bir tek bir tetikleyici) — script
her çağrıldığında "sırası geldi mi" diye kendi kendine karar verir.
`--count N` verirsen bu otomatik kademe DEVRE DIŞI kalır, tam N kadarı
zamanlama beklemeden hemen işlenir.

Çıktı hem konsola hem auto_process.log dosyasına yazılır.
"""

import argparse
import datetime
import json
import os
import sys
import time

# Windows'ta konsol/log çıktısı UTF-8'e zorlanır (Türkçe karakter + emoji)
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "upload"))

import config
import yayin_ritmi
from git_sync import auto_pull, push_path

from gizli_maskele import maskele
from log_rotate import trim_log
from pathlib import Path

AUDIO_NAMES = ["audio.wav", "audio.mp3", "audio.m4a"]
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "auto_process.log")
LOCK_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".auto_process.lock")
LOCK_STALE_SECONDS = 4 * 60 * 60
DAILY_WINDOW_SECONDS = 24 * 60 * 60
MIN_YAYIN_ARALIGI_SN = 52 * 60 * 60
UPLOAD_TIMESTAMP_KEYS = ("youtube_uploaded_at", "youtube_shorts_uploaded_at")

YENI_YAYIN_TIMESTAMP_KEYS = ("youtube_uploaded_at",)
YENI_YAYIN_PUBLIC_ANI_KEYS = ("youtube_publish_at",)

GORUNURLUK_PLANI_ALANI = "youtube_gorunurluk_plani"
GORUNURLUK_UYGULANDI_ALANI = "youtube_gorunurluk_uygulandi_at"
GORUNURLUK_TEKRAR_BEKLEME_SN = 3 * 3600
GORUNURLUK_TEMPO_ALANI = "tempo_sayilir"
TEMPO_DISI_PUBLIC_ANI_ALANI = "youtube_public_ani_tempo_disi"
STUDIO_PLAN_ALANI = "youtube_studio_planli"


_KILIT_BIZDE = False


def log(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {maskele(msg)}"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    if _KILIT_BIZDE:
        try:
            os.utime(LOCK_PATH, None)
        except OSError:
            pass


def _acquire_lock() -> bool:
    global _KILIT_BIZDE
    try:
        fd = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        try:
            age = time.time() - os.path.getmtime(LOCK_PATH)
        except OSError:
            return False
        if age < LOCK_STALE_SECONDS:
            return False
        log(f"  Eski kilit dosyası bulundu ({age:.0f}s) — önceki çalıştırma muhtemelen "
            f"yarıda kalmış, yok sayılıp devam ediliyor.")
        try:
            os.remove(LOCK_PATH)
            fd = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except OSError:
            return False
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))
    _KILIT_BIZDE = True
    return True


def _release_lock() -> None:
    global _KILIT_BIZDE
    _KILIT_BIZDE = False
    if os.path.isfile(LOCK_PATH):
        os.remove(LOCK_PATH)


def _has_any(project_dir: str, names: list) -> bool:
    return any(os.path.isfile(os.path.join(project_dir, n)) for n in names)


def _load_state(project_dir: str) -> dict:
    state_path = os.path.join(project_dir, "state.json")
    if os.path.isfile(state_path):
        with open(state_path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def find_ready_projects(base: str) -> list:
    """audio'su hazır olan tüm proje klasörlerini, klasörün oluşturulma zamanına
    göre (en eskiden en yeniye) sıralı döner."""
    ready = []
    if not os.path.isdir(base):
        return ready
    for name in os.listdir(base):
        project_dir = os.path.join(base, name)
        if not os.path.isdir(project_dir):
            continue
        if _has_any(project_dir, AUDIO_NAMES):
            ready.append(project_dir)
    ready.sort(key=lambda p: (os.path.getctime(p), p))
    return ready


_ANA_ANAHTARLAR = ("youtube_video_id", "youtube_shorts_video_id")


def _is_fully_done(project_dir: str) -> bool:
    """YouTube uzun format + Shorts yüklenmişse True."""
    state = _load_state(project_dir)
    return all(key in state for key in _ANA_ANAHTARLAR)


def _last_upload_time(project_dirs: list, keys: tuple = UPLOAD_TIMESTAMP_KEYS):
    latest = None
    for project_dir in project_dirs:
        state = _load_state(project_dir)
        studio = STUDIO_PLAN_ALANI in state
        if studio:
            an = _studio_public_ani(state)
            if an is not None and an <= time.time() and (latest is None or an > latest):
                latest = an
        for key in keys:
            if studio and key.startswith("youtube_"):
                continue
            ts = state.get(key)
            if not ts:
                continue
            try:
                t = time.mktime(time.strptime(ts, "%Y-%m-%dT%H:%M:%S"))
            except ValueError:
                continue
            if latest is None or t > latest:
                latest = t
    return latest


def _studio_public_ani(state: dict):
    from datetime import datetime
    kayit = (state or {}).get(STUDIO_PLAN_ALANI)
    adaylar = [state.get("youtube_publish_at")]
    if isinstance(kayit, dict):
        adaylar.append(kayit.get("an"))
    for deger in adaylar:
        if not isinstance(deger, str) or not deger:
            continue
        try:
            an = datetime.fromisoformat(deger.replace("Z", "+00:00"))
        except ValueError:
            continue
        if an.tzinfo is not None:
            return an.timestamp()
    return None


def _studio_public_oncesi(state: dict) -> bool:
    if STUDIO_PLAN_ALANI not in (state or {}):
        return False
    an = _studio_public_ani(state)
    return an is None or an > time.time()


def _son_yeni_yayin_ani(project_dirs: list):
    from datetime import datetime
    latest = _last_upload_time(project_dirs, YENI_YAYIN_TIMESTAMP_KEYS)
    for project_dir in project_dirs:
        state = _load_state(project_dir)
        if STUDIO_PLAN_ALANI in state:
            an = _studio_public_ani(state)
            if an is not None and (latest is None or an > latest):
                latest = an
            continue
        for key in YENI_YAYIN_PUBLIC_ANI_KEYS:
            deger = state.get(key)
            if not isinstance(deger, str) or not deger:
                continue
            try:
                an = datetime.fromisoformat(deger.replace("Z", "+00:00"))
            except ValueError:
                continue
            if an.tzinfo is None:
                continue
            t = an.timestamp()
            if latest is None or t > latest:
                latest = t
    return latest


def _auto_pace_count(pending: list, ready: list, count: int = 1,
                     pencere_paydasi: int | None = None) -> int:
    """YENİ ÜRETİM PLANI: 6 şarkı/hafta + 28 saat taban + golden-hour slot tahsisi."""
    if not pending:
        return 0

    simdi = time.time()

    # 1. Yeni şarkı vs geri doldurma ayır
    yeni_sarkilar = []
    geri_doldurma = []
    for p in pending:
        st = _load_state(p)
        if st.get("youtube_video_id"):
            geri_doldurma.append(p)
        else:
            yeni_sarkilar.append(p)

    # 2. Haftalık sayaç kontrolü
    yeni_kalan = yayin_ritmi.haftalik_kalan("sarki")
    if yeni_kalan <= 0:
        log(f"  Haftalık şarkı tavanı doldu ({config.HAFTALIK_SARKI_HEDEFI}/{config.HAFTALIK_SARKI_HEDEFI}), yeni şarkı işlenmeyecek")
        yeni_sarkilar = []

    # 3. Batch hazırla
    batch_adaylar = yeni_sarkilar + geri_doldurma
    batch = batch_adaylar[:count] or batch_adaylar[:1]

    batch_yeni = any("youtube_video_id" not in _load_state(p) for p in batch)

    # 4. İlk yükleme ise hemen başla
    last = _last_upload_time(ready)
    if last is None:
        log(f"  İlk yükleme, hemen başlıyor ({len(batch)} proje)")
        return min(count, len(batch))

    # 5. YENİ ŞARKI kontrolleri
    if batch_yeni:
        # 5a. 28 saat tabanı
        son_yeni = _son_yeni_yayin_ani(ready)
        if son_yeni is not None:
            taban_kalan = config.MIN_YENI_SARKI_ARALIK_SAAT - (simdi - son_yeni)
            if taban_kalan > 0:
                log(f"  Yeni şarkı tabanı: {taban_kalan/3600:.1f} saat bekleme")
                return 0

        # 5b. R1: set/derleme ↔ şarkı 48 saat
        try:
            _izin, _kalan, _sebep = yayin_ritmi.kanal_tabani(batch[0], simdi=simdi, tur="sarki")
            if not _izin:
                log(f"  Ritim kapısı (set/şarkı): {_sebep}")
                return 0
        except Exception as e:
            log(f"  Ritim kapısı hesaplanamadı ({type(e).__name__}: {str(e)[:120]}) — bekliyor")
            return 0

        # 5c. Golden-hour slot tahsisi
        proje_adi = os.path.basename(os.path.normpath(batch[0]))
        pub_at, slot, sebep = yayin_ritmi.publish_at_hesapla(proje_adi, "sarki", simdi)
        if pub_at is None:
            log(f"  Slot tahsisi başarısız: {sebep}")
            return 0
        log(f"  ✓ Slot tahsis edildi: {sebep}")

        # Günlük maks 2 yeni şarkı
        bugun = datetime.datetime.now(config.TR_TZ).date()
        bugun_yeni = 0
        for p in ready:
            st = _load_state(p)
            pub = st.get("youtube_publish_at") or st.get("youtube_uploaded_at")
            if pub:
                try:
                    pub_dt = datetime.datetime.fromisoformat(pub.replace("Z", "+00:00"))
                    if pub_dt.date() == bugun and not st.get("youtube_video_id"):
                        bugun_yeni += 1
                except Exception:
                    pass
        if bugun_yeni >= config.GUNLUK_MAKS_YENI_SARKI:
            log(f"  Günlük yeni şarkı tavanı doldu ({config.GUNLUK_MAKS_YENI_SARKI}/{config.GUNLUK_MAKS_YENI_SARKI})")
            return 0

    # 6. GERİ DOLDURMA için: boş slot var mı?
    geri_batch = [p for p in batch if "youtube_video_id" in _load_state(p)]
    if geri_batch and not batch_yeni:
        slotlar = yayin_ritmi.golden_hour_slotlari()
        musait = False
        for s in slotlar:
            if s["baslangic"] >= simdi and not s["dolu"]:
                musait = True
                break
        if not musait:
            log(f"  Geri doldurma için müsait golden-hour slotu yok")
            return 0
        log(f"  ✓ Geri doldurma için slot müsait ({len(geri_batch)} proje)")

    # 7. Günlük pencere bölüşümü (sadece geri doldurma için)
    pencere_gap = DAILY_WINDOW_SECONDS / (pencere_paydasi or len(pending))
    pencere_kalan = pencere_gap - (simdi - last)
    if pencere_kalan > 0 and not batch_yeni:
        log(f"  Günlük pencere: {pencere_kalan/3600:.1f} saat bekleme (geri doldurma)")
        return 0

    return min(count, len(batch))


def _youtube_servisi():
    from youtube_auth import get_authenticated_service
    return get_authenticated_service()


def _gorunurlugu_youtubeda_uygula(youtube, video_idler: list, hedef: str) -> list:
    from set_privacy import guvenli_status_govdesi

    def _oku():
        yanit = youtube.videos().list(part="status", id=",".join(video_idler)).execute()
        return {it.get("id"): (it.get("status") or {}) for it in (yanit.get("items") or [])}

    mevcut = _oku()
    eksik = [v for v in video_idler if v not in mevcut]
    if eksik:
        raise RuntimeError("status okunamadı: %s — gizlilik DEĞİŞTİRİLMEDİ" % ", ".join(eksik))
    degisen = []
    for vid in video_idler:
        if mevcut[vid].get("privacyStatus") == hedef:
            continue
        govde = guvenli_status_govdesi(mevcut[vid], hedef)
        youtube.videos().update(part="status", body={"id": vid, "status": govde}).execute()
        degisen.append(vid)
    deneme = max(1, int(getattr(config, "GORUNURLUK_GERI_OKUMA_DENEME", 2)))
    bekleme = float(getattr(config, "GORUNURLUK_GERI_OKUMA_BEKLEME_SN", 5))
    yanlis = []
    for deneme_no in range(deneme):
        sonra = _oku()
        yanlis = ["%s=%s" % (v, (sonra.get(v) or {}).get("privacyStatus"))
                  for v in video_idler if (sonra.get(v) or {}).get("privacyStatus") != hedef]
        if not yanlis:
            break
        if deneme_no + 1 < deneme:
            time.sleep(bekleme)
    if yanlis:
        raise RuntimeError("geri okuma hedefi (%s) doğrulamadı: %s" % (hedef, ", ".join(yanlis)))
    return degisen


def _youtube_gorunurluk_planlarini_uygula(project_dirs: list) -> None:
    from datetime import datetime, timezone
    import state_io
    import uyumluluk

    planlilar = []
    for p in project_dirs:
        try:
            plan = _load_state(p).get(GORUNURLUK_PLANI_ALANI)
        except (OSError, ValueError):
            continue
        if isinstance(plan, dict) and plan.get("hedef"):
            planlilar.append((str(plan.get("istendi_at") or ""),
                              os.path.basename(os.path.normpath(p)), p))
    if not planlilar:
        return
    simdi = datetime.now(config.TR_TZ)
    pencere = _golden_pencere_anahtari(simdi)
    if pencere is None:
        return
    planlilar.sort()
    _, ad, proje = planlilar[0]

    for p in project_dirs:
        try:
            damga = _load_state(p).get(GORUNURLUK_UYGULANDI_ALANI)
            if damga and _golden_pencere_anahtari(datetime.fromisoformat(damga)) == pencere:
                log(f"  YouTube görünürlük planı: '{os.path.basename(os.path.normpath(p))}' zaten uygulandı — '{ad}' bekliyor")
                return
        except (OSError, ValueError, TypeError):
            continue

    state = uyumluluk._durum(proje)
    plan = state.get(GORUNURLUK_PLANI_ALANI) or {}
    hedef = plan.get("hedef")
    if hedef not in ("public", "unlisted", "private"):
        log(f"  YouTube görünürlük planı: '{ad}' geçersiz hedef ({hedef!r})")
        return
    if _yayin_bekletiliyor(state):
        log(f"  YouTube görünürlük planı: '{ad}' yayın bekletiliyor ({_bekletme_sebebi(state)})")
        return
    son_hata_at = plan.get("son_hata_at")
    if son_hata_at:
        try:
            gecen = (simdi - datetime.fromisoformat(son_hata_at)).total_seconds()
        except (ValueError, TypeError):
            gecen = None
        if gecen is not None and gecen < GORUNURLUK_TEKRAR_BEKLEME_SN:
            log(f"  YouTube görünürlük planı: '{ad}' soğuma sürüyor ({int(gecen // 60)} dk önce)")
            return
    if hedef == "public":
        try:
            u_hatalar, _ = uyumluluk.kontrol(proje, "yukleme")
        except Exception as e:
            log(f"  YouTube görünürlük planı: '{ad}' public YAPILMADI — uyumluluk ÇÖKTÜ ({type(e).__name__}: {str(e)[:150]})")
            return
        if u_hatalar:
            log(f"  YouTube görünürlük planı: '{ad}' public YAPILMADI — uyumluluk HATASI: {str(u_hatalar[0])[:200]}")
            return
    onekler = [o for o in ("youtube", "youtube_shorts") if state.get(o + "_video_id")]
    if not onekler:
        log(f"  YouTube görünürlük planı: '{ad}' state'inde video kimliği yok")
        return

    try:
        degisen = set(_gorunurlugu_youtubeda_uygula(_youtube_servisi(),
                        [state[o + "_video_id"] for o in onekler], hedef) or ())
    except Exception as e:
        taze = uyumluluk._durum(proje)
        taze_plan = taze.get(GORUNURLUK_PLANI_ALANI)
        if isinstance(taze_plan, dict):
            taze_plan["son_hata_at"] = simdi.isoformat(timespec="seconds")
            taze_plan["son_hata"] = ("%s: %s" % (type(e).__name__, e))[:300]
            state_io.durum_yaz(proje, taze)
        log(f"  YouTube görünürlük planı HATA: '{ad}' -> {hedef}: {type(e).__name__}: {str(e)[:200]}")
        return

    an_utc = simdi.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    tempo_sayilir = plan.get(GORUNURLUK_TEMPO_ALANI, True) is not False
    taze = uyumluluk._durum(proje)
    notlar = []
    for o in onekler:
        taze[o + "_privacy"] = hedef
        vid = state[o + "_video_id"]
        if hedef != "public":
            continue
        if vid not in degisen:
            notlar.append(f"{vid} zaten public")
            continue
        if o == "youtube" and not tempo_sayilir:
            taze[TEMPO_DISI_PUBLIC_ANI_ALANI] = an_utc
            notlar.append(f"{vid} tempo DIŞI")
        else:
            taze[o + "_publish_at"] = an_utc
    taze.pop(GORUNURLUK_PLANI_ALANI, None)
    taze[GORUNURLUK_UYGULANDI_ALANI] = simdi.isoformat(timespec="seconds")
    state_io.durum_yaz(proje, taze)
    idler = ", ".join(str(taze.get(o + "_video_id")) for o in onekler)
    log(f"  YouTube görünürlük planı UYGULANDI: '{ad}' -> {hedef} ({idler}), public anı {an_utc}" + (f" [{'; '.join(notlar)}]" if notlar else ""))


def _golden_pencere_anahtari(an):
    an = an.astimezone(config.TR_TZ)
    for bas, bit in config.GOLDEN_HOURS:
        if bas <= an.hour < bit:
            return "%s@%02d" % (an.strftime("%Y-%m-%d"), bas)
    return None


def _yayin_bekletiliyor(state: dict) -> bool:
    import uyumluluk
    return bool((state or {}).get(uyumluluk.BEKLETME_ALANI))


def _bekletme_sebebi(state: dict) -> str:
    import uyumluluk
    b = (state or {}).get(uyumluluk.BEKLETME_ALANI)
    sebep = b.get("sebep") if isinstance(b, dict) else b
    return str(sebep or "sebep yazılmamış")[:160]


def _bekletilenleri_ayir(project_dirs: list) -> tuple:
    kalan, bekletilen = [], []
    for p in project_dirs:
        try:
            bekle = _yayin_bekletiliyor(_load_state(p))
        except (OSError, ValueError):
            bekle = False
        (bekletilen if bekle else kalan).append(p)
    return kalan, bekletilen


def _yalniz_drain_bekleyenleri_ayir(project_dirs: list) -> tuple:
    """Instagram kaldırıldı — Shorts gecikmeli süpürgesi bu işi yapar."""
    return list(project_dirs), []


def _studio_planli_bekleyenleri_ayir(project_dirs: list) -> tuple:
    secilebilir, bekleyen = [], []
    for p in project_dirs:
        try:
            bekle = _studio_public_oncesi(_load_state(p))
        except (OSError, ValueError, TypeError):
            bekle = False
        (bekleyen if bekle else secilebilir).append(p)
    return secilebilir, bekleyen


def _drain_golden_hour_queue(project_dirs: list) -> None:
    """YouTube görünürlük planı + Shorts gecikmeli süpürgesi kontrolü."""
    for project_dir in project_dirs:
        state = _load_state(project_dir)
        if _yayin_bekletiliyor(state):
            continue
    try:
        _youtube_gorunurluk_planlarini_uygula(project_dirs)
    except Exception as e:
        log(f"  YouTube görünürlük planı HATA: {type(e).__name__}: {str(e)[:200]}")


def _olustur_dagitim_paketleri(project_dirs: list) -> None:
    """YouTube/Shorts yüklenmiş projeler için Distribution Package oluşturur."""
    try:
        from distribution_package import build_distribution_package
    except ImportError as e:
        log(f"  Dagitim paketi modulu yuklenemedi: {e}")
        return

    for project_dir in project_dirs:
        try:
            state = _load_state(project_dir)
            if not (state.get("youtube_video_id") or state.get("youtube_shorts_video_id")):
                continue

            pkg_dir = Path(project_dir) / "distribution"
            manifest_path = pkg_dir / "package.json"
            if manifest_path.exists():
                try:
                    with open(manifest_path, encoding="utf-8") as f:
                        existing = json.load(f)
                    if existing.get("source_hash") == state.get("audio_hash"):
                        continue
                except Exception:
                    pass

            build_distribution_package(
                project_dir=project_dir,
                include_categories=["video", "streaming", "social_audio", "distributor"],
                distributor="distrokid"
            )
            log(f"  [OK] Dagitim paketi hazir: {os.path.basename(project_dir)}")

            import state_io
            fresh_state = state_io.load_state(project_dir)
            audio_path = None
            for name in ["audio.wav", "audio.mp3", "audio.m4a"]:
                p = os.path.join(project_dir, name)
                if os.path.isfile(p):
                    audio_path = p
                    break
            if audio_path:
                import hashlib
                h = hashlib.sha256()
                with open(audio_path, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        h.update(chunk)
                fresh_state["audio_hash"] = h.hexdigest()
                state_io.durum_yaz(project_dir, fresh_state)
        except Exception as e:
            log(f"  Dagitim paketi HATA ({os.path.basename(project_dir)}): {e}")


def _topluluk_bildir(project_dir: str, video_id: str, log_fn=log) -> None:
    """Yeni yayinlanan videoyu topluluğa bildir (Madde 29).

    Discord webhook + Telegram kanal mesaji + abone listesi logu.

    FAIL-SAFE KURALI: bu fonksiyon YAYINI ASLA GERI ALMAZ, geri almaz —
    hata olursa sadece bildirim atlanir ve loglanir. Sebep: bildirim
    altyapisi (webhook/token) kapali olabilir; bu durumda yayin yine de
    basarili olmalidir. CLAUDE.md §2 "fail-closed" kurali YAYIN icindir;
    bildirim YAN etki (side-effect) alanidir ve fail-OPEN olmalidir.
    """
    try:
        import topluluk
    except Exception as e:
        log_fn(f"  Topluluk bildirimi atlandi (modul hatasi): {e}")
        return

    try:
        meta = {}
        meta_yolu = os.path.join(project_dir, "meta.json")
        if os.path.isfile(meta_yolu):
            with open(meta_yolu, encoding="utf-8") as f:
                meta = json.load(f) or {}

        baslik = meta.get("title") or os.path.basename(os.path.normpath(project_dir))
        tur = meta.get("theme") or ""
        etiketler = meta.get("tags") or []
        if isinstance(etiketler, list) and etiketler:
            etiketler = ", ".join(str(t) for t in etiketler[:4])
        else:
            etiketler = tur or "Türkçe Müzik"

        link = f"https://youtu.be/{video_id}"
        site = getattr(config, "SITE_URL", "https://famousmusicstudio.com")

        mesaj = (
            f"**{baslik}**\n\n"
            f"🎵 {etiketler}\n"
            f"▶️ {link}\n\n"
            f"🌐 {site}\n"
            f"🔔 Abone ol → https://youtube.com/@{getattr(config, 'YOUTUBE_HANDLE', 'Famous_musics_studio')}"
        )

        sonuc = topluluk.bildir(baslik=f"🎵 {baslik}", mesaj=mesaj, link=link)
        kanallar = []
        if sonuc.get("discord"):
            kanallar.append("Discord")
        if sonuc.get("telegram"):
            kanallar.append("Telegram")
        if sonuc.get("abone_sayisi"):
            kanallar.append(f"{sonuc['abone_sayisi']} abone logu")
        if kanallar:
            log_fn(f"  📣 Topluluk bildirimi: {', '.join(kanallar)}")
        else:
            log_fn("  📣 Topluluk bildirimi: kanal yapilandirilmamis (atlandi)")
    except Exception as e:
        log_fn(f"  📣 Topluluk bildirimi HATA (yayin etkilenmedi): {e}")


def _arsivle_yukleme_sonrasi(project_dir: str) -> None:
    """Upload sonrasi kritik dosyalari arsivle."""
    if not getattr(config, 'ARCHIVE_CONFIG', {}).get('enabled', True):
        return
    
    from datetime import datetime
    import shutil
    
    backup_dir = Path("archives") / datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # Kritik dosyalar
    for fname in ["audio.wav", "art.jpg", "cover.png", "cover_vertical.png",
                   "meta.json", "sozler.md", "structure.txt", "segments.json"]:
        src = Path(project_dir) / fname
        if src.exists():
            shutil.copy2(src, backup_dir / fname)
    
    # Render ciktilari
    output_dir = Path(project_dir) / "output"
    if output_dir.exists():
        for f in output_dir.glob("*.mp4"):
            shutil.copy2(f, backup_dir / f.name)
    
    log(f"  📦 Arsivlendi: {backup_dir}")

def _shorts_gecikmeli_supurge() -> None:
    """YouTube Shorts'u uzun formatın public anından 24 sa SONRA yükler (R3a)."""
    if not yayin_ritmi.shorts_gecikmeli_mi():
        log("  Shorts süpürgesi: kapalı (config.YAYIN_RITMI_SHORTS_GECIKMELI)")
        return
    if not os.path.isfile(os.path.join(os.path.dirname(os.path.abspath(__file__)), "upload", "token.json")):
        log("  Shorts süpürgesi: upload/token.json yok, atlandı")
        return
    bekleyen, yuklenen = 0, None
    try:
        import uyumluluk
        for proje in uyumluluk.proje_klasorleri():
            try:
                st = _load_state(proje)
            except (OSError, ValueError):
                continue
            if (not st.get("youtube_video_id") or st.get("youtube_shorts_video_id")
                    or st.get("dj_tarama_bekliyor") or st.get("dj_tarama_engelli")
                    or _yayin_bekletiliyor(st)
                    or not os.path.isfile(os.path.join(proje, "output", "shorts_9x16.mp4"))):
                continue
            hazir, _kalan, sebep = yayin_ritmi.shorts_zamani(st)
            if not hazir:
                bekleyen += 1
                continue
            ad = os.path.basename(os.path.normpath(proje))
            izin, sebep = yayin_ritmi.platform_gun_izni(st, "youtube_shorts")
            if not izin:
                log(f"  Shorts süpürgesi: {ad} — {sebep}")
                bekleyen += 1
                continue
            if not _shorts_uyumluluk_gecti(proje, ad):
                continue
            if yuklenen is not None:
                bekleyen += 1
                continue
            try:
                from youtube_upload import upload_short as yt_upload_short
                sid = yt_upload_short(proje, st.get("youtube_privacy") or "public",
                                      st["youtube_video_id"], schedule=True)
                yuklenen = ad
                log(f"  YouTube Shorts (24 sa gecikmeli): {ad} tamam, https://youtube.com/shorts/{sid}")
            except Exception as e:
                log(f"  YouTube Shorts (24 sa gecikmeli) HATA ({ad}): {e}")
                continue
            try:
                from youtube_playlists import get_authenticated_service as yt_service
                from youtube_playlists import sync_project as yt_sync_playlist
                yt_sync_playlist(yt_service(), proje)
            except Exception as e:
                log(f"  YouTube playlist HATA: {e}")
    except Exception as e:
        log(f"  Shorts süpürgesi HATA: {type(e).__name__}: {str(e)[:200]}")
        return
    log(f"  Shorts süpürgesi: yüklenen {yuklenen or 'yok'}, bekleyen {bekleyen}")


def _shorts_uyumluluk_gecti(proje: str, ad: str) -> bool:
    try:
        import uyumluluk
        _uh, _uu = uyumluluk.kontrol(proje, "yukleme")
    except Exception as e:
        log(f"  Shorts süpürgesi: {ad} uyumluluk kapısı ÇÖKTÜ ({type(e).__name__})")
        return False
    if _uh:
        log(f"  Shorts süpürgesi: {ad} uyumluluk HATASI — atlandı: {_uh[0][:120]}")
        return False
    return True


def _refresh_latest_listing() -> None:
    try:
        import latest_release
        latest_release.regenerate()
        push_path(
            os.path.dirname(os.path.abspath(__file__)),
            "docs/latest.html",
            "docs: şarkı listesini güncelle (otomatik)",
            log,
        )
    except Exception as e:
        log(f"  latest.html güncelleme HATA: {e}")


def _refresh_stats(base: str) -> None:
    try:
        from youtube_stats import get_stats_batch
        sonuc = get_stats_batch(base)
        if sonuc.get("istek"):
            log(f"  İstatistik: {sonuc['video']} video, {sonuc['proje']} proje ({sonuc['istek']} istek)")
    except Exception as e:
        log(f"  İstatistik güncelleme HATA: {e}")


def _refresh_comments() -> None:
    try:
        from youtube_comments import fetch_comments
        veri = fetch_comments()
        if veri.get("istek"):
            log(f"  Yorumlar: {len(veri.get('bekleyen', []))} yanıt bekliyor ({veri['istek']} istek)")
    except Exception as e:
        log(f"  Yorum güncelleme HATA: {e}")


def process_project(project_dir: str, privacy: str, schedule: bool = True) -> None:
    upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "upload")

    # Uyumluluk kapısı
    try:
        import uyumluluk
        _uh, _uu = uyumluluk.kontrol(project_dir, "yukleme")
    except Exception as e:
        log(f"  uyumluluk kapisi COKTU ({type(e).__name__}: {e}) — fail-closed, bu proje bu kosuda yayinlanmiyor")
        return
    try:
        uyumluluk.rapor_yaz(project_dir, _uh, _uu, log)
    except Exception as e:
        log(f"  uyumluluk raporu yazilamadi ({type(e).__name__}: {e}) — hata/uyari: {len(_uh)}/{len(_uu)}")
    if _uh:
        log("  uyumluluk hatasi nedeniyle bu proje yayinlanmiyor")
        return

    state = _load_state(project_dir)
    youtube_video_id = state.get("youtube_video_id")

    if youtube_video_id:
        log("  YouTube: zaten yüklü, atlanıyor")
    elif os.path.isfile(os.path.join(upload_dir, "token.json")):
        try:
            from youtube_upload import upload_video as yt_upload
            youtube_video_id = yt_upload(project_dir, privacy, schedule=schedule)
            log(f"  YouTube: tamam, https://youtu.be/{youtube_video_id}")
            # Upload sonrası arşivleme
            _arsivle_yukleme_sonrasi(project_dir)
            # TOPLULUK BILDIRIMI (Madde 29) — yeni video Discord/Telegram'a düşer.
            # FAIL-SAFE: buradaki HATA yayını geri almaz, sadece bildirimi atlar.
            _topluluk_bildir(project_dir, youtube_video_id, log)
        except Exception as e:
            log(f"  YouTube HATA: {e}")
    else:
        log("  YouTube atlandı: upload/token.json yok (önce youtube_auth.py çalıştır)")

    # Playlist senkronu
    if youtube_video_id and os.path.isfile(os.path.join(upload_dir, "token.json")):
        try:
            from youtube_playlists import get_authenticated_service as yt_service
            from youtube_playlists import sync_project as yt_sync_playlist
            yt_sync_playlist(yt_service(), project_dir)
        except Exception as e:
            log(f"  YouTube playlist HATA: {e}")

    # YouTube Shorts
    if "youtube_shorts_video_id" in state:
        log("  YouTube Shorts: zaten yüklü, atlanıyor")
    elif not youtube_video_id:
        log("  YouTube Shorts atlandı: önce uzun format yüklenmeli")
    elif not yayin_ritmi.shorts_zamani(_load_state(project_dir))[0]:
        _sonuc = yayin_ritmi.shorts_zamani(_load_state(project_dir))
        log(f"  YouTube Shorts: {_sonuc[2]} — Shorts süpürgesi yükleyecek")
    elif os.path.isfile(os.path.join(upload_dir, "token.json")):
        try:
            from youtube_upload import upload_short as yt_upload_short
            shorts_id = yt_upload_short(project_dir, privacy, youtube_video_id, schedule=schedule)
            log(f"  YouTube Shorts: tamam, https://youtube.com/shorts/{shorts_id}")
        except Exception as e:
            log(f"  YouTube Shorts HATA: {e}")
    else:
        log("  YouTube Shorts atlandı: upload/token.json yok")

    # İkinci playlist senkronu (Shorts sonrası)
    if youtube_video_id and os.path.isfile(os.path.join(upload_dir, "token.json")):
        try:
            from youtube_playlists import get_authenticated_service as yt_service
            from youtube_playlists import sync_project as yt_sync_playlist
            yt_sync_playlist(yt_service(), project_dir)
        except Exception as e:
            log(f"  YouTube playlist HATA: {e}")

    # BÜYÜME: takvim.json oluştur/güncelle (T-minus takvimi)
    try:
        import takvim
        meta = _load_state(project_dir)
        if not meta.get("yayin_tarihi"):
            # Golden-hour penceresinden birini tahmin et
            import config
            from datetime import datetime, timezone, timedelta
            TR_TZ = timezone(timedelta(hours=3))
            yayin_tarihi = config.next_golden_publish_time()
            if yayin_tarihi is None:
                yayin_tarihi = datetime.now(TR_TZ) + timedelta(hours=2)
            meta["yayin_tarihi"] = yayin_tarihi.isoformat()
            from state_io import atomic_write
            atomic_write(os.path.join(project_dir, "state.json"), meta)
        takvim.olustur(project_dir, meta["yayin_tarihi"])
        log(f"  Takvim.json oluşturuldu: {project_dir}")
    except Exception as e:
        log(f"  Takvim oluşturma HATA: {e}")

    # BÜYÜME: Seri playlist'lerine ekle (City Pulse, Night Drive, vb.)
    meta = _load_state(project_dir)
    if meta.get("series") and youtube_video_id:
        try:
            from youtube_playlists import get_authenticated_service as yt_service
            from youtube_playlists import add_to_series_playlist as yt_add_series
            yt_add_series(yt_service(), project_dir, youtube_video_id)
            log(f"  Seri playlist'e eklendi: {meta['series']}")
        except Exception as e:
            log(f"  Seri playlist ekleme HATA: {e}")
    elif not meta.get("series") and youtube_video_id:
        # Normal playlist (config.PLAYLIST_IDS)
        try:
            from youtube_playlists import get_authenticated_service as yt_service
            from youtube_playlists import sync_project as yt_sync_playlist
            yt_sync_playlist(yt_service(), project_dir)
        except Exception as e:
            log(f"  YouTube playlist HATA: {e}")


def main():
    parser = argparse.ArgumentParser(description="Bekleyen (audio hazır) projeleri otomatik render edip YouTube/Shorts'a yükler.")
    parser.add_argument("--privacy", default="public", choices=["private", "unlisted", "public"], help="YouTube görünürlük")
    parser.add_argument("--base", default="projects", help="Proje klasörlerinin kök dizini")
    parser.add_argument("--no-schedule", action="store_true", help="Golden-hour zamanlamasını devre dışı bırakır")
    parser.add_argument("--count", type=int, default=None, help="Bu koşuda işlenecek en fazla proje sayısı")
    args = parser.parse_args()

    trim_log(LOG_PATH)
    auto_pull(os.path.dirname(os.path.abspath(__file__)), log)

    if not _acquire_lock():
        log("Başka bir auto_process.py çalışması zaten sürüyor — bu çalıştırma atlanıyor.")
        return

    try:
        from gizli_maskele import reset_trace_context, start_span, end_span
        reset_trace_context()
        main_span_id = start_span("auto_process_main")

        ready = find_ready_projects(args.base)
        if not ready:
            log("İşlenecek proje yok (audio hazır olan bulunamadı).")
            end_span(main_span_id)
            return

        pending = [p for p in ready if not _is_fully_done(p)]
        pending, bekletilen = _bekletilenleri_ayir(pending)
        for p in bekletilen:
            log(f"Yayın bekletiliyor, sıraya alınmadı: {os.path.basename(os.path.normpath(p))} ({_bekletme_sebebi(_load_state(p))})")
        if not pending:
            _drain_golden_hour_queue(ready)
            log("Tüm hazır projeler zaten YouTube/Shorts'a yüklenmiş.")
            end_span(main_span_id)
            return

        pencere_paydasi = len(pending)
        secilebilir, _ = _yalniz_drain_bekleyenleri_ayir(pending)
        secilebilir, studio_bekleyen = _studio_planli_bekleyenleri_ayir(secilebilir)
        if studio_bekleyen:
            log(f"YouTube Studio'dan planlı, public anı bekleniyor: {', '.join(os.path.basename(os.path.normpath(p)) for p in studio_bekleyen)}")

        if not secilebilir:
            _drain_golden_hour_queue(ready)
            log("İşlenecek proje yok bu kosuda, sadece golden-hour kontrolü yapıldı.")
            end_span(main_span_id)
            return

        count = (args.count if args.count is not None
                 else _auto_pace_count(secilebilir, ready, pencere_paydasi=pencere_paydasi))
        if count == 0:
            _drain_golden_hour_queue(ready)
            log("İşlenecek proje yok bu koşuda (count=0), sadece golden-hour kontrolü yapıldı.")
            end_span(main_span_id)
            return

        batch = secilebilir[:count]
        log(f"{len(pending)} bekleyen proje var, bu koşuda işlenecek ({len(batch)}): {', '.join(os.path.basename(p) for p in batch)}")
        for project_dir in batch:
            process_project(project_dir, args.privacy, schedule=not args.no_schedule)

        _drain_golden_hour_queue([p for p in ready if p not in batch])
        log("Çalıştırma tamamlandı.")
        _islenen = list(batch)
        _kuyruk = list(secilebilir[count:])
        _hatalar = []

    finally:
        if 'main_span_id' in locals():
            from gizli_maskele import end_span
            end_span(main_span_id)

        _islenen = _islenen if '_islenen' in dir() else []
        _kuyruk = _kuyruk if '_kuyruk' in dir() else []
        _hatalar = _hatalar if '_hatalar' in dir() else []

        _refresh_latest_listing()
        _refresh_stats(None)
        _refresh_comments()
        _olustur_dagitim_paketleri(ready)
        _shorts_gecikmeli_supurge()

        # YouTube Analytics
        try:
            from upload.youtube_analytics import rapor as _yt_analytics
            _yt_analytics()
        except Exception as e:
            log(f"  YouTube analytics HATASI: {e}")

        # YouTube kota
        try:
            from youtube_kota import kosu_sonu as _youtube_kota_sonu
            _youtube_kota_sonu(log=log)
        except Exception as e:
            log(f"  YouTube kota kosu sonu HATASI: {e}")

        # End screen kontrolü
        try:
            from uyumluluk import end_screen_kontrol as _end_kontrol
            for _p in _islenen:
                try:
                    _end_kontrol(_p, log=log)
                except Exception as _e:
                    log(f"  End screen kontrolu HATASI ({_p}): {_e}")
        except Exception as e:
            log(f"  End screen kontrolu HATASI: {e}")

        # ABONE KALDIRACLARI (2026-10-20) — yeni görev DEĞİL, mevcut
        # saatlik görevin `finally` bloğuna bağlanan süpürge.
        # NEDEN burada: yeni bir yüklemeden sonra sabitlenen ilk yorum
        # eksik kalmasın. Watermark kanal seviyesindedir (tek çağrı);
        # ilk yorum video başına bir kez yapılır (state bayrağı korur).
        try:
            from upload.youtube_abone import abone_supurge as _abone_supurge
            _abone_supurge(log=log)
        except Exception as e:
            log(f"  Abone kaldiraclari HATASI: {e}")

        _release_lock()
        try:
            from _llm_router import provider_status as _llm_status
            _llm_status()
        except Exception as e:
            log(f"  LLM router HATASI: {e}")


if __name__ == "__main__":
    main()