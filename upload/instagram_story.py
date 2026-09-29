"""Instagram hikaye (story) container oluşturma ve publish kuyrugu.

Instagram Graph API ile STORIES media_type container oluşturulabiliyor
(v21.0+): POST .../media?media_type=STORIES&image_url=... veya video_url=...
Container oluşunca media_publish ile yayinlanir (reel/container ile ayni
mekanizma). Hikaye 24 saatli — replay yapilmaz, her versiyon yeni container.

Zamanlama: golden-hour penceresinde (config.GOLDEN_HOURS, TR yerel).
Hikaye versiyonlari: yayin +2-6s (V1), +24s (V2), +3-4g (V3).

NOT: Instagram hikaye API'si var — bu dosya ona bagli. Yalnizca Instagram.
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import state_io
from gizli_maskele import maskele
from instagram_auth import get_access_token
from social_text import build_story_overlay, resolve_language

GRAPH_API = "https://graph.instagram.com/v21.0"

# Hikaye containeri 24 saat — reel containeriyla AYNI omur.
# 23 saat kapisi (aynen instagram_upload.KONTEYNER_OMRU_SN).
KONTEYNER_OMRU_SN = 23 * 3600

# Hikaye versiyonlari: 1/2/3 — state'te `story_versiyon`.
# V1: yayin +2-6 saat (golden-hour'da tetiklenir — tum versiyonlar golden-hour'da)
# V2: yayin +24 saat (gecenin ilk golden-hour'unda)
# V3: yayin +3-4 gun (hafta icinde)
STORY_VERSIYO_SURELERI = {1: (2, 6), 2: (24,), 3: (72, 96)}  # saat araliklari

# Hikaye keyframe (görsel) dosya adlari — cover_vertical aliniyor, yoksa cover.
COVER_VERTICAL_NAMES = ["cover_vertical.jpg", "cover_vertical.jpeg", "cover_vertical.png"]
COVER_NAMES = ["cover.jpg", "cover.jpeg", "cover.png"]


def _en_yeni_kapak(project_dir: str, names: list) -> str | None:
    """Verilen adaylar arasından EN YENİ (mtime) olanı donderir."""
    adaylar = [
        os.path.join(project_dir, ad)
        for ad in names
        if os.path.isfile(os.path.join(project_dir, ad))
    ]
    if not adaylar:
        return None
    adaylar.sort(key=os.path.getmtime, reverse=True)
    return adaylar[0]


def _find_story_keyframe(project_dir: str) -> str | None:
    """Hikaye görseli: öncelikle cover_vertical, yoksa cover."""
    dikey = _en_yeni_kapak(project_dir, COVER_VERTICAL_NAMES)
    if dikey:
        return dikey
    return _en_yeni_kapak(project_dir, COVER_NAMES)


def _load_meta(project_dir: str) -> dict:
    meta_path = os.path.join(project_dir, "meta.json")
    if os.path.isfile(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _load_state(project_dir: str) -> dict:
    state_path = os.path.join(project_dir, "state.json")
    if os.path.isfile(state_path):
        with open(state_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_state(project_dir: str, updates: dict) -> None:
    state = _load_state(project_dir)
    state.update(updates)
    state_io.durum_yaz(project_dir, state)


def _konteyner_yasi_sn(state: dict, simdi: float | None = None) -> float | None:
    olusturuldu = state.get("story_container_created_at")
    if not olusturuldu:
        return None
    try:
        epoch = time.mktime(time.strptime(str(olusturuldu), "%Y-%m-%dT%H:%M:%S"))
    except (ValueError, TypeError, OverflowError):
        return None
    return (simdi if simdi is not None else time.time()) - epoch


def _konteyner_bayat(state: dict, simdi: float | None = None) -> bool:
    yas = _konteyner_yasi_sn(state, simdi)
    if yas is None:
        return False
    return yas > KONTEYNER_OMRU_SN


def _konteyner_yayindan_yeni(state: dict) -> bool:
    """Bu container en son yayindan SONRA mi olusturuldu (Cift yayin korumasi)."""
    olusturuldu = state.get("story_container_created_at")
    yayinlandi = state.get("story_published_at")
    if not olusturuldu or not yayinlandi:
        return False
    return str(olusturuldu) > str(yayinlandi)


def _bekleyen_konteyneri_temizle(project_dir: str, state: dict, container_id: str, gerekce: str) -> None:
    print(f"  Instagram hikaye: bekleyen container (id={container_id}) {gerekce}, kaydi temizleniyor")
    state.pop("story_container_id", None)
    state.pop("story_container_created_at", None)
    state_io.durum_yaz(project_dir, state)


def _story_versiyonu_tarafi_bul(state: dict, meta: dict) -> int | None:
    """Bu projenin hikaye versiyonunu belirle — state'te kayitli ve egitim sirasi."""
    yayinlandi_str = state.get("youtube_uploaded_at") or state.get("instagram_uploaded_at")
    if not yayinlandi_str:
        return None
    try:
        yayinlandi = time.mktime(time.strptime(str(yayinlandi_str), "%Y-%m-%dT%H:%M:%S"))
    except (ValueError, TypeError, OverflowError):
        return None
    simdi = time.time()
    gecikme_saate = (simdi - yayinlandi) / 3600.0

    # V1: 2-6 saat, V2: 24 saat (tek bir pencere), V3: 72-96 saat
    for versiyon in (3, 2, 1):  # en son pasta once — V3 daha once dogru
        araliklar = STORY_VERSIYO_SURELERI[versiyon]
        if any(beg <= gecikme_saate <= end for beg, end in [(
            araliklar[0], araliklar[-1] if len(araliklar) > 1 else araliklar[0]
        )]):
            # V2 tek saat (24) — kesin
            if versiyon == 2:
                if abs(gecikme_saate - 24) <= 6:
                    return 2
                continue
            return versiyon
    return None


