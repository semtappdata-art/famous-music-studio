"""JSON formatlı logger — yapılandırılmış loglama için."""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

_loggers: Dict[str, logging.Logger] = {}
_log_dir: Optional[Path] = None


def _get_log_dir() -> Path:
    global _log_dir
    if _log_dir is None:
        _log_dir = Path(__file__).parent.parent / "logs"
        _log_dir.mkdir(parents=True, exist_ok=True)
    return _log_dir


class JSONFormatter(logging.Formatter):
    """Log kayıtlarını JSON formatında biçimlendir."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Ekstra alanları ekle (record.__dict__'ten standart olmayanları)
        for key, value in record.__dict__.items():
            if key not in {
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "message", "msg", "pathname", "process", "processName",
                "relativeCreated", "thread", "threadName", "exc_info",
                "exc_text", "stack_info", "getMessage"
            }:
                try:
                    json.dumps(value)  # Serileştirilebilir mi?
                    log_obj[key] = value
                except (TypeError, ValueError):
                    log_obj[key] = str(value)
        
        # Exception info
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_obj, ensure_ascii=False)


def get_logger(name: str, level: int = logging.INFO, json_format: bool = False) -> logging.Logger:
    """
    Logger al (singleton pattern).
    
    Args:
        name: Logger adı
        level: Log seviyesi
        json_format: True ise JSON formatında dosyaya yaz
    """
    if name in _loggers:
        return _loggers[name]
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False  # Root logger'a gitmesin
    
    # Console handler (her zaman)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(console_handler)
    
    # File handler (JSON format opsiyonel)
    if json_format:
        log_file = _get_log_dir() / f"{name}.jsonl"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)
    
    _loggers[name] = logger
    return logger


def configure_root_logger(level: int = logging.INFO, json_format: bool = False):
    """Root logger'ı yapılandır (uygulama başlangıcında bir kez çağrılmalı)."""
    root = logging.getLogger()
    root.setLevel(level)
    
    # Mevcut handler'ları temizle
    for h in root.handlers[:]:
        root.removeHandler(h)
    
    # Console
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    root.addHandler(console)
    
    # JSON file
    if json_format:
        log_file = _get_log_dir() / "app.jsonl"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(JSONFormatter())
        root.addHandler(file_handler)