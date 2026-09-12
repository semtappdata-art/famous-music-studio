"""auto_process._auto_pace_count() için testler — --count elle verilmediğinde
kaç proje işleneceğine karar veren otomatik kademeleme mantığı. Yanlışsa
şarkılar art arda (algoritma rekabeti riski) ya da hiç paylaşılmaz.

2026-09-11'den beri iki kural birlikte çalışıyor:
1. Günlük pencere bölüşümü: 24 saat / bekleyen sayısı.
2. YENİ yayınlar için MIN_YAYIN_ARALIGI_SN (52 saat) TABANI — 1. kural tek
   başına bir günde 7 yayına izin veriyordu ("toplu üretim" deseni).
Taban SADECE bu koşuda GERÇEKTEN işlenecek projeler (`pending[:count]`, yani
main()'deki batch dilimiyle birebir aynısı) arasında yeni bir yayın varsa
uygulanır; state.json'ında `youtube_video_id` olanlar "geri doldurma" sayılır
ve muaftır. Ölçüt 2026-09-11'de `pending[0]`'dan batch'in TAMAMINA genişletildi
(bkz. test_batch_icindeki_yeni_yayin_tabani_atlatmiyor).
"""

import json
import time

import auto_process as ap


def _project_with_upload(tmp_path, name, hours_ago):
    d = tmp_path / name
    d.mkdir()
    ts = time.strftime(
        "%Y-%m-%dT%H:%M:%S", time.localtime(time.time() - hours_ago * 3600)
    )
    (d / "state.json").write_text(json.dumps({"youtube_uploaded_at": ts}))
    return str(d)


def _geri_doldurma_projesi(tmp_path, name="backfill"):
    """YouTube'a çoktan çıkmış, sadece Instagram'ı eksik kalmış bir proje.
    İşlenecek dilimin (`pending[:count]`) TAMAMI böyleyse 52 saatlik
    yeni-yayın tabanı uygulanmamalı."""
    d = tmp_path / name
    d.mkdir()
    (d / "state.json").write_text(json.dumps({
        "youtube_video_id": "abc123",
        "youtube_shorts_video_id": "def456",
        # instagram_media_id YOK -> _is_fully_done() False -> pending'de kalır
    }))
    return str(d)


def test_no_pending_projects_returns_zero():
    assert ap._auto_pace_count(pending=[], ready=[]) == 0


def test_never_uploaded_before_starts_immediately(tmp_path):
    ready = [str(tmp_path)]  # state.json yok -> _last_upload_time None döner
    assert ap._auto_pace_count(pending=["a"], ready=ready) == 1


def test_single_pending_recent_upload_is_too_early(tmp_path):
    ready = [_project_with_upload(tmp_path, "p1", hours_ago=1)]
    # tek proje bekliyor -> gerekli aralık en az 52 saat, 1 saat önce yüklenmiş -> erken
    assert ap._auto_pace_count(pending=["a"], ready=ready) == 0


def test_new_release_waits_for_min_gap_not_24h(tmp_path):
    """ESKİDEN 24 saat yeterliydi; artık YENİ bir yayın için taban 52 saat.
    25 saat sonra HENÜZ erken, 53 saat sonra sırası gelmiş olmalı."""
    ready_25h = [_project_with_upload(tmp_path, "p1", hours_ago=25)]
    assert ap._auto_pace_count(pending=["a"], ready=ready_25h) == 0

    ready_53h = [_project_with_upload(tmp_path, "p2", hours_ago=53)]
    assert ap._auto_pace_count(pending=["a"], ready=ready_53h) == 1


