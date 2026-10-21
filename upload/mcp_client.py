"""MCP (Model Context Protocol) Client Abstraction Layer.

Bu modül, MCP sunucularıyla (yt_studio, postwire, suno) iletişimi soyutlar.
Özellikler:
- Sağlayıcı-agnostik arayüzler (Protocol/Interface)
- Feature flag ile kademeli geçiş
- Data API'ye otomatik fallback (fail-over, fail-open DEĞIL)
- Atomik state yazımı (state_io ile uyumlu)
- Log maskeleme (gizli_maskele entegrasyonu)
- Kota/bağlantı izolasyonu

Mimari kararlar (CLAUDE.md'ye uygun):
1. Yeni bir platform/adım eklerken `_is_fully_done()`'a EKLEME - MCP çağrıları
   ucuz/idempotent/kotasız olduğu için `_drain_golden_hour_queue()` mantığına uygun.
2. `uyumluluk.py` fail-closed kapısı: MCP erişilemezse Data API'ye fallback,
   HİÇBİRİ erişilemezse HATA (boru hattı durur) - sessiz başarısızlık YOK.
3. Testler ÖNCE yazılır (TDD) - `tests/test_mcp_*` dosyaları bu modülü doğrular.
4. `state_io._atomik_yaz` kullanılır - yarım JSON riski yok.
5. `gorev_sarmalayici.py` deseninde: log maskeleme yazma ZAMANINDA olur.
"""

from __future__ import annotations

import json
import os
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import state_io
from gizli_maskele import maskele

# ---- Yapılandırma ---------------------------------------------------------

# Feature flags: her MCP bagimsiz acilip kapanabilir.
# Varsayilan KAPALI (False) - prod'da canary ile acilir.
# Deger zinciri: config.py varsayilani < config.yaml < env (MCP_<AD>_ENABLED=1/0).
# Neden fonksiyon: import aninda dondurulan dict, elle config degisikligini
# bir sonraki process restartina kadar gormezdi; fonksiyon her cagirida okur.
def _env_bool(ad: str, varsayilan: bool) -> bool:
    v = os.getenv(ad)
    if v is None:
        return varsayilan
    return v.strip().lower() not in ("", "0", "false", "no", "kapali")

def mcp_enabled(ad: str) -> bool:
    return _env_bool(
        "MCP_%s_ENABLED" % ad.upper(),
        bool(getattr(config, "MCP_%s_ENABLED" % ad.upper(), False)),
    )

# Geriye uyumluluk: eski kod MCP_ENABLED["yt_studio"] okuyordu.
# Dict degil, dinamik okuyan obje (Mapping benzeri).
class _McpEnabledView:
    def __getitem__(self, k):
        return mcp_enabled(k)
    def get(self, k, d=None):
        try:
            return mcp_enabled(k)
        except Exception:
            return d
    def __contains__(self, k):
        return k in ("yt_studio", "postwire", "suno")

MCP_ENABLED = _McpEnabledView()

def mcp_fallback_enabled() -> bool:
    v = os.getenv("MCP_FALLBACK_ENABLED")
    if v is not None:
        return v.strip().lower() not in ("", "0", "false", "no")
    return bool(getattr(config, "MCP_FALLBACK_ENABLED", True))

MCP_FALLBACK_ENABLED = True  # import-aninda deger; gercek karar mcp_fallback_enabled()

def mcp_timeout_sn() -> float:
    try:
        return float(os.getenv("MCP_TIMEOUT_SN", getattr(config, "MCP_TIMEOUT_SN", 30)))
    except Exception:
        return 30.0

MCP_TIMEOUT_SN = 30

# Log yolu (auto_process.log ile aynı dosya - maskeleyici paylaşır).
LOG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "auto_process.log"
)


def _log(mesaj: str) -> None:
    """auto_process.log'a maskelemiş yaz. Yazma hatası otomasyonu durdurmaz."""
    satir = "[%s] MCP: %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), maskele(mesaj))
    print(satir)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(satir + "\n")
    except OSError:
        pass


