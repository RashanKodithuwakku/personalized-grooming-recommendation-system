import json
import os

import numpy as np


BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIBRARY_PATH = os.path.join(BACKEND_DIR, "templates", "library.json")


def load_library(library_path=None):
    """Load template metadata using a stable path, independent of CWD."""
    path = library_path or LIBRARY_PATH
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Template library not found: {path}")

    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("Template library must be a JSON object.")
    return data


def select_variant(
    user_face_width,
    user_hair_density,
    style_prefix,
    gender,
    library_path=None
):
    """
    Select the closest available variant using image-derived user metrics.

    user_face_width and user_hair_density should be normalized values in [0, 1].
    These are visual proxies, not medical or strand-level measurements.
    """
    values = np.asarray(
        [user_face_width, user_hair_density],
        dtype=np.float32
    )
    if not np.isfinite(values).all():
        raise ValueError("User geometry measurements must be finite.")

    user_face_width = float(np.clip(values[0], 0.0, 1.0))
    user_hair_density = float(np.clip(values[1], 0.0, 1.0))

    library = load_library(library_path)

    candidates = {
        name: data
        for name, data in library.items()
        if name.startswith(style_prefix)
        and data.get("gender") == gender
        and "face_width_ratio" in data
        and "hair_density_score" in data
    }

    if not candidates:
        return None, None, None

    user_vec = np.asarray(
        [user_face_width, user_hair_density],
        dtype=np.float32
    )

    best_name = None
    best_data = None
    best_distance = float("inf")

    for name, data in candidates.items():
        try:
            template_vec = np.asarray(
                [
                    float(data["face_width_ratio"]),
                    float(data["hair_density_score"])
                ],
                dtype=np.float32
            )
        except (TypeError, ValueError):
            continue

        if not np.isfinite(template_vec).all():
            continue

        distance = float(np.linalg.norm(user_vec - template_vec))
        if distance < best_distance:
            best_distance = distance
            best_name = name
            best_data = data

    if best_name is None:
        return None, None, None

    return best_name, best_distance, best_data
