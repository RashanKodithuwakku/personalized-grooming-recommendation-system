"""Central configuration for Component 4."""
import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
PROJECT_DIR = BACKEND_DIR.parent
STANDARD_WIDTH = int(os.getenv("C4_STANDARD_WIDTH", "512"))
STANDARD_HEIGHT = int(os.getenv("C4_STANDARD_HEIGHT", "512"))
STANDARD_SIZE = (STANDARD_WIDTH, STANDARD_HEIGHT)  # OpenCV order: width, height
UPLOAD_DIR = BACKEND_DIR / "test_photos"
TEMPLATE_DIR = BACKEND_DIR / "templates"
LIBRARY_PATH = TEMPLATE_DIR / "library.json"
POINTS_PATH = TEMPLATE_DIR / "points_raw.json"
FEEDBACK_DB_PATH = BACKEND_DIR / "feedback.db"
MAX_UPLOAD_BYTES = int(os.getenv("C4_MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
