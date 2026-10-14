"""Shared fixtures for Component 3 tests."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.paths import BACKEND_ROOT, DEFAULT_MODEL_BINARIES_DIR
from app.main import create_app
from app.schemas.requests import PreferenceOptions, ProfileFeatures, RecommendationRequest


@pytest.fixture(scope="session")
def backend_root() -> Path:
    return BACKEND_ROOT


@pytest.fixture(scope="session")
def model_binaries_present() -> bool:
    required = [
        "hair_ranker_gender_aware.cbm",
        "beard_ranker_gender_aware.cbm",
        "grooming_ranker_gender_aware.cbm",
        "compatibility_scorer_gender_aware.cbm",
    ]
    return all((DEFAULT_MODEL_BINARIES_DIR / name).exists() for name in required)


@pytest.fixture
def settings() -> Settings:
    get_settings.cache_clear()
    return Settings()


@pytest.fixture(scope="module")
def client():
    """Module-scoped API client to avoid reloading models/parity every test."""
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    get_settings.cache_clear()


@pytest.fixture
def male_profile() -> ProfileFeatures:
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


@pytest.fixture
def female_profile() -> ProfileFeatures:
    return ProfileFeatures(
        face_length_ratio=1.4741868136966976,
        jaw_width_ratio=0.7022803446346432,
        upper_width_ratio=0.8874882194850102,
        lower_face_ratio=0.4261109355990833,
        symmetry=0.5257072408486533,
        face_shape="round",
        jawline="soft",
        forehead="high",
        hairline="receding",
        gender="female",
    )


@pytest.fixture
def male_request(male_profile: ProfileFeatures) -> RecommendationRequest:
    return RecommendationRequest(
        profile=male_profile,
        categories=["hair", "beard", "grooming"],
        top_n=3,
        preferences=PreferenceOptions(
            include_beard=True,
            facial_hair_available=True,
            excluded_style_ids=[],
        ),
    )


@pytest.fixture
def female_request(female_profile: ProfileFeatures) -> RecommendationRequest:
    return RecommendationRequest(
        profile=female_profile,
        categories=["hair", "beard", "grooming"],
        top_n=3,
        preferences=PreferenceOptions(facial_hair_available=False),
    )


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
