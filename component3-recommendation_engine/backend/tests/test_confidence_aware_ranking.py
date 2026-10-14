"""Tests for optional ranking_mode=confidence_aware."""

from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.schemas.requests import PreferenceOptions, ProfileFeatures, RecommendationRequest
from app.schemas.responses import RuleContribution
from app.services.artifact_loader import ArtifactLoader
from app.services.confidence_aware_rules import (
    adjust_rule_evaluation,
    hybrid_score_with_rule_term,
)
from app.services.input_quality_service import FACIAL_CONFIDENCE_ATTRIBUTES
from app.services.recommendation_engine import RecommendationEngine


def _male() -> ProfileFeatures:
    return ProfileFeatures(
        face_length_ratio=1.1075061748845896,
        jaw_width_ratio=0.7981134693568468,
        upper_width_ratio=0.8836110941414184,
        lower_face_ratio=0.519768052719499,
        symmetry=0.8105352571132579,
        face_shape="round",
        jawline="soft",
        forehead="low",
        hairline="straight",
        gender="male",
    )


def _conf(**overrides: float) -> dict[str, float]:
    base = {attr: 1.0 for attr in FACIAL_CONFIDENCE_ATTRIBUTES}
    base.update(overrides)
    return base


def _engine() -> RecommendationEngine:
    settings = Settings()
    return RecommendationEngine(ArtifactLoader(settings).load(), settings)


def test_default_request_without_ranking_mode_is_standard(model_binaries_present):
    if not model_binaries_present:
        pytest.skip("models missing")
    engine = _engine()
    base = RecommendationRequest(
        profile=_male(),
        categories=["hair"],
        top_n=5,
        preferences=PreferenceOptions(include_beard=True),
    )
    assert base.ranking_mode == "standard"
    assert base.confidence_source == "unspecified"
    a = engine.recommend(base, "std-a")
    b = engine.recommend(
        RecommendationRequest(
            profile=_male(),
            categories=["hair"],
            top_n=5,
            preferences=PreferenceOptions(include_beard=True),
            ranking_mode="standard",
        ),
        "std-b",
    )
    assert a.ranking_mode == "standard"
    assert a.ranking_policy.policy_name == "hybrid_model_rank_rules_v1"
    assert [i.style_id for i in a.category_results[0].recommendations] == [
        i.style_id for i in b.category_results[0].recommendations
    ]
    assert [i.hybrid_score for i in a.category_results[0].recommendations] == [
        i.hybrid_score for i in b.category_results[0].recommendations
    ]
    for item in a.category_results[0].recommendations:
        assert item.confidence_adjusted_rule_score is None
        assert item.recommendation_support_score is None


def test_all_ones_reproduces_original_rule_score_and_ranking(model_binaries_present):
    if not model_binaries_present:
        pytest.skip("models missing")
    engine = _engine()
    profile = _male()
    standard = engine.recommend(
        RecommendationRequest(
            profile=profile,
            categories=["hair"],
            top_n=8,
            preferences=PreferenceOptions(include_beard=True),
            ranking_mode="standard",
        ),
        "ones-std",
    )
    aware = engine.recommend(
        RecommendationRequest(
            profile=profile,
            categories=["hair"],
            top_n=8,
            preferences=PreferenceOptions(include_beard=True),
            ranking_mode="confidence_aware",
            confidence_source="manual",
            attribute_confidence=_conf(),
        ),
        "ones-aware",
    )
    assert aware.ranking_policy.policy_name == "hybrid_confidence_adjusted_rules_v1"
    assert aware.ranking_policy.adjusts_rule_component_only is True
    assert aware.confidence_source == "manual"
    std_items = {i.style_id: i for i in standard.category_results[0].recommendations}
    for item in aware.category_results[0].recommendations:
        std = std_items[item.style_id]
        assert item.rule_compatibility_score == pytest.approx(
            std.rule_compatibility_score, abs=1e-6
        )
        assert item.confidence_adjusted_rule_score == pytest.approx(
            item.rule_compatibility_score, abs=1e-5
        )
        assert item.hybrid_score == pytest.approx(std.hybrid_score, abs=1e-5)
        assert item.recommendation_support_score == pytest.approx(
            item.rule_confidence_coverage * item.confidence_adjusted_rule_score,
            abs=1e-5,
        )
    assert [i.style_id for i in aware.category_results[0].recommendations] == [
        i.style_id for i in standard.category_results[0].recommendations
    ]


