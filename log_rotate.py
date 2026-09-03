"""auto_process.log ve watch_projects.log için paylaşılan basit log temizleme.

Log dosyaları süresiz büyümesin diye — 7 günden eski satırlar her çağrıda
atılıp dosya yeniden yazılıyor (ayrı .1/.2 gibi döndürülmüş dosyalar yok,
kullanıcı isteği: "eski logun üzerine değişiklik yapsın" — tek dosya, sürekli
budanıyor)."""

import os
import re
import time

_TS_RE = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]")


def trim_log(path: str, days: int = 7) -> None:
    """path'teki log dosyasını, satır başındaki [YYYY-MM-DD HH:MM:SS] zaman
    damgasına göre son `days` günden eski satırları atarak yeniden yazar.
    Zaman damgası ayrıştırılamayan satırlar (ör. bir hatanın çok satırlı izi)
    bir önceki zaman damgalı satırla aynı grupta sayılır, kaybolmaz."""
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
    for line in lines:
        m = _TS_RE.match(line)
        if m:
            try:
                ts = time.mktime(time.strptime(m.group(1), "%Y-%m-%d %H:%M:%S"))
                keep_current = ts >= cutoff
            except ValueError:
                keep_current = True
        if keep_current:
            kept.append(line)

    if len(kept) != len(lines):
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.writelines(kept)
        except OSError:
            pass
