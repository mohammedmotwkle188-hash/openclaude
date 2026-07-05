"""Hand gesture recognition via MediaPipe Hands landmarks — a single-frame snapshot
classified with simple, explainable geometry rules (finger-extended heuristics) rather
than a trained gesture-classifier model, so it needs no extra downloads beyond MediaPipe
itself and is easy to extend with new gestures.
"""

from __future__ import annotations

from typing import List

import cv2
import mediapipe as mp

_FINGER_TIPS = [4, 8, 12, 16, 20]
_FINGER_MCPS = [2, 5, 9, 13, 17]  # base joints used to judge "extended" vs "curled"


def _grab_frame():
    cam = cv2.VideoCapture(0)
    try:
        ok, frame = cam.read()
        if not ok:
            raise RuntimeError("Couldn't read from the webcam — is it in use by another app?")
        return frame
    finally:
        cam.release()


def _fingers_extended(landmarks) -> List[bool]:
    extended = []
    # Thumb: compare x rather than y since it extends sideways, not upward.
    extended.append(abs(landmarks[4].x - landmarks[0].x) > abs(landmarks[3].x - landmarks[0].x))
    for tip, mcp in zip(_FINGER_TIPS[1:], _FINGER_MCPS[1:]):
        extended.append(landmarks[tip].y < landmarks[mcp].y)
    return extended


def _classify(extended: List[bool]) -> str:
    thumb, index, middle, ring, pinky = extended
    count = sum(extended)
    if count == 0:
        return "fist"
    if count == 5:
        return "open palm"
    if thumb and not any([index, middle, ring, pinky]):
        return "thumbs up"
    if index and middle and not any([thumb, ring, pinky]):
        return "peace sign"
    if index and not any([thumb, middle, ring, pinky]):
        return "pointing"
    return f"{count} finger{'s' if count != 1 else ''} raised"


def detect_gesture() -> str:
    frame = _grab_frame()
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    with mp.solutions.hands.Hands(static_image_mode=True, max_num_hands=2, min_detection_confidence=0.5) as hands:
        result = hands.process(rgb)

    if not result.multi_hand_landmarks:
        return "I don't see a hand in front of the camera."

    gestures = [_classify(_fingers_extended(h.landmark)) for h in result.multi_hand_landmarks]
    if len(gestures) == 1:
        return f"I see a {gestures[0]}."
    return "I see: " + ", ".join(gestures)
