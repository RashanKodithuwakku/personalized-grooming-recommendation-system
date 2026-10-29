
import os
import sys

import cv2
import numpy as np
import torch
import torchvision.transforms as transforms
from PIL import Image

from app.config import STANDARD_SIZE


# --------------------------------------------------
# BiSeNet repository and model setup
# --------------------------------------------------

BACKEND_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

BISENET_REPO = os.path.abspath(
    os.path.join(BACKEND_DIR, "..", "face-parsing.PyTorch")
)

if BISENET_REPO not in sys.path:
    sys.path.insert(0, BISENET_REPO)

try:
    from model import BiSeNet
    _BISENET_IMPORT_ERROR = None
except Exception as exc:
    BiSeNet = None
    _BISENET_IMPORT_ERROR = str(exc)


HAIR_CLASS_ID = 17


# --------------------------------------------------
# Image preprocessing
# --------------------------------------------------

to_tensor = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize(
        (0.485, 0.456, 0.406),
        (0.229, 0.224, 0.225)
    ),
])


# --------------------------------------------------
# Load BiSeNet model
# --------------------------------------------------

def load_bisenet_model(weight_path=None):
    """
    Load the pretrained BiSeNet face-parsing model.
    Runs on CPU by default.
    """

    if weight_path is None:
        weight_path = os.path.join(
            BISENET_REPO,
            "res",
            "cp",
            "79999_iter.pth"
        )
    elif not os.path.isabs(weight_path):
        weight_path = os.path.abspath(
            os.path.join(BACKEND_DIR, weight_path)
        )

    if not os.path.isfile(weight_path):
        raise FileNotFoundError(
            f"BiSeNet weights not found: {weight_path}"
        )
    if BiSeNet is None:
        raise RuntimeError(
            "Could not import BiSeNet from the face-parsing.PyTorch repository. "
            f"Check that the repository exists at {BISENET_REPO}. "
            f"Import detail: {_BISENET_IMPORT_ERROR}"
        )

    model = BiSeNet(n_classes=19)

    state_dict = torch.load(
        weight_path,
        map_location="cpu"
    )

    model.load_state_dict(state_dict)
    model.eval()

    return model


# --------------------------------------------------
# Keep the largest connected component
# --------------------------------------------------

def keep_largest_component(mask):
    """
    Remove small disconnected foreground regions.
    This is a basic cleanup step and does not guarantee
    that every remaining pixel belongs to hair.
    """

    binary = (mask > 0).astype(np.uint8)

    count, labels, stats, _ = cv2.connectedComponentsWithStats(
        binary,
        connectivity=8
    )

    if count <= 1:
        return np.zeros_like(mask)

    # Ignore label 0, which represents the background
    areas = stats[1:, cv2.CC_STAT_AREA]

    largest_label = 1 + int(np.argmax(areas))

    cleaned = np.zeros_like(mask)
    cleaned[labels == largest_label] = 255

    return cleaned


# --------------------------------------------------
# Generate hair segmentation mask
# --------------------------------------------------

def get_hair_mask(model, image_path):
    """
    Generate a binary hair mask using BiSeNet class 17.

    Args:
        model: Loaded BiSeNet model.
        image_path: Path to the input image.

    Returns:
        uint8 mask with values 0 and 255, at the original
        image dimensions.
    """

    if model is None:
        raise ValueError("BiSeNet model is not loaded.")

    image = cv2.imread(image_path)

    if image is None:
        raise FileNotFoundError(
            f"Could not read image: {image_path}"
        )

    original_height, original_width = image.shape[:2]

    # Resize image to the dimensions expected by the project
    resized = cv2.resize(image, STANDARD_SIZE)

    # OpenCV uses BGR; BiSeNet preprocessing expects RGB
    rgb_image = cv2.cvtColor(
        resized,
        cv2.COLOR_BGR2RGB
    )

    pil_image = Image.fromarray(rgb_image)
    image_tensor = to_tensor(pil_image).unsqueeze(0)

    # Inference
    model.eval()

    with torch.no_grad():
        output = model(image_tensor)[0]
        parsing = (
            output.squeeze(0)
            .cpu()
            .numpy()
            .argmax(0)
        )

    print("Unique classes detected:", np.unique(parsing))

    # Extract the hair class
    hair_mask = (
        parsing == HAIR_CLASS_ID
    ).astype(np.uint8) * 255

    print(
        "Hair pixels before cleanup:",
        int(np.count_nonzero(hair_mask))
    )

    if np.count_nonzero(hair_mask) == 0:
        print(
            "WARNING: No hair pixels detected. "
            "Returning an empty mask."
        )

        return np.zeros(
            (original_height, original_width),
            dtype=np.uint8
        )

    # Fill small holes without aggressively changing the hair outline
    kernel = np.ones((3, 3), dtype=np.uint8)

    hair_mask = cv2.morphologyEx(
        hair_mask,
        cv2.MORPH_CLOSE,
        kernel
    )

    # Remove disconnected noise
    hair_mask = keep_largest_component(hair_mask)

    print(
        "Hair pixels after cleanup:",
        int(np.count_nonzero(hair_mask))
    )

    # Restore original image dimensions
    hair_mask_original = cv2.resize(
        hair_mask,
        (original_width, original_height),
        interpolation=cv2.INTER_NEAREST
    )

    return hair_mask_original


# --------------------------------------------------
# Standalone test
# --------------------------------------------------

if __name__ == "__main__":

    model = load_bisenet_model()

    image_path = os.path.join(
        BACKEND_DIR,
        "test_photos",
        "user1.jpg"
    )

    mask = get_hair_mask(model, image_path)

    output_path = os.path.join(
        BACKEND_DIR,
        "test_photos",
        "hair_mask_output.png"
    )

    os.makedirs(
        os.path.dirname(output_path),
        exist_ok=True
    )

    if cv2.imwrite(output_path, mask):
        print("Hair mask saved to:", output_path)
        print("Mask dimensions:", mask.shape)
    else:
        raise RuntimeError(
            f"Could not save hair mask: {output_path}"
        )
