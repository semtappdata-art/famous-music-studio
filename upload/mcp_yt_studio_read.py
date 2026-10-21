"""YouTube Studio MCP - Salt Okuma Sağlayıcısı.

Bu modül `mcp__yt_studio` üzerinden YouTube salt-okuma işlemlerini yapar:
- Video istatistikleri (batch)
- Playlist öğeleri (üyelik kontrolü)
- Altyazı parçaları listesi/indirme

Özellikler:
- `mcp_client.YouTubeReadProvider` arayüzünü uygular
- Data API formatında veri döner (çağıran kod değişmez)
- Hata durumunda `MCPError` fırlatır → fallback tetiklenir
- Kota etkisi: MCP çağrıları YouTube Data API kotasını TÜKETMEZ
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_client import (
    YouTubeReadProvider,
    VideoStats,
    PlaylistItem,
    CaptionTrack,
    MCPError,
    MCPUnavailableError,
    _log,
)


class YTStudioReadProvider(YouTubeReadProvider):
    """yt_studio MCP sunucusu üzerinden YouTube salt-okuma."""

    def __init__(self):
        self._session = None
        self._init_session()

    def _init_session(self) -> None:
        """MCP oturumunu başlatır (lazy)."""
        try:
            # Pi agent MCP client kullanımı
            import asyncio
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client

            # Not: Gerçek MCP bağlantısı async, sync wrapper yazıyoruz.
            # Bu implementasyonda `mcp__yt_studio` streamable HTTP endpoint'i
            # kullanılıyor (mcp_servers.json konfigürasyonu).
            self._server_url = os.getenv("YT_STUDIO_MCP_URL", "")
            self._token = os.getenv("YT_STUDIO_MCP_TOKEN", "")
            # Authorization header mcp_servers.json'dan alınır
            _log("yt_studio MCP read provider başlatıldı (HTTP endpoint)")
        except Exception as e:
            _log(f"yt_studio MCP read provider başlatılamadı: {e}")
            raise MCPUnavailableError("yt_studio", f"Başlatma hatası: {e}")

    def _call_mcp(self, tool: str, arguments: dict) -> Any:
        """MCP aracını çağırır (sync wrapper over async)."""
        try:
            import asyncio
            import httpx

            # Streamable HTTP MCP endpoint'ine POST
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer " + (self._token or "")
            }

            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool,
                    "arguments": arguments
                }
            }

            # Zaman aşımı
            timeout = 30.0

            with httpx.Client(timeout=timeout) as client:
                response = client.post(self._server_url, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()

            if "error" in result:
                error = result["error"]
                raise MCPError("yt_studio", f"MCP hata: {error.get('message', 'Bilinmeyen')}")

            return result.get("result", {})

        except httpx.TimeoutException:
            raise MCPUnavailableError("yt_studio", "Zaman aşımı")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                from mcp_client import MCPQuotaExceededError
                raise MCPQuotaExceededError("yt_studio", "Rate limit")
            raise MCPUnavailableError("yt_studio", f"HTTP {e.response.status_code}: {e}")
        except Exception as e:
            if isinstance(e, MCPError):
                raise
            raise MCPUnavailableError("yt_studio", f"Bağlantı hatası: {e}")

    # ---- YouTubeReadProvider Arayüzü ----

    def get_video_stats(self, video_ids: list[str]) -> dict[str, VideoStats]:
        """Tek istekte çoklu video istatistikleri.
        
        MCP aracı: `get_video_details` (batch destekli)
        Data API karşılığı: `videos.list(part="statistics,status", id=...)` - 1 birim/50 video
        """
        if not video_ids:
            return {}

        # MCP aracı video_ids listesini kabul etmeli
        result = self._call_mcp("get_video_details", {"video_ids": video_ids})

        stats = {}
        for item in result.get("items", []):
            vid = item.get("id")
            if not vid:
                continue
            statistics = item.get("statistics", {})
            status = item.get("status", {})
            stats[vid] = VideoStats(
                video_id=vid,
                views=int(statistics.get("viewCount", 0) or 0),
                likes=int(statistics.get("likeCount", 0) or 0),
                comments=int(statistics.get("commentCount", 0) or 0),
                privacy_status=status.get("privacyStatus", ""),
            )
        return stats

    def get_playlist_items(self, playlist_id: str) -> list[PlaylistItem]:
        """Playlist öğeleri - üyelik kontrolü için.
        
        MCP aracı: `get_playlist_items`
        Data API karşılığı: `playlistItems.list(part="contentDetails,snippet,status")` - 1 birim/sayfa
        """
        result = self._call_mcp("get_playlist_items", {"playlist_id": playlist_id})

        items = []
        for item in result.get("items", []):
            content = item.get("contentDetails", {})
            snippet = item.get("snippet", {})
            status = item.get("status", {})
            items.append(PlaylistItem(
                video_id=content.get("videoId", ""),
                title=snippet.get("title", ""),
                privacy_status=status.get("privacyStatus", ""),
            ))
        return items

    def get_caption_tracks(self, video_id: str) -> list[CaptionTrack]:
        """Video altyazı parçaları.
        
        MCP aracı: `get_caption_tracks`
        Data API karşılığı: `captions.list(part="snippet", videoId=...)` - 50 birim
        """
        result = self._call_mcp("get_caption_tracks", {"video_id": video_id})

        tracks = []
        for item in result.get("items", []):
            snippet = item.get("snippet", {})
            tracks.append(CaptionTrack(
                id=item.get("id", ""),
                track_kind=(snippet.get("trackKind", "") or "").lower(),
                language=snippet.get("language", ""),
            ))
        return tracks

    def download_caption(self, caption_id: str) -> bytes:
        """Altyazı indir (SRT baytları).
        
        MCP aracı: `download_caption`
        Data API karşılığı: `captions.download(id=..., tfmt="srt")` - 200 birim
        """
        result = self._call_mcp("download_caption", {"caption_id": caption_id, "format": "srt"})

        content = result.get("content", "")
        if isinstance(content, str):
            return content.encode("utf-8")
        return content  # zaten bytes

    def health_check(self) -> bool:
        """Basit bir video detayı çekerek bağlantıyı test et."""
        try:
            # Kanalın herhangi bir videosu ile test (cache'lenmiş olabilir)
            self._call_mcp("get_video_details", {"video_ids": ["HEALTH_CHECK_TEST"]})
            return True
        except Exception:
            return False


# ---- Test amaçlı standalone çalıştırma ----

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="yt_studio MCP read test")
    parser.add_argument("--video-ids", nargs="+", help="Test video ID'leri")
    parser.add_argument("--playlist-id", help="Test playlist ID")
    parser.add_argument("--caption-video-id", help="Altyazı test video ID")
    args = parser.parse_args()

    provider = YTStudioReadProvider()

    if args.video_ids:
        print(f"Video istatistikleri çekiliyor: {args.video_ids}")
        stats = provider.get_video_stats(args.video_ids)
        for vid, s in stats.items():
            print(f"  {vid}: views={s.views}, likes={s.likes}, privacy={s.privacy_status}")

    if args.playlist_id:
        print(f"Playlist öğeleri: {args.playlist_id}")
        items = provider.get_playlist_items(args.playlist_id)
        print(f"  {len(items)} öğe")
        for item in items[:5]:
            print(f"  - {item.video_id}: {item.title[:50]}")

    if args.caption_video_id:
        print(f"Altyazı parçaları: {args.caption_video_id}")
        tracks = provider.get_caption_tracks(args.caption_video_id)
        for t in tracks:
            print(f"  {t.id}: kind={t.track_kind}, lang={t.language}")