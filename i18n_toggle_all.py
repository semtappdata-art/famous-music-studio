# -*- coding: utf-8 -*-
"""Tum sayfalara dil toggle + i18n.css baglar (Madde 31)."""
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

TOGGLE = """
<!-- DIL TOGGLE (Madde 31) -->
<div class="dil-toggle" role="group" aria-label="Dil / Language">
  <button type="button" data-dil-btn="tr" aria-pressed="true" class="aktif">TR</button>
  <span class="ayrac" aria-hidden="true"></span>
  <button type="button" data-dil-btn="en" aria-pressed="false">EN</button>
</div>
"""

SAYAFLAR = [
    ("site/privacy.html", "i18n.css"),
    ("site/epk/bio.html", "../i18n.css"),
    ("site/404.html", "i18n.css"),
]


def main():
    for dosya, css_yolu in SAYAFLAR:
        with open(dosya, encoding="utf-8") as f:
            c = f.read()
        n = 0

        # 1) CSS baglantisi
        if "i18n.css" not in c:
            link = '  <link rel="stylesheet" href="%s">\n' % css_yolu
            if "</head>" in c:
                c = c.replace("</head>", link + "</head>", 1)
                n += 1

        # 2) dil toggle (body basinda)
        if "dil-toggle" not in c:
            if "<body>" in c:
                c = c.replace("<body>", "<body>\n" + TOGGLE, 1)
                n += 1
            else:
                # <body ...> attribute'li olabilir
                import re
                m = re.search(r"<body[^>]*>", c)
                if m:
                    c = c[:m.end()] + "\n" + TOGGLE + c[m.end():]
                    n += 1

        with open(dosya, "w", encoding="utf-8") as f:
            f.write(c)
        print("  %-24s %d eklendi (css=%s)" % (dosya, n, css_yolu))

    # 3) index.html: gomulu CSS'i i18n.css'e tasla (tek kaynak)
    with open("site/index.html", encoding="utf-8") as f:
        c = f.read()
    bas = c.find("  /* ===== DIL TOGGLE (Madde 31) ===== */")
    if bas >= 0:
        son = c.find("  .hero {", bas)
        if son > bas:
            c = c[:bas] + c[son:]
            if "i18n.css" not in c:
                c = c.replace("</head>", '  <link rel="stylesheet" href="i18n.css">\n</head>', 1)
            with open("site/index.html", "w", encoding="utf-8") as f:
                f.write(c)
            print("  site/index.html          gomulu CSS -> i18n.css'e tasindi")


if __name__ == "__main__":
    main()
