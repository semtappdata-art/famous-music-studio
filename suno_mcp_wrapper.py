"""Suno MCP Wrapper — Mevcut suno_producer.py / yeni_parca.py ile entegre."""

import asyncio
from typing import Optional, List
from dataclasses import dataclass, field

@dataclass
class SunoResult:
    task_id: str = ""
    audio_id: Optional[str] = None
    status: str = "pending"
    audio_url: Optional[str] = None
    title: Optional[str] = None
    lyrics: Optional[str] = None
    duration: Optional[float] = None
    style_tags: Optional[str] = None
    error: Optional[str] = None

class SunoMCP:
    """Suno MCP tool'larını sarmalayan async wrapper."""
    
    def __init__(self):
        self._tools = None
    
    async def _get_tools(self):
        if self._tools is None:
            import sys
            sys.path.insert(0, ".")
            from tools import mcp__suno
            self._tools = mcp__suno
        return self._tools
    
    # 1. Referans vibe al (Inspo)
    async def inspo(self, audio_urls: List[str], prompt: str, style: str,
                    audio_weight: float = 0.6, model: str = "chirp-v5-5") -> SunoResult:
        tools = await self._get_tools()
        r = await tools.mcp__suno__suno_generate_inspo({
            "audio_urls": audio_urls[:4],
            "audio_weight": audio_weight,
            "prompt": prompt,
            "style": style,
            "model": model
        })
        return self._parse_result(r)
    
    # 2. Style optimize
    async def optimize_style(self, raw_prompt: str) -> str:
        tools = await self._get_tools()
        r = await tools.mcp__suno__suno_optimize_style({"prompt": raw_prompt})
        return r.get("result", "")
    
    # 3. Lyric format guide
    async def lyric_format_guide(self) -> str:
        tools = await self._get_tools()
        r = await tools.mcp__suno__suno_get_lyric_format_guide({})
        return r.get("result", "")
    
    # 4. Custom mode generate (ANA TOOL)
    async def generate_custom(self,
        lyric: str,
        style: str,
        title: str = "",
        vocal_gender: str = "",
        model: str = "chirp-v5-5",
        duration: int = 240,
        negative_tags: str = "heavy metal, screaming, autotune, generic pop",
        style_influence: float = 1.0,
        variation_category: str = "normal",
        weirdness: float = 0.0,
        instrumental: bool = False,
        lyric_prompt: str = "",
    ) -> SunoResult:
        tools = await self._get_tools()
        args = {
            "lyric": lyric,
            "style": style,
            "model": model,
            "duration": duration,
            "negative_tags": negative_tags,
        }
        if title: args["title"] = title
        if vocal_gender: args["vocal_gender"] = vocal_gender
        if lyric_prompt: args["lyric_prompt"] = lyric_prompt
        r = await tools.mcp__suno__suno_generate_custom_music(args)
        return self._parse_result(r)
    
    # 5. Extend + Concat
    async def extend(self, audio_id: str, continue_at: float, lyric: str,
                     model: str = "chirp-v5-5", style: str = "") -> SunoResult:
        tools = await self._get_tools()
        r = await tools.mcp__suno__suno_extend_music({
            "audio_id": audio_id,
            "continue_at": continue_at,
            "lyric": lyric,
            "model": model,
            "style": style
        })
        return self._parse_result(r)
    
    async def concat(self, last_audio_id: str) -> SunoResult:
        tools = await self._get_tools()
        r = await tools.mcp__suno__suno_concat_music({"audio_id": last_audio_id})
        return self._parse_result(r)
    
    # 6. Cover / Remix
    async def cover(self, audio_id: str, style: str, prompt: str = "",
                    model: str = "chirp-v5-5", audio_weight: float = 0.5) -> SunoResult:
        tools = await self._get_tools()
        r = await tools.mcp__suno__suno_cover_music({
            "audio_id": audio_id,
            "style": style,
            "prompt": prompt,
            "model": model,
            "audio_weight": audio_weight
        })
        return self._parse_result(r)
    
    # 7. Persona
    async def create_persona(self, audio_id: str, name: str, description: str,
                             vocal_start: float = 0, vocal_end: float = None) -> SunoResult:
        tools = await self._get_tools()
        r = await tools.mcp__suno__suno_create_persona({
            "audio_id": audio_id,
            "name": name,
            "description": description,
            "vocal_start": vocal_start,
            "vocal_end": vocal_end
        })
        return self._parse_result(r)
    
    async def generate_with_persona(self, persona_id: str, prompt: str, style: str,
                                    model: str = "chirp-v5-5") -> SunoResult:
        tools = await self._get_tools()
        r = await tools.mcp__suno__suno_generate_with_persona_vox({
            "persona_id": persona_id,
            "prompt": prompt,
            "style": style,
            "model": model
        })
        return self._parse_result(r)
    
    # 8. Batch polling (VERİMLİ)
    async def poll_batch(self, task_ids: List[str]) -> List[SunoResult]:
        tools = await self._get_tools()
        r = await tools.mcp__suno__suno_get_tasks_batch({"task_ids": task_ids[:50]})
        results = []
        for item in r.get("results", []):
            results.append(self._parse_result(item))
        return results
    
    # 9. İndirme
    async def download_mp3(self, audio_id: str) -> SunoResult:
        tools = await self._get_tools()
        r = await tools.mcp__suno__suno_get_mp3({"audio_id": audio_id})
        return self._parse_result(r)
    
    async def download_mp4(self, audio_id: str) -> SunoResult:
        tools = await self._get_tools()
        r = await tools.mcp__suno__suno_get_mp4({"audio_id": audio_id})
        return self._parse_result(r)
    
    # 10. Timing (altyazı)
    async def get_timing(self, audio_id: str) -> dict:
        tools = await self._get_tools()
        r = await tools.mcp__suno__suno_get_timing({"audio_id": audio_id})
        return r.get("result", {})
    
    def _parse_result(self, raw: dict) -> SunoResult:
        """MCP raw response'u SunoResult'a çevir."""
        if isinstance(raw, dict):
            return SunoResult(
                task_id=raw.get("task_id") or raw.get("id") or "",
                audio_id=raw.get("audio_id") or raw.get("id"),
                status=raw.get("status", "unknown"),
                audio_url=raw.get("audio_url") or raw.get("url"),
                title=raw.get("title"),
                lyrics=raw.get("lyrics"),
                duration=raw.get("duration"),
                style_tags=raw.get("style") or raw.get("style_tags"),
                error=raw.get("error")
            )
        return SunoResult(task_id="", error=str(raw))


