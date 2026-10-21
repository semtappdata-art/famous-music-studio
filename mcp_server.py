#!/usr/bin/env python
"""Famous Music Studio — Production MCP Server.

Real project workflow (auto_process, render, upload, validate, yayin_ritmi,
dj_famous) exposed as MCP tools. Monkey-patch prevents MCP 1.x known bugs.

Usage:
    python mcp_server.py                    # stdio transport
    python mcp_server.py --http             # HTTP transport (port 8000)

Client connection (stdio):
    from mcp.client.stdio import stdio_client
    params = StdioServerParameters(command="python", args=["mcp_server.py"])
    read, write = await stdio_client(params)

Client connection (HTTP):
    from mcp.client.streamable_http import streamablehttp_client
    read, write = await streamablehttp_client("http://localhost:8000/mcp")
"""

# ============================================================
# MONKEY-PATCH: MCP 1.x "Connection closed" / "Request already responded to" FIX
# ============================================================
# REQUIRED for MCP 1.x (up to 1.30.0).
# DELETE THIS BLOCK if using MCP 2.x.
# ============================================================
try:
    from mcp.shared.session import RequestResponder
    _orig_respond = RequestResponder.respond
    _orig_cancel = RequestResponder.cancel

    async def _safe_respond(self, response):
        if getattr(self, "_completed", False):
            return
        await _orig_respond(self, response)

    async def _safe_cancel(self):
        if getattr(self, "_completed", False):
            return
        await _orig_cancel(self)

    RequestResponder.respond = _safe_respond
    RequestResponder.cancel = _safe_cancel
    print("[mcp_server] Monkey-patch applied: RequestResponder guarded", file=__import__("sys").stderr)
except (ImportError, AttributeError):
    pass

# ============================================================
# SERVER CODE
# ============================================================

import os
import sys
import json
import argparse
import asyncio
import subprocess
import time
from pathlib import Path
from typing import Any, Optional, Dict, List
from datetime import datetime
from functools import wraps

import config

# Project root directory
ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "upload"))

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.utilities.logging import get_logger

logger = get_logger(__name__)

# FastMCP server
mcp = FastMCP("famous-music-studio")

# ============================================================
# HELPER FUNCTIONS — Stability First
# ============================================================

def _project_dir(name: str) -> Path:
    """Regular project directory path."""
    return ROOT / "projects" / name


def _dj_set_dir(name: str) -> Path:
    """DJ set directory path."""
    return ROOT / "dj_sets" / name


