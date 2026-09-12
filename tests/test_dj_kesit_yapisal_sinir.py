# -*- coding: utf-8 -*-
"""İkinci dalga kesit hattının ÜÇ "bağlantı" bulgusunun kalıcı bekçisi
(2026-09-11 bağlantı denetimi, B3/B9/B10).

Üçü de fonksiyon seviyesinde bozuk DEĞİLDİ — hepsi bu deponun en pahalı hata
sınıfı olan "bağlantı seviyesindeki sessiz arıza"ydı (bkz. CLAUDE.md):

B3 — ÖLÜ SABİT. `dj_clips.SET_BASINA_YAYIN = 1` hiçbir yerden OKUNMUYORDU
     (AST taramasıyla doğrulandı) ama hem modül notu hem kendi yorumu onu bir
     MEKANİZMA gibi sunuyordu: "ileride '2 yapalım' denirse kararın maliyeti
     tek yerden görülebilsin". Gerçekte 2 yazan biri HİÇBİR ŞEYİN
     değişmediğini görürdü — sınırı uygulayan şey `kesit_sec()` tek eleman
     döndürmesi ve `yayina_uygun_mu`'nun `youtube_clip_video_id` kapısı.
     Sabit KALDIRILDI; buradaki testler sınırın YAPISAL olduğunu çiviliyor ve
     sabitin geri gelmesini engelliyor.

B9 — GÖRELİ KÖK. `supur(base="dj_sets")` ve `dj_famous_process --base`
     varsayılanı göreliydi: yanlış cwd'de `os.path.isdir` False döner, liste
     boş çıkar, ikinci dalga hiç çalışmaz. `uyumluluk.KOKLER`,
     `dj_tarama_kontrol.BASELER` ve `youtube_analytics`'te aynı gün düzeltilen
     hatanın aynısı.

B10 — `finally` DIŞINDA SÜPÜRGE. `_kesit_yayini` döngüden sonra, `try`ın
     içindeydi: `process_set()` yakalanmamış bir istisna atarsa süpürge o
     koşuda hiç çalışmıyordu ve kesit yayını küresel olarak haftada bir olduğu
     için tek bir istisna ikinci dalgayı bir HAFTA geciktiriyordu.
"""

import ast
import io
import json
import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import dj_clips


def _set_kur(kok, ad="Test Set", state=None, kesitler=("clip_01.mp4",)):
    d = os.path.join(kok, ad)
    os.makedirs(os.path.join(d, "output"))
    with io.open(os.path.join(d, "meta.json"), "w", encoding="utf-8") as f:
        f.write(json.dumps({"title": ad, "theme": "dj"}))
    if state is not None:
        with io.open(os.path.join(d, "state.json"), "w", encoding="utf-8") as f:
            f.write(json.dumps(state, ensure_ascii=False))
    for n in kesitler:
        with open(os.path.join(d, "output", n), "wb") as f:
            f.write(b"x")
    return d


def _hazir_state(gecen_sn, kesitler=("clip_01.mp4",)):
    """Kesit yayınına HAZIR bir set state'i."""
    return {
        "youtube_shorts_video_id": "s1",
        "youtube_shorts_uploaded_at": time.strftime(
            "%Y-%m-%dT%H:%M:%S", time.localtime(time.time() - gecen_sn)),
        "dj_tarama_temiz": True,
        "dj_clips": [{"dosya": n, "bas": 100.0 * i, "son": 100.0 * i + 45,
                      "enerji": i}
                     for i, n in enumerate(kesitler, 1)],
    }


# --- B3: sabit gitti, kural YAPISAL ---------------------------------------


def test_set_basina_yayin_sabiti_geri_gelmedi():
    """Sabit geri eklenirse yine hiçbir şey yapmayacak — vaat eden bir isim,
    olmayan bir mekanizma. 2'ye çıkarmak state anahtarını (tekil
    `youtube_clip_video_id`) listeye çevirmeyi gerektirir."""
    assert not hasattr(dj_clips, "SET_BASINA_YAYIN")


def _modul_sabitleri(yol):
    agac = ast.parse(io.open(yol, encoding="utf-8").read())
    for d in agac.body:
        if isinstance(d, ast.Assign):
            for h in d.targets:
                if isinstance(h, ast.Name) and h.id.isupper():
                    yield h.id


def test_dj_clips_sabitlerinin_hepsi_gercekten_OKUNUYOR():
    """Genel bekçi: B3 tek bir sabitin hikâyesi değil, bir hata SINIFI.

    `dj_clips.py`'nin modül düzeyindeki her BÜYÜK HARFLİ sabiti en az bir
    yerden OKUNMALI (atandığı satır sayılmaz). Okunmayan bir sabit, yanındaki
    yorumla birlikte yapmadığı bir şeyi vaat eder.
    """
    kaynaklar = []
    for kok in (REPO, os.path.join(REPO, "upload"), os.path.join(REPO, "tests")):
        for ad in sorted(os.listdir(kok)):
            if ad.endswith(".py"):
                kaynaklar.append(os.path.join(kok, ad))

    okunanlar = set()
    for yol in kaynaklar:
        try:
            agac = ast.parse(io.open(yol, encoding="utf-8").read())
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        for d in ast.walk(agac):
            if isinstance(d, ast.Name) and isinstance(d.ctx, ast.Load):
                okunanlar.add(d.id)
            elif isinstance(d, ast.Attribute) and isinstance(d.ctx, ast.Load):
                okunanlar.add(d.attr)

    olu = [s for s in _modul_sabitleri(os.path.join(REPO, "dj_clips.py"))
           if s not in okunanlar]
    assert olu == [], "hicbir yerden okunmayan sabit(ler): %s" % olu


