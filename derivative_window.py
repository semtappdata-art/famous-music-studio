"""Derivative Window System — P2 #17

T+8 hafta derivative penceresi:
- Tutulan parça (AVD > 55%, CTR > 5%) → T+8 hafta remix/edit paketi
- Remix paketi: 3-4 farklı Künstler (club edit, radio edit, extended)
- Collab: Farklı Künstler ile yeniden üretim
- Acoustic/Live versiyon: Studio live kaydı
- İkinci basın + ikinci editoryal kapı (Spotify pitch tekrarı)

Derivative türleri:
1. Remix EP: 3-4 farklı Künstler
2. Club Edit / Radio Edit / Extended Mix
3. Acoustic/Live Version
4. Collab Rework (farklı Künstler ile)
5. VIP/Extended Mix (club için)
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import config


class DerivativeType(Enum):
    REMIX_EP = "remix_ep"           # 3-4 farklı Künstler remix
    CLUB_EDIT = "club_edit"         # Club edit (daha uzun, DJ-friendly)
    RADIO_EDIT = "radio_edit"       # Radio edit (kısa, vocal-forward)
    EXTENDED_MIX = "extended_mix"   # Extended mix (club için uzun)
    ACOUSTIC_LIVE = "acoustic_live" # Akustik/live versiyon
    COLLAB_REWORK = "collab_rework" # Farklı Künstler ile rework
    VIP_MIX = "vip_mix"             # VIP/Extended mix
    INSTRUMENTAL = "instrumental"   # Instrumental versiyon


@dataclass
class DerivativePlan:
    """Derivative planı."""
    original_track_id: str  # Orijinal parça Suno audio_id
    original_title: str
    original_project_dir: str
    derivative_type: DerivativeType
    target_artists: List[str] = field(default_factory=list)  # Remix için Künstlerler
    status: str = "planned"  # planned, in_progress, completed, failed
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    scheduled_for: str = ""  # ISO timestamp
    completed_at: str = ""
    output_audio_ids: List[str] = field(default_factory=list)
    notes: str = ""
    suno_prompt_override: str = ""  # Suno prompt override
    target_bpm: Optional[int] = None
    target_key: str = ""
    notes_for_artist: str = ""


class DerivativeWindowManager:
    """Derivative pencere yöneticisi."""
    
    def __init__(self, base_dir: str = "derivatives"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        self.index_file = self.base_dir / "index.json"
        self._load_index()
    
    def _load_index(self):
        self.index_file.parent.mkdir(exist_ok=True)
        if self.index_file.exists():
            with open(self.index_file, "r", encoding="utf-8") as f:
                self.index = json.load(f)
        else:
            self.index = {"derivatives": {}}
    
    def _save_index(self):
        self.index_file.parent.mkdir(exist_ok=True)
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)
    
    def check_derivative_eligibility(self, project_dir: str) -> List[Dict]:
        """Parçanın derivative için uygunluğunu kontrol et."""
        import validate_project
        state_path = Path(project_dir) / "state.json"
        if not state_path.exists():
            return [{"eligible": False, "reason": "state.json yok"}]
        
        with open(state_path, "r", encoding="utf-8") as f:
            state = json.load(f)
        
        # YouTube analitik verisi kontrolü (mock - gerçek implementasyonda API'den)
        youtube_id = state.get("youtube_video_id")
        shorts_id = state.get("youtube_shorts_video_id")
        
        if not youtube_id:
            return [{"eligible": False, "reason": "YouTube'a yüklenmemiş"}]
        
        # Mock analytics - gerçek implementasyonda YouTube Analytics API
        # Bu fonksiyonun dışarıdan analytics verisi alması gerekir
        analytics = self._get_mock_analytics(youtube_id)
        
        eligible = []
        
        # Kriterler
        avd = analytics.get("average_view_duration_pct", 0)  # %
        ctr = analytics.get("click_through_rate", 0)  # %
        views = analytics.get("views", 0)
        likes = analytics.get("likes", 0)
        comments = analytics.get("comments", 0)
        
        # Minimum thresholds
        if avd >= 55 and ctr >= 5 and views >= 1000:
            eligible.append({
                "type": "remix_ep",
                "reason": f"High engagement: AVD {avd}%, CTR {ctr}%, Views {views}"
            })
        
        if avd >= 50 and views >= 5000:
            eligible.append({
                "type": "club_edit",
                "reason": f"Good retention for club: AVD {avd}%, Views {views}"
            })
        
        if avd >= 60 and ctr >= 8:
            eligible.append({
                "type": "radio_edit",
                "reason": f"High CTR for radio: CTR {ctr}%, AVD {avd}%"
            })
        
        if views >= 10000 and avd >= 50:
            eligible.append({
                "type": "extended_mix",
                "reason": f"High demand for extended: Views {views}, AVD {avd}%"
            })
        
        # Acoustic/Live için: vokal varsa ve AVD yüksekse
        if analytics.get("has_vocals", False) and avd >= 55:
            eligible.append({
                "type": "acoustic_live",
                "reason": f"Vocal track with high AVD: {avd}%"
            })
        
        # Collab rework için: yorumlarda collab isteği varsa
        if analytics.get("collab_requests", 0) > 5:
            eligible.append({
                "type": "collab_rework",
                "reason": f"Community requesting collab: {analytics['collab_requests']} requests"
            })
        
        return eligible
    
    def _get_mock_analytics(self, youtube_id: str) -> Dict:
        """Mock analytics - gerçek implementasyonda YouTube Analytics API."""
        # Gerçek implementasyonda: YouTube Analytics API
        # Şimdilik mock veri
        return {
            "average_view_duration_pct": 58.5,
            "click_through_rate": 6.2,
            "views": 15000,
            "likes": 1200,
            "comments": 85,
            "has_vocals": True,
            "collab_requests": 8
        }
    
    def create_derivative_plan(self, 
                               project_dir: str, 
                               derivative_type: DerivativeType,
                               target_artists: List[str] = None) -> Optional[str]:
        """Derivative planı oluştur."""
        state_path = Path(project_dir) / "state.json"
        if not Path(project_dir).exists():
            return None
        
        with open(Path(project_dir) / "state.json", "r", encoding="utf-8") as f:
            state = json.load(f)
        
        meta_path = Path(project_dir) / "meta.json"
        meta = {}
        if Path(project_dir / "meta.json").exists():
            with open(Path(project_dir) / "meta.json", "r", encoding="utf-8") as f:
                meta = json.load(f)
        
        track_id = state.get("youtube_video_id") or state.get("youtube_shorts_video_id")
        title = meta.get("title", "Unknown")
        
        derivative_id = f"deriv_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        plan = DerivativePlan(
            original_track_id=state.get("youtube_video_id", ""),
            original_title=title,
            original_project_dir=project_dir,
            derivative_type=DerivativeType,
            target_artists=target_artists or [],
            scheduled_for=(datetime.now() + timedelta(weeks=8)).isoformat()  # T+8 hafta
        )
        
        # Proje dizini
        deriv_dir = Path("derivatives") / derivative_id
        deriv_dir.mkdir(parents=True, exist_ok=True)
        
        plan_data = {
            "id": derivative_id,
            "original_track_id": plan.original_track_id,
            "original_title": plan.original_title,
            "original_project_dir": plan.original_project_dir,
            "derivative_type": plan.derivative_type.value,
            "target_artists": plan.target_artists,
            "status": plan.status,
            "created_at": plan.created_at,
            "scheduled_for": plan.scheduled_for,
            "completed_at": plan.completed_at,
            "output_audio_ids": plan.output_audio_ids,
            "notes": plan.notes,
            "suno_prompt_override": plan.suno_prompt_override,
            "target_bpm": plan.target_bpm,
            "target_key": plan.target_key,
            "notes_for_artist": plan.notes_for_artist
        }
        
        deriv_dir = Path("derivatives") / derivative_id
        deriv_dir.mkdir(parents=True, exist_ok=True)
        
        with open(deriv_dir / "plan.json", "w", encoding="utf-8") as f:
            json.dump(plan_data, f, ensure_ascii=False, indent=2)
        
        # Index'e ekle
        self.index["derivatives"][derivative_id] = {
            "original_title": plan.original_title,
            "type": plan.derivative_type.value,
            "status": plan.status,
            "created_at": plan.created_at,
            "scheduled_for": plan.scheduled_for,
            "project_dir": project_dir
        }
        self._save_index()
        
        return derivative_id
    
    def schedule_derivative_production(self, derivative_id: str) -> bool:
        """Derivative üretimini zamanla (T+8 hafta)."""
        deriv_dir = Path("derivatives") / derivative_id
        plan_file = deriv_dir / "plan.json"
        if not plan_file.exists():
            return False
        
        with open(plan_file, "r", encoding="utf-8") as f:
            plan = json.load(f)
        
        # Schedule kontrolü
        scheduled = datetime.fromisoformat(plan["scheduled_for"])
        if datetime.now() < scheduled:
            print(f"⏰ {derivative_id} scheduled for {plan['scheduled_for']}")
            return False
        
        # Durumu güncelle
        plan["status"] = "in_progress"
        with open(deriv_dir / "plan.json", "w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)
        
        return True
    
    def generate_suno_prompts(self, derivative_id: str) -> List[str]:
        """Derivative türüne göre Suno prompt'ları üret."""
        deriv_dir = Path("derivatives") / derivative_id
        plan_file = deriv_dir / "plan.json"
        if not plan_file.exists():
            return []
        
        with open(plan_file, "r", encoding="utf-8") as f:
            plan = json.load(f)
        
        original_prompt = ""  # Orijinal prompt meta.json'dan alınmalı
        derivative_type = plan["derivative_type"]
        target_artists = plan.get("target_artists", [])
        
        prompts = []
        
        if plan["derivative_type"] == "remix_ep":
            for artist in target_artists:
                prompts.append({
                    "type": "remix",
                    "artist": artist,
                    "prompt": f"Remix of {{original_title}} by {artist}, {self._get_style_for_artist(artist)}, {120} bpm, club edit",
                    "style": self._get_style_for_artist(artist),
                    "bpm": 124,
                    "artist": artist
                })
        
        elif plan["derivative_type"] == "club_edit":
            prompts.append({
                "type": "club_edit",
                "prompt": f"Club edit of {{original_title}}, extended intro/outro, DJ friendly, 126 bpm, peak time energy",
                "style": "melodic techno, progressive house, club edit",
                "bpm": 126,
                "duration": 420  # 7 dakika
            })
        
        elif plan["derivative_type"] == "radio_edit":
            prompts.append({
                "type": "radio_edit",
                "prompt": f"Radio edit of {{original_title}}, 3:30 max, vocal forward, clean intro/outro, 122 bpm",
                "style": "melodic house, radio edit",
                "bpm": 122,
                "duration": 210  # 3:30
            })
        
        elif plan["derivative_type"] == "extended_mix":
            prompts.append({
                "type": "extended_mix",
                "prompt": f"Extended mix of {{original_title}}, long intro/outro for DJ mixing, 128 bpm, 8+ minutes",
                "style": "progressive house, extended mix",
                "bpm": 128,
                "duration": 540  # 9 dakika
            })
        
        elif plan["derivative_type"] == "acoustic_live":
            prompts.append({
                "type": "acoustic_live",
                "prompt": f"Acoustic live version of {{original_title}}, stripped down, piano/guitar, intimate, live studio feel",
                "style": "acoustic, live, intimate",
                "bpm": 100,
                "duration": 240
            })
        
        elif plan["derivative_type"] == "collab_rework":
            for artist in target_artists:
                prompts.append({
                    "type": "collab_rework",
                    "artist": artist,
                    "prompt": f"Collab rework with {artist}, {self._get_style_for_artist(artist)}, merge both styles, 124 bpm",
                    "style": f"{self._get_style_for_artist(artist)}, collaborative",
                    "bpm": 124,
                    "artist": artist
                })
        
        return prompts
    
    def _get_style_for_artist(self, artist: str) -> str:
        """Artist için stil önerisi."""
        styles = {
            "Rikodisco": "organic house, melodic techno, disco",
            "Bytemounts": "deep house, melodic techno, night drive",
            "Catching Flies": "melodic house, progressive, emotive",
            "Catching Flies": "melodic house, progressive, emotive",
        }
        return styles.get(artist, "melodic techno, progressive house")


