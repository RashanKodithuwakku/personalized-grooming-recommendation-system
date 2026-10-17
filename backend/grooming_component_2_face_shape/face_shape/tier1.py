"""Tier 1 face-shape decision from MFI, JMI, and FZI.

Trichion and jaw type are carried on the result, but they do not change the
class scores. Those modifiers belong to the second tier.
"""

from face_shape.contracts import FACE_SHAPES, ClassificationInput, FaceShapeName, FaceShapeResult
from face_shape.geometry import prepare_landmarks
from face_shape.indices import measure_ratios
from face_shape.membership import confidence_vector, tier1_scores


def classify_tier1(sample: ClassificationInput) -> FaceShapeResult:
    """Classify one Component 1 sample with the three core indices."""

    ratios = measure_ratios(prepare_landmarks(sample))
    scores = tier1_scores(ratios)
    return FaceShapeResult(
        face_type=select_face_type(scores),
        face_type_confidence=confidence_vector(scores),
        ratios=ratios,
        modifiers_applied=[],
        jaw_type=sample.jaw_type,
    )


def select_face_type(scores: dict[FaceShapeName, float]) -> FaceShapeName:
    """Pick the strongest class. Equal scores follow the fixed class order."""

    return max(FACE_SHAPES, key=lambda name: (scores[name], -FACE_SHAPES.index(name)))
