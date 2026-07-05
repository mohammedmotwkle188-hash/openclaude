"""Media playback control — delegates to the OS media-key layer in tools.system_control."""

from tools.system_control import media_control, open_app


def play() -> str:
    return media_control("play")


def pause() -> str:
    return media_control("pause")


def stop() -> str:
    return media_control("stop")


def next_track() -> str:
    return media_control("next")


def previous_track() -> str:
    return media_control("prev")


def open_spotify() -> str:
    return open_app("spotify")
