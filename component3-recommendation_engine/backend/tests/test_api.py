"""API endpoint tests using real local model binaries."""

from __future__ import annotations

import math
from pathlib import Path

import pytest


def _require_models(model_binaries_present: bool) -> None:
    if not model_binaries_present:
        pytest.skip("Local CatBoost model binaries are not available")


def test_health_live(client, model_binaries_present):
    _require_models(model_binaries_present)
    response = client.get("/health/live")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"


def test_health_ready(client, model_binaries_present):
    _require_models(model_binaries_present)
    response = client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["ready"] is True
    assert body["status"] == "ready"
    assert body["models_loaded"]["hair"] is True
    assert body["models_loaded"]["compatibility"] is True
    assert body["rules_available"] is True


def test_capabilities_and_input_schema(client, model_binaries_present):
    _require_models(model_binaries_present)
    caps = client.get("/api/v1/capabilities").json()
    assert caps["recommendation_ready"] is True
    assert caps["rules_available"] is True
    assert caps["rules_status"] == "available_verified"
    assert caps["rule_parameter_status"] == "provisional_unvalidated"
    assert set(caps["rule_verified_categories"]) == {"hair", "beard", "grooming"}
    assert len(caps["rule_covered_style_ids"]) == 16
    assert caps["rule_parity"]["mismatches"] == 0
    assert caps["ranking_policy"]["policy_name"] == "hybrid_model_rank_rules_v1"
    assert "confidence_aware" in caps["available_ranking_modes"]
    assert "confidence_adjusted_rule_score" in caps["score_terminology"]
    assert caps["confidence_calibration_status"] == "not_calibrated"
    assert "beard" in [item["category"] for item in caps["model_coverage_limitations"]]

    schema = client.get("/api/v1/input-schema").json()
    assert schema["model_features"][-2:] == ["style_id", "category"]
    assert "empirical_ranges_note" in schema


def test_styles_endpoint_filters(client, model_binaries_present):
    _require_models(model_binaries_present)
    all_styles = client.get("/api/v1/styles").json()
    assert all_styles["count"] == 16
    beard = client.get("/api/v1/styles", params={"category": "beard"}).json()
    assert beard["count"] == 4
    assert all(item["category"] == "beard" for item in beard["styles"])
    bad = client.get("/api/v1/styles", params={"category": "makeup"})
    assert bad.status_code == 422


def test_models_info_no_filesystem_paths(client, model_binaries_present):
    _require_models(model_binaries_present)
    info = client.get("/api/v1/models/info").json()
    assert info["confidence_calibrated"] is False
    assert len(info["models"]) == 4
    for model in info["models"]:
        assert "path" not in model
        assert model["sha256"]


def test_male_recommendations(client, model_binaries_present, male_request):
    _require_models(model_binaries_present)
    response = client.post("/api/v1/recommendations", json=male_request.model_dump())
    assert response.status_code == 200
    body = response.json()
    assert body["recommendation_confidence"] is None
    assert body["recommendation_confidence_status"] == "not_calibrated"
    assert body["input_quality"]["confidence_status"] == "not_provided"
    assert body["input_quality"]["assessment"] == "unknown"
    assert body["input_quality"]["input_quality_score"] is None
    assert body["input_quality"]["confidence_coverage"] == 0.0
    assert body["input_quality"]["attributes_missing"] == body["input_quality"][
        "confidence_attributes_missing"
    ]
    assert body["input_quality"]["caution_flag"] is True
    assert "confidence_not_provided" in body["input_quality"]["caution_reasons"]

    assert body["ranking_policy"]["policy_name"] == "hybrid_model_rank_rules_v1"
    assert body["ranking_policy"]["weights"]["rule_compatibility"] == pytest.approx(0.20)
    by_cat = {item["category"]: item for item in body["category_results"]}
    assert by_cat["hair"]["status"] == "ok"
    assert by_cat["beard"]["status"] == "ok"
    assert by_cat["grooming"]["status"] == "ok"
    assert by_cat["hair"]["returned_count"] <= male_request.top_n
    assert by_cat["hair"]["recommendation_disposition"] == "review_required"
    assert "eligibility_filtering" in by_cat["hair"]["recommendations"][0][
        "explanation"
    ]["pipeline_stages"]
    for item in by_cat["hair"]["recommendations"]:
        assert math.isfinite(item["raw_ranker_score"])
        assert 1.0 <= item["display_compatibility_rating"] <= 5.0
        expected = 100.0 * (item["display_compatibility_rating"] - 1.0) / 4.0
        assert abs(item["compatibility_score"] - expected) < 1e-9
        assert item["rule_compatibility_score"] is not None
        assert 0.0 <= item["rule_compatibility_score"] <= 1.0
        assert len(item["explanation"]["rule_contributions"]) == 9


