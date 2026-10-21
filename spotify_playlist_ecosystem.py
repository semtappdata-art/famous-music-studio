"""Spotify Playlist Ecosystem — P2 #16

Anjunadeep doktrini: "Önce kendi pazarını büyüt, sonra editörel kapıları çal."
4 ana playlist + haftalık güncelleme + cross-promo.
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import config


# Spotify playlist konfigürasyonu
SPOTIFY_PLAYLISTS = {
    "city_pulse": {
        "name": "City Pulse Sessions",
        "description": "Melodic techno & progressive house from the world's most iconic rooftops. Curated by DJ Famous.",
        "tags": ["melodic techno", "progressive house", "rooftop", "cityscape"],
        "update_schedule": "biweekly_friday",
        "max_tracks": 50,
        "cover_art": "auto",  # series thumbnail'dan
        "public": True,
        "collaborative": False
    },
    "night_drive": {
        "name": "Night Drive Series",
        "description": "Cinematic melodic techno for late night drives. Dashboard POV meets cinematic landscapes.",
        "tags": ["melodic techno", "night drive", "driving music", "progressive house"],
        "update_schedule": "monthly_last_friday",
        "max_tracks": 40,
        "cover_art": "auto",
        "public": True,
        "collaborative": False
    },
    "deep_focus": {
        "name": "Deep Focus Sessions",
        "description": "Organic house & melodic techno for focus, meditation & morning rituals. Nature immersive.",
        "tags": ["organic house", "deep house", "focus music", "ambient", "meditation"],
        "update_schedule": "monthly_first_friday",
        "max_tracks": 30,
        "cover_art": "auto",
        "public": True,
        "collaborative": False
    },
    "dj_famous_essentials": {
        "name": "DJ Famous Essentials",
        "description": "Complete discography: All DJ Famous tracks, sets & collaborations. Chronological journey.",
        "tags": ["dj famous", "discography", "melodic techno", "progressive house", "organic house"],
        "update_schedule": "weekly_monday",
        "max_tracks": 100,
        "cover_art": "brand",  # DJ Famous logo
        "public": True,
        "collaborative": False
    }
}


@dataclass
class PlaylistTrack:
    """Playlist parçası."""
    track_id: str  # Spotify track ID
    title: str
    artist: str
    added_at: str
    position: int = 0
    is_own: bool = True  # Kendi parçamız mı
    source_project: str = ""  # Hangi proje


@dataclass
class PlaylistState:
    """Playlist durumu."""
    playlist_key: str
    name: str
    playlist_id: str = ""  # Spotify playlist ID
    tracks: List[Dict] = field(default_factory=list)
    last_updated: str = ""
    total_tracks: int = 0
    last_synced: str = ""


class SpotifyPlaylistManager:
    """Spotify playlist ekosistem yöneticisi."""
    
    def __init__(self, config_path: str = "spotify_playlists.json"):
        self.config_path = Path(config_path)
        self.playlists_file = Path("spotify_playlists_state.json")
        self._load_state()
    
    def _load_state(self):
        if self.playlists_file.exists():
            with open(self.playlists_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.playlists = {k: PlaylistState(**v) for k, v in data.get("playlists", {}).items()}
        else:
            self.playlists = {}
            for key, config in SPOTIFY_PLAYLISTS.items():
                self.playlists[key] = PlaylistState(
                    playlist_key=key,
                    name=config["name"],
                    tracks=[],
                    last_updated="",
                    total_tracks=0,
                    last_synced=""
                )
        self._save_state()
    
    def _save_state(self):
        data = {
            "playlists": {k: {
                "playlist_key": v.playlist_key,
                "playlist_id": v.playlist_id,
                "name": v.name,
                "tracks": v.tracks,
                "last_updated": v.last_updated,
                "total_tracks": v.total_tracks,
                "last_synced": v.last_synced
            } for k, v in self.playlists.items()}
        }
        with open(self.playlists_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def register_playlist(self, playlist_key: str, spotify_playlist_id: str) -> bool:
        """Spotify playlist ID'sini kaydet."""
        if spotify_key in SPOTIFY_PLAYLISTS:
            if spotify_key not in self.playlists:
                self.playlists[spotify_key] = PlaylistState(
                    playlist_key=key,
                    name=SPOTIFY_PLAYLISTS[key]["name"]
                )
            self.playlists[key].playlist_id = spotify_playlist_id
            self._save_state()
            return True
        return False
    
    def add_track_to_playlist(self, playlist_key: str, track: Dict) -> bool:
        """Parça ekle (kendi parçamız + referral)."""
        if playlist_key not in self.playlists:
            return False
        
        playlist = self.playlists[key]
        track_entry = {
            "track_id": track.get("spotify_id", ""),
            "title": track.get("title", ""),
            "artist": track.get("artist", "DJ Famous"),
            "added_at": datetime.now().isoformat(),
            "position": len(playlist.tracks),
            "is_own": True,
            "source_project": track.get("project_dir", "")
        }
        
        # Duplicate kontrolü
        if any(t["track_id"] == track_entry["track_id"] for t in playlist.tracks):
            return False
        
        playlist.tracks.append(track_entry)
        playlist.total_tracks = len(playlist.tracks)
        playlist.last_updated = datetime.now().isoformat()
        self._save_state()
        return True
    
    def sync_from_distrokid(self, distrokid_data: List[Dict]) -> int:
        """DistroKid'den yeni parçaları al ve playlist'lere ekle."""
        added = 0
        for track in distrokid_data:
            # Track türüne göre playlist'e ekle
            genre = track.get("genre", "").lower()
            target_playlists = []
            
            if any(g in genre for g in ["melodic techno", "progressive house"]):
                target_playlists.append("city_pulse")
            if "organic" in genre or "ambient" in genre:
                target_playlists.append("deep_focus")
            if "night" in genre or "driving" in genre:
                target_playlists.append("night_drive")
            
            # Her zaman essentials'e ekle
            target_playlists.append("dj_famous_essentials")
            
            for playlist_key in set(target_playlists):
                track_data = {
                    "spotify_id": track.get("spotify_id", ""),
                    "title": track.get("title", ""),
                    "artist": "DJ Famous",
                    "project_dir": track.get("project_dir", "")
                }
                if self.add_track_to_playlist(playlist_key, track_data):
                    added += 1
        
        return added
    
    def get_playlist_for_description(self, playlist_key: str) -> str:
        """Playlist açıklaması için markdown formatında track listesi."""
        if playlist_key not in self.playlists:
            return ""
        
        playlist = self.playlists[key]
        config = SPOTIFY_PLAYLISTS[key]
        
        lines = [
            f"# {config['name']}",
            "",
            config["description"],
            "",
            f"🎧 {len(playlist.tracks)} tracks • Last updated: {playlist.last_updated[:10]}",
            ""
        ]
        
        for i, track in enumerate(playlist.tracks[-20:], 1):  # Son 20
            lines.append(f"{i}. {track['title']} - {track['artist']}")
        
        lines.extend([
            "",
            f"🎵 Full playlist: https://open.spotify.com/playlist/{self.playlists[key].playlist_id}",
            f"🎧 Follow for updates: {config.YOUTUBE_HANDLE}",
            f"#{config['tags'][0].replace(' ', '')} #{config['tags'][1].replace(' ', '')} #DJFamous"
        ])
        
        return "\n".join(lines)
    
    def get_cross_promo_data(self) -> Dict:
        """Cross-promo verisi (diğer playlist'lerin linkleri)."""
        return {
            "playlists": {
                k: {
                    "name": v.name,
                    "url": f"https://open.spotify.com/playlist/{v.playlist_id}",
                    "track_count": v.total_tracks
                }
                for k, v in self.playlists.items() if v.playlist_id
            }
        }


