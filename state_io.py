# -*- coding: utf-8 -*-
"""state.json yazimi icin TEK atomik yardimci.

NEDEN VAR: uc ayri yerde (`dj_tarama_kontrol._kaydet`,
`upload/youtube_upload._update_state`, `dj_famous_process._kaydet_durum`)
state.json dogrudan `open(..., "w")` ile HEDEFIN USTUNE yaziliyordu. `open`
dosyayi once SIFIRLIYOR; `json.dump` bitmeden surec olurse (guc kesintisi,
Gorev Zamanlayici timeout'unda TerminateProcess, paralel kosu) diskte YARIM
bir JSON kaliyor.

Bunun bedeli bugun buyudu: `uyumluluk._durum()` sertlestirildi ve bozuk bir
state.json artik sessizce `{}` sayilmiyor, `DurumBozuk` -> HATA uretip boru
hattini durduruyor. Yani yarim bir yazim artik yayini tamamen durduruyor.
Kaynagi duzeltmenin yeri burasi.

NEDEN AYRI MODUL (config.py degil): `config.py` gorunum/kalite ayarlarinin
yeri — disk G/C sorumlulugu oraya ait degil. Ayrica `upload/youtube_upload.py`
gibi alt klasordeki modullerin de ayni fonksiyonu cekmesi gerekiyor; kucuk ve
bagimsiz bir modul uc kopyayi tek yerde topluyor.
"""

import json
import os


def _atomik_metin_yaz(yol: str, metin: str) -> None:
    """Hazir bir METIN'i `yol`a atomik yazar (bkz. `_atomik_yaz`).

    NEDEN AYRI: bazi cagirilar JSON'u kendileri URETIYOR ve elimize sozluk
    degil STRING olarak veriyor — ornegi `upload/youtube_analytics.py`de
    `creds.to_json()`. Onu `json.loads` ile sozluge cevirip tekrar `json.dump`
    etmek kutuphanenin urettigi gosterimi bizim bicimlendirmemizle DEGISTIRIR
    (google-auth token dosyasini kendisi de yazip okuyor); token gibi bir
    dosyada bu gereksiz bir risk. Yerel bir tmp+replace kopyasi yazmak yerine
    burasi: atomik yazim deseni bu depoda zaten bir kez cogaltilip sorun
    olmustu, ikinci kez cogaltmanin anlami yok.
    """
    gecici = yol + ".tmp"
    with open(gecici, "w", encoding="utf-8") as f:
        f.write(metin)
        f.flush()
        os.fsync(f.fileno())      # icerik diske insin, sadece replace yetmez
    os.replace(gecici, yol)       # Windows'ta da atomik


def _atomik_yaz(yol: str, veri: dict) -> None:
    """`veri`yi `yol`a atomik yazar: ya tam eski hali ya tam yeni hali kalir.

    Once komsu bir `.tmp` dosyasina yazilip `os.replace` ile hedefin uzerine
    TASINIYOR. Hedef dosya bu sirada hic sifirlanmiyor — yazim yarida kesilirse
    yarim veri `.tmp`'de kalir, hedef ESKI (gecerli) halini korur.

    `flush` + `fsync` SART: `os.replace` tek basina sadece dizin girdisini
    degistirir; icerik hala isletim sistemi onbellegindeyse ani bir guc
    kesintisinde adi degismis ama ICI BOS/yarim bir dosya kalabilir.
    `os.replace` Windows'ta da atomik (MoveFileEx + REPLACE_EXISTING).

    `_atomik_metin_yaz`e DELEGE EDILMIYOR (kardes fonksiyon, asagida): yazim
    `json.dump` ile dogrudan dosyaya akiyor ki cok buyuyen bir durum sozlugu
    once tamamen bellekte string'e cevrilmek zorunda kalmasin — ve kesintinin
    `json.dump`in ORTASINDA olmasi testlerle taklit edilebilsin
    (tests/test_state_io.py). Atomiklik mantigi iki fonksiyonda birebir ayni.
    """
    gecici = yol + ".tmp"
    with open(gecici, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())      # icerik diske insin, sadece replace yetmez
    os.replace(gecici, yol)       # Windows'ta da atomik


def durum_yaz(proje: str, veri: dict) -> None:
    """`<proje>/state.json`i atomik yazar (yolu kendi kurar)."""
    _atomik_yaz(os.path.join(proje, "state.json"), veri)
