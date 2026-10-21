"""Sanal Lokasyon Sistemi — P2 #13

Cercle modelini 'sanal lokasyon + AI şeffaflığı' ile ölçeklenebilir hale getirir.
Gerçek drone/ekip maliyeti olmadan `art_query` + Pexels/Unsplash + `DJ_SERIES` şablonları ile
"Virtual Istanbul Rooftop", "Virtual Cappadocia Sunrise" hikayeleri üretir.

Kaynak: config.py -> DJ_SERIES, SERIES_THUMBNAIL_TEMPLATES, stock_art.py
"""

import os
import json
import random
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime

import config


@dataclass
class VirtualLocation:
    """Sanal lokasyon tanımı."""
    series_key: str
    episode: int
    city: str
    country: str
    landmark: str
    gps: str
    story: str
    story_tr: str
    art_query: str
    visual_concept: str  # "drone_establishing -> rooftop_dj -> city_timelapse"
    thumbnail_concept: str  # "artist_silhouette + landmark + series_logo"
    scheduled_date: Optional[str] = None  # ISO format
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class VirtualLocationManager:
    """Sanal lokasyon yöneticisi — DJ_SERIES config'ten üretir."""
    
    def __init__(self):
        self.locations_dir = Path("virtual_locations")
        self.locations_dir.mkdir(exist_ok=True)
        self.index_file = self.locations_dir / "index.json"
        self._load_index()
    
    def _load_index(self):
        if self.index_file.exists():
            with open(self.index_file, "r", encoding="utf-8") as f:
                self.index = json.load(f)
        else:
            self.index = {"locations": [], "next_episode": {}}
    
    def _save_index(self):
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)
    
    def generate_locations_for_series(self, series_key: str, count: int = 10) -> List[VirtualLocation]:
        """DJ_SERIES config'ten sanal lokasyonlar üretir."""
        series = config.DJ_SERIES.get(series_key)
        if not series:
            raise ValueError(f"Series not found: {series_key}")
        
        locations_config = series.get("locations", [])
        if not locations_config:
            raise ValueError(f"No locations defined for series: {series_key}")
        
        locations = []
        next_ep = self.index["next_episode"].get(series_key, 1)
        
        for i in range(count):
            loc_idx = i % len(locations_config)
            loc = locations_config[loc_idx]
            ep = next_ep + i
            
            vl = VirtualLocation(
                series_key=series_key,
                episode=ep,
                city=loc["city"],
                country=loc["country"],
                landmark=loc.get("landmark", loc["city"]),
                gps=loc.get("gps", ""),
                story=loc.get("story", ""),
                story_tr=loc.get("story_tr", ""),
                art_query=loc.get("art_query", config.DJ_SERIES[series_key].get("art_query", "")),
                visual_concept=series.get("visual_theme", "cinematic"),
                thumbnail_concept=series.get("thumbnail_template", "artist_silhouette + landmark + logo"),
                scheduled_date=self._next_scheduled_date(series, ep)
            )
            locations.append(vl)
        
        # Index güncelle
        self.index["next_episode"][series_key] = next_ep + count
        self._save_index()
        
        # Her lokasyon için ayrı dosya
        for vl in locations:
            self._save_location(vl)
        
        return locations
    
    def _next_scheduled_date(self, series: dict, episode: int) -> str:
        """Seri takvimine göre bir sonraki yayın tarihi."""
        import datetime
        schedule = series.get("schedule", "biweekly_friday_18:00_tr")
        # Basit implementasyon: iki haftada bir Cuma
        base = datetime.datetime(2026, 1, 2)  # İlk Cuma
        delta_weeks = (episode - 1) * 2
        scheduled = base + datetime.timedelta(weeks=delta_weeks)
        return scheduled.replace(hour=18, minute=0).isoformat()
    
    def _save_location(self, vl: VirtualLocation):
        """Lokasyonu JSON dosyası olarak kaydet."""
        filename = f"{vl.series_key}_ep{vl.episode:02d}.json"
        path = self.locations_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "series_key": vl.series_key,
                "episode": vl.episode,
                "city": vl.city,
                "country": vl.country,
                "landmark": vl.landmark,
                "gps": vl.gps,
                "story": vl.story,
                "story_tr": vl.story_tr,
                "art_query": vl.art_query,
                "visual_concept": vl.visual_concept,
                "thumbnail_concept": vl.thumbnail_concept,
                "scheduled_date": vl.scheduled_date,
                "created_at": vl.created_at
            }, f, ensure_ascii=False, indent=2)
    
    def get_location(self, series_key: str, episode: int) -> Optional[VirtualLocation]:
        """Kaydedilmiş lokasyonu yükle."""
        filename = f"{series_key}_ep{episode:02d}.json"
        path = self.locations_dir / filename
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return VirtualLocation(**data)
    
    def get_next_location(self, series_key: str) -> Optional[VirtualLocation]:
        """Bir sonraki episod için lokasyon."""
        next_ep = self.index["next_episode"].get(series_key, 1)
        return self.get_location(series_key, next_ep)


