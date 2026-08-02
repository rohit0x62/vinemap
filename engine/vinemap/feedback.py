"""Opt-in feedback prompt and issue helper."""

import json
import os
import sys
import webbrowser
from typing import Optional
from urllib.parse import quote

FEEDBACK_DIR = os.path.expanduser("~/.vinemap")
PROMPTED_FILE = os.path.join(FEEDBACK_DIR, "feedback_prompted.json")
ISSUES_URL = "https://github.com/rohit0x62/vinemap/issues/new/choose"


def _load_prompted() -> dict:
    if not os.path.isfile(PROMPTED_FILE):
        return {}
    try:
        with open(PROMPTED_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_prompted(data: dict) -> None:
    os.makedirs(FEEDBACK_DIR, exist_ok=True)
    with open(PROMPTED_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)


def maybe_prompt_feedback(*, context: str = "quickstart") -> None:
    """One-time interactive prompt after successful setup (TTY only)."""
    if not sys.stdin.isatty():
        return
    data = _load_prompted()
    if data.get("prompted"):
        return
    print("\n--- Feedback (optional, one-time) ---")
    print("How was setup? (1=great  2=ok  3=issues  Enter=skip)")
    choice = input("> ").strip()
    data["prompted"] = True
    data["context"] = context
    if choice == "3":
        data["rating"] = "issues"
        print(f"Sorry it was rough — open an issue: {ISSUES_URL}")
    elif choice in ("1", "2"):
        data["rating"] = "great" if choice == "1" else "ok"
        msg = input("Anything we should know? (Enter to skip): ").strip()
        if msg:
            data["note"] = msg[:500]
            print("Thanks — use `vinemap feedback \"...\"` anytime to send more.")
    _save_prompted(data)


def open_feedback(message: Optional[str] = None, *, open_browser: bool = True) -> str:
    """Return GitHub issue URL; optionally open browser."""
    if message:
        body = quote(f"**Feedback via vinemap CLI**\n\n{message.strip()[:2000]}")
        url = f"https://github.com/rohit0x62/vinemap/issues/new?labels=feedback&body={body}"
    else:
        url = ISSUES_URL
    if open_browser:
        try:
            webbrowser.open(url)
        except OSError:
            pass
    return url
