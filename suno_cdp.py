# -*- coding: utf-8 -*-
"""Suno.com'u CDP (Chrome DevTools Protocol) üzerinden yöneten yardımcı modül.

NEDEN VAR (2026-09-15): Suno işlemleri (üretim → varyant ölçümü → kazanan seçimi
→ WAV indirme) bu depoda tarayıcı otomasyonuyla yapılıyor ama önceki CDP betikleri
(`suno_hover.py`, `suno_modal_tara.py`) GEÇİCİ dosyalardı ve kayboldu. Bu modül
kalıcıdır: Chrome'u debug portuyla açar, `suno.com` sekmelerine bağlanır, JS
çalıştırır, tıklar, hover yapar ve indirilen dosyaları izler. Detaylı akış:
`suno_ab_secimi.md` "İndirme akışı (2026-09-14 — CDP ile create sayfasından WAV)".

KULLANIM (elle/ajan):
    chromeu = suno_cdp.ChromeCDP()
    chromeu.baslat()                    # /json (istenen sekmeleri listeler)
    sayfa = chromeu.sekme("suno.com")   # URL'si suno.com içeren ilk sekme
    sayfa.js("document.title")          # Runtime.evaluate
    sayfa.tikla('button[aria-label="More options"]')   # hover+tıkla
    sayfa.bekle_sure(3)
    chromeu.kapat()

İNDİRME: tarayıcının kendi indirme akışı `%USERPROFILE%\\Downloads`'a yazar;
`izle_indirme(onceki_anlık)` yeni dosyayı döndürür. WAV boyutu ~40 MB, MP3 ~5 MB.

ÜÇ SORU (CLAUDE.md):
1. Kim çağırıyor? Suno üretimini yapan ajan/insan, elle. Boru hattı çağırmıyor.
2. Hangi zamanlayıcı? Hiçbiri — Suno, render hatlarının (auto_process / haftalık
   dj_famous) DIŞINDA, tamamen etkileşimli bir adım.
3. Çalışmadığını nasıl anlarız? Her bağlantıda `başlat()` ya hata fırlatır ya da
   sekme listesi boş kalır; `js()` sonucu `exceptionDetails` içeriyorsa hata verir.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

import requests
import websocket

CHROME_YOLLARI = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
]

DEBUG_PORT = 9222
DEBUG_URL = "http://127.0.0.1:%d" % DEBUG_PORT
INDIRME_KOKU = os.path.expandvars(r"%USERPROFILE%\Downloads")


def chrome_bul() -> Optional[str]:
    for yol in CHROME_YOLLARI:
        if os.path.isfile(yol):
            return yol
    return None


def on_dizi(konu: str, **kwargs: Any) -> str:
    try:
        return json.dumps({"id": 1, "method": konu, "params": kwargs},
                          ensure_ascii=False)
    except TypeError:
        return json.dumps({"id": 1, "method": konu, "params": repr(kwargs)})


class SunoCDPHata(Exception):
    pass


class Sekme:
    """Bir CDP hedefine (sayfa sekmesi) bağlı WebSocket oturumu."""

    def __init__(self, ws_url: str):
        self._ws = websocket.create_connection(ws_url, timeout=20)
        self._kimlik = 0

    def _gonder(self, yontem: str, **params: Any) -> Any:
        self._kimlik += 1
        mesaj = {"id": self._kimlik, "method": yontem, "params": params}
        self._ws.send(json.dumps(mesaj, ensure_ascii=False))
        while True:
            yanit = json.loads(self._ws.recv())
            if yanit.get("id") == self._kimlik:
                if "error" in yanit:
                    raise SunoCDPHata("%s: %s" % (yontem, yanit["error"]))
                return yanit.get("result", {})

    def js(self, ifade: str) -> Any:
        """Sayfada JS çalıştırır; sonucu Python tipine çevirir."""
        sonuc = self._gonder("Runtime.evaluate",
                             expression=ifade, returnByValue=True,
                             awaitPromise=True)
        if "exceptionDetails" in sonuc:
            detay = sonuc["exceptionDetails"].get("exception", {})
            raise SunoCDPHata("js háta: %s" % detay.get("description",
                                                        sonuc["exceptionDetails"]))
        if "result" in sonuc and "value" in sonuc["result"]:
            return sonuc["result"]["value"]
        return None

    def _fare(self, tur: str, x: float, y: float) -> None:
        """CDP Input.dispatchMouseEvent — gerçek tarayıcı fare olayı.

        JS `element.click()` React'in yanıt vermediği durumlarda (ör. Suno'nun
        hover ile açılan menüleri) Input domain'inin ham olayı gerekir.
        """
        self._gonder("Input.dispatchMouseEvent",
                     type=tur, x=x, y=y)

    def tikla(self, secici: str, bekle_sn: float = 0.0) -> Dict[str, Any]:
        """Wait, yok— gerçek CDP tıklaması: öğeyi yakala, koordinata
        mousePressed+mouseReleased gönder.

        Döner: {'bulundu': bool, 'merkez': [x,y]} — bulunmadıysa merkez None.
        """
        kutu = self.js("""
          (() => {
            const e = document.querySelector(arg0); if (!e) return null;
            const r = e.getBoundingClientRect();
            return {x: r.left + r.width/2, y: r.top + r.height/2,
                    w: r.width, h: r.height};
          })()
        """)
        # arg0 geçemeyiz — seciciyi string'e gömyoruz:
        kutu = self.js("""
          (() => {
            const e = document.querySelector(%s); if (!e) return null;
            const r = e.getBoundingClientRect();
            return {x: r.left + r.width/2, y: r.top + r.height/2, boyut: r.width};
          })()
        """ % json.dumps(secici))
        if not kutu:
            return {"bulundu": False, "merkez": None}
        x, y = kutu["x"], kutu["y"]
        self._fare("mouseMoved", x, y)
        self._fare("mousePressed", x, y)
        self._fare("mouseReleased", x, y)
        if bekle_sn:
            time.sleep(bekle_sn)
        return {"bulundu": True, "merkez": [round(x), round(y)]}

    def kapat(self) -> None:
        try:
            self._ws.close()
        except Exception:
            pass


class ChromeCDP:
    def __init__(self, port: int = DEBUG_PORT, kullan: Optional[str] = None) -> None:
        self._port = port
        self._temyiz: Optional[subprocess.Popen] = None
        self._kullan = kullan

    # --- Başlatma / tarayıcı işlemleri ---

    def calisiyor(self) -> bool:
        try:
            requests.get(DEBUG_URL + "/json/version", timeout=1)
            return True
        except Exception:
            return False

    def baslat(self, url: str = "https://suno.com/create") -> None:
        """Debug portu açık Chrome bulamazsa temiz profille yeni bir tane açar.

        YENİ PROFİL → Suno GİRİŞİ HİÇBİR ZAMAN YOK. Kullanıcının oturumu mevcut
        Chrome'un profilinde duruyor; bu yüzden gerçek kullanımda Chrome elle
        `--remote-debugging-port=%d` ile (Mevcut profille) yeniden başlatılır ve
        bu fonksiyon yalnızca bağlanır. `baslat()` otomatik yeni-Chrome-açma
        YOLU, yalnızca profil sorununun olmadığı adım testleri (tıkla/JS) içindir.
        """
        if self.calisiyor():
            return
        yol = chrome_bul()
        if not yol:
            raise SunoCDPHata("Chrome bulunamadı")
        args = [yol, "--remote-debugging-port=%d" % self._port,
                "--remote-allow-origins=*"]
        if self._kullan:
            args.append("--user-data-dir=%s" % self._kullan)
        args.append(url)
        self._temyiz = subprocess.Popen(args, stdout=subprocess.DEVNULL,
                                        stderr=subprocess.DEVNULL)
        for _ in range(30):
            if self.calisiyor():
                return
            time.sleep(0.5)
        raise SunoCDPHata("Chrome açılmadı (%d sn)" % 15)

    def sekmeler(self) -> List[Dict[str, Any]]:
        if not self.calisiyor():
            raise SunoCDPHata("Debug portu kapalı (%d). Chrome'u "
                              "--remote-debugging-port ile başlat." % self._port)
        yanit = requests.get(DEBUG_URL + "/json", timeout=3).json()
        return [t for t in yanit if t.get("type") == "page"]

    def sekme(self, url_icerir: str = "") -> Sekme:
        for bilgi in self.sekmeler():
            if url_icerir.lower() in bilgi.get("url", "").lower():
                return Sekme(bilgi["webSocketDebuggerUrl"])
        raise SunoCDPHata("'%s' içeren sekme yok. Sayfalar: %s"
                          % (url_icerir, [t.get("url") for t in self.sekmeler()]))

    def sonsayfa(self) -> Sekme:
        sekmeler = self.sekmeler()
        if not sekmeler:
            raise SunoCDPHata("Açık sayfa yok")
        return Sekme(sekmeler[-1]["webSocketDebuggerUrl"])

    def kapat(self) -> None:
        if self._temyiz is not None:
            try:
                self._temyiz.terminate()
            except Exception:
                pass
            self._temyiz = None

    # --- İndirme izleme ---

    def indirme_anlik(self) -> Dict[str, float]:
        """Downloads klasöründeki dosya adı -> boyut."""
        sonuc: Dict[str, float] = {}
        if not os.path.isdir(INDIRME_KOKU):
            return sonuc
        for ad in os.listdir(INDIRME_KOKU):
            yol = os.path.join(INDIRME_KOKU, ad)
            if os.path.isfile(yol):
                try:
                    sonuc[ad] = os.path.getsize(yol)
                except OSError:
                    pass
        return sonuc

    def izle_indirme(self, onceki: Dict[str, float],
                     bekle_sn: int = 90) -> Optional[str]:
        """`onceki` anlık görüntüsünden SONRA Downloads'a inen yeni dosya."""
        bas = time.time()
        while time.time() - bas < bekle_sn:
            suan = self.indirme_anlik()
            for ad, boyut in suan.items():
                if ad not in onceki or onceki[ad] != boyut:
                    # İndirme "devam ediyor" olabilir (boyut büyüyor): kararlı
                    # olana kadar bekle.
                    if self._kararli_dosya(ad, boyut):
                        return ad
            time.sleep(1)
        return None

    def _kararli_dosya(self, ad: str, boyut: int, deneme: int = 5) -> bool:
        yol = os.path.join(INDIRME_KOKU, ad)
        for _ in range(deneme):
            time.sleep(0.6)
            try:
                if os.path.getsize(yol) != boyut or not os.path.isfile(yol):
                    return False
            except OSError:
                return False
        return True

    # --- Tarayıcı yardımcıları (Sekme üzerinden de erişilebilir) ---

    def sayfa_ac(self, url: str) -> Sekme:
        sonuc = requests.put(DEBUG_URL + "/json/new", params={"url": url},
                             timeout=5)
        if sonuc.status_code != 200:
            raise SunoCDPHata("Sekme açılamadı: %d" % sonuc.status_code)
        bilgi = sonuc.json()
        return Sekme(bilgi["webSocketDebuggerUrl"])


def main(argv=None) -> int:
    import argparse
    p = argparse.ArgumentParser(description="Chrome CDP durum kontrolü (YAN ETKİSİZ).")
    p.add_argument("--liste", action="store_true", help="Açık sekmeleri listele")
    a = p.parse_args(argv)
    c = ChromeCDP()
    if not c.calisiyor():
        print("Chrome debug portu KAPALI (%d)." % DEBUG_PORT)
        print("Başlatma örneği: \"chrome.exe\" "
              "--remote-debugging-port=%d https://suno.com/create" % DEBUG_PORT)
        return 1
    print("Chrome debug portu AÇIK (%d)." % DEBUG_PORT)
    if a.liste:
        for t in c.sekmeler():
            print("  -", t.get("title", ""), "|", t.get("url", ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())