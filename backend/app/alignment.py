import cv2
import numpy as np

from app.config import STANDARD_SIZE


def _validate_points(points, name):
    """Validate and return exactly three 2D landmark points."""
    try:
        points_array = np.asarray(points, dtype=np.float32)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must contain numeric 2D points.") from exc

    if points_array.shape != (3, 2):
        raise ValueError(
            f"{name} must have shape (3, 2); received {points_array.shape}."
        )

    if not np.isfinite(points_array).all():
        raise ValueError(f"{name} contains invalid or non-finite coordinates.")

    return points_array


def align_variant(template_img, template_points, user_points):
    """
    Resize and affine-align a template image to the user's landmarks.

    Landmark order must match in both lists:
        1. Left-side face/jaw point
        2. Right-side face/jaw point
        3. Upper-face point

    Important:
        This aligns the whole template image using three points. It does not
        independently align the hairline. For accurate hairstyle placement,
        the template library needs a separately annotated hairline point or
        hairline landmarks, and the hair layer should be warped separately.

    Args:
        template_img: OpenCV BGR image.
        template_points: Three template landmarks in STANDARD_SIZE coordinates.
        user_points: Three user landmarks in STANDARD_SIZE coordinates.

    Returns:
        warped: Aligned BGR template with STANDARD_SIZE dimensions.
        matrix: 2x3 affine transformation matrix.
    """
    if template_img is None:
        raise ValueError("Template image could not be loaded.")

    if not isinstance(template_img, np.ndarray) or template_img.size == 0:
        raise ValueError("Template image is empty or invalid.")

    src = _validate_points(template_points, "template_points")
    dst = _validate_points(user_points, "user_points")

    # STANDARD_SIZE is (width, height). Points stored in library.json must
    # correspond to the template after this resize.
    target_width, target_height = STANDARD_SIZE
    if target_width <= 0 or target_height <= 0:
        raise ValueError(f"Invalid STANDARD_SIZE: {STANDARD_SIZE}")

    template_img = cv2.resize(
        template_img,
        (target_width, target_height),
        interpolation=cv2.INTER_AREA
    )

    # Reject nearly-collinear points: they produce unstable affine matrices.
    src_area = abs(
        (src[1, 0] - src[0, 0]) * (src[2, 1] - src[0, 1])
        - (src[2, 0] - src[0, 0]) * (src[1, 1] - src[0, 1])
    )
    dst_area = abs(
        (dst[1, 0] - dst[0, 0]) * (dst[2, 1] - dst[0, 1])
        - (dst[2, 0] - dst[0, 0]) * (dst[1, 1] - dst[0, 1])
    )

    if src_area < 1.0 or dst_area < 1.0:
        raise ValueError(
            "Alignment landmarks are too close together or nearly collinear."
        )

    matrix = cv2.getAffineTransform(src, dst)

    if not np.isfinite(matrix).all():
        raise ValueError("Could not calculate a valid affine transformation.")

    warped = cv2.warpAffine(
        template_img,
        matrix,
        (target_width, target_height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0)
    )

    return warped, matrix


def transform_points(points, matrix):
    """Apply a 2x3 affine transformation to one or more 2D points."""
    if matrix is None:
        raise ValueError("Transformation matrix is missing.")

    matrix = np.asarray(matrix, dtype=np.float32)
    if matrix.shape != (2, 3) or not np.isfinite(matrix).all():
        raise ValueError("matrix must be a finite 2x3 affine matrix.")

    try:
        points_array = np.asarray(points, dtype=np.float32)
    except (TypeError, ValueError) as exc:
        raise ValueError("points must contain numeric 2D coordinates.") from exc

    if points_array.size == 0:
        return []

    if points_array.ndim != 2 or points_array.shape[1] != 2:
        raise ValueError("points must have shape (N, 2).")

    if not np.isfinite(points_array).all():
        raise ValueError("points contains invalid or non-finite coordinates.")

    points_array = points_array.reshape(-1, 1, 2)
    transformed = cv2.transform(points_array, matrix)

    return transformed.reshape(-1, 2).tolist()


def fixed_overlay_baseline(template_img, target_size=STANDARD_SIZE):
    """Resize a template without applying landmark alignment."""
    if template_img is None:
        raise ValueError("Template image could not be loaded.")

    if not isinstance(template_img, np.ndarray) or template_img.size == 0:
        raise ValueError("Template image is empty or invalid.")

    if (
        not isinstance(target_size, (tuple, list))
        or len(target_size) != 2
        or int(target_size[0]) <= 0
        or int(target_size[1]) <= 0
    ):
        raise ValueError("target_size must be a positive (width, height) pair.")

    width, height = int(target_size[0]), int(target_size[1])
    return cv2.resize(
        template_img,
        (width, height),
        interpolation=cv2.INTER_AREA
    )
