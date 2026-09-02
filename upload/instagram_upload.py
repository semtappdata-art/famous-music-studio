"""Render edilmiş bir projeyi Instagram'a Reels olarak yükler (Instagram Graph API).

Kullanım:
    python upload/instagram_upload.py --project "projects/beni bırakma"

ÖNEMLİ — Instagram Graph API dosya upload'ı değil, HERKESE AÇIK bir video_url
bekliyor. İki seçenek var:
  1. --video-url ile zaten barındırılan (örn. bir CDN/hosting'deki) bir URL ver.
  2. upload/netlify_client_secrets.json dosyasını doldur ({"token": "...",
     "site_id": "..."}) — bu durumda script, projedeki shorts_9x16.mp4 dosyasını
     otomatik olarak ayrı bir Netlify sitesine deploy edip URL'i kendisi üretir.
     Bu Netlify sitesi SADECE geçici video barındırma için kullanılmalı (her
     yüklemede içeriğinin tamamen değişmesi beklenir) — famousmusicstudio.com
     ana sitesiyle KARIŞTIRILMAMALI, ayrı bir site olmalı.
"""

import argparse
import hashlib
import json
import os
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from instagram_auth import get_access_token
from social_text import build_caption, build_youtube_comment

UPLOAD_DIR = os.path.dirname(os.path.abspath(__file__))
NETLIFY_SECRETS_PATH = os.path.join(UPLOAD_DIR, "netlify_client_secrets.json")

GRAPH_API = "https://graph.instagram.com/v21.0"


