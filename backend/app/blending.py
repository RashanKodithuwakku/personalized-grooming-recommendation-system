import cv2
import numpy as np


def _as_uint8_image(image, name):
    """Validate an image and return it as uint8."""
    if image is None:
        raise ValueError(f"{name} is required.")

    if not isinstance(image, np.ndarray) or image.size == 0:
        raise ValueError(f"{name} must be a non-empty NumPy image.")

    if image.dtype != np.uint8:
        image = np.clip(image, 0, 255).astype(np.uint8)

    return image


def _prepare_mask(mask, target_width, target_height):
    """Return a single-channel 8-bit mask with the target dimensions."""
    if mask is None:
        raise ValueError("mask is required.")

    if not isinstance(mask, np.ndarray) or mask.size == 0:
        raise ValueError("mask must be a non-empty NumPy array.")

    if mask.ndim == 3:
        if mask.shape[2] == 4:
            mask = cv2.cvtColor(mask, cv2.COLOR_BGRA2GRAY)
        elif mask.shape[2] == 3:
            mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
        else:
            raise ValueError(f"Unsupported mask shape: {mask.shape}")
    elif mask.ndim != 2:
        raise ValueError(f"Unsupported mask shape: {mask.shape}")

    if mask.shape != (target_height, target_width):
        mask = cv2.resize(
            mask,
            (target_width, target_height),
            interpolation=cv2.INTER_LINEAR
        )

    if mask.dtype != np.uint8:
        mask = np.clip(mask, 0, 255).astype(np.uint8)

    return mask


def make_soft_alpha(mask, feather_radius=3, edge_blur=2.0):
    """
    Convert a grayscale/binary mask into a soft alpha matte.

    Args:
        mask: 8-bit mask; white means template pixels are visible.
        feather_radius: small edge-feather amount in pixels.
        edge_blur: Gaussian sigma for softening the edge.

    Returns:
        Float32 alpha array with shape (height, width), values 0..1.

    Note:
        A blurred segmentation mask cannot recover individual hair strands.
        For best results, the source template should already be hair-only
        with a clean, accurate mask.
    """
    if mask is None or not isinstance(mask, np.ndarray) or mask.size == 0:
        raise ValueError("A non-empty mask is required.")

    if mask.ndim == 3:
        if mask.shape[2] == 4:
            mask = cv2.cvtColor(mask, cv2.COLOR_BGRA2GRAY)
        elif mask.shape[2] == 3:
            mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
        else:
            raise ValueError(f"Unsupported mask shape: {mask.shape}")

    if mask.ndim != 2:
        raise ValueError(f"Mask must be 2D or 3D; got {mask.shape}.")

    if mask.dtype != np.uint8:
        mask = np.clip(mask, 0, 255).astype(np.uint8)

    alpha = mask.astype(np.float32) / 255.0
    alpha = np.clip(alpha, 0.0, 1.0)

    # Feather only a narrow edge band. Avoid blurring the whole hairstyle.
    if feather_radius > 0:
        radius = max(1, int(feather_radius))
        kernel_size = radius * 2 + 1
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (kernel_size, kernel_size)
        )
        eroded = cv2.erode(mask, kernel, iterations=1).astype(np.float32) / 255.0
        dilated = cv2.dilate(mask, kernel, iterations=1).astype(np.float32) / 255.0

        # Use the blurred mask as a soft transition, but preserve the core.
        blurred = cv2.GaussianBlur(
            alpha,
            (0, 0),
            sigmaX=max(float(edge_blur), 0.1)
        )
        edge_band = np.clip(dilated - eroded, 0.0, 1.0)
        alpha = alpha * (1.0 - edge_band) + blurred * edge_band

    alpha = np.clip(alpha, 0.0, 1.0)
    return alpha.astype(np.float32)


def blend_template(
    warped_template,
    user_photo,
    mask,
    center=None,
    feather_radius=3,
    edge_blur=2.0
):
    """
    Composite the masked template region over the user's photo.

    Args:
        warped_template: BGR template image already aligned to user_photo.
        user_photo: original/prepared BGR user image.
        mask: mask where white pixels indicate visible template pixels.
        center: kept for compatibility with existing callers; not used.
        feather_radius: narrow edge feather in pixels.
        edge_blur: edge-softening Gaussian sigma.

    Returns:
        uint8 BGR blended image.

    Important:
        This function blends pixels; it does not itself remove original hair,
        reconstruct the forehead, or align the hairline. The mask must match
        the actual hair region, and warped_template should contain the desired
        template hair pixels in that region.
    """
    warped_template = _as_uint8_image(warped_template, "warped_template")
    user_photo = _as_uint8_image(user_photo, "user_photo")

    if warped_template.ndim != 3 or warped_template.shape[2] != 3:
        raise ValueError(
            "warped_template must be a 3-channel BGR image."
        )

    if user_photo.ndim != 3 or user_photo.shape[2] != 3:
        raise ValueError("user_photo must be a 3-channel BGR image.")

    target_height, target_width = user_photo.shape[:2]

    if warped_template.shape[:2] != (target_height, target_width):
        warped_template = cv2.resize(
            warped_template,
            (target_width, target_height),
            interpolation=cv2.INTER_LINEAR
        )

    mask = _prepare_mask(mask, target_width, target_height)

    if cv2.countNonZero(mask) == 0:
        return user_photo.copy()

    alpha = make_soft_alpha(
        mask,
        feather_radius=feather_radius,
        edge_blur=edge_blur
    )[:, :, np.newaxis]

    template_float = warped_template.astype(np.float32)
    user_float = user_photo.astype(np.float32)

    blended = (
        template_float * alpha
        + user_float * (1.0 - alpha)
    )

    return np.clip(blended, 0, 255).astype(np.uint8)
