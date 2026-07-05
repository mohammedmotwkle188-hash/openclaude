"""Rolling in-memory conversation window fed to the AI as context for the current session."""

from collections import deque
from typing import Deque, List

from core.brain import ChatTurn

MAX_TURNS = 40

_turns: Deque[ChatTurn] = deque(maxlen=MAX_TURNS)


def add(role: str, text: str) -> None:
    _turns.append(ChatTurn(role=role, text=text))


def get_turns() -> List[ChatTurn]:
    """Returns a shallow copy so callers can safely attach a transient image to the last turn."""
    return [ChatTurn(role=t.role, text=t.text, image=t.image) for t in _turns]


def clear() -> None:
    _turns.clear()
