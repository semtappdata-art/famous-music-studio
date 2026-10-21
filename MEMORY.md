# MODEL KILIDI — Sabit

**Seçilen model:** `gemma2:2b` (ollama, ücretsiz, 1.6GB)
- Basit düşünür, hızlı, düşük token
- %40 özetici hafıza ile oturum içi hatırla
- Her oturum sonunda token tasarrufu önerisi verir

## Kullanım

```python
import session_memory as sm

# Oturum başı — son 4 özetleri al
ctx = sm.load_context(limit=4)

# Her işlem sonrası
sm.log("action brief", "result brief", tokens=120)

# Oturum sonu raporu
print(sm.session_report())
```

## Kilidi Kaldır
```bash
del .model_lock
del .session_journal.jsonl
```

## Neden gemma2:2b?
- En küçük ücretsiz model (1.6GB) → hızlı
- Ollama yerel → internet gerekmez
- Basit karar + özetleme görevleri için yeterli
- Complex reasoning ihtiyacında `phi3.5` veya `groq Llama-3.3-70B` kullan
