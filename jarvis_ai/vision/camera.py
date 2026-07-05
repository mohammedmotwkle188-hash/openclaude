"""Webcam access: open the OS camera app, or grab a still frame directly via OpenCV."""

from tools.system_control import open_app


def open_camera() -> str:
    return open_app("camera")


def capture_photo(save_path: str) -> str:
    """Grabs a single frame from the default webcam. Requires opencv-python."""
    import cv2

    cam = cv2.VideoCapture(0)
    try:
        ok, frame = cam.read()
        if not ok:
            raise RuntimeError("Couldn't read from the webcam — is it in use by another app?")
        cv2.imwrite(save_path, frame)
        return f"Saved photo to {save_path}"
    finally:
        cam.release()