def _story_metni_uret(project_dir: str, versiyon: int) -> str:
    """Hikaye overlay metni (versiyona gore)."""
    meta = _load_meta(project_dir)
    title = meta.get("title", "Yeni Parça")
    dil = resolve_language(meta)
    return build_story_overlay(title=title, versiyon=versiyon, dil=dil, meta=meta)


def _container_olustur(project_dir: str, access_token: str, ig_user_id: str, keyframe_url: str, versiyon: int) -> str:
    """STORIES container olustur. creation_id donderir."""
    caption_metni = _story_metni_uret(project_dir, versiyon)
    media_data = {
        "media_type": "STORIES",
        "image_url": keyframe_url,
        "caption": caption_metni,
        "access_token": access_token,
    }
    # Not: Instagram story container'ı için 'caption' alanı destekleniyor
    # (v21.0+), hikaye ustune yazilan metin — ancak bu hikaye overlay
    # text sticker olarak gozukebilir (platform davranisi). Alternatif olarak
    # text overlay icin ayrı bir yontem gerekebilir — şimdilik caption ile.
    create_resp = _graph_istek_post(
        f"{GRAPH_API}/{ig_user_id}/media",
        data=media_data,
        ne_yapiliyordu="hikaye container olusturma",
    )
    creation_id = create_resp.json()["id"]
    print(f"  hikaye container olusturuldu: creation_id={creation_id} (versiyon={versiyon})")
    return creation_id


def _graph_istek_post(url: str, data: dict, ne_yapiliyordu: str, timeout=(10, 30)) -> dict:
    """Basit POST istegi — hikaye container icin. Token log'a dusmez."""
    token = get_access_token()
    access_token = token["access_token"]
    ig_user_id = token["ig_user_id"]

    # context: token POST body'de (instagram_upload.py veya parametreler)
    data["access_token"] = access_token

    import requests
    from gizli_maskele import maskele

    resp = requests.post(url, data=data, timeout=timeout)
    if resp.status_code >= 400:
        raise RuntimeError(
            f"Instagram {ne_yapiliyordu}: HTTP {resp.status_code} — "
            f"{maskele(resp.text[:300])}"
        )
    return resp.json()


def _publish_container(ig_user_id: str, access_token: str, creation_id: str, project_dir: str) -> str:
    """Hazır container yayınlanir, media_id donderir."""
    publish_resp = _graph_istek_post(
        f"{GRAPH_API}/{ig_user_id}/media_publish",
        data={"creation_id": creation_id, "access_token": access_token},
        ne_yapiliyordu="hikaye yayinlama (media_publish)",
        timeout=(10, 30),
    )
    media_id = publish_resp["id"]
    print(f"  tamam: media_id={media_id}")
    return media_id