def test_lowering_one_confidence_changes_contributions(model_binaries_present):
    if not model_binaries_present:
        pytest.skip("models missing")
    engine = _engine()
    full = engine.recommend(
        RecommendationRequest(
            profile=_male(),
            categories=["hair"],
            top_n=3,
            ranking_mode="confidence_aware",
            confidence_source="manual",
            attribute_confidence=_conf(),
        ),
        "low-full",
    )
    low_shape = engine.recommend(
        RecommendationRequest(
            profile=_male(),
            categories=["hair"],
            top_n=3,
            ranking_mode="confidence_aware",
            confidence_source="manual",
            attribute_confidence=_conf(face_shape=0.1),
        ),
        "low-shape",
    )
    a = full.category_results[0].recommendations[0]
    b = next(
        i
        for i in low_shape.category_results[0].recommendations
        if i.style_id == a.style_id
    )
    contrib_a = {c.attribute: c for c in a.explanation.rule_contributions}
    contrib_b = {c.attribute: c for c in b.explanation.rule_contributions}
    assert contrib_a["face_shape"].confidence == 1.0
    assert contrib_b["face_shape"].confidence == 0.1
    assert contrib_b["face_shape"].effective_weight == pytest.approx(
        contrib_b["face_shape"].weight * 0.1, abs=1e-6
    )
    assert contrib_b["face_shape"].support_contribution == pytest.approx(
        contrib_b["face_shape"].effective_weight * contrib_b["face_shape"].similarity,
        abs=1e-6,
    )
    assert b.rule_confidence_coverage < a.rule_confidence_coverage
    assert b.recommendation_support_score != a.recommendation_support_score


def test_constructed_relative_confidence_can_change_ordering():
    """Deterministic constructed example — no live model / artifact changes."""
    weights = [0.05, 0.05, 0.05, 0.05, 0.40, 0.30, 0.05, 0.03, 0.02]
    attrs = list(FACIAL_CONFIDENCE_ATTRIBUTES)
    # Candidate X strong on face_shape, weak on jawline.
    sims_x = [0.5, 0.5, 0.5, 0.5, 1.0, 0.1, 0.5, 0.5, 0.5]
    # Candidate Y strong on jawline, weak on face_shape.
    sims_y = [0.5, 0.5, 0.5, 0.5, 0.1, 1.0, 0.5, 0.5, 0.5]
    # Shared model terms so only the rule term can flip order.
    norm_pred = {"X": 0.70, "Y": 0.70}
    rank_pct = {"X": 0.60, "Y": 0.60}
    hybrid_weights = {
        "predicted_compatibility": 0.50,
        "rank_percentile": 0.30,
        "rule_compatibility": 0.20,
    }

    def score(sims: list[float], conf: dict[str, float]) -> tuple[float, float, float]:
        contribs = [
            RuleContribution(
                attribute=attrs[i],
                contribution=weights[i] * sims[i],
                similarity=sims[i],
                weight=weights[i],
            )
            for i in range(9)
        ]
        original = sum(weights[i] * sims[i] for i in range(9))
        adj = adjust_rule_evaluation(
            weights=weights,
            facial_conf=conf,
            original_contributions=contribs,
            original_score=original,
        )
        hybrid = hybrid_score_with_rule_term(
            normalized_predicted_compatibility=0.70,
            rank_percentile=0.60,
            rule_term=adj["confidence_adjusted_rule_score"],
            weights=hybrid_weights,
        )
        return (
            adj["confidence_adjusted_rule_score"],
            adj["recommendation_support_score"],
            hybrid,
        )

    high_shape = _conf(face_shape=1.0, jawline=0.05)
    high_jaw = _conf(face_shape=0.05, jawline=1.0)

    ax, sx, hx = score(sims_x, high_shape)
    ay, sy, hy = score(sims_y, high_shape)
    assert hx > hy
    assert ax > ay

    bx, _, hx2 = score(sims_x, high_jaw)
    by, _, hy2 = score(sims_y, high_jaw)
    assert hy2 > hx2
    assert by > bx
    # Ordering by hybrid then style_id would flip X vs Y.
    order_shape = sorted(
        [("X", hx), ("Y", hy)], key=lambda t: (-t[1], t[0])
    )
    order_jaw = sorted(
        [("X", hx2), ("Y", hy2)], key=lambda t: (-t[1], t[0])
    )
    assert [c[0] for c in order_shape] != [c[0] for c in order_jaw]


