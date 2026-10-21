"""Merkezi config yükleyici — config.yaml + çevre değişkenleri + gizli dosyalar."""

import os
import json
from pathlib import Path
from typing import Any, Optional, List, Union

# Config dosyası yolu (repo kökünde)
_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"
_SECRETS_DIR = Path(__file__).parent.parent / ".secrets"

# Cache
_config_cache: Optional[dict] = None


def _load_config() -> dict:
    """config.yaml dosyasını yükle (cache'li)."""
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    if _CONFIG_PATH.is_file():
        try:
            import yaml
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                _config_cache = yaml.safe_load(f) or {}
        except Exception:
            _config_cache = {}
    else:
        _config_cache = {}
    return _config_cache


def get(key: str, default: Any = None) -> Any:
    """
    Config değerini al.
    
    Öncelik sırası:
    1. Çevre değişkeni (KEY büyük harf, nokta yerine alt çizgi: FPS -> FPS, GORSEL_DIL.AKTIF -> GORSEL_DIL_AKTIF)
    2. config.yaml dosyası (nokta ile iç içe: "GORSEL_DIL.AKTIF")
    3. default
    """
    # 1. Çevre değişkeni
    env_key = key.upper().replace(".", "_")
    if env_key in os.environ:
        val = os.environ[env_key]
        # Tip dönüşümü dene
        if val.lower() in ("true", "false"):
            return val.lower() == "true"
        try:
            if "." in val:
                return float(val)
            return int(val)
        except ValueError:
            return val

    # 2. config.yaml
    config = _load_config()
    keys = key.split(".")
    val = config
    for k in keys:
        if isinstance(val, dict) and k in val:
            val = val[k]
        else:
            return default
    return val


def get_secret(
    key: str,
    env_names: Optional[List[str]] = None,
    legacy_json: Optional[str] = None,
    legacy_key: Optional[str] = None,
    default: Any = None,
) -> Any:
    """
    Gizli değeri al (token, API key, vb.).
    
    Öncelik sırası:
    1. Çevre değişkenleri (env_names listesi)
    2. .secrets/ klasöründeki JSON dosyaları
    3. legacy_json dosyası (eski yapı için geriye uyumluluk)
    4. default
    """
    # GUARD (2026-10-08): env_names string gelirse HARF HARF iterate edilir ve
    # tek harfli bir env (`_` = python yolu gibi) YANLIS eslesir — notify.py'deki
    # `chat not found` ariza tam boyle oldu (chat_id yerine python yolu dondu).
    # Savunmaci normalizasyon: str -> [str]. Test: test_config_loader_env_guvenligi.py.
    if isinstance(env_names, str):
        env_names = [env_names]
    # 1. Cevre degiskenleri
    if env_names:
        for env in env_names:
            if env in os.environ:
                return os.environ[env]

    # 2. .secrets/ klasörü
    if _SECRETS_DIR.is_dir():
        for json_file in _SECRETS_DIR.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if key in data:
                    return data[key]
            except Exception:
                continue

    # 3. Legacy JSON dosyası
    if legacy_json:
        legacy_path = Path(__file__).parent.parent / legacy_json
        if legacy_path.is_file():
            try:
                with open(legacy_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if legacy_key and legacy_key in data:
                    return data[legacy_key]
                if key in data:
                    return data[key]
            except Exception:
                pass

    return default


def reload():
    """Config cache'i temizle (test/değişiklik sonrası)."""
    global _config_cache
    _config_cache = None