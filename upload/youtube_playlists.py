"""Şarkıları tema/tarza göre (config.THEMES) YouTube playlist'lerine otomatik ekler —
kanal içinde "Rap/Hip-Hop", "Pop", "Arabesk" gibi ayrı tarz alanları oluşturur.

Kullanım:
    python upload/youtube_playlists.py --sync-all
        Zaten YouTube'a yüklenmiş (state.json'da youtube_video_id olan) TÜM projeleri
        tarar, her birini kendi temasının playlist'ine ekler (henüz eklenmemişse).
        Playlist yoksa otomatik oluşturur. Geriye dönük çalışır — mevcut kataloğu
        gruplamak için bunu bir kere çalıştırman yeterli.

    python upload/youtube_playlists.py --project "projects/sarki-adi"
        Tek bir projeyi kendi temasının playlist'ine ekler.

auto_process.py, her yeni uzun-format YouTube upload'ından sonra bunu otomatik çağırır —
elle çalıştırman sadece geçmiş kataloğu bir kerelik gruplamak (--sync-all) için gerekiyor.

Playlist ID'leri upload/playlist_ids.json'da (theme_key -> playlist_id) önbelleğe alınır —
secret DEĞİL (sadece kanalın kendi playlist ID'leri), bu yüzden .gitignore'da değil, repoya
commit edilir — projects/*/state.json gibi. Bu, aynı playlist'in yanlışlıkla birden fazla
kez oluşturulmasını önler (hem yerel hem bulut oturumu aynı ID'leri görsün diye).
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from youtube_auth import get_authenticated_service

UPLOAD_DIR = os.path.dirname(os.path.abspath(__file__))
PLAYLIST_IDS_PATH = os.path.join(UPLOAD_DIR, "playlist_ids.json")


def _load_playlist_ids() -> dict:
    if os.path.isfile(PLAYLIST_IDS_PATH):
        with open(PLAYLIST_IDS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_playlist_ids(ids: dict) -> None:
    with open(PLAYLIST_IDS_PATH, "w", encoding="utf-8") as f:
        json.dump(ids, f, ensure_ascii=False, indent=2)


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
    state_path = os.path.join(project_dir, "state.json")
    state = _load_state(project_dir)
    state.update(fields)
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def get_theme_key(meta: dict) -> str:
    theme_key = meta.get("theme", config.DEFAULT_THEME)
    return theme_key if theme_key in config.THEMES else config.DEFAULT_THEME


def get_or_create_playlist(youtube, theme_key: str) -> str:
    """theme_key'e karşılık gelen playlist'in ID'sini döner — yoksa oluşturur.
    Önbellekten (playlist_ids.json) okur/yazar, her seferinde YouTube'da arama yapmaz."""
    ids = _load_playlist_ids()
    if theme_key in ids:
        return ids[theme_key]

    theme = config.THEMES.get(theme_key, config.THEMES[config.DEFAULT_THEME])
    title = f"{theme['label']} Şarkılar — {config.STATIC_LABEL_TEXT}"
    body = {
        "snippet": {
            "title": title,
            "description": (
                f"{config.STATIC_LABEL_TEXT} kanalının {theme['label'].lower()} "
                f"tarzındaki AI-üretimi şarkıları."
            ),
        },
        "status": {"privacyStatus": "public"},
    }
    response = youtube.playlists().insert(part="snippet,status", body=body).execute()
    playlist_id = response["id"]
    print(f"  playlist oluşturuldu: {title!r} ({playlist_id})")

    ids[theme_key] = playlist_id
    _save_playlist_ids(ids)
    return playlist_id


def ensure_in_playlist(youtube, project_dir: str, video_id: str, theme_key: str) -> None:
    """video_id'yi theme_key'in playlist'ine ekler — state.json'da youtube_playlist_id
    zaten varsa (daha önce eklenmişse) atlar, aynı videoyu tekrar eklemez."""
    state = _load_state(project_dir)
    if state.get("youtube_playlist_id"):
        return

    playlist_id = get_or_create_playlist(youtube, theme_key)
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
    _update_state(project_dir, {"youtube_playlist_id": playlist_id})


def sync_project(youtube, project_dir: str) -> None:
    state = _load_state(project_dir)
    video_id = state.get("youtube_video_id")
    if not video_id:
        print(f"  {os.path.basename(project_dir)}: henüz YouTube'a yüklenmemiş, atlanıyor")
        return
    meta = _load_meta(project_dir)
    theme_key = get_theme_key(meta)
    ensure_in_playlist(youtube, project_dir, video_id, theme_key)


def sync_all(base: str = "projects") -> None:
    youtube = get_authenticated_service()
    if not os.path.isdir(base):
        print(f"{base} bulunamadı.")
        return
    for name in sorted(os.listdir(base)):
        project_dir = os.path.join(base, name)
        if not os.path.isdir(project_dir):
            continue
        print(f"=== {name} ===")
        sync_project(youtube, project_dir)


def main():
    parser = argparse.ArgumentParser(
        description="Şarkıları tema/tarza göre YouTube playlist'lerine ekler."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--sync-all", action="store_true", help="Tüm yüklü projeleri senkronla")
    group.add_argument("--project", help="Tek bir proje klasörü (örn. projects/sarki-adi)")
    parser.add_argument("--base", default="projects", help="Proje klasörlerinin kök dizini")
    args = parser.parse_args()

    if args.sync_all:
        sync_all(args.base)
    else:
        youtube = get_authenticated_service()
        sync_project(youtube, args.project)


if __name__ == "__main__":
    main()
