"""En son yayınlanan şarkıya yönlendiren `docs/latest.html`'i günceller.

NEDEN VAR: Instagram/TikTok'ta caption/yorum içindeki linkler tıklanamıyor
(platform kısıtı, WebSearch ile doğrulandı) — tek gerçekten tıklanabilir yer
profildeki "bio link". Kullanıcı bio linkini `famousmusicstudio.com/latest.html`
olarak ayarlayınca, yeni bir paylaşımı gören/beğenen biri bio'ya gittiğinde
DOĞRUDAN o anki (en güncel) şarkının YouTube sayfasına düşüyor — statik bir
kanal linkinden farklı olarak, her yeni yüklemede otomatik güncelleniyor.

auto_process.py, yeni bir YouTube yüklemesi (upload_video) başarılı olduğunda
bunu çağırıp `git_sync.push_path()` ile SADECE bu dosyayı commit'leyip push
ediyor (kullanıcı onayı, 2026-09-05 — projects/*/state.json gibi diğer
commit'siz değişikliklere dokunmuyor)."""

import html
import os

DOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
LATEST_HTML_PATH = os.path.join(DOCS_DIR, "latest.html")

_TEMPLATE = """<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Famous Music Studio — Yeni Parça</title>
<meta name="description" content="Famous Music Studio'nun en son yayınlanan şarkısına yönlendiriliyorsunuz.">
<meta http-equiv="refresh" content="0; url={url}">
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
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 6vh 1.5rem;
  }}

  main {{ max-width: 28rem; width: 100%; text-align: center; }}

  p.eyebrow {{
    font-size: 0.8rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-dim);
    margin: 0 0 0.8rem;
  }}

  h1 {{
    font-family: 'Cormorant Garamond', serif;
    font-weight: 600;
    font-size: clamp(1.8rem, 6vw, 2.4rem);
    margin: 0 0 1.8rem;
    color: var(--gold-bright);
  }}

  a.button {{
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.8rem 1.6rem;
    border: 1px solid var(--border);
    border-radius: 999px;
    color: var(--text);
    text-decoration: none;
    font-size: 0.95rem;
  }}

  a.button:hover, a.button:focus-visible {{
    border-color: var(--gold);
    color: var(--gold-bright);
    background: rgba(201, 161, 90, 0.06);
  }}
</style>
</head>
<body>
<main>
  <p class="eyebrow">Yeni şarkı</p>
  <h1>{title}</h1>
  <a class="button" href="{url}">YouTube'da dinle</a>
</main>
<script>
  location.replace("{url}");
</script>
</body>
</html>
"""


def update(title: str, youtube_url: str) -> None:
    rendered = _TEMPLATE.format(title=html.escape(title), url=youtube_url)
    with open(LATEST_HTML_PATH, "w", encoding="utf-8") as f:
        f.write(rendered)
