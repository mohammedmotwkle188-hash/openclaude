"""YouTube open/search — playback stays in the real browser; this deliberately doesn't
download video/audio (that treads into ToS territory and wasn't asked for)."""

from tools.browser import open_url, search_web


def open_youtube() -> str:
    return open_url("https://youtube.com")


def search(query: str) -> str:
    return search_web("youtube", query)
