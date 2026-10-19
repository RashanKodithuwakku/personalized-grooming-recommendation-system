"""Tier 2 modifiers on top of the three core indices.

TFI can raise oblong membership when trichion is present, and slightly
lowers Oval when TFI sits in the oblong core. Jaw type breaks the JMI 83
Square vs Round/Oval tie: angular raises Square, rounded raises Round.
Tapered leaves the scores unchanged.
"""

from dataclasses import dataclass

from face_shape.contracts import (
    AppliedModifier,
    ClassificationInput,
    FaceShapeName,
    FaceShapeResult,
    JawTypeName,
)
from face_shape.geometry import prepare_landmarks
from face_shape.indices import measure_ratios
from face_shape.membership import confidence_vector, tier1_scores, trapezoid_membership
from face_shape.rules import hard_threshold_label, morphological_class
from face_shape.thresholds import JAW_TIE_BAND, OVAL_TFI_PENALTY, TFI_OBLONG
from face_shape.tier1 import select_face_type


@dataclass(frozen=True)
class JawRule:
    suppress: tuple[FaceShapeName, ...] = ()
    boost: tuple[FaceShapeName, ...] = ()


JAW_RULES: dict[JawTypeName, JawRule] = {
    "angular": JawRule(suppress=("round", "oval"), boost=("square",)),
    "rounded": JawRule(suppress=("square",), boost=("round",)),
    "tapered": JawRule(),
}


def classify_face(sample: ClassificationInput) -> FaceShapeResult:
    """Identify the face shape through tier 1 and the optional modifiers."""

    ratios = measure_ratios(prepare_landmarks(sample))
    notes: list[str] = []
    scores = tier1_scores(ratios)
    if ratios.fzi is None:
        notes.append("missing_frontotemporale")
        if ratios.jmi is not None and ratios.jmi < 75.0:
            notes.append("narrow_jaw_unresolved")
    scores, modifiers = apply_modifiers(scores, ratios.tfi, ratios.jmi, sample)
    return FaceShapeResult(
        face_type=select_face_type(scores),
        face_type_confidence=confidence_vector(scores),
        ratios=ratios,
        modifiers_applied=modifiers,
        jaw_type=sample.jaw_type,
        face_shape_class=morphological_class(ratios.mfi) if ratios.mfi is not None else None,
        baseline_label=hard_threshold_label(ratios, notes),
        processing_notes=notes,
    )


def apply_modifiers(
    scores: dict[FaceShapeName, float],
    tfi: float | None,
    jmi: float | None,
    sample: ClassificationInput,
) -> tuple[dict[FaceShapeName, float], list[AppliedModifier]]:
    adjusted = dict(scores)
    modifiers: list[AppliedModifier] = []
    adjusted, tfi_applied = apply_tfi(adjusted, tfi)
    if tfi_applied:
        modifiers.append("tfi")
    if jmi is not None:
        adjusted, jaw_applied = apply_jaw(adjusted, jmi, sample)
        if jaw_applied:
            modifiers.append("jaw_type")
    return adjusted, modifiers


def apply_tfi(
    scores: dict[FaceShapeName, float],
    tfi: float | None,
) -> tuple[dict[FaceShapeName, float], bool]:
    if tfi is None:
        return scores, False
    mu_tfi = trapezoid_membership(tfi, TFI_OBLONG)
    if mu_tfi <= 0.0:
        return scores, False
    updated = dict(scores)
    updated["oblong"] = max(updated["oblong"], mu_tfi)
    updated["oval"] *= 1.0 - OVAL_TFI_PENALTY * mu_tfi
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
    if weight <= 0.0 or not (rule.suppress or rule.boost):
        return scores, False

    updated = dict(scores)
    for name in rule.suppress:
        updated[name] = updated[name] * (1.0 - weight)
    for name in rule.boost:
        updated[name] = _lift(updated[name], weight)
    return updated, updated != scores


def _lift(score: float, weight: float) -> float:
    return score + weight * (1.0 - score)
