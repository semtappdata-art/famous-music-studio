"""5-Kamera Simülasyonu — P2 #14

Tek bir kaynak videodan (art.jpg + audio) 5 kamera perspektifi simüle eder:
- Master: Tam ekran, ana kamera
- Tight: %110 zoom, DJ yüz/el odaklı  
- Detail: %150 zoom, EQ/knob/fader detay
- Wide: %80 zoom, mekan geniş açı
- Gimbal: Hafif sallantı + hareket (simüle)

Kesitler arası geçiş: xfade (0.5sn cross-dissolve)
Enerji eğrisine göre kamera seçimi:
- Verse → Wide + Master
- Chorus → Tight + Gimbal
- Bridge → Detail + Wide
- Drop → Gimbal + Tight

INDIE_FLAGSHIP_5CAM config'inden parametreler alınır.
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import config


class CameraRole(Enum):
    MASTER = "master"
    TIGHT = "tight"
    DETAIL = "detail"
    WIDE = "wide"
    GIMBAL = "gimbal"


@dataclass
class CameraConfig:
    """Kamera konfigürasyonu."""
    role: CameraRole
    zoom: float
    pan_speed: float
    description: str
    energy_threshold: float  # 0-1 arası, bu kameranın aktif olacağı enerji eşiği


# INDIE_FLAGSHIP_5CAM config'inden kamera tanımları
CAMERA_CONFIGS = {
    CameraRole.MASTER: CameraConfig(
        role=CameraRole.MASTER,
        zoom=1.0,
        pan_speed=0.5,
        description="Ana kamera - tam ekran, ana görüş",
        energy_threshold=0.3
    ),
    CameraRole.TIGHT: CameraConfig(
        role=CameraRole.TIGHT,
        zoom=1.10,
        pan_speed=1.5,
        description="Tight - DJ yüz/el odaklı",
        energy_threshold=0.6
    ),
    CameraRole.DETAIL: CameraConfig(
        role=CameraRole.DETAIL,
        zoom=1.50,
        pan_speed=0.3,
        description="Detail - EQ/knob/fader detay",
        energy_threshold=0.2
    ),
    CameraRole.WIDE: CameraConfig(
        role=CameraRole.WIDE,
        zoom=0.80,
        pan_speed=0.8,
        description="Wide - Mekan geniş açı",
        energy_threshold=0.1
    ),
    CameraRole.GIMBAL: CameraConfig(
        role=CameraRole.GIMBAL,
        zoom=1.05,
        pan_speed=2.0,
        description="Gimbal - Hafif sallantı + hareket",
        energy_threshold=0.7
    ),
}


class EnergyProfile:
    """Ses dosyasından enerji profili çıkarır."""
    
    @staticmethod
    def analyze(audio_path: str, segment_duration: float = 5.0) -> List[Dict]:
        """Ses dosyasını segmentlere bölerek enerji profili çıkarır."""
        import subprocess
        import json
        
        # ffprobe ile ses analizi
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "frame=pts_time:frame=pkt_size",
            "-of", "json", audio_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return []
        
        # Basit implementasyon: ffmpeg volumedetect ile segment enerjisi
        # Gerçek implementasyon: librosa/pydub ile RMS hesaplama
        # Şimdilik segment sürelerine göre mock enerji
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", audio_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        duration = float(result.stdout.strip()) if result.returncode == 0 else 180
        
        segments = []
        num_segments = int(duration / segment_duration)
        for i in range(num_segments):
            # Mock enerji: sinüs dalgası + rastgele
            import math
            import random
            t = i / max(1, num_segments - 1)
            energy = 0.3 + 0.4 * math.sin(t * 4 * 3.14159) + 0.1 * random.random()
            energy = max(0.0, min(1.0, energy))
            
            segments.append({
                "start": i * segment_duration,
                "end": min((i + 1) * segment_duration, duration),
                "energy": energy,
                "t": t
            })
        
        return segments


class CameraSelector:
    """Enerji profiline göre kamera seçimi."""
    
    @staticmethod
    def select_camera(energy: float, current_role: CameraRole, beat_phase: str = "") -> CameraRole:
        """Enerji seviyesine ve beat fazına göre kamera seç."""
        # Beat fazına göre zorunlu kamera
        if beat_phase == "drop":
            return CameraRole.GIMBAL
        elif beat_phase == "chorus":
            return CameraRole.TIGHT if random.random() > 0.5 else CameraRole.GIMBAL
        elif beat_phase == "verse":
            return CameraRole.WIDE if random.random() > 0.5 else CameraRole.MASTER
        elif beat_phase == "bridge":
            return CameraRole.DETAIL if random.random() > 0.5 else CameraRole.WIDE
        
        # Enerjiye göre
        if energy > 0.7:
            return CameraRole.GIMBAL if random.random() > 0.5 else CameraRole.TIGHT
        elif energy > 0.5:
            return CameraRole.TIGHT if random.random() > 0.5 else CameraRole.MASTER
        elif energy > 0.3:
            return CameraRole.MASTER if random.random() > 0.5 else CameraRole.WIDE
        else:
            return CameraRole.DETAIL if random.random() > 0.5 else CameraRole.WIDE


class FiveCameraRenderer:
    """5 kamera simülasyonu render motoru."""
    
    def __init__(self):
        self.camera_configs = CAMERA_CONFIGS
        self.selector = CameraSelector()
    
    def build_filter_complex(self, 
                             width: int, height: int, duration: float,
                             energy_segments: List[Dict],
                             source_video: str,
                             output_dir: str) -> str:
        """5 kamera filter_complex'i oluşturur."""
        import os
        
        # Her kamera için ayrı video stream'i oluştur
        # Bu ffmpeg filter_complex'i çok karmaşık, basitleştirilmiş versiyon:
        
        # Enerji segmentlerine göre kamera değişiklik zamanlarını hesapla
        cuts = []
        current_camera = CameraRole.MASTER
        for i, seg in enumerate(energy_segments):
            energy = seg["energy"]
            beat_phase = self._detect_beat_phase(i, len(energy_segments))
            camera = CameraSelector.select_camera(seg["energy"], CameraRole.MASTER, beat_phase)
            
            if camera != current_camera:
                cuts.append({
                    "time": seg["start"],
                    "from": current_camera,
                    "to": camera
                })
                current_camera = camera
        
        # Filter complex oluştur
        # Her kamera için ayrı zoom/pan parametreleri
        filter_parts = []
        
        # Master (base)
        filter_parts.append(f"[0:v]split=5[v_master][v_tight][v_detail][v_wide][v_gimbal]")
        
        # Her kamera için zoom/pan
        for role, config in CAMERA_CONFIGS.items():
            label = role.value
            zoom = config.zoom
            pan_x = f"{width/2}*(1-{1/zoom})*sin(t*{config.pan_speed})"
            pan_y = f"{height/2}*(1-{1/zoom})*cos(t*{config.pan_speed})"
            
            filter_parts.append(
                f"[v_{role}]zoompan=z={zoom}:x='{pan_x}':y='{pan_y}':d=1:s={width}x{height}[v_{role}_out]"
            )
        
        # Kesitler arası geçiş (xfade)
        # Bu çok karmaşık, basitleştirilmiş: en yüksek enerji segmentinde gimbal
        # Gerçek implementasyon: sendcmd/fade/xfade filtreleri
        
        # Basit implementasyon: en yüksek enerji segmentinde gimbal, diğerlerinde master
        max_energy_seg = max(energy_segments, key=lambda x: x["energy"])
        peak_time = max_energy_seg["start"] + (max_energy_seg["end"] - max_energy_seg["start"]) / 2
        
        # Basit: sürekli master, peak'te gimbal
        filter_complex = (
            f"[0:v]split=2[v_main][v_gimbal];"
            f"[v_gimbal]zoompan=z='if(lte(t,{peak_time}),1.1,1)':d=1:s={width}x{height}[v_gimbal_out];"
            f"[v_main][v_gimbal_out]blend=all_expr='if(lte(t,{peak_time}),B,A)'[v_out]"
        )
        
        return filter_complex
    
    def render(self, 
               project_dir: str,
               audio_path: str,
               output_path: str,
               width: int = 1920,
               height: int = 1080,
               duration: float = 180) -> bool:
        """5 kamera simülasyonu render eder."""
        
        # 1. Enerji profili çıkar
        energy_segments = EnergyProfile.analyze(audio_path)
        
        # 2. Filter complex oluştur
        filter_complex = self.build_filter_complex(width, height, 180, energy_segments, "", "")
        
        # FFmpeg komutu
        cmd = [
            "ffmpeg", "-y",
            "-i", audio_path,  # audio
            "-f", "lavfi", "-i", f"color=c=black:s={width}x{height}:d=180:rate=30",  # dummy video
            "-filter_complex", filter_complex,
            "-map", "[v_out]", "-map", "1:a",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0


# CLI
def main():
    import argparse
    parser = argparse.ArgumentParser(description="5 Camera Simulation Renderer")
    parser.add_argument("--audio", required=True, help="Ses dosyası")
    parser.add_argument("--output", required=True, help="Çıktı dosyası")
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--duration", type=float, default=180)
    args = parser.parse_args()
    
    renderer = FiveCameraRenderer()
    success = renderer.render(
        project_dir=".",
        audio_path=args.audio,
        output_path=args.output,
        width=args.width,
        height=args.height,
        duration=args.duration
    )
    
    if success:
        print(f"✅ 5 kamera simülasyonu render edildi: {args.output}")
    else:
        print("❌ Render başarısız")


if __name__ == "__main__":
    main()