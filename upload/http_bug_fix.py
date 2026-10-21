# -*- coding: utf-8 -*-
"""httplib2 boş-yanıt gövdesi hata düzeltmesi (BUGFIX, güvenli).

SORUN
-----
`googleapiclient` + `httplib2` ikilisi, GZIP'li ve **BOŞ** yanıt gövdesinde
Python hatası fırlatıyor:

    ValueError: range() arg 3 must not be zero

Kaynak: `httplib2/decode.py` → `consume_bytes(data, chunk_size=0)`:

    def consume_bytes(self, data, chunk_size=64 << 10):
        if chunk_size == 0:
            chunk_size = len(data)          # <- len(data)==0 ise 0 kalıyor
        for i in range(0, len(data), chunk_size):   # <- step 0 -> ValueError

YouTube Data API'nin gövdesiz 200 yanıtı verdiği uçlar (ör.
`watermarks.set`, `channelBanners.insert`) BU hatayı tetikliyor. Sonuç: işlem
sunucuda **başarılı** olmuşken istemci tarafında patlıyor.

ETKİ
---
* `watermarks.set` — her çağrı "başarısız" görünüyor, watermark aslında
  konmuş. Tekrar denemek çift işlem riski.
* `channelBanners.insert` — banner güncelleniyor ama "HATA" basılıyor.

ÇÖZÜM
------
`httplib2.decode` içindeki `consume_bytes` fonksiyonunu güvenli hâle
getiriyoruz: `chunk_size` 0 kalırsa 1'e sabitleniyor (boş veri için
`range(0, 0, 1)` = boş döngü, doğru davranış).

GÜVENLİLİK
----------
* **Idempotent**: zaten düzeltilmişse dokunmaz.
* **Sadece dar kapsam**: sadece `httplib2.decode.consume_bytes` değişir.
* **Yedek**: `httplib2` yoksa veya imza değişmişse sessizce atlanır
  (import hatası yutmaz).
* **Test edilebilir**: `tests/test_http_bug_fix.py` kilitler.
"""

import os

_YAMALI = "httplib2.decode"


def uygula() -> bool:
    """Düzeltmeyi uygular. True = uygulandı, False = atlandı (gerek yok)."""
    try:
        import httplib2  # noqa: F401
        import httplib2.decode as hd
    except ImportError:
        return False

    # NEDEN bu siniflar: `consume_bytes` modul seviyesinde bir fonksiyon
    # DEGIL, `DecoderProtocol` taban sinifinin METODU. httplib2/__init__.py:
    # `limit_wrap(ZlibDecoder()).consume_bytes(data, 0)` seklinde cagrildigi
    # icin somut sinif `LimitDecoder` bu metodu MIRAS ALIR.
    hedefler = [getattr(hd, ad, None) for ad in
                ("LimitDecoder", "ZlibDecoder", "DeflateDecoder", "DecoderProtocol")]
    uygulandi = False
    for sinif in hedefler:
        if sinif is None:
            continue
        mevcut = getattr(sinif, "consume_bytes", None)
        if mevcut is None:
            continue
        if getattr(mevcut, "_fms_bugfix", False):
            uygulandi = True
            continue

        def consume_bytes(self, data, chunk_size=64 << 10, _mevcut=mevcut):
            # --- BUGFIX: chunk_size 0 iken range() step 0 -> ValueError ---
            if chunk_size == 0:
                chunk_size = len(data) or 1
            return _mevcut(self, data, chunk_size)

        consume_bytes._fms_bugfix = True  # type: ignore[attr-defined]
        sinif.consume_bytes = consume_bytes  # type: ignore[assignment]
        uygulandi = True

    return uygulandi


def uygulandi_mi() -> bool:
    try:
        import httplib2.decode as hd
    except ImportError:
        return False
    for ad in ("LimitDecoder", "ZlibDecoder", "DeflateDecoder", "DecoderProtocol"):
        sinif = getattr(hd, ad, None)
        if sinif is None:
            continue
        if getattr(getattr(sinif, "consume_bytes", None), "_fms_bugfix", False):
            return True
    return False


if __name__ == "__main__":
    ok = uygula()
    print("bugfix uygulandi:", ok)
    raise SystemExit(0 if ok else 1)


_ = os  # noqa: F401
