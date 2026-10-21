"""Sosyal Medya Yayını - MCP Wrapper (PostWire).

Bu modül `auto_process._ek_platformlari_isle` ve `dj_famous_process`
içindeki platform yükleme mantığını PostWire MCP ile değiştirir.

Özellikler:
- Tek fonksiyon: `publish_to_platforms(project_dir, state, meta, platforms)`
- Native zamanlama (scheduled_publish_time) - Instagram/TikTok golden-hour kuyruğu GEREKSİZ
- Data API/Graph API kota KULLANMAZ
- MCP başarısız olursa mevcut upload modüllerine fallback
"""

from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_client import (
    mcp_manager,
    MCPProvider,
    MCPError,
    mcp_enabled,
    mcp_fallback_enabled,
    _log,
    load_project_state,
)
from mcp_postwire import (
    publish_to_platform as mcp_publish_to_platform,
    build_youtube_metadata,
    build_tiktok_metadata,
    build_instagram_metadata,
    build_facebook_metadata,
    build_telegram_metadata,
    build_bluesky_metadata,
)

# Fallback modüller
import youtube_upload
import tiktok_upload
import instagram_upload
import facebook_upload
import ek_platform_backfill


# Platform -> video dosyası eşlemesi
PLATFORM_VIDEO_MAP = {
    "youtube": "youtube_16x9.mp4",
    "youtube_shorts": "shorts_9x16.mp4",
    "tiktok": "shorts_9x16.mp4",
    "instagram": "shorts_9x16.mp4",
    "facebook": "shorts_9x16.mp4",
    "telegram": "shorts_9x16.mp4",
    "bluesky": "shorts_9x16.mp4",
}


def publish_to_platforms(project_dir: str, platforms: list[str] | None = None,
                         scheduled_at: str | None = None) -> dict[str, dict]:
    """Projeyi belirtilen platformlara yayınlar.
    
    Args:
        project_dir: Proje klasörü
        platforms: Platform listesi (None = config.EK_PLATFORMLAR + ana platformlar)
        scheduled_at: ISO8601 UTC zamanlanmış yayın (None = hemen)
        
    Returns:
        {platform: {"success": bool, "post_id": str, "status": str, "error": str}}
    """
    if platforms is None:
        platforms = ["youtube", "youtube_shorts"] + getattr(__import__("config"), "EK_PLATFORMLAR", [])

    state = load_project_state(project_dir)
    results = {}

    for platform in platforms:
        try:
            result = _publish_single_platform(project_dir, platform, state, scheduled_at)
            results[platform] = result
        except Exception as e:
            _log(f"Yayın hatası ({platform}): {e}")
            results[platform] = {
                "success": False,
                "post_id": "",
                "status": "error",
                "error": str(e)
            }

    return results


def _publish_single_platform(project_dir: str, platform: str, state: dict,
                              scheduled_at: str | None) -> dict:
    """Tek platforma yayın - MCP öncelikli, fallback Data/API."""
    video_file = PLATFORM_VIDEO_MAP.get(platform)
    if not video_file:
        return {"success": False, "post_id": "", "status": "error",
                "error": f"Bilinmeyen platform: {platform}"}

    video_path = os.path.join(project_dir, "output", video_file)
    if not os.path.isfile(video_path):
        return {"success": False, "post_id": "", "status": "error",
                "error": f"Video dosyası yok: {video_path}"}

    # 1. MCP dene
    provider = mcp_manager.get_social_provider()
    if provider is not None:
        try:
            result = mcp_publish_to_platform(platform, project_dir, video_path, scheduled_at)
            _log(f"MCP yayın başarılı: {platform} -> {result.get('post_id')}")
            return {
                "success": True,
                "post_id": result.get("post_id", ""),
                "status": result.get("status", "published"),
                "error": ""
            }
        except MCPError as e:
            _log(f"MCP yayın hatası ({platform}), fallback: {e}")
            mcp_manager.invalidate_health(MCPProvider.POSTWIRE)
        except Exception as e:
            _log(f"MCP beklenmedik hata ({platform}), fallback: {e}")
            mcp_manager.invalidate_health(MCPProvider.POSTWIRE)

    # 2. Fallback: Mevcut upload modülleri
    return _fallback_publish(project_dir, platform, state, video_path, scheduled_at)


def _fallback_publish(project_dir: str, platform: str, state: dict,
                       video_path: str, scheduled_at: str | None) -> dict:
    """Mevcut upload modülleriyle fallback."""
    try:
        if platform == "youtube":
            return _fallback_youtube(project_dir, state, video_path, scheduled_at, is_shorts=False)
        elif platform == "youtube_shorts":
            return _fallback_youtube(project_dir, state, video_path, scheduled_at, is_shorts=True)
        elif platform == "tiktok":
            return _fallback_tiktok(project_dir, state, video_path)
        elif platform == "instagram":
            return _fallback_instagram(project_dir, state, video_path)
        elif platform == "facebook":
            return _fallback_facebook(project_dir, state, video_path)
        elif platform in ("telegram", "bluesky"):
            return _fallback_ek_platform(project_dir, state, platform, video_path)
        else:
            return {"success": False, "post_id": "", "status": "error",
                    "error": f"Fallback yok: {platform}"}
    except Exception as e:
        return {"success": False, "post_id": "", "status": "error", "error": str(e)}


