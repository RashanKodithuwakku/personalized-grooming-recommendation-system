import cv2
import numpy as np


class QualityService:
    """
    Service for validating image quality attributes such as resolution,
    blurriness (Laplacian variance), and brightness levels.
    """

    def __init__(
        self,
        min_resolution: int = 300,
        blur_threshold: float = 100.0,
        min_brightness: float = 40.0,
        max_brightness: float = 240.0
    ):
        self.min_resolution = min_resolution
        self.blur_threshold = blur_threshold
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness

    def validate_image_quality(self, image_bytes: bytes) -> dict:
        """
        Validates the quality of an input image provided as raw bytes.

        Checks performed:
        1. Decode raw bytes to OpenCV BGR image array.
        2. Resolution check: Width and Height must be >= min_resolution (300px).
        3. Blur check: Laplacian variance must be >= blur_threshold (100.0).
        4. Brightness check: Average pixel intensity must be between
           min_brightness (40.0) and max_brightness (240.0).

        Returns:
            dict: {
                "is_valid": bool,
                "reason": str,
                "image": np.ndarray or None
            }
        """
        try:
            if not image_bytes:
                return {
                    "is_valid": False,
                    "reason": "Provided image bytes are empty.",
                    "image": None
                }

            # Convert bytes to numpy array and decode to OpenCV BGR image
            np_arr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if img is None:
                return {
                    "is_valid": False,
                    "reason": "Failed to decode image bytes. Image format may be invalid or corrupted.",
                    "image": None
                }

            # 1. Resolution Check
            height, width = img.shape[:2]
            if width < self.min_resolution or height < self.min_resolution:
                return {
                    "is_valid": False,
                    "reason": (
                        f"Image resolution too low ({width}x{height}px). "
                        f"Minimum required is {self.min_resolution}x{self.min_resolution}px."
                    ),
                    "image": img
                }

            # Convert image to grayscale for blur & brightness checks
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # 2. Blur Check using Laplacian Variance
            laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            if laplacian_var < self.blur_threshold:
                return {
                    "is_valid": False,
                    "reason": (
                        f"Image is too blurry (Laplacian variance: {laplacian_var:.2f}, "
                        f"threshold: {self.blur_threshold}). Please provide a clearer photo."
                    ),
                    "image": img
                }

            # 3. Brightness Check using Average Pixel Intensity
            brightness = float(np.mean(gray))
            if brightness < self.min_brightness:
                return {
                    "is_valid": False,
                    "reason": (
                        f"Image is too dark (average brightness: {brightness:.2f}, "
                        f"minimum threshold: {self.min_brightness}). Please improve lighting."
                    ),
                    "image": img
                }

            if brightness > self.max_brightness:
                return {
                    "is_valid": False,
                    "reason": (
                        f"Image is overexposed (average brightness: {brightness:.2f}, "
                        f"maximum threshold: {self.max_brightness}). Please reduce excessive lighting."
                    ),
                    "image": img
                }

            # All checks passed successfully
            return {
                "is_valid": True,
                "reason": "Image quality validation passed successfully.",
                "image": img
            }

        except Exception as e:
            return {
                "is_valid": False,
                "reason": f"An error occurred during image quality validation: {str(e)}",
                "image": None
            }
