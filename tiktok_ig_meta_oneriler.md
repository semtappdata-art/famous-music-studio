# TikTok Studio + Instagram Edits — Meta Yükleme Önerileri
# (CLAUDE.md §6, §7, §13 — yükleme prensiplerine uygun)

## 1. TikTok Studio (Zamanlayıcı ile Otomatik — Elle sadece onay/istisna)
- Zaman: Taslak + ZAMANLAYICI ile otomatik yayın (tiktok_publish_plan.py CLI + native schedule); elle yayın sadece onay/istisna
- Meta: Başlık ≤100 char, açıklama, AI hashtag YASAK (§13)
- Kapak: cover_vertical.png (9:16), başlık %14 punkt, beyaz + 3px siyah outline
- Video: render.py çıktısı, dikey hook (1sn chorus), marquee/progress bar YOK
- Otomasyon bağ: watch_projects -> zamanlayıcı tetikleyici -> taslak doğrulama (uyumluluk.kontrol) -> native schedule -> finally (yeni görev YOK, elle adım sadece onay/istisna)

## 2. Instagram Reels (Kendi Kuyruğu)
- Zaman: Golden hour 18-00 / 12-14 (TR), 23sa konteyner ömrü
- Meta: Başlık + açıklama + konum, cover_vertical (9:16)
- Kontrol: Bayat = sil + manuel yeniden yükle
- Otomasyon bağ: auto_process + ek_platform_backfill.py

## 3. Meta Genel (Tüm Platformlar)
- Kaynak: projects/<şarkı>/meta.json -> theme (akustik/hiphop)
- Kapak: generate_cover.py (16:9 + 9:16), art.jpg dominant renk → başlık rengi
- Video: ffmpeg_utils + render.py (bölüm bazlı görsel)
- Doğrulama: validate_project.py -> uyumluluk.kontrol() (7 nokta, fail-closed)
- Yazım: state_io.atomic_write() (.tmp + flush + fsync + os.replace)
- Log: gizli_maskele.maskele() her yazımda
- Bildirim: notify.is_configured() ZORUNLU önce send sonra
- Commit: git add ... && git commit -m 'rule: <kısa açıklama>' (tek commit)

## 4. Öneri (Gerçekçi, Bu Yıl — §11)
- Ko-fi + DistroKid + Şablon README (bu ay)
- DistroKid → Spotify/Apple (50$/ay, 2-3 ay)
- Şablon satış: 1000$/ay (1 hafta doküman, 1-2 ay gelir)

## 5. Test / CI
- tests/test_kurallar.py -> 14 passed
- pytest -q -p no:cacheprovider --basetemp="..."
- ruff + mypy --strict + trufflehog