# ============================================================
# Config / Spec Yapısı
# ============================================================

@dataclass
class TrackSpec:
    title: str
    project_dir: str
    prompt: str
    style_raw: str
    style_optimized: str = ""
    reference_urls: List[str] = field(default_factory=list)
    audio_weight: float = 0.6
    vocal_gender: str = ""
    target_duration_sec: int = 240
    persona_id: str = ""
    negative_tags: str = "heavy metal, screaming, autotune, generic pop, cheap synth"


# ============================================================
# Producer Entegrasyon Sınıfı
# ============================================================

class SunoProducerMCP:
    """Mevcut SunoProducer ile uyumlu MCP tabanlı producer."""
    
    def __init__(self):
        self.mcp = SunoMCP()
    
    def _load_lyrics(self, project_dir: str) -> str:
        """Proje dizininden sözleri oku (sozler.md veya *_sozler.md)."""
        import os
        import glob
        
        # Önce sozler.md
        sozler_path = os.path.join(project_dir, "sozler.md")
        if os.path.exists(sozler_path):
            with open(sozler_path, encoding="utf-8") as f:
                return f.read()
        
        # Sonra *_sozler.md
        for f in glob.glob(os.path.join(project_dir, "*_sozler.md")):
            with open(f, encoding="utf-8") as f:
                return f.read()
        
        return ""
    
    async def generate_track(self, spec: TrackSpec) -> SunoResult:
        """Tam pipeline: inspo (varsa) → optimize → custom generate."""
        
        # 1. Style optimize (bir kere)
        if not spec.style_optimized:
            spec.style_optimized = await self.mcp.optimize_style(spec.style_raw)
        
        # 2. Inspo (referans varsa)
        if spec.reference_urls:
            inspo = await self.mcp.inspo(
                audio_urls=spec.reference_urls,
                prompt=spec.prompt,
                style=spec.style_optimized,
                audio_weight=spec.audio_weight
            )
            # Inspo'dan style tag'lerini birleştir
            if inspo.style_tags:
                spec.style_optimized = f"{spec.style_optimized}, {inspo.style_tags}"
        
        # 3. Sözler
        lyrics = self._load_lyrics(spec.project_dir)
        if not lyrics:
            raise ValueError(f"Söz bulunamadı: {spec.project_dir}")
        
        # 4. Custom generate
        result = await self.mcp.generate_custom(
            lyric=lyrics,
            style=spec.style_optimized,
            title=spec.title,
            vocal_gender=spec.vocal_gender,
            model="chirp-v5-5",
            duration=spec.target_duration_sec,
            negative_tags=spec.negative_tags
        )
        
        return result
    
    async def wait_and_download(self, task_id: str, project_dir: str) -> str:
        """Poll + indir + timing al + wav'a çevir."""
        import os
        import subprocess
        
        # Batch poll (her 15sn, max 10dk = 40 iterasyon)
        for i in range(40):
            await asyncio.sleep(15)
            results = await self.mcp.poll_batch([task_id])
            if results and results[0].status == "completed":
                break
            if results and results[0].status == "failed":
                raise RuntimeError(f"Suno generation failed: {results[0].error}")
        else:
            raise TimeoutError(f"Suno generation timeout: {task_id}")
        
        # MP3 indir
        mp3_result = await self.mcp.download_mp3(task_id)
        if not mp3_result.audio_url:
            raise RuntimeError("MP3 URL alınamadı")
        
        # İndir
        mp3_path = os.path.join(project_dir, "audio.mp3")
        await self._download_file(mp3_result.audio_url, mp3_path)
        
        # MP3 -> WAV çevir (ffmpeg)
        wav_path = os.path.join(project_dir, "audio.wav")
        await self._mp3_to_wav(mp3_path, wav_path)
        
        # Timing al (caption_align için)
        timing = await self.mcp.get_timing(task_id)
        await self._save_timing(project_dir, timing)
        
        # Geçici mp3 sil
        if os.path.exists(mp3_path):
            os.remove(mp3_path)
        
        return wav_path
    
    async def _download_file(self, url: str, dest: str):
        """Async dosya indir."""
        import httpx
        async with httpx.AsyncClient(timeout=300) as client:
            async with client.stream("GET", url) as resp:
                resp.raise_for_status()
                with open(dest, "wb") as f:
                    async for chunk in resp.aiter_bytes(8192):
                        f.write(chunk)
    
    async def _mp3_to_wav(self, mp3_path: str, wav_path: str):
        """ffmpeg ile mp3 -> wav (16-bit, 44.1kHz)."""
        cmd = [
            "ffmpeg", "-y", "-i", mp3_path,
            "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2",
            wav_path
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError("ffmpeg mp3->wav çevirme hatası")
    
    async def _save_timing(self, project_dir: str, timing: dict):
        """Timing verisini JSON olarak kaydet (caption_align kullanır)."""
        import json
        timing_path = os.path.join(project_dir, "timing.json")
        with open(timing_path, "w", encoding="utf-8") as f:
            json.dump(timing, f, ensure_ascii=False, indent=2)


# ============================================================
# Kullanım Örneği
# ============================================================

async def example_kumdan_denize():
    """Kumdan Denize için tam pipeline örneği."""
    
    spec = TrackSpec(
        title="Kumdan Denize",
        project_dir="projects/Kumdan Denize",
        prompt="Golden desert dunes meeting ocean, afro-house arabic EDM, cinematic aerial",
        style_raw="afro house arabic edm desert vibe",
        reference_urls=[
            "https://youtu.be/afro_house_ref",
            "https://soundcloud.com/arabic_edm_vibe"
        ],
        audio_weight=0.6,
        vocal_gender="f",
        target_duration_sec=240
    )
    
    producer = SunoProducerMCP()
    
    # 1. Generate
    print("Generating...")
    result = await producer.generate_track(spec)
    print(f"Task: {result.task_id}, Status: {result.status}")
    
    # 3. Wait + download
    print("Waiting & downloading...")
    wav_path = await producer.wait_and_download(result.task_id, spec.project_dir)
    print(f"Done: {wav_path}")


if __name__ == "__main__":
    asyncio.run(example_kumdan_denize())