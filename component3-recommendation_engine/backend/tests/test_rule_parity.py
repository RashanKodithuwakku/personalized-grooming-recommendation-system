"""Rule-parameter loading and dataset-label parity tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.paths import (
    DEFAULT_CATALOGUE_PATH,
    DEFAULT_RULE_PARAMETERS_PATH,
    DEFAULT_TRAINING_PAIRS_PATH,
)
from app.schemas.requests import ProfileFeatures
from app.services.compatibility_rules import (
    PARITY_ABS_TOLERANCE,
    CompatibilityRulesService,
)
from app.core.config import Settings
from app.services.artifact_loader import ArtifactLoader


def test_original_rule_parameters_load_and_cover_catalogue():
    assert DEFAULT_RULE_PARAMETERS_PATH.exists()
    import pandas as pd

    catalogue = pd.read_csv(DEFAULT_CATALOGUE_PATH)
    catalogue_ids = set(catalogue["style_id"].astype(str).str.upper())
    service = CompatibilityRulesService(
        rule_parameters_path=DEFAULT_RULE_PARAMETERS_PATH,
        catalogue_style_ids=catalogue_ids,
        training_pairs_path=None,
        run_parity_check=False,
    )
    assert service.structurally_loaded
    assert service.parameters is not None
    assert service.parameters.parameter_status == "provisional_unvalidated"
    assert set(service.parameters.covered_style_ids) == catalogue_ids
    assert set(service.parameters.covered_style_ids) == {
        "H001",
        "H002",
        "H003",
        "H004",
        "H005",
        "H006",
        "H007",
        "H008",
        "B001",
        "B002",
        "B003",
        "B004",
        "G001",
        "G002",
        "G003",
        "G004",
    }
    for category in ("hair", "beard", "grooming"):
        assert abs(sum(service.parameters.weights[category]) - 1.0) < 1e-9


def test_full_training_pairs_parity_by_category():
    import pandas as pd

    catalogue = pd.read_csv(DEFAULT_CATALOGUE_PATH)
    catalogue_ids = set(catalogue["style_id"].astype(str).str.upper())
    service = CompatibilityRulesService(
        rule_parameters_path=DEFAULT_RULE_PARAMETERS_PATH,
        catalogue_style_ids=catalogue_ids,
        training_pairs_path=None,
        run_parity_check=False,
    )
    report = service.verify_against_training_pairs(
        DEFAULT_TRAINING_PAIRS_PATH,
        target_column="rating",
        tolerance=PARITY_ABS_TOLERANCE,
    )
    assert report.checked_rows == 84000
    assert report.mismatches == 0
    assert report.max_abs_error <= PARITY_ABS_TOLERANCE
    assert report.mae <= PARITY_ABS_TOLERANCE
    assert set(report.verified_categories) == {"hair", "beard", "grooming"}
    for category in ("hair", "beard", "grooming"):
        cat = report.by_category[category]
        assert cat.verified
        assert cat.mismatches == 0
        assert cat.checked_rows > 0
        print(
            f"parity[{category}] rows={cat.checked_rows} "
            f"mae={cat.mae:.3e} max={cat.max_abs_error:.3e}"
        )


def test_rule_evaluation_contributions():
    service = CompatibilityRulesService(
        rule_parameters_path=DEFAULT_RULE_PARAMETERS_PATH,
        training_pairs_path=None,
        run_parity_check=False,
    )
    # Mark verified for hybrid-facing available status in engine tests.
    service.verified_categories = {"hair", "beard", "grooming"}
    profile = ProfileFeatures(
        face_length_ratio=1.45,
        jaw_width_ratio=0.8,
        upper_width_ratio=0.96,
        lower_face_ratio=0.43,
        symmetry=0.85,
        face_shape="oval",
        jawline="soft",
        forehead="low",
        hairline="straight",
        gender="male",
    )
    result = service.evaluate(profile, "H001", "hair")
    assert result.available is True
    assert result.category_verified is True
    assert result.score is not None
    assert 0.0 <= result.score <= 1.0
    assert len(result.contributions) == 9
    attrs = [c.attribute for c in result.contributions]
    assert attrs == [
        "face_length_ratio",
        "jaw_width_ratio",
        "upper_width_ratio",
        "lower_face_ratio",
        "face_shape",
        "jawline",
        "forehead",
        "hairline",
        "symmetry",
    ]
    assert abs(sum(c.contribution for c in result.contributions) - result.score) < 1e-5


def test_startup_loader_enables_verified_rules(model_binaries_present):
    if not model_binaries_present:
        pytest.skip("Local CatBoost model binaries are not available")
    settings = Settings()
    bundle = ArtifactLoader(settings).load()
    assert bundle.ready
    assert bundle.rules is not None
    assert bundle.rules.available is True
    assert set(bundle.rules.verified_categories) == {"hair", "beard", "grooming"}
    assert bundle.rules.parity_report is not None
    assert bundle.rules.parity_report.mismatches == 0
