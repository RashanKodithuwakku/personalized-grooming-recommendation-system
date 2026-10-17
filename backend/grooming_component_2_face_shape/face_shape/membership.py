"""Trapezoidal membership, geometric-mean class scores, and confidence."""

import math

from face_shape.contracts import FACE_SHAPES, FaceShapeName, RatioFeatures
from face_shape.thresholds import CLASS_TRAPEZOIDS, Trapezoid


def trapezoid_membership(value: float, interval: Trapezoid) -> float:
    """Map one measurement onto the unit interval."""

    if interval.a is not None and value <= interval.a:
        return 0.0
    if interval.d is not None and value >= interval.d:
        return 0.0
    if _on_plateau(value, interval):
        return 1.0
    if interval.a is not None and interval.b is not None and interval.a < value < interval.b:
        return (value - interval.a) / (interval.b - interval.a)
    if interval.c is not None and interval.d is not None and interval.c < value < interval.d:
        return (interval.d - value) / (interval.d - interval.c)
    return 0.0


def geometric_mean(values: list[float]) -> float:
    """Conjunction of feature memberships. A zero feature blocks the class."""

    if not values or any(value <= 0.0 for value in values):
        return 0.0
    return math.exp(sum(math.log(value) for value in values) / len(values))


def tier1_scores(ratios: RatioFeatures) -> dict[FaceShapeName, float]:
    """Score each class from MFI, JMI, and FZI only."""

    if ratios.mfi is None or ratios.jmi is None or ratios.fzi is None:
        raise ValueError("tier-1 scores require mfi, jmi, and fzi")

    observed = {"mfi": ratios.mfi, "jmi": ratios.jmi, "fzi": ratios.fzi}
    scores: dict[FaceShapeName, float] = {}
    for name in FACE_SHAPES:
        memberships = [
            trapezoid_membership(observed[feature], interval)
            for feature, interval in CLASS_TRAPEZOIDS[name].items()
        ]
        scores[name] = geometric_mean(memberships)
    return scores


def confidence_vector(scores: dict[FaceShapeName, float]) -> dict[FaceShapeName, float]:
    """Normalise class scores so the six values sum to 1 when any score is positive."""

    total = sum(scores[name] for name in FACE_SHAPES)
    if total <= 0.0:
        return {name: 0.0 for name in FACE_SHAPES}
    return {name: scores[name] / total for name in FACE_SHAPES}


def _on_plateau(value: float, interval: Trapezoid) -> bool:
    left_open = interval.b is None or value >= interval.b
    right_open = interval.c is None or value <= interval.c
    return left_open and right_open