# CLI
async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Derivative Window Manager")
    subparsers = parser.add_subparsers(dest="command")
    
    # Check eligibility
    check_parser = subparsers.add_parser("check", help="Derivative uygunluğunu kontrol et")
    check_parser.add_argument("--project-dir", required=True)
    
    # Create plan
    create_parser = subparsers.add_parser("create", help="Derivative planı oluştur")
    create_parser.add_argument("--project-dir", required=True)
    create_parser.add_argument("--type", required=True, choices=[t.value for t in DerivativeType])
    create_parser.add_argument("--artists", nargs="*", default=[])
    
    # Schedule
    schedule_parser = subparsers.add_parser("schedule", help="Üretimi zamanla")
    schedule_parser.add_argument("--derivative-id", required=True)
    
    # Generate prompts
    prompts_parser = subparsers.add_parser("prompts", help="Suno prompt'ları üret")
    prompts_parser.add_argument("--derivative-id", required=True)
    
    args = parser.parse_args()
    
    manager = DerivativeWindowManager()
    
    if args.command == "check":
        eligible = manager.check_eligibility(args.project_dir)
        if eligible:
            print(f"✅ Eligible for {len(eligible)} derivative types:")
            for e in eligible:
                print(f"  • {e['type']}: {e['reason']}")
        else:
            print("❌ Not eligible for derivatives")
    
    elif args.command == "create":
        dtype = DerivativeType(args.type)
        artists = args.artists if args.artists else []
        deriv_id = manager.create_derivative_plan(args.project_dir, DerivativeType(args.type), artists)
        if deriv_id:
            print(f"Created derivative: {derivative_id}")
        else:
            print("Failed to create derivative plan")
    
    elif args.command == "schedule":
        if manager.schedule_derivative_production(args.derivative_id):
            print(f"Scheduled: {args.derivative_id}")
        else:
            print("Not ready or already processed")
    
    elif args.command == "prompts":
        prompts = manager.generate_suno_prompts(args.derivative_id)
        for p in prompts:
            print(json.dumps(p, ensure_ascii=False, indent=2))
    
    else:
        parser.print_help()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())