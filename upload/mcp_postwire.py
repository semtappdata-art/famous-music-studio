"""PostWire MCP - Çok Platformlu Yayın Sağlayıcısı.

Bu modül `mcp__postwire` üzerinden tüm platformlara (YouTube, TikTok, Instagram,
Facebook, Telegram, Bluesky) yayın yapar.

Özellikler:
- Native zamanlama desteği (scheduled_publish_time) - Instagram/TikTok için
  kendi golden-hour kuyruğumuzun (`instagram_upload.creation_id`) KARŞILIĞI
- Tek çağrıda çok platformlu yayın
- `mcp_client.SocialPublishProvider` arayüzünü uygular
- Kota/bağlantı izolasyonu - Data API/Graph API kotasını TÜKETMEZ
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_client import (
    SocialPublishProvider,
    MCPError,
    MCPUnavailableError,
    MCPQuotaExceededError,
    _log,
)


# Platform anahtarları - PostWire'ın beklediği değerler
PLATFORM_KEYS = {
    "youtube": "youtube",
    "youtube_shorts": "youtube_shorts",
    "tiktok": "tiktok",
    "instagram": "instagram_reels",
    "facebook": "facebook_reels",
    "telegram": "telegram",
    "bluesky": "bluesky",
}


class PostWireProvider(SocialPublishProvider):
    """PostWire MCP sunucusu üzerinden çok platformlu yayın."""

    def __init__(self):
        # mcp_servers.json'da postwire yoksa environment'tan al
        self._server_url = os.getenv("POSTWIRE_MCP_URL", "")
        self._token = os.getenv("POSTWIRE_TOKEN", "")

    def _call_mcp(self, tool: str, arguments: dict) -> Any:
        """MCP aracını çağırır."""
        if not getattr(self, "_server_url", ""):
            raise MCPUnavailableError("postwire", "yapilandirilmamis (env POSTWIRE_MCP_URL bos) -> fallback")
        try:
            import httpx

            headers = {
                "Content-Type": "application/json",
            }
            if self._token:
                headers["Authorization"] = f"Bearer {self._token}"

            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool,
                    "arguments": arguments
                }
            }

            timeout = 120.0  # video yükleme uzun sürebilir

            with httpx.Client(timeout=timeout) as client:
                response = client.post(self._server_url, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()

            if "error" in result:
                error = result["error"]
                msg = error.get("message", "Bilinmeyen")
                if "quota" in msg.lower() or "rate limit" in msg.lower():
                    raise MCPQuotaExceededError("postwire", msg)
                raise MCPError("postwire", f"MCP hata: {msg}")

            return result.get("result", {})

        except httpx.TimeoutException:
            raise MCPUnavailableError("postwire", "Zaman aşımı (video yükleme)")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise MCPQuotaExceededError("postwire", "Rate limit")
            raise MCPUnavailableError("postwire", f"HTTP {e.response.status_code}: {e}")
        except Exception as e:
            if isinstance(e, MCPError):
                raise
            raise MCPUnavailableError("postwire", f"Bağlantı hatası: {e}")

    def _normalize_platform(self, platform: str) -> str:
        """Platform adını PostWire anahtarına çevirir."""
        return PLATFORM_KEYS.get(platform.lower(), platform.lower())

    # ---- SocialPublishProvider Arayüzü ----

    def publish(self, platform: str, video_path: str, metadata: dict,
                scheduled_at: str | None = None) -> dict:
        """Video yayınlar.
        
        Args:
            platform: "youtube" | "youtube_shorts" | "tiktok" | "instagram" |
                      "facebook" | "telegram" | "bluesky"
            video_path: Video dosyası yolu (mutlak)
            metadata: {
                "title": str,
                "description": str,
                "tags": list[str],
                "privacy": "public" | "private" | "unlisted" | "scheduled",
                "thumbnail_path": str (opsiyonel),
                "location": str (opsiyonel),
            }
            scheduled_at: ISO8601 UTC (örn. "2026-09-15T12:00:00Z") - None ise hemen
            
        Returns:
            {"post_id": ..., "platform": ..., "status": "published"|"scheduled"|"draft"}
        """
        pw_platform = self._normalize_platform(platform)

        # Dosya varlığını kontrol et
        if not os.path.isfile(video_path):
            raise MCPError("postwire", f"Video dosyası bulunamadı: {video_path}")

        args = {
            "platform": pw_platform,
            "video_path": video_path,
            "title": metadata.get("title", ""),
            "description": metadata.get("description", ""),
            "tags": metadata.get("tags", []),
            "privacy": metadata.get("privacy", "public"),
        }

        if metadata.get("thumbnail_path"):
            args["thumbnail_path"] = metadata["thumbnail_path"]

        if scheduled_at:
            args["scheduled_publish_time"] = scheduled_at
            # privacy "scheduled" olmalı native zamanlama için
            if args["privacy"] == "public":
                args["privacy"] = "scheduled"

        result = self._call_mcp("publish_video", args)

        return {
            "post_id": result.get("post_id") or result.get("id", ""),
            "platform": platform,
            "status": result.get("status", "published"),
        }

    def get_scheduled_posts(self, platform: str) -> list[dict]:
        """Zamanlanmış/pending gönderileri listeler.
        
        Instagram/TikTok golden-hour kuyruğu yerine geçer.
        """
        pw_platform = self._normalize_platform(platform)
        result = self._call_mcp("get_scheduled_posts", {"platform": pw_platform})

        posts = []
        for item in result.get("posts", []):
            posts.append({
                "post_id": item.get("post_id") or item.get("id", ""),
                "platform": platform,
                "scheduled_at": item.get("scheduled_publish_time"),
                "status": item.get("status", "scheduled"),
                "title": item.get("title", ""),
            })
        return posts

    def health_check(self) -> bool:
        """PostWire bağlantı sağlığı."""
        try:
            self._call_mcp("health_check", {})
            return True
        except Exception:
            return False


# ---- Yardımcı: Platform özel metadata hazırlama ----

def build_youtube_metadata(project_dir: str, state: dict, meta: dict, is_shorts: bool) -> dict:
    """YouTube/Shorts için metadata hazırlar (youtube_upload.py ile uyumlu)."""
    from youtube_upload import build_snippet, build_shorts_snippet
    from social_text import resolve_language

    if is_shorts:
        snippet = build_shorts_snippet(project_dir, state, meta)
    else:
        snippet = build_snippet(project_dir, state, meta)

    return {
        "title": snippet.get("title", ""),
        "description": snippet.get("description", ""),
        "tags": snippet.get("tags", []),
        "privacy": state.get("youtube_privacy", "private"),  # scheduled için private
        "language": resolve_language(meta),
    }


def build_tiktok_metadata(project_dir: str, state: dict, meta: dict) -> dict:
    """TikTok için metadata hazırlar (tiktok_upload.py ile uyumlu)."""
    from social_text import build_caption, build_ai_disclosure_line
    from upload.tiktok_upload import _build_tags

    caption = build_caption(meta.get("title", ""), meta)
    ai_line = build_ai_disclosure_line(meta)
    tags = _build_tags(meta)

    full_caption = f"{caption}\n\n{ai_line}\n{' '.join(tags)}"

    return {
        "title": meta.get("title", "")[:100],  # TikTok başlık limiti
        "description": full_caption,
        "tags": tags,
        "privacy": "public",  # Taslak için "self_only" PostWire'da ayrı alan
    }


def build_instagram_metadata(project_dir: str, state: dict, meta: dict) -> dict:
    """Instagram Reels için metadata hazırlar (instagram_upload.py ile uyumlu)."""
    from social_text import build_caption, build_ai_disclosure_line, resolve_language

    caption = build_caption(meta.get("title", ""), meta)
    ai_line = build_ai_disclosure_line(meta)

    return {
        "title": meta.get("title", ""),
        "description": f"{caption}\n\n{ai_line}",
        "tags": [],  # Instagram hashtag'ler caption içinde
        "privacy": "public",
    }


def build_facebook_metadata(project_dir: str, state: dict, meta: dict) -> dict:
    """Facebook Reels için metadata."""
    from social_text import build_caption, build_ai_disclosure_line

    caption = build_caption(meta.get("title", ""), meta)
    ai_line = build_ai_disclosure_line(meta)

    return {
        "title": meta.get("title", ""),
        "description": f"{caption}\n\n{ai_line}",
        "tags": [],
        "privacy": "public",
    }


def build_telegram_metadata(project_dir: str, state: dict, meta: dict) -> dict:
    """Telegram için metadata (ek_platform_backfill.py ile uyumlu)."""
    from social_text import build_caption, resolve_language

    caption = build_caption(meta.get("title", ""), meta)

    return {
        "title": meta.get("title", ""),
        "description": caption,
        "tags": [],
        "privacy": "public",
    }


def build_bluesky_metadata(project_dir: str, state: dict, meta: dict) -> dict:
    """Bluesky için metadata (ek_platform_backfill.py ile uyumlu)."""
    from social_text import build_caption, resolve_language

    caption = build_caption(meta.get("title", ""), meta)

    return {
        "title": meta.get("title", ""),
        "description": caption,
        "tags": [],
        "privacy": "public",
    }


PLATFORM_METADATA_BUILDERS = {
    "youtube": build_youtube_metadata,
    "youtube_shorts": lambda p, s, m: build_youtube_metadata(p, s, m, is_shorts=True),
    "tiktok": build_tiktok_metadata,
    "instagram": build_instagram_metadata,
    "facebook": build_facebook_metadata,
    "telegram": build_telegram_metadata,
    "bluesky": build_bluesky_metadata,
}


def publish_to_platform(platform: str, project_dir: str, video_path: str,
                        scheduled_at: str | None = None) -> dict:
    """Kolaylık fonksiyonu: proje klasöründen metadata üretir ve yayınlar.
    
    Bu fonksiyon `auto_process._ek_platformlari_isle` ve `dj_famous_process`
    yerinde çağrılabilir.
    """
    from mcp_client import mcp_manager

    provider = mcp_manager.get_social_provider()
    if provider is None:
        raise MCPError("postwire", "PostWire MCP etkin değil")

    state = load_project_state(project_dir)
    meta_path = os.path.join(project_dir, "meta.json")
    meta = {}
    if os.path.isfile(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

    builder = PLATFORM_METADATA_BUILDERS.get(platform)
    if not builder:
        raise MCPError("postwire", f"Bilinmeyen platform: {platform}")

    metadata = builder(project_dir, state, meta)

    # Kapak görseli
    if platform in ("youtube", "youtube_shorts"):
        cover = os.path.join(project_dir, "output", "cover.png")
        if os.path.isfile(cover):
            metadata["thumbnail_path"] = cover

    return provider.publish(platform, video_path, metadata, scheduled_at)


# State yardımcıları (mcp_client'tan import edilirse circular import olmaz)
def load_project_state(project_dir: str) -> dict:
    import json
    state_path = os.path.join(project_dir, "state.json")
    if os.path.isfile(state_path):
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}
    return {}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="PostWire MCP test")
    parser.add_argument("--platform", required=True, choices=list(PLATFORM_KEYS.keys()))
    parser.add_argument("--video", required=True, help="Video dosyası yolu")
    parser.add_argument("--title", default="Test Video")
    parser.add_argument("--description", default="Test açıklama")
    parser.add_argument("--scheduled",  help="ISO8601 UTC zaman (örn. 2026-09-15T12:00:00Z)")
    args = parser.parse_args()

    provider = PostWireProvider()
    metadata = {
        "title": args.title,
        "description": args.description,
        "tags": ["test"],
        "privacy": "scheduled" if args.scheduled else "public",
    }

    result = provider.publish(args.platform, args.video, metadata, args.scheduled)
    print(f"Yayın sonucu: {result}")