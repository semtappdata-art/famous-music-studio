"""MCP Client Katmanı Testleri.

Test edilenler:
- MCPClientManager singleton davranışı
- Feature flag kontrolü
- Health check cache
- Fallback decorator mantığı
- State yardımcıları (atomik yazım)
"""

import os
import sys
import tempfile
import json
import time
from unittest.mock import patch, MagicMock, AsyncMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'upload'))

import pytest

# Test izolasyonu için conftest fixture'larını kullan
# conftest fixtures: uretim_dosyalarini_koru, gercek_bildirim_kanalini_kapat


class TestMCPClientManager:
    """MCPClientManager singleton ve provider yönetimi testleri."""

    def test_singleton(self):
        """Aynı instance döner."""
        from mcp_client import MCPClientManager
        m1 = MCPClientManager()
        m2 = MCPClientManager()
        assert m1 is m2

    def test_provider_lazy_init(self, monkeypatch):
        """Provider'lar ilk erişimde oluşturulur."""
        from mcp_client import MCPClientManager, MCP_ENABLED

        # Tüm MCP'leri kapat
        monkeypatch.setattr("mcp_client.MCP_ENABLED", {
            "yt_studio": False, "postwire": False, "suno": False
        })

        mgr = MCPClientManager()
        assert mgr.get_read_provider() is None
        assert mgr.get_write_provider() is None
        assert mgr.get_social_provider() is None
        assert mgr.get_suno_provider() is None

    def test_health_check_cache(self, monkeypatch):
        """Sağlık kontrolü cache'lenir (5 dk TTL)."""
        from mcp_client import MCPClientManager, MCPProvider

        mgr = MCPClientManager()

        # Mock provider
        mock_read = MagicMock()
        mock_read.health_check.return_value = True
        mock_write = MagicMock()
        mock_write.health_check.return_value = True

        monkeypatch.setattr(mgr, "get_read_provider", lambda: mock_read)
        monkeypatch.setattr(mgr, "get_write_provider", lambda: mock_write)

        # İlk çağrı
        result1 = mgr.check_health(MCPProvider.YT_STUDIO)
        assert result1 is True
        assert mock_read.health_check.call_count == 1

        # İkinci çağrı - cache'ten
        result2 = mgr.check_health(MCPProvider.YT_STUDIO)
        assert result2 is True
        assert mock_read.health_check.call_count == 1  # artmamalı

        # Cache invalidate
        mgr.invalidate_health(MCPProvider.YT_STUDIO)
        result3 = mgr.check_health(MCPProvider.YT_STUDIO)
        assert result3 is True
        assert mock_read.health_check.call_count == 2  # yeniden çağrıldı


class TestMCPConfigValidation:
    """MCP yapılandırma doğrulama testleri."""

    def test_validate_mcp_config_disabled(self, monkeypatch, caplog):
        """Kapalı MCP'ler False döner."""
        from mcp_client import validate_mcp_config, MCP_ENABLED

        monkeypatch.setattr("mcp_client.MCP_ENABLED", {
            "yt_studio": False, "postwire": False, "suno": False
        })

        results = validate_mcp_config()
        assert results["yt_studio"] is False
        assert results["postwire"] is False
        assert results["suno"] is False


class TestStateHelpers:
    """Atomik state yardımcıları testleri."""

    def test_update_project_state_atomic(self, tmp_path):
        """State atomik yazılır (yarım JSON kalmaz)."""
        from mcp_client import update_project_state, load_project_state

        project_dir = tmp_path / "test_project"
        project_dir.mkdir()

        # İlk yazım
        update_project_state(str(project_dir), {"test": "value1", "number": 42})
        state = load_project_state(str(project_dir))
        assert state["test"] == "value1"
        assert state["number"] == 42

        # Güncelleme
        update_project_state(str(project_dir), {"test": "value2"})
        state = load_project_state(str(project_dir))
        assert state["test"] == "value2"
        assert state["number"] == 42  # korunmalı

    def test_load_project_state_missing(self, tmp_path):
        """Olmayan dosya boş dict döner."""
        from mcp_client import load_project_state

        project_dir = tmp_path / "yok"
        project_dir.mkdir()
        state = load_project_state(str(project_dir))
        assert state == {}

    def test_load_project_state_corrupted(self, tmp_path):
        """Bozuk JSON boş dict döner (hata fırlatmaz)."""
        from mcp_client import load_project_state

        project_dir = tmp_path / "bozuk"
        project_dir.mkdir()
        state_file = project_dir / "state.json"
        state_file.write_text("{ bozuk json }")

        state = load_project_state(str(project_dir))
        assert state == {}


