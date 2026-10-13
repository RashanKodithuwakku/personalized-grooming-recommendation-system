"""Confidence-adjusted weighted rule scoring for optional ranking_mode.

Uses original category weights and per-attribute similarities. Adjusts only
the rule component of hybrid ranking. Not calibrated recommendation confidence.
"""

from __future__ import annotations

from typing import Any

from app.schemas.responses import RuleContribution
from app.services.compatibility_rules import EXPECTED_TERM_ORDER
from app.services.input_quality_service import FACIAL_CONFIDENCE_ATTRIBUTES

assert tuple(FACIAL_CONFIDENCE_ATTRIBUTES) == EXPECTED_TERM_ORDER


def facial_confidence_vector(
    attribute_confidence: dict[str, float],
) -> dict[str, float]:
    """Return the nine facial confidences; gender is excluded."""
    return {attr: float(attribute_confidence[attr]) for attr in FACIAL_CONFIDENCE_ATTRIBUTES}


def compute_rule_confidence_coverage(
    weights: list[float],
    facial_conf: dict[str, float],
) -> float:
    """A = sum(w_i * c_i) over the nine facial attributes."""
    total = 0.0
    for idx, attr in enumerate(FACIAL_CONFIDENCE_ATTRIBUTES):
        total += float(weights[idx]) * float(facial_conf[attr])
    return round(total, 6)


def adjust_rule_evaluation(
    *,
    weights: list[float],
    facial_conf: dict[str, float],
    original_contributions: list[RuleContribution],
    original_score: float | None,
) -> dict[str, Any]:
    """Compute confidence-adjusted rule scores for one candidate.

    A = sum(w_i * c_i)
    S_j = sum(w_i * c_i * s_ij)
    confidence_adjusted_rule_score = S_j / A when A > 0, else null.
    """
    if len(weights) != len(FACIAL_CONFIDENCE_ATTRIBUTES):
        raise ValueError("weights length must equal nine facial attributes")

    sim_by_attr = {
        item.attribute: float(item.similarity)
        for item in original_contributions
        if item.similarity is not None
    }
    for attr in FACIAL_CONFIDENCE_ATTRIBUTES:
        if attr not in sim_by_attr:
            raise ValueError(f"Missing similarity for attribute={attr}")

    coverage = 0.0
    support = 0.0
    enriched: list[RuleContribution] = []

    for idx, attr in enumerate(FACIAL_CONFIDENCE_ATTRIBUTES):
        weight = float(weights[idx])
        confidence = float(facial_conf[attr])
        similarity = float(sim_by_attr[attr])
        effective_weight = weight * confidence
        support_contribution = effective_weight * similarity
        coverage += effective_weight
        support += support_contribution
        original = next(
            (c for c in original_contributions if c.attribute == attr),
            None,
        )
        enriched.append(
            RuleContribution(
                attribute=attr,
                contribution=round(weight * similarity, 6),
                similarity=round(similarity, 6),
                weight=weight,
                confidence=confidence,
                effective_weight=round(effective_weight, 6),
                support_contribution=round(support_contribution, 6),
                detail=(
                    (original.detail + "; ") if original and original.detail else ""
                )
                + (
                    f"confidence={confidence:.6f}; "
                    f"effective_weight=w*c; "
                    f"support_contribution=w*c*s"
                ),
            )
        )

    coverage_r = round(coverage, 6)
    support_r = round(support, 6)
    if coverage_r > 0.0:
        adjusted = round(support / coverage, 6)
    else:
        adjusted = None

    return {
        "rule_confidence_coverage": coverage_r,
        "recommendation_support_score": support_r,
        "confidence_adjusted_rule_score": adjusted,
        "rule_compatibility_score": original_score,
        "contributions": enriched,
        "support_equals_coverage_times_adjusted": (
            adjusted is None
            or abs(support_r - round(coverage_r * adjusted, 6)) < 1e-5
        ),
    }


def hybrid_score_with_rule_term(
    *,
    normalized_predicted_compatibility: float,
    rank_percentile: float,
    rule_term: float | None,
    weights: dict[str, float],
) -> float:
    """Provisional hybrid mix; rule_term may be original or confidence-adjusted."""
    score = (
        weights.get("predicted_compatibility", 0.0)
        * float(normalized_predicted_compatibility)
        + weights.get("rank_percentile", 0.0) * float(rank_percentile)
    )
    if rule_term is not None:
        score += weights.get("rule_compatibility", 0.0) * float(rule_term)
    return float(score)
