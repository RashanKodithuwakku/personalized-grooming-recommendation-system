"""Real-model integration tests (not mocked).

Compares a small deterministic sample against exported raw predictions in
gender_test_predictions.csv using a documented numerical tolerance.

Hybrid application ordering is intentionally NOT compared to raw model
ordering; only raw ranker / scorer outputs are checked.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from catboost import CatBoostRanker, CatBoostRegressor

from app.core.config import Settings
from app.core.paths import DEFAULT_MODEL_BINARIES_DIR, DEFAULT_TEST_PREDICTIONS_PATH
from app.schemas.requests import ProfileFeatures
from app.services.artifact_loader import ArtifactLoader, EXPECTED_MODEL_FEATURES
from app.services.feature_builder import FeatureBuilder
from app.services.recommendation_engine import RecommendationEngine, clip_rating

# Documented absolute tolerance for floating-point / CatBoost parity checks.
RAW_PREDICTION_TOLERANCE = 1e-5


def _require_models(model_binaries_present: bool) -> None:
    if not model_binaries_present:
        pytest.skip("Local CatBoost model binaries are not available")


def test_model_feature_order_and_categorical_types(model_binaries_present):
    _require_models(model_binaries_present)
    settings = Settings()
    bundle = ArtifactLoader(settings).load()
    assert bundle.ready
    for name, loaded in bundle.rankers.items():
        assert loaded.feature_names == EXPECTED_MODEL_FEATURES
        assert loaded.categorical_names == [
            "face_shape",
            "jawline",
            "forehead",
            "hairline",
            "gender",
            "style_id",
            "category",
        ]
    assert bundle.scorer is not None
    assert bundle.scorer.feature_names == EXPECTED_MODEL_FEATURES


def test_exported_raw_predictions_parity(model_binaries_present):
    """Compare application model outputs to exported test predictions.

    This is a real-model check. Mocked predictors are not used.
    """
    _require_models(model_binaries_present)
    if not DEFAULT_TEST_PREDICTIONS_PATH.exists():
        pytest.skip("gender_test_predictions.csv not available")

    preds = pd.read_csv(DEFAULT_TEST_PREDICTIONS_PATH)
    # One profile per category for a small deterministic sample.
    samples = []
    for category in ("hair", "beard", "grooming"):
        subset = preds.loc[preds["category"] == category]
        if subset.empty:
            continue
        profile_id = subset["profile_id"].iloc[0]
        samples.append(subset.loc[subset["profile_id"] == profile_id].copy())
    assert samples, "No prediction samples found"
    sample = pd.concat(samples, ignore_index=True)

    hair = CatBoostRanker()
    hair.load_model(str(DEFAULT_MODEL_BINARIES_DIR / "hair_ranker_gender_aware.cbm"))
    beard = CatBoostRanker()
    beard.load_model(str(DEFAULT_MODEL_BINARIES_DIR / "beard_ranker_gender_aware.cbm"))
    grooming = CatBoostRanker()
    grooming.load_model(
        str(DEFAULT_MODEL_BINARIES_DIR / "grooming_ranker_gender_aware.cbm")
    )
    scorer = CatBoostRegressor()
    scorer.load_model(
        str(DEFAULT_MODEL_BINARIES_DIR / "compatibility_scorer_gender_aware.cbm")
    )
    rankers = {"hair": hair, "beard": beard, "grooming": grooming}

    builder = FeatureBuilder(feature_names=list(hair.feature_names_))
    for (profile_id, category), group in sample.groupby(["profile_id", "category"]):
        row0 = group.iloc[0]
        profile = ProfileFeatures(
            face_length_ratio=float(row0["face_length_ratio"]),
            jaw_width_ratio=float(row0["jaw_width_ratio"]),
            upper_width_ratio=float(row0["upper_width_ratio"]),
            lower_face_ratio=float(row0["lower_face_ratio"]),
            symmetry=float(row0["symmetry"]),
            face_shape=str(row0["face_shape"]),
            jawline=str(row0["jawline"]),
            forehead=str(row0["forehead"]),
            hairline=str(row0["hairline"]),
            gender=str(row0["gender"]),
        )
        styles = group[["style_id", "category"]].copy()
        features = builder.build_candidates(profile, styles)
        # Ensure categorical columns remain object/string dtype.
        for col in [
            "face_shape",
            "jawline",
            "forehead",
            "hairline",
            "gender",
            "style_id",
            "category",
        ]:
            assert features[col].dtype == object or str(features[col].dtype) == "string"

        ranker_out = rankers[category].predict(features, thread_count=1)
        scorer_out = scorer.predict(features, thread_count=1)
        for idx, (_, expected_row) in enumerate(group.iterrows()):
            assert abs(float(ranker_out[idx]) - float(expected_row["ranker_prediction"])) < RAW_PREDICTION_TOLERANCE
            assert abs(
                float(scorer_out[idx]) - float(expected_row["predicted_rating_raw"])
            ) < RAW_PREDICTION_TOLERANCE


def test_engine_raw_scores_match_exported_sample(
    model_binaries_present, male_profile
):
    _require_models(model_binaries_present)
    if not DEFAULT_TEST_PREDICTIONS_PATH.exists():
        pytest.skip("gender_test_predictions.csv not available")

    preds = pd.read_csv(DEFAULT_TEST_PREDICTIONS_PATH)
    # Use the known male profile SIM9_000027 from fixtures / exports.
    group = preds.loc[
        (preds["profile_id"] == "SIM9_000027") & (preds["category"] == "hair")
    ]
    if group.empty:
        pytest.skip("SIM9_000027 hair rows not present in prediction export")

    settings = Settings()
    bundle = ArtifactLoader(settings).load()
    engine = RecommendationEngine(bundle, settings)
    from app.schemas.requests import PreferenceOptions, RecommendationRequest

    request = RecommendationRequest(
        profile=male_profile,
        categories=["hair"],
        top_n=8,
        preferences=PreferenceOptions(),
    )
    response = engine.recommend(request, request_id="test-parity")
    hair = response.category_results[0]
    by_id = {item.style_id: item for item in hair.recommendations}
    for _, row in group.iterrows():
        style_id = str(row["style_id"])
        assert style_id in by_id
        item = by_id[style_id]
        assert abs(item.raw_ranker_score - float(row["ranker_prediction"])) < RAW_PREDICTION_TOLERANCE
        assert abs(
            item.raw_predicted_compatibility_rating - float(row["predicted_rating_raw"])
        ) < RAW_PREDICTION_TOLERANCE
        assert item.display_compatibility_rating == clip_rating(
            item.raw_predicted_compatibility_rating
        )


def test_single_candidate_category_percentile(model_binaries_present, male_profile):
    _require_models(model_binaries_present)
    settings = Settings()
    bundle = ArtifactLoader(settings).load()
    engine = RecommendationEngine(bundle, settings)
    from app.schemas.requests import PreferenceOptions, RecommendationRequest

    request = RecommendationRequest(
        profile=male_profile,
        categories=["beard"],
        top_n=1,
        preferences=PreferenceOptions(
            facial_hair_available=False,
            excluded_style_ids=[],
        ),
    )
    response = engine.recommend(request, request_id="single-cand")
    beard = response.category_results[0]
    assert beard.eligible_count == 1
    assert beard.recommendations[0].rank_percentile == 1.0
