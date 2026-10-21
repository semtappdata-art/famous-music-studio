#!/usr/bin/env python3
"""YouTube kanal durumu okuma — 5 manuel işlem öncesi denetim."""
import os
import sys
import json

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

REPO = os.path.dirname(os.path.abspath(__file__))
UPLOAD = os.path.join(REPO, "upload")
sys.path.insert(0, UPLOAD)
sys.path.insert(0, REPO)

from youtube_auth import get_authenticated_service

CHANNEL_ID = "UCbbcH8rtQTtz8R66jfKoSZg"


def main():
    yt = get_authenticated_service()

    ch = yt.channels().list(
        part="snippet,brandingSettings,contentDetails,statistics",
        id=CHANNEL_ID,
    ).execute()["items"][0]

    sn = ch["snippet"]
    bs = ch.get("brandingSettings", {})
    chan_bs = bs.get("channel", {})

    print("=" * 70)
    print("KANAL:", sn.get("title"))
    print("HANDLE:", sn.get("customUrl") or sn.get("title"))
    print("=" * 70)

    desc = sn.get("description", "")
    print("\n--- ACIKLAMA (%d karakter) ---" % len(desc))
    print(desc if desc else "(BOS)")

    print("\n--- BANNER (image) ---")
    img = chan_bs.get("image", {})
    print("url:", img.get("url", "(YOK)"))

    print("\n--- KANAL LINKLERI ---")
    links = chan_bs.get("links", [])
    if links:
        for l in links:
            print(f"  [{l.get('rel')}] {l.get('title')} -> {l.get('url')}")
    else:
        print("  (YOK)")

    print("\n--- TRAILER (video) ---")
    tr = chan_bs.get("trailer", {})
    print("  videoId:", tr.get("videoId", "(YOK)"))

    print("\n--- KANAL BOLUMLERI (channelSections) ---")
    try:
        resp = yt.channelSections().list(
            part="snippet,contentDetails",
            channelId=CHANNEL_ID,
        ).execute()
        for it in resp.get("items", []):
            snip = it.get("snippet", {})
            cd = it.get("contentDetails", {})
            print(f"  pos={snip.get('position')} type={snip.get('type')} "
                  f"title={snip.get('title')} style={cd.get('style')}")
        if not resp.get("items"):
            print("  (YOK)")
    except Exception as e:
        print("  HATA:", e)

    print("\n--- OYNATMA LİSTELERİ ---")
    resp = yt.playlists().list(
        part="snippet,contentDetails",
        channelId=CHANNEL_ID,
        maxResults=100,
    ).execute()
    for p in resp.get("items", []):
        print(f"  {p['id']}  {p['snippet']['title']}  "
              f"({p['contentDetails'].get('itemCount', 0)} video, {p['snippet'].get('privacyStatus')})")

    print("\n--- KANAL VİDEOLARI (ilk 30) ---")
    resp = yt.search().list(
        part="snippet",
        channelId=CHANNEL_ID,
        type="video",
        order="date",
        maxResults=30,
    ).execute()
    for v in resp.get("items", []):
        s = v["snippet"]
        print(f"  {v['id']['videoId']}  {s.get('title', '')[:60]}")

    print("\n--- İSTATİSTİK ---")
    st = ch.get("statistics", {})
    for k, v in st.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
