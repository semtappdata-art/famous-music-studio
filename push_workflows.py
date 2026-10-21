# -*- coding: utf-8 -*-
"""GitHub'a YENI dizin iceren dosya yukler (3 adimli tree).

SORUN (2026-10-21): `git/trees` API'si `base_tree` ile **yeni dizin
olusturan** bir path ekleyemiyor -> "Not Found" (404). Dizin GitHub tarafindan
otomatik olusturulmuyor.

COZUM (3 adim):
  1. `.github/workflows/` icerigini AYRI bir tree olarak kur (base_tree YOK)
     -> t1
  2. `.github/workflows` dizinini base_tree'ye "tree" tipi entry olarak ekle
     -> t2
  3. `.github` dizinini t2'ye "tree" tipi entry olarak ekle
     -> t3
  4. t3'ü main'in base_tree'sine ekle -> commit -> ref

Not: Adim 1'de base_tree verilMEZ; sadece o dizinin icerigi verilir.
"""
import base64
import json
import os
import subprocess
import sys
import urllib.request
import urllib.error

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

REPO = "semtappdata-art/famous-music-studio"
API = "https://api.github.com"
REPO_KOK = os.path.dirname(os.path.abspath(__file__))

HEDEFLER = [
    ".github/workflows/ci.yml",
    ".github/workflows/deploy-site.yml",
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
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            c = resp.read()
            return json.loads(c) if c else {}
    except urllib.error.HTTPError as e:
        det = e.read().decode("utf-8", "replace")[:200]
        raise RuntimeError("%s %s -> %s" % (method, path, det))


def main():
    tok = gh_token()

    # --- mevcut main ---
    head = api(f"/repos/{REPO}/git/ref/heads/main", tok=tok)["object"]["sha"]
    main_tree = api(f"/repos/{REPO}/git/commits/{head}", tok=tok)["tree"]["sha"]
    print(f"  main head: {head[:8]}  tree: {main_tree[:8]}")

    # --- 0) blob'lari yukle ---
    blobs = {}
    for f in HEDEFLER:
        veri = open(os.path.join(REPO_KOK, f), "rb").read()
        b = api(f"/repos/{REPO}/git/blobs",
                {"content": base64.b64encode(veri).decode("ascii"),
                 "encoding": "base64"}, method="POST", tok=tok)
        blobs[f] = b["sha"]
        print(f"  blob: {f} ({len(veri)//1024} KB)")

    # --- 1-3) tree zinciri (asagida, commit adiminda tekrarlanir) ---
    wf_entries = [{"path": os.path.basename(f), "mode": "100644", "type": "blob",
                   "sha": blobs[f]} for f in HEDEFLER]

    # --- 4) commit + ref ---
    # NOT: arada Pages/CI workflow'u commit atabiliyor -> head degisiyor ->
    # PATCH "Not Found" veriyor. Her denemede head TAZE alinir.
    son_hata = None
    for deneme in range(1, 5):
        try:
            head = api(f"/repos/{REPO}/git/ref/heads/main", tok=tok)["object"]["sha"]
            main_tree = api(f"/repos/{REPO}/git/commits/{head}", tok=tok)["tree"]["sha"]

            t1 = api(f"/repos/{REPO}/git/trees", {"tree": wf_entries},
                     method="POST", tok=tok)
            t2 = api(f"/repos/{REPO}/git/trees",
                     {"base_tree": t1["sha"],
                      "tree": [{"path": "workflows", "mode": "040000",
                                "type": "tree", "sha": t1["sha"]}]},
                     method="POST", tok=tok)
            t3 = api(f"/repos/{REPO}/git/trees",
                     {"base_tree": main_tree,
                      "tree": [{"path": ".github", "mode": "040000",
                                "type": "tree", "sha": t2["sha"]}]},
                     method="POST", tok=tok)
            c = api(f"/repos/{REPO}/git/commits",
                    {"message": "ci: kendi workflow dosyalari + pytest.ini collect_ignore + eksik moduller",
                     "tree": t3["sha"], "parents": [head]},
                    method="POST", tok=tok)
            # Ref guncelleme: urllib PATCH bu repo'da 404 veriyor
            # (curl/gh ile calisiyor) -> commit SHA'sini basilip
            # cikis ile gh api'ye devrediyoruz.
            print(f"COMMIT_SHA={c['sha']}")
            return 0
        except Exception as e:
            son_hata = e
            print(f"  deneme {deneme} basarisiz: {str(e)[:110]}")
            import time as _t
            _t.sleep(4)
    raise son_hata


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print("  HATA:", e)
        sys.exit(1)
