"""Bounded, polling-friendly public financial jobs; source results arrive separately."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Lock
from time import monotonic

_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="official-financial")
_lock = Lock()
_jobs = {}


def _growth(symbol):
    from mops_history import fetch_mops_eps_history
    from auto_fundamentals import eps_growth
    rows, failures = fetch_mops_eps_history(symbol, years=3)
    return eps_growth(rows), failures


def _book(symbol, allow_alternative):
    from auto_fundamentals import fetch_book_value, fetch_alternative_book_value
    result, error = fetch_book_value(symbol)
    if result is None and allow_alternative:
        alternate, alternate_error = fetch_alternative_book_value(symbol)
        if alternate is not None:
            alternate["official_error"] = error
            return alternate, None
        error += "；" + (alternate_error or "替代來源不可用")
    return result, error


def start_job(symbol, allow_alternative=False, growth_loader=None, book_loader=None):
    key = (symbol, bool(allow_alternative))
    with _lock:
        existing = _jobs.get(key)
        if existing and not all(f.done() for f in existing["futures"].values()):
            return existing, None
        active = sum(not all(f.done() for f in j["futures"].values()) for j in _jobs.values())
        if active >= 2:
            return None, "財報來源忙碌中，請稍後再讀取；不會重複排入查詢。"
        for old in list(_jobs):
            j = _jobs[old]
            if all(f.done() for f in j["futures"].values()) and monotonic()-j["started"] > 3600:
                del _jobs[old]
        job = {"symbol": symbol, "started": monotonic(),
               "retrieved_at": datetime.now(timezone.utc).isoformat(),
               "futures": {"growth": _pool.submit(growth_loader or _growth, symbol),
                           "book": _pool.submit(book_loader or _book, symbol, allow_alternative)}}
        _jobs[key] = job
        return job, None


def poll_job(job):
    result = {"symbol": job["symbol"], "retrieved_at": job["retrieved_at"],
              "growth": {}, "book": None, "book_error": None,
              "history_failures": [], "pending": []}
    for name, future in job["futures"].items():
        if not future.done():
            result["pending"].append(name)
            continue
        try:
            value, details = future.result()
        except Exception:
            value, details = None, "財報來源暫時無法取得，請稍後重試。"
        if name == "growth":
            result["growth"] = value if value is not None else {"error": str(details)}
            result["history_failures"] = details if isinstance(details, list) else []
        else:
            result["book"], result["book_error"] = value, details
    return result
