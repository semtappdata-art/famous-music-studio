"""Universal Model Connector - Clean rewrite."""
import os, json, urllib.request, hashlib
from dataclasses import dataclass
from typing import Dict, List, Optional
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ─── Config ──────────────────────────────────────────────
@dataclass
class ModelConfig:
    name: str
    provider: str
    api_base: str
    api_key_env: str
    context: int
    free: bool
    strengths: List[str]

# ─── Models ──────────────────────────────────────────────
MODELS = {
    # Local Ollama
    "gemma2:2b": ModelConfig("gemma2:2b", "ollama", "http://localhost:11434", "", 8192, True, ["speed", "privacy", "free"]),
    "phi3.5:latest": ModelConfig("phi3.5:latest", "ollama", "http://localhost:11434", "", 131072, True, ["reasoning", "code"]),
    "qwen3.5:4b": ModelConfig("qwen3.5:4b", "ollama", "http://localhost:11434", "", 262144, True, ["code", "multimodal", "context"]),
    # OpenRouter Free
    "nemotron-3.5-lightning": ModelConfig("nvidia/nemotron-3.5-lightning:free", "openrouter", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", 131072, True, ["reasoning", "code", "fast"]),
    "nemotron-3-ultra": ModelConfig("nvidia/nemotron-3-ultra-550b-a55b:free", "openrouter", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", 1000000, True, ["reasoning", "code", "context"]),
    "ling-3.1-flash": ModelConfig("inclusionai/ling-3.1-flash", "openrouter", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", 131072, True, ["speed", "code"]),
    "apodex-mini": ModelConfig("apodex/apodex-1.1-mini:free", "openrouter", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", 131072, True, ["reasoning", "code"]),
    "nemotron-nano": ModelConfig("nvidia/nemotron-nano", "openrouter", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", 131072, True, ["reasoning", "omni"]),
    "openrouter-free": ModelConfig("openrouter/free", "openrouter", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", 131072, True, ["general"]),
    "gemma-4-26b": ModelConfig("google/gemma-4-26b-it:free", "openrouter", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", 131072, True, ["code", "reasoning"]),
    "gemma-4-31b": ModelConfig("google/gemma-4-31b-it:free", "openrouter", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", 131072, True, ["code", "reasoning"]),
    # Anthropic
    "claude-3.5-sonnet": ModelConfig("claude-3-5-sonnet-20241022", "anthropic", "https://api.anthropic.com/v1", "ANTHROPIC_API_KEY", 200000, False, ["code", "reasoning", "speed"]),
    "claude-3.5-haiku": ModelConfig("claude-3-5-haiku-20241022", "anthropic", "https://api.anthropic.com/v1", "ANTHROPIC_API_KEY", 200000, False, ["speed", "code", "cost-efficient"]),
    "claude-3-opus": ModelConfig("claude-3-opus-20240229", "anthropic", "https://api.anthropic.com/v1", "ANTHROPIC_API_KEY", 200000, False, ["reasoning", "code", "analysis"]),
    # Groq
    "llama-3.3-70b-groq": ModelConfig("llama-3.3-70b-special", "groq", "https://api.groq.com/openai/v1", "GROQ_API_KEY", 131072, False, ["speed", "code", "reasoning"]),
    "mixtral-8x7b-groq": ModelConfig("mixtral-8x7b-xxx", "groq", "https://api.groq.com/openai/v1", "GROQ_API_KEY", 32768, False, ["speed", "general"]),
    "gemma2-9b-groq": ModelConfig("gemma2-9b-xxx", "groq", "https://api.groq.com/openai/v1", "GROQ_API_KEY", 8192, False, ["speed", "instruction"]),
    # NVIDIA
    "llama-3.3-70b-nvidia": ModelConfig("llama-3.3-70b-instruct", "nvidia", "https://integrate.api.nvidia.com/v1", "NVIDIA_API_KEY", 131072, False, ["speed", "code"]),
    # Video
    "kling-v1": ModelConfig("kling-v1", "kling", "https://api.klingai.com", "KLING_API_KEY", 999999, False, ["video"]),
    "runway-gen3": ModelConfig("runway-gen3", "runway", "https://api.runwayml.com", "RUNWAY_API_KEY", 999999, False, ["video"]),
    "stability-svd": ModelConfig("stability-svd", "stability", "https://api.stability.ai", "STABILITY_API_KEY", 999999, False, ["video"]),
    "luma-ray2": ModelConfig("luma-ray2", "luma", "https://api.lumalabs.ai", "LUMA_API_KEY", 999999, False, ["video"]),
    "pika": ModelConfig("pika", "pika", "https://api.pika.art", "PIKA_API_KEY", 999999, False, ["video"]),
    "minimax": ModelConfig("minimax", "minimax", "https://api.minimax.chat", "MINIMAX_API_KEY", 999999, False, ["video"]),
    "haiper": ModelConfig("haiper", "haiper", "https://api.haiper.ai", "HAIPER_API_KEY", 999999, False, ["video"]),
}

# ─── f&f / özgür-ünlü Brand ────────────────────────────
FF_ALIASES = {
    "özgür-ünlü": "gemma2:2b", "özgür-ünlü-hızlı": "gemma2:2b",
    "özgür-ünlü-kod": "qwen3.5:4b", "özgür-ünlü-akıl": "phi3.5:latest",
    "özgür-ünlü-maks": "qwen3.5:4b", "özgür-ünlü-nice": "qwen3.5:4b",
    "f&f": "gemma2:2b", "f&f-fast": "gemma2:2b", "f&f-code": "qwen3.5:4b",
    "f&f-reason": "phi3.5:latest", "f&f-max": "qwen3.5:4b",
}

# ─── Providers ───────────────────────────────────────────
class OllamaProvider:
    def call(self, model, messages, temperature=0.1, max_tokens=512, ctx_size=4096, **_):
        prompt = chr(10).join([f"{m['role']}: {m['content']}" for m in messages])
        data = {"model": model, "prompt": prompt, "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens, "ctx_size": ctx_size}}
        req = urllib.request.Request(f"{MODELS[model].api_base}/api/generate",
                                     json.dumps(data).encode(), {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode()).get("response", "").strip()
    
    def stream(self, model, messages, temperature=0.1, max_tokens=512, ctx_size=4096, **_):
        prompt = chr(10).join([f"{m['role']}: {m['content']}" for m in messages])
        data = {"model": model, "prompt": prompt, "stream": True,
                "options": {"temperature": temperature, "num_predict": max_tokens, "ctx_size": ctx_size}}
        req = urllib.request.Request(f"{MODELS[model].api_base}/api/generate",
                                     json.dumps(data).encode(), {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            for line in r:
                line = line.decode().strip()
                if line.startswith("data: "):
                    try:
                        chunk = json.loads(line[6:])
                        if "response" in chunk: yield chunk["response"]
                        if chunk.get("done", False): break
                    except: pass

class OpenAICompatibleProvider:
    def __init__(self, api_base, api_key_env, extra_headers=None):
        self.api_base = api_base
        self.api_key_env = api_key_env
        self.api_key = os.getenv(api_key_env, "")
        self.extra_headers = extra_headers or {}
    
    def call(self, model, messages, temperature=0.1, max_tokens=512, **_):
        headers = {"Content-Type": "application/json"}
        if self.api_key: headers["Authorization"] = f"Bearer {self.api_key}"
        headers.update(self.extra_headers)
        data = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
        req = urllib.request.Request(self.api_base + "/chat/completions",
                                     json.dumps(data).encode(), headers)
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())["choices"][0]["message"]["content"].strip()
    
    def stream(self, model, messages, temperature=0.1, max_tokens=512, **_):
        headers = {"Content-Type": "application/json"}
        if self.api_key: headers["Authorization"] = f"Bearer {self.api_key}"
        headers.update(self.extra_headers)
        data = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens, "stream": True}
        req = urllib.request.Request(self.api_base + "/chat/completions",
                                     json.dumps(data).encode(), headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                for line in r:
                    line = line.decode().strip()
                    if line.startswith("data: "):
                        chunk = line[6:]
                        if chunk == "[DONE]": break
                        try:
                            d = json.loads(chunk)
                            delta = d.get("choices", [{}])[0].get("delta", {})
                            if "content" in delta: yield delta["content"]
                        except: pass
        except Exception as e: yield f"ERR: {e}"

class AnthropicProvider:
    def __init__(self): self.api_key = os.getenv("ANTHROPIC_API_KEY", "")
    def call(self, model, messages, temperature=0.1, max_tokens=512, **_):
        if not self.api_key: return "ERR: ANTHROPIC_API_KEY not set"
        system = ""
        user_msgs = []
        for m in messages:
            if m["role"] == "system": system = m["content"]
            else: user_msgs.append(m)
        data = {"model": model, "messages": user_msgs, "temperature": temperature, "max_tokens": max_tokens}
        if system: data["system"] = system
        req = urllib.request.Request("https://api.anthropic.com/v1/messages",
                                     json.dumps(data).encode(),
                                     {"Content-Type": "application/json", "x-api-key": self.api_key, "anthropic-version": "2023-06-01"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())["content"][0]["text"]

class GoogleProvider:
    def __init__(self): self.api_key = os.getenv("GOOGLE_API_KEY", "")
    def call(self, model, messages, temperature=0.1, max_tokens=512, **_):
        if not self.api_key: return "ERR: GOOGLE_API_KEY not set"
        system = ""
        user_msgs = []
        for m in messages:
            if m["role"] == "system": system = m["content"]
            else: user_msgs.append(m)
        data = {"model": model, "contents": user_msgs, "temperature": temperature, "maxOutputTokens": max_tokens}
        if system: data["system_instruction"] = system
        req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key=" + self.api_key,
                                     json.dumps(data).encode(), {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())["candidates"][0]["content"]["parts"][0]["text"]

class NvidiaProvider:
    def __init__(self): self.api_key = os.getenv("NVIDIA_API_KEY", "")
    def call(self, model, messages, temperature=0.1, max_tokens=512, **_):
        if not self.api_key: return "ERR: NVIDIA_API_KEY not set"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
        data = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
        req = urllib.request.Request("https://integrate.api.nvidia.com/v1/chat/completions",
                                     json.dumps(data).encode(), headers)
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())["choices"][0]["message"]["content"].strip()

class TogetherProvider:
    def __init__(self): self.api_key = os.getenv("TOGETHER_API_KEY", "")
    def call(self, model, messages, temperature=0.1, max_tokens=512, **_):
        if not self.api_key: return "ERR: TOGETHER_API_KEY not set"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
        data = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
        req = urllib.request.Request("https://api.together.xyz/v1/chat/completions",
                                     json.dumps(data).encode(), headers)
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())["choices"][0]["message"]["content"].strip()

class VideoProvider:
    def call(self, model, messages, **_): return "ERR: Video API - use video() function"
    def stream(self, model, messages, **_): yield "ERR: Video streaming not supported"

PROVIDERS = {
    "ollama": OllamaProvider(),
    "openrouter": OpenAICompatibleProvider("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", {"HTTP-Referer": "http://localhost:8000", "X-Title": "FamousStudio"}),
    "groq": OpenAICompatibleProvider("https://api.groq.com/openai/v1", "GROQ_API_KEY"),
    "together": TogetherProvider(),
    "google": GoogleProvider(),
    "anthropic": AnthropicProvider(),
    "nvidia": NvidiaProvider(),
    "kling": VideoProvider(), "runway": VideoProvider(), "stability": VideoProvider(),
    "luma": VideoProvider(), "pika": VideoProvider(), "minimax": VideoProvider(), "haiper": VideoProvider(),
}

# ─── Paths ───────────────────────────────────────────────
KB_DIR = Path(".universal_kb")
FB_DIR = Path(".feedback")
KB_DIR.mkdir(exist_ok=True)
FB_DIR.mkdir(exist_ok=True)

# ─── Router ──────────────────────────────────────────────
def route_model(query: str) -> str:
    # PI_MODEL_LOCK varsa onu kullan (format: model@provider)
    lock = os.getenv("PI_MODEL_LOCK", "").strip()
    if lock:
        # Sadece model adı kısmını al (provider kısmını at)
        model_name = lock.split("@")[0]
        if model_name in MODELS:
            return model_name
    q = query.lower()
    if q in FF_ALIASES: return FF_ALIASES[q]
    if any(w in q for w in ["code", "debug", "python", "async", "api", "class", "function", "fix"]): return "gemma2:2b"
    if any(w in q for w in ["video", "generate", "visual", "clip", "render"]): return "kling-v1"
    if any(w in q for w in ["analyze", "reason", "complex", "architect", "design"]): return "nemotron-3.5-lightning"
    return "gemma2:2b"

# ─── Knowledge Base ──────────────────────────────────────
def kb_add(domain: str, key: str, value: str, source: str = "manual"):
    path = KB_DIR / f"{domain}.jsonl"
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"key": key, "value": value, "source": source}, ensure_ascii=False) + chr(10))

def kb_query(q: str, domain: Optional[str] = None, limit: int = 3):
    results = []
    pattern = q.lower()
    for p in KB_DIR.glob("*.jsonl"):
        if domain and p.stem != domain: continue
        try:
            with open(p, encoding="utf-8") as f:
                for line in f:
                    d = json.loads(line.strip())
                    if pattern in d.get("key", "").lower() or pattern in d.get("value", "").lower():
                        results.append((p.stem, d))
        except: pass
    return results[:limit]

def kb_ctx(q, d=None):
    hits = kb_query(q, d)
    return chr(10).join([f"[{h[0]}] {h[1].get('value', '')}" for h in hits]) if hits else ""

def kb_list(): return [p.stem for p in KB_DIR.glob("*.jsonl")]

# ─── Feedback ────────────────────────────────────────────
def fb_key(query: str) -> str: return hashlib.sha256(query.encode()).hexdigest()[:16]

def fb_add(query: str, answer: str, rating: int, fix: str = ""):
    path = FB_DIR / f"{fb_key(query)}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"query": query, "answer": answer, "rating": rating, "fix": fix}, f, ensure_ascii=False)

# ─── Masking ─────────────────────────────────────────────
def mask_sensitive(data: str) -> str:
    for key, val in os.environ.items():
        if any(k in key for k in ["KEY", "TOKEN", "SECRET", "PASSWORD"]):
            data = data.replace(val, "***"[:len(val)//2] + "***")
    return data

# ─── Learning ────────────────────────────────────────────
def learn_from_feedback():
    if not FB_DIR.exists(): return
    for p in FB_DIR.glob("*.json"):
        try:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
            if d.get("rating", 3) <= 2 and d.get("fix"):
                kb_add("feedback", fb_key(d["query"])[:8], d["fix"], "fb")
        except: pass

learn_from_feedback()

# ─── Main Functions ──────────────────────────────────────
def ask(query: str, model: Optional[str] = None, domain: str = "general",
        tr: bool = True, fb: bool = False, stream: bool = False,
        fallback: bool = True, **kwargs) -> str:
    """Universal ask - auto-router + KB + feedback + fallback chain."""
    if model is None: model = route_model(query)
    
    fallback_chain = [model]
    if fallback and model != "gemma2:2b":
        fallback_chain.extend(["gemma2:2b", "nemotron-3.5-lightning", "ling-3.1-flash", "openrouter-free", "phi3.5:latest"])
    elif fallback:
        fallback_chain.extend(["nemotron-3.5-lightning", "ling-3.1-flash", "openrouter-free"])
    
    ctx = kb_ctx(query, domain)
    sys_prompt = "You are a senior engineer. Format: [A] 1 line -> [C] code -> [W] 1 line."
    if tr: sys_prompt += " Turkish explanation."
    messages = [{"role": "system", "content": sys_prompt}]
    if ctx: messages.append({"role": "system", "content": "Knowledge: " + ctx})
    messages.append({"role": "user", "content": query})
    
    ans = "ERR: All models failed"
    tried = set()
    for fb_model in fallback_chain:
        if fb_model in tried: continue
        tried.add(fb_model)
        fb_cfg = MODELS.get(fb_model)
        if not fb_cfg: continue
        fb_provider = PROVIDERS.get(fb_cfg.provider)
        if not fb_provider: continue
        try:
            extra_kwargs = dict(kwargs)
            if any(k in fb_model.lower() for k in ["nemotron", "ling", "deepseek", "r1", "o1", "qwq", "reasoning"]):
                extra_kwargs.setdefault("max_tokens", 2048)
            ans = fb_provider.call(fb_model, messages, **extra_kwargs)
            if not ans.startswith("ERR:"):
                model = fb_model
                break
        except Exception:
            continue
    
    if fb:
        print(f"[{model}] Rate 1-5: ", end="")
        try:
            rt = input().strip()
            if rt.isdigit() and 1 <= int(rt) <= 5:
                c = input("Fix: ").strip() if int(rt) < 4 else ""
                fb_add(query, ans, int(rt), c)
                if int(rt) <= 2 and c: kb_add(domain, fb_key(query)[:8], c, "fb")
        except: pass
    
    if "ERR:" not in ans and len(ans) > 20:
        kb_add(domain, fb_key(query)[:8], ans[:500], "auto")
    
    cost_log(model, len(query)*4, len(ans)*2, None)
    return ans

def stream(query: str, model: Optional[str] = None, domain: str = "general",
        tr: bool = True, **kwargs):
    cfg = MODELS.get(model or route_model(query))
    if not cfg: yield "ERR: Unknown model"; return
    provider = PROVIDERS.get(cfg.provider)
    if not provider: yield "ERR: No provider"; return
    sys_prompt = "You are a senior engineer. Format: [A] 1 line -> [C] code -> [W] 1 line."
    if tr: sys_prompt += " Turkish explanation."
    messages = [{"role": "system", "content": sys_prompt}, {"role": "user", "content": query}]
    yield from provider.stream(cfg.name, messages, **kwargs)

def code(q, lang="python", **kw): return ask(f"[LANG:{lang}] {q}", domain="code", **kw)
def debug(c, e, **kw): return ask(f"CODE:\n{c}\n\nERR:\n{e}\n\n[ROOT]->[FIX]->[TEST]", domain="debug", **kw)
def arch(s, **kw): return ask(f"SYS:{s}\n\n[ARCH] comps+flow+API+scale+sec+Mermaid", domain="architect", **kw)
def review(c, **kw): return ask(f"REVIEW:\n{c}\n\n[BUGS][PERF][SEC][STYLE][FIX]", domain="review", **kw)
def test(c, **kw): return ask(f"CODE:\n{c}\n\n[TESTS] pytest+edge+mock+param", domain="test", **kw)

# ─── Video ───────────────────────────────────────────────
def video(prompt: str, model: str = "runway-gen3", duration: int = 5, aspect: str = "16:9", **kw) -> str:
    if model.startswith("kling"):
        api_key = os.getenv("KLING_API_KEY", "")
        if not api_key: return "ERR: KLING_API_KEY not set"
        data = {"prompt": prompt, "duration": duration, "aspect_ratio": aspect}
        req = urllib.request.Request("https://api.klingai.com/v1/videos",
                                     json.dumps(data).encode(),
                                     {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode()).get("data", {}).get("url", "ERR: No URL")
    return "ERR: Video model not supported"

def video_list() -> List[str]: return list(VIDEO_MODELS.keys()) if "VIDEO_MODELS" in dir() else []

# ─── Cost Tracking ───────────────────────────────────────
COST_PER_1K = {
    'gemma2:2b': 0.0, 'phi3.5:latest': 0.0, 'qwen3.5:4b': 0.0,
    'nemotron-3.5-lightning': 0.0, 'nemotron-3-ultra': 0.0,
    'claude-3.5-sonnet': 3.0, 'claude-3.5-haiku': 0.25,
    'llama-3.3-70b-groq': 0.59, 'kling-v1': 0.417, 'runway-gen3': 1.5,
}
COST_LOG = []

def cost_log(model, prompt_tokens, completion_tokens, usage):
    rate = COST_PER_1K.get(model, 0.01)
    cost = (prompt_tokens + completion_tokens) / 1000 * rate
    COST_LOG.append({'model': model, 'input': prompt_tokens, 'output': completion_tokens, 'cost': cost, 'usage': usage})
    return cost

def cost_summary():
    total = sum(e['cost'] for e in COST_LOG)
    print(f"{chr(10)}=== Cost Summary ===")
    print(f"Total calls: {len(COST_LOG)}")
    print(f"Total cost: ${total:.4f}")
    by_model = {}
    for e in COST_LOG:
        by_model.setdefault(e['model'], 0)
        by_model[e['model']] += e['cost']
    for m, c in sorted(by_model.items(), key=lambda x: -x[1]):
        print(f"  {m}: ${c:.4f}")
    return total

def get_cost_log(): return list(COST_LOG)

# ─── Turkish Encoding Fix ────────────────────────────────
def tr_fix(text: str) -> str:
    replacements = {
        'İ': 'I', 'ı': 'i', 'ş': 's', 'Ş': 'S', 'ç': 'c', 'Ç': 'C',
        'ğ': 'g', 'Ğ': 'G', 'ö': 'o', 'Ö': 'O', 'ü': 'u', 'Ü': 'U',
        '→': '->', '✅': '[OK]', '⚡': '[!]', '📁': '[dir]', '📄': '[file]',
        '🔊': '[sound]', '🌹': '[rose]', '❤': '[heart]', '🎵': '[note]',
        '🎧': '[headphones]', '📊': '[chart]', '🔧': '[tool]', '⚠': '[warn]',
        '❌': '[X]', '💰': '[$]', '🚀': '[rocket]', '🔄': '[retry]',
        '⏱': '[time]', '📝': '[note]', '🎬': '[video]', '🎤': '[mic]',
        '💡': '[idea]', '🔑': '[key]', '🔒': '[lock]', '🌐': '[web]',
        '📦': '[pkg]', '🧠': '[brain]', '🤖': '[bot]', '⚙': '[gear]',
        '📋': '[clip]', '🎯': '[target]', '🏆': '[trophy]', '⭐': '[star]',
        '💎': '[gem]',
    }
    for k, v in replacements.items(): text = text.replace(k, v)
    result = []
    for ch in text:
        try:
            ch.encode('cp1254')
            result.append(ch)
        except UnicodeEncodeError:
            result.append('?')
    return ''.join(result)

def tr_print(text: str): print(tr_fix(text))

# ─── FMS Integration ─────────────────────────────────────
def fms_status():
    import os as _os
    files = {
        'auto_process.py': 'Orkestrasyon', 'render.py': 'Video render',
        'generate_cover.py': 'Kapak üret', 'platform_publisher.py': 'Platform yayın',
        'state_io.py': 'State yönetim', 'validate_project.py': 'Doğrulama',
        'config.py': 'Config (75KB)', '.env': 'API keys',
    }
    print(f"{'Dosya':<25} {'Açıklama':<20} {'Durum'}")
    print('-' * 65)
    for f, desc in files.items():
        exists = 'VAR' if _os.path.exists(f) else 'YOK'
        size = _os.path.getsize(f) if _os.path.exists(f) else 0
        print(f"{f:<25} {desc:<20} {exists} ({size}B)")

def fms_fix(file: str, issue: str): return ask(f"[FMS:{file}] {issue}", domain='fms')
def fms_code(task: str, **kw): return code(task, domain='fms', **kw)
def fms_render(audio: str, **kw): return ask(f"[RENDER] {audio}", domain='render', **kw)
def fms_publish(project: str, platforms=None, **kw):
    plats = platforms or ['youtube', 'tiktok', 'instagram']
    return ask(f"[PUBLISH] {project} -> {', '.join(plats)}", domain='publish', **kw)

# ─── List Models ─────────────────────────────────────────
def list_models(free_only=True, local_only=False):
    print(f"{'Model':<30} {'Provider':<12} {'Ctx':>6} {'Free':>5} {'Strengths'}")
    print('-' * 70)
    for name, cfg in MODELS.items():
        if local_only and cfg.provider != 'ollama': continue
        if free_only and not cfg.free: continue
        print(f"{name:<30} {cfg.provider:<12} {cfg.context:>6} {str(cfg.free):>5} {', '.join(cfg.strengths[:3])}")
    print('-' * 70)
    print('f&f / özgür-ünlü brand aliases:')
    for alias, real in FF_ALIASES.items():
        cfg = MODELS.get(real)
        print(f"  {alias:<15} -> {real:<20} ({cfg.provider})")

# ─── Env Validator ──────────────────────────────────
def env_validate():
    """Check which API keys are available."""
    keys = {
        'OPENROUTER_API_KEY': 'OpenRouter (free tier)',
        'ANTHROPIC_API_KEY': 'Anthropic Claude',
        'GOOGLE_API_KEY': 'Google AI Studio',
        'GROQ_API_KEY': 'Groq (ultra fast)',
        'TOGETHER_API_KEY': 'Together AI',
        'OPENAI_API_KEY': 'OpenAI GPT',
        'KLING_API_KEY': 'Kling Video',
        'RUNWAY_API_KEY': 'Runway Gen-3',
        'STABILITY_API_KEY': 'Stability AI',
        'LUMA_API_KEY': 'Luma Labs',
        'NVIDIA_API_KEY': 'NVIDIA',
        'WAVESPEED_API_KEY': 'WaveSpeed',
        'HF_API_KEY': 'HuggingFace',
        'POSTWIRE_TOKEN': 'PostWire MCP',
        'YOUTUBE_API_KEY': 'YouTube Data API',
    }
    print(f"{chr(10)}=== API Key Status ===")
    for key, desc in keys.items():
        val = os.getenv(key, '')
        if val and not val.startswith('your-') and not val.startswith('xxx') and not val.startswith('placeholder'):
            if len(val) > 8:
                print(f"  {desc:<25} OK ({key[:4]}...{key[-4:]})")
            else:
                print(f"  {desc:<25} PLACEHOLDER")
        else:
            print(f"  {desc:<25} MISSING")
    print()

# ─── CLI ─────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "models":
            list_models(free_only="--free" in sys.argv, local_only="--local" in sys.argv)
        elif sys.argv[1] == "video-models":
            print("Video models:", video_list())
        elif sys.argv[1] == "video":
            model = "runway-gen3"
            duration = 5
            aspect = "16:9"
            args = sys.argv[2:]
            prompt_parts = []
            skip = False
            for a in args:
                if skip: skip = False; continue
                if a in ("--model", "--duration", "--aspect"): skip = True; continue
                prompt_parts.append(a)
            prompt = " ".join(prompt_parts)
            print(video(prompt, model=model, duration=duration, aspect=aspect) if prompt else "Usage: video 'prompt'")
        elif sys.argv[1] == "cost":
            cost_summary()
        elif sys.argv[1] == "stream":
            for chunk in stream(" ".join(sys.argv[2:])): print(chunk, end="", flush=True)
            print()
        elif sys.argv[1] == "env":
            from universal_model import env_validate
            env_validate()
        elif sys.argv[1] == "tr-test":
            tr_print("Istanbul'da saskin oksuruculer gulleri sever")
        elif sys.argv[1] == "fms-status":
            fms_status()
        elif sys.argv[1] == "fms-fix":
            print(fms_fix(sys.argv[2], " ".join(sys.argv[3:])))
        elif sys.argv[1] == "fms-code":
            print(fms_code(" ".join(sys.argv[2:])))
        elif sys.argv[1] == "fms-render":
            print(fms_render(" ".join(sys.argv[2:])))
        elif sys.argv[1] == "fms-publish":
            plats = sys.argv[2].split(",") if len(sys.argv) > 2 else None
            print(fms_publish(" ".join(sys.argv[3:] if len(sys.argv) > 3 else []), platforms=plats))
        elif sys.argv[1] in {"code", "debug", "arch", "review", "test"}:
            fn = {"code": code, "debug": debug, "arch": arch, "review": review, "test": test}[sys.argv[1]]
            print(fn(" ".join(sys.argv[2:]), tr=True))
        else:
            print(ask(" ".join(sys.argv[1:]), tr=True))
    else:
        print("Universal Model Connector (f&f / özgür-ünlü)")
        print("Usage:")
        print("  python -m universal_model 'soru'")
        print("  python -m universal_model code 'async retry'")
        print("  python -m universal_model models [--free] [--local]")
        print("  python -m universal_model --model f&f 'prompt'")
        print("  python -m universal_model cost")
        print("  python -m universal_model stream 'prompt'")
        print("  python -m universal_model env")
        print("  python -m universal_model fms-status")