def _fallback_youtube(project_dir: str, state: dict, video_path: str,
                       scheduled_at: str | None, is_shorts: bool) -> dict:
    """YouTube fallback - youtube_upload.py kullanır."""

    privacy = state.get("youtube_privacy", "private")
    if scheduled_at and privacy == "public":
        privacy = "private"  # scheduled için private + publishAt

    if is_shorts:
        video_id = youtube_upload.upload_shorts(project_dir, video_path, privacy, scheduled_at)
        field = "youtube_shorts_video_id"
        publish_field = "youtube_shorts_publish_at"
    else:
        video_id = youtube_upload.upload_video(project_dir, video_path, privacy, scheduled_at)
        field = "youtube_video_id"
        publish_field = "youtube_publish_at"

    if video_id:
        from mcp_client import update_project_state
        update_data = {field: video_id}
        if scheduled_at:
            update_data[publish_field] = scheduled_at
        update_project_state(project_dir, update_data)
        return {"success": True, "post_id": video_id, "status": "published", "error": ""}

    return {"success": False, "post_id": "", "status": "error", "error": "YouTube upload failed"}


def _fallback_tiktok(project_dir: str, state: dict, video_path: str) -> dict:
    """TikTok fallback - tiktok_upload.py (taslak/gelen kutusu)."""

    # tiktok_upload taslak yükler, post_id = publish_id
    publish_id = tiktok_upload.upload_video(project_dir, video_path)
    if publish_id:
        from mcp_client import update_project_state
        update_project_state(project_dir, {
            "tiktok_publish_id": publish_id,
            "tiktok_hatirlatma": "kit",  # yeni kit sistemi
        })
        return {"success": True, "post_id": publish_id, "status": "draft", "error": ""}

    return {"success": False, "post_id": "", "status": "error", "error": "TikTok upload failed"}


def _fallback_instagram(project_dir: str, state: dict, video_path: str) -> dict:
    """Instagram fallback - instagram_upload.py (konteyner + golden-hour)."""

    creation_id = instagram_upload.upload_reels(project_dir, video_path)
    if creation_id:
        from mcp_client import update_project_state
        update_project_state(project_dir, {
            "instagram_creation_id": creation_id,
            "instagram_container_created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        })
        return {"success": True, "post_id": creation_id, "status": "scheduled", "error": ""}

    return {"success": False, "post_id": "", "status": "error", "error": "Instagram upload failed"}


def _fallback_facebook(project_dir: str, state: dict, video_path: str) -> dict:
    """Facebook fallback - facebook_upload.py (native scheduling)."""

    video_id = facebook_upload.upload_reels(project_dir, video_path)
    if video_id:
        from mcp_client import update_project_state
        update_project_state(project_dir, {"facebook_video_id": video_id})
        return {"success": True, "post_id": video_id, "status": "published", "error": ""}

    return {"success": False, "post_id": "", "status": "error", "error": "Facebook upload failed"}


def _fallback_ek_platform(project_dir: str, state: dict, platform: str, video_path: str) -> dict:
    """Telegram/Bluesky fallback - ek_platform_backfill.py."""

    # ek_platform_backfill tek proje için yayınlama fonksiyonu sağlamıyor,
    # doğrudan modül fonksiyonlarını çağırmak gerekir.
    # Basitlik için: bu platformlar MCP olmadan çalışmaz (config'da kapalıysa).
    return {"success": False, "post_id": "", "status": "skipped",
            "error": f"{platform} MCP olmadan desteklenmiyor (ek_platform_backfill kullanın)"}


# ---- Auto_process.py entegrasyonu ----

def ek_platformlari_isle_mcp(project_dir: str, state: dict, meta: dict) -> None:
    """`auto_process._ek_platformlari_isle` yerinde MCP versiyonu.
    
    Bu fonksiyon:
    1. YouTube (uzun + Shorts) yükleme SONRA çağrılır
    2. config.EK_PLATFORMLAR listesini işler
    3. Golden-hour penceresi kontrolü YAPMAZ (PostWire native scheduling yapar)
    4. Günlük tavan kontrolü YAPMAZ (PostWire tarafında)
    """
    from config import EK_PLATFORMLAR

    platforms = ["youtube", "youtube_shorts"] + EK_PLATFORMLAR

    # YouTube zaten yüklendiği varsayılıyor (process_project içinde önce yapılır)
    # Burada yalnız EK platformlar
    ek_platforms = [p for p in platforms if p not in ("youtube", "youtube_shorts")]

    if not ek_platforms:
        return

    _log(f"MCP ek platformlar: {ek_platforms}")

    results = publish_to_platforms(project_dir, ek_platforms)

    for platform, result in results.items():
        if result["success"]:
            _log(f"  ✓ {platform}: {result['post_id']} ({result['status']})")
        else:
            _log(f"  ✗ {platform}: {result['error']}")


def dj_famous_yayinla_mcp(project_dir: str, state: dict, meta: dict,
                           platforms: list[str] | None = None) -> dict:
    """`dj_famous_process.process_set` yerinde MCP versiyonu.
    
    DJ setleri için: YouTube (uzun) + Shorts + config.EK_PLATFORMLAR
    Content ID tarama sonrası (dj_tarama_kontrol) çağrılır.
    """
    if platforms is None:
        from config import EK_PLATFORMLAR
        platforms = ["youtube", "youtube_shorts"] + EK_PLATFORMLAR

    _log(f"MCP DJ Famous yayın: {platforms}")

    return publish_to_platforms(project_dir, platforms)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Sosyal medya yayını (MCP wrapper)")
    parser.add_argument("--project", required=True)
    parser.add_argument("--platforms", nargs="+", default=["youtube", "tiktok", "instagram"])
    parser.add_argument("--scheduled", help="ISO8601 UTC")
    args = parser.parse_args()

    results = publish_to_platforms(args.project, args.platforms, args.scheduled)
    for platform, result in results.items():
        status = "✓" if result["success"] else "✗"
        print(f"  {status} {platform}: {result.get('post_id', result.get('error', ''))}")