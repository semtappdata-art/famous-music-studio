#!/usr/bin/env python3
"""
Famous Music Studio - Tüm Bağlantıları Kur ve Test Et
=====================================================
Bu script:
1. .env'deki eksik key'leri kontrol eder
2. Eksik key'leri interaktif doldurur
3. MCP server'ları başlatır
4. Tüm bağlantıları test eder
5. Pilot testi çalıştırır
"""

import os
import sys
import subprocess
import asyncio
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Renkli çıktı
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_status(msg, status="info"):
    colors = {"info": Colors.BLUE, "success": Colors.GREEN, "error": Colors.RED, "warning": Colors.YELLOW}
    print(f"{colors.get(status, Colors.RESET)}[{status.upper()}]{Colors.RESET} {msg}")

def print_header(title):
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{title.center(60)}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.RESET}\n")

# ============================================================
# KRİTİK ANAHTARLAR
# ============================================================

CRITICAL_KEYS = {
    "SUNO_API_KEY": {
        "desc": "Suno API Key",
        "url": "https://suno.ai/account/api-keys",
        "required": True,
        "placeholder": "sk-xxxxxxxxxxxxxxxx"
    },
    "SUNO_MCP_TOKEN": {
        "desc": "Suno MCP Token",
        "url": "https://acedata.cloud (Suno MCP Dashboard)",
        "required": True,
        "placeholder": "xxxx-xxxx-xxxx-xxxx"
    },
    "YOUTUBE_CLIENT_ID": {
        "desc": "YouTube OAuth Client ID",
        "url": "https://console.cloud.google.com/apis/credentials",
        "required": True,
        "placeholder": "xxx.apps.googleusercontent.com"
    },
    "YOUTUBE_CLIENT_SECRET": {
        "desc": "YouTube Client Secret",
        "url": "Google Cloud Console → OAuth 2.0 Client IDs",
        "required": True,
        "placeholder": "GOCSPX-xxxxxxxxxxxx"
    },
    "YOUTUBE_REDIRECT_URI": {
        "desc": "YouTube OAuth Redirect URI",
        "url": "Google Cloud Console → Authorized redirect URIs",
        "required": True,
        "placeholder": "http://localhost:3000/oauth2callback"
    },
    "DISTROKID_API_KEY": {
        "desc": "DistroKid API Key (Dağıtım için)",
        "url": "https://distrokid.com/settings/api",
        "required": True,
        "placeholder": "xxxxxxxxxxxx"
    },
}

