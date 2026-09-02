"""projects/ altındaki tüm şarkıların YouTube istatistiklerini (görüntülenme,
beğeni, yorum) tazeleyip özet bir tablo basar — haftalık takip için. Ayrıca
Instagram token'ının süresi yaklaşıyorsa uyarır (bkz. _check_instagram_token_expiry).

Kullanım:
    python weekly_report.py
    python weekly_report.py --base projects

Sadece youtube_video_id'si state.json'da olan projeler dahil edilir (henüz
YouTube'a yüklenmemiş projeler atlanır). Her proje için upload/youtube_stats.py
ile aynı get_stats() çağrılır, state.json güncellenir.
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "upload"))

from youtube_stats import get_stats

INSTAGRAM_TOKEN_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "upload", "instagram_token.json"
)
INSTAGRAM_WARN_DAYS = 10  # bu kadar gün kala uyar (60 günlük token için makul bir tampon)


def _check_instagram_token_expiry() -> None:
    """TikTok'un aksine Instagram token'ı hiçbir yerden otomatik yenilenmiyor
    (upload/instagram_auth.py::refresh_access_token() tanımlı ama hiç çağrılmıyor) —
    ~60 günde bir sessizce süresi doluyor. Otomatik yenileme yerine (Meta'nın refresh
    endpoint'inin canlı davranışı bu ortamdan doğrulanamadığı için) sadece UYARI
    basıyoruz — kullanıcı gerektiğinde elle `python upload/instagram_auth.py
    --print-url` ile yeniden yetkilendirir."""
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
        with open(state_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def main():
    parser = argparse.ArgumentParser(
        description="Tüm projelerin YouTube istatistiklerini tazeleyip özet tablo basar."
    )
    parser.add_argument("--base", default="projects", help="Proje klasörlerinin kök dizini")
    args = parser.parse_args()

    _check_instagram_token_expiry()

    if not os.path.isdir(args.base):
        print(f"{args.base} bulunamadı.")
        return

    rows = []
    for name in sorted(os.listdir(args.base)):
        project_dir = os.path.join(args.base, name)
        if not os.path.isdir(project_dir):
            continue
        state = _load_state(project_dir)
        if not state.get("youtube_video_id"):
            continue
        try:
            state = get_stats(project_dir)
        except Exception as e:
            print(f"  {name}: HATA ({e})")
            continue
        rows.append((
            name,
            state.get("youtube_views", 0),
            state.get("youtube_likes", 0),
            state.get("youtube_comments", 0),
            state.get("youtube_privacy", "?"),
        ))

    if not rows:
        print("Henüz YouTube'a yüklenmiş proje yok.")
        return

    rows.sort(key=lambda r: r[1], reverse=True)
    name_w = max(len(r[0]) for r in rows) + 2
    print(f"{'Şarkı'.ljust(name_w)}{'İzlenme':>10}{'Beğeni':>10}{'Yorum':>8}  Görünürlük")
    print("-" * (name_w + 36))
    total_views = 0
    for name, views, likes, comments, privacy in rows:
        print(f"{name.ljust(name_w)}{views:>10}{likes:>10}{comments:>8}  {privacy}")
        total_views += views
    print("-" * (name_w + 36))
    print(f"{'Toplam'.ljust(name_w)}{total_views:>10}")


if __name__ == "__main__":
    main()
