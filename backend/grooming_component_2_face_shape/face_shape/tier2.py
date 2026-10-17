"""Tier 2 modifiers on top of the three core indices.

TFI can raise the oblong length membership when trichion is present.
Jaw type breaks the JMI 81-85 tie: angular supports square, rounded supports
whichever of round or oval is already stronger. Tapered leaves the scores
unchanged. Symmetry and balance are not computed here.
"""

from dataclasses import dataclass

from face_shape.contracts import (
    FACE_SHAPES,
    AppliedModifier,
    ClassificationInput,
    FaceShapeName,
    FaceShapeResult,
    JawTypeName,
)
from face_shape.geometry import prepare_landmarks
from face_shape.indices import measure_ratios
from face_shape.membership import confidence_vector, geometric_mean, tier1_scores, trapezoid_membership
from face_shape.thresholds import CLASS_TRAPEZOIDS, JAW_TIE_BAND, TFI_OBLONG
from face_shape.tier1 import select_face_type


@dataclass(frozen=True)
class JawRule:
    suppress: tuple[FaceShapeName, ...] = ()
    boost: tuple[FaceShapeName, ...] = ()
    boost_leader: tuple[FaceShapeName, ...] = ()


JAW_RULES: dict[JawTypeName, JawRule] = {
    "angular": JawRule(suppress=("round", "oval"), boost=("square",)),
    "rounded": JawRule(suppress=("square",), boost_leader=("round", "oval")),
    "tapered": JawRule(),
}


def classify_face(sample: ClassificationInput) -> FaceShapeResult:
    """Identify the face shape through tier 1 and the optional modifiers."""

    ratios = measure_ratios(prepare_landmarks(sample))
    scores = tier1_scores(ratios)
    scores, modifiers = apply_modifiers(scores, ratios.mfi, ratios.jmi, ratios.fzi, ratios.tfi, sample)
    return FaceShapeResult(
        face_type=select_face_type(scores),
        face_type_confidence=confidence_vector(scores),
        ratios=ratios,
        modifiers_applied=modifiers,
        jaw_type=sample.jaw_type,
    )


def apply_modifiers(
    scores: dict[FaceShapeName, float],
    mfi: float | None,
    jmi: float | None,
    fzi: float | None,
    tfi: float | None,
    sample: ClassificationInput,
) -> tuple[dict[FaceShapeName, float], list[AppliedModifier]]:
    if mfi is None or jmi is None or fzi is None:
        raise ValueError("modifiers require mfi, jmi, and fzi")

    adjusted = dict(scores)
    modifiers: list[AppliedModifier] = []
    adjusted, tfi_applied = apply_tfi(adjusted, mfi, jmi, fzi, tfi)
    if tfi_applied:
        modifiers.append("tfi")
    adjusted, jaw_applied = apply_jaw(adjusted, jmi, sample)
    if jaw_applied:
        modifiers.append("jaw_type")
    return adjusted, modifiers


def apply_tfi(
    scores: dict[FaceShapeName, float],
    mfi: float,
    jmi: float,
    fzi: float,
    tfi: float | None,
) -> tuple[dict[FaceShapeName, float], bool]:
    length_from_mfi = trapezoid_membership(mfi, CLASS_TRAPEZOIDS["oblong"]["mfi"])
    if tfi is None:
        return scores, False

    length = max(length_from_mfi, trapezoid_membership(tfi, TFI_OBLONG))
    if length == length_from_mfi:
        return scores, False

    updated = dict(scores)
    updated["oblong"] = geometric_mean(
        [
            length,
            trapezoid_membership(jmi, CLASS_TRAPEZOIDS["oblong"]["jmi"]),
            trapezoid_membership(fzi, CLASS_TRAPEZOIDS["oblong"]["fzi"]),
        ]
    )
    return updated, True


def apply_jaw(
    scores: dict[FaceShapeName, float],
    jmi: float,
    sample: ClassificationInput,
) -> tuple[dict[FaceShapeName, float], bool]:
    jaw = sample.jaw_type
    if jaw is None:
        return scores, False

    weight = trapezoid_membership(jmi, JAW_TIE_BAND) * jaw.confidence
    rule = JAW_RULES[jaw.label]
    if weight <= 0.0 or not (rule.suppress or rule.boost or rule.boost_leader):
        return scores, False

    updated = dict(scores)
    for name in rule.suppress:
        updated[name] = updated[name] * (1.0 - weight)
    for name in rule.boost:
        updated[name] = _lift(updated[name], weight)
    if rule.boost_leader:
        leader = max(rule.boost_leader, key=lambda name: (updated[name], -FACE_SHAPES.index(name)))
        updated[leader] = _lift(updated[leader], weight)
    return updated, updated != scores


def _lift(score: float, weight: float) -> float:
    return score + weight * (1.0 - score)