def test_female_default_beard_exclusion(client, model_binaries_present, female_request):
    _require_models(model_binaries_present)
    response = client.post("/api/v1/recommendations", json=female_request.model_dump())
    assert response.status_code == 200
    body = response.json()
    skipped = {item["category"]: item for item in body["skipped_categories"]}
    assert "beard" in skipped
    assert skipped["beard"]["status"] == "default_gender_policy"
    by_cat = {item["category"]: item for item in body["category_results"]}
    assert by_cat["hair"]["status"] == "ok"
    assert by_cat["grooming"]["status"] == "ok"
    assert by_cat["beard"]["status"] == "skipped"


def test_female_explicit_beard_unsupported(client, model_binaries_present, female_profile):
    _require_models(model_binaries_present)
    payload = {
        "profile": female_profile.model_dump(),
        "categories": ["hair", "beard", "grooming"],
        "top_n": 2,
        "preferences": {"include_beard": True},
    }
    response = client.post("/api/v1/recommendations", json=payload)
    assert response.status_code == 200
    body = response.json()
    skipped = {item["category"]: item for item in body["skipped_categories"]}
    assert skipped["beard"]["status"] == "unsupported_model_coverage"
    by_cat = {item["category"]: item for item in body["category_results"]}
    assert by_cat["hair"]["status"] == "ok"
    assert by_cat["grooming"]["status"] == "ok"


def test_male_beard_opt_out(client, model_binaries_present, male_profile):
    _require_models(model_binaries_present)
    payload = {
        "profile": male_profile.model_dump(),
        "categories": ["beard"],
        "top_n": 3,
        "preferences": {"include_beard": False},
    }
    response = client.post("/api/v1/recommendations", json=payload)
    body = response.json()
    assert body["skipped_categories"][0]["status"] == "excluded_by_preference"


def test_facial_hair_and_clean_shaven(client, model_binaries_present, male_profile):
    _require_models(model_binaries_present)
    payload = {
        "profile": male_profile.model_dump(),
        "categories": ["beard"],
        "top_n": 10,
        "preferences": {"facial_hair_available": False},
    }
    response = client.post("/api/v1/recommendations", json=payload)
    body = response.json()
    beard = body["category_results"][0]
    assert beard["status"] == "ok"
    ids = [item["style_id"] for item in beard["recommendations"]]
    assert ids == ["B001"]
    assert beard["recommendations"][0]["requires_facial_hair"] is False


def test_excluded_styles_empty_category(client, model_binaries_present, male_profile):
    _require_models(model_binaries_present)
    payload = {
        "profile": male_profile.model_dump(),
        "categories": ["grooming"],
        "top_n": 5,
        "preferences": {
            "excluded_style_ids": ["G001", "G002", "G003", "G004"],
        },
    }
    response = client.post("/api/v1/recommendations", json=payload)
    body = response.json()
    grooming = body["category_results"][0]
    assert grooming["status"] == "empty"
    assert grooming["returned_count"] == 0
    assert grooming["recommendations"] == []


def test_top_n_greater_than_eligible(client, model_binaries_present, male_profile):
    _require_models(model_binaries_present)
    payload = {
        "profile": male_profile.model_dump(),
        "categories": ["grooming"],
        "top_n": 20,
    }
    response = client.post("/api/v1/recommendations", json=payload)
    body = response.json()
    grooming = body["category_results"][0]
    assert grooming["eligible_count"] == 4
    assert grooming["returned_count"] == 4