def _load_meta(project_dir: str) -> dict:
    meta_path = os.path.join(project_dir, "meta.json")
    if os.path.isfile(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _upload_to_netlify(video_path: str) -> str:
    """Video dosyasını ayrı bir 'sadece medya' Netlify sitesine deploy edip
    ortaya çıkan public URL'i döner. netlify_client_secrets.json gerektirir.

    NOT: Önceden burada ham bir zip'i `Content-Type: application/zip` ile tek
    POST'ta göndermeyi deniyorduk (Netlify'ın "one-off deploy" yöntemi) — ama
    gerçek kullanımda Netlify bunu zip olarak AÇMADI, tüm içeriği tek, yanlış
    mime type'lı ("text/plain") bir kök (`/`) dosyası olarak kaydetti, video
    hiçbir zaman gerçek dosya adıyla erişilebilir olmadı. Onun yerine Netlify'ın
    "digest deploy" API'si kullanılıyor (dosya yolu + SHA1 hash'i JSON ile
    bildirilip, Netlify içeriği zaten önbelleğinde tutmuyorsa dosya ayrıca PUT
    edilir) — bu, Netlify'ın kendi web arayüzündeki (sürükle-bırak) yöntemle
    aynı ve bu projede elle doğrulanmış şekilde çalışıyor."""
    if not os.path.isfile(NETLIFY_SECRETS_PATH):
        raise FileNotFoundError(
            f"{NETLIFY_SECRETS_PATH} bulunamadı ve --video-url verilmedi.\n"
            "Ya --video-url ile herkese açık bir video linki ver, ya da Netlify'da "
            "ayrı bir 'medya' sitesi oluşturup token/site_id'sini şu formatta kaydet:\n"
            '{"token": "...", "site_id": "..."}'
        )
    with open(NETLIFY_SECRETS_PATH, "r", encoding="utf-8") as f:
        creds = json.load(f)

    filename = os.path.basename(video_path)
    with open(video_path, "rb") as f:
        content = f.read()
    file_sha1 = hashlib.sha1(content).hexdigest()

    auth_headers = {"Authorization": f"Bearer {creds['token']}"}

    create_resp = requests.post(
        f"https://api.netlify.com/api/v1/sites/{creds['site_id']}/deploys",
        headers={**auth_headers, "Content-Type": "application/json"},
        json={"files": {f"/{filename}": file_sha1}},
        timeout=(10, 30),
    )
    create_resp.raise_for_status()
    deploy = create_resp.json()
    deploy_id = deploy["id"]

    # Netlify aynı içeriği (aynı SHA1) daha önce görmediyse dosyayı ayrıca yükle.
    if file_sha1 in (deploy.get("required") or []):
        upload_resp = requests.put(
            f"https://api.netlify.com/api/v1/deploys/{deploy_id}/files/{filename}",
            headers={**auth_headers, "Content-Type": "application/octet-stream"},
            data=content,
            timeout=(10, 300),
        )
        upload_resp.raise_for_status()

    # Deploy 'ready' olana kadar bekle
    status_resp = None
    for _ in range(30):
        status_resp = requests.get(
            f"https://api.netlify.com/api/v1/deploys/{deploy_id}",
            headers=auth_headers,
            timeout=(10, 30),
        )
        status_resp.raise_for_status()
        if status_resp.json().get("state") == "ready":
            break
        time.sleep(2)
    else:
        raise RuntimeError("Netlify deploy zaman aşımına uğradı.")

    base_url = status_resp.json()["ssl_url"]
    return f"{base_url}/{filename}"


def upload_video(project_dir: str, video_url: str | None = None, caption: str | None = None) -> str:
    video_path = os.path.join(project_dir, "output", "shorts_9x16.mp4")
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"{video_path} bulunamadı — önce render.py ile bu projeyi render et.")

    token = get_access_token()
    access_token = token["access_token"]
    ig_user_id = token["ig_user_id"]

    if video_url is None:
        print("  video_url verilmedi, Netlify'a yükleniyor...")
        video_url = _upload_to_netlify(video_path)
        print(f"  yüklendi: {video_url}")

    youtube_url = None
    state_path = os.path.join(project_dir, "state.json")
    if os.path.isfile(state_path):
        with open(state_path, "r", encoding="utf-8") as f:
            video_id = json.load(f).get("youtube_video_id")
        if video_id:
            youtube_url = f"https://youtu.be/{video_id}"

    if caption is None:
        meta = _load_meta(project_dir)
        caption = build_caption(meta)

    # AÇIK MADDE: Meta, gerçekçi AI-üretimi içerik için "AI Info" etiketlemesini
    # zorunlu kılıyor (about.fb.com/news/2024/02 ve 2024/04 duyuruları). Graph API
    # media endpoint'inde buna karşılık gelen resmi alan adı bu depoda DOĞRULANAMADI
    # (developers.facebook.com'a bu ortamdan erişilemedi) — ikincil kaynaklarda
    # `is_ai_generated` benzeri bir alan geçiyor ama teyitsiz. Yanlış alan adını
    # buraya eklemek her yüklemede API hatasına yol açabileceği için BİLEREK
    # eklenmedi — resmi dokümantasyondan doğrulanınca buraya eklenmeli.

    # 1) Media container olustur
    create_resp = requests.post(
        f"{GRAPH_API}/{ig_user_id}/media",
        data={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "access_token": access_token,
        },
        timeout=(10, 30),
    )
    create_resp.raise_for_status()
    creation_id = create_resp.json()["id"]

    # 2) Container video islenene kadar bekle (status_code: FINISHED)
    print(f"  işleniyor: creation_id={creation_id}")
    for _ in range(60):
        time.sleep(5)
        status_resp = requests.get(
            f"{GRAPH_API}/{creation_id}",
            params={"fields": "status_code", "access_token": access_token},
            timeout=(10, 30),
        )
        status_resp.raise_for_status()
        status_code = status_resp.json().get("status_code")
        if status_code == "FINISHED":
            break
        if status_code == "ERROR":
            raise RuntimeError(f"Instagram video işleme hatası: {status_resp.json()}")
    else:
        raise RuntimeError("Instagram video işleme zaman aşımına uğradı.")

    # 3) Yayinla
    publish_resp = requests.post(
        f"{GRAPH_API}/{ig_user_id}/media_publish",
        data={"creation_id": creation_id, "access_token": access_token},
        timeout=(10, 30),
    )
    publish_resp.raise_for_status()
    media_id = publish_resp.json()["id"]
    print(f"  tamam: media_id={media_id}")

    # YouTube linki caption'a DEĞİL, paylaşımdan SONRA bir yoruma ekleniyor — bkz.
    # social_text.build_caption()'daki not. Yorum başarısız olsa bile ana yükleme
    # zaten tamamlandığı için hata fırlatmıyoruz, sadece logluyoruz.
    if youtube_url:
        try:
            comment_resp = requests.post(
                f"{GRAPH_API}/{media_id}/comments",
                data={"message": build_youtube_comment(youtube_url), "access_token": access_token},
                timeout=(10, 30),
            )
            comment_resp.raise_for_status()
            print(f"  YouTube linki yorum olarak eklendi: {comment_resp.json().get('id')}")
        except requests.exceptions.RequestException as e:
            print(f"  UYARI: YouTube linki yorumu eklenemedi: {e}")

    state_path = os.path.join(project_dir, "state.json")
    state = {}
    if os.path.isfile(state_path):
        with open(state_path, "r", encoding="utf-8") as f:
            state = json.load(f)
    state["instagram_media_id"] = media_id
    state["instagram_uploaded_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    return media_id


def main():
    parser = argparse.ArgumentParser(description="Render edilmiş bir projeyi Instagram'a Reels olarak yükler.")
    parser.add_argument("--project", required=True, help="Proje klasörü (örn. projects/sarki-adi)")
    parser.add_argument("--video-url", default=None, help="Herkese açık video URL'si (verilmezse Netlify'a otomatik yüklenir)")
    parser.add_argument("--caption", default=None, help="Gönderi açıklaması (verilmezse meta.json'daki title kullanılır)")
    args = parser.parse_args()

    upload_video(args.project, args.video_url, args.caption)


if __name__ == "__main__":
    main()