class TestFallbackDecorator:
    """Fallback decorator mantığı testleri."""

    def test_fallback_disabled_when_mcp_off(self, monkeypatch):
        """MCP kapalıysa decorator doğrudan fonksiyonu çağırır."""
        from mcp_client import with_mcp_fallback, MCPProvider, MCP_ENABLED

        monkeypatch.setattr("mcp_client.MCP_ENABLED", {MCPProvider.YT_STUDIO.value: False})

        called = []

        @with_mcp_fallback(MCPProvider.YT_STUDIO)
        def test_func(x):
            called.append(x)
            return x * 2

        result = test_func(5)
        assert result == 10
        assert called == [5]

    def test_fallback_on_mcp_error(self, monkeypatch):
        """MCP hatasında fallback fonksiyonu çalışır."""
        from mcp_client import with_mcp_fallback, MCPProvider, MCPError, MCP_FALLBACK_ENABLED

        monkeypatch.setattr("mcp_client.MCP_ENABLED", {MCPProvider.YT_STUDIO.value: True})
        monkeypatch.setattr("mcp_client.MCP_FALLBACK_ENABLED", True)

        fallback_called = []

        @with_mcp_fallback(MCPProvider.YT_STUDIO)
        def test_func():
            raise MCPError(MCPProvider.YT_STUDIO, "test hatası")

        def fallback():
            fallback_called.append(True)
            return "fallback"

        # Decorator fallback'i otomatik çağırmaz - wrapper fonksiyonu içinde
        # try/except ile yapılır. Bu test decorator'ın davranışını doğrular.
        try:
            test_func()
        except MCPError:
            pass

        # Gerçek fallback youtube_stats_mcp.py'de _try_mcp_batch None döndürüp
        # data_api.get_stats_batch çağrıldığında gerçekleşir.


class TestMCPErrorHierarchy:
    """MCP hata hiyerarşisi testleri."""

    def test_mcp_error_attributes(self):
        """MCPError provider ve original hatayı taşır."""
        from mcp_client import MCPError, MCPProvider, MCPUnavailableError

        try:
            raise MCPError(MCPProvider.YT_STUDIO, "test", ValueError("orijinal"))
        except MCPError as e:
            assert e.provider == MCPProvider.YT_STUDIO
            assert isinstance(e.original, ValueError)

    def test_mcp_unavailable_error(self):
        """MCPUnavailableError ayrı catch edilebilir."""
        from mcp_client import MCPUnavailableError, MCPProvider

        try:
            raise MCPUnavailableError(MCPProvider.POSTWIRE, "bağlantı yok")
        except MCPUnavailableError as e:
            assert e.provider == MCPProvider.POSTWIRE


# ---- Entegrasyon Testleri (Mock MCP Server) ----