def test_min_gap_blocks_same_day_batch_of_seven(tmp_path):
    """Tabanın asıl amacı: 7 YENİ dosya aynı gün düşerse eski formül
    24/7 ≈ 3,4 saatlik aralık verip yedisini de aynı gün yayınlıyordu.
    Taban devredeyken 3 saat önce yükleme yapılmışsa hâlâ 0 dönmeli."""
    ready = [_project_with_upload(tmp_path, "p1", hours_ago=3)]
    pending = ["yeni"] * 7  # var olmayan yollar -> state {} -> yeni yayın sayılır
    assert ap._auto_pace_count(pending=pending, ready=ready) == 0

    # 51 saat sonra bile erken (taban 52), 53 saatte sırası gelir.
    ready_51h = [_project_with_upload(tmp_path, "p2", hours_ago=51)]
    assert ap._auto_pace_count(pending=pending, ready=ready_51h) == 0
    ready_53h = [_project_with_upload(tmp_path, "p3", hours_ago=53)]
    assert ap._auto_pace_count(pending=pending, ready=ready_53h) == 1


def test_backfill_project_is_exempt_from_min_gap(tmp_path):
    """Geri doldurma muafiyeti: işlenecek proje YouTube'a çıkmışsa taban
    uygulanmaz, sadece günlük pencere bölüşümü geçerli olur (varsayılan
    count=1, yani dilim sadece pending[0]). 9 bekleyen -> ~2,67 saat."""
    pending = [_geri_doldurma_projesi(tmp_path)] + ["b"] * 8

    ready_2h = [_project_with_upload(tmp_path, "p1", hours_ago=2)]
    assert ap._auto_pace_count(pending=pending, ready=ready_2h) == 0  # 2h < 2.67h

    ready_3h = [_project_with_upload(tmp_path, "p2", hours_ago=3)]
    assert ap._auto_pace_count(pending=pending, ready=ready_3h) == 1  # 3h > 2.67h

    # Aynı 3 saatte, sıradaki proje YENİ bir yayın olsaydı taban onu bloklardı.
    assert ap._auto_pace_count(pending=["yeni"] * 9, ready=ready_3h) == 0


def test_more_pending_backfill_projects_shortens_required_gap(tmp_path):
    """Geri doldurma senaryosunda (taban devre dışı) eski davranış korunuyor:
    aynı "3 saat önce yüklendi" durumunda 2 bekleyen varsa (aralık 12h) erken,
    9 bekleyen varsa (aralık ~2,67h) sırası gelmiş olmalı."""
    backfill = _geri_doldurma_projesi(tmp_path)
    ready = [_project_with_upload(tmp_path, "p1", hours_ago=3)]
    assert ap._auto_pace_count(pending=[backfill, "b"], ready=ready) == 0
    assert ap._auto_pace_count(pending=[backfill] + ["b"] * 8, ready=ready) == 1


def test_uses_most_recent_upload_across_multiple_platforms(tmp_path):
    d = tmp_path / "p1"
    d.mkdir()
    old_ts = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() - 25 * 3600))
    recent_ts = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() - 1 * 3600))
    (d / "state.json").write_text(json.dumps({
        "youtube_uploaded_at": old_ts,
        "tiktok_uploaded_at": recent_ts,  # bu daha yeni, referans bu olmalı
    }))

    # Geri doldurma senaryosu bilerek seçildi: 52 saatlik taban devredeyken hem
    # 25 saat hem 1 saat "erken" çıkardı ve test hangi damganın referans
    # alındığını AYIRT EDEMEZDİ. Taban muaf + tek bekleyen -> aralık 24 saat:
    # eski damga (25h) sırası gelmiş, yeni damga (1h) erken demek.
    pending = [_geri_doldurma_projesi(tmp_path)]
    assert ap._auto_pace_count(pending=pending, ready=[str(d)]) == 0


