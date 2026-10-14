"""Readiness diagnostics and optional rule-parameter interface tests."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.schemas.requests import ProfileFeatures
from app.services.artifact_loader import ArtifactLoader
from app.services.compatibility_rules import (
    MISSING_RULE_ARTIFACT,
    CompatibilityRulesService,
    create_example_rule_parameters_template,
)


def test_missing_rule_artifact_message():
    service = CompatibilityRulesService(None)
    assert service.available is False
    assert service.status == "unavailable"
    assert MISSING_RULE_ARTIFACT in (service.missing_artifact_message or "")


def test_rule_parameters_template_loads_and_scores(tmp_path: Path):
    template = create_example_rule_parameters_template()
    path = tmp_path / "rating_parameters.json"
    path.write_text(json.dumps(template), encoding="utf-8")
    service = CompatibilityRulesService(
        path,
        training_pairs_path=None,
        run_parity_check=False,
    )
    assert service.structurally_loaded is True
    assert service.available is True
    profile = ProfileFeatures(
        face_length_ratio=1.35,
        jaw_width_ratio=0.85,
        upper_width_ratio=0.96,
        lower_face_ratio=0.44,
        symmetry=0.7,
        face_shape="oval",
        jawline="angular",
        forehead="medium",
        hairline="straight",
        gender="male",
    )
    result = service.evaluate(profile, style_id="H001", category="hair")
    assert result.available is True
    assert result.score is not None
    assert 0.0 <= result.score <= 1.0
    assert result.contributions


def test_invalid_rule_parameters_reported(tmp_path: Path):
    path = tmp_path / "bad_rules.json"
    path.write_text(json.dumps({"version": "1"}), encoding="utf-8")
    service = CompatibilityRulesService(
        path,
        training_pairs_path=None,
        run_parity_check=False,
    )
    assert service.available is False
    assert service.status == "configured_but_invalid"
    assert service.load_diagnostics


def test_corrupt_model_makes_ready_false(
    tmp_path: Path, backend_root: Path, model_binaries_present: bool
):
    if not model_binaries_present:
        pytest.skip("Local CatBoost model binaries are not available")

    models_dir = tmp_path / "models"
    binaries = models_dir / "models"
    binaries.mkdir(parents=True)
    shutil.copy(
        backend_root / "models" / "gender_aware_schema.json",
        models_dir / "gender_aware_schema.json",
    )
    for name in [
        "beard_ranker_gender_aware.cbm",
        "grooming_ranker_gender_aware.cbm",
        "compatibility_scorer_gender_aware.cbm",
    ]:
        shutil.copy(
            backend_root / "models" / "models" / name,
            binaries / name,
        )
    (binaries / "hair_ranker_gender_aware.cbm").write_bytes(b"not-a-catboost-model")

    settings = Settings(
        models_dir=models_dir,
        schema_path=models_dir / "gender_aware_schema.json",
        datasets_dir=backend_root / "datasets",
        catalogue_path=backend_root
        / "datasets"
        / "generated_data"
        / "style_catalogue.csv",
    )
    bundle = ArtifactLoader(settings).load()
    assert bundle.ready is False
    assert bundle.models_loaded_map()["hair"] is False
    assert any("hair_ranker" in d or "Failed to load" in d for d in bundle.diagnostics)

    # Also verify the HTTP readiness surface with a temporary app.
    import app.main as main_module

    get_settings.cache_clear()
    original = main_module.get_settings

    def _settings() -> Settings:
        return settings

    main_module.get_settings = _settings  # type: ignore[assignment]
    try:
        app = main_module.create_app()
        with TestClient(app) as client:
            ready = client.get("/health/ready").json()
            assert ready["ready"] is False
            assert ready["status"] == "not_ready"
            assert ready["diagnostics"]
            assert ready["models_loaded"]["hair"] is False
            response = client.post(
                "/api/v1/recommendations",
                json={
                    "profile": {
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
                    },
                    "categories": ["hair"],
                    "top_n": 1,
                },
            )
            assert response.status_code == 503
    finally:
        main_module.get_settings = original  # type: ignore[assignment]
        get_settings.cache_clear()
