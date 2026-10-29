
import glob
import os

import cv2
import numpy as np

from app.selection import select_variant
from app.alignment import align_variant
from app.segmentation import get_hair_mask
from app.blending import blend_template
from app.comparison import create_before_after
from app.explanation import generate_explanation
from app.database import save_feedback
from app.mock_component3 import get_next_style, get_ranked_styles
from app.config import STANDARD_SIZE


# Absolute backend directory:
# D:\grooming_component4\backend
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def backend_path(*parts):
    """Build an absolute path relative to the backend directory."""
    return os.path.join(BACKEND_DIR, *parts)


def find_template_path(gender, variant_name):
    """Find a template without assuming .jpg/.JPG extension."""
    template_dir = backend_path("templates", gender)
    pattern = os.path.join(template_dir, variant_name + ".*")

    for path in glob.glob(pattern):
        if os.path.splitext(path)[1].lower() in (
            ".jpg", ".jpeg", ".png"
        ):
            return path

    return None


def resize_mask(mask, target_size):
    """Resize a mask to (width, height)."""
    if mask is None:
        return None

    if mask.ndim == 3:
        mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)

    return cv2.resize(
        mask,
        target_size,
        interpolation=cv2.INTER_NEAREST
    )




def save_image(path, image):
    """Save an image using OpenCV, with a PIL fallback."""
    import os
    import cv2
    import numpy as np
    from PIL import Image

    absolute_path = (
        path if os.path.isabs(path)
        else backend_path(path)
    )

    absolute_path = os.path.normpath(absolute_path)
    output_dir = os.path.dirname(absolute_path)

    os.makedirs(output_dir, exist_ok=True)

    if image is None:
        raise ValueError(f"Cannot save empty image: {absolute_path}")

    if image.dtype != np.uint8:
        image = np.clip(image, 0, 255).astype(np.uint8)

    # First try OpenCV
    try:
        if cv2.imwrite(absolute_path, image):
            return absolute_path
    except Exception as exc:
        print("OpenCV save failed:", repr(exc))

    # Fallback to PIL
    try:
        if image.ndim == 2:
            pil_image = Image.fromarray(image)
        elif image.ndim == 3 and image.shape[2] == 3:
            pil_image = Image.fromarray(
                cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            )
        else:
            raise ValueError(
                f"Unsupported image shape: {image.shape}"
            )

        pil_image.save(absolute_path)
        return absolute_path

    except Exception as exc:
        raise RuntimeError(
            f"Could not save image to {absolute_path}. "
            f"OpenCV and PIL both failed. PIL error: {exc!r}"
        ) from exc



