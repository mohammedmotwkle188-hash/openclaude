"""Tells a joke — tries the keyless icanhazdadjoke API, falls back to a local list offline."""

import random

import requests

_LOCAL_JOKES = [
    "I would tell you a UDP joke, but you might not get it.",
    "There are only 10 kinds of people in the world: those who understand binary, and those who don't.",
    "I'm reading a book about anti-gravity. It's impossible to put down.",
    "Why do programmers prefer dark mode? Because light attracts bugs.",
    "A SQL query walks into a bar, goes up to two tables and asks: may I join you?",
    "I told my computer I needed a break, and now it won't stop sending me KitKat ads.",
]


def tell_joke() -> str:
    try:
        res = requests.get(
            "https://icanhazdadjoke.com/", headers={"Accept": "application/json", "User-Agent": "JarvisAI"}, timeout=6
        )
        if res.ok:
            joke = res.json().get("joke")
            if joke:
                return joke
    except requests.RequestException:
        pass
    return random.choice(_LOCAL_JOKES)
