# -*- coding: utf-8 -*-
"""Kalan i18n niteliklerini ekler (privacy.html, epk/bio.html)."""
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def main():
    hedefler = [
        ("site/privacy.html", [
            ('<p>Bu veriler <strong>kendi sunucumuzda</strong>',
             '<p data-i18n="prv.p_1b">Bu veriler <strong>kendi sunucumuzda</strong>'),
            ('<td class="yes">Evet</td>', '<td class="yes" data-i18n="prv.evet">Evet</td>'),
            ('<a href="./">← Ana sayfa</a>',
             '<a href="./" data-i18n="prv.f_ana">← Ana sayfa</a>'),
            ('<a href="epk/bio.html">Press Kit</a>',
             '<a href="epk/bio.html" data-i18n="prv.f_epk">Press Kit</a>'),
        ]),
        ("site/epk/bio.html", [
            ('<p>Famous Music Studio · Medya, promosör ve işbirliği için kaynaklar</p>',
             '<p data-i18n="epk.sub2">Famous Music Studio · Medya, promosör ve işbirliği için kaynaklar</p>'),
            ('<p>Kanal haftalık yeni parça ve DJ setleriyle büyür; <em>DJ Famous</em>',
             '<p data-i18n="epk.bio_p9">Kanal haftalık yeni parça ve DJ setleriyle büyür; <em>DJ Famous</em>'),
            ('<h3>Biyografi &amp; Olgu Dosyası</h3>',
             '<h3 data-i18n="epk.k_bio">Biyografi &amp; Olgu Dosyası</h3>'),
            ('<h3>Booking &amp; İşbirliği</h3>',
             '<h3 data-i18n="epk.k_booking">Booking &amp; İşbirliği</h3>'),
            ('<p>DJ booking, remix, sync lisans ve form şablonu.</p>',
             '<p data-i18n="epk.k_booking_p">DJ booking, remix, sync lisans ve form şablonu.</p>'),
            ('<strong>Not:</strong> Basın görselleri ve ses dosyaları için',
             '<strong data-i18n="epk.not">Not:</strong> Basın görselleri ve ses dosyaları için'),
            ('adresine yazın. Talebe 48 saat içinde yanıt verilir.',
             'adresine yazın. Talebe 48 saat içinde yanıt verilir.'),
            ('<a href="./">← Ana sayfa</a>',
             '<a href="./" data-i18n="epk.f_ana">← Ana sayfa</a>'),
            ('<a href="privacy.html">Gizlilik</a>',
             '<a href="privacy.html" data-i18n="epk.f_privacy">Gizlilik</a>'),
        ]),
    ]

    for dosya, ciftler in hedefler:
        with open(dosya, encoding="utf-8") as f:
            c = f.read()
        n = 0
        for eski, yeni in ciftler:
            if eski in c:
                c = c.replace(eski, yeni, 1)
                n += 1
            else:
                print("    BULUNAMADI (%s): %s" % (dosya, eski[:50]))
        with open(dosya, "w", encoding="utf-8") as f:
            f.write(c)
        print("  %s: %d eklendi" % (dosya, n))


if __name__ == "__main__":
    main()
