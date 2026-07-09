"""Face detection + recognition via OpenCV (Haar cascade detector + LBPH recognizer).

Deliberately not using `face_recognition`/dlib — that needs a C++ toolchain and CMake to
build, which many users won't have set up. OpenCV's own LBPH recognizer is less accurate
but ships in `opencv-contrib-python` as a plain pip install with no compiler needed.
Enrolled face samples and the trained model live under ~/.jarvis_ai/faces/.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from config import APP_DIR

FACES_DIR = APP_DIR / "faces"
MODEL_FILE = FACES_DIR / "lbph_model.yml"
LABELS_FILE = FACES_DIR / "labels.json"

_cascade: Optional[cv2.CascadeClassifier] = None


def _detector() -> cv2.CascadeClassifier:
    global _cascade
    if _cascade is None:
        path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        _cascade = cv2.CascadeClassifier(path)
    return _cascade


def _grab_frame() -> np.ndarray:
    cam = cv2.VideoCapture(0)
    try:
        ok, frame = cam.read()
        if not ok:
            raise RuntimeError("Couldn't read from the webcam — is it in use by another app?")
        return frame
    finally:
        cam.release()


def detect_faces(frame: Optional[np.ndarray] = None) -> List[Tuple[int, int, int, int]]:
    """Returns a list of (x, y, w, h) boxes for every face found in the frame."""
    if frame is None:
        frame = _grab_frame()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    boxes = _detector().detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(60, 60))
    return [tuple(map(int, b)) for b in boxes]


def _load_labels() -> Dict[str, int]:
    if LABELS_FILE.exists():
        return json.loads(LABELS_FILE.read_text("utf-8"))
    return {}


def _save_labels(labels: Dict[str, int]) -> None:
    FACES_DIR.mkdir(parents=True, exist_ok=True)
    LABELS_FILE.write_text(json.dumps(labels), encoding="utf-8")


def enroll_face(name: str, samples: int = 20) -> str:
    """Captures several frames of whoever is in front of the webcam and trains/updates
    the recognizer to know them as `name`. Ask the person to move their head slightly
    between samples for a more robust model."""
    labels = _load_labels()
    label_id = labels.get(name, len(labels))
    labels[name] = label_id

    FACES_DIR.mkdir(parents=True, exist_ok=True)
    person_dir = FACES_DIR / name
    person_dir.mkdir(exist_ok=True)

    cam = cv2.VideoCapture(0)
    captured = 0
    try:
        while captured < samples:
            ok, frame = cam.read()
            if not ok:
                break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            boxes = _detector().detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(60, 60))
            if len(boxes) == 1:
                x, y, w, h = boxes[0]
                face = cv2.resize(gray[y : y + h, x : x + w], (200, 200))
                cv2.imwrite(str(person_dir / f"{captured}.png"), face)
                captured += 1
    finally:
        cam.release()

    if captured == 0:
        raise RuntimeError("Couldn't capture a clear face — make sure you're well-lit and facing the camera.")

    _save_labels(labels)
    _train(labels)
    return f"Learned {captured} samples of {name}'s face."


def _train(labels: Dict[str, int]) -> None:
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    images: List[np.ndarray] = []
    ids: List[int] = []
    for name, label_id in labels.items():
        person_dir = FACES_DIR / name
        if not person_dir.exists():
            continue
        for img_path in person_dir.glob("*.png"):
            img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
            if img is not None:
                images.append(img)
                ids.append(label_id)
    if not images:
        raise RuntimeError("No enrolled faces to train on yet.")
    recognizer.train(images, np.array(ids))
    recognizer.save(str(MODEL_FILE))


def recognize_face(confidence_threshold: float = 75.0) -> str:
    """Returns a friendly description of who (if anyone known) is in front of the camera.
    Lower LBPH distance = more confident; anything above the threshold is "unrecognized".
    """
    labels = _load_labels()
    if not labels or not MODEL_FILE.exists():
        raise RuntimeError("No faces enrolled yet — say \"learn my face as <name>\" first.")

    id_to_name = {v: k for k, v in labels.items()}
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(str(MODEL_FILE))

    frame = _grab_frame()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    boxes = _detector().detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(60, 60))
    if not boxes:
        return "I don't see anyone in front of the camera."

    results = []
    for x, y, w, h in boxes:
        face = cv2.resize(gray[y : y + h, x : x + w], (200, 200))
        label_id, distance = recognizer.predict(face)
        if distance <= confidence_threshold and label_id in id_to_name:
            results.append(id_to_name[label_id])
        else:
            results.append("someone I don't recognize")

    if len(results) == 1:
        return f"That looks like {results[0]}."
    return "I can see multiple people: " + ", ".join(results)
