"""Keyless internet research — news, weather, web search, Wikipedia, Reddit.

Everything here uses free, public, no-signup sources so it works out of the box:
  - News:      BBC RSS feeds (world / football / technology / business), stdlib XML parsing
  - Weather:   Open-Meteo (geocoding + current conditions), no key
  - Wikipedia: the public MediaWiki API
  - Reddit:    reddit.com's public search JSON
  - Web:       DuckDuckGo's HTML endpoint (best-effort scrape; degrades gracefully)

Each function returns plain text for the Groq brain to summarise, or raises RuntimeError
with a short, friendly message. Deliberately requests-only — no heavy scraping libraries,
this must stay light on a 2.7 GB Chromebook.
"""

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from typing import Dict, List

import requests

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) JarvisAGI/2.2"}

NEWS_FEEDS: Dict[str, str] = {
    "top": "https://feeds.bbci.co.uk/news/rss.xml",
    "world": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "football": "https://feeds.bbci.co.uk/sport/football/rss.xml",
    "sport": "https://feeds.bbci.co.uk/sport/rss.xml",
    "technology": "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "finance": "https://feeds.bbci.co.uk/news/business/rss.xml",
}


def _strip_tags(text: str) -> str:
    cleaned = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    return re.sub(r"\s+", " ", cleaned).strip()


def fetch_rss(url: str, limit: int = 8) -> List[Dict[str, str]]:
    res = requests.get(url, headers=UA, timeout=12)
    res.raise_for_status()
    items = []
    for item in ET.fromstring(res.content).iter("item"):
        title = _strip_tags(item.findtext("title") or "")
        if not title:
            continue
        items.append({
            "title": title,
            "summary": _strip_tags(item.findtext("description") or ""),
            "url": (item.findtext("link") or "").strip(),
        })
        if len(items) >= limit:
            break
    return items


def news_digest(topic: str = "top") -> str:
    """Headlines + one-liners for a topic, as text for the brain to summarise."""
    feed = NEWS_FEEDS.get(topic, NEWS_FEEDS["top"])
    try:
        items = fetch_rss(feed)
    except requests.RequestException as err:
        raise RuntimeError("I couldn't reach the news feed — check the internet connection.") from err
    if not items:
        raise RuntimeError("The news feed came back empty. Try again in a minute.")
    return "\n".join(f"- {i['title']}. {i['summary']}" for i in items)


def news_headlines(limit: int = 6) -> List[Dict[str, str]]:
    """Keyless headlines for the HUD News widget (BBC top stories)."""
    items = fetch_rss(NEWS_FEEDS["top"], limit)
    return [
        {"id": str(n), "title": i["title"], "source": "BBC News", "url": i["url"] or "#"}
        for n, i in enumerate(items)
    ]


# --- weather (Open-Meteo, keyless) --------------------------------------------------------

_WMO_CODES = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "freezing fog", 51: "light drizzle", 53: "drizzle", 55: "heavy drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain", 66: "freezing rain", 67: "freezing rain",
    71: "light snow", 73: "snow", 75: "heavy snow", 77: "snow grains",
    80: "light showers", 81: "showers", 82: "heavy showers",
    85: "snow showers", 86: "snow showers", 95: "thunderstorm",
    96: "thunderstorm with hail", 99: "thunderstorm with hail",
}


def weather_now(location: str) -> Dict:
    """Current weather via Open-Meteo. Same shape as the OpenWeather-backed widget data."""
    place = (location or "London").split(",")[0].strip() or "London"
    try:
        geo = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": place, "count": 1, "language": "en"}, headers=UA, timeout=10,
        ).json()
        results = geo.get("results") or []
        if not results:
            raise RuntimeError(f'I couldn\'t find a place called "{place}".')
        spot = results[0]
        cur = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": spot["latitude"], "longitude": spot["longitude"],
                "current": "temperature_2m,relative_humidity_2m,weather_code",
            }, headers=UA, timeout=10,
        ).json()["current"]
    except requests.RequestException as err:
        raise RuntimeError("Weather service unreachable — check the internet connection.") from err
    return {
        "location": spot.get("name", place),
        "tempC": round(cur["temperature_2m"]),
        "condition": _WMO_CODES.get(cur.get("weather_code", -1), "unknown"),
        "humidityPercent": cur.get("relative_humidity_2m", 0),
    }


# --- wikipedia / reddit / web search ------------------------------------------------------

def wikipedia_summary(query: str) -> str:
    try:
        found = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={"action": "opensearch", "search": query, "limit": 1, "format": "json"},
            headers=UA, timeout=10,
        ).json()
        titles = found[1] if len(found) > 1 else []
        if not titles:
            raise RuntimeError(f'Wikipedia has nothing for "{query}".')
        page = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(titles[0])}",
            headers=UA, timeout=10,
        ).json()
    except requests.RequestException as err:
        raise RuntimeError("Wikipedia is unreachable — check the internet connection.") from err
    extract = page.get("extract")
    if not extract:
        raise RuntimeError(f'Wikipedia has nothing readable for "{query}".')
    return f"{page.get('title', titles[0])}: {extract}"


def reddit_digest(query: str) -> str:
    try:
        res = requests.get(
            "https://www.reddit.com/search.json",
            params={"q": query, "limit": 8, "sort": "relevance", "t": "week"},
            headers=UA, timeout=12,
        )
        res.raise_for_status()
        posts = res.json().get("data", {}).get("children", [])
    except requests.RequestException as err:
        raise RuntimeError("Reddit is unreachable right now (it sometimes blocks anonymous requests).") from err
    lines = [
        f"- r/{p['data'].get('subreddit')}: {p['data'].get('title')} "
        f"({p['data'].get('score', 0)} points, {p['data'].get('num_comments', 0)} comments)"
        for p in posts if p.get("data", {}).get("title")
    ]
    if not lines:
        raise RuntimeError(f'No Reddit discussions found for "{query}".')
    return "\n".join(lines)


def web_search(query: str) -> str:
    """Best-effort DuckDuckGo scrape; falls back to Wikipedia if the page shape changes."""
    try:
        res = requests.get(
            "https://html.duckduckgo.com/html/", params={"q": query}, headers=UA, timeout=12
        )
        res.raise_for_status()
        titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', res.text, re.S)
        snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', res.text, re.S)
        lines = []
        for i, title in enumerate(titles[:6]):
            snippet = _strip_tags(snippets[i]) if i < len(snippets) else ""
            lines.append(f"- {_strip_tags(title)}: {snippet}")
        if lines:
            return "\n".join(lines)
    except requests.RequestException:
        pass
    # Search page unreachable or reshaped -> encyclopedic fallback beats failing.
    return wikipedia_summary(query)
