# -*- coding: utf-8 -*-
"""
CDP ile OpenRouter'da yeni API anahtari olusturur ve TAM anahtari yakalar.

NEDEN: OpenRouter anahtari DOM'da MASKELI gosterir ("sk-or-v1-d5f•••1606").
Tek gorunur kopyalama yolu panoya yaziyor; pano okunamayinca (document
not focused) anahtar kayboluyor. Cozum: fetch/XHR interceptor — anahtarin
olusturuldugu API yanitinin govdesi tam anahtari icerir.

Akis: New Key -> ad -> No expiration -> $50 limit -> Create -> yaniti yakala.
"""
import json
import sys
import time
import urllib.parse
import urllib.request

import websocket

CDP = "http://127.0.0.1:9222"
HEDEF = "https://openrouter.ai/workspaces/default/keys"

JS = r"""
(async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const out = {};
  const setVal = (el, v) => {
    const proto = Object.getPrototypeOf(el);
    const desc = Object.getOwnPropertyDescriptor(proto, 'value');
    desc.set.call(el, v);
    el.dispatchEvent(new Event('input', {bubbles: true}));
    el.dispatchEvent(new Event('change', {bubbles: true}));
  };
  const clickText = (root, text) => {
    const els = [...root.querySelectorAll('div,li,button,span,option')].filter(
      e => (e.textContent||'').trim() === text && e.offsetParent !== null);
    if (!els.length) return false;
    els[els.length-1].click();
    return true;
  };

  // 1) New Key modalini ac
  const nk = [...document.querySelectorAll('button')].find(
    e => (e.textContent||'').trim() === 'New Key');
  if (!nk) return JSON.stringify({hata: 'New Key butonu yok'});
  nk.click();
  await sleep(1200);

  // 2) Ad
  const inp = document.querySelector('input[placeholder*="Chatbot"]');
  if (!inp) return JSON.stringify({hata: 'ad inputu yok'});
  setVal(inp, 'fms-production');
  await sleep(400);

  // 3) Expiration -> No expiration
  const expBtn = [...document.querySelectorAll('[role=dialog] button')].find(
    e => (e.textContent||'').trim() === 'Select expiration');
  if (!expBtn) return JSON.stringify({hata: 'expiration dropdown yok'});
  expBtn.click();
  await sleep(700);
  if (!clickText(document.body, 'No expiration'))
    return JSON.stringify({hata: 'No expiration secenegi yok'});
  await sleep(700);

  // 4) Credit limit -> $50
  const limBtn = [...document.querySelectorAll('[role=dialog] button')].find(
    e => (e.textContent||'').trim() === 'Choose a credit limit');
  if (!limBtn) return JSON.stringify({hata: 'limit dropdown yok'});
  limBtn.click();
  await sleep(700);
  if (!clickText(document.body, '$50'))
    return JSON.stringify({hata: '$50 secenegi yok'});
  await sleep(700);

  out.form = [...document.querySelectorAll('[role=dialog] button')]
    .map(e => (e.textContent||'').trim())
    .filter(t => t === 'No expiration' || t === '$50');

  // 5) Create
  const cr = [...document.querySelectorAll('[role=dialog] button')].find(
    e => (e.textContent||'').trim() === 'Create');
  if (!cr) return JSON.stringify({hata: 'Create butonu yok'});
  cr.click();

  // 6) Yaniti bekle
  for (let i = 0; i < 40; i++) {
    await sleep(500);
    const caps = window.__cap || [];
    for (const c of caps) {
      const m = (c.body||'').match(/sk-or-v1-[A-Za-z0-9_-]{30,}/);
      if (m) return JSON.stringify({ok: true, key: m[0], url: c.url});
    }
  }
  // Yakalanamadiysa DOM'a bak (bazen tam deger DOM'da olur)
  const dom = (document.body.innerText.match(/sk-or-v1-[A-Za-z0-9_-]{30,}/)||[])[0] || null;
  return JSON.stringify({ok: false, dom: dom, caps: (window.__cap||[]).length});
})()
"""


def yeni_hedef(url):
    req = urllib.request.Request(
        CDP + "/json/new?" + urllib.parse.quote(url, safe=":/?=&"), method="PUT")
    return json.loads(urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "replace"))


def main():
    t = yeni_hedef(HEDEF)
    print("hedef:", t.get("id"))
    time.sleep(7)
    ws = websocket.create_connection(t["webSocketDebuggerUrl"], timeout=90,
                                    suppress_origin=True)
    try:
        # interceptor
        ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate", "params": {
            "expression": "(function(){window.__cap=[];var of=window.fetch;window.fetch=function(){"
                          "var p=Array.prototype.slice.call(arguments);return of.apply(this,p).then(function(r){"
                          "try{var c=r.clone();c.text().then(function(t){if(t&&t.indexOf('sk-or-v1-')>=0){"
                          "window.__cap.push({url:String(p[0]&&p[0].url?p[0].url:p[0]),body:t.slice(0,8000)});}})"
                          ".catch(function(){});}catch(e){}return r;});};return 'ok';})()",
            "returnByValue": True}}))
        # akis
        ws.send(json.dumps({"id": 2, "method": "Runtime.evaluate", "params": {
            "expression": JS, "returnByValue": True, "awaitPromise": True,
            "userGesture": True}}))
        while True:
            m = json.loads(ws.recv())
            if m.get("id") == 2:
                r = m.get("result", {}).get("result", {})
                val = r.get("value")
                if val is None:
                    val = r.get("description", "?")
                print(val)
                break
    finally:
        ws.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
