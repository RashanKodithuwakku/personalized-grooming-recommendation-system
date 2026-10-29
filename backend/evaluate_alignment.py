
import cv2
import numpy as np


def evaluate_alignment(template_points, user_points):
    """
    Points must be corresponding landmarks in the same coordinate space.
    Use at least 4 landmarks:
      first 3 = affine fitting anchors
      remaining points = independent test landmarks
    """
    src = np.asarray(template_points, dtype=np.float32)
    dst = np.asarray(user_points, dtype=np.float32)

    if src.shape != dst.shape or src.ndim != 2 or src.shape[1] != 2:
        raise ValueError("Template and user points must have matching Nx2 shapes.")

    if len(src) < 4:
        raise ValueError("At least 4 corresponding landmarks are required.")

    # Fit transform using only 3 anchor landmarks
    matrix = cv2.getAffineTransform(src[:3], dst[:3])

    # Evaluate only on landmarks NOT used to fit the transform
    test_template = src[3:]
    test_user = dst[3:]

    baseline_pred = test_template.copy()  # fixed overlay
    affine_pred = cv2.transform(
        test_template.reshape(-1, 1, 2), matrix
    ).reshape(-1, 2)

    # Normalize by the distance between the first two user landmarks
    face_width = np.linalg.norm(dst[1] - dst[0])
    if face_width <= 1e-6:
        raise ValueError("Invalid face-width normalization.")

    baseline_errors = (
        np.linalg.norm(baseline_pred - test_user, axis=1)
        / face_width * 100
    )
    affine_errors = (
        np.linalg.norm(affine_pred - test_user, axis=1)
        / face_width * 100
    )

    return {
        "baseline_mean_nme_percent": float(np.mean(baseline_errors)),
        "baseline_median_nme_percent": float(np.median(baseline_errors)),
        "affine_mean_nme_percent": float(np.mean(affine_errors)),
        "affine_median_nme_percent": float(np.median(affine_errors)),
        "affine_matrix": matrix.tolist(),
    }
