# -*- coding: utf-8 -*-
"""
Chrome DevTools Protocol (CDP) istemcisi — agent_browser olmadan doğrudan.

NEDEN (2026-10-21): `mcp__chrome_devtools` bu oturumda yuklenmemisti ve
agent_browser CDP oturumu bir kez koptu (timeout 10060). Chrome'un debug
portu (9222) saglam kaldigi icin dogrudan WebSocket uzerinden Runtime.evaluate
yapmak daha guvenli.

Kullanim:
    python cdp.py <url_fragmani> "<js ifadesi>"
    python cdp.py --list
"""
import json
import sys
import urllib.request

import websocket

CDP = "http://127.0.0.1:9222"


def hedefler():
    with urllib.request.urlopen(CDP + "/json/list", timeout=8) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def sec(fragman):
    for t in hedefler():
        if t.get("type") == "page" and fragman in (t.get("url") or ""):
            return t
    return None


def deger(ws_url, ifade, zaman_asimi=30):
    ws = websocket.create_connection(ws_url, timeout=zaman_asimi,
                                    suppress_origin=True)
    try:
        ws.send(json.dumps({
            "id": 1, "method": "Runtime.evaluate",
            "params": {"expression": ifade, "returnByValue": True,
                       "awaitPromise": True, "userGesture": True},
        }))
        while True:
            msg = json.loads(ws.recv())
            if msg.get("id") == 1:
                if "error" in msg:
                    return {"hata": msg["error"]}
                res = msg.get("result", {}).get("result", {})
                if res.get("subtype") == "error":
                    return {"hata": res.get("description", "?")}
                return {"deger": res.get("value")}
    finally:
        ws.close()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    if sys.argv[1] == "--list":
        for t in hedefler():
            if t.get("type") == "page":
                print("  %-34s %s" % (t.get("id"), (t.get("url") or "")[:80]))
        return 0
    fragman = sys.argv[1]
    ifade = sys.argv[2] if len(sys.argv) > 2 else "1+1"
    t = sec(fragman)
    if not t:
        print("HEDEF BULUNAMADI: %s" % fragman)
        for x in hedefler():
            if x.get("type") == "page":
                print("  mevcut: %s" % (x.get("url") or "")[:80])
        return 2
    sonuc = deger(t["webSocketDebuggerUrl"], ifade)
    if "hata" in sonuc:
        print("HATA: %s" % json.dumps(sonuc["hata"])[:400])
        return 1
    d = sonuc.get("deger")
    if isinstance(d, (dict, list)):
        print(json.dumps(d, ensure_ascii=False, indent=1)[:20000])
    else:
        print(d)
    return 0


if __name__ == "__main__":
    sys.exit(main())
