"""Famous Music Studio - Otomatik Yukleme Sistemi

Kullanim:
    python upload/yukleme_sistemi.py --projeler "Küllerimden Geç,Sokaklar Beni Tanır,Son Kez,Yürek Yarası"
    python upload/yukleme_sistemi.py --hepsi
    python upload/yukleme_sistemi.py --kontrol
"""
import argparse, json, os, sys, datetime, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import state_io

UPLOAD_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROJELER = ['Küllerimden Geç', 'Sokaklar Beni Tanır', 'Son Kez', 'Yürek Yarası']


def instagram_token_durum():
    token_path = os.path.join(UPLOAD_DIR, 'instagram_token.json')
    if not os.path.isfile(token_path):
        return False, "Token yok"
    with open(token_path, encoding='utf-8') as f:
        t = json.load(f)
    token = t.get('access_token', '')
    ig_user_id = t.get('ig_user_id', '')
    if not token or not ig_user_id:
        return False, "Token veya user_id eksik"
    try:
        url = f"https://graph.instagram.com/v21.0/{ig_user_id}?fields=id,username,media_count&access_token={token}"
        req = urllib.request.Request(url, method='GET')
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        if data.get('username'):
            return True, f"OK: {data['username']} ({data.get('media_count', 0)} post)"
        return False, f"Bilinmeyen yanit: {data}"
    except Exception as e:
        return False, f"HATA: {str(e)[:100]}"


def tiktok_token_durum():
    token_path = os.path.join(UPLOAD_DIR, 'tiktok_token.json')
    if not os.path.isfile(token_path):
        return False, "Token yok"
    with open(token_path, encoding='utf-8') as f:
        t = json.load(f)
    token = t.get('access_token', '')
    if not token:
        return False, "Token yok"
    return True, f"OK: {token[:20]}..."


def instagram_yukle(proje):
    import upload.instagram_upload as ig_upload
    return ig_upload.main(proje)


def tiktok_schedule_guncelle():
    base = datetime.datetime(2026, 10, 9, 18, 0, 0)
    for i, proj in enumerate(PROJELER):
        sp = os.path.join(PROJECTS_DIR, 'projects', proj, 'state.json')
        if os.path.isfile(sp):
            with open(sp, encoding='utf-8') as f:
                st = json.load(f)
            st['tiktok_scheduled_at'] = (base + datetime.timedelta(days=i)).isoformat()
            st['tiktok_scheduled'] = True
            state_io.atomic_write(sp, st)
            print(f"  [{proj}] schedule: {st['tiktok_scheduled_at']}")
        else:
            print(f"  [{proj}] state.json yok")


def hepsi_yukle():
        print("=" * 60)
        print("FAMOUS MUSIC STUDIO - OTOMATIK YUKLEME")
        print("=" * 60)

        print("\n[Instagram] Token Kontrol:")
        ok, msg = instagram_token_durum()
        print(f"  {msg}")
        if not ok:
            print("  [HATA] Token gecersiz. Once: python upload/instagram_auth.py --print-url")
            return

        print("\n[TikTok] Token Kontrol:")
        ok, msg = tiktok_token_durum()
        print(f"  {msg}")

        print("\n[Instagram] Reels Yukleme:")
        for proj in PROJELER:
            print(f"  [BEKLEME] {proj}...")
            try:
                instagram_yukle(proj)
                print(f"  [OK] {proj} yuklendi")
            except Exception as e:
                print(f"  [HATA] {proj}: {str(e)[:80]}")

        print("\n[TikTok] Schedule Guncelleme:")
        tiktok_schedule_guncelle()

        print("\n[Durum] Son Durum:")
        ok, msg = instagram_token_durum()
        print(f"  Instagram: {msg}")
        ok, msg = tiktok_token_durum()
        print(f"  TikTok: {msg}")

        print("\n[OK] Tum yuklemeler tamamlandi!")


def kontrol():
        print("=" * 60)
        print("FAMOUS MUSIC STUDIO - DURUM KONTROLU")
        print("=" * 60)

        print("\n[Instagram]:")
        ok, msg = instagram_token_durum()
        print(f"  Token: {msg}")

        print("\n[TikTok]:")
        ok, msg = tiktok_token_durum()
        print(f"  Token: {msg}")

        print("\n[Projeler]:")
        for proj in PROJELER:
            sp = os.path.join(PROJECTS_DIR, 'projects', proj, 'state.json')
            if os.path.isfile(sp):
                with open(sp, encoding='utf-8') as f:
                    st = json.load(f)
                tiktok_pub = st.get('tiktok_published_at', 'YOK')
                tiktok_sched = st.get('tiktok_scheduled_at', 'YOK')
                print(f"  {proj}:")
                print(f"    TikTok published: {tiktok_pub}")
                print(f"    TikTok scheduled: {tiktok_sched}")
            else:
                print(f"  {proj}: state.json yok")


def main():
    parser = argparse.ArgumentParser(description='Famous Music Studio Yukleme Sistemi')
    parser.add_argument('--projeler', help='Projeleri virgulle ayir')
    parser.add_argument('--hepsi', action='store_true', help='Tum projeleri yukle')
    parser.add_argument('--kontrol', action='store_true', help='Durumu kontrol et')
    args = parser.parse_args()

    if args.hepsi:
        hepsi_yukle()
    elif args.kontrol:
        kontrol()
    elif args.projeler:
        projeler = args.projeler.split(',')
        for proj in projeler:
            proj = proj.strip()
            print(f"\n[Instagram] {proj}:")
            try:
                instagram_yukle(proj)
                print(f"  [OK] {proj} yuklendi")
            except Exception as e:
                print(f"  [HATA] {proj}: {str(e)[:80]}")
        tiktok_schedule_guncelle()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
