"""Weather / news / stocks / crypto — same providers as the Electron build's webdata.ts."""

from typing import Dict, List, Optional

import requests

import config


def fetch_weather(location: Optional[str] = None) -> Dict:
    loc = (location or "").strip() or config.get_settings()["weatherLocation"]
    api_key = config.get_api_key("openweather")
    if not api_key:
        raise RuntimeError("Add an OpenWeather API key in Settings to enable live weather.")
    res = requests.get(
        "https://api.openweathermap.org/data/2.5/weather",
        params={"q": loc, "units": "metric", "appid": api_key},
        timeout=10,
    )
    if not res.ok:
        raise RuntimeError(f'Weather lookup failed ({res.status_code}) for "{loc}".')
    data = res.json()
    return {
        "location": data.get("name", loc),
        "tempC": round(data.get("main", {}).get("temp", 0)),
        "condition": (data.get("weather") or [{}])[0].get("description", "unknown"),
        "humidityPercent": data.get("main", {}).get("humidity", 0),
    }


def fetch_news() -> List[Dict]:
    api_key = config.get_api_key("newsapi")
    if not api_key:
        raise RuntimeError("Add a NewsAPI key in Settings to enable live headlines.")
    res = requests.get(
        "https://newsapi.org/v2/top-headlines",
        params={"language": "en", "pageSize": 8, "apiKey": api_key},
        timeout=10,
    )
    if not res.ok:
        raise RuntimeError(f"News lookup failed ({res.status_code}).")
    articles = res.json().get("articles", [])
    return [
        {"id": str(i), "title": a.get("title"), "source": (a.get("source") or {}).get("name", "unknown"), "url": a.get("url")}
        for i, a in enumerate(articles)
    ]


def fetch_stock_quote(symbol: str) -> str:
    res = requests.get("https://stooq.com/q/l/", params={"s": symbol, "f": "sd2t2ohlcv", "h": "", "e": "csv"}, timeout=10)
    if not res.ok:
        raise RuntimeError("Stock lookup failed.")
    lines = res.text.strip().split("\n")
    if len(lines) < 2:
        raise RuntimeError(f'No quote found for "{symbol}".')
    cols = lines[1].split(",")
    close = cols[6] if len(cols) > 6 else "N/D"
    if close == "N/D":
        raise RuntimeError(f'No quote found for "{symbol}".')
    return f"{symbol.upper()}: {close}"


def fetch_crypto_price(symbol: str) -> str:
    coin_id = symbol.lower()
    res = requests.get(
        "https://api.coingecko.com/api/v3/simple/price", params={"ids": coin_id, "vs_currencies": "usd"}, timeout=10
    )
    if not res.ok:
        raise RuntimeError("Crypto lookup failed.")
    data = res.json()
    price = data.get(coin_id, {}).get("usd")
    if price is None:
        raise RuntimeError(f'No price found for "{symbol}". Try the full CoinGecko id (e.g. "bitcoin").')
    return f"{symbol.upper()}: ${price:,}"
