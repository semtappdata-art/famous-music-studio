"""Render edilmiş bir projeyi TikTok'a Content Posting API (Direct Post) ile yükler.

Kullanım:
    python upload/tiktok_upload.py --project "projects/beni bırakma"

NOT: App henüz TikTok'un audit/review sürecinden geçmediyse, video sadece
sandbox'ta tanımlı hedef kullanıcıya (target user) gönderilebilir, herkese
açık yayınlanamaz. Detay: https://developers.tiktok.com/docs/en/content-posting-api-get-started
"""

import argparse
import json
import os
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from tiktok_auth import get_access_token
from social_text import build_caption, build_youtube_comment

API_BASE = "https://open.tiktokapis.com/v2"


def _headers(access_token: str) -> dict:
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
    }


def _load_meta(project_dir: str) -> dict:
    meta_path = os.path.join(project_dir, "meta.json")
    if os.path.isfile(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def upload_video(project_dir: str) -> str:
    """App'de sadece video.upload scope'u varsa (video.publish yok), TikTok'un
    "Upload to TikTok" (inbox/draft) akışı kullanılır: video kullanıcının TikTok
    gelen kutusuna taslak olarak düşer, yayınlamayı kullanıcı TikTok uygulamasından
    elle tamamlar. Doğrudan/otomatik yayın (Direct Post) video.publish scope'u
    gerektirir — app review onayı olmadan bu scope alınamıyor."""
    video_path = os.path.join(project_dir, "output", "shorts_9x16.mp4")
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"{video_path} bulunamadı — önce render.py ile bu projeyi render et.")

    token = get_access_token()
    access_token = token["access_token"]

    meta = _load_meta(project_dir)
    display_title = meta.get("title", "Untitled")

    # API'nin inbox/draft akışı caption/title alanı KABUL ETMİYOR — kullanıcı
    # taslağı TikTok uygulamasından yayınlarken caption'ı elle girmesi gerekiyor.
    # Burada önerilen caption'ı hesaplayıp hem konsola/log'a yazdırıyoruz hem de
    # state.json'a kaydediyoruz ki kullanıcı saatler sonra yayınlarken kolayca
    # kopyalayabilsin. YouTube linki caption'a DEĞİL — Instagram'daki gibi aynı
    # sebeple (keşfet/For You dağıtımı riski) — ayrı, "paylaşımdan sonra yorum
    # olarak ekle" şeklinde öneriliyor.
    youtube_url = None
    state_path = os.path.join(project_dir, "state.json")
    existing_state = {}
    if os.path.isfile(state_path):
        with open(state_path, "r", encoding="utf-8") as f:
            existing_state = json.load(f)
        video_id = existing_state.get("youtube_video_id")
        if video_id:
            youtube_url = f"https://youtu.be/{video_id}"
    suggested_caption = build_caption(meta)
    suggested_comment = build_youtube_comment(youtube_url) if youtube_url else None
    print("  --- TikTok'ta yayınlarken caption olarak yapıştır ---")
    print(f"  {suggested_caption}")
    print("  ------------------------------------------------------")
    if suggested_comment:
        print("  --- Paylaşımdan SONRA ilk yorum olarak ekle ---")
        print(f"  {suggested_comment}")
        print("  -------------------------------------------------")
    # TikTok, gerçekçi AI-üretimi içerik için "AI-generated content" etiketinin
    # (Content Credentials/AIGC) açılmasını zorunlu kılıyor (newsroom.tiktok.com/
    # en-us/new-labels-for-disclosing-ai-generated-content). inbox/draft akışı bu
    # alanı API ile göndermiyor (video.publish scope'u yok) — kullanıcı TikTok
    # uygulamasından elle yayınlarken bunu da elle açmalı.
    print("  --- TikTok uygulamasından yayınlarken UNUTMA: 'AI-generated content' etiketini de aç ---")

    video_size = os.path.getsize(video_path)
    init_body = {
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": video_size,
            "chunk_size": video_size,
            "total_chunk_count": 1,
        },
    }
    resp = requests.post(
        f"{API_BASE}/post/publish/inbox/video/init/", headers=_headers(access_token), json=init_body,
        timeout=(10, 30),
    )
    resp.raise_for_status()
    init_data = resp.json()["data"]
    publish_id = init_data["publish_id"]
    upload_url = init_data["upload_url"]

    print(f"  yükleniyor (taslak): {display_title}")
    with open(video_path, "rb") as f:
        video_bytes = f.read()

    # PUT çağrısı ağ seviyesinde (bir yanıt hiç gelmeden) başarısız olursa, TikTok'un
    # video baytlarını alıp almadığını KESİN olarak bilemeyiz — init zaten publish_id
    # ürettiği için videoyu sıfırdan tekrar yüklemek yerine durum sorgulamasına devam
    # ediyoruz (aşağıdaki mantık bu belirsizliği zaten ele alıyor: FAILED ise gerçek
    # başarısızlık kabul edilip state kaydedilmiyor, aksi halde publish_id kaydediliyor).
    # TikTok'tan GERÇEK bir "reddedildi" yanıtı (HTTPError) alırsak bu güvenle gerçek
    # bir başarısızlıktır, aynen eskisi gibi hemen raise ediyoruz.
    try:
        upload_resp = requests.put(
            upload_url,
            headers={
                "Content-Type": "video/mp4",
                "Content-Range": f"bytes 0-{video_size - 1}/{video_size}",
            },
            data=video_bytes,
            timeout=(10, 300),
        )
        upload_resp.raise_for_status()
    except requests.exceptions.HTTPError:
        raise
    except requests.exceptions.RequestException as e:
        print(f"  UYARI: video yükleme yanıtı alınamadı ({e}) — durum sorgulanarak devam ediliyor.")

    # Yayın durumunu poll et — bu noktada video baytları TikTok'a ZATEN ulaştı
    # (PUT başarılı oldu), yani durum sorgulaması sırasında bir AĞ hatası
    # (timeout/bağlantı kopması) olursa bunu "başarısız yükleme" gibi ele
    # alıp fonksiyonu patlatmıyoruz — aksi halde state.json'a publish_id hiç
    # yazılmaz, bir sonraki koşu videoyu TEKRAR yükleyip TikTok'un gelen
    # kutusunda yinelenen bir taslak bırakır. Sadece TikTok'un kendisinin
    # açıkça "FAILED" dediği durum gerçek bir başarısızlıktır (o zaman raise
    # edip state'i KAYDETMEDEN çıkıyoruz, tekrar deneme mümkün olsun).
    try:
        for _ in range(30):
            time.sleep(3)
            status_resp = requests.post(
                f"{API_BASE}/post/publish/status/fetch/",
                headers=_headers(access_token),
                json={"publish_id": publish_id},
                timeout=(10, 30),
            )
            status_resp.raise_for_status()
            status = status_resp.json()["data"]["status"]
            if status in ("PUBLISH_COMPLETE", "SEND_TO_USER_INBOX"):
                print(f"  tamam ({status}): publish_id={publish_id} — TikTok uygulamasından yayınla.")
                break
            if status == "FAILED":
                raise RuntimeError(f"TikTok yükleme başarısız: {status_resp.json()}")
        else:
            print(f"  Durum belirsiz (timeout), publish_id={publish_id} — TikTok Studio'dan kontrol et.")
    except requests.exceptions.RequestException as e:
        print(
            f"  UYARI: durum sorgulanamadı ({e}) — video muhtemelen zaten yüklendi, "
            f"publish_id={publish_id} yine de kaydediliyor, TikTok Studio'dan kontrol et."
        )

    existing_state["tiktok_publish_id"] = publish_id
    existing_state["tiktok_uploaded_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    existing_state["tiktok_privacy"] = "DRAFT_INBOX"
    existing_state["tiktok_suggested_caption"] = suggested_caption
    if suggested_comment:
        existing_state["tiktok_suggested_comment"] = suggested_comment
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(existing_state, f, ensure_ascii=False, indent=2)

    return publish_id


def main():
    parser = argparse.ArgumentParser(description="Render edilmiş bir projeyi TikTok'a yükler.")
    parser.add_argument("--project", required=True, help="Proje klasörü (örn. projects/sarki-adi)")
    args = parser.parse_args()

    upload_video(args.project)


if __name__ == "__main__":
    main()
