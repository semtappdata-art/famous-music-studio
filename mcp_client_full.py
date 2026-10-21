#!/usr/bin/env python
"""MCP Client — mcp_server.py full integration test (DJ sets English only + new tools)."""

import asyncio
import sys
import os
import json
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    server_script = Path(__file__).parent / "mcp_server.py"

    if not server_script.exists():
        print(f"[ERROR] Server script not found: {server_script}")
        sys.exit(1)

    print(f"[INFO] Connecting to: {server_script}")

    params = StdioServerParameters(
        command=sys.executable,
        args=[str(server_script)],
        env=None,
        stderr_to_stdout=True,
    )

    try:
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                print("[INFO] Initializing...")
                await session.initialize()
                print("[OK] Connected!")

                # Tool list
                tools = await session.list_tools()
                print(f"\n[INFO] Available tools ({len(tools.tools)}):")
                for t in tools.tools:
                    print(f"  - {t.name}")

                # ===== REGULAR PROJECT TESTS =====
                print("\n========== REGULAR PROJECT TESTS ==========")

                # Test: list_projects
                print("\n[INFO] Testing list_projects...")
                result = await session.call_tool("list_projects", {})
                data = json.loads(result.content[0].text)
                print(f"  Found {len(data)} projects")
                for p in data[:3]:
                    print(f"    {p['name']}: status={p['status']}, audio={p['has_audio']}, uploaded={p['upload_status']['uploaded_count']}/{p['upload_status']['total_count']}")

                # Test: get_project
                if data:
                    first = data[0]['name']
                    print(f"\n[INFO] Testing get_project({first})...")
                    result = await session.call_tool("get_project", {"project": first})
                    proj = json.loads(result.content[0].text)
                    print(f"  Title: {proj['meta'].get('title')}")
                    print(f"  Theme: {proj['meta'].get('theme')}")
                    print(f"  Files: {len(proj['files'])}")
                    print(f"  Upload: {proj['upload_status']['uploaded_count']}/{proj['upload_status']['total_count']}")

                # Test: check_upload_ready
                if data:
                    first = data[0]['name']
                    print(f"\n[INFO] Testing check_upload_ready({first})...")
                    result = await session.call_tool("check_upload_ready", {"project": first})
                    ready = json.loads(result.content[0].text)
                    print(f"  Ready: {ready.get('ready')}, Reason: {ready.get('reason')}")

                # ===== DJ SET TESTS (ENGLISH ONLY) =====
                print("\n========== DJ SET TESTS (ENGLISH) ==========")

                # Test: list_dj_series
                print("\n[INFO] Testing list_dj_series...")
                result = await session.call_tool("list_dj_series", {})
                series_data = json.loads(result.content[0].text)
                print(f"  Found {len(series_data['series'])} series:")
                for s in series_data['series']:
                    print(f"    {s['key']}: {s['brand']} ({s['locations_count']} locations)")
                    print(f"      Schedule: {s['schedule']}")
                    print(f"      Visual theme: {s['visual_theme']}")
                    print(f"      YouTube tags: {s['youtube']['tags_base'][:3]}...")

                # Test: list_dj_sets
                print("\n[INFO] Testing list_dj_sets...")
                result = await session.call_tool("list_dj_sets", {})
                dj_data = json.loads(result.content[0].text)
                print(f"  Found {len(dj_data)} DJ sets")
                for d in dj_data:
                    print(f"    {d['name']}: series={d.get('series')}, ep={d.get('episode')}, style={d['set_style']}, audio={d['has_audio']}, uploaded={d['upload_status']['uploaded_count']}/{d['upload_status']['total_count']}")
                    if d.get('copyright_track'):
                        print(f"      Copyright: {d['copyright_track']}")

                # Test: get_dj_set
                if dj_data:
                    first_dj = dj_data[0]['name']
                    print(f"\n[INFO] Testing get_dj_set({first_dj})...")
                    result = await session.call_tool("get_dj_set", {"name": first_dj})
                    dj = json.loads(result.content[0].text)
                    print(f"  Title: {dj['meta'].get('title')}")
                    print(f"  Series: {dj['meta'].get('series')}, Episode: {dj['meta'].get('episode')}")
                    print(f"  Style: {dj['meta'].get('set_style')}")
                    print(f"  Location: {dj['meta'].get('location', {}).get('city')}")
                    print(f"  Files: {len(dj['files'])}")
                    print(f"  Upload: {dj['upload_status']['uploaded_count']}/{dj['upload_status']['total_count']}")
                    print(f"  Missing: {dj['upload_status']['missing']}")
                    print(f"  Segments: {len(dj.get('segments', []))}")
                    if dj.get('copyright', {}).get('track'):
                        print(f"  Copyright: {dj['copyright']['track']}")

                # Test: check_dj_set_upload_status
                if dj_data:
                    first_dj = dj_data[0]['name']
                    print(f"\n[INFO] Testing check_dj_set_upload_status({first_dj})...")
                    result = await session.call_tool("check_dj_set_upload_status", {"name": first_dj})
                    status = json.loads(result.content[0].text)
                    print(f"  YouTube: {status['youtube']['video_id']} (privacy: {status['youtube']['privacy']})")
                    print(f"  TikTok: {status['tiktok']['status']}")
                    print(f"  Instagram: {status['instagram'].get('reel_id')}")
                    print(f"  Facebook: {status['facebook'].get('reels_id')}")
                    print(f"  Bluesky: {status['bluesky'].get('uri')}")
                    print(f"  Telegram: {status['telegram'].get('message_id')}")

                # Test: create_dj_set with series
                print("\n[INFO] Testing create_dj_set (deep_focus series)...")
                result = await session.call_tool("create_dj_set", {
                    "name": "Deep_Focus_Ep2_Tulum",
                    "series": "deep_focus",
                    "episode": 2,
                })
                created = json.loads(result.content[0].text)
                print(f"  Created: {created.get('ok')}")
                print(f"  Series: {created.get('series')}, Episode: {created.get('episode')}")
                print(f"  Location: {created.get('location', {}).get('city')}")
                auto_title = created.get('auto_title')
                print(f"  Auto-title: {auto_title}")
                yt_tags = created.get('youtube_tags')
                if yt_tags:
                    print(f"  YouTube tags: {yt_tags[:3]}...")
                print(f"  YouTube hashtags: {created.get('youtube_hashtags')}")

                # Test: create_tracklist_from_timing
                print("\n[INFO] Testing create_tracklist_from_timing...")
                result = await session.call_tool("create_tracklist_from_timing", {
                    "name": "City_Pulse_Ep1_Istanbul",
                    "timing_file": "timing.json"
                })
                tracklist_result = json.loads(result.content[0].text)
                print(f"  OK: {tracklist_result.get('ok')}")
                print(f"  Track count: {tracklist_result.get('count')}")
                for t in tracklist_result.get('tracklist', [])[:3]:
                    print(f"    {t['timestamp']} - {t['title']}")

                # Test: generate_youtube_metadata (auto from meta)
                print("\n[INFO] Testing generate_youtube_metadata...")
                result = await session.call_tool("generate_youtube_metadata", {
                    "name": "City_Pulse_Ep1_Istanbul",
                    "artist": "DJ Famous"
                })
                yt_meta = json.loads(result.content[0].text)
                print(f"  Title: {yt_meta['title']}")
                print(f"  Description: {len(yt_meta['description'])} chars")
                print(f"  Tags: {yt_meta['tags'][:100]}...")
                print(f"  Hashtags: {yt_meta['hashtags']}")
                print(f"  Chapters: {len(yt_meta['chapters'])}")
                for ch in yt_meta['chapters'][:3]:
                    print(f"    {ch['timestamp']} - {ch['title']}")
                print(f"  Playlist: {yt_meta['playlist_id']}")
                print(f"  Premiere: {yt_meta['premiere_recommended']}")
                print(f"  End screen: {yt_meta['end_screen']}")
                print(f"  Cards: {len(yt_meta['cards'])}")

                # Test: Night Drive set metadata
                print("\n[INFO] Testing generate_youtube_metadata (Night_Drive_Ep1_LA)...")
                result = await session.call_tool("generate_youtube_metadata", {
                    "name": "Night_Drive_Ep1_LA",
                    "artist": "DJ Famous"
                })
                yt_meta = json.loads(result.content[0].text)
                print(f"  Title: {yt_meta['title']}")
                print(f"  Hashtags: {yt_meta['hashtags']}")
                print(f"  Thumbnail: {yt_meta['thumbnail_concept']}")

                # ===== SYSTEM TESTS =====
                print("\n========== SYSTEM TESTS ==========")

                # Test: check_upload_schedule
                print("\n[INFO] Testing check_upload_schedule...")
                result = await session.call_tool("check_upload_schedule", {})
                ritim = json.loads(result.content[0].text)
                print(f"  Daily: {ritim.get('daily_count')}, Weekly: {ritim.get('weekly_count')}")
                print(f"  Tempo OK: {ritim.get('tempo_ok')}")
                print(f"  Recent: {len(ritim.get('recent_uploads', []))}")

                # Test: health_check
                print("\n[INFO] Testing health_check...")
                result = await session.call_tool("health_check", {})
                health = json.loads(result.content[0].text)
                print(f"  Status: {health['status']}")
                print(f"  Dirs: {health['directories']}")
                print(f"  Modules OK: {health['modules']['ok']}")

                # Test: get_logs
                print("\n[INFO] Testing get_logs...")
                result = await session.call_tool("get_logs", {"lines": 5})
                logs = json.loads(result.content[0].text)
                for k, v in logs.items():
                    print(f"  {k}: {len(v)} chars")

                # Test: update_dj_set_state
                print("\n[INFO] Testing update_dj_set_state...")
                result = await session.call_tool("update_dj_set_state", {
                    "name": "Deep_Focus_Ep1_Bali",
                    "updates": {"custom_field": "test_value", "status": "ready_for_render"}
                })
                updated = json.loads(result.content[0].text)
                print(f"  Updated: {updated.get('ok')}")

                print("\n[OK] All tests passed!")

    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())