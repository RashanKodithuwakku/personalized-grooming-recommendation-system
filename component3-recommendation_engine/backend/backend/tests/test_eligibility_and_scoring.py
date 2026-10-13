"""Eligibility rules, scoring helpers, and percentile tests."""

from __future__ import annotations

import pandas as pd

from app.schemas.requests import PreferenceOptions, ProfileFeatures
from app.services.eligibility import EligibilityService
from app.services.recommendation_engine import (
    clip_rating,
    compatibility_score_0_100,
    normalize_predicted_compatibility,
    tie_aware_rank_percentiles,
)


def _catalogue() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "style_id": "B001",
                "category": "beard",
                "style_name": "Clean shaven",
                "gender_restriction": "none",
                "requires_facial_hair": False,
            },
            {
                "style_id": "B002",
                "category": "beard",
                "style_name": "Short stubble",
                "gender_restriction": "none",
                "requires_facial_hair": True,
            },
            {
                "style_id": "B003",
                "category": "beard",
                "style_name": "Short boxed beard",
                "gender_restriction": "none",
                "requires_facial_hair": True,
            },
        ]
    )


def _male() -> ProfileFeatures:
    return ProfileFeatures(
        face_length_ratio=1.2,
        jaw_width_ratio=0.8,
        upper_width_ratio=0.9,
        lower_face_ratio=0.4,
        symmetry=0.7,
        face_shape="oval",
        jawline="angular",
        forehead="medium",
        hairline="straight",
        gender="male",
    )


def _female() -> ProfileFeatures:
    return ProfileFeatures(
        face_length_ratio=1.2,
        jaw_width_ratio=0.8,
        upper_width_ratio=0.9,
        lower_face_ratio=0.4,
        symmetry=0.7,
        face_shape="oval",
        jawline="soft",
        forehead="medium",
        hairline="straight",
        gender="female",
    )


def test_female_default_skips_beard():
    decision = EligibilityService().evaluate_category(
        "beard", _female(), PreferenceOptions(), _catalogue()
    )
    assert decision.include_category is False
    assert decision.skip_status == "default_gender_policy"


def test_female_explicit_beard_unsupported_coverage():
    decision = EligibilityService().evaluate_category(
        "beard",
        _female(),
        PreferenceOptions(include_beard=True),
        _catalogue(),
    )
    assert decision.include_category is False
    assert decision.skip_status == "unsupported_model_coverage"


def test_male_beard_opt_out():
    decision = EligibilityService().evaluate_category(
        "beard",
        _male(),
        PreferenceOptions(include_beard=False),
        _catalogue(),
    )
    assert decision.include_category is False
    assert decision.skip_status == "excluded_by_preference"


def test_facial_hair_filter_keeps_clean_shaven():
    decision = EligibilityService().evaluate_category(
        "beard",
        _male(),
        PreferenceOptions(facial_hair_available=False),
        _catalogue(),
    )
    assert decision.include_category is True
    ids = set(decision.eligible_styles["style_id"])
    assert ids == {"B001"}
    assert "facial_hair_available_false_filter" in decision.applied_rules


def test_excluded_styles_not_reintroduced():
    decision = EligibilityService().evaluate_category(
        "beard",
        _male(),
        PreferenceOptions(excluded_style_ids=["B001", "B002", "B003"]),
        _catalogue(),
    )
    assert decision.eligible_styles.empty
    assert decision.empty_reason is not None


def test_compatibility_scaling_and_clipping():
    assert clip_rating(0.5) == 1.0
    assert clip_rating(6.0) == 5.0
    assert clip_rating(3.0) == 3.0
    assert compatibility_score_0_100(1.0) == 0.0
    assert compatibility_score_0_100(5.0) == 100.0
    assert compatibility_score_0_100(3.0) == 50.0
    assert normalize_predicted_compatibility(3.0) == 0.5


def test_tie_aware_rank_percentiles_and_single_candidate():
    assert tie_aware_rank_percentiles([10.0]) == [1.0]
    # Higher score is better.
    percentiles = tie_aware_rank_percentiles([1.0, 3.0, 2.0])
    assert percentiles[1] == 1.0
    assert percentiles[2] == 2.0 / 3.0
    assert percentiles[0] == 1.0 / 3.0
    # Ties get average ranks.
    tied = tie_aware_rank_percentiles([5.0, 5.0, 1.0])
    assert tied[0] == tied[1]
    assert tied[0] > tied[2]
