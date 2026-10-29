"""Face landmark detection for the three points used by the hair-fitting pipeline.

Preferred backend: MediaPipe Face Mesh. If it is not installed, a clearly marked
OpenCV Haar-cascade approximation is used so the rest of the pipeline can be
smoke-tested. The fallback is not a true landmark detector and may fit poorly.
"""
from pathlib import Path
import cv2
import numpy as np
from app.config import STANDARD_SIZE

# Face Mesh contour anchors: left cheek/jaw, right cheek/jaw, upper forehead.
_MEDIAPIPE_INDICES = (234, 454, 10)


def _mediapipe_points(image_rgb):
    try:
        import mediapipe as mp
    except ImportError:
        return None
    height, width = image_rgb.shape[:2]
    with mp.solutions.face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
    ) as mesh:
        result = mesh.process(image_rgb)
    if not result.multi_face_landmarks:
        return None
    landmarks = result.multi_face_landmarks[0].landmark
    points = []
    for index in _MEDIAPIPE_INDICES:
        point = landmarks[index]
        points.append([float(point.x * width), float(point.y * height)])
    return np.asarray(points, dtype=np.float32)


def _haar_approximation(image_bgr):
    """Return approximate anchors from a face box; used only if MediaPipe absent."""
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
    detector = cv2.CascadeClassifier(str(cascade_path))
    faces = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
    if len(faces) == 0:
        return None
    x, y, w, h = max(faces, key=lambda box: int(box[2]) * int(box[3]))
    # These are geometric estimates, not detected facial landmarks.
    return np.asarray([
        [x + 0.12 * w, y + 0.76 * h],
        [x + 0.88 * w, y + 0.76 * h],
        [x + 0.50 * w, y + 0.18 * h],
    ], dtype=np.float32)


def get_user_landmarks(image_path):
    """Return [[left jaw], [right jaw], [upper forehead]] in source-image pixels."""
    image = cv2.imread(str(image_path))
    if image is None:
        raise FileNotFoundError(f"Could not read image for landmark detection: {image_path}")
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    points = _mediapipe_points(rgb)
    if points is None:
        points = _haar_approximation(image)
    if points is None:
        return None
    if points.shape != (3, 2) or not np.isfinite(points).all():
        raise ValueError("Landmark detector returned invalid coordinates.")
    # main_flow resizes images to STANDARD_SIZE before using these coordinates.
    source_h, source_w = image.shape[:2]
    target_w, target_h = STANDARD_SIZE
    points[:, 0] *= target_w / float(source_w)
    points[:, 1] *= target_h / float(source_h)
    return points.tolist()
