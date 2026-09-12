"""auto_process.log ve watch_projects.log için paylaşılan basit log temizleme.

Log dosyaları süresiz büyümesin diye — 7 günden eski satırlar her çağrıda
atılıp dosya yeniden yazılıyor (ayrı .1/.2 gibi döndürülmüş dosyalar yok,
kullanıcı isteği: "eski logun üzerine değişiklik yapsın" — tek dosya, sürekli
budanıyor)."""

import os
import re
import time

from gizli_maskele import maskele

_TS_RE = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]")


def trim_log(path: str, days: int = 7) -> None:
    """path'teki log dosyasını, satır başındaki [YYYY-MM-DD HH:MM:SS] zaman
    damgasına göre son `days` günden eski satırları atarak yeniden yazar.
    Zaman damgası ayrıştırılamayan satırlar (ör. bir hatanın çok satırlı izi)
    bir önceki zaman damgalı satırla aynı grupta sayılır, kaybolmaz.

    AYRICA: tutulan her satır `gizli_maskele.maskele()`'den geçiriliyor.
    NEDEN: 2026-09-04'te `dj_famous_process.log`'a gerçek bir Instagram
    token'ı düştü (bir ağ hatasının mesajı tam istek URL'sini içeriyordu) ve
    GÜNLERCE orada durdu. Asıl düzeltme token'ın hiç yazılmaması (bkz.
    `gizli_maskele.py` ve çağrı noktaları), ama bu ikinci savunma hattı iki
    şeyi kapatıyor: (1) diskte HÂLİHAZIRDA duran eski sızıntılar bir sonraki
    budamada temizleniyor, (2) henüz maskeleyiciden geçmeyen bir çağrı noktası
    kalmışsa (ör. başka bir ajanın sahip olduğu `auto_process.py`/
    `dj_famous_process.py`) sızıntı log'da kalıcı olmuyor."""
    if not os.path.isfile(path):
        return
    cutoff = time.time() - days * 86400
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return

    kept = []
    keep_current = True
    maskelendi = False
    for line in lines:
        m = _TS_RE.match(line)
        if m:
            try:
                ts = time.mktime(time.strptime(m.group(1), "%Y-%m-%d %H:%M:%S"))
                keep_current = ts >= cutoff
            except ValueError:
                keep_current = True
        if keep_current:
            temiz = maskele(line)
            if temiz != line:
                maskelendi = True      # sızıntı bulundu, dosya yeniden yazılmalı
            kept.append(temiz)

    # Satır sayısı değişmese bile maskeleme yapıldıysa yeniden yazılıyor —
    # aksi halde diskteki eski bir token olduğu gibi kalırdı.
    if len(kept) != len(lines) or maskelendi:
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.writelines(kept)
        except OSError:
            pass
