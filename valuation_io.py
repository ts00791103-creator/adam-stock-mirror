"""Bound optional valuation I/O; keep timed-out work from multiplying."""
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from threading import Lock

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="valuation")
_pending = {}
_lock = Lock()


def bounded_fetch(key, loader, timeout_seconds=12):
    with _lock:
        future = _pending.get(key)
        if future is None:
            for old_key in list(_pending):
                if _pending[old_key].done():
                    del _pending[old_key]
            if len(_pending) >= 2:
                return None, "估價資料來源仍忙碌，請稍後重試；一般個股分析仍可使用"
            future = _executor.submit(loader)
            _pending[key] = future
    try:
        result = future.result(timeout=timeout_seconds)
    except TimeoutError:
        return None, "估價資料讀取超時，請稍後再按讀取；一般個股分析仍可使用"
    except Exception:
        return None, "估價來源暫時不可用，請稍後重試"
    else:
        return result
    finally:
        if future.done():
            with _lock:
                if _pending.get(key) is future:
                    del _pending[key]
