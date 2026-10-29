"""Before/after composition and simple image-difference metrics."""
import cv2
import numpy as np


def _validate_image(image, name):
    if image is None or not isinstance(image, np.ndarray) or image.size == 0:
        raise ValueError(f"{name} must be a non-empty image array.")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"{name} must be a 3-channel BGR image.")
    if image.dtype != np.uint8:
        image = np.clip(image, 0, 255).astype(np.uint8)
    return image


def create_before_after(original_photo, preview_photo):
    """Join original and preview images side-by-side at a shared height."""
    original_photo = _validate_image(original_photo, "original_photo")
    preview_photo = _validate_image(preview_photo, "preview_photo")
    h1, w1 = original_photo.shape[:2]
    h2, w2 = preview_photo.shape[:2]
    target_height = min(h1, h2)
    if target_height < 1:
        raise ValueError("Images must have positive dimensions.")
    original_resized = cv2.resize(original_photo, (max(1, round(w1 * target_height / h1)), target_height))
    preview_resized = cv2.resize(preview_photo, (max(1, round(w2 * target_height / h2)), target_height))
    gap = np.full((target_height, 10, 3), 255, dtype=np.uint8)
    return np.hstack([original_resized, gap, preview_resized])


def calculate_preview_metrics(original_photo, preview_photo, changed_threshold=12):
    """Return transparent pixel-difference metrics, not a beauty/quality score.

    Both images are resized to the same dimensions before comparison.
    """
    original_photo = _validate_image(original_photo, "original_photo")
    preview_photo = _validate_image(preview_photo, "preview_photo")
    if original_photo.shape[:2] != preview_photo.shape[:2]:
        preview_photo = cv2.resize(preview_photo, (original_photo.shape[1], original_photo.shape[0]))
    a = original_photo.astype(np.float32)
    b = preview_photo.astype(np.float32)
    diff = np.abs(a - b)
    mae = float(np.mean(diff))
    mse = float(np.mean((a - b) ** 2))
    psnr = float("inf") if mse == 0 else float(20 * np.log10(255.0 / np.sqrt(mse)))
    per_pixel_diff = np.max(diff, axis=2)
    changed_ratio = float(np.mean(per_pixel_diff > float(changed_threshold)))
    return {
        "mean_absolute_pixel_difference": round(mae, 4),
        "psnr_db": "infinite" if np.isinf(psnr) else round(psnr, 4),
        "changed_pixel_ratio": round(changed_ratio, 6),
        "changed_pixel_percent": round(changed_ratio * 100, 3),
        "threshold": int(changed_threshold),
        "note": "Pixel-difference metrics describe image changes; they do not measure realism or user satisfaction."
    }
