"""Çağrı koruyucusu — hata yakalama, loglama, yeniden deneme dekoratörü."""

import functools
import logging
import time
from typing import Any, Callable, Optional, TypeVar, ParamSpec

P = ParamSpec("P")
R = TypeVar("R")

logger = logging.getLogger(__name__)


def guarded_call(
    fn: Optional[Callable[P, R]] = None,
    *,
    max_retries: int = 0,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None,
    on_failure: Optional[Callable[[Exception], None]] = None,
    log_args: bool = False,
    log_result: bool = False,
) -> Callable[P, R]:
    """
    Fonksiyonu hata yakalama ve yeniden deneme ile sarmala.
    
    Kullanım:
        @guarded_call(max_retries=3, base_delay=1.0)
        def api_call():
            ...
        
        # veya dekoratörsüz:
        result = guarded_call(lambda: api_call(), max_retries=3)
    """
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            last_exc = None
            for attempt in range(max_retries + 1):
                try:
                    if log_args:
                        logger.debug("Calling %s args=%s kwargs=%s", func.__name__, args, kwargs)
                    result = func(*args, **kwargs)
                    if log_result:
                        logger.debug("%s returned %s", func.__name__, result)
                    return result
                except exceptions as exc:
                    last_exc = exc
                    if attempt < max_retries:
                        delay = min(base_delay * (exponential_base ** attempt), max_delay)
                        logger.warning(
                            "%s attempt %d/%d failed: %s. Retrying in %.1fs",
                            func.__name__, attempt + 1, max_retries + 1, exc, delay
                        )
                        if on_retry:
                            on_retry(exc, attempt)
                        time.sleep(delay)
                    else:
                        logger.error(
                            "%s failed after %d attempts: %s",
                            func.__name__, max_retries + 1, exc
                        )
                        if on_failure:
                            on_failure(exc)
                        raise
            # Should not reach here
            raise last_exc  # type: ignore
        return wrapper

    if fn is None:
        return decorator
    return decorator(fn)


def safe_call(
    fn: Callable[P, R],
    *args: P.args,
    default: Any = None,
    log_error: bool = True,
    **kwargs: P.kwargs,
) -> Any:
    """
    Fonksiyonu güvenle çağır, hata olursa default dön.
    
    Kullanım:
        result = safe_call(risky_function, arg1, arg2, default="fallback")
    """
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        if log_error:
            logger.exception("safe_call: %s failed: %s", fn.__name__, exc)
        return default