OPTIONAL_KEYS = {
    "TIKTOK_CLIENT_KEY": ("TikTok Client Key", "https://developers.tiktok.com/"),
    "TIKTOK_CLIENT_SECRET": ("TikTok Client Secret", "https://developers.tiktok.com/"),
    "TIKTOK_ACCESS_TOKEN": ("TikTok Access Token", "https://developers.tiktok.com/"),
    "INSTAGRAM_APP_ID": ("Instagram App ID", "https://developers.facebook.com/apps/"),
    "INSTAGRAM_APP_SECRET": ("Instagram App Secret", "https://developers.facebook.com/apps/"),
    "INSTAGRAM_ACCESS_TOKEN": ("Instagram Access Token", "Meta Developer Portal"),
    "FACEBOOK_APP_ID": ("Facebook App ID", "https://developers.facebook.com/apps/"),
    "FACEBOOK_APP_SECRET": ("Facebook App Secret", ""),
    "FACEBOOK_ACCESS_TOKEN": ("Facebook Access Token", ""),
    "BLUESKY_HANDLE": ("Bluesky Handle", "bsky.app → Settings → App Passwords"),
    "BLUESKY_APP_PASSWORD": ("Bluesky App Password", "bsky.app → Settings → App Passwords"),
    "SPOTIFY_CLIENT_ID": ("Spotify Client ID", "https://developer.spotify.com/dashboard/"),
    "SPOTIFY_CLIENT_SECRET": ("Spotify Client Secret", ""),
    "SPOTIFY_CLIENT_SECRET": ("Spotify Client Secret", ""),
    "DISTROKID_API_KEY": ("DistroKid API Key", "https://distrokid.com/settings/api"),
    "GROQ_API_KEY": ("Groq API Key", "https://console.groq.com/keys"),
    "TOGETHER_API_KEY": ("Together AI API Key", "https://api.together.xyz/settings/api-keys"),
    "GOOGLE_API_KEY": ("Google AI Studio API Key", "https://aistudio.google.com/apikey"),
    "OPENAI_API_KEY": ("OpenAI API Key", "https://platform.openai.com/api-keys"),
    "RUNWAY_API_KEY": ("Runway API Key", "https://runwayml.com/"),
    "STABILITY_API_KEY": ("Stability AI API Key", "https://platform.stability.ai/"),
    "LUMA_API_KEY": ("Luma AI API Key", "https://lumalabs.ai/"),
    "MINIMAX_API_KEY": ("Minimax API Key", "https://minimax.chat/"),
    "HIGGSFIELD_API_KEY": ("Higgsfield AI Key", "https://higgsfield.ai/"),
    "PIKA_API_KEY": ("Pika API Key", "https://pika.art/"),
    "HAIPER_API_KEY": ("Haiper AI Key", "https://haiper.ai/"),
    "HF_API_KEY": ("Hugging Face API Key", "https://huggingface.co/settings/tokens"),
    "GROQ_API_KEY": ("Groq API Key", "https://console.groq.com/keys"),
    "TOGETHER_API_KEY": ("Together AI API Key", "https://api.together.xyz/settings/api-keys"),
    "OPENAI_API_KEY": ("OpenAI API Key", "https://platform.openai.com/api-keys"),
    "RUNWAY_API_KEY": ("Runway API Key", "https://runwayml.com/"),
    "STABILITY_API_KEY": ("Stability AI API Key", "https://platform.stability.ai/"),
    "LUMA_API_KEY": ("Luma AI API Key", "https://lumalabs.ai/"),
    "MINIMAX_API_KEY": ("Minimax API Key", "https://api.minimax.chat/"),
    "HIGGSFIELD_API_KEY": ("Higgsfield AI Key", "https://higgsfield.ai/"),
    "PIKA_API_KEY": ("Pika API Key", "https://pika.art/"),
    "HAIPER_API_KEY": ("Haiper AI Key", "https://haiper.ai/"),
    "HF_API_KEY": ("Hugging Face API Key", "https://huggingface.co/settings/tokens"),
}

def load_env():
    from dotenv import load_dotenv
    load_dotenv()

