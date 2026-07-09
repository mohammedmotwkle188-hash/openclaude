"""Plain-HTTP page fetch + text extraction — for "summarize this page" without needing a
full browser. For JS-rendered pages, use tools.browser.automate_fetch_text instead."""

import requests
from bs4 import BeautifulSoup


def fetch_page_text(url: str, max_chars: int = 8000) -> str:
    res = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0 (JarvisAI)"})
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = " ".join(soup.get_text(separator=" ").split())
    return text[:max_chars]
