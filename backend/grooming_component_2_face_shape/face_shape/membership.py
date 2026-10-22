"""Trapezoidal membership, geometric-mean class scores, and confidence."""

import math

from face_shape.contracts import FACE_SHAPES, FaceShapeName, RatioFeatures
from face_shape.thresholds import CLASS_TRAPEZOIDS, Trapezoid


def trapezoid_membership(value: float, interval: Trapezoid) -> float:
    """Map one measurement onto the unit interval."""

    # Outside the feet the class gets no credit. On the plateau it gets
    # full credit. On a ramp the credit rises or falls linearly.
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
    """Conjunction of available feature memberships.

    Invalid features are omitted by the caller. A remaining zero still blocks
    the class.
    """

    # One failed feature (membership 0) rejects the whole class.
    # The mean is taken in log space so every feature must agree.
    if not values or any(value <= 0.0 for value in values):
        return 0.0
    return math.exp(sum(math.log(value) for value in values) / len(values))


def tier1_scores(ratios: RatioFeatures) -> dict[FaceShapeName, float]:
    """Score each class from MFI, JMI, and FZI when those values exist."""

    if ratios.mfi is None or ratios.jmi is None:
        raise ValueError("tier-1 scores require mfi and jmi")

    # FZI is included only when both forehead points exist. Heart and
    # diamond cannot be separated without it, so both stay at zero.
    observed: dict[str, float] = {"mfi": ratios.mfi, "jmi": ratios.jmi}
    fzi_valid = ratios.fzi is not None
    if fzi_valid:
        observed["fzi"] = ratios.fzi

    scores: dict[FaceShapeName, float] = {}
    for name in FACE_SHAPES:
        memberships = [
            trapezoid_membership(observed[feature], interval)
            for feature, interval in CLASS_TRAPEZOIDS[name].items()
            if feature in observed
        ]
        scores[name] = geometric_mean(memberships) if memberships else 0.0

    if fzi_valid:
        scores["oval"] *= oval_fzi_factor(ratios.jmi, ratios.fzi)
        scores["square"] *= square_fzi_factor(ratios.jmi, ratios.fzi)
        scores["heart"] *= heart_relation(ratios.jmi, ratios.fzi)
        scores["diamond"] *= diamond_relation(ratios.jmi, ratios.fzi)
    else:
        scores["heart"] = 0.0
        scores["diamond"] = 0.0
    return scores


def oval_fzi_factor(jmi: float, fzi: float) -> float:
    """Full credit when FZI >= JMI - 3, then a six-point linear drop."""

    # Oval expects the forehead to be at least about as wide as the jaw.
    gap = (jmi - 3.0) - fzi
    if gap <= 0.0:
        return 1.0
    return max(0.0, 1.0 - gap / 6.0)


def square_fzi_factor(jmi: float, fzi: float) -> float:
    """Lower Square when the forehead is much narrower than the jaw."""

    # A much narrower forehead pulls Square down, but not below 0.4,
    # so a clearly wide jaw is not wiped out by forehead alone.
    if fzi >= jmi - 6.0:
        return 1.0
    deficit = (jmi - 6.0) - fzi
    return max(0.4, 1.0 - deficit / 10.0)


def heart_relation(jmi: float, fzi: float) -> float:
    """Heart needs FZI >= 75 and FZI >= JMI + 6."""

    # Full heart credit needs a broad forehead well above the jaw.
    # The two-point band between +4 and +6 is the soft transition.
    if fzi < 75.0:
        return 0.0
    delta = fzi - jmi
    if delta >= 6.0:
        return 1.0
    if delta <= 4.0:
        return 0.0
    return (delta - 4.0) / 2.0


def diamond_relation(jmi: float, fzi: float) -> float:
    """Diamond takes the leftover narrow-jaw cases that are not Heart."""

    # Narrow forehead on a narrow jaw is diamond. Where heart membership
    # rises, diamond falls by the same amount.
    if fzi < 75.0:
        return 1.0
    return 1.0 - heart_relation(jmi, fzi)


def confidence_vector(scores: dict[FaceShapeName, float]) -> dict[FaceShapeName, float]:
    """Normalise class scores so the six values sum to 1 when any score is positive."""

    # L1 normalisation. If every class scored zero, the vector stays zero
    # rather than being divided by zero.
    total = sum(scores[name] for name in FACE_SHAPES)
    if total <= 0.0:
        return {name: 0.0 for name in FACE_SHAPES}
    return {name: scores[name] / total for name in FACE_SHAPES}


# True when the value sits between the two shoulders. An open side
# (missing shoulder) stays inside all the way to that infinity.
def _on_plateau(value: float, interval: Trapezoid) -> bool:
    left_open = interval.b is None or value >= interval.b
    right_open = interval.c is None or value <= interval.c
    return left_open and right_open