def check_critical_keys():
    """Kritik key'leri kontrol et"""
    load_dotenv()
    import os
    
    critical = {
        "SUNO_API_KEY": os.getenv("SUNO_API_KEY"),
        "SUNO_MCP_TOKEN": os.getenv("SUNO_MCP_TOKEN"),
        "SUNO_MCP_URL": os.getenv("SUNO_MCP_URL"),
        "YOUTUBE_CLIENT_ID": os.getenv("YOUTUBE_CLIENT_ID"),
        "YOUTUBE_CLIENT_SECRET": os.getenv("YOUTUBE_CLIENT_SECRET"),
        "YOUTUBE_REDIRECT_URI": os.getenv("YOUTUBE_REDIRECT_URI"),
        "DISTROKID_API_KEY": os.getenv("DISTROKID_API_KEY"),
    }
    
    missing = []
    ok = []
    for key, value in critical.items():
        if not value or value.startswith("your-") or value.startswith("your-") or value.startswith("xxx") or value.startswith("your-"):
            print(f"  {Colors.RED}❌ {key}: EKSİK/PLACEHOLDER{Colors.RESET}")
            if key in ["SUNO_API_KEY", "SUNO_MCP_TOKEN", "YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "DISTROKID_API_KEY"]:
                print(f"  {Colors.RED}  → KRİTİK: {critical[key].get('desc', '')} {Colors.RESET}")
        else:
            print(f"  {Colors.GREEN}✓ {key}: OK{Colors.RESET}")
            if key in ["SUNO_API_KEY", "SUNO_MCP_TOKEN", "YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "DISTROKID_API_KEY"]:
                print(f"  {Colors.GREEN}  → KRİTİK OK{Colors.RESET}")
    
    return all(v and not v.startswith("your-") and not v.startswith("xxx") and not v.startswith("your-") for v in critical.values())

def check_optional_keys():
    """Opsiyonel key'leri kontrol et"""
    load_dotenv()
    import os
    
    print(f"\n{Colors.CYAN}--- Opsiyonel Key'ler ---{Colors.RESET}")
    for key, (desc, url) in OPTIONAL_KEYS.items():
        val = os.getenv(key)
        status = "✅" if val and not val.startswith("your-") and not val.startswith("xxx") and not val.startswith("your-") else "❌"
        print(f"  {key}: {Colors.GREEN if val else Colors.RED}{'✅ SET' if val and not val.startswith('your-') else '❌ EKSİK'}{Colors.RESET}")

def interactive_fill():
    """Eksik kritik key'leri interaktif doldur"""
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    critical = {
        "SUNO_API_KEY": ("Suno API Key", "https://suno.ai/account/api-keys"),
        "SUNO_MCP_TOKEN": ("Suno MCP Token", "https://acedata.cloud (MCP Dashboard)"),
        "YOUTUBE_CLIENT_ID": ("YouTube Client ID", "Google Cloud Console → APIs & Services → Credentials"),
        "YOUTUBE_CLIENT_SECRET": ("YouTube Client Secret", "Google Cloud Console → OAuth 2.0 Client IDs"),
        "YOUTUBE_REDIRECT_URI": ("YouTube Redirect URI", "http://localhost:3000/oauth2callback"),
        "DISTROKID_API_KEY": ("DistroKid API Key", "https://distrokid.com/settings/api"),
    }
    
    updates = {}
    for key, (desc, url) in critical.items():
        val = os.getenv(key)
        if not val or val.startswith("your-") or val.startswith("xxx") or val.startswith("your-"):
            print(f"\n{Colors.YELLOW}⚠️  {key} eksik: {desc}{Colors.RESET}")
            print(f"  {Colors.CYAN}Kaynak: {Colors.CYAN}{Colors.BOLD}{url}{Colors.RESET}")
            value = input(f"  {Colors.CYAN}Değer girin (boş bırakırsa atlar): {Colors.RESET}").strip()
            if value:
                # .env dosyasını güncelle
                update_env_file(key, value)
                print(f"  {Colors.GREEN}✓ {key} güncellendi{Colors.RESET}")
            else:
                print(f"  {Colors.YELLOW}⚠ Atlandı{Colors.RESET}")

def update_env_file(key, value):
    """ .env dosyasını güncelle """
    env_path = Path(".env")
    lines = []
    with open(".env", "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    found = False
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}="):
            lines[i] = f"{key}={value}\n"
            found = True
            break
    
    if not found:
        lines.append(f"{key}={value}\n")
    
    with open(".env", "w", encoding="utf-8") as f:
        f.writelines(lines)

def start_mcp_servers():
    """MCP server'larını başlat"""
    print_status("MCP Server'lar başlatılıyor...")
    try:
        # start_mcp_servers.sh çalıştır
        result = subprocess.run(["./start_mcp_servers.sh"], capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print_status("MCP server'lar başlatıldı", "success")
            print(result.stdout)
            return True
        else:
            print_status(f"MCP başlatma hatası: {result.stderr}", "error")
            return False
    except subprocess.TimeoutExpired:
        print_status("MCP başlatma timeout", "error")
        return False
    except Exception as e:
        print_status(f"MCP başlatma hatası: {e}", "error")
        return False

def test_suno_connection():
    """Suno MCP bağlantısını test et"""
    print_status("Suno MCP bağlantısı test ediliyor...")
    try:
        from upload.mcp_suno import SunoMCPProvider
        provider = SunoMCPProvider()
        print(f"  Server URL: {provider._server_url}")
        print(f"  Token: {'SET' if provider._token else 'NOT SET'}")
        health = provider.health_check()
        print_status(f"Suno Health Check: {health}", "success" if health else "error")
        return health
    except Exception as e:
        print_status(f"Suno bağlantı hatası: {e}", "error")
        return False

def test_youtube_studio():
    print_status("YouTube Studio MCP test ediliyor...")
    try:
        from upload.mcp_yt_studio_read import YTStudioReadProvider
        p = YTStudioReadProvider()
        print(f"  Server URL: {getattr(p, '_server_url', 'NOT SET')}")
        print(f"  Token: {'SET' if hasattr(p, '_token') and p._token else 'NOT SET'}")
        return True
    except Exception as e:
        print_status(f"YouTube Studio MCP hatası: {e}", "error")
        return False

def test_postwire():
    print_status("PostWire MCP test ediliyor...")
    try:
        from upload.mcp_postwire import PostWireProvider
        from mcp_client import mcp_manager
        provider = PostWireProvider()
        print(f"  Server URL: {provider._server_url or 'NOT SET'}")
        print(f"  Token: {'SET' if hasattr(provider, '_token') and provider._token else 'NOT SET'}")
        health = provider.health_check()
        print_status(f"PostWire Health: {health}", "success" if health else "error")
        return health
    except Exception as e:
        print_status(f"PostWire hatası: {e}", "error")
        return False

def run_pilot_test():
    """Pilot test - 1 proje işle"""
    print_header("PİLOT TEST")
    print_status("Pilot test başlatılıyor: TR01_ArabeskTrap")
    
    # Önce render test
    print_status("Render test ediliyor...")
    result = subprocess.run([
        sys.executable, "render.py", "--project", "projects/TR01_ArabeskTrap"
    ], capture_output=True, text=True, timeout=300)
    
    if result.returncode == 0:
        print_status("Render başarılı", "success")
    else:
        print_status(f"Render hatası: {result.stderr[:500]}", "error")
        return False
    
    # Upload test (unlisted)
    print_status("Upload test ediliyor (unlisted)...")
    result = subprocess.run([
        sys.executable, "auto_process.py", 
        "--project", "projects/TR01_ArabeskTrap", 
        "--count", "1", 
        "--privacy", "unlisted"
    ], capture_output=True, text=True, timeout=600)
    
    if result.returncode == 0:
        print_status("Pilot test BAŞARILI!", "success")
        return True
    else:
        print_status(f"Pilot test hatası: {result.stderr[:500]}", "error")
        return False

def main():
    print_header("FAMOUS MUSIC STUDIO - FULL SETUP & TEST")
    
    # 1. .env kontrolü
    print_header("1. ENV KONTROLÜ")
    critical_ok = check_critical_keys()
    check_optional_keys()
    
    # 2. Eksik kritik key'leri sor
    if not check_critical_keys():
        print_status("KRİTİK anahtarlar eksik!", "error")
        print("\nLütfen eksik anahtarları girin:")
        fill_missing_keys()
        
        # .env'yi yeniden yükle
        from dotenv import load_dotenv
        load_dotenv(override=True)
    
    # 2. MCP Server'ları başlat
    print_header("2. MCP SERVER BAŞLATMA")
    if not start_mcp_servers():
        print_status("MCP server başlatma başarısız", "error")
        return False
    
    # 3. Bağlantıları test et
    print_header("3. BAĞLANTI TESTLERİ")
    suno_ok = test_suno_connection()
    yt_ok = test_youtube_studio()
    postwire_ok = test_postwire()
    
    # 4. Pilot test
    print_header("4. PILOT TEST")
    pilot_ok = run_pilot_test()
    
    # Özet
    print_header("ÖZET")
    print_status(f"Suno MCP: {'✅' if test_suno_connection() else '❌'}", "success" if test_suno_connection() else "error")
    print_status(f"YouTube Studio: {'✅' if test_youtube_studio() else '❌'}")
    print_status(f"PostWire: {'✅' if test_postwire() else '❌'}")
    
    if all([test_suno_connection(), test_youtube_studio()]):
        print_status("\n🎉 TÜM SİSTEMLER HAZIR!", "success")
        print_status("Tam otomasyon için: python auto_process.py --count 8", "info")
    else:
        print_status("\n⚠️  Bazı bağlantılar eksik, yukarıdaki hataları düzeltin", "warning")
    
    return True

if __name__ == "__main__":
    main()