def measure_user_geometry(user_points, user_hair_mask):
    """Estimate normalized face-width and hair-density scores from this photo.

    face_width_ratio is the jaw landmark distance divided by the detected
    hair-mask bounding-box width. hair_density_score is the fraction of pixels
    occupied by the hair mask inside its bounding box. These are image-derived
    proxies, not clinical measurements or true strand-level density.
    """
    if user_points is None or len(user_points) < 3:
        raise ValueError("At least three user face landmarks are required.")
    if user_hair_mask is None or not isinstance(user_hair_mask, np.ndarray):
        raise ValueError("A valid user hair mask is required.")

    if user_hair_mask.ndim == 3:
        if user_hair_mask.shape[2] == 4:
            user_hair_mask = cv2.cvtColor(user_hair_mask, cv2.COLOR_BGRA2GRAY)
        else:
            user_hair_mask = cv2.cvtColor(user_hair_mask, cv2.COLOR_BGR2GRAY)

    binary = (user_hair_mask > 127).astype(np.uint8)
    ys, xs = np.where(binary > 0)
    if len(xs) == 0 or len(ys) == 0:
        raise ValueError("User hair mask has no foreground pixels.")

    jaw_left = np.asarray(user_points[0], dtype=np.float32)
    jaw_right = np.asarray(user_points[1], dtype=np.float32)
    face_width_px = float(np.linalg.norm(jaw_right - jaw_left))
    if face_width_px < 20:
        raise ValueError("Detected face width is too small to measure reliably.")

    hair_box_width = int(xs.max() - xs.min() + 1)
    hair_box_height = int(ys.max() - ys.min() + 1)
    if hair_box_width < 10 or hair_box_height < 10:
        raise ValueError("Detected hair-mask bounding box is too small.")

    # Normalized ratio compatible with template metadata values such as 0.60-0.75.
    face_width_ratio = float(np.clip(face_width_px / hair_box_width, 0.0, 1.0))

    # Mask occupancy in its own bounding box. This estimates mask fullness;
    # it does not measure individual hair strands or biological hair density.
    box_area = float(hair_box_width * hair_box_height)
    hair_density_score = float(np.clip(np.count_nonzero(binary) / box_area, 0.0, 1.0))

    measurements = {
        "face_width_px": round(face_width_px, 2),
        "hair_bbox_width_px": hair_box_width,
        "hair_bbox_height_px": hair_box_height,
        "user_face_width": round(face_width_ratio, 4),
        "user_hair_density": round(hair_density_score, 4),
    }
    print("Measured user geometry:", measurements)
    return measurements


