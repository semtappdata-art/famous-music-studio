# -*- coding: utf-8 -*-
"""4 sayfada TR/EN gecisini tarayicida dogrular (Madde 31 dogrulama)."""
import json
import shutil
import subprocess
import sys
import time

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

SAYAFALAR = [
    ("/", "index"),
    ("/privacy.html", "privacy"),
    ("/epk/bio.html", "epk"),
    ("/404.html", "404"),
]

JS = """(function(){
  var out = {dil: window.FMS_I18N ? window.FMS_I18N.dil() : 'YOK',
             toggle: !!document.querySelector('[data-dil-btn=\\"en\\"]')};
  function topla(){
    var h1 = document.querySelector('h1');
    var h2 = document.querySelector('h2');
    out.h1 = h1 ? h1.textContent.trim() : '';
    out.h2 = h2 ? h2.textContent.trim() : '';
    out.lang = document.documentElement.lang;
    var kotu = [];
    document.querySelectorAll('[data-i18n]').forEach(function(el){
      var t = el.innerHTML;
      if (t.indexOf('<p>') >= 0 || t.indexOf('&amp;') >= 0 || t.indexOf('&lt;') >= 0) {
        kotu.push(el.getAttribute('data-i18n'));
      }
    });
    out.kirli = kotu;
    out.ciftP = document.body.innerHTML.indexOf('<p><p>') >= 0;
  }
  topla();
  out.tr = {h1: out.h1, h2: out.h2};
  document.querySelector('[data-dil-btn=\\"en\\"]').click();
  return new Promise(function(res){
    setTimeout(function(){
      topla();
      out.en = {h1: out.h1, h2: out.h2};
      res(JSON.stringify(out));
    }, 400);
  });
})()"""


def main():
    port = "8791"
    ab = shutil.which("agent-browser") or "agent-browser"
    for yol, ad in SAYAFALAR:
        url = "http://127.0.0.1:%s%s?v=%d" % (port, yol, int(time.time()))
        r = subprocess.run(
            [ab, "--session", "i18n-verify", "open", url, "--wait", "2500"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
        )
        time.sleep(0.6)
        r2 = subprocess.run(
            [ab, "--session", "i18n-verify", "eval", JS],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
        )
        cikti = (r2.stdout or "").strip()
        # JSON bul
        bas = cikti.find("{")
        son = cikti.rfind("}")
        veri = {}
        if bas >= 0 and son > bas:
            try:
                veri = json.loads(cikti[bas:son + 1])
            except json.JSONDecodeError:
                pass
        if not veri:
            print("  [FAIL] %-16s cevap alinamadi: %s" % (ad, cikti[:120]))
            continue
        ok = (
            veri.get("toggle")
            and veri.get("dil") == "en"
            and veri.get("lang") == "en"
            and not veri.get("kirli")
            and not veri.get("ciftP")
            and veri.get("tr", {}).get("h1") != veri.get("en", {}).get("h1")
            and bool(veri.get("tr", {}).get("h1"))
        )
        print("  [%s] %-16s toggle=%s dil=%s kirli=%s ciftP=%s" % (
            "PASS" if ok else "FAIL", ad, veri.get("toggle"), veri.get("dil"),
            veri.get("kirli") or "-", veri.get("ciftP")))
        print("        TR: %s" % (veri.get("tr", {}).get("h1") or "")[:52])
        print("        EN: %s" % (veri.get("en", {}).get("h1") or "")[:52])


if __name__ == "__main__":
    main()