def test_batch_icindeki_yeni_yayin_tabani_atlatmiyor(tmp_path):
    """KIRILGANLIK DÜZELTMESİ (2026-09-11): ölçüt `pending[0]` DEĞİL, bu koşuda
    gerçekten işlenecek dilim (`pending[:count]`, main()'deki batch).

    Senaryo bugünkü gerçek kuyruk: sırada 3 geri doldurma projesi var (üçünün
    de YouTube videosu var, eksik olan Instagram) ve arkalarına YENİ bir şarkı
    giriyor. `count > 1` olduğu anda eski ölçüt sadece ilk sıradaki geri
    doldurmaya bakıp muafiyet veriyor, arkadaki yeni şarkı da o muafiyete
    binerek 52 saatlik tabanı SESSİZCE atlıyordu."""
    pending = [
        _geri_doldurma_projesi(tmp_path, "b1"),
        _geri_doldurma_projesi(tmp_path, "b2"),
        _geri_doldurma_projesi(tmp_path, "b3"),
        "yeni",  # var olmayan yol -> state {} -> YENİ yayın
    ]
    # 4 bekleyen -> günlük pencere payı 24/4 = 6 saat. Son yükleme 7 saat önce:
    # pencere kuralı için sıra GELMİŞ, 52 saatlik taban için ÇOK erken.
    ready = [_project_with_upload(tmp_path, "p1", hours_ago=7)]

    # Eski ölçütün neden yanıldığını testin içinde sabitle: pending[0] bir geri
    # doldurma, yani "sadece ilkine bak" kuralı tabanı her hâlükârda atlardı.
    assert "youtube_video_id" in json.loads(
        (tmp_path / "b1" / "state.json").read_text()
    )

    # Yalnızca geri doldurmalar işlenecekse muafiyet DEVAM ediyor (Instagram
    # geri doldurması yavaşlamamalı — bu düzeltmenin bozmaması gereken davranış).
    assert ap._auto_pace_count(pending=pending, ready=ready, count=1) == 1
    assert ap._auto_pace_count(pending=pending, ready=ready, count=3) == 3

    # Batch YENİ şarkıya UZANDIĞI anda taban geri geliyor -> bu koşuda 0.
    assert ap._auto_pace_count(pending=pending, ready=ready, count=4) == 0

    # 53 saat geçtiğinde aynı batch serbest kalıyor (taban gerçekten aşılmış).
    ready_53h = [_project_with_upload(tmp_path, "p2", hours_ago=53)]
    assert ap._auto_pace_count(pending=pending, ready=ready_53h, count=4) == 4


def test_yeni_yayinin_batch_icindeki_sirasi_onemsiz(tmp_path):
    """`pending` sıralaması değişirse de taban atlanmamalı: ölçüt `any()`,
    yeni yayın dilimin neresinde olursa olsun tabanı uyguluyor."""
    yeni = str(tmp_path / "yok")  # state {} -> yeni yayın
    b1 = _geri_doldurma_projesi(tmp_path, "s1")
    b2 = _geri_doldurma_projesi(tmp_path, "s2")
    ready = [_project_with_upload(tmp_path, "p1", hours_ago=7)]

    for pending in ([yeni, b1, b2], [b1, yeni, b2], [b1, b2, yeni]):
        assert ap._auto_pace_count(pending=pending, ready=ready, count=3) == 0


def test_varsayilan_count_bugunku_davranisi_koruyor(tmp_path):
    """`count` verilmezse 1 varsayılıyor: main() bugün tam olarak böyle
    çağırıyor, yani düzeltme mevcut üretim davranışını DEĞİŞTİRMİYOR."""
    pending = [_geri_doldurma_projesi(tmp_path, "g1"), "yeni"]
    ready = [_project_with_upload(tmp_path, "p1", hours_ago=13)]  # 24/2 = 12h

    assert ap._auto_pace_count(pending=pending, ready=ready) == 1
    assert ap._auto_pace_count(pending=pending, ready=ready, count=1) == 1
    # Aynı anda ikisi birden işlenecek olsaydı taban devreye girerdi.
    assert ap._auto_pace_count(pending=pending, ready=ready, count=2) == 0


def test_sifir_count_cokmeden_sifir_donuyor(tmp_path):
    """Savunma: count<=0 gelirse dilim boş kalır, `any([])` False döner ve
    taban sessizce kaybolurdu. `or pending[:1]` bunu kapatıyor; dönüş zaten 0
    ama yeni-yayın kararı yine de doğru hesaplanmalı."""
    ready = [_project_with_upload(tmp_path, "p1", hours_ago=7)]
    assert ap._auto_pace_count(pending=["yeni"], ready=ready, count=0) == 0
