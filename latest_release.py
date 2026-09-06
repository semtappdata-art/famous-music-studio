"""Yayındaki TÜM şarkıları listeleyen `docs/latest.html`'i günceller.

NEDEN VAR: Instagram/TikTok'ta caption/yorum içindeki linkler tıklanamıyor
(platform kısıtı, WebSearch ile doğrulandı) — tek gerçekten tıklanabilir yer
profildeki "bio link". Kullanıcı bio linkini `famousmusicstudio.com/latest.html`
olarak ayarlayınca, herhangi bir paylaşımı gören biri bio'ya gittiğinde bu
sayfada TÜM yayındaki şarkıları (en yeni en üstte) görüp istediğine tıklayarak
YouTube'a ulaşabiliyor — sadece "en son"a değil, ESKİ bir paylaşımı görüp gelen
biri de aradığı şarkıyı bulabiliyor.

auto_process.py, yeni bir YouTube yüklemesi (upload_video) başarılı olduğunda
regenerate()'i çağırıp `git_sync.push_path()` ile SADECE bu dosyayı commit'leyip
push ediyor (kullanıcı onayı, 2026-09-05 — projects/*/state.json gibi diğer
commit'siz değişikliklere dokunmuyor)."""

import glob
import html
import json
import os
from datetime import datetime, timezone

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(REPO_DIR, "docs")
LATEST_HTML_PATH = os.path.join(DOCS_DIR, "latest.html")


def _load_json(path: str) -> dict:
    if not os.path.isfile(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _already_live(state: dict) -> bool:
    """state.json'daki youtube_privacy="public", golden-hour zamanlaması
    kullanıldığında (youtube_publish_at dolu) videonun O AN gerçekten canlı
    olduğu anlamına GELMİYOR — YouTube, publishAt zamanına kadar videoyu
    private tutup kendisi public'e çeviriyor (bkz. config.next_golden_publish_time,
    youtube_upload.py::_compute_publish_at). publish_at varsa geçmiş olmalı,
    yoksa (zamanlamasız yüklendi) doğrudan public sayılır."""
    publish_at = state.get("youtube_publish_at")
    if not publish_at:
        return True
    try:
        return datetime.fromisoformat(publish_at.replace("Z", "+00:00")) <= datetime.now(timezone.utc)
    except ValueError:
        return True


def _collect(base: str) -> list[tuple[str, str, str]]:
    """(uploaded_at, title, youtube_url) üçlülerini, GERÇEKTEN canlı + youtube_video_id
    olan projeler için, en yeni önce sıralı döner."""
    rows = []
    for state_path in glob.glob(os.path.join(REPO_DIR, base, "*", "state.json")):
        state = _load_json(state_path)
        video_id = state.get("youtube_video_id")
        if state.get("youtube_privacy") != "public" or not video_id or not _already_live(state):
            continue
        project_dir = os.path.dirname(state_path)
        meta = _load_json(os.path.join(project_dir, "meta.json"))
        title = meta.get("title", os.path.basename(project_dir))
        rows.append((state.get("youtube_uploaded_at", ""), title, f"https://youtu.be/{video_id}"))
    rows.sort(reverse=True)
    return rows


def _section(heading: str, rows: list[tuple[str, str, str]]) -> str:
    if not rows:
        return ""
    items = "\n".join(
        f'    <li><a href="{url}">{html.escape(title)}</a></li>'
        for _, title, url in rows
    )
    return f'  <h2>{heading}</h2>\n  <ul>\n{items}\n  </ul>\n'


_TEMPLATE = """<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Famous Music Studio — Şarkılar</title>
<meta name="description" content="Famous Music Studio'nun tüm yayındaki şarkıları — YouTube'da dinle.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600&family=Inter:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: #0a0806;
    --bg-alt: #131009;
    --text: #ece6da;
    --text-dim: #a89b84;
    --gold: #c9a15a;
    --gold-bright: #e6c17e;
    --border: rgba(201, 161, 90, 0.25);
  }}

  * {{ box-sizing: border-box; }}

  body {{
    margin: 0;
    min-height: 100vh;
    background: radial-gradient(ellipse at 50% 0%, var(--bg-alt) 0%, var(--bg) 65%);
    color: var(--text);
    font-family: 'Inter', -apple-system, sans-serif;
    padding: 6vh 1.5rem;
  }}

  main {{ max-width: 28rem; width: 100%; margin: 0 auto; text-align: center; }}

  h1 {{
    font-family: 'Cormorant Garamond', serif;
    font-weight: 600;
    font-size: clamp(1.8rem, 6vw, 2.4rem);
    margin: 0 0 2rem;
    color: var(--gold-bright);
  }}

  h2 {{
    font-size: 0.8rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-dim);
    margin: 2rem 0 0.8rem;
    text-align: left;
  }}

  ul {{ list-style: none; margin: 0; padding: 0; }}

  li + li {{ margin-top: 0.6rem; }}

  a {{
    display: block;
    padding: 0.8rem 1.2rem;
    border: 1px solid var(--border);
    border-radius: 12px;
    color: var(--text);
    text-decoration: none;
    font-size: 0.95rem;
    text-align: left;
  }}

  a:hover, a:focus-visible {{
    border-color: var(--gold);
    color: var(--gold-bright);
    background: rgba(201, 161, 90, 0.06);
  }}
</style>
</head>
<body>
<main>
  <h1>Famous Music Studio</h1>
{sections}
</main>
</body>
</html>
"""


def regenerate() -> None:
    sections = _section("Şarkılar", _collect("projects")) + _section("DJ Famous Setleri", _collect("dj_sets"))
    rendered = _TEMPLATE.format(sections=sections)
    with open(LATEST_HTML_PATH, "w", encoding="utf-8") as f:
        f.write(rendered)