def _try_publish_pending(project_dir: str, sebep_out: dict | None = None) -> str | None:
    """Bekleyen hikaye container varsa kontrol et, golden-hour'da yayinla."""
    state = _load_state(project_dir)
    creation_id = state.get("story_container_id")
    if not creation_id:
        if sebep_out is not None:
            sebep_out["kod"] = "bekleyen_yok"
        return None

    # Yas kapisi
    if _konteyner_bayat(state):
        _bekleyen_konteyneri_temizle(
            project_dir, state, creation_id,
            "24 saatlik omrunu asmis (hiks ye kapisi)"
        )
        if sebep_out is not None:
            sebep_out["kod"] = "bayat_temizlendi"
        return None

    # Cift yayin korumasi
    if state.get("story_published_at") and not _konteyner_yayindan_yeni(state):
        if sebep_out is not None:
            sebep_out["kod"] = "zaten_yayinlandi"
        return None

    token = get_access_token()
    access_token = token["access_token"]
    ig_user_id = token["ig_user_id"]

    # Container durumu
    try:
        import requests
        resp = requests.get(
            f"{GRAPH_API}/{creation_id}",
            params={"fields": "status_code", "access_token": access_token},
            timeout=(10, 30),
        )
        resp.raise_for_status()
        status_code = resp.json().get("status_code")
    except Exception as e:
        raise RuntimeError(f"Instagram hikaye container durumu okunamadi: {e}") from e

    if status_code == "EXPIRED":
        _bekleyen_konteyneri_temizle(
            project_dir, state, creation_id, "sureli dolmus (EXPIRED)"
        )
        if sebep_out is not None:
            sebep_out["kod"] = "suresi_doldu"
        return None
    if status_code != "FINISHED":
        print(f"  Instagram hikaye: container hala isleniyor ({status_code})")
        if sebep_out is not None:
            sebep_out["kod"] = "isleniyor"
        return None

    # Golden-hour kontrolü
    if config.next_golden_publish_time() is not None:
        print(f"  Instagram hikaye: container hazir (creation_id={creation_id}), golden-hour bekleniyor")
        if sebep_out is not None:
            sebep_out["kod"] = "golden_hour_bekleniyor"
        return None

    # Yayinla
    media_id = _publish_container(ig_user_id, access_token, creation_id, project_dir)
    print(f"  Instagram hikaye: yayinlandi (versiyon container id={creation_id})")
    _save_state(project_dir, {
        "story_published_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "story_media_id": media_id,
    })
    if sebep_out is not None:
        sebep_out["kod"] = "yayinlandi"
    return media_id


def _story_container_olustur(project_dir: str) -> str | None:
    """Yeni hikaye container olustur (golden-hour'da calisirsan hemen yayinla)."""
    project_dir = os.path.abspath(project_dir)
    keyframe_path = _find_story_keyframe(project_dir)
    if not keyframe_path:
        print(f"  Instagram hikaye: keyframe bulunamadi ({project_dir})")
        return None

    token = get_access_token()
    access_token = token["access_token"]
    ig_user_id = token["ig_user_id"]

    # Versiyonu belirle
    state = _load_state(project_dir)
    meta = _load_meta(project_dir)
    versiyon = _story_versiyonu_tarafi_bul(state, meta)
    if versiyon is None:
        # Hicbir versiyon capamis — varsayılan V1
        versiyon = 1

    # Keyframe URL'i — Netlify ile depolama (instagram_upload.py ile ayni yol)
    # Hikaye container'i image_url gorur — keyframe'i Netlify'a yüklüyoruz.
    try:
        import instagram_upload
        urls = instagram_upload._upload_to_netlify([keyframe_path])
        keyframe_url = list(urls.values())[0]
    except Exception as e:
        print(f"  Instagram hikaye: keyframe yukleme hatasi: {e}")
        return None

    # Container olustur
    creation_id = _container_olustur(project_dir, access_token, ig_user_id, keyframe_url, versiyon)

    # State'e kaydet
    _save_state(project_dir, {
        "story_container_id": creation_id,
        "story_container_created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "story_versiyon": versiyon,
    })

    # Golden-hour varsa hemen yayinla
    if config.next_golden_publish_time() is None:
        print(f"  Instagram hikaye: golden-hour penceresinde — hemen yayinla")
        return _try_publish_pending(project_dir)
    else:
        print(f"  Instagram hikaye: container hazir (creation_id={creation_id}), golden-hour bekleniyor")
        return None


def try_publish_pending(project_dir: str, sebep_out: dict | None = None) -> str | None:
    """Dışarıdan cagrilabilen: hikaye container kontrol + yayin (Varsa)."""
    return _try_publish_pending(project_dir, sebep_out)


def create_story(project_dir: str) -> str | None:
    """Yeni hikaye container olustur (dışarıdan cagrilabilen)."""
    return _story_container_olustur(project_dir)


def main():
    parser = argparse.ArgumentParser(description="Instagram hikaye (story) container olustur/yayinla.")
    parser.add_argument("--project", required=True, help="Proje klasoru (orn. projects/sarki-adi)")
    parser.add_argument("--action", choices=["create", "publish"], help="islem tipi")
    args = parser.parse_args()

    project_dir = os.path.abspath(args.project)
    if args.action == "create":
        _story_container_olustur(project_dir)
    elif args.action == "publish":
        _try_publish_pending(project_dir)
    else:
        # Varsayilan: create + golden-hour varsa publish
        _story_container_olustur(project_dir)


if __name__ == "__main__":
    main()
