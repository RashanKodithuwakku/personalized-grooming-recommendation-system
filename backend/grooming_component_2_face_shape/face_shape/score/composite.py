"""Grooming suitability from shape, symmetry, and balance.

Proportion is not used. Missing symmetry or balance drops that term and the
remaining weights are renormalised so the index stays on 0-100.
"""

from dataclasses import dataclass

from face_shape.contracts import FACE_SHAPES, FaceShapeName


# Fixed display weights. Proportion is not a term.
# 0.50 shape + 0.25 symmetry + 0.25 balance.
SHAPE_WEIGHT = 0.50
SYMMETRY_WEIGHT = 0.25
BALANCE_WEIGHT = 0.25


# compatibility_score is the 0-1 weighted value.
# grooming_suitability_index is that value times 100, for the headline.
@dataclass(frozen=True)
class CompositeResult:
    shape_score: float | None
    compatibility_score: float | None
    grooming_suitability_index: float | None
    weights: dict[str, float]


# Shape term is the winning class confidence, not a blend of all six.
def shape_confidence(vector: dict[FaceShapeName, float] | None) -> float | None:
    if not vector:
        return None
    return max(vector[name] for name in FACE_SHAPES if name in vector)


# Drop a missing term and divide by the weight that remains, so a
# missing symmetry score does not pull the index down by 0.25.
def score_composite(
    shape_score: float | None,
    symmetry_score: float | None,
    balance_score: float | None,
) -> CompositeResult:
    parts: list[tuple[str, float, float]] = []
    if shape_score is not None:
        parts.append(("shape", SHAPE_WEIGHT, _unit(shape_score)))
    if symmetry_score is not None:
        parts.append(("symmetry", SYMMETRY_WEIGHT, _unit(symmetry_score)))
    if balance_score is not None:
        parts.append(("balance", BALANCE_WEIGHT, _unit(balance_score)))

    if not parts:
        return CompositeResult(shape_score, None, None, {})

    total_weight = sum(weight for _, weight, _ in parts)
    weighted = sum(weight * value for _, weight, value in parts) / total_weight
    index = round(100.0 * weighted, 1)
    return CompositeResult(
        shape_score=shape_score,
        compatibility_score=weighted,
        grooming_suitability_index=index,
        weights={name: weight / total_weight for name, weight, _ in parts},
    )


# Clamp one input onto 0-1 before it enters the weighted sum.
def _unit(value: float) -> float:
    return max(0.0, min(1.0, value))