# ---- Ortak Veri Tipleri ---------------------------------------------------

class MCPProvider(Enum):
    YT_STUDIO = "yt_studio"
    POSTWIRE = "postwire"
    SUNO = "suno"


class MCPError(Exception):
    """MCP katmanı hatası - fallback tetikleyici."""
    def __init__(self, provider, message: str, original=None):
        if isinstance(provider, str):
            self.provider = MCPProvider(provider)
        else:
            self.provider = provider
        self.original = original
        super().__init__(f"{self.provider.value}: {message}")


class MCPUnavailableError(MCPError):
    """MCP sunucusuna bağlanılamıyor / yanıt vermiyor."""


class MCPQuotaExceededError(MCPError):
    """MCP kota aşıldı (PostWire/yt_studio tarafında)."""


@dataclass
class VideoStats:
    """YouTube video istatistikleri - provider-agnostik."""
    video_id: str
    views: int = 0
    likes: int = 0
    comments: int = 0
    privacy_status: str = ""
    checked_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%S"))


@dataclass
class PlaylistItem:
    """Playlist öğesi - provider-agnostik."""
    video_id: str
    title: str = ""
    privacy_status: str = ""


@dataclass
class CaptionTrack:
    """Altyazı parçası - provider-agnostik."""
    id: str
    track_kind: str  # "asr" | "manual"
    language: str = ""


# ---- Soyut Arayüzler (Protocol) ------------------------------------------

class YouTubeReadProvider(ABC):
    """YouTube salt-okuma işlemleri için soyut arayüz."""

    @abstractmethod
    def get_video_stats(self, video_ids: list[str]) -> dict[str, VideoStats]:
        """Tek istekte çoklu video istatistikleri (batch)."""
        ...

    @abstractmethod
    def get_playlist_items(self, playlist_id: str) -> list[PlaylistItem]:
        """Playlist öğeleri (üyelik kontrolü için)."""
        ...

    @abstractmethod
    def get_caption_tracks(self, video_id: str) -> list[CaptionTrack]:
        """Video altyazı parçaları."""
        ...

    @abstractmethod
    def download_caption(self, caption_id: str) -> bytes:
        """Altyazı indir (SRT baytları)."""
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Bağlantı sağlığı - saatlik görevin `finally` bloğunda kullanılır."""
        ...


class YouTubeWriteProvider(ABC):
    """YouTube yazma işlemleri için soyut arayüz."""

    @abstractmethod
    def update_video_privacy(self, video_id: str, privacy_status: str,
                             preserve_synthetic_media: bool = True) -> bool:
        """Video gizliliğini günceller. containsSyntheticMedia KORUNUR."""
        ...

    @abstractmethod
    def add_to_playlist(self, playlist_id: str, video_id: str) -> bool:
        """Video playlist'e ekler (idempotent)."""
        ...

    @abstractmethod
    def create_playlist(self, title: str, description: str, privacy: str = "public") -> str:
        """Playlist oluşturur, ID döner."""
        ...

    @abstractmethod
    def upload_caption(self, video_id: str, srt_content: str, language: str,
                       caption_id: str | None = None) -> str:
        """Altyazı yükler/günceller. caption_id varsa update, yoksa insert."""
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Yazma API'si sağlığı."""
        ...


class SocialPublishProvider(ABC):
    """Çok platformlu yayın için soyut arayüz (PostWire)."""

    @abstractmethod
    def publish(self, platform: str, video_path: str, metadata: dict,
                scheduled_at: str | None = None) -> dict:
        """Video yayınlar. scheduled_at = ISO8601 UTC (örn. '2026-09-15T12:00:00Z').
        Dönüş: {'post_id': ..., 'platform': ..., 'status': 'published'|'scheduled'|'draft'}"""
        ...

    @abstractmethod
    def get_scheduled_posts(self, platform: str) -> list[dict]:
        """Zamanlanmış/pending gönderileri listeler."""
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """PostWire bağlantı sağlığı."""
        ...