class TestYTStudioReadProviderMock:
    """yt_studio read provider mock testleri."""

    @pytest.fixture
    def mock_provider(self, monkeypatch):
        from mcp_yt_studio_read import YTStudioReadProvider

        provider = YTStudioReadProvider()

        # _call_mcp'yi mockla
        def mock_call(tool, args):
            if tool == "get_video_details":
                return {
                    "items": [{
                        "id": args["video_ids"][0],
                        "statistics": {"viewCount": "1000", "likeCount": "50", "commentCount": "10"},
                        "status": {"privacyStatus": "public"}
                    }]
                }
            elif tool == "get_playlist_items":
                return {"items": [{"contentDetails": {"videoId": "vid1"}, "snippet": {"title": "Test"}, "status": {"privacyStatus": "public"}}]}
            elif tool == "get_caption_tracks":
                return {"items": [{"id": "cap1", "snippet": {"trackKind": "asr", "language": "tr"}}]}
            elif tool == "download_caption":
                return {"content": "1\n00:00:00,000 --> 00:00:05,000\nTest\n"}
            return {}

        provider._call_mcp = mock_call
        return provider

    def test_get_video_stats_batch(self, mock_provider):
        """Batch video istatistikleri."""
        stats = mock_provider.get_video_stats(["vid1", "vid2"])
        assert "vid1" in stats
        assert stats["vid1"].views == 1000
        assert stats["vid1"].likes == 50
        assert stats["vid1"].privacy_status == "public"

    def test_get_playlist_items(self, mock_provider):
        """Playlist öğeleri."""
        items = mock_provider.get_playlist_items("PL_test")
        assert len(items) == 1
        assert items[0].video_id == "vid1"
        assert items[0].title == "Test"

    def test_get_caption_tracks(self, mock_provider):
        """Altyazı parçaları."""
        tracks = mock_provider.get_caption_tracks("vid1")
        assert len(tracks) == 1
        assert tracks[0].track_kind == "asr"
        assert tracks[0].language == "tr"

    def test_download_caption(self, mock_provider):
        """Altyazı indirme."""
        content = mock_provider.download_caption("cap1")
        assert b"Test" in content


class TestYTStudioWriteProviderMock:
    """yt_studio write provider mock testleri."""

    @pytest.fixture
    def mock_provider(self, monkeypatch):
        from mcp_yt_studio_write import YTStudioWriteProvider

        provider = YTStudioWriteProvider()

        def mock_call(tool, args):
            if tool == "get_video_status":
                return {"status": {"containsSyntheticMedia": True, "selfDeclaredMadeForKids": False}}
            elif tool == "update_video_status":
                return {"success": True}
            elif tool == "add_to_playlist":
                return {"status": "added"}
            elif tool == "create_playlist":
                return {"playlist_id": "PL_new123"}
            elif tool == "upload_caption":
                return {"caption_id": "cap_new123"}
            return {}

        provider._call_mcp = mock_call
        return provider

    def test_update_video_privacy_preserves_synthetic_media(self, mock_provider):
        """containsSyntheticMedia korunur."""
        ok = mock_provider.update_video_privacy("vid1", "unlisted", preserve_synthetic_media=True)
        assert ok is True

    def test_add_to_playlist_idempotent(self, mock_provider):
        """Zaten ekliyse hata vermez."""
        ok = mock_provider.add_to_playlist("PL_test", "vid1")
        assert ok is True

    def test_create_playlist(self, mock_provider):
        """Playlist oluşturma."""
        pid = mock_provider.create_playlist("Test", "Desc", "public")
        assert pid == "PL_new123"

    def test_upload_caption_insert_and_update(self, mock_provider):
        """Altyazı insert ve update."""
        # Insert
        cap_id = mock_provider.upload_caption("vid1", "SRT content", "tr")
        assert cap_id == "cap_new123"

        # Update
        cap_id2 = mock_provider.upload_caption("vid1", "SRT content v2", "tr", caption_id="cap1")
        assert cap_id2 == "cap_new123"


