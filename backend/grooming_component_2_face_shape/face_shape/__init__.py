"""Face shape classification component.

Tier 1 uses eight anthropometric landmarks. Tier 2 may add trichion and a
jaw-type observation. Symmetry and balance are outside this component.
"""

from face_shape.contracts import (
    CORE_LANDMARKS,
    FACE_SHAPES,
    MEDIAPIPE_FACE_MESH_INDEX,
    ClassificationInput,
    FaceShapeResult,
    JawTypeObservation,
    LandmarkPoint,
    RatioFeatures,
    Tier1Landmarks,
    Tier2Landmarks,
    parse_named_landmarks,
)

__all__ = [
    "CORE_LANDMARKS",
    "FACE_SHAPES",
    "MEDIAPIPE_FACE_MESH_INDEX",
    "ClassificationInput",
    "FaceShapeResult",
    "JawTypeObservation",
    "LandmarkPoint",
    "RatioFeatures",
    "Tier1Landmarks",
    "Tier2Landmarks",
    "parse_named_landmarks",
]

__version__ = "0.1.0"