def generate_preview(
    user_id,
    user_photo_path,
    gender,
    style_type,
    current_rank=1,
    bisenet_model=None
):
    """
    Generate a template-based hairstyle preview.

    Note:
    This is a template-warping and blending pipeline, not a
    photorealistic AI hairstyle-transfer model.
    """

    from app.landmarks import get_user_landmarks

    if style_type != "hairstyle":
        return {
            "error": (
                "Beard preview requires a beard-specific segmentation "
                "and blending pipeline. It is not implemented yet."
            )
        }

    # Resolve uploaded/user image path
    if not os.path.isabs(user_photo_path):
        resolved_user_path = backend_path(user_photo_path)
    else:
        resolved_user_path = user_photo_path

    if not os.path.isfile(resolved_user_path):
        return {
            "error": f"User photo not found: {resolved_user_path}"
        }

    if bisenet_model is None:
        return {"error": "BiSeNet model is not loaded."}

    # Load the user's original image
    user_photo_original = cv2.imread(resolved_user_path)

    if user_photo_original is None:
        return {"error": "Could not read user photo."}

    target_width, target_height = STANDARD_SIZE
    target_size = (target_width, target_height)

    # Keep the current project workflow's standard dimensions
    user_photo = cv2.resize(user_photo_original, target_size)

    # Detect facial landmarks in the same standard coordinate space
    user_points = get_user_landmarks(resolved_user_path)

    if user_points is None:
        return {"error": "No face detected in user photo."}

    # Get ranked styles for the selected category
    ranked_styles = get_ranked_styles(gender, style_type)

    if not ranked_styles:
        return {
            "error": f"No {style_type} styles available for {gender}."
        }

    current_style_data = next(
        (
            item for item in ranked_styles
            if item.get("rank") == current_rank
        ),
        None
    )

    if current_style_data is None:
        return {"error": f"No style found for rank {current_rank}."}

    style_prefix = current_style_data["style"]

    # Measure the uploaded user's actual hair and face geometry before
    # selecting a template. The fixed values 0.72 and 0.35 are no longer used.
    try:
        user_hair_mask = get_hair_mask(
            bisenet_model,
            resolved_user_path
        )
        if user_hair_mask is None:
            return {"error": "Could not segment hair from user photo."}
        user_hair_mask = resize_mask(user_hair_mask, target_size)
        user_geometry = measure_user_geometry(user_points, user_hair_mask)
    except Exception as exc:
        return {"error": f"Could not measure user face/hair geometry: {exc}"}

    variant_name, distance, variant_data = select_variant(
        user_face_width=user_geometry["user_face_width"],
        user_hair_density=user_geometry["user_hair_density"],
        style_prefix=style_prefix,
        gender=gender
    )

    if variant_name is None or variant_data is None:
        return {
            "error": f"No matching template variant for {style_prefix}."
        }

    # Load template using its actual file extension
    template_path = find_template_path(gender, variant_name)

    if template_path is None:
        return {
            "error": f"Template image not found for {variant_name}."
        }

    template_img = cv2.imread(template_path)

    if template_img is None:
        return {
            "error": f"Could not read template image: {template_path}"
        }

    template_img = cv2.resize(template_img, target_size)

    template_points = variant_data.get("points")

    if not template_points or len(template_points) != 3:
        return {
            "error": (
                f"Template {variant_name} must contain exactly "
                "three alignment points."
            )
        }

    # The old whole-portrait affine warp often makes the template hair look
    # like a floating strip. We will segment the template hair first, crop the
    # actual hair pixels, then fit that isolated layer to the user's face width.
    # Template points are still checked above for compatibility with library.json.

    # The user hair mask was already generated for geometry measurement.
    # Segment only the selected template here.
    try:
        template_hair_mask = get_hair_mask(
            bisenet_model,
            template_path
        )
    except Exception as exc:
        return {"error": f"Template hair segmentation failed: {exc}"}

    if template_hair_mask is None:
        return {"error": "Could not segment hair from template."}

    user_hair_mask = resize_mask(user_hair_mask, target_size)
    template_hair_mask = resize_mask(template_hair_mask, target_size)

    # -------------------------------------------------
    # STEP 4: Fit isolated template hair to user face geometry
    # -------------------------------------------------

    user_hair_mask = resize_mask(user_hair_mask, target_size)
    template_hair_mask = resize_mask(template_hair_mask, target_size)

    if user_hair_mask is None or not np.any(user_hair_mask):
        return {"error": "User hair mask is empty; cannot estimate hair coverage."}
    if template_hair_mask is None or not np.any(template_hair_mask):
        return {"error": "Template hair mask is empty; cannot isolate template hair."}

    user_binary_mask = np.where(user_hair_mask > 127, 255, 0).astype(np.uint8)
    template_binary_mask = np.where(template_hair_mask > 127, 255, 0).astype(np.uint8)

    # Face landmarks are: left jaw, right jaw, and upper-face point.
    # The first two determine face width; the third is a rough hairline anchor,
    # not a true hairline detector.
    jaw_left = np.asarray(user_points[0], dtype=np.float32)
    jaw_right = np.asarray(user_points[1], dtype=np.float32)
    upper_face = np.asarray(user_points[2], dtype=np.float32)

    face_width = float(np.linalg.norm(jaw_right - jaw_left))
    if face_width < 20:
        return {"error": "Detected face width is too small for hairstyle fitting."}

    # Isolate template hair using the segmentation mask, then crop to its
    # occupied bounding box so the template face/background is not warped.
    ys, xs = np.where(template_binary_mask > 0)
    if len(xs) == 0 or len(ys) == 0:
        return {"error": "Template hair mask contains no foreground pixels."}

    pad = 3
    x0 = max(0, int(xs.min()) - pad)
    x1 = min(target_width, int(xs.max()) + 1 + pad)
    y0 = max(0, int(ys.min()) - pad)
    y1 = min(target_height, int(ys.max()) + 1 + pad)

    hair_crop = template_img[y0:y1, x0:x1].copy()
    hair_mask_crop = template_binary_mask[y0:y1, x0:x1].copy()

    crop_h, crop_w = hair_mask_crop.shape
    if crop_w < 5 or crop_h < 5:
        return {"error": "Isolated template hair crop is too small."}

    # Fit width to face geometry. This ratio is a tunable visual parameter:
    # a hairstyle should generally be wider than the jaw/cheek landmark span.
    # Use the selected template's face-width ratio as a per-hairstyle prior.
    # library.json defines face_width_ratio as a template-specific compatibility
    # value; it is not a user-specific measurement. Calibrate around 0.68 so
    # existing previews do not jump dramatically, then clamp the adjustment.
    template_face_width_ratio = float(
        variant_data.get("face_width_ratio", 0.68)
    )
    if not np.isfinite(template_face_width_ratio) or template_face_width_ratio <= 0:
        template_face_width_ratio = 0.68

    template_fit_adjustment = float(
        np.clip(0.68 / template_face_width_ratio, 0.90, 1.10)
    )
    fit_multiplier = 1.42 * template_fit_adjustment
    target_hair_width = int(
        np.clip(face_width * fit_multiplier, 150, target_width * 0.92)
    )
    scale = target_hair_width / float(crop_w)
    fitted_w = max(1, int(round(crop_w * scale)))
    fitted_h = max(1, int(round(crop_h * scale)))

    hair_crop = cv2.resize(hair_crop, (fitted_w, fitted_h), interpolation=cv2.INTER_CUBIC)
    hair_mask_crop = cv2.resize(
        hair_mask_crop, (fitted_w, fitted_h), interpolation=cv2.INTER_LINEAR
    )
    hair_mask_crop = np.clip(hair_mask_crop, 0, 255).astype(np.uint8)

    # Align the central hairline (bottom-most mask pixel around the centre)
    # to the user's upper-face anchor. Side locks may extend below this point.
    centre_l = int(fitted_w * 0.35)
    centre_r = int(fitted_w * 0.65)
    central_region = hair_mask_crop[:, centre_l:centre_r]
    central_ys = np.where(central_region > 127)[0]
    if len(central_ys):
        hairline_y_in_crop = int(central_ys.max())
    else:
        hairline_y_in_crop = fitted_h - 1

    face_centre_x = int(round((jaw_left[0] + jaw_right[0]) / 2.0))
    # MediaPipe landmark 10 is not the true hairline. Use a small conservative
    # offset; this is an initial geometric fit, not semantic hairline detection.
    hairline_target_y = int(round(upper_face[1] + 2))

    canvas = np.zeros((target_height, target_width, 3), dtype=np.uint8)
    canvas_mask = np.zeros((target_height, target_width), dtype=np.uint8)

    place_x = int(round(face_centre_x - fitted_w / 2.0))
    place_y = int(round(hairline_target_y - hairline_y_in_crop))

    # Clip placement to the canvas without distorting the hair layer.
    src_x0 = max(0, -place_x)
    src_y0 = max(0, -place_y)
    dst_x0 = max(0, place_x)
    dst_y0 = max(0, place_y)
    copy_w = min(fitted_w - src_x0, target_width - dst_x0)
    copy_h = min(fitted_h - src_y0, target_height - dst_y0)
    if copy_w <= 0 or copy_h <= 0:
        return {"error": "Fitted hairstyle falls outside the preview canvas."}

    canvas[dst_y0:dst_y0 + copy_h, dst_x0:dst_x0 + copy_w] = hair_crop[
        src_y0:src_y0 + copy_h, src_x0:src_x0 + copy_w
    ]
    canvas_mask[dst_y0:dst_y0 + copy_h, dst_x0:dst_x0 + copy_w] = hair_mask_crop[
        src_y0:src_y0 + copy_h, src_x0:src_x0 + copy_w
    ]

    # Remove the full detected original-hair region, then let the fitted
    # hairstyle cover the inpainted area. Keep the fitted hair geometry above
    # unchanged so the current preview position and scale are preserved.
    removal_kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (5, 5)
    )
    removal_mask = cv2.dilate(
        user_binary_mask,
        removal_kernel,
        iterations=1
    )

    if np.any(removal_mask):
        cleaned_user_photo = cv2.inpaint(
            user_photo,
            removal_mask,
            3,
            cv2.INPAINT_TELEA
        )
    else:
        cleaned_user_photo = user_photo.copy()

    # Keep alpha edges soft but do not blur the entire hairstyle.
    blend_mask = canvas_mask.copy()

    # -------------------------------------------------
    # Save diagnostics
    # -------------------------------------------------
    user_mask_path = f"test_photos/user_hair_mask_rank{current_rank}.png"
    template_mask_path = f"test_photos/template_hair_mask_rank{current_rank}.png"
    warped_mask_path = f"test_photos/warped_template_hair_mask_rank{current_rank}.png"
    blend_mask_path = f"test_photos/combined_hair_mask_rank{current_rank}.png"
    removal_mask_path = f"test_photos/hair_removal_mask_rank{current_rank}.png"
    cleaned_photo_path = f"test_photos/cleaned_user_photo_rank{current_rank}.jpg"

    save_image(user_mask_path, user_binary_mask)
    save_image(template_mask_path, template_binary_mask)
    save_image(warped_mask_path, canvas_mask)
    save_image(blend_mask_path, blend_mask)
    save_image(removal_mask_path, removal_mask)
    save_image(cleaned_photo_path, cleaned_user_photo)

    # Blend the isolated template hair layer over the original photo.
    final_preview = blend_template(
        canvas,
        cleaned_user_photo,
        blend_mask,
        None,
        feather_radius=2,
        edge_blur=1.5
    )

    # Generate before/after comparison
    before_after = create_before_after(
        user_photo,
        final_preview
    )

    # Demo explanation from ranked-style metadata
    mock_attribution = {
        "confidence": current_style_data.get("confidence", 0),
        "contributing_factors": {
            "jawline": 0.4,
            "forehead": 0.3,
            "symmetry": 0.3
        }
    }

    explanation_text = generate_explanation(mock_attribution)

    # Save generated images
    preview_path = (
        f"test_photos/preview_{style_type}_rank{current_rank}.jpg"
    )
    comparison_path = (
        f"test_photos/before_after_{style_type}_rank{current_rank}.jpg"
    )

    save_image(preview_path, final_preview)
    save_image(comparison_path, before_after)

    return {
        "style": style_prefix,
        "style_type": style_type,
        "variant": variant_name,
        "preview_path": preview_path.replace("\\", "/"),
        "before_after_path": comparison_path.replace("\\", "/"),
        "explanation": explanation_text,
        "current_rank": current_rank,
        "measured_geometry": user_geometry,
        "fit_diagnostics": {
            "template_face_width_ratio": round(template_face_width_ratio, 4),
            "template_fit_adjustment": round(template_fit_adjustment, 4),
            "fit_multiplier": round(fit_multiplier, 4),
            "target_hair_width_px": int(target_hair_width),
            "fitted_hair_size_px": [int(fitted_w), int(fitted_h)]
        }
    }


def process_feedback(
    user_id,
    current_rank,
    feedback_value,
    style_shown,
    variant_shown,
    gender,
    style_type
):
    """Save feedback and choose the next action."""

    save_feedback(
        user_id,
        style_shown,
        variant_shown,
        feedback_value
    )

    if feedback_value == "dislike":
        next_style = get_next_style(
            current_rank,
            gender,
            style_type
        )

        if next_style:
            return {
                "action": "show_next",
                "next_rank": current_rank + 1,
                "style": next_style
            }

        return {"action": "no_more_styles"}

    if feedback_value == "like":
        return {"action": "ask_advanced_preview"}

    return {"action": "unknown"}


def process_advanced_preview_choice(wants_advanced):
    """Handle the user's advanced-preview choice."""

    if wants_advanced:
        return {
            "action": "advanced_preview_requested",
            "message": (
                "Advanced rendering is not integrated yet. "
                "The current preview remains template-based."
            )
        }

    return {
        "action": "preview_accepted",
        "message": "User accepted the current template-based preview."
    }