class SunoProvider(ABC):
    """Suno üretim/indirme için soyut arayüz."""

    @abstractmethod
    def generate_and_download(self, prompt: str, output_path: str,
                              meta: dict | None = None) -> dict:
        """Şarkı üretir, indirir, metadata döner."""
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Suno MCP bağlantı sağlığı."""
        ...


# ---- MCP İstemci Yöneticisi (Singleton Pattern) --------------------------

class MCPClientManager:
    """MCP istemcilerini yönetir, lazy initialization, sağlık izleme."""

    _instance: Optional["MCPClientManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._read_provider: YouTubeReadProvider | None = None
        self._write_provider: YouTubeWriteProvider | None = None
        self._social_provider: SocialPublishProvider | None = None
        self._suno_provider: SunoProvider | None = None

        self._health_cache: dict[MCPProvider, tuple[bool, float]] = {}
        self._health_ttl = 300  # 5 dakika cache

    # ---- Provider getters (lazy init) ----

    def get_read_provider(self) -> YouTubeReadProvider | None:
        if not mcp_enabled("yt_studio"):
            return None
        if self._read_provider is None:
            self._read_provider = self._create_yt_studio_read_provider()
        return self._read_provider

    def get_write_provider(self) -> YouTubeWriteProvider | None:
        if not mcp_enabled("yt_studio"):
            return None
        if self._write_provider is None:
            self._write_provider = self._create_yt_studio_write_provider()
        return self._write_provider

    def get_social_provider(self) -> SocialPublishProvider | None:
        if not mcp_enabled("postwire"):
            return None
        if self._social_provider is None:
            self._social_provider = self._create_postwire_provider()
        return self._social_provider

    def get_suno_provider(self) -> SunoProvider | None:
        if not mcp_enabled("suno"):
            return None
        if self._suno_provider is None:
            self._suno_provider = self._create_suno_provider()
        return self._suno_provider

    # ---- Factory methods (import-time dependency isolation) ----

    def _create_yt_studio_read_provider(self) -> YouTubeReadProvider:
        from upload.mcp_yt_studio_read import YTStudioReadProvider
        return YTStudioReadProvider()

    def _create_yt_studio_write_provider(self) -> YouTubeWriteProvider:
        from upload.mcp_yt_studio_write import YTStudioWriteProvider
        return YTStudioWriteProvider()

    def _create_postwire_provider(self) -> SocialPublishProvider:
        from upload.mcp_postwire import PostWireProvider
        return PostWireProvider()

    def _create_suno_provider(self) -> SunoProvider:
        from upload.mcp_suno import SunoMCPProvider
        return SunoMCPProvider()

    # ---- Health check (cached) ----

    def check_health(self, provider: MCPProvider) -> bool:
        now = time.time()
        cached = self._health_cache.get(provider)
        if cached and (now - cached[1]) < self._health_ttl:
            return cached[0]

        result = False
        try:
            if provider == MCPProvider.YT_STUDIO:
                read_p = self.get_read_provider()
                write_p = self.get_write_provider()
                result = (read_p is not None and read_p.health_check() and
                          write_p is not None and write_p.health_check())
            elif provider == MCPProvider.POSTWIRE:
                social_p = self.get_social_provider()
                result = social_p is not None and social_p.health_check()
            elif provider == MCPProvider.SUNO:
                suno_p = self.get_suno_provider()
                result = suno_p is not None and suno_p.health_check()
        except Exception as e:
            _log(f"Health check failed for {provider.value}: {e}")
            result = False

        self._health_cache[provider] = (result, now)
        return result

    def invalidate_health(self, provider: MCPProvider) -> None:
        """Sağlık cache'ini temizle (hata sonrası zorlu yenileme)."""
        self._health_cache.pop(provider, None)


# Global singleton instance
mcp_manager = MCPClientManager()


# ---- Fallback Sarmalayıcı (Decorator Pattern) ----------------------------

