"""Focused tests for confidence-aware input-quality flagging."""

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.schemas.requests import PreferenceOptions, ProfileFeatures, RecommendationRequest
from app.services.artifact_loader import ArtifactLoader
from app.services.input_quality_service import (
    FACIAL_CONFIDENCE_ATTRIBUTES,
    InputQualityService,
)
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


def _service(weights=None) -> InputQualityService:
    return InputQualityService(
        caution_threshold=0.60,
        low_confidence_attribute_threshold=0.50,
        min_coverage=1.0,
        category_rule_weights=weights
        or {
            "hair": [0.16, 0.08, 0.08, 0.05, 0.22, 0.08, 0.12, 0.14, 0.07],
        },
    )


def test_no_confidence_review_required_and_aliases():
    payload = _service().evaluate(None, ["hair"])
    assert payload["confidence_status"] == "not_provided"
    assert payload["assessment"] == "unknown"
    assert payload["input_quality_score"] is None
    assert payload["confidence_coverage"] == 0.0
    assert payload["confidence_weight_coverage"] == 0.0
    assert payload["confidence_attributes_missing"] == sorted(
        FACIAL_CONFIDENCE_ATTRIBUTES
    )
    assert payload["attributes_missing"] == payload["confidence_attributes_missing"]
    assert payload["attributes_provided"] == payload["confidence_attributes_provided"]
    assert payload["coverage"] == payload["confidence_coverage"]
    assert payload["caution_flag"] is True
    assert "confidence_not_provided" in payload["caution_reasons"]
    disp = _service().disposition_for_category(payload["category_input_quality"]["hair"])
    assert disp["recommendation_disposition"] == "review_required"


def test_partial_confidence_lists_missing_and_observed_only_aggregate():
    conf = {"face_shape": 0.95, "jawline": 0.9, "symmetry": 0.8}
    payload = _service().evaluate(conf, ["hair"])
    assert payload["confidence_status"] == "partial"
    assert payload["assessment"] == "insufficient_coverage"
    assert "forehead" in payload["confidence_attributes_missing"]
    assert "gender" not in payload["confidence_attributes_missing"]
    assert payload["input_quality_score"] == pytest.approx(
        (0.95 + 0.9 + 0.8) / 3.0
    )
    assert payload["caution_flag"] is True
    hair = payload["category_input_quality"]["hair"]
    assert hair["confidence_status"] == "partial"
    assert hair["confidence_attributes_missing"]
    # Category score uses only supplied weights.
    w = hair["rule_weights_used"]
    num = (
        w["face_shape"] * 0.95
        + w["jawline"] * 0.9
        + w["symmetry"] * 0.8
    )
    den = w["face_shape"] + w["jawline"] + w["symmetry"]
    assert hair["input_quality_score"] == pytest.approx(num / den)


def test_complete_high_confidence_standard():
    conf = {attr: 0.95 for attr in FACIAL_CONFIDENCE_ATTRIBUTES}
    payload = _service().evaluate(conf, ["hair"])
    assert payload["confidence_status"] == "complete"
    assert payload["assessment"] == "adequate"
    assert payload["caution_flag"] is False
    disp = _service().disposition_for_category(payload["category_input_quality"]["hair"])
    assert disp["recommendation_disposition"] == "standard"


def test_complete_low_confidence_review_required():
    conf = {attr: 0.2 for attr in FACIAL_CONFIDENCE_ATTRIBUTES}
    payload = _service().evaluate(conf, ["hair"])
    assert payload["confidence_status"] == "complete"
    assert payload["assessment"] == "low"
    assert payload["caution_flag"] is True
    disp = _service().disposition_for_category(payload["category_input_quality"]["hair"])
    assert disp["recommendation_disposition"] == "review_required"


def test_low_confidence_high_weight_attribute_affects_category_score():
    weights = {
        "hair": [0.01, 0.01, 0.01, 0.01, 0.90, 0.01, 0.01, 0.02, 0.02],
    }
    conf = {attr: 0.95 for attr in FACIAL_CONFIDENCE_ATTRIBUTES}
    conf["face_shape"] = 0.05  # high weight index 4
    hair = _service(weights).evaluate(conf, ["hair"])["category_input_quality"]["hair"]
    assert hair["input_quality_score"] < 0.60
    assert hair["assessment"] == "low"


def test_gender_confidence_alone_does_not_count_as_facial_coverage():
    payload = _service().evaluate({"gender": 0.99}, ["hair"])
    assert payload["confidence_status"] == "not_provided"
    assert payload["confidence_coverage"] == 0.0
    assert payload["gender_confidence_supplied"] is True
    assert payload["gender_excluded_from_facial_aggregate"] is True
    assert payload["input_quality_score"] is None


def test_engine_confidence_does_not_change_hybrid_ordering(model_binaries_present):
    if not model_binaries_present:
        pytest.skip("models missing")
    settings = Settings()
    bundle = ArtifactLoader(settings).load()
    engine = RecommendationEngine(bundle, settings)
    profile = _male()
    base = RecommendationRequest(
        profile=profile,
        categories=["hair"],
        top_n=5,
        preferences=PreferenceOptions(include_beard=True),
    )
    with_conf = RecommendationRequest(
        profile=profile,
        categories=["hair"],
        top_n=5,
        preferences=PreferenceOptions(include_beard=True),
        attribute_confidence={attr: 0.2 for attr in FACIAL_CONFIDENCE_ATTRIBUTES},
    )
    a = engine.recommend(base, "a")
    b = engine.recommend(with_conf, "b")
    a_items = a.category_results[0].recommendations
    b_items = b.category_results[0].recommendations
    assert [i.style_id for i in a_items] == [i.style_id for i in b_items]
    assert [i.hybrid_score for i in a_items] == [i.hybrid_score for i in b_items]
    assert a.recommendation_confidence is None
    assert b.recommendation_confidence is None
    assert b.recommendation_confidence_status == "not_calibrated"
    assert a.category_results[0].recommendation_disposition == "review_required"
    assert b.category_results[0].recommendation_disposition == "review_required"
    assert a.input_quality.confidence_status == "not_provided"
    assert b.input_quality.confidence_status == "complete"
    assert b.input_quality.assessment == "low"


def test_engine_complete_high_confidence_standard_disposition(model_binaries_present):
    if not model_binaries_present:
        pytest.skip("models missing")
    settings = Settings()
    engine = RecommendationEngine(ArtifactLoader(settings).load(), settings)
    request = RecommendationRequest(
        profile=_male(),
        categories=["hair", "beard"],
        top_n=2,
        preferences=PreferenceOptions(include_beard=True),
        attribute_confidence={attr: 0.95 for attr in FACIAL_CONFIDENCE_ATTRIBUTES},
    )
    response = engine.recommend(request, "hi")
    assert response.input_quality.assessment == "adequate"
    assert response.input_quality.caution_flag is False
    for cat in response.category_results:
        if cat.status == "ok":
            assert cat.recommendation_disposition == "standard"
    assert response.recommendation_confidence is None