# Anjunadeep-style: Kendi playlist'ini önce büyüt
def bootstrap_playlists():
    """Playlist'leri oluştur ve ID'leri kaydet."""
    manager = SpotifyPlaylistManager()
    
    print("🎵 Spotify Playlist Ecosystem - Bootstrap")
    print("=" * 50)
    
    for key, config in SPOTIFY_PLAYLISTS.items():
        print(f"\n📋 {config['name']} ({key})")
        print(f"   Tags: {', '.join(config['tags'])}")
        print(f"   Schedule: {config['update_schedule']}")
        print(f"   Max tracks: {config['max_tracks']}")
        
        # Kullanıcıdan playlist ID al
        playlist_id = input(f"   Spotify Playlist ID (boş = atla): ").strip()
        if playlist_id:
            SpotifyPlaylistManager().register_playlist(key, playlist_id)
            print(f"   ✅ Registered: {playlist_id}")
        else:
            print("   ⏭️  Skipped")
    
    print("\n✅ Bootstrap complete!")
    print("Next: Run sync_from_distrokid() after DistroKid release")


# Auto-sync scheduler
class PlaylistSyncScheduler:
    """Playlist senkronizasyon zamanlayıcısı."""
    
    def __init__(self):
        self.manager = SpotifyPlaylistManager()
    
    def should_update(self, playlist_key: str) -> bool:
        """Güncelleme zamanı mı?"""
        if playlist_key not in SPOTIFY_PLAYLISTS:
            return False
        
        schedule = SPOTIFY_PLAYLISTS[key]["update_schedule"]
        playlist = SpotifyPlaylistManager().playlists.get(key)
        
        if not playlist or not playlist.last_synced:
            return True
        
        last_sync = datetime.fromisoformat(playlist.last_synced)
        now = datetime.now()
        
        if "weekly" in schedule:
            return (datetime.now() - last_sync).days >= 7
        elif "biweekly" in schedule:
            return (datetime.now() - last_sync).days >= 14
        elif "monthly" in schedule:
            return (now - last_sync).days >= 30
        
        return False
    
    def run_scheduled_sync(self) -> Dict[str, int]:
        """Zamanı gelen playlist'leri senkronize et."""
        results = {}
        for key in SPOTIFY_PLAYLISTS:
            if self.should_update(key):
                # Gerçek implementasyonda: DistroKid/Spotify API'dan yeni track'leri çek
                # Şimdilik mock
                print(f"🔄 Syncing {key}...")
                results[key] = 0  # mock
        return results


# CLI
async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Spotify Playlist Ecosystem Manager")
    parser.add_argument("--bootstrap", action="store_true", help="Playlist'leri bootstrap et")
    parser.add_argument("--sync", action="store_true", help="Senklonize et")
    parser.add_argument("--register", nargs=2, metavar=("KEY", "PLAYLIST_ID"), help="Playlist ID kaydet")
    parser.add_argument("--describe", help="Playlist açıklaması üret")
    args = parser.parse_args()
    
    manager = SpotifyPlaylistManager()
    
    if args.bootstrap:
        bootstrap_playlists()
    elif args.sync:
        scheduler = PlaylistSyncScheduler()
        results = scheduler.run_scheduled_sync()
        print(f"Sync results: {results}")
    elif args.register:
        key, pid = args.register
        if SpotifyPlaylistManager().register_playlist(key, pid):
            print(f"✅ Registered {key}: {pid}")
        else:
            print("❌ Invalid key")
    elif args.describe:
        desc = SpotifyPlaylistManager().get_playlist_for_description(args.describe)
        print(desc)
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())