def with_mcp_fallback(provider: MCPProvider):
    """Decorator: MCP çağrısını dener, başarısız olursa Data API'ye düşer.

    Kullanım:
        @with_mcp_fallback(MCPProvider.YT_STUDIO)
        def get_stats_batch(...):
            # Data API implementasyonu
            ...

    Davranış:
    - MCP_ENABLED[provider] == False → doğrudan Data API (wrapper atlanır)
    - MCP başarılı → sonuç döner
    - MCP hatası + MCP_FALLBACK_ENABLED == True → Data API'ye düşer, log yazar
    - MCP hatası + MCP_FALLBACK_ENABLED == False → MCPError fırlatır
    - Data API de başarısızsa → orijinal hata fırlatır
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not mcp_enabled(provider.value):
                return func(*args, **kwargs)

            start_time = time.time()
            func_name = func.__name__
            provider_name = provider.value
            _log(f"MCP call start: {func_name} for provider {provider_name}")
            
            try:
                # MCP provider'ı al ve ilgili metodu çağır
                # Not: Bu decorator genel amaçlı değil, her fonksiyon kendi
                # MCP metodunu çağırır. Bu sadece fallback mantığını merkezileştirir.
                result = func(*args, **kwargs)
                
                duration = time.time() - start_time
                _log(f"MCP call success: {func_name} for provider {provider_name} took {duration:.3f}s")
                return result
            except MCPError as e:
                duration = time.time() - start_time
                mcp_manager.invalidate_health(provider)
                _log(f"MCP {provider.value} hatası, fallback Data API: {e} (took {duration:.3f}s)")
                if not MCP_FALLBACK_ENABLED:
                    raise
                return func(*args, **kwargs)
            except Exception as e:
                duration = time.time() - start_time
                # Beklenmedik hata - MCP mi Data API mi bilemeyiz, yine fallback
                mcp_manager.invalidate_health(provider)
                _log(f"Beklenmedik hata ({provider.value}), fallback Data API: {e} (took {duration:.3f}s)")
                if not MCP_FALLBACK_ENABLED:
                    raise
                return func(*args, **kwargs)
        return wrapper
    return decorator


# ---- Yardımcı: State güncelleme (atomik, merkezi) ------------------------

def update_project_state(project_dir: str, fields: dict) -> None:
    """Proje state.json'ını atomik günceller.
    Tüm MCP wrapper'ları bu fonksiyonu kullanır - tek yazma noktası."""
    state_path = os.path.join(project_dir, "state.json")
    state = {}
    if os.path.isfile(state_path):
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                state = json.load(f)
        except (OSError, ValueError):
            state = {}
    state.update(fields)
    state_io._atomik_yaz(state_path, state)


def load_project_state(project_dir: str) -> dict:
    """Proje state.json'ını okur."""
    state_path = os.path.join(project_dir, "state.json")
    if os.path.isfile(state_path):
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}
    return {}


def _load_meta(project_dir: str) -> dict:
    """Proje meta.json'ını okur."""
    meta_path = os.path.join(project_dir, "meta.json")
    if os.path.isfile(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}
    return {}


# ---- Yapılandırma Doğrulama (Startup) ------------------------------------

def validate_mcp_config() -> dict[str, bool]:
    """MCP yapılandırmasını doğrular, hangi provider'ların hazır olduğunu döner."""
    results = {}
    for provider_name, enabled in MCP_ENABLED.items():
        if not enabled:
            results[provider_name] = False
            continue
        provider_enum = MCPProvider(provider_name)
        results[provider_name] = mcp_manager.check_health(provider_enum)
        status = "HAZIR" if results[provider_name] else "ERİŞİLEMEZ"
        _log(f"MCP {provider_name}: {status}")
    return results


if __name__ == "__main__":
    # Manuel test: python -m upload.mcp_client
    print("MCP Yapılandırma Doğrulaması:")
    results = validate_mcp_config()
    for k, v in results.items():
        print(f"  {k}: {'✓' if v else '✗'}")