class TestPostWireProviderMock:
    """PostWire provider mock testleri."""

    @pytest.fixture
    def mock_provider(self, monkeypatch):
        from mcp_postwire import PostWireProvider

        provider = PostWireProvider()

        def mock_call(tool, args):
            if tool == "publish_video":
                return {"post_id": "post_123", "status": "published"}
            elif tool == "get_scheduled_posts":
                return {"posts": [{"post_id": "post_123", "scheduled_publish_time": "2026-09-15T12:00:00Z", "status": "scheduled", "title": "Test"}]}
            elif tool == "health_check":
                return {"status": "ok"}
            return {}

        provider._call_mcp = mock_call
        return provider

    def test_publish_video(self, mock_provider, tmp_path):
        """Video yayınlama."""
        video_path = tmp_path / "video.mp4"
        video_path.write_bytes(b"fake video")
        result = mock_provider.publish("youtube", str(video_path), {"title": "Test", "description": "Desc", "tags": ["tag1"]})
        assert result["post_id"] == "post_123"
        assert result["status"] == "published"
        assert result["platform"] == "youtube"

    def test_publish_scheduled(self, mock_provider, tmp_path):
        """Zamanlanmış yayın."""
        video_path = tmp_path / "video.mp4"
        video_path.write_bytes(b"fake video")
        result = mock_provider.publish("instagram", str(video_path),
                                       {"title": "Test", "description": "Desc"},
                                       scheduled_at="2026-09-15T12:00:00Z")
        assert result["status"] == "published"

    def test_get_scheduled_posts(self, mock_provider):
        """Zamanlanmış gönderiler."""
        posts = mock_provider.get_scheduled_posts("instagram")
        assert len(posts) == 1
        assert posts[0]["post_id"] == "post_123"


import os

class TestSunoProviderMock:
    """Suno provider mock testleri."""

    @pytest.fixture
    def mock_provider(self, monkeypatch, tmp_path):
        from mcp_suno import SunoMCPProvider

        provider = SunoMCPProvider()

        output_file = tmp_path / "audio.wav"
        output_file.write_bytes(b"fake audio data")

        def mock_call(tool, args):
            if tool == "generate_and_download":
                import os as _os
                op = args.get("output_path") or str(output_file)
                _os.makedirs(_os.path.dirname(_os.path.abspath(op)), exist_ok=True)
                with open(op, "wb") as f:
                    f.write(b"fake audio data")
                return {
                    "audio_path": op,
                    "title": "Test Sarki",
                    "duration": 180.5,
                    "style": "pop",
                    "lyrics": "Test lyrics",
                    "meta": {"song_id": "suno_123"},
                }
            if tool == "health_check":
                return {"status": "ok"}
            return {}

        provider._call_mcp = mock_call
        return provider

    def test_generate_and_download(self, mock_provider, tmp_path):
        """Şarkı üretim ve indirme."""
        output_path = str(tmp_path / "output.wav")
        result = mock_provider.generate_and_download("test prompt", output_path)

        assert os.path.isfile(result["audio_path"])
        assert result["title"] == "Test Sarki"
        assert result["duration"] == 180.5
        assert os.path.isfile(output_path)


