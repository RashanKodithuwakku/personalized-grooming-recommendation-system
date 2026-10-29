"""Fixed-reference NME metrics calculated from fixed_user_landmarks.json only.
The JSON input is intentionally not modified by this module.
"""
import json
from pathlib import Path
import numpy as np


def _load_fixed_reference(backend_dir: Path) -> dict:
    candidates = (
        backend_dir / "app" / "fixed_user_landmarks.json",
        backend_dir / "fixed_user_landmarks.json",
    )
    for path in candidates:
        if path.is_file():
            with path.open("r", encoding="utf-8") as stream:
                return json.load(stream)
    raise FileNotFoundError(
        "fixed_user_landmarks.json not found. Put the existing file in backend/app/ "
        "or backend/."
    )


def _nme(predicted: np.ndarray, reference: np.ndarray, normalizer: float):
    distances = np.linalg.norm(predicted - reference, axis=1)
    value = float((100.0 / len(reference)) * np.sum(distances / normalizer))
    return value, distances


def calculate_fixed_alignment_metrics(*, gender: str, style_prefix: str, backend_dir: Path) -> dict:
    """Calculate baseline NME, affine NME and error reduction using the document formulas."""
    if gender not in {"male", "female"}:
        raise ValueError("gender must be 'male' or 'female'.")

    fixed = _load_fixed_reference(backend_dir)
    if fixed.get("gender") and fixed["gender"] != gender:
        raise ValueError(
            f"The fixed reference JSON is for gender={fixed['gender']!r}, not {gender!r}."
        )

    coordinates = fixed.get("landmark_coordinates", {})
    reference = np.asarray(coordinates.get("reference_landmarks_p_i"), dtype=np.float64)
    baseline_predicted = np.asarray(coordinates.get("draft_predicted_landmarks_p_hat_i"), dtype=np.float64)
    affine_predicted = np.asarray(coordinates.get("affine_predicted_landmarks_p_hat_i"), dtype=np.float64)

    for label, points in (
        ("reference_landmarks_p_i", reference),
        ("draft_predicted_landmarks_p_hat_i", baseline_predicted),
        ("affine_predicted_landmarks_p_hat_i", affine_predicted),
    ):
        if points.shape != (3, 2) or not np.isfinite(points).all():
            raise ValueError(
                f"fixed_user_landmarks.json landmark_coordinates.{label} must contain 3 finite [x, y] points."
            )

    interocular = fixed.get("interocular_calculation", {})
    eye_points_data = interocular.get("eye_corner_landmarks", {})
    left_eye = np.asarray(eye_points_data.get("left_eye_outer_corner"), dtype=np.float64)
    right_eye = np.asarray(eye_points_data.get("right_eye_outer_corner"), dtype=np.float64)
    if left_eye.shape != (2,) or right_eye.shape != (2,) or not np.isfinite(left_eye).all() or not np.isfinite(right_eye).all():
        raise ValueError("Both outer eye-corner coordinates must be present in fixed_user_landmarks.json.")

    # Use the coordinates to compute d, rather than trusting a possibly stale stored number.
    normalizer = float(np.linalg.norm(right_eye - left_eye))
    if normalizer <= 1e-9:
        raise ValueError("Inter-ocular distance must be greater than zero.")

    baseline_nme, baseline_distances = _nme(baseline_predicted, reference, normalizer)
    affine_nme, affine_distances = _nme(affine_predicted, reference, normalizer)
    reduction = ((baseline_nme - affine_nme) / baseline_nme * 100.0) if baseline_nme > 1e-12 else 0.0

    prefix = style_prefix or fixed.get("style_prefix", "")
    return {
        "status": "completed",
        "reference_id": fixed.get("reference_id", "fixed_reference_user"),
        "fixed_reference": True,
        "selected_template": prefix,
        "style_prefix": prefix,
        "gender": gender,
        "landmarks_order": fixed.get("landmarks_order", []),
        "user_landmarks": reference.tolist(),
        "baseline_predicted_landmarks": baseline_predicted.tolist(),
        "affine_predicted_landmarks": affine_predicted.tolist(),
        "normalizer_name": "inter-ocular distance (outer left-eye corner to outer right-eye corner)",
        "normalizer_px": round(normalizer, 6),
        "eye_corner_landmarks": [left_eye.tolist(), right_eye.tolist()],
        "formulas": {
            "nme": "NME(%) = (100 / N) * sum(||p_hat_i - p_i||_2 / d_interocular)",
            "error_reduction": "Error Reduction(%) = ((NME_baseline - NME_affine) / NME_baseline) * 100",
        },
        "accuracy_metrics": {
            "baseline_mean_nme_percent": round(baseline_nme, 4),
            "affine_mean_nme_percent": round(affine_nme, 4),
            "error_reduction_percent": round(reduction, 4),
            "baseline_landmark_distances_px": baseline_distances.round(4).tolist(),
            "affine_landmark_distances_px": affine_distances.round(4).tolist(),
            "number_of_landmarks_N": int(len(reference)),
        },
        "accuracy_note": (
            "Values are calculated from the fixed reference JSON using the same three reference landmarks "
            "and the same inter-ocular normalizer for baseline and affine NME. They are fixed demonstration "
            "data, not recalculated from the currently uploaded photo and not independent validation of real-world accuracy."
        ),
    }