def test_uniform_scaling_preserves_adjusted_changes_support(model_binaries_present):
    if not model_binaries_present:
        pytest.skip("models missing")
    engine = _engine()
    profile = _male()
    full = engine.recommend(
        RecommendationRequest(
            profile=profile,
            categories=["hair"],
            top_n=5,
            ranking_mode="confidence_aware",
            confidence_source="manual",
            attribute_confidence=_conf(),
        ),
        "scale-1",
    )
    scaled = engine.recommend(
        RecommendationRequest(
            profile=profile,
            categories=["hair"],
            top_n=5,
            ranking_mode="confidence_aware",
            confidence_source="manual",
            attribute_confidence=_conf(**{a: 0.25 for a in FACIAL_CONFIDENCE_ATTRIBUTES}),
        ),
        "scale-025",
    )
    for a, b in zip(
        full.category_results[0].recommendations,
        scaled.category_results[0].recommendations,
        strict=True,
    ):
        assert a.style_id == b.style_id
        assert a.confidence_adjusted_rule_score == pytest.approx(
            b.confidence_adjusted_rule_score, abs=1e-5
        )
        assert b.recommendation_support_score == pytest.approx(
            a.recommendation_support_score * 0.25, abs=1e-5
        )
        assert b.rule_confidence_coverage == pytest.approx(
            a.rule_confidence_coverage * 0.25, abs=1e-5
        )
    assert scaled.input_quality.input_quality_score == pytest.approx(0.25, abs=1e-6)
    assert scaled.input_quality.assessment == "low"
    assert scaled.category_results[0].recommendation_disposition == "review_required"


def test_all_zero_confidence_fallback(model_binaries_present):
    if not model_binaries_present:
        pytest.skip("models missing")
    engine = _engine()
    profile = _male()
    standard = engine.recommend(
        RecommendationRequest(
            profile=profile,
            categories=["hair"],
            top_n=5,
            ranking_mode="standard",
        ),
        "zero-std",
    )
    zeros = {attr: 0.0 for attr in FACIAL_CONFIDENCE_ATTRIBUTES}
    fallback = engine.recommend(
        RecommendationRequest(
            profile=profile,
            categories=["hair"],
            top_n=5,
            ranking_mode="confidence_aware",
            confidence_source="manual",
            attribute_confidence=zeros,
        ),
        "zero-fb",
    )
    assert fallback.ranking_policy.fallback_applied is True
    assert fallback.ranking_policy.active_ranking_mode == "standard"
    assert fallback.ranking_policy.policy_name == "hybrid_model_rank_rules_v1"
    assert "zero" in (fallback.ranking_policy.fallback_reason or "").lower()
    assert fallback.category_results[0].recommendation_disposition == "review_required"
    assert "confidence_aware_zero_coverage_fallback" in (
        fallback.category_results[0].disposition_reasons or []
    )
    assert [i.style_id for i in fallback.category_results[0].recommendations] == [
        i.style_id for i in standard.category_results[0].recommendations
    ]
    for item in fallback.category_results[0].recommendations:
        assert item.recommendation_support_score == 0.0
        assert item.confidence_adjusted_rule_score is None
        assert item.rule_confidence_coverage == 0.0
        assert item.hybrid_score == pytest.approx(
            next(
                s.hybrid_score
                for s in standard.category_results[0].recommendations
                if s.style_id == item.style_id
            ),
            abs=1e-5,
        )
    assert fallback.recommendation_confidence is None
    assert fallback.recommendation_confidence_status == "not_calibrated"