def test_confidence_provided_and_missing(client, model_binaries_present, male_profile):
    _require_models(model_binaries_present)
    payload = {
        "profile": male_profile.model_dump(),
        "categories": ["hair"],
        "top_n": 2,
        "attribute_confidence": {
            "face_shape": 0.9,
            "jawline": 0.2,
            "gender": 0.95,
        },
    }
    response = client.post("/api/v1/recommendations", json=payload)
    body = response.json()
    quality = body["input_quality"]
    assert quality["confidence_status"] == "partial"
    assert quality["assessment"] == "insufficient_coverage"
    assert quality["input_quality_score"] is not None
    assert "jawline" in quality["low_confidence_attributes"]
    assert "forehead" in quality["confidence_attributes_missing"]
    assert quality["attributes_missing"] == quality["confidence_attributes_missing"]
    assert quality["gender_confidence_supplied"] is True
    assert body["category_results"][0]["recommendation_disposition"] == "review_required"
    assert quality["note"]


def test_capabilities_catalogue_and_confidence_policy(client, model_binaries_present):
    _require_models(model_binaries_present)
    caps = client.get("/api/v1/capabilities").json()
    assert caps["catalogue_coverage"]["hair_style_count"] == 8
    assert caps["catalogue_coverage"]["beard_style_count"] == 4
    assert caps["catalogue_coverage"]["grooming_style_count"] == 4
    assert "eyebrow" in caps["catalogue_coverage"]["grooming_focus"].lower()
    assert caps["confidence_policy"]["policy_name"] == "confidence_aware_topn_flagging_v1"
    assert caps["confidence_calibration_status"] == "not_calibrated"
    schema = client.get("/api/v1/input-schema").json()
    assert len(schema["facial_confidence_attributes"]) == 9
    assert schema["upstream_integration_contract"]


def test_nan_request_rejected(client, model_binaries_present, male_profile):
    _require_models(model_binaries_present)
    # Use a JSON non-finite token representation that Pydantic rejects.
    payload = male_profile.model_dump()
    payload["symmetry"] = "NaN"
    response = client.post(
        "/api/v1/recommendations",
        json={"profile": payload, "categories": ["hair"], "top_n": 1},
    )
    assert response.status_code == 422

    payload_inf = male_profile.model_dump()
    payload_inf["face_length_ratio"] = "Infinity"
    response_inf = client.post(
        "/api/v1/recommendations",
        json={"profile": payload_inf, "categories": ["hair"], "top_n": 1},
    )
    assert response_inf.status_code == 422


def test_deterministic_ranking(client, model_binaries_present, male_request):
    _require_models(model_binaries_present)
    first = client.post("/api/v1/recommendations", json=male_request.model_dump()).json()
    second = client.post("/api/v1/recommendations", json=male_request.model_dump()).json()
    for left, right in zip(first["category_results"], second["category_results"]):
        left_ids = [item["style_id"] for item in left["recommendations"]]
        right_ids = [item["style_id"] for item in right["recommendations"]]
        assert left_ids == right_ids
        left_scores = [item["hybrid_score"] for item in left["recommendations"]]
        right_scores = [item["hybrid_score"] for item in right["recommendations"]]
        assert left_scores == right_scores


def test_no_persistence_of_user_data(
    client, model_binaries_present, male_request, backend_root: Path
):
    _require_models(model_binaries_present)
    protected = list((backend_root / "datasets").rglob("*")) + list(
        (backend_root / "models").rglob("*")
    )
    before_map = {
        p.resolve(): (p.stat().st_mtime_ns, p.stat().st_size)
        for p in protected
        if p.is_file()
    }
    client.post("/api/v1/recommendations", json=male_request.model_dump())
    after_map = {
        p.resolve(): (p.stat().st_mtime_ns, p.stat().st_size)
        for p in protected
        if p.is_file()
    }
    assert before_map == after_map
