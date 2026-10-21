"""YouTube Studio MCP - Yazma Sağlayıcısı.

Bu modül `mcp__yt_studio` üzerinden YouTube yazma işlemlerini yapar:
- Video gizlilik güncelleme (containsSyntheticMedia KORUNUR)
- Playlist oluşturma / video ekleme
- Altyazı yükleme/güncelleme (insert/update)

Özellikler:
- `mcp_client.YouTubeWriteProvider` arayüzünü uygular
- `guvenli_status_govdesi()` mantığı MCP isteğine de uygulanır
- Idempotent işlemler (playlist ekleme zaten varsa sessizce başarı)
- Hata durumunda `MCPError` fırlatır → fallback tetiklenir
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_client import (
    YouTubeWriteProvider,
    MCPError,
    MCPUnavailableError,
    MCPQuotaExceededError,
    _log,
)


class YTStudioWriteProvider(YouTubeWriteProvider):
    """yt_studio MCP sunucusu üzerinden YouTube yazma."""

    def __init__(self):
        self._server_url = os.getenv("YT_STUDIO_MCP_URL", "")
        self._token = os.getenv("YT_STUDIO_MCP_TOKEN", "")

    def _call_mcp(self, tool: str, arguments: dict) -> Any:
        """MCP aracını çağırır."""
        if not getattr(self, "_server_url", ""):
            raise MCPUnavailableError("yt_studio", "yapilandirilmamis (env YT_STUDIO_MCP_URL bos) -> fallback")
        try:
            import httpx

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

            timeout = 60.0  # yazma işlemleri daha uzun sürebilir

            with httpx.Client(timeout=timeout) as client:
                response = client.post(self._server_url, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()

            if "error" in result:
                error = result["error"]
                msg = error.get("message", "Bilinmeyen")
                if "quota" in msg.lower() or "rate limit" in msg.lower():
                    raise MCPQuotaExceededError("yt_studio", msg)
                raise MCPError("yt_studio", f"MCP hata: {msg}")

            return result.get("result", {})

        except httpx.TimeoutException:
            raise MCPUnavailableError("yt_studio", "Zaman aşımı")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise MCPQuotaExceededError("yt_studio", "Rate limit")
            raise MCPUnavailableError("yt_studio", f"HTTP {e.response.status_code}: {e}")
        except Exception as e:
            if isinstance(e, MCPError):
                raise
            raise MCPUnavailableError("yt_studio", f"Bağlantı hatası: {e}")

    # ---- YouTubeWriteProvider Arayüzü ----

    def update_video_privacy(self, video_id: str, privacy_status: str,
                             preserve_synthetic_media: bool = True) -> bool:
        """Video gizliliğini günceller.
        
        KRİTİK: `containsSyntheticMedia: true` ve `selfDeclaredMadeForKids: false`
        alanları KORUNMALI (bkz. CLAUDE.md: `upload/set_privacy.py` tuzağı).
        
        MCP aracı: `update_video_status`
        Data API karşılığı: `videos.update(part="status", body={...})` - 50 birim
        
        Argümanlar:
            video_id: Video kimliği
            privacy_status: "public" | "private" | "unlisted"
            preserve_synthetic_media: True ise mevcut containsSyntheticMedia korunur
        """
        # Önce mevcut status'u oku (guvenli_status_govdesi mantığı)
        current = self._call_mcp("get_video_status", {"video_id": video_id})
        status = current.get("status", {})

        # Korunacak alanlar
        synthetic_media = status.get("containsSyntheticMedia", True)  # varsayılan True
        made_for_kids = status.get("selfDeclaredMadeForKids", False)

        # Güncelleme gövdesi
        body = {
            "privacyStatus": privacy_status,
        }
        if preserve_synthetic_media:
            body["containsSyntheticMedia"] = synthetic_media
            body["selfDeclaredMadeForKids"] = made_for_kids

        result = self._call_mcp("update_video_status", {
            "video_id": video_id,
            "status": body
        })

        success = result.get("success", False)
        if success:
            _log(f"Video gizliliği güncellendi (MCP): {video_id} -> {privacy_status}")
        return success

    def add_to_playlist(self, playlist_id: str, video_id: str) -> bool:
        """Video playlist'e ekler (idempotent).
        
        MCP aracı: `add_to_playlist`
        Data API karşılığı: `playlistItems.insert` - 50 birim
        
        Zaten ekliyse hata VERMEZ, True döner (idempotent).
        """
        result = self._call_mcp("add_to_playlist", {
            "playlist_id": playlist_id,
            "video_id": video_id
        })

        # MCP zaten varsa "already_exists" dönebilir
        status = result.get("status", "")
        if status in ("added", "already_exists"):
            _log(f"Playlist'e eklendi (MCP): {video_id} -> {playlist_id}")
            return True
        return False

    def create_playlist(self, title: str, description: str, privacy: str = "public") -> str:
        """Playlist oluşturur, ID döner.
        
        MCP aracı: `create_playlist`
        Data API karşılığı: `playlists.insert` - 50 birim
        """
        result = self._call_mcp("create_playlist", {
            "title": title,
            "description": description,
            "privacy": privacy
        })

        playlist_id = result.get("playlist_id") or result.get("id")
        if playlist_id:
            _log(f"Playlist oluşturuldu (MCP): {title} -> {playlist_id}")
        return playlist_id or ""

    def upload_caption(self, video_id: str, srt_content: str, language: str,
                       caption_id: str | None = None) -> str:
        """Altyazı yükler/günceller.
        
        MCP aracı: `upload_caption`
        Data API karşılığı: `captions.insert` (yeni) / `captions.update` (mevcut) - 50+200 birim
        
        caption_id verilmişse update, yoksa insert.
        Dönüş: caption_id (yeni veya güncellenen)
        """
        result = self._call_mcp("upload_caption", {
            "video_id": video_id,
            "srt_content": srt_content,
            "language": language,
            "caption_id": caption_id,
            "is_draft": False,
        })

        new_id = result.get("caption_id") or result.get("id")
        action = "güncellendi" if caption_id else "yükledi"
        if new_id:
            _log(f"Altyazı {action} (MCP): {video_id} -> {new_id}")
        return new_id or ""

    def health_check(self) -> bool:
        """Yazma API'si sağlığı - basit bir status okuma ile test."""
        try:
            self._call_mcp("get_video_status", {"video_id": "HEALTH_CHECK_TEST"})
            return True
        except Exception:
            return False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="yt_studio MCP write test")
    parser.add_argument("--video-id", help="Test video ID")
    parser.add_argument("--privacy", choices=["public", "private", "unlisted"], help="Gizlilik")
    parser.add_argument("--playlist-id", help="Test playlist ID")
    parser.add_argument("--add-video-id", help="Playlist'e eklenecek video ID")
    args = parser.parse_args()

    provider = YTStudioWriteProvider()

    if args.video_id and args.privacy:
        print(f"Gizlilik güncelleniyor: {args.video_id} -> {args.privacy}")
        ok = provider.update_video_privacy(args.video_id, args.privacy)
        print(f"  Başarılı: {ok}")

    if args.playlist_id and args.add_video_id:
        print(f"Playlist'e ekleme: {args.add_video_id} -> {args.playlist_id}")
        ok = provider.add_to_playlist(args.playlist_id, args.add_video_id)
        print(f"  Başarılı: {ok}")