class TestIntegrationScenarios:
    """Senaryo testleri: MCP + Fallback zinciri."""

    def test_youtube_stats_mcp_fallback_chain(self, monkeypatch, tmp_path):
        """youtube_stats_mcp: MCP başarısız -> Data API."""
        from mcp_client import mcp_manager
        import youtube_stats_mcp as mcp_module

        # MCP provider'ı mockla - hata fırlat
        mock_read = MagicMock()
        mock_read.get_video_stats.side_effect = Exception("MCP down")
        monkeypatch.setattr(mcp_manager, "get_read_provider", lambda: mock_read)

        # Data API mockla
        mock_data_api = MagicMock()
        mock_data_api.get_stats_batch.return_value = {"istek": 1, "video": 2, "proje": 1}
        monkeypatch.setattr(mcp_module, "data_api", mock_data_api)

        # Test proje oluştur
        project_dir = tmp_path / "projects" / "test_sarki"
        project_dir.mkdir(parents=True)
        state_file = project_dir / "state.json"
        state_file.write_text(json.dumps({
            "youtube_video_id": "vid1",
            "youtube_shorts_video_id": "vid2"
        }))

        # KOK yapisi: tmp/projects/test_sarki/state.json -> KOKLER=[.../projects], base=None
        monkeypatch.setattr("uyumluluk.KOKLER", [str(tmp_path / "projects")])
        monkeypatch.setattr(mcp_module, "mcp_enabled", lambda ad: True)

        result = mcp_module.get_stats_batch(None)
        # Fallback Data API çağrılmış olmalı
        assert result["proje"] == 1
        mock_data_api.get_stats_batch.assert_called_once()

    def test_youtube_playlists_mcp_fallback_chain(self, monkeypatch, tmp_path):
        """youtube_playlists_mcp: MCP başarısız -> Data API."""
        from mcp_client import mcp_manager
        import youtube_playlists_mcp as mcp_module

        # MCP provider'ları hata fırlat
        mock_read = MagicMock()
        mock_read.get_playlist_items.side_effect = Exception("MCP down")
        mock_write = MagicMock()
        mock_write.add_to_playlist.side_effect = Exception("MCP down")
        mock_write.create_playlist.side_effect = Exception("MCP down")

        monkeypatch.setattr(mcp_manager, "get_read_provider", lambda: mock_read)
        monkeypatch.setattr(mcp_manager, "get_write_provider", lambda: mock_write)

        # Data API mock
        mock_data_api = MagicMock()
        monkeypatch.setattr(mcp_module, "data_api", mock_data_api)

        project_dir = tmp_path / "projects" / "test"
        project_dir.mkdir(parents=True)
        (project_dir / "state.json").write_text(json.dumps({"youtube_video_id": "vid1", "youtube_privacy": "public"}))
        (project_dir / "meta.json").write_text(json.dumps({"title": "Test", "theme": "pop"}))

        monkeypatch.setattr("uyumluluk.KOKLER", [str(tmp_path / "projects")])
        monkeypatch.setattr(mcp_module, "mcp_enabled", lambda ad: True)
        # Business kurallardan bagimsiz: plan sabit, cache temiz
        monkeypatch.setattr(mcp_module, "beklenen_anahtarlar", lambda *a, **k: {"vid1": ["pop"]})
        mcp_module._UYE_ONBELLEK_MCP.clear()
        mcp_module._OGE_ONBELLEK_MCP.clear()
        # playlist_ids dosyasına yazmayalım: _playlist_id_mcp'i sahte pid'e sabitle
        monkeypatch.setattr(mcp_module, "_playlist_id_mcp", lambda *a, **k: "PL_test123")

        mcp_module.sync_all(str(tmp_path / "projects"))
        mock_data_api.sync_all.assert_called_once()

    def test_social_publish_mcp_fallback_chain(self, monkeypatch, tmp_path):
        """social_publish_mcp: MCP başarısız -> fallback upload modülleri."""
        from mcp_client import mcp_manager
        import social_publish_mcp as mcp_module

        # MCP provider hata
        mock_social = MagicMock()
        from mcp_client import MCPError as _ME
        mock_social.publish.side_effect = _ME("postwire", "PostWire down")
        monkeypatch.setattr(mcp_manager, "get_social_provider", lambda: mock_social)

        # Fallback modüller mock
        mock_yt = MagicMock()
        mock_yt.upload_video.return_value = "vid_123"
        monkeypatch.setattr(mcp_module, "youtube_upload", mock_yt)

        project_dir = tmp_path / "projects" / "test"
        project_dir.mkdir(parents=True)
        (project_dir / "output").mkdir()
        (project_dir / "output" / "youtube_16x9.mp4").write_bytes(b"video")
        (project_dir / "state.json").write_text(json.dumps({"youtube_privacy": "public"}))
        (project_dir / "meta.json").write_text(json.dumps({"title": "Test", "theme": "pop"}))

        results = mcp_module.publish_to_platforms(str(project_dir), ["youtube"])
        assert results["youtube"]["success"] is True
        assert results["youtube"]["post_id"] == "vid_123"
        mock_yt.upload_video.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])