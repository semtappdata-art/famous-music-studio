"""Suno MCP - Şarkı Üretim/İndirme Sağlayıcısı.

Bu modül `mcp__suno` üzerinden şarkı üretir ve `audio.wav` olarak indirir.
`watch_projects.py` klasör izleyicisinin yerini alabilir.

Özellikler:
- `mcp_client.SunoProvider` arayüzünü uygular
- Prompt'tan üretim → indirme tek akışta
- Metadata (şarkı adı, stil, vb.) döner
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_client import (
    SunoProvider,
    MCPError,
    MCPUnavailableError,
    MCPQuotaExceededError,
    _log,
)



def _mcp_servers_json(ad: str, vars_url: str, vars_tok: str):
    """mcp_servers.json + env birlesimi. Secret koda gomulmez."""
    url, tok = vars_url, vars_tok
    try:
        import json as _j
        kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        jf = os.path.join(kok, "mcp_servers.json")
        if os.path.isfile(jf):
            with open(jf, "r", encoding="utf-8") as f:
                cfg = _j.load(f).get("mcpServers", {}).get(ad, {})
            url = url or cfg.get("url", "")
            hdrs = cfg.get("headers", {}) or {}
            auth = hdrs.get("Authorization", "")
            if not tok and auth.startswith("Bearer "):
                tok = auth[len("Bearer "):]
    except Exception:
        pass
    return url, tok

class SunoMCPProvider(SunoProvider):
    """Suno MCP sunucusu üzerinden şarkı üretim/indirme."""

    def __init__(self):
        self._server_url, self._token = _mcp_servers_json("suno", os.getenv("SUNO_MCP_URL", "https://suno.mcp.acedata.cloud/mcp"), os.getenv("SUNO_MCP_TOKEN", os.getenv("SUNO_TOKEN", "")))

    def _call_mcp(self, tool: str, arguments: dict) -> Any:
        """MCP aracını çağırır."""
        try:
            import httpx

            headers = {
                "Content-Type": "application/json",
            }
            if self._token:
                headers["Authorization"] = f"Bearer {self._token}"

            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool,
                    "arguments": arguments
                }
            }

            timeout = 180.0  # şarkı üretimi uzun sürebilir

            with httpx.Client(timeout=timeout) as client:
                response = client.post(self._server_url, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()

            if "error" in result:
                error = result["error"]
                msg = error.get("message", "Bilinmeyen")
                if "quota" in msg.lower() or "rate limit" in msg.lower() or "credit" in msg.lower():
                    raise MCPQuotaExceededError("suno", msg)
                raise MCPError("suno", f"MCP hata: {msg}")

            return result.get("result", {})

        except httpx.TimeoutException:
            raise MCPUnavailableError("suno", "Zaman aşımı (şarkı üretimi)")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise MCPQuotaExceededError("suno", "Rate limit / kredi yetersiz")
            raise MCPUnavailableError("suno", f"HTTP {e.response.status_code}: {e}")
        except Exception as e:
            if isinstance(e, MCPError):
                raise
            raise MCPUnavailableError("suno", f"Bağlantı hatası: {e}")

    # ---- SunoProvider Arayüzü ----

    def generate_and_download(self, prompt: str, output_path: str,
                              meta: dict | None = None) -> dict:
        """Şarkı üretir, indirir, metadata döner.
        
        Args:
            prompt: Suno prompt'u (style, lyrics, vb.)
            output_path: Çıktı dosyası yolu (örn. "projects/yeni-sarki/audio.wav")
            meta: Ek metadata (theme, title, vb.) - MCP'ye iletilebilir
            
        Returns:
            {
                "audio_path": str,
                "title": str,
                "duration": float,
                "style": str,
                "lyrics": str,
                "meta": dict,  # Suno'dan dönen ham metadata
            }
        """
        # Çıktı dizinini oluştur
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        args = {
            "prompt": prompt,
            "output_path": output_path,
        }
        if meta:
            args["meta"] = meta

        result = self._call_mcp("generate_and_download", args)

        audio_path = result.get("audio_path") or result.get("file_path")
        if not audio_path or not os.path.isfile(audio_path):
            raise MCPError("suno", f"Ses dosyası üretilmedi: {result}")

        _log(f"Suno MCP: şarkı üretildi -> {audio_path}")

        return {
            "audio_path": audio_path,
            "title": result.get("title", ""),
            "duration": float(result.get("duration", 0) or 0),
            "style": result.get("style", ""),
            "lyrics": result.get("lyrics", ""),
            "meta": result.get("meta", {}),
        }

    def health_check(self) -> bool:
        """Suno MCP bağlantı sağlığı."""
        try:
            self._call_mcp("health_check", {})
            return True
        except Exception:
            return False


# ---- Yardımcı: Suno prompt hazırlama (suno_prompt_enhancer.py ile uyumlu) ----

def build_suno_prompt(meta: dict) -> str:
    """meta.json'dan Suno prompt'u üretir.
    
    `suno_prompt_enhancer.enhance_prompt` mantığıyla uyumlu.
    """
    from suno_prompt_enhancer import enhance_prompt
    return enhance_prompt(meta)


def generate_song_for_project(project_dir: str, meta: dict) -> dict:
    """Proje klasörü için şarkı üretir ve audio.wav yazar.
    
    `watch_projects.py` ve `yeni_parca_otomasyon.py` yerinde kullanılabilir.
    """
    from mcp_client import mcp_manager

    provider = mcp_manager.get_suno_provider()
    if provider is None:
        raise MCPError("suno", "Suno MCP etkin değil")

    output_path = os.path.join(project_dir, "audio.wav")
    prompt = build_suno_prompt(meta)

    result = provider.generate_and_download(prompt, output_path, meta)

    # meta.json'ı güncelle (Suno'dan dönen metadata ile)
    meta_path = os.path.join(project_dir, "meta.json")
    meta.update({
        "title": result.get("title") or meta.get("title"),
        "duration": result.get("duration"),
        "style": result.get("style"),
        "lyrics": result.get("lyrics"),
        "suno_meta": result.get("meta"),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    })
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return result


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Suno MCP test")
    parser.add_argument("--prompt", required=True, help="Suno prompt")
    parser.add_argument("--output", required=True, help="Çıktı dosyası (audio.wav)")
    parser.add_argument("--meta", help="JSON metadata")
    args = parser.parse_args()

    meta = json.loads(args.meta) if args.meta else {}
    provider = SunoMCPProvider()
    result = provider.generate_and_download(args.prompt, args.output, meta)
    print(f"Sonuç: {json.dumps(result, ensure_ascii=False, indent=2)}")