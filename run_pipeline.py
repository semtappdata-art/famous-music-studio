"""Tek komutla render + YouTube upload zinciri.

Kullanım:
    python run_pipeline.py --project "projects/beni bırakma"
    python run_pipeline.py --project "projects/beni bırakma" --privacy public
    python run_pipeline.py --project "projects/beni bırakma" --skip-upload

Adımlar: render.py (3 platform) -> upload/youtube_upload.py (youtube_16x9.mp4).
Upload adımı, upload/token.json henüz yoksa (OAuth consent flow tamamlanmadıysa)
açıkça hata verir — sessizce atlanmaz.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "upload"))

import render as render_module


def main():
    parser = argparse.ArgumentParser(description="Render + YouTube upload zinciri.")
    parser.add_argument("--project", required=True, help="Proje klasörü (örn. projects/sarki-adi)")
    parser.add_argument(
        "--privacy", default="private", choices=["private", "unlisted", "public"],
        help="YouTube görünürlüğü (varsayılan: private)",
    )
    parser.add_argument(
        "--skip-upload", action="store_true",
        help="Sadece render et, YouTube'a yükleme",
    )
    args = parser.parse_args()

    print(f"=== 1/2: Render ===")
    ok = render_module.render_project(args.project)
    if not ok:
        print("Render başarısız, upload adımı atlanıyor.")
        sys.exit(1)

    if args.skip_upload:
        print("--skip-upload verildi, upload adımı atlandı.")
        return

    token_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "upload", "token.json")
    if not os.path.isfile(token_path):
        print(
            "\nHATA: upload/token.json bulunamadı — OAuth consent flow henüz tamamlanmamış.\n"
            "Önce şunu çalıştır: python upload/youtube_auth.py\n"
            "(Tarayıcıda açılan linki tamamlaman gerekiyor, bu adım otomatikleştirilemez.)"
        )
        sys.exit(1)

    print(f"\n=== 2/2: YouTube Upload ===")
    from youtube_upload import upload_video
    upload_video(args.project, args.privacy)


if __name__ == "__main__":
    main()
