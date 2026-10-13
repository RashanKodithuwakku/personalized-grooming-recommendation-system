"""Request validation and schema contract tests."""

from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

from app.schemas.requests import PreferenceOptions, ProfileFeatures, RecommendationRequest


def _base_profile(**overrides):
    data = {
        "face_length_ratio": 1.3,
        "jaw_width_ratio": 0.85,
        "upper_width_ratio": 0.96,
        "lower_face_ratio": 0.44,
        "symmetry": 0.7,
        "face_shape": "oval",
        "jawline": "angular",
        "forehead": "medium",
        "hairline": "straight",
        "gender": "male",
    }
    data.update(overrides)
    return data


def test_valid_profile_normalizes_case_and_whitespace():
    profile = ProfileFeatures(**_base_profile(face_shape=" Oval ", gender="MALE"))
    assert profile.face_shape == "oval"
    assert profile.gender == "male"


def test_missing_essential_attribute_rejected():
    data = _base_profile()
    del data["face_shape"]
    with pytest.raises(ValidationError):
        ProfileFeatures(**data)


def test_unsupported_face_shape_rejected():
    with pytest.raises(ValidationError):
        ProfileFeatures(**_base_profile(face_shape="triangle"))


def test_unsupported_category_not_remapped():
    with pytest.raises(ValidationError):
        RecommendationRequest(
            profile=ProfileFeatures(**_base_profile()),
            categories=["makeup"],
        )


def test_nan_rejected():
    with pytest.raises(ValidationError):
        ProfileFeatures(**_base_profile(symmetry=float("nan")))


def test_infinity_rejected():
    with pytest.raises(ValidationError):
        ProfileFeatures(**_base_profile(face_length_ratio=math.inf))


def test_symmetry_out_of_bounds_rejected():
    with pytest.raises(ValidationError):
        ProfileFeatures(**_base_profile(symmetry=1.2))


def test_confidence_out_of_bounds_rejected():
    with pytest.raises(ValidationError):
        RecommendationRequest(
            profile=ProfileFeatures(**_base_profile()),
            attribute_confidence={"face_shape": 1.5},
        )


def test_confidence_nan_rejected():
    with pytest.raises(ValidationError):
        RecommendationRequest(
            profile=ProfileFeatures(**_base_profile()),
            attribute_confidence={"face_shape": float("nan")},
        )


def test_confidence_infinity_rejected():
    with pytest.raises(ValidationError):
        RecommendationRequest(
            profile=ProfileFeatures(**_base_profile()),
            attribute_confidence={"symmetry": math.inf},
        )


def test_unknown_confidence_key_rejected():
    with pytest.raises(ValidationError):
        RecommendationRequest(
            profile=ProfileFeatures(**_base_profile()),
            attribute_confidence={"skin_tone": 0.9},
        )


def test_excluded_style_ids_normalized():
    prefs = PreferenceOptions(excluded_style_ids=[" h001 ", "H001", "b002"])
    assert prefs.excluded_style_ids == ["H001", "B002"]


def test_top_n_bounds():
    with pytest.raises(ValidationError):
        RecommendationRequest(
            profile=ProfileFeatures(**_base_profile()),
            top_n=0,
        )
    with pytest.raises(ValidationError):
        RecommendationRequest(
            profile=ProfileFeatures(**_base_profile()),
            top_n=100,
        )
