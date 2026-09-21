# AGENT.md — Famous Music Studio Çalışma Notu

Bu dosya bu repoda çalışan kod ajanı için kısa operasyon sözleşmesidir. Ayrıntılı ve bağlayıcı proje hafızası `CLAUDE.md` dosyasıdır; çelişki olursa `CLAUDE.md` kazanır.

> Not: Dosya bilerek `AGENTS.md` değil. Repo belgelerinde `.hermes.md`/`AGENTS.md` dosyalarının özellikle kullanılmadığı yazıyor; Hermes/diğer araçların bağlam önceliğini değiştirmemek için tekil ad seçildi.

## 1. Hızlı bağlam

- Proje: Suno şarkılarından otomatik video üretimi ve çoklu platform yayın hattı.
- Ana giriş: `auto_process.py`.
- Render hattı: `audio.wav` → `generate_cover.py` → `validate_project.py` → `render.py` → platform yüklemeleri.
- Ayrı hatlar: `dj_sets/` ve `derlemeler/`, giriş `dj_famous_process.py`.
- Kritik ilke: Yeni adım eklenirse **kim çağıracak, hangi zamanlayıcıdan, çalışmadığı nasıl anlaşılacak** soruları cevaplanmadan iş bitmiş sayılmaz.

## 2. Çalışma kuralları

1. Önce ilgili belgeyi oku: genel işlerde `CLAUDE.md`, kullanımda `README.md`, render/video işlerinde `.claude/skills/suno-video-render/SKILL.md`.
2. Üretim verisini koru: `git reset --hard`, `git clean -f` ve state dosyalarını elle ezmek yasak sayılır.
3. `state.json` yazacaksan `state_io.py` kullan.
4. Yeni platform/adımı `_is_fully_done()` içine ekleme; uygun yer genelde `auto_process.main()` `finally` bloğu veya ayrı süpürgedir.
5. Zamanlayıcı sayısı üçtür: `auto_process.py`, `dj_famous_process.py`, `watch_projects.py`. Yeni görev ekleme; mevcut hatta bağla.
6. Kapılar fail-closed kalmalı: `uyumluluk.kontrol()` hatası “temiz” sayılmaz.
7. Elle yapılan platform işlemleri `elle_islem.py` / `elle_islemler.jsonl` defterine yazılır.
8. Test çalıştırırken Windows için doğru kalıp:
   ```bash
   python -m pytest -q -p no:cacheprovider --basetemp="<scratchpad>/pytest_tmp"
   ```

## 3. Basit İletişim Standardı — STE

STE, kullanıcı ile ajan arasında kısa ve tekrar eden cevap biçimidir.

### STE çıktı biçimi

Her teknik cevap mümkünse şu sırayı izler:

1. **Özet:** Ne yapılacak / ne bulundu? 1-3 madde.
2. **Durum:** Dosya, komut, test veya kararların güncel hali.
3. **Eylem:** Yapılan değişiklikler veya önerilen net sonraki adım.

### STE etiketleri

- `STE:PLAN` — işe başlamadan kısa plan.
- `STE:DURUM` — ara durum / ilerleme.
- `STE:KARAR` — kullanıcı kararı gereken yer.
- `STE:RİSK` — geri dönüşü zor risk veya üretim verisi riski.
- `STE:TEST` — çalıştırılan/çalıştırılmayan testler.
- `STE:TESLİM` — iş bitti özeti.

### Kısa örnek

```text
STE:PLAN
Özet: Kapak üretimindeki taşma hatasını inceleyeceğim.
Durum: Önce generate_cover.py ve ilgili testlere bakacağım.
Eylem: Bulgudan sonra küçük bir patch + test çalıştıracağım.
```

## 4. Ajanın varsayılan cevap dili

- Kullanıcı Türkçe yazarsa Türkçe cevap ver.
- Gereksiz uzun açıklama yapma; risk, test ve dosya yollarını açık yaz.
- Belirsiz üretim etkisi varsa önce sor; salt belge/küçük kod değişikliğinde doğrudan ilerle.