def test_partial_map_rejected_only_in_confidence_aware_mode():
    partial = {"face_shape": 0.9, "jawline": 0.8}
    # standard accepts partial
    RecommendationRequest(
        profile=_male(),
        categories=["hair"],
        ranking_mode="standard",
        attribute_confidence=partial,
    )
    with pytest.raises(ValidationError) as exc:
        RecommendationRequest(
            profile=_male(),
            categories=["hair"],
            ranking_mode="confidence_aware",
            attribute_confidence=partial,
        )
    assert "nine facial" in str(exc.value).lower() or "Missing" in str(exc.value)

    with pytest.raises(ValidationError):
        RecommendationRequest(
            profile=_male(),
            categories=["hair"],
            ranking_mode="confidence_aware",
            attribute_confidence=None,
        )


def test_invalid_numbers_and_unknown_attributes_rejected():
    complete = _conf()
    with pytest.raises(ValidationError):
        RecommendationRequest(
            profile=_male(),
            ranking_mode="confidence_aware",
            attribute_confidence={**complete, "face_shape": float("nan")},
        )
    with pytest.raises(ValidationError):
        RecommendationRequest(
            profile=_male(),
            ranking_mode="confidence_aware",
            attribute_confidence={**complete, "jawline": math.inf},
        )
    with pytest.raises(ValidationError):
        RecommendationRequest(
            profile=_male(),
            ranking_mode="confidence_aware",
            attribute_confidence={**complete, "skin_tone": 0.5},
        )
    with pytest.raises(ValidationError):
        RecommendationRequest(
            profile=_male(),
            ranking_mode="confidence_aware",
            attribute_confidence={**complete, "symmetry": -0.1},
        )


def test_support_equals_sum_of_support_contributions(model_binaries_present):
    if not model_binaries_present:
        pytest.skip("models missing")
    engine = _engine()
    response = engine.recommend(
        RecommendationRequest(
            profile=_male(),
            categories=["hair"],
            top_n=3,
            ranking_mode="confidence_aware",
            confidence_source="manual",
            attribute_confidence=_conf(face_shape=0.4, jawline=0.7),
        ),
        "sum-support",
    )
    for item in response.category_results[0].recommendations:
        contrib_sum = sum(
            c.support_contribution
            for c in item.explanation.rule_contributions
            if c.support_contribution is not None
        )
        assert item.recommendation_support_score == pytest.approx(contrib_sum, abs=1e-5)
        assert len(item.explanation.rule_contributions) == 9


def test_gender_confidence_excluded_from_confidence_aware_weights(model_binaries_present):
    if not model_binaries_present:
        pytest.skip("models missing")
    engine = _engine()
    without = engine.recommend(
        RecommendationRequest(
            profile=_male(),
            categories=["hair"],
            top_n=3,
            ranking_mode="confidence_aware",
            confidence_source="manual",
            attribute_confidence=_conf(),
        ),
        "nog",
    )
    with_gender = engine.recommend(
        RecommendationRequest(
            profile=_male(),
            categories=["hair"],
            top_n=3,
            ranking_mode="confidence_aware",
            confidence_source="manual",
            attribute_confidence={**_conf(), "gender": 0.01},
        ),
        "withg",
    )
    for a, b in zip(
        without.category_results[0].recommendations,
        with_gender.category_results[0].recommendations,
        strict=True,
    ):
        assert a.style_id == b.style_id
        assert a.hybrid_score == pytest.approx(b.hybrid_score, abs=1e-9)
        assert a.confidence_adjusted_rule_score == pytest.approx(
            b.confidence_adjusted_rule_score, abs=1e-9
        )


def test_confidence_source_does_not_change_scores(model_binaries_present):
    if not model_binaries_present:
        pytest.skip("models missing")
    engine = _engine()
    conf = _conf(face_shape=0.5)
    a = engine.recommend(
        RecommendationRequest(
            profile=_male(),
            categories=["hair"],
            top_n=3,
            ranking_mode="confidence_aware",
            confidence_source="manual",
            attribute_confidence=conf,
        ),
        "src-m",
    )
    b = engine.recommend(
        RecommendationRequest(
            profile=_male(),
            categories=["hair"],
            top_n=3,
            ranking_mode="confidence_aware",
            confidence_source="upstream",
            attribute_confidence=conf,
        ),
        "src-u",
    )
    assert a.confidence_source != b.confidence_source
    assert [i.hybrid_score for i in a.category_results[0].recommendations] == [
        i.hybrid_score for i in b.category_results[0].recommendations
    ]
