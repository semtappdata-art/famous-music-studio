"""projects/ altındaki tüm şarkıların YouTube istatistiklerini (görüntülenme,
beğeni, yorum) tazeleyip özet bir tablo basar — haftalık takip için.

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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "upload"))

from youtube_stats import get_stats


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
