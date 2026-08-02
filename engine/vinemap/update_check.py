"""Optional version check — single anonymous GET, documented in docs/MOAT.md."""

import json
import os
import time
import urllib.error
import urllib.request
from typing import Optional

from vinemap import __version__

PYPI_JSON = "https://pypi.org/pypi/vinemap/json"
CHECK_ENV = "VINEMAP_SKIP_UPDATE_CHECK"
CACHE_PATH = os.path.expanduser("~/.vinemap/last_update_check.json")
CHECK_INTERVAL_SECONDS = 24 * 3600


def check_for_update(timeout: float = 2.0) -> Optional[str]:
    """Return latest PyPI version if newer than installed, else None."""
    if os.environ.get(CHECK_ENV):
        return None
    try:
        with urllib.request.urlopen(PYPI_JSON, timeout=timeout) as resp:
            data = json.load(resp)
        latest = data["info"]["version"]
    except (urllib.error.URLError, OSError, KeyError, json.JSONDecodeError):
        return None
    if latest and latest != __version__:
        return latest
    return None


def maybe_notify_update() -> None:
    """Print a one-line update hint at most once per day (stderr)."""
    if os.environ.get(CHECK_ENV):
        return
    now = time.time()
    try:
        if os.path.isfile(CACHE_PATH):
            with open(CACHE_PATH, encoding="utf-8") as f:
                cached = json.load(f)
            if now - float(cached.get("ts", 0)) < CHECK_INTERVAL_SECONDS:
                return
    except (json.JSONDecodeError, OSError, TypeError, ValueError):
        pass

    latest = check_for_update()
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    try:
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump({"ts": now, "latest": latest}, f)
    except OSError:
        pass

    if latest:
        import sys

        print(
            f"note: vinemap {latest} available (you have {__version__}) — "
            "pip install -U vinemap  or  vinemap --update",
            file=sys.stderr,
        )
