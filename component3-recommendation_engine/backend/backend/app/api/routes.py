"""HTTP endpoints for Component 3."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from app.api.deps import ArtifactsDep, EngineDep, SettingsDep
from app.core.exceptions import RecommendationNotReadyError
from app.core.logging import get_logger
from app.schemas.requests import (
    FACIAL_CONFIDENCE_KEYS,
    SUPPORTED_CATEGORIES,
    SUPPORTED_CONFIDENCE_SOURCES,
    SUPPORTED_FACE_SHAPES,
    SUPPORTED_FOREHEADS,
    SUPPORTED_GENDERS,
    SUPPORTED_HAIRLINES,
    SUPPORTED_JAWLINES,
    SUPPORTED_RANKING_MODES,
    RecommendationRequest,
)
from app.schemas.responses import (
    CapabilitiesResponse,
    CatalogueCoverageInfo,
    ConfidencePolicyInfo,
    EvaluationSummary,
    HealthLiveResponse,
    HealthReadyResponse,
    InputSchemaResponse,
    ModelArtifactInfo,
    ModelCoverageLimitation,
    ModelInfoResponse,
    RecommendationResponse,
    StyleRecord,
    StylesResponse,
    UpstreamFieldContract,
)
from app.services.input_quality_service import FACIAL_CONFIDENCE_ATTRIBUTES
from app.services.artifact_loader import (
    EXPECTED_CATEGORICAL_FEATURES,
    EXPECTED_MODEL_FEATURES,
    EXPECTED_PROFILE_FEATURES,
    NUMERIC_FEATURES,
    supported_categorical_values,
)
from app.services.compatibility_rules import MISSING_RULE_ARTIFACT

logger = get_logger(__name__)

router = APIRouter()


def _request_id(request: Request) -> str:
    existing = request.headers.get("X-Request-ID")
    if existing and existing.strip():
        return existing.strip()[:64]
    return str(uuid.uuid4())


@router.get("/health/live", response_model=HealthLiveResponse, tags=["health"])
def health_live(settings: SettingsDep) -> HealthLiveResponse:
    return HealthLiveResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
    )


@router.get("/health/ready", response_model=HealthReadyResponse, tags=["health"])
def health_ready(artifacts: ArtifactsDep) -> HealthReadyResponse:
    return HealthReadyResponse(
        status="ready" if artifacts.ready else "not_ready",
        ready=artifacts.ready,
        diagnostics=list(artifacts.diagnostics),
        models_loaded=artifacts.models_loaded_map(),
        catalogue_loaded=not artifacts.catalogue.empty,
        schema_loaded=bool(artifacts.schema),
        rules_available=bool(artifacts.rules and artifacts.rules.available),
    )


@router.get(
    "/api/v1/capabilities",
    response_model=CapabilitiesResponse,
    tags=["meta"],
)
def capabilities(
    artifacts: ArtifactsDep,
    engine: EngineDep,
    settings: SettingsDep,
) -> CapabilitiesResponse:
    rules_meta = (
        artifacts.rules.capabilities_payload()
        if artifacts.rules is not None
        else {
            "rules_available": False,
            "rules_status": "unavailable",
            "missing_rule_artifact": MISSING_RULE_ARTIFACT,
            "parameter_status": None,
            "verified_categories": [],
            "covered_style_ids": [],
            "parity": None,
            "formula": None,
            "similarity_definition": None,
            "provenance": None,
        }
    )
    hair_n = int((artifacts.catalogue["category"] == "hair").sum()) if not artifacts.catalogue.empty else 0
    beard_n = int((artifacts.catalogue["category"] == "beard").sum()) if not artifacts.catalogue.empty else 0
    grooming_n = (
        int((artifacts.catalogue["category"] == "grooming").sum())
        if not artifacts.catalogue.empty
        else 0
    )
    policy = engine.input_quality_policy_info()
    return CapabilitiesResponse(
        available_categories=list(SUPPORTED_CATEGORIES),
        model_readiness=artifacts.models_loaded_map(),
        recommendation_ready=artifacts.ready,
        rules_available=bool(rules_meta["rules_available"]),
        rules_status=str(rules_meta["rules_status"]),
        missing_rule_artifact=rules_meta.get("missing_rule_artifact"),
        rule_parameter_status=rules_meta.get("parameter_status"),
        rule_verified_categories=list(rules_meta.get("verified_categories") or []),
        rule_covered_style_ids=list(rules_meta.get("covered_style_ids") or []),
        rule_formula=rules_meta.get("formula"),
        rule_similarity_definition=rules_meta.get("similarity_definition"),
        rule_parity=rules_meta.get("parity"),
        rule_provenance=rules_meta.get("provenance"),
        catalogue_coverage=CatalogueCoverageInfo(
            hair_style_count=hair_n,
            beard_style_count=beard_n,
            grooming_style_count=grooming_n,
            total_style_count=hair_n + beard_n + grooming_n,
            grooming_focus=(
                "Current grooming catalogue styles concern eyebrow styling "
                "(natural / straight / soft-angled / rounded brow)."
            ),
            unsupported_preference_inputs=[
                "hair_length",
                "hair_texture",
                "hair_density",
                "maintenance_preferences",
            ],
            notes=[
                "Current recommendations do not evaluate hair length, hair texture, "
                "hair density, or maintenance preferences unless those attributes are "
                "genuinely supported by the implementation (they are not today).",
                "Hair styles are not arbitrarily restricted by gender; a male profile "
                "receiving Long layers is not inherently a defect under the current "
                "catalogue (gender_restriction=none).",
            ],
        ),
        confidence_policy=ConfidencePolicyInfo(**policy),
        supported_genders=list(SUPPORTED_GENDERS),
        supported_face_shapes=list(SUPPORTED_FACE_SHAPES),
        supported_jawlines=list(SUPPORTED_JAWLINES),
        supported_foreheads=list(SUPPORTED_FOREHEADS),
        supported_hairlines=list(SUPPORTED_HAIRLINES),
        confidence_calibration_status="not_calibrated",
        ranking_policy=engine.ranking_policy_info(),
        available_ranking_modes=list(SUPPORTED_RANKING_MODES),
        ranking_mode_notes=[
            "ranking_mode=standard (default): existing hybrid_model_rank_rules_v1 "
            "behavior; confidence is used only for input-quality flagging.",
            "ranking_mode=confidence_aware: requires all nine facial attribute "
            "confidence values; uses hybrid_confidence_adjusted_rules_v1 which "
            "replaces only the rule hybrid term with confidence_adjusted_rule_score "
            "= sum(w_i*c_i*s_ij)/sum(w_i*c_i). CatBoost models still consume "
            "profile values without uncertainty propagation.",
            "All-zero facial confidence in confidence_aware mode falls back to "
            "standard ranking (no divide-by-zero) with review_required.",
            "confidence_source (manual|upstream|unspecified) is provenance only "
            "and does not change scores. Manual confidence is demo/test input "
            "until upstream components populate the same contract.",
            "recommendation_support_score is a heuristic confidence-weighted "
            "rule-support score, not a probability or calibrated confidence.",
        ],
        model_coverage_limitations=[
            ModelCoverageLimitation(
                category="beard",
                limitation=(
                    "Beard ranker trained on male profiles only. Female beard "
                    "training rows were excluded. Explicit female include_beard=true "
                    "returns unsupported_model_coverage and does not run beard ranking."
                ),
                status="male_only_training_coverage",
            )
        ],
        rating_scale={
            "training_target": "rating",
            "approx_range": "1-5",
            "rating_source": artifacts.schema.get("rating_source")
            or artifacts.dataset_metadata.get("rating_source")
            or "rule_generated",
            "human_reviewed": artifacts.dataset_metadata.get("human_reviewed", False),
            "note": (
                "The compatibility scorer predicts ratings on a 1–5 style scale. "
                "Training ratings were rule-generated from provisional rule "
                "parameters, not human-reviewed."
            ),
        },
        compatibility_score_definition=(
            "compatibility_score = 100 * (clipped_display_rating - 1) / 4. "
            "This is a rescaled predicted rating, not accuracy or a confidence probability."
        ),
        score_terminology={
            "compatibility_score": "Rescaled predicted rating (0–100).",
            "rule_compatibility_score": "Original weighted rule agreement (0–1).",
            "confidence_adjusted_rule_score": (
                "S_j/A confidence-adjusted rule compatibility (0–1); "
                "used only in ranking_mode=confidence_aware."
            ),
            "recommendation_support_score": (
                "S_j = sum(w_i*c_i*s_ij); heuristic confidence-weighted rule support "
                "(not a probability)."
            ),
            "rule_confidence_coverage": "A = sum(w_i*c_i) for the category.",
            "hybrid_score": "Final ranking / ordering score from the active policy.",
            "input_quality_score": (
                "Heuristic input reliability from supplied confidence "
                "(not style-suitability probability)."
            ),
            "recommendation_confidence": (
                "Unavailable until calibrated (always null / not_calibrated)."
            ),
        },
        notes=[
            "Adding gender as a feature does not by itself prove gender-specific suitability.",
            "Full research validation is not claimed complete.",
            "Rule parameter_status remains provisional_unvalidated even after "
            "dataset-label parity verification.",
            "Recommendation confidence remains not_calibrated.",
            "Human suitability validation remains unfinished research work.",
            f"Default top_n={settings.default_top_n}, max_top_n={settings.max_top_n}.",
        ],
    )


@router.get(
    "/api/v1/input-schema",
    response_model=InputSchemaResponse,
    tags=["meta"],
)
def input_schema(artifacts: ArtifactsDep, settings: SettingsDep) -> InputSchemaResponse:
    ranges = artifacts.empirical_numeric_ranges or {}
    upstream: list[UpstreamFieldContract] = []
    for field in EXPECTED_PROFILE_FEATURES:
        if field in NUMERIC_FEATURES:
            range_note = (
                f"Empirical training range "
                f"[{ranges[field]['min']:.6f}, {ranges[field]['max']:.6f}] "
                "(not a biological limit)."
                if field in ranges
                else "Empirical training range unavailable."
            )
            upstream.append(
                UpstreamFieldContract(
                    field=field,
                    required=True,
                    role="model_and_rule_numeric_input",
                    notes=(
                        f"{range_note} Exact physical measurement definition and "
                        "normalization convention require agreement with the upstream "
                        "component; this API does not invent a physical interpretation."
                    ),
                )
            )
        elif field == "gender":
            upstream.append(
                UpstreamFieldContract(
                    field=field,
                    required=True,
                    role="eligibility_and_model_categorical_input",
                    notes=(
                        "Supported values: male, female. Used for eligibility / model "
                        "coverage. Gender confidence may be supplied but is excluded "
                        "from the nine-attribute facial input-quality aggregate."
                    ),
                )
            )
        else:
            upstream.append(
                UpstreamFieldContract(
                    field=field,
                    required=True,
                    role="model_and_rule_categorical_input",
                    notes=(
                        f"Supported values: {supported_categorical_values().get(field, [])}. "
                        "Upstream label mapping must match these tokens exactly "
                        "(case/whitespace normalized)."
                    ),
                )
            )
    upstream.extend(
        [
            UpstreamFieldContract(
                field="attribute_confidence.<facial_attribute>",
                required=False,
                role="optional_upstream_confidence",
                notes=(
                    "Finite value in [0,1] for any of the nine facial attributes. "
                    "Missing confidence is unknown reliability, not a missing "
                    "measurement. Manual input demos may omit this map in "
                    "ranking_mode=standard. ranking_mode=confidence_aware requires "
                    "all nine facial keys (zeros allowed)."
                ),
            ),
            UpstreamFieldContract(
                field="ranking_mode",
                required=False,
                role="ranking_policy_selector",
                notes=(
                    "standard (default) or confidence_aware. confidence_aware "
                    "requires a complete nine-attribute confidence map."
                ),
            ),
            UpstreamFieldContract(
                field="confidence_source",
                required=False,
                role="confidence_provenance",
                notes=(
                    "manual | upstream | unspecified. Provenance only; does not "
                    "change scores. Use manual for demo/test until upstream fills "
                    "the same contract."
                ),
            ),
            UpstreamFieldContract(
                field="preferences.include_beard",
                required=False,
                role="eligibility_preference",
                notes="Optional boolean beard inclusion preference.",
            ),
            UpstreamFieldContract(
                field="preferences.facial_hair_available",
                required=False,
                role="eligibility_preference",
                notes=(
                    "When false, catalogue styles with requires_facial_hair=true "
                    "are excluded; clean-shaven remains eligible."
                ),
            ),
            UpstreamFieldContract(
                field="preferences.excluded_style_ids",
                required=False,
                role="eligibility_preference",
                notes="Optional catalogue style IDs to exclude.",
            ),
        ]
    )
    facial_ones = {key: 1.0 for key in FACIAL_CONFIDENCE_KEYS}
    return InputSchemaResponse(
        profile_features=list(EXPECTED_PROFILE_FEATURES),
        model_features=list(EXPECTED_MODEL_FEATURES),
        categorical_features=list(EXPECTED_CATEGORICAL_FEATURES),
        numeric_features=list(NUMERIC_FEATURES),
        supported_categories=list(SUPPORTED_CATEGORIES),
        supported_genders=list(SUPPORTED_GENDERS),
        categorical_values=supported_categorical_values(),
        preferences_fields=[
            "include_beard",
            "facial_hair_available",
            "excluded_style_ids",
        ],
        attribute_confidence_keys=list(EXPECTED_PROFILE_FEATURES),
        facial_confidence_attributes=list(FACIAL_CONFIDENCE_ATTRIBUTES),
        ranking_modes=list(SUPPORTED_RANKING_MODES),
        confidence_sources=list(SUPPORTED_CONFIDENCE_SOURCES),
        ranking_mode_requirements={
            "standard": (
                "Default. attribute_confidence optional; used for input-quality "
                "flagging only; hybrid ordering unchanged."
            ),
            "confidence_aware": (
                "Requires all nine facial confidence keys "
                f"{list(FACIAL_CONFIDENCE_KEYS)}. Zeros accepted. Incomplete maps "
                "rejected. Gender confidence optional and excluded from rule weighting."
            ),
        },
        top_n_limits={"default": settings.default_top_n, "max": settings.max_top_n},
        empirical_numeric_ranges=artifacts.empirical_numeric_ranges or None,
        empirical_ranges_note=(
            "Empirical ranges are derived from the training split for "
            "out-of-distribution warnings only. They are not biological limits. "
            "Physical definitions of ratios require upstream agreement."
        ),
        upstream_integration_contract=upstream,
        request_example={
            "schema_version": "1.0",
            "profile": {
                "face_length_ratio": 1.35,
                "jaw_width_ratio": 0.85,
                "upper_width_ratio": 0.96,
                "lower_face_ratio": 0.44,
                "symmetry": 0.72,
                "face_shape": "oval",
                "jawline": "angular",
                "forehead": "medium",
                "hairline": "straight",
                "gender": "male",
            },
            "categories": ["hair", "beard", "grooming"],
            "top_n": 3,
            "ranking_mode": "standard",
            "confidence_source": "unspecified",
            "preferences": {
                "include_beard": True,
                "facial_hair_available": True,
                "excluded_style_ids": [],
            },
            "attribute_confidence": {
                "face_shape": 0.9,
                "jawline": 0.8,
                "gender": 0.95,
            },
        },
        confidence_aware_request_example={
            "schema_version": "1.0",
            "profile": {
                "face_length_ratio": 1.35,
                "jaw_width_ratio": 0.85,
                "upper_width_ratio": 0.96,
                "lower_face_ratio": 0.44,
                "symmetry": 0.72,
                "face_shape": "oval",
                "jawline": "angular",
                "forehead": "medium",
                "hairline": "straight",
                "gender": "male",
            },
            "categories": ["hair"],
            "top_n": 3,
            "ranking_mode": "confidence_aware",
            "confidence_source": "manual",
            "attribute_confidence": facial_ones,
        },
    )


@router.get("/api/v1/styles", response_model=StylesResponse, tags=["catalogue"])
def list_styles(
    artifacts: ArtifactsDep,
    category: str | None = Query(
        default=None,
        description="Optional category filter: hair, beard, or grooming",
    ),
) -> StylesResponse:
    if artifacts.catalogue.empty:
        raise HTTPException(status_code=503, detail="Style catalogue not loaded")
    df = artifacts.catalogue
    if category is not None:
        token = category.strip().lower()
        if token not in SUPPORTED_CATEGORIES:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Unsupported category={category!r}. "
                    f"Supported: {list(SUPPORTED_CATEGORIES)}"
                ),
            )
        df = df.loc[df["category"] == token]
    styles = [StyleRecord(**_style_row_to_dict(row)) for _, row in df.iterrows()]
    return StylesResponse(count=len(styles), styles=styles)


def _style_row_to_dict(row: Any) -> dict[str, Any]:
    return {
        "style_id": str(row["style_id"]),
        "category": str(row["category"]),
        "style_name": str(row["style_name"]),
        "definition": None if _is_blank(row.get("definition")) else str(row.get("definition")),
        "reference_image": (
            None
            if _is_blank(row.get("reference_image"))
            else str(row.get("reference_image"))
        ),
        "catalogue_status": (
            None
            if _is_blank(row.get("catalogue_status"))
            else str(row.get("catalogue_status"))
        ),
        "definition_status": (
            None
            if _is_blank(row.get("definition_status"))
            else str(row.get("definition_status"))
        ),
        "gender_restriction": (
            None
            if _is_blank(row.get("gender_restriction"))
            else str(row.get("gender_restriction"))
        ),
        "requires_facial_hair": bool(row.get("requires_facial_hair", False)),
        "availability_constraints_validated": bool(
            row.get("availability_constraints_validated", False)
        ),
    }


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    text = str(value).strip()
    return text == "" or text.lower() == "nan"


@router.get("/api/v1/models/info", response_model=ModelInfoResponse, tags=["meta"])
def models_info(artifacts: ArtifactsDep) -> ModelInfoResponse:
    training_rows = {}
    if not artifacts.training_summary.empty and "model" in artifacts.training_summary.columns:
        for _, row in artifacts.training_summary.iterrows():
            training_rows[str(row["model"])] = row.to_dict()

    models: list[ModelArtifactInfo] = []
    for category, loaded in artifacts.rankers.items():
        summary_key = loaded.filename.replace(".cbm", "")
        summary = training_rows.get(summary_key, {})
        models.append(
            ModelArtifactInfo(
                name=loaded.name,
                role=loaded.role,
                filename=loaded.filename,
                sha256=loaded.sha256,
                feature_names=loaded.feature_names,
                categorical_feature_names=loaded.categorical_names,
                loaded=True,
                training_rows=_as_optional_int(summary.get("training_rows")),
                validation_rows=_as_optional_int(summary.get("validation_rows")),
                trees=_as_optional_int(summary.get("trees")),
            )
        )
    if artifacts.scorer is not None:
        loaded = artifacts.scorer
        summary_key = loaded.filename.replace(".cbm", "")
        summary = training_rows.get(summary_key, {})
        models.append(
            ModelArtifactInfo(
                name=loaded.name,
                role=loaded.role,
                filename=loaded.filename,
                sha256=loaded.sha256,
                feature_names=loaded.feature_names,
                categorical_feature_names=loaded.categorical_names,
                loaded=True,
                training_rows=_as_optional_int(summary.get("training_rows")),
                validation_rows=_as_optional_int(summary.get("validation_rows")),
                trees=_as_optional_int(summary.get("trees")),
            )
        )

    evaluation = None
    if not artifacts.evaluation.empty:
        rows = artifacts.evaluation.to_dict(orient="records")
        evaluation = EvaluationSummary(
            source="gender_evaluation.csv",
            disclaimer=(
                "Metrics measure agreement with rule-generated ratings on held-out "
                "generated data. They are not real-world human suitability accuracy."
            ),
            rows=rows,
        )

    run = artifacts.run_information
    return ModelInfoResponse(
        artifact_version=artifacts.artifact_version,
        catboost_version_trained=run.get("catboost_version"),
        gender_feature_used=run.get("gender_feature_used"),
        female_beard_rows_removed=run.get("female_beard_rows_removed"),
        rating_source=artifacts.schema.get("rating_source")
        or artifacts.dataset_metadata.get("rating_source"),
        confidence_calibrated=bool(
            artifacts.schema.get("confidence_calibrated", False)
        ),
        models=models,
        evaluation=evaluation,
        notes=[
            "Absolute filesystem paths are intentionally omitted.",
            "Do not interpret generated-data agreement as human validation.",
            "Confidence calibration has not been performed.",
        ],
    )


def _as_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


@router.post(
    "/api/v1/recommendations",
    response_model=RecommendationResponse,
    tags=["recommendations"],
)
def create_recommendations(
    payload: RecommendationRequest,
    request: Request,
    engine: EngineDep,
    settings: SettingsDep,
) -> RecommendationResponse:
    request_id = _request_id(request)
    logger.info(
        "recommendation_request categories=%s top_n=%s gender=%s",
        payload.categories,
        payload.top_n,
        payload.profile.gender,
        extra={"request_id": request_id},
    )
    if payload.top_n > settings.max_top_n:
        raise HTTPException(
            status_code=422,
            detail=f"top_n must be <= {settings.max_top_n}",
        )
    try:
        response = engine.recommend(payload, request_id=request_id)
    except RecommendationNotReadyError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "message": exc.message,
                "diagnostics": exc.diagnostics,
            },
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    logger.info(
        "recommendation_complete returned_categories=%s",
        [c.category for c in response.category_results if c.status == "ok"],
        extra={"request_id": request_id},
    )
    return response