class VirtualLocationRenderer:
    """Sanal lokasyon görsellerini üretir (cover_generator + stock_art entegrasyonu)."""
    
    def __init__(self):
        self.vlm = VirtualLocationManager()
    
    def render_location_assets(self, vl: VirtualLocation, project_dir: str) -> bool:
        """Lokasyon için kapak, art, thumbnail üretir."""
        from cover_generator import generate as generate_cover
        import cover_generator
        
        # Geçici meta oluştur
        meta = {
            "title": f"{config.DJ_SERIES[vl.series_key]['brand']} Ep{vl.episode:02d}",
            "series": vl.series_key,
            "episode": vl.episode,
            "theme": "dj",
            "location": {
                "city": vl.city,
                "country": vl.country,
                "landmark": vl.landmark,
                "gps": vl.gps,
                "story": vl.story,
                "story_tr": vl.story_tr
            },
            "art_query": vl.art_query,
            "visual_concept": vl.visual_concept,
            "thumbnail_concept": vl.thumbnail_concept,
            "series": vl.series_key
        }
        
        # Proje dizini hazırla
        project_path = Path("dj_sets") / f"{vl.series_key}_Ep{vl.episode:02d}_{vl.city.replace(' ', '_')}"
        project_path.mkdir(parents=True, exist_ok=True)
        
        meta_path = Path(project_dir) / "meta.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        
        # Kapak üret (series-based thumbnail + landmark silüeti)
        try:
            cover_generator.generate(str(project_path))
            return True
        except Exception as e:
            print(f"Cover generation failed: {e}")
            return False
    
    def generate_location_story_assets(self, vl: VirtualLocation, project_dir: str) -> Dict[str, str]:
        """Lokasyon hikayesi için görsel/ metin assetleri."""
        assets = {}
        
        # Story card (Instagram/Bluesky için)
        story_card = f"""
📍 {vl.landmark}, {vl.city}, {vl.country}
📅 Episode {vl.episode} - {vl.city} Sessions

{vl.story_tr}

📍 GPS: {vl.gps}
#DJFamous #{vl.series_key.replace('_', '').title()} #ElectronicMusic
"""
        assets["story_card_tr"] = story_card.strip()
        assets["story_card_en"] = story_card.replace(vl.story_tr, vl.story).strip()
        
        # GPS QR kod komutu
        assets["gps_qr_command"] = f"qrencode -o gps_qr.png '{vl.gps}'"
        
        return assets


# CLI
async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Virtual Location Manager")
    parser.add_argument("--series", required=True, help="Series key (city_pulse, deep_focus, night_drive, boiler_room_style)")
    parser.add_argument("--count", type=int, default=10, help="Kaç lokasyon üretilecek")
    parser.add_argument("--render", action="store_true", help="Kapak/asset üret")
    args = parser.parse_args()
    
    vlm = VirtualLocationManager()
    locations = vlm.generate_locations_for_series(args.series, args.count)
    
    print(f"Generated {len(locations)} locations for {args.series}:")
    for vl in locations:
        print(f"  Ep{vl.episode:02d}: {vl.landmark}, {vl.city}, {vl.country}")
        print(f"    Scheduled: {vl.scheduled_date}")
        print(f"    Art query: {vl.art_query[:60]}...")
    
    if args.render:
        print("\nRendering assets...")
        renderer = VirtualLocationRenderer()
        for vl in locations:
            project_dir = f"dj_sets/{vl.series_key}_Ep{vl.episode:02d}_{vl.city.replace(' ', '_')}"
            if vlm.render_location_assets(vl, project_dir):
                assets = vlm.generate_location_story_assets(vl, project_dir)
                print(f"  ✅ {vl.series_key}_Ep{vl.episode:02d} - Assets ready")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())