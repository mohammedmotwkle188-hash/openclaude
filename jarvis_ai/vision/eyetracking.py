"""Eye state (open/closed) and rough gaze direction via MediaPipe FaceMesh's iris
landmarks. This is a single-frame heuristic, not calibrated screen-coordinate gaze
tracking — it reports "looking left/center/right" relative to the camera, not where on
a monitor someone is looking. Calibrated gaze-to-screen tracking needs a per-user
calibration step this voice-command interface isn't set up to run.
"""

from __future__ import annotations

import cv2
import mediapipe as mp

# Six-point eye contours in the classic EAR (eye-aspect-ratio) order, mapped onto
# MediaPipe's 468-point face mesh indices — the same indices widely used in
# MediaPipe-based blink-detection references.
_LEFT_EYE = [362, 385, 387, 263, 373, 380]
_RIGHT_EYE = [33, 160, 158, 133, 153, 144]
_LEFT_IRIS_CENTER = 468
_RIGHT_IRIS_CENTER = 473
_BLINK_EAR_THRESHOLD = 0.21


def _grab_frame():
    cam = cv2.VideoCapture(0)
    try:
        ok, frame = cam.read()
        if not ok:
            raise RuntimeError("Couldn't read from the webcam — is it in use by another app?")
        return frame
    finally:
        cam.release()


def _dist(a, b) -> float:
    return ((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** 0.5


def _eye_aspect_ratio(pts) -> float:
    vertical1 = _dist(pts[1], pts[5])
    vertical2 = _dist(pts[2], pts[4])
    horizontal = _dist(pts[0], pts[3])
    if horizontal == 0:
        return 0.0
    return (vertical1 + vertical2) / (2.0 * horizontal)


def _gaze_direction(landmarks, iris_idx: int, outer_idx: int, inner_idx: int) -> str:
    iris_x = landmarks[iris_idx].x
    outer_x, inner_x = landmarks[outer_idx].x, landmarks[inner_idx].x
    span = inner_x - outer_x
    if span == 0:
        return "center"
    position = (iris_x - outer_x) / span
    if position < 0.35:
        return "right"
    if position > 0.65:
        return "left"
    return "center"


def check_eyes() -> str:
    frame = _grab_frame()
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    with mp.solutions.face_mesh.FaceMesh(
        static_image_mode=True, max_num_faces=1, refine_landmarks=True, min_detection_confidence=0.5
    ) as face_mesh:
        result = face_mesh.process(rgb)

    if not result.multi_face_landmarks:
        return "I don't see a face in front of the camera."

    landmarks = result.multi_face_landmarks[0].landmark
    left_ear = _eye_aspect_ratio([landmarks[i] for i in _LEFT_EYE])
    right_ear = _eye_aspect_ratio([landmarks[i] for i in _RIGHT_EYE])
    avg_ear = (left_ear + right_ear) / 2

    if avg_ear < _BLINK_EAR_THRESHOLD:
        return "Your eyes look closed."

    gaze = _gaze_direction(landmarks, _RIGHT_IRIS_CENTER, 33, 133)
    return f"Your eyes are open, looking roughly {gaze}."
