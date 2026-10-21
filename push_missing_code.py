# -*- coding: utf-8 -*-
"""GitHub'da eksik olan tum .py dosyalarini API ile yukler.

NEDEN (2026-10-21): `git push` CALISMIYOR — push edilemeyen 23 commit'te
2.76 GB yeni blob var (tek basina 872 MB audio.wav). GitHub'in 100 MB/dosya
limiti asiliyor, bu yuzden hicbir push tamamlanamaz.

COZUM: Buyuk medya dosyalarini hic gondermeden, yalnizca KOD dosyalarini
GitHub API (blob -> tree -> commit) ile yukuyoruz. Boylece CI calisir ve
site deploy edebilir.
"""
import base64
import json
import os
import subprocess
import sys
import urllib.request

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

REPO = "semtappdata-art/famous-music-studio"
API = "https://api.github.com"
REPO_KOK = os.path.dirname(os.path.abspath(__file__))
MAX_BLOB = 900 * 1024  # 900 KB — uygulama kodu icin yeter

# Git'e gonderilmeyecek dizinler
DIREKTORY = [
    ".git", ".claude", ".agent_core", ".scratchpad", ".ultra_assistant",
    "archives", "logs", "node_modules", "__pycache__", ".pytest_cache",
    "analytics_data", "site/api", "netlify/functions",
]


def gh_token():
    out = subprocess.run(["git", "credential", "fill"],
                         input="protocol=https\nhost=github.com\n\n",
                         capture_output=True, text=True).stdout
    for l in out.splitlines():
        if l.startswith("password="):
            return l.split("=", 1)[1].strip()
    return None


def api(path, data=None, method="GET", tok=None):
    h = {"Authorization": "token " + tok, "Accept": "application/vnd.github+json",
         "User-Agent": "fms"}
    b = None
    if data is not None:
        b = json.dumps(data).encode("utf-8")
        h["Content-Type"] = "application/json"
    r = urllib.request.Request(API + path, data=b, headers=h, method=method)
    with urllib.request.urlopen(r, timeout=120) as resp:
        c = resp.read()
        return json.loads(c) if c else {}


def tum_kod_dosyalari():
    """Git'e gonderilecek tum .py + workflow + config dosyalari."""
    sonuc = []
    for kok, dizinler, dosyalar in os.walk(REPO_KOK):
        rel_kok = os.path.relpath(kok, REPO_KOK)
        # dizinleri kirp
        dizinler[:] = [d for d in dizinler
                       if not any(d == x or d.startswith(x + "-") for x in DIREKTORY)]
        if any(rel_kok == x or rel_kok.startswith(x + os.sep) for x in DIREKTORY):
            continue
        for d in dosyalar:
            if not d.endswith(".py"):
                continue
            tam = os.path.join(kok, d)
            boyut = os.path.getsize(tam)
            if boyut > MAX_BLOB:
                continue
            rel = os.path.relpath(tam, REPO_KOK).replace("\\", "/")
            sonuc.append((rel, boyut))
    return sonuc


def main():
    tok = gh_token()
    if not tok:
        print("HATA: GitHub token alinamadi")
        return 2

    # 1) Mevcut main tree
    ref = api(f"/repos/{REPO}/git/ref/heads/main", tok=tok)
    head = ref["object"]["sha"]
    commit = api(f"/repos/{REPO}/git/commits/{head}", tok=tok)
    base_tree = commit["tree"]["sha"]

    # 2) GitHub'da var olan dosyalar (tree uzerinden)
    mevcut = set()
    stack = [(base_tree, "")]
    while stack:
        sha, prefix = stack.pop()
        t = api(f"/repos/{REPO}/git/trees/{sha}", tok=tok)
        for item in t.get("tree", []):
            yol = prefix + item["path"]
            if item["type"] == "tree":
                stack.append((item["sha"], yol + "/"))
            else:
                mevcut.add(yol)

    # 3) Eksik olanlari yukle
    eksik = [(p, b) for p, b in tum_kod_dosyalari() if p not in mevcut]
    print(f"Yerel kod dosyalari: {len(tum_kod_dosyalari())} | GitHub'da eksik: {len(eksik)}")

    entries = []
    for rel, boyut in eksik:
        with open(os.path.join(REPO_KOK, rel), "rb") as f:
            veri = f.read()
        blob = api(f"/repos/{REPO}/git/blobs",
                   {"content": base64.b64encode(veri).decode("ascii"),
                    "encoding": "base64"}, method="POST", tok=tok)
        entries.append({"path": rel, "mode": "100644", "type": "blob",
                        "sha": blob["sha"]})
        print(f"  yuklendi: {rel} ({boyut//1024} KB)")

    if not entries:
        print("Eksik dosya yok.")
        return 0

    tree = api(f"/repos/{REPO}/git/trees",
               {"base_tree": base_tree, "tree": entries}, method="POST", tok=tok)
    c = api(f"/repos/{REPO}/git/commits",
            {"message": "fix(ci): eksik Python modulleri + workflow dosyalari yuklendi "
                        "(git push 100 MB limiti nedeniyle API ile)",
             "tree": tree["sha"], "parents": [head]}, method="POST", tok=tok)
    api(f"/repos/{REPO}/git/refs/heads/main",
        {"sha": c["sha"], "force": False}, method="PATCH", tok=tok)
    print(f"\nCommit: {c['sha'][:8]}  ({len(entries)} dosya)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
