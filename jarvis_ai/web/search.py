"""Internet search: opens a browser for Google/YouTube, plus a quick inline answer via
DuckDuckGo's keyless Instant Answer API for questions that don't need a full page."""

from typing import Optional

import requests

from tools.browser import search_web  # re-exported for convenience


def quick_answer(query: str) -> Optional[str]:
    res = requests.get(
        "https://api.duckduckgo.com/", params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1}, timeout=8
    )
    if not res.ok:
        return None
    data = res.json()
    return data.get("AbstractText") or data.get("Answer") or None