def test_yayin_sinirini_uygulayan_sey_state_anahtari(tmp_path):
    """Set başına tek yayın: `youtube_clip_video_id` yazıldıktan sonra kapı
    kapanıyor — diskte HÂLÂ yayınlanabilir ikinci bir kesit dosyası olsa
    bile."""
    kesitler = ("clip_01.mp4", "clip_02.mp4")
    st = _hazir_state(dj_clips.KESIT_MIN_ARA_SN + 3600, kesitler=kesitler)
    set_dir = _set_kur(str(tmp_path), state=st, kesitler=kesitler)

    kesit, sebep = dj_clips.yayina_uygun_mu(set_dir)
    assert kesit is not None, sebep          # ilk kesit yayına uygun

    st["youtube_clip_video_id"] = "abc"
    st["youtube_clip_dosya"] = "clip_01.mp4"
    with io.open(os.path.join(set_dir, "state.json"), "w", encoding="utf-8") as f:
        f.write(json.dumps(st, ensure_ascii=False))

    kesit, sebep = dj_clips.yayina_uygun_mu(set_dir)
    assert kesit is None and "zaten" in sebep


def test_kesit_sec_TEK_kesit_donduruyor(tmp_path):
    """Sınırın ikinci yarısı: seçici bir LİSTE değil, tek bir kayıt döndürüyor
    (en yüksek enerjili = `enerji` en küçük)."""
    kesitler = ("clip_01.mp4", "clip_02.mp4", "clip_03.mp4")
    set_dir = _set_kur(str(tmp_path),
                       state=_hazir_state(dj_clips.KESIT_MIN_ARA_SN + 3600,
                                          kesitler=kesitler),
                       kesitler=kesitler)
    kesit = dj_clips.kesit_sec(set_dir)
    assert isinstance(kesit, dict)
    assert kesit["dosya"] == "clip_01.mp4"


# --- B9: göreli kök, yanlış cwd -------------------------------------------


def test_goreli_base_yanlis_cwdde_de_calisiyor(tmp_path, monkeypatch):
    """`supur(base="dj_sets")` göreli; cwd repo kökü DEĞİLKEN de setleri
    bulmalı. Eskiden boş liste dönüyordu ve ikinci dalga sessizce duruyordu."""
    kok = tmp_path / "dj_sets"
    kok.mkdir()
    _set_kur(str(kok), ad="Just Relax", state={})
    baska_yer = tmp_path / "baska"
    baska_yer.mkdir()

    monkeypatch.setattr(dj_clips, "_KOK", str(tmp_path))
    monkeypatch.chdir(str(baska_yer))

    bulunan = dj_clips._set_klasorleri("dj_sets")
    assert [os.path.basename(p) for p in bulunan] == ["Just Relax"]
    assert all(os.path.isabs(p) for p in bulunan)


def test_mutlak_base_oldugu_gibi_kullaniliyor(tmp_path, monkeypatch):
    """Mutlak yol verilirse `_KOK`'e YAPIŞTIRILMAMALI (mevcut çağrıların ve
    testlerin tamamı mutlak yol veriyor)."""
    _set_kur(str(tmp_path), ad="Set A", state={})
    monkeypatch.setattr(dj_clips, "_KOK", os.path.join(str(tmp_path), "yanlis"))
    bulunan = dj_clips._set_klasorleri(str(tmp_path))
    assert [os.path.basename(p) for p in bulunan] == ["Set A"]


def test_nokta_ve_alt_cizgi_onekleri_eleniyor(tmp_path):
    """Kanonik filtre (`uyumluluk.proje_klasorleri`): `_arda` gibi yardımcı
    klasörler ve `.tmp-<ad>` gibi YARIM üretim klasörleri set değildir."""
    for ad in ("_arda", ".tmp-Gece Seansi"):
        os.makedirs(os.path.join(str(tmp_path), ad))
    _set_kur(str(tmp_path), ad="Gercek Set", state={})
    assert [os.path.basename(p)
            for p in dj_clips._set_klasorleri(str(tmp_path))] == ["Gercek Set"]


# --- B10: süpürge `finally` bloğunda --------------------------------------


def _main_try(yol="dj_famous_process.py"):
    agac = ast.parse(io.open(os.path.join(REPO, yol), encoding="utf-8").read())
    main = next(d for d in agac.body
                if isinstance(d, ast.FunctionDef) and d.name == "main")
    return next(d for d in ast.walk(main) if isinstance(d, ast.Try))


def _cagri_var_mi(dugumler, ad):
    for d in dugumler:
        for alt in ast.walk(d):
            if isinstance(alt, ast.Call) and isinstance(alt.func, ast.Name) \
                    and alt.func.id == ad:
                return True
    return False


def test_kesit_yayini_finally_blogunda_cagriliyor():
    """`process_set()` patlarsa bile ikinci dalga o koşuda çalışmalı —
    `auto_process.main()` tüm arka plan süpürgelerini aynı şekilde
    `finally`den koşuyor."""
    t = _main_try()
    assert _cagri_var_mi(t.finalbody, "_kesit_yayini"), \
        "_kesit_yayini `finally` blogunda cagrilmiyor"
    assert not _cagri_var_mi(t.body, "_kesit_yayini"), \
        "`try` govdesinde IKINCI bir _kesit_yayini cagrisi var (cift yayin riski)"


def test_kilit_finallyde_hala_birakiliyor():
    """Süpürgenin hatası kilidin bırakılmasını ENGELLEMEMELİ: bırakılmayan bir
    kilit sonraki koşuları LOCK_STALE_SECONDS (4 saat) boyunca bloklar."""
    t = _main_try()
    assert _cagri_var_mi(t.finalbody, "_release_lock")
