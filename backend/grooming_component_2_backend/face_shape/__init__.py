"""Face shape classification component.

Tier 1 uses eight anthropometric landmarks. Tier 2 may add trichion and a
jaw-type observation. Symmetry and balance are separate scoring modules.
"""

from face_shape.contracts import (
    CORE_LANDMARKS,
    FACE_SHAPES,
    MEDIAPIPE_FACE_MESH_INDEX,
    REQUIRED_LANDMARKS,
    ClassificationInput,
    FaceShapeResult,
    JawTypeObservation,
    LandmarkPoint,
    RatioFeatures,
    Tier1Landmarks,
    Tier2Landmarks,
    parse_named_landmarks,
)
from face_shape.geometry import prepare_landmarks
from face_shape.indices import measure_ratios
from face_shape.membership import confidence_vector, tier1_scores
from face_shape.tier1 import classify_tier1
from face_shape.api import create_app
from face_shape.pipeline import analyse_profile
from face_shape.tier2 import classify_face

__all__ = [
    "CORE_LANDMARKS",
    "FACE_SHAPES",
    "MEDIAPIPE_FACE_MESH_INDEX",
    "REQUIRED_LANDMARKS",
    "ClassificationInput",
    "analyse_profile",
    "create_app",
    "classify_face",
    "classify_tier1",
    "FaceShapeResult",
    "JawTypeObservation",
    "LandmarkPoint",
    "RatioFeatures",
    "Tier1Landmarks",
    "Tier2Landmarks",
    "confidence_vector",
    "measure_ratios",
    "parse_named_landmarks",
    "prepare_landmarks",
    "tier1_scores",
]

__version__ = "0.1.0"
