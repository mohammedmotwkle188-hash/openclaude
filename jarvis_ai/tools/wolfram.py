"""STEM / computational questions via the Wolfram Alpha Short Answers API.

Needs a free App ID from https://developer.wolframalpha.com/ (the "Short Answers API"
is free for non-commercial use). Store it in Settings as the `wolfram` API key.
"""

import urllib.parse

import requests

import config


def ask_wolfram(query: str) -> str:
    app_id = config.get_api_key("wolfram")
    if not app_id:
        raise RuntimeError("Add a Wolfram Alpha App ID in Settings to answer computational questions.")
    url = "https://api.wolframalpha.com/v1/result?" + urllib.parse.urlencode({"appid": app_id, "i": query})
    res = requests.get(url, timeout=15)
    if res.status_code == 501:
        # Wolfram returns 501 specifically when it can't interpret the query.
        raise RuntimeError(f'Wolfram Alpha couldn\'t make sense of "{query}".')
    if not res.ok:
        raise RuntimeError(f"Wolfram Alpha request failed ({res.status_code}).")
    return res.text.strip()