def _read_state(name: str, is_dj: bool = False) -> dict:
    """Read state.json (returns empty dict if corrupted)."""
    base = _dj_set_dir(name) if is_dj else _project_dir(name)
    state_file = base / "state.json"
    if not state_file.exists():
        return {}
    try:
        with open(state_file, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def _write_state(name: str, data: dict, is_dj: bool = False) -> None:
    """Write state.json atomically (uses state_io.atomic_write)."""
    base = _dj_set_dir(name) if is_dj else _project_dir(name)
    state_file = base / "state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        from state_io import atomic_write
        atomic_write(str(state_file), data)
    except Exception:
        # Fallback
        tmp = state_file.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(state_file)


def _read_meta(name: str, is_dj: bool = False) -> dict:
    """Read meta.json."""
    base = _dj_set_dir(name) if is_dj else _project_dir(name)
    meta_file = base / "meta.json"
    if not meta_file.exists():
        return {}
    try:
        with open(meta_file, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def _run_subprocess(cmd: list, cwd: Optional[Path] = None, timeout: int = 300) -> dict:
    """Run subprocess and return result (stable)."""
    try:
        result = subprocess.run(
            cmd, cwd=cwd or ROOT, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace"
        )
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout[-5000:] if result.stdout else "",
            "stderr": result.stderr[-5000:] if result.stderr else "",
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"Timeout after {timeout}s", "returncode": -1}
    except Exception as e:
        return {"success": False, "error": str(e), "returncode": -1}


def _stable_tool(func):
    """Tool wrapper: catch errors, log, return JSON."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            return json.dumps({
                "error": f"{type(e).__name__}: {e}",
                "tool": func.__name__,
                "args": kwargs,
            }, ensure_ascii=False)
    return wrapper


def _list_subdirs(base: Path) -> List[str]:
    """List subdirectories only."""
    if not base.exists():
        return []
    return sorted([d.name for d in base.iterdir() if d.is_dir()])


def _get_audio_path(name: str, is_dj: bool = False) -> Optional[Path]:
    """Find audio file path."""
    base = _dj_set_dir(name) if is_dj else _project_dir(name)
    for fname in ("audio.wav", "audio.mp3", "audio.m4a"):
        p = base / fname
        if p.exists():
            return p
    return None


def _get_output_files(name: str, is_dj: bool = False) -> List[dict]:
    """List rendered files in output directory."""
    base = _dj_set_dir(name) if is_dj else _project_dir(name)
    out_dir = base / "output"
    if not out_dir.exists():
        return []
    files = []
    for f in out_dir.glob("*.mp4"):
        try:
            stat = f.stat()
            files.append({
                "file": f.name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
        except OSError:
            pass
    return files


# ============================================================
# DJ SET HELPER FUNCTIONS
# ============================================================

def _dj_upload_status(state: dict) -> dict:
    """Extract upload status from DJ set state."""
    platforms = {
        "youtube": bool(state.get("youtube_video_id")),
        "youtube_shorts": bool(state.get("youtube_shorts_video_id")),
        "instagram": bool(state.get("instagram_reel_id") or state.get("instagram_container_id")),
        "tiktok": bool(state.get("tiktok_publish_id")),
        "facebook": bool(state.get("facebook_reels_id")),
        "bluesky": bool(state.get("bluesky_uri")),
        "telegram": bool(state.get("telegram_message_id")),
    }
    uploaded = sum(1 for v in platforms.values() if v)
    total = len(platforms)
    return {
        "platforms": platforms,
        "uploaded_count": uploaded,
        "total_count": total,
        "complete": uploaded == total,
        "missing": [k for k, v in platforms.items() if not v],
    }


def _project_upload_status(state: dict) -> dict:
    """Extract upload status from regular project state."""
    platforms = {
        "youtube": bool(state.get("youtube_video_id")),
        "youtube_shorts": bool(state.get("youtube_shorts_video_id")),
        "instagram": bool(state.get("instagram_reel_id") or state.get("instagram_container_id")),
        "tiktok": bool(state.get("tiktok_publish_id")),
        "facebook": bool(state.get("facebook_reels_id")),
        "bluesky": bool(state.get("bluesky_uri")),
        "telegram": bool(state.get("telegram_message_id")),
    }
    uploaded = sum(1 for v in platforms.values() if v)
    total = len(platforms)
    return {
        "platforms": platforms,
        "uploaded_count": uploaded,
        "total_count": total,
        "complete": uploaded == total,
        "missing": [k for k, v in platforms.items() if not v],
    }


# ============================================================
# TOOLS — REGULAR PROJECTS
# ============================================================

@mcp.tool()
@_stable_tool
async def list_projects() -> str:
    """List all music projects (status + meta + upload status)."""
    projects_dir = ROOT / "projects"
    result = []
    for name in _list_subdirs(projects_dir):
        state = _read_state(name, is_dj=False)
        meta = _read_meta(name, is_dj=False)
        audio_path = _get_audio_path(name, is_dj=False)
        output_files = _get_output_files(name, is_dj=False)
        upload_status = _project_upload_status(state)

        result.append({
            "name": name,
            "status": state.get("status", "unknown"),
            "title": meta.get("title", name),
            "theme": meta.get("theme", ""),
            "style": meta.get("style", ""),
            "has_audio": audio_path is not None,
            "audio_file": audio_path.name if audio_path else None,
            "output_files": len(output_files),
            "youtube_video_id": state.get("youtube_video_id"),
            "youtube_shorts_video_id": state.get("youtube_shorts_video_id"),
            "updated_at": state.get("updated_at"),
            "upload_status": upload_status,
        })

    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
@_stable_tool
async def get_project(project: str) -> str:
    """Get single project details (state + meta + files + upload status)."""
    pdir = _project_dir(project)
    if not pdir.exists():
        return json.dumps({"error": f"Project not found: {project}"}, ensure_ascii=False)

    state = _read_state(project, is_dj=False)
    meta = _read_meta(project, is_dj=False)
    audio_path = _get_audio_path(project, is_dj=False)
    output_files = _get_output_files(project, is_dj=False)
    upload_status = _project_upload_status(state)

    files = []
    for f in pdir.rglob("*"):
        if f.is_file():
            try:
                files.append({
                    "path": str(f.relative_to(pdir)),
                    "size": f.stat().st_size,
                    "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                })
            except OSError:
                pass

    return json.dumps({
        "project": project,
        "state": state,
        "meta": meta,
        "files": files,
        "audio_file": audio_path.name if audio_path else None,
        "output_files": output_files,
        "upload_status": upload_status,
    }, ensure_ascii=False, indent=2)


@mcp.tool()
@_stable_tool
async def validate_project(project: str) -> str:
    """Validate project (uyumluluk.py + validate_project.py)."""
    result = _run_subprocess([
        sys.executable, "validate_project.py", project
    ], timeout=60)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
@_stable_tool
async def render_project(project: str, force: bool = False) -> str:
    """Render project (generate video)."""
    state = _read_state(project, is_dj=False)
    if not force and state.get("status") == "rendered":
        return json.dumps({"skipped": True, "reason": "Already rendered"}, ensure_ascii=False)

    result = _run_subprocess([
        sys.executable, "render.py", project
    ], timeout=600)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
@_stable_tool
async def generate_cover(project: str) -> str:
    """Generate cover art (16:9 + 9:16)."""
    result = _run_subprocess([
        sys.executable, "generate_cover.py", project
    ], timeout=120)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
@_stable_tool
async def check_upload_ready(project: str) -> str:
    """Check if ready for upload (yayin_ritmi + uyumluluk)."""
    try:
        from yayin_ritmi import yuklenmeye_hazir_mi
        from uyumluluk import kontrol

        ready, reason = yuklenmeye_hazir_mi(project)
        uyum = kontrol(project, "yukleme")

        return json.dumps({
            "project": project,
            "ready": ready,
            "reason": reason,
            "compliance": uyum,
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@mcp.tool()
@_stable_tool
async def upload_youtube(project: str, privacy: str = "private") -> str:
    """Upload to YouTube (long-form video)."""
    result = _run_subprocess([
        sys.executable, "-m", "upload.youtube_upload", project, "--privacy", privacy
    ], timeout=300)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
@_stable_tool
async def upload_shorts(project: str) -> str:
    """Upload to YouTube Shorts."""
    result = _run_subprocess([
        sys.executable, "-m", "upload.shorts_upload", project
    ], timeout=180)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
@_stable_tool
async def upload_instagram(project: str) -> str:
    """Upload to Instagram Reels."""
    result = _run_subprocess([
        sys.executable, "-m", "upload.instagram_upload", project
    ], timeout=180)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
@_stable_tool
async def upload_tiktok(project: str) -> str:
    """Create TikTok draft (manual publish required)."""
    result = _run_subprocess([
        sys.executable, "-m", "upload.tiktok_upload", project
    ], timeout=180)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
@_stable_tool
async def upload_facebook(project: str) -> str:
    """Upload to Facebook Reels."""
    result = _run_subprocess([
        sys.executable, "-m", "upload.facebook_upload", project
    ], timeout=180)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
@_stable_tool
async def upload_bluesky(project: str) -> str:
    """Upload to Bluesky."""
    result = _run_subprocess([
        sys.executable, "-m", "upload.bluesky_upload", project
    ], timeout=120)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
@_stable_tool
async def upload_telegram(project: str) -> str:
    """Upload to Telegram."""
    result = _run_subprocess([
        sys.executable, "-m", "upload.telegram_upload", project
    ], timeout=120)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
@_stable_tool
async def run_auto_process(count: int = 0, privacy: str = "private") -> str:
    """Run auto_process.py (process pending projects)."""
    cmd = [sys.executable, "auto_process.py"]
    if count > 0:
        cmd.extend(["--count", str(count)])
    if privacy:
        cmd.extend(["--privacy", privacy])

    result = _run_subprocess(cmd, timeout=600)
    return json.dumps(result, ensure_ascii=False, indent=2)


# ============================================================
# TOOLS — DJ SETS (ENGLISH ONLY)
# ============================================================

@mcp.tool()
@_stable_tool
async def list_dj_series() -> str:
    """List all available DJ series with their configurations (Cercle/HÖR/Boiler Room best practices)."""
    from config import list_dj_series, get_dj_series
    
    result = []
    for key in list_dj_series():
        series = get_dj_series(key)
        locations = series.get("locations", [])
        result.append({
            "key": key,
            "brand": series.get("brand", ""),
            "tagline": series.get("tagline", ""),
            "visual_theme": series.get("visual_theme", ""),
            "schedule": series.get("schedule", ""),
            "locations_count": len(locations),
            "locations": [
                {"city": loc.get("city"), "country": loc.get("country"), "landmark": loc.get("landmark")}
                for loc in locations
            ],
            "youtube": {
                "playlist_id": series["youtube"].get("playlist_id"),
                "tags_base": series["youtube"].get("tags_base"),
                "hashtags": series["youtube"].get("hashtags"),
                "title_format": series["youtube"].get("title_format"),
            },
            "thumbnail_template": series.get("thumbnail_template"),
            "description_template": series.get("description_template"),
            "seo": series.get("seo"),
        })
    
    return json.dumps({"series": result}, ensure_ascii=False, indent=2)


@mcp.tool()
@_stable_tool
async def list_dj_sets() -> str:
    """List all DJ sets (status + meta + upload status + series info)."""
    dj_dir = ROOT / "dj_sets"
    result = []
    for name in _list_subdirs(dj_dir):
        state = _read_state(name, is_dj=True)
        meta = _read_meta(name, is_dj=True)
        audio_path = _get_audio_path(name, is_dj=True)
        output_files = _get_output_files(name, is_dj=True)
        upload_status = _dj_upload_status(state)

        result.append({
            "name": name,
            "title": meta.get("title", name),
            "series": meta.get("series", "legacy"),
            "episode": meta.get("episode"),
            "set_style": meta.get("set_style", ""),
            "marquee_text": meta.get("marquee_text", ""),
            "art_query": meta.get("art_query", ""),
            "location": meta.get("location", {}),
            "has_audio": audio_path is not None,
            "audio_file": audio_path.name if audio_path else None,
            "output_files": len(output_files),
            "youtube_video_id": state.get("youtube_video_id"),
            "youtube_shorts_video_id": state.get("youtube_shorts_video_id"),
            "youtube_privacy": state.get("youtube_privacy"),
            "youtube_publish_at": state.get("youtube_publish_at"),
            "upload_status": upload_status,
            "copyright_track": state.get("telif_eser"),
            "copyright_strike_changed": state.get("telif_ihtar_degik"),
        })

    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
@_stable_tool
async def get_dj_set(name: str) -> str:
    """Get DJ set details (state + meta + files + upload status + copyright)."""
    ddir = _dj_set_dir(name)
    if not ddir.exists():
        return json.dumps({"error": f"DJ set not found: {name}"}, ensure_ascii=False)

    state = _read_state(name, is_dj=True)
    meta = _read_meta(name, is_dj=True)
    audio_path = _get_audio_path(name, is_dj=True)
    output_files = _get_output_files(name, is_dj=True)
    upload_status = _dj_upload_status(state)

    files = []
    for f in ddir.rglob("*"):
        if f.is_file():
            try:
                files.append({
                    "path": str(f.relative_to(ddir)),
                    "size": f.stat().st_size,
                    "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                })
            except OSError:
                pass

    return json.dumps({
        "name": name,
        "state": state,
        "meta": meta,
        "files": files,
        "audio_file": audio_path.name if audio_path else None,
        "output_files": output_files,
        "upload_status": upload_status,
        "segments": state.get("dj_clips", []),
        "copyright": {
            "track": state.get("telif_eser"),
            "date": state.get("telif_tarih"),
            "video_id": state.get("telif_video_id"),
            "strike_changed": state.get("telif_ihtar_degik"),
            "claims": state.get("telif_araliklari", []),
        },
    }, ensure_ascii=False, indent=2)


@mcp.tool()
@_stable_tool
async def check_dj_set_upload_status(name: str) -> str:
    """Check detailed upload status for a DJ set (which platforms are missing)."""
    ddir = _dj_set_dir(name)
    if not ddir.exists():
        return json.dumps({"error": f"DJ set not found: {name}"}, ensure_ascii=False)

    state = _read_state(name, is_dj=True)
    upload_status = _dj_upload_status(state)

    yt_privacy = state.get("youtube_privacy")
    yt_publish_at = state.get("youtube_publish_at")
    yt_privacy_actual = state.get("youtube_privacy_gercek")
    yt_privacy_actual_at = state.get("youtube_privacy_gercek_at")

    tiktok_id = state.get("tiktok_publish_id")
    tiktok_status = "draft" if tiktok_id and "v_inbox" in str(tiktok_id) else ("published" if tiktok_id else "not_uploaded")

    return json.dumps({
        "name": name,
        "upload_status": upload_status,
        "youtube": {
            "video_id": state.get("youtube_video_id"),
            "shorts_id": state.get("youtube_shorts_video_id"),
            "privacy": yt_privacy,
            "publish_at": yt_publish_at,
            "actual_privacy": yt_privacy_actual,
            "actual_privacy_at": yt_privacy_actual_at,
        },
        "tiktok": {
            "publish_id": tiktok_id,
            "status": tiktok_status,
        },
        "instagram": {
            "reel_id": state.get("instagram_reel_id"),
            "container_id": state.get("instagram_container_id"),
        },
        "facebook": {
            "reels_id": state.get("facebook_reels_id"),
        },
        "bluesky": {
            "uri": state.get("bluesky_uri"),
        },
        "telegram": {
            "message_id": state.get("telegram_message_id"),
        },
    }, ensure_ascii=False, indent=2)


@mcp.tool()
@_stable_tool
async def render_dj_set(name: str, force: bool = False) -> str:
    """Render DJ set (uses dj_set_video.py)."""
    state = _read_state(name, is_dj=True)
    if not force and state.get("last_render"):
        return json.dumps({"skipped": True, "reason": "Already rendered (use force=true)"}, ensure_ascii=False)

    result = _run_subprocess([
        sys.executable, "dj_set_video.py", name
    ], timeout=900)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
@_stable_tool
async def generate_dj_cover(name: str) -> str:
    """Generate DJ set cover art (generate_cover.py)."""
    result = _run_subprocess([
        sys.executable, "generate_cover.py", name
    ], timeout=120)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
@_stable_tool
async def upload_dj_youtube(name: str, privacy: str = "private") -> str:
    """Upload DJ set to YouTube."""
    result = _run_subprocess([
        sys.executable, "-m", "upload.youtube_upload", name, "--privacy", privacy, "--dj-set"
    ], timeout=300)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
@_stable_tool
async def upload_dj_shorts(name: str) -> str:
    """Upload DJ set to YouTube Shorts."""
    result = _run_subprocess([
        sys.executable, "-m", "upload.shorts_upload", name, "--dj-set"
    ], timeout=180)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
@_stable_tool
async def upload_dj_instagram(name: str) -> str:
    """Upload DJ set to Instagram Reels (AI disclosure added)."""
    result = _run_subprocess([
        sys.executable, "-m", "upload.instagram_upload", name, "--dj-set"
    ], timeout=180)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
@_stable_tool
async def upload_dj_tiktok(name: str) -> str:
    """Create DJ set TikTok draft."""
    result = _run_subprocess([
        sys.executable, "-m", "upload.tiktok_upload", name, "--dj-set"
    ], timeout=180)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
@_stable_tool
async def upload_dj_facebook(name: str) -> str:
    """Upload DJ set to Facebook Reels."""
    result = _run_subprocess([
        sys.executable, "-m", "upload.facebook_upload", name, "--dj-set"
    ], timeout=180)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
@_stable_tool
async def upload_dj_bluesky(name: str) -> str:
    """Upload DJ set to Bluesky."""
    result = _run_subprocess([
        sys.executable, "-m", "upload.bluesky_upload", name, "--dj-set"
    ], timeout=120)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
@_stable_tool
async def upload_dj_telegram(name: str) -> str:
    """Upload DJ set to Telegram."""
    result = _run_subprocess([
        sys.executable, "-m", "upload.telegram_upload", name, "--dj-set"
    ], timeout=120)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
@_stable_tool
async def run_dj_famous_process(privacy: str = "private") -> str:
    """Run weekly DJ Famous process (dj_famous_process.py)."""
    cmd = [sys.executable, "dj_famous_process.py"]
    if privacy:
        cmd.extend(["--privacy", privacy])

    result = _run_subprocess(cmd, timeout=1200)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
@_stable_tool
async def create_dj_set(
    name: str,
    series: str = "",
    title: str = "",
    set_style: str = "",
    location_idx: int = None,
    custom_location: dict = None,
    episode: int = 1,
    marquee_text: str = "",
    art_query: str = "",
) -> str:
    """Create new DJ set with series-based best practices (Cercle/HÖR/Boiler Room style).
    
    Args:
        name: Unique directory name (e.g., 'City_Pulse_Ep1_Istanbul')
        series: Series key from DJ_SERIES (city_pulse, deep_focus, night_drive, boiler_room_style)
        title: Display title (auto-generated from series if empty)
        set_style: Override series default style
        location_idx: Override series default location index
        custom_location: Custom location dict {city, country, landmark, gps, story}
        episode: Episode number for series
        marquee_text: Override default marquee
        art_query: Override default art query
    """
    # Validate series
    from config import get_dj_series, get_series_location, list_dj_series
    
    if not series:
        available = list_dj_series()
        return json.dumps({
            "error": "Series is required",
            "available_series": available,
            "usage": "create_dj_set(name='My_Set', series='city_pulse', episode=1)"
        }, ensure_ascii=False)
    
    series_config = get_dj_series(series)
    if not series_config:
        return json.dumps({"error": f"Unknown series: {series}", "available": list_dj_series()}, ensure_ascii=False)

    ddir = _dj_set_dir(name)
    if ddir.exists():
        return json.dumps({"error": f"DJ set already exists: {name}"}, ensure_ascii=False)

    ddir.mkdir(parents=True)
    (ddir / "output").mkdir(exist_ok=True)
    (ddir / "_segments").mkdir(exist_ok=True)

    # Get location (custom > indexed > series default)
    if custom_location:
        location = custom_location
    else:
        location = get_series_location(series, location_idx)
    
    # Build meta with series best practices
    landmark = location.get("landmark", location.get("city", ""))
    city = location.get("city", "")
    country = location.get("country", "")
    gps = location.get("gps", "")
    story = location.get("story", "")
    
    # Title format from series
    title_format = series_config["youtube"]["title_format"]
    artist_name = "DJ Famous"  # Could be parameterized later
    auto_title = title_format.format(artist=artist_name, landmark=landmark, city=city, route=location.get("route", ""))
    
    meta = {
        "title": title or auto_title,
        "series": series,
        "episode": episode,
        "theme": "dj",
        "set_style": set_style or series_config.get("visual_theme", "").replace("_cinematic", "").replace("_", " "),
        "marquee_text": marquee_text or f"{series_config['brand']}  •  Ep{episode:02d}  •  #DJFamous",
        "art_query": art_query or f"{location.get('city', '')} {location.get('landmark', '')} {series_config['visual_theme'].replace('_', ' ')} cinematic",
        "location": {
            "city": city,
            "country": country,
            "landmark": landmark,
            "gps": gps,
            "story": story,
            "route": location.get("route", ""),
        },
        "youtube": {
            "playlist_id": series_config["youtube"].get("playlist_id", ""),
            "tags_base": series_config["youtube"].get("tags_base", []),
            "hashtags": series_config["youtube"].get("hashtags", ""),
            "title_format": series_config["youtube"].get("title_format", ""),
        },
        "seo": series_config.get("seo", {}),
        "thumbnail_concept": series_config.get("thumbnail_template", ""),
        "description_template": series_config.get("description_template", ""),
        "schedule": series_config.get("schedule", ""),
        "cross_promo": {
            "shorts_clips": ["hook_0-30s", "transition_mid", "outro_last_3min"],
            "instagram_reel": "30s_vertical_hook",
            "tiktok_draft": "60s_best_moment",
            "bluesky_thread": "track_by_track_breakdown",
        },
        "created_at": datetime.now().isoformat(),
    }
    with open(ddir / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    state = {
        "status": "created",
        "series": series,
        "episode": episode,
        "created_at": datetime.now().isoformat(),
    }
    _write_state(name, state, is_dj=True)

    return json.dumps({
        "ok": True,
        "name": name,
        "path": str(ddir),
        "series": series,
        "episode": episode,
        "location": location,
        "auto_title": auto_title,
        "thumbnail_concept": meta["thumbnail_concept"],
        "youtube_tags": meta["youtube"]["tags_base"],
        "youtube_hashtags": meta["youtube"]["hashtags"],
    }, ensure_ascii=False, indent=2)


@mcp.tool()
@_stable_tool
async def update_dj_set_state(name: str, updates: dict) -> str:
    """Update DJ set state.json atomically."""
    ddir = _dj_set_dir(name)
    if not ddir.exists():
        return json.dumps({"error": f"DJ set not found: {name}"}, ensure_ascii=False)

    state = _read_state(name, is_dj=True)
    state.update(updates)
    state["updated_at"] = datetime.now().isoformat()
    _write_state(name, state, is_dj=True)

    return json.dumps({"ok": True, "state": state}, ensure_ascii=False, indent=2)


# ============================================================
# TOOLS — SYSTEM / COMMON
# ============================================================

@mcp.tool()
@_stable_tool
async def check_upload_schedule() -> str:
    """Check upload schedule status (daily/weekly limits, tempo)."""
    try:
        from yayin_ritmi import gunluk_yukleme_sayisi, haftalik_yukleme_sayisi, tempo_kontrol

        recent = []
        for base, is_dj in [(ROOT / "projects", False), (ROOT / "dj_sets", True)]:
            if base.exists():
                for item in base.iterdir():
                    if not item.is_dir():
                        continue
                    state = _read_state(item.name, is_dj=is_dj)
                    for key in ("youtube_uploaded_at", "youtube_shorts_uploaded_at"):
                        if state.get(key):
                            recent.append({
                                "name": item.name,
                                "type": "dj_set" if is_dj else "project",
                                "key": key,
                                "time": state[key],
                            })

        recent.sort(key=lambda x: x["time"], reverse=True)

        return json.dumps({
            "recent_uploads": recent[:10],
            "daily_count": gunluk_yukleme_sayisi(),
            "weekly_count": haftalik_yukleme_sayisi(),
            "tempo_ok": tempo_kontrol(),
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@mcp.tool()
@_stable_tool
async def git_sync(pull: bool = True, push: bool = False, message: str = "") -> str:
    """Git sync (pull + optional push)."""
    results = {}
    if pull:
        results["pull"] = _run_subprocess([sys.executable, "git_sync.py", "--pull"])
    if push:
        results["push"] = _run_subprocess([sys.executable, "git_sync.py", "--push", "--message", message or "MCP auto-commit"])
    return json.dumps(results, ensure_ascii=False, indent=2)


@mcp.tool()
@_stable_tool
async def get_logs(name: str = "", lines: int = 50, is_dj: bool = False) -> str:
    """Read log files."""
    logs = {}

    log_file = ROOT / ("dj_famous_process.log" if is_dj else "auto_process.log")
    if log_file.exists():
        with open(log_file, encoding="utf-8", errors="replace") as f:
            content = f.readlines()[-lines:]
        logs["main"] = "".join(content)

    if name:
        base = _dj_set_dir(name) if is_dj else _project_dir(name)
        proj_log = base / "render.log"
        if proj_log.exists():
            with open(proj_log, encoding="utf-8", errors="replace") as f:
                logs[name] = "".join(f.readlines()[-lines:])

    return json.dumps(logs, ensure_ascii=False, indent=2)


@mcp.tool()
@_stable_tool
async def create_project(name: str, title: str = "", theme: str = "", style: str = "") -> str:
    """Create new regular project (basic structure + meta.json)."""
    pdir = _project_dir(name)
    if pdir.exists():
        return json.dumps({"error": f"Project already exists: {name}"}, ensure_ascii=False)

    pdir.mkdir(parents=True)
    (pdir / "output").mkdir(exist_ok=True)

    meta = {
        "title": title or name,
        "theme": theme or "pop",
        "style": style or "",
        "marquee_text": "DJ Famous",
        "art_query": f"{theme} music background aesthetic" if theme else "music studio aesthetic",
        "created_at": datetime.now().isoformat(),
    }
    with open(pdir / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    state = {
        "status": "created",
        "created_at": datetime.now().isoformat(),
    }
    _write_state(name, state, is_dj=False)

    (pdir / "sozler.md").write_text("", encoding="utf-8")

    return json.dumps({"ok": True, "project": name, "path": str(pdir)}, ensure_ascii=False, indent=2)


@mcp.tool()
@_stable_tool
async def update_state(name: str, updates: dict, is_dj: bool = False) -> str:
    """Update project/DJ set state.json atomically."""
    base = _dj_set_dir(name) if is_dj else _project_dir(name)
    if not base.exists():
        kind = "DJ set" if is_dj else "Project"
        return json.dumps({"error": f"{kind} not found: {name}"}, ensure_ascii=False)

    state = _read_state(name, is_dj=is_dj)
    state.update(updates)
    state["updated_at"] = datetime.now().isoformat()
    _write_state(name, state, is_dj=is_dj)

    return json.dumps({"ok": True, "state": state}, ensure_ascii=False, indent=2)


@mcp.tool()
@_stable_tool
async def generate_youtube_metadata(name: str, tracklist: list = None, artist: str = "DJ Famous") -> str:
    """Generate YouTube-optimized metadata (title, description, tags, chapters) for a DJ set.
    
    Args:
        name: DJ set directory name
        tracklist: List of tracks with timestamp, title, artist, bpm, key
                   Example: [{"timestamp": "00:00", "title": "Track 1", "artist": "Artist", "bpm": 124, "key": "Am"}]
                   If not provided, reads from meta.json tracklist.
        artist: Artist name for title (default: DJ Famous)
    
    Returns complete YouTube metadata ready for upload.
    """
    ddir = _dj_set_dir(name)
    if not ddir.exists():
        return json.dumps({"error": f"DJ set not found: {name}"}, ensure_ascii=False)

    meta = _read_meta(name, is_dj=True)
    state = _read_state(name, is_dj=True)
    
    series_key = meta.get("series")
    if not series_key:
        return json.dumps({"error": "Set has no series. Use create_dj_set with series parameter."}, ensure_ascii=False)

    from config import get_dj_series, get_series_location
    series = get_dj_series(series_key)
    if not series:
        return json.dumps({"error": f"Unknown series: {series_key}"}, ensure_ascii=False)

    # Use tracklist from meta if not provided
    if tracklist is None:
        tracklist = meta.get("tracklist", [])
    
    # Get location for title
    location = meta.get("location") or get_series_location(series_key)
    landmark = location.get("landmark", location.get("city", ""))
    city = location.get("city", "")
    country = location.get("country", "")
    route = location.get("route", "")
    story = location.get("story", "")
    gps = location.get("gps", "")
    
    episode = meta.get("episode", 1)
    
    # Generate title from series format
    title_format = series["youtube"]["title_format"]
    title = title_format.format(artist=artist, landmark=landmark, city=city, route=route)
    
    # Ensure title <= 100 chars (YouTube limit)
    if len(title) > 100:
        title = title[:97] + "..."

    # Build description
    desc_parts = []
    
    # Hook line (first 2 lines visible in search)
    hook_lines = [
        f"{artist} playing {series['brand'].lower()} at {landmark}, {city}.",
        f"Episode {episode} of {series['brand']} — {series['tagline']}",
    ]
    desc_parts.extend(hook_lines)
    desc_parts.append("")
    
    # Tracklist with timestamps = YouTube chapters
    if tracklist:
        desc_parts.append("🎧 TRACKLIST:")
        for i, track in enumerate(tracklist):
            ts = track.get("timestamp", "00:00")
            tr_title = track.get("title", f"Track {i+1}")
            tr_artist = track.get("artist", "Unknown")
            bpm = track.get("bpm", "")
            key = track.get("key", "")
            extra = f" [{bpm} BPM, {key}]" if bpm or key else ""
            desc_parts.append(f"{ts} {tr_title} - {tr_artist}{extra}")
        desc_parts.append("")
    else:
        desc_parts.append("🎧 TRACKLIST: (Add track timestamps for chapters)")
        desc_parts.append("")
    
    # Location story (Cercle style)
    if story:
        desc_parts.append(f"📍 LOCATION STORY:")
        desc_parts.append(story)
        if gps:
            desc_parts.append(f"GPS: {gps}")
        desc_parts.append("")
    
    # Credits
    desc_parts.append("🎬 CREDITS:")
    desc_parts.append(f"Artist: {artist}")
    desc_parts.append(f"Series: {series['brand']} (Ep {episode})")
    desc_parts.append(f"Location: {landmark}, {city}, {country}")
    desc_parts.append(f"Produced by: DJ Famous")
    desc_parts.append("")

    # Artist links
    desc_parts.append("🔗 CONNECT:")
    desc_parts.append("YouTube: {config.SOCIAL_LINKS['youtube']}")
    desc_parts.append("Instagram: https://instagram.com/djfamous")
    desc_parts.append("Spotify: https://spotify.com/artist/djfamous")
    desc_parts.append("TikTok: https://tiktok.com/@djfamous")
    desc_parts.append("Bluesky: https://bsky.app/profile/djfamous.bsky.social")
    desc_parts.append("Telegram: https://t.me/djfamous")
    desc_parts.append("")

    # Series links
    desc_parts.append(f"📺 {series['brand'].upper()}:")
    desc_parts.append(f"Playlist: https://youtube.com/playlist?list={series['youtube'].get('playlist_id', '')}")
    desc_parts.append("Subscribe for more sets!")
    desc_parts.append("")

    # Hashtags
    hashtags = series["youtube"].get("hashtags", "")
    if hashtags:
        desc_parts.append(hashtags)
    
    description = "\n".join(desc_parts)
    
    # Ensure description <= 5000 chars
    if len(description) > 5000:
        description = description[:4997] + "..."

    # Build tags
    tags = []
    tags.extend(series["youtube"].get("tags_base", []))
    tags.extend([artist.lower(), series_key.replace("_", " "), city.lower(), country.lower()])
    if landmark:
        tags.append(landmark.lower())
    # Add SEO keywords
    seo = series.get("seo", {})
    if seo.get("primary_keyword"):
        tags.append(seo["primary_keyword"])
    tags.extend(seo.get("secondary_keywords", []))
    # Deduplicate
    tags = list(dict.fromkeys([t.strip().lower() for t in tags if t.strip()]))
    
    # Limit to 500 chars total (YouTube limit)
    tags_str = ", ".join(tags)
    if len(tags_str) > 500:
        tags_str = tags_str[:497] + "..."
    
    # Build chapters for YouTube
    chapters = []
    if tracklist:
        for track in tracklist:
            ts = track.get("timestamp", "00:00")
            tr_title = track.get("title", "Track")
            chapters.append({"timestamp": ts, "title": tr_title})
    
    # Thumbnail concept
    thumbnail_concept = meta.get("thumbnail_concept", series.get("thumbnail_template", ""))
    
    # End screen suggestions
    end_screen = {
        "subscribe": True,
        "next_video": f"{series['brand']} Ep {episode + 1}",
        "playlist": series["youtube"].get("playlist_id", ""),
        "channel": "DJ Famous",
    }
    
    # Cards
    cards = [
        {"time": "0:30", "type": "playlist", "title": series['brand'], "url": f"https://youtube.com/playlist?list={series['youtube'].get('playlist_id', '')}"},
    ]
    if tracklist and len(tracklist) > 3:
        mid_time = tracklist[len(tracklist)//2].get("timestamp", "5:00")
        cards.append({"time": mid_time, "type": "video", "title": f"{series['brand']} Ep {episode - 1}", "url": ""})

    return json.dumps({
        "title": title,
        "description": description,
        "tags": tags_str,
        "tags_list": tags,
        "chapters": chapters,
        "thumbnail_concept": thumbnail_concept,
        "end_screen": end_screen,
        "cards": cards,
        "hashtags": hashtags,
        "playlist_id": series["youtube"].get("playlist_id", ""),
        "premiere_recommended": True,
        "category": "Music",
        "language": "en",
        "location": f"{city}, {country}",
        "recording_date": datetime.now().strftime("%Y-%m-%d"),
        "video_elements": {
            "chapters": len(chapters) > 0,
            "end_screen": True,
            "cards": len(cards) > 0,
            "premiere": True,
        },
    }, ensure_ascii=False, indent=2)


@mcp.tool()
@_stable_tool
async def create_tracklist_from_timing(name: str, timing_file: str = "timing.json") -> str:
    """Create tracklist from Suno timing.json or audio analysis.
    
    Args:
        name: DJ set directory name
        timing_file: Timing file name (default: timing.json from Suno)
    
    Returns tracklist with timestamps ready for generate_youtube_metadata.
    """
    ddir = _dj_set_dir(name)
    if not ddir.exists():
        return json.dumps({"error": f"DJ set not found: {name}"}, ensure_ascii=False)

    timing_path = ddir / timing_file
    if not timing_path.exists():
        # Try to find any timing file
        timing_files = list(ddir.glob("*timing*.json"))
        if timing_files:
            timing_path = timing_files[0]
        else:
            return json.dumps({"error": f"Timing file not found: {timing_file}"}, ensure_ascii=False)

    try:
        with open(timing_path, encoding="utf-8") as f:
            timing = json.load(f)
    except Exception as e:
        return json.dumps({"error": f"Failed to read timing file: {e}"}, ensure_ascii=False)

    tracklist = []
    
    # Parse Suno timing format
    if isinstance(timing, dict) and "segments" in timing:
        # Suno get_timing format
        for i, seg in enumerate(timing["segments"]):
            start = seg.get("start", 0)
            end = seg.get("end", 0)
            text = seg.get("text", f"Segment {i+1}")
            # Convert seconds to MM:SS or HH:MM:SS
            def fmt(t):
                h = int(t // 3600)
                m = int((t % 3600) // 60)
                s = int(t % 60)
                if h > 0:
                    return f"{h:02d}:{m:02d}:{s:02d}"
                return f"{m:02d}:{s:02d}"
            tracklist.append({
                "timestamp": fmt(start),
                "title": text[:80],
                "artist": "DJ Famous",
                "start_sec": start,
                "end_sec": end,
            })
    elif isinstance(timing, dict) and "words" in timing:
        # Word-level timing - group into phrases
        words = timing["words"]
        current_phrase = []
        phrase_start = 0
        for w in words:
            if not current_phrase:
                phrase_start = w.get("start", 0)
            current_phrase.append(w.get("text", ""))
            # End phrase on punctuation or length
            if w.get("text", "").endswith((".", "!", "?", ",")) or len(current_phrase) >= 10:
                text = " ".join(current_phrase).strip()
                if text:
                    def fmt(t):
                        h = int(t // 3600)
                        m = int((t % 3600) // 60)
                        s = int(t % 60)
                        if h > 0:
                            return f"{h:02d}:{m:02d}:{s:02d}"
                        return f"{m:02d}:{s:02d}"
                    tracklist.append({
                        "timestamp": fmt(phrase_start),
                        "title": text[:80],
                        "artist": "DJ Famous",
                        "start_sec": phrase_start,
                        "end_sec": w.get("end", phrase_start),
                    })
                current_phrase = []
    elif isinstance(timing, list):
        # Direct list of segments
        for i, seg in enumerate(timing):
            if isinstance(seg, dict):
                start = seg.get("start", seg.get("timestamp", 0))
                end = seg.get("end", start + 30)
                text = seg.get("text", seg.get("title", f"Track {i+1}"))
                def fmt(t):
                    h = int(t // 3600)
                    m = int((t % 3600) // 60)
                    s = int(t % 60)
                    if h > 0:
                        return f"{h:02d}:{m:02d}:{s:02d}"
                    return f"{m:02d}:{s:02d}"
                tracklist.append({
                    "timestamp": fmt(start),
                    "title": text[:80],
                    "artist": "DJ Famous",
                    "start_sec": start,
                    "end_sec": end,
                })
    
    if not tracklist:
        return json.dumps({"error": "Could not parse timing format", "timing_sample": str(timing)[:500]}, ensure_ascii=False)

    # Save tracklist to meta
    meta = _read_meta(name, is_dj=True)
    meta["tracklist"] = tracklist
    meta["tracklist_updated_at"] = datetime.now().isoformat()
    with open(ddir / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return json.dumps({
        "ok": True,
        "tracklist": tracklist,
        "count": len(tracklist),
        "source": str(timing_path),
    }, ensure_ascii=False, indent=2)


@mcp.tool()
@_stable_tool
async def health_check() -> str:
    """Server health check."""
    projects_ok = (ROOT / "projects").exists()
    dj_sets_ok = (ROOT / "dj_sets").exists()
    upload_ok = (ROOT / "upload").exists()

    modules_ok = True
    module_errors = []
    for mod in ["config", "uyumluluk", "yayin_ritmi", "state_io", "render", "generate_cover"]:
        try:
            __import__(mod)
        except Exception as e:
            modules_ok = False
            module_errors.append(f"{mod}: {e}")

    return json.dumps({
        "status": "healthy" if (projects_ok and dj_sets_ok and upload_ok and modules_ok) else "degraded",
        "directories": {
            "projects": projects_ok,
            "dj_sets": dj_sets_ok,
            "upload": upload_ok,
        },
        "modules": {
            "ok": modules_ok,
            "errors": module_errors,
        },
        "python": sys.version,
        "root": str(ROOT),
    }, ensure_ascii=False, indent=2)


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Famous Music Studio MCP Server")
    parser.add_argument("--http", action="store_true", help="HTTP transport (port 8000)")
    parser.add_argument("--port", type=int, default=8000, help="HTTP port")
    parser.add_argument("--host", default="127.0.0.1", help="HTTP host")
    args = parser.parse_args()

    print("Starting Famous Music Studio MCP Server...", file=sys.stderr)
    print(f"Project root: {ROOT}", file=sys.stderr)
    print(f"Transport: {'HTTP' if args.http else 'stdio'}", file=sys.stderr)

    if args.http:
        mcp.run(transport="streamable-http", host=args.host, port=args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()