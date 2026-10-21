#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Pages icerigini GitHub API ile yayinlar (docs/ alt-yolu).

NEDEN API (2026-10-21): repo 4.4 GB; `git push` HTTP 408 (timeout) veriyor.
Sadece docs/ altindaki site dosyalarini API ile yuklemek hem hizli hem
guvenli — dev pack gonderilmez, gecmis degismez.

Kullanim:
    python publish_site_github.py            # docs/ -> GitHub (main branch)
    python publish_site_github.py --dry-run
"""
import base64
import hashlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

REPO = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(REPO, "site")
DOCS = os.path.join(REPO, "docs")
OWNER = "semtappdata-art"
REPO_NAME = "famous-music-studio"
API = "https://api.github.com"

# docs/ altinda yayinlanacak dosyalar (site/ -> docs/ eslemesi)
DOSYALAR = [
    "index.html", "404.html", "privacy.html", "analytics.js", "i18n.js",
    "robots.txt", "sitemap.xml", "og-cover.jpg", ".nojekyll",
    "assets/youtube-banner-2560x1440.png",
    "assets/brand/icon_big.jpg",
    "epk/bio.html", "epk/bio.json", "epk/bio.md", "epk/booking.md",
    "epk/index.json", "epk/music_assets_README.md", "epk/photos_README.md",
]


def token_al():
    """GitHub PAT: git credential store veya GITHUB_TOKEN ortam degiskeni."""
    ortam = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if ortam:
        return ortam.strip()
    try:
        out = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=github.com\n\n",
            capture_output=True, text=True, timeout=30,
        ).stdout
        for satir in out.splitlines():
            if satir.startswith("password="):
                return satir.split("=", 1)[1].strip()
    except Exception:
        pass
    return None


def api(yol, veri=None, method="GET", token=None):
    url = API + yol
    headers = {
        "Authorization": "token " + token,
        "Accept": "application/vnd.github+json",
        "User-Agent": "fms-publish",
    }
    govde = None
    if veri is not None:
        govde = json.dumps(veri).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=govde, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=120) as r:
        ic = r.read()
        return json.loads(ic) if ic else {}


def main():
    dry = "--dry-run" in sys.argv
    token = token_al()
    if not token:
        print("HATA: GitHub PAT bulunamadi (git credential fill veya GITHUB_TOKEN).")
        return 2

    # 1) Mevcut main commit + tree
    ref = api(f"/repos/{OWNER}/{REPO_NAME}/git/ref/heads/main", token=token)
    head_sha = ref["object"]["sha"]
    commit = api(f"/repos/{OWNER}/{REPO_NAME}/git/commits/{head_sha}", token=token)
    base_tree = commit["tree"]["sha"]
    print(f"main HEAD: {head_sha[:8]}  tree: {base_tree[:8]}")

    # 2) Blob'olustur
    yeni_girdiler = []
    for rel in DOSYALAR:
        kaynak = os.path.join(SITE, rel.replace("/", os.sep))
        hedef = os.path.join(DOCS, rel.replace("/", os.sep))
        if not os.path.isfile(kaynak):
            print(f"  ATLANDI (yok): {rel}")
            continue
        with open(kaynak, "rb") as f:
            veri = f.read()
        # degismediyse atla (sha ayni)
        yeni_sha = hashlib.sha1(b"blob %d\0" % len(veri) + veri).hexdigest()
        mevcut = None
        if os.path.isfile(hedef):
            with open(hedef, "rb") as f:
                mevcut = hashlib.sha1(b"blob %d\0" % len(f.read()) + f.read()).hexdigest()
        if mevcut == yeni_sha:
            print(f"  ayni (atlandi): {rel}")
            continue
        if dry:
            print(f"  [KURU] blob yuklenecek: {rel} ({len(veri)} bayt)")
            yeni_girdiler.append({"path": "docs/" + rel, "mode": "100644",
                                  "type": "blob", "sha": None, "_veri": veri})
            continue
        blob = api(f"/repos/{OWNER}/{REPO_NAME}/git/blobs", {
            "content": base64.b64encode(veri).decode("ascii"),
            "encoding": "base64",
        }, method="POST", token=token)
        print(f"  yuklendi: {rel} ({len(veri)//1024} KB)")
        yeni_girdiler.append({
            "path": "docs/" + rel,
            "mode": "100644",
            "type": "blob",
            "sha": blob["sha"],
        })

    if not yeni_girdiler:
        print("Degisiklik yok — docs/ guncel.")
        return 0
    if dry:
        return 0

    # 3) Tree olustur
    tree = api(f"/repos/{OWNER}/{REPO_NAME}/git/trees", {
        "base_tree": base_tree,
        "tree": yeni_girdiler,
    }, method="POST", token=token)

    # 4) Commit
    yeni_commit = api(f"/repos/{OWNER}/{REPO_NAME}/git/commits", {
        "message": "docs: site yayinlandi (Madde 25-31: tarz secici, analitik, topluluk, dil toggle)",
        "tree": tree["sha"],
        "parents": [head_sha],
    }, method="POST", token=token)

    # 5) Ref guncelle
    api(f"/repos/{OWNER}/{REPO_NAME}/git/refs/heads/main", {
        "sha": yeni_commit["sha"],
        "force": False,
    }, method="PATCH", token=token)

    print(f"\nCommit olusturuldu: {yeni_commit['sha'][:8]}")
    print(f"GitHub Pages: https://{OWNER}.github.io/{REPO_NAME}/")
    print("Pages buildi baslayacak (1-3 dk).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
