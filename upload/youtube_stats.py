"""Yüklenmiş bir projenin YouTube istatistiklerini (görüntülenme, beğeni) çeker.

Kullanım:
    python upload/youtube_stats.py --project "projects/beni bırakma"

projects/<isim>/state.json'daki youtube_video_id'yi kullanır, sonucu aynı
dosyaya (views/likes/last_checked) yazar.
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import state_io
from youtube_auth import get_authenticated_service


def get_stats(project_dir: str) -> dict:
    state_path = os.path.join(project_dir, "state.json")
    if not os.path.isfile(state_path):
        raise FileNotFoundError(f"{state_path} bulunamadı — önce upload/youtube_upload.py ile yükle.")

    with open(state_path, "r", encoding="utf-8") as f:
        state = json.load(f)

    video_id = state.get("youtube_video_id")
    if not video_id:
        raise ValueError(f"{state_path} içinde youtube_video_id yok.")

    youtube = get_authenticated_service()
    response = youtube.videos().list(part="statistics,status", id=video_id).execute()
    items = response.get("items", [])
    if not items:
        raise ValueError(f"Video bulunamadı: {video_id}")

    stats = items[0]["statistics"]
    status = items[0]["status"]

    state["youtube_views"] = int(stats.get("viewCount", 0))
    state["youtube_likes"] = int(stats.get("likeCount", 0))
    state["youtube_comments"] = int(stats.get("commentCount", 0))
    state["youtube_privacy"] = status.get("privacyStatus", state.get("youtube_privacy"))
    state["youtube_stats_checked_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")

    # ATOMIK yazim (state_io) — eskiden ham `open(state_path, "w")` idi.
    # `open` dosyayi once SIFIRLIYOR: yarida kesilen bir yazim diskte yarim
    # bir JSON birakiyordu ve `uyumluluk._durum()` sertlestikten sonra bu
    # `DurumBozuk` -> HATA demek, yani o proje TAMAMEN yayin disi kaliyor.
    # Istatistik cekmek gibi TAMAMEN ISTEGE BAGLI bir islemin yayin hattini
    # durdurabilmesi kabul edilemez.
    state_io._atomik_yaz(state_path, state)

    return state


BATCH_SINIRI = 50          # videos.list tek istekte en fazla 50 id kabul ediyor
TAZELEME_ARALIGI_SN = 20 * 60 * 60   # gunde bir; saatlik kosuda tekrar tekrar cekmesin


def _durum_yolu(project_dir: str) -> str:
    return os.path.join(project_dir, "state.json")


def _oku(yol: str) -> dict:
    try:
        with open(yol, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _eskimis_mi(state: dict) -> bool:
    damga = state.get("youtube_stats_checked_at")
    if not damga:
        return True
    try:
        t = time.mktime(time.strptime(damga, "%Y-%m-%dT%H:%M:%S"))
    except ValueError:
        return True
    return (time.time() - t) >= TAZELEME_ARALIGI_SN


# Katalogun UC koku var (projects / dj_sets / derlemeler). dj_sets uzun sure
# gozden kaciyordu: 2 set (City Pulse, Just Relax) YouTube'a yuklenmis ama
# hicbir olcume girmiyordu — hatta okunmamis yorumlardan biri o setlerden
# birine gelmisti. `derlemeler` de ayni sekilde sonradan eklendi.
# Liste artik ELLE SAYILMIYOR: tek kanonik kaynak `uyumluluk.KOKLER` (mutlak
# yollar — goreli birakilirsa yanlis cwd'de os.path.isdir False doner ve
# fonksiyon SESSIZCE bos sonuc uretir). Yeni bir kok acilirsa burasi
# kendiliginden kapsar. Muhafiz: tests/test_kok_listesi_muhafizi.py
from uyumluluk import KOKLER      # noqa: E402  (sys.path yukarida kuruluyor)


def get_stats_batch(base: str | None = None, force: bool = False) -> dict:
    """TUM projelerin uzun + Shorts istatistiklerini TEK API cagrisinda ceker.

    Neden toplu: get_stats() proje basina bir istek atiyor (18 proje = 18 istek)
    ve Shorts'u HIC olcmuyor — oysa 18/18 projede youtube_shorts_video_id dolu,
    yani katalogun yarisi hic olculmuyordu. videos.list tek istekte 50 id
    kabul ediyor: 18 uzun + 18 Shorts = 36 id = 1 istek = 1 kota birimi.

    Onceki anlik goruntu de saklaniyor (`*_prev`, `youtube_stats_prev_at`):
    tek basina "142 izlenme" bir sey soylemiyor, "son gunde +12" soyluyor.
    Delta hesaplanabilsin diye ustune yazmadan once eskisi kenara aliniyor.

    force=False ise TAZELEME_ARALIGI_SN dolmadan hicbir istek atilmaz — bu
    fonksiyon saatlik auto_process'ten cagriliyor.
    """
    # base verilmezse HER IKI kok taranir; verilirse (testler, tek kok islemek
    # isteyen cagrilar) yalnizca o.
    kokler = (base,) if base else KOKLER

    hedefler = []          # (state_yolu, alan_oneki, video_id)
    klasorler = []
    for kok in kokler:
        if not os.path.isdir(kok):
            continue
        klasorler.extend(os.path.join(kok, a) for a in sorted(os.listdir(kok)))

    for klasor in klasorler:
        if not os.path.isdir(klasor):
            continue
        yol = _durum_yolu(klasor)
        st = _oku(yol)
        if not st:
            continue
        if not force and not _eskimis_mi(st):
            continue
        if st.get("youtube_video_id"):
            hedefler.append((yol, "youtube", st["youtube_video_id"]))
        if st.get("youtube_shorts_video_id"):
            hedefler.append((yol, "youtube_shorts", st["youtube_shorts_video_id"]))

    if not hedefler:
        return {"istek": 0, "video": 0, "proje": 0}

    youtube = get_authenticated_service()
    olcum = {}
    idler = [h[2] for h in hedefler]
    istek = 0
    for i in range(0, len(idler), BATCH_SINIRI):
        dilim = idler[i:i + BATCH_SINIRI]
        yanit = youtube.videos().list(part="statistics",
                                      id=",".join(dilim),
                                      maxResults=BATCH_SINIRI).execute()
        istek += 1
        for x in yanit.get("items", []):
            olcum[x["id"]] = x.get("statistics", {})

    simdi = time.strftime("%Y-%m-%dT%H:%M:%S")
    yazilan = {}
    for yol, onek, vid in hedefler:
        s = olcum.get(vid)
        if s is None:
            continue          # silinmis/erisilemez video — sessizce atla
        st = yazilan.get(yol) or _oku(yol)
        for alan, anahtar in (("views", "viewCount"),
                              ("likes", "likeCount"),
                              ("comments", "commentCount")):
            yeni_ad = "%s_%s" % (onek, alan)
            if yeni_ad in st:
                st["%s_prev" % yeni_ad] = st[yeni_ad]
            st[yeni_ad] = int(s.get(anahtar, 0) or 0)
        yazilan[yol] = st

    # Zaman damgasi PROJE BASINA bir kez guncelleniyor, hedef basina degil:
    # her projenin iki hedefi var (uzun + Shorts) ve bu blok donguden
    # cikarilmazsa ikinci hedef, ilk hedefin az once yazdigi damgayi
    # "onceki" sanip prev_at == checked_at yaziyordu — delta hep sifir cikardi.
    for yol, st in yazilan.items():
        if st.get("youtube_stats_checked_at"):
            st["youtube_stats_prev_at"] = st["youtube_stats_checked_at"]
        st["youtube_stats_checked_at"] = simdi

    # ATOMIK yazim (state_io) — bu dongudeki ham `open(yol, "w")` dosyanin EN
    # RISKLI yaziciydi: saatlik kosuda ONLARCA projenin state.json'i art arda
    # uzerine yaziliyor, yani tek bir kesinti (timeout/guc) hangi projeye denk
    # gelirse o projeyi `uyumluluk._durum()` -> `DurumBozuk` -> HATA ile
    # tamamen yayin disi birakiyordu. `_atomik_yaz` ile her dosya ya tam eski
    # ya tam yeni halini koruyor. (Dongu bilerek ayni: her proje AYRI bir
    # atomik yazim — toplu bir "ya hep ya hic" garantisine gerek yok, her
    # state.json bagimsiz.)
    for yol, st in yazilan.items():
        state_io._atomik_yaz(yol, st)

    return {"istek": istek, "video": len(olcum), "proje": len(yazilan)}


def main():
    parser = argparse.ArgumentParser(description="YouTube video istatistiklerini çeker.")
    parser.add_argument("--project", required=True, help="Proje klasörü (örn. projects/sarki-adi)")
    args = parser.parse_args()

    state = get_stats(args.project)
    print(f"  görüntülenme: {state['youtube_views']}")
    print(f"  beğeni: {state['youtube_likes']}")
    print(f"  yorum: {state['youtube_comments']}")
    print(f"  görünürlük: {state['youtube_privacy']}")


if __name__ == "__main__":
    main()
