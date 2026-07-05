"""Browser open/search helpers, plus optional Playwright-driven automation for anything
beyond "open this URL" (loading a page, reading its content, clicking through it)."""

import urllib.parse
import webbrowser


def open_url(url: str) -> str:
    webbrowser.open(url)
    return f"Opened {url}"


def search_web(engine: str, query: str) -> str:
    if engine == "google":
        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
    else:
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
    webbrowser.open(url)
    return f'Searching {engine} for "{query}".'


def automate_fetch_text(url: str, timeout_ms: int = 15000) -> str:
    """Loads a page in a real (headless) browser via Playwright and returns its visible text.

    Heavier than tools/browser fetches via requests+BeautifulSoup (web/scraper.py) but
    handles JS-rendered pages those can't. Requires `playwright install chromium` once.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url, timeout=timeout_ms)
        text = page.inner_text("body")
        browser.close()
        return text
