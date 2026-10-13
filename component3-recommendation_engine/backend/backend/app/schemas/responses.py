"""API response schemas documented in OpenAPI."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthLiveResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str
    version: str


class HealthReadyResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    ready: bool
    diagnostics: list[str] = Field(default_factory=list)
    models_loaded: dict[str, bool] = Field(default_factory=dict)
    catalogue_loaded: bool = False
    schema_loaded: bool = False
    rules_available: bool = False


class StyleRecord(BaseModel):
    style_id: str
    category: str
    style_name: str
    definition: str | None = None
    reference_image: str | None = None
    catalogue_status: str | None = None
    definition_status: str | None = None
    gender_restriction: str | None = None
    requires_facial_hair: bool = False
    availability_constraints_validated: bool = False


class StylesResponse(BaseModel):
    count: int
    styles: list[StyleRecord]


class RankingPolicyInfo(BaseModel):
    policy_name: str
    description: str
    weights: dict[str, float]
    provisional: bool = True
    note: str
    requested_ranking_mode: Literal["standard", "confidence_aware"] = "standard"
    active_ranking_mode: Literal["standard", "confidence_aware"] = "standard"
    available_ranking_modes: list[str] = Field(
        default_factory=lambda: ["standard", "confidence_aware"]
    )
    fallback_applied: bool = False
    fallback_reason: str | None = None
    fallback_policy_name: str | None = None
    adjusts_rule_component_only: bool = False
    confidence_source: Literal["manual", "upstream", "unspecified"] = "unspecified"
    confidence_source_affects_scores: bool = False


class ModelCoverageLimitation(BaseModel):
    category: str
    limitation: str
    status: str


class CatalogueCoverageInfo(BaseModel):
    hair_style_count: int
    beard_style_count: int
    grooming_style_count: int
    total_style_count: int
    grooming_focus: str
    unsupported_preference_inputs: list[str]
    notes: list[str]


class ConfidencePolicyInfo(BaseModel):
    policy_name: str
    description: str
    facial_attributes: list[str]
    expected_attribute_count: int
    gender_excluded_from_facial_aggregate: bool
    caution_threshold: float
    low_confidence_attribute_threshold: float
    min_coverage: float
    assessment_precedence: list[str]
    disposition_values: list[str]
    recommendation_confidence_status: Literal["not_calibrated"] = "not_calibrated"
    limitations: list[str]


class CapabilitiesResponse(BaseModel):
    schema_version: str = "1.0"
    available_categories: list[str]
    model_readiness: dict[str, bool]
    recommendation_ready: bool
    rules_available: bool
    rules_status: str
    missing_rule_artifact: str | None = None
    rule_parameter_status: str | None = None
    rule_verified_categories: list[str] = Field(default_factory=list)
    rule_covered_style_ids: list[str] = Field(default_factory=list)
    rule_formula: str | None = None
    rule_similarity_definition: str | None = None
    rule_parity: dict[str, Any] | None = None
    rule_provenance: str | None = None
    catalogue_coverage: CatalogueCoverageInfo | None = None
    confidence_policy: ConfidencePolicyInfo | None = None
    supported_genders: list[str]
    supported_face_shapes: list[str]
    supported_jawlines: list[str]
    supported_foreheads: list[str]
    supported_hairlines: list[str]
    confidence_calibration_status: Literal["not_calibrated"] = "not_calibrated"
    ranking_policy: RankingPolicyInfo
    available_ranking_modes: list[str] = Field(
        default_factory=lambda: ["standard", "confidence_aware"]
    )
    ranking_mode_notes: list[str] = Field(default_factory=list)
    model_coverage_limitations: list[ModelCoverageLimitation]
    rating_scale: dict[str, Any]
    compatibility_score_definition: str
    score_terminology: dict[str, str] = Field(default_factory=dict)
    notes: list[str]


class UpstreamFieldContract(BaseModel):
    field: str
    required: bool
    role: str
    notes: str


class InputSchemaResponse(BaseModel):
    schema_version: str = "1.0"
    profile_features: list[str]
    model_features: list[str]
    categorical_features: list[str]
    numeric_features: list[str]
    supported_categories: list[str]
    supported_genders: list[str]
    categorical_values: dict[str, list[str]]
    preferences_fields: list[str]
    attribute_confidence_keys: list[str]
    facial_confidence_attributes: list[str]
    ranking_modes: list[str] = Field(
        default_factory=lambda: ["standard", "confidence_aware"]
    )
    confidence_sources: list[str] = Field(
        default_factory=lambda: ["manual", "upstream", "unspecified"]
    )
    ranking_mode_requirements: dict[str, str] = Field(default_factory=dict)
    top_n_limits: dict[str, int]
    empirical_numeric_ranges: dict[str, dict[str, float]] | None = None
    empirical_ranges_note: str
    upstream_integration_contract: list[UpstreamFieldContract] = Field(
        default_factory=list
    )
    request_example: dict[str, Any]
    confidence_aware_request_example: dict[str, Any] | None = None


class EvaluationSummary(BaseModel):
    source: str
    disclaimer: str
    rows: list[dict[str, Any]] = Field(default_factory=list)


class ModelArtifactInfo(BaseModel):
    name: str
    role: str
    filename: str
    sha256: str | None = None
    feature_names: list[str] = Field(default_factory=list)
    categorical_feature_names: list[str] = Field(default_factory=list)
    loaded: bool
    training_rows: int | None = None
    validation_rows: int | None = None
    trees: int | None = None


class ModelInfoResponse(BaseModel):
    artifact_version: str
    catboost_version_trained: str | None = None
    gender_feature_used: bool | None = None
    female_beard_rows_removed: bool | None = None
    rating_source: str | None = None
    confidence_calibrated: bool = False
    models: list[ModelArtifactInfo]
    evaluation: EvaluationSummary | None = None
    notes: list[str]


class RuleContribution(BaseModel):
    attribute: str
    contribution: float = Field(
        ...,
        description="Weight × similarity contribution to weighted_compatibility.",
    )
    similarity: float | None = Field(
        default=None,
        description="Per-attribute similarity in [0, 1].",
    )
    weight: float | None = Field(
        default=None,
        description="Category-specific term weight from rating_parameters.json.",
    )
    confidence: float | None = Field(
        default=None,
        description=(
            "Supplied facial attribute confidence in [0, 1] when ranking_mode="
            "confidence_aware. Absent in standard mode."
        ),
    )
    effective_weight: float | None = Field(
        default=None,
        description="w_i * c_i for confidence-aware rule scoring.",
    )
    support_contribution: float | None = Field(
        default=None,
        description="w_i * c_i * s_ij contribution to recommendation_support_score.",
    )
    detail: str | None = None


class RecommendationExplanation(BaseModel):
    summary: str
    pipeline_stages: list[str] = Field(default_factory=list)
    applied_eligibility_rules: list[str]
    requires_facial_hair: bool
    score_sources: dict[str, str]
    rule_contributions: list[RuleContribution] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class CategoryInputQualityInfo(BaseModel):
    category: str
    confidence_status: Literal["not_provided", "partial", "complete"]
    assessment: Literal["unknown", "insufficient_coverage", "low", "adequate"]
    assessment_reasons: list[str] = Field(default_factory=list)
    input_quality_score: float | None = Field(
        default=None,
        description=(
            "Heuristic category input reliability using that category's rule "
            "weights over supplied facial confidence attributes. Not calibrated "
            "recommendation confidence."
        ),
    )
    observed_attribute_count: int
    expected_attribute_count: int = 9
    confidence_coverage: float
    confidence_weight_coverage: float
    confidence_attributes_provided: list[str] = Field(default_factory=list)
    confidence_attributes_missing: list[str] = Field(default_factory=list)
    low_confidence_attributes: list[str] = Field(default_factory=list)
    note: str


class RecommendationItem(BaseModel):
    rank: int
    style_id: str
    style_name: str
    category: str
    raw_ranker_score: float
    raw_predicted_compatibility_rating: float
    display_compatibility_rating: float = Field(
        ...,
        description="Predicted compatibility rating clipped to [1, 5].",
    )
    compatibility_score: float = Field(
        ...,
        description=(
            "Rescaled predicted rating on 0–100 using "
            "100 * (clipped_rating - 1) / 4. Not accuracy or confidence."
        ),
    )
    rank_percentile: float
    normalized_predicted_compatibility: float
    rule_compatibility_score: float | None = Field(
        default=None,
        description=(
            "Original weighted rule agreement (0–1). Unchanged by confidence "
            "adjustment; retained for transparency."
        ),
    )
    rule_confidence_coverage: float | None = Field(
        default=None,
        description=(
            "A = sum(w_i * c_i) for the category. Same for all candidates in a "
            "category. 0–1 scale; not calibrated confidence."
        ),
    )
    recommendation_support_score: float | None = Field(
        default=None,
        description=(
            "S_j = sum(w_i * c_i * s_ij). Heuristic confidence-weighted rule "
            "support (0–1). Not a probability, accuracy, or calibrated "
            "recommendation confidence."
        ),
    )
    confidence_adjusted_rule_score: float | None = Field(
        default=None,
        description=(
            "S_j / A when A > 0; null when A = 0. Used as the rule term in "
            "hybrid_confidence_adjusted_rules_v1. Not calibrated confidence."
        ),
    )
    hybrid_score: float
    requires_facial_hair: bool
    explanation: RecommendationExplanation


class CategoryResult(BaseModel):
    category: str
    status: Literal["ok", "empty", "skipped"]
    eligible_count: int
    returned_count: int
    recommendations: list[RecommendationItem] = Field(default_factory=list)
    empty_reason: str | None = None
    applied_eligibility_rules: list[str] = Field(default_factory=list)
    recommendation_disposition: Literal["standard", "review_required"] | None = None
    disposition_reasons: list[str] = Field(default_factory=list)
    disposition_explanation: str | None = None
    category_input_quality: CategoryInputQualityInfo | None = None


class SkippedCategory(BaseModel):
    category: str
    reason: str
    status: str


class InputQualityInfo(BaseModel):
    confidence_status: Literal["not_provided", "partial", "complete"]
    assessment: Literal["unknown", "insufficient_coverage", "low", "adequate"]
    assessment_reasons: list[str] = Field(default_factory=list)
    input_quality_score: float | None = Field(
        default=None,
        description=(
            "Heuristic equal-weight aggregate over supplied facial confidence "
            "attributes (nine rule attributes; gender excluded). "
            "Not calibrated recommendation confidence."
        ),
    )
    confidence_attributes_provided: list[str] = Field(
        default_factory=list,
        description="Facial attributes for which upstream confidence was supplied.",
    )
    confidence_attributes_missing: list[str] = Field(
        default_factory=list,
        description=(
            "Facial attributes without upstream confidence values. "
            "This is not a list of missing required profile measurements."
        ),
    )
    confidence_coverage: float = Field(
        ...,
        description="observed facial confidence count / 9.",
    )
    confidence_weight_coverage: float = Field(
        ...,
        description=(
            "For the global equal-weight view, same as confidence_coverage. "
            "Category-level objects use category rule-weight sums."
        ),
    )
    observed_attribute_count: int
    expected_attribute_count: int = 9
    # Deprecated aliases — exact same values as the confidence_* fields.
    attributes_provided: list[str] = Field(
        default_factory=list,
        description=(
            "Deprecated alias of confidence_attributes_provided. "
            "Does not mean profile measurements were missing."
        ),
    )
    attributes_missing: list[str] = Field(
        default_factory=list,
        description=(
            "Deprecated alias of confidence_attributes_missing. "
            "Refers to missing confidence values, not missing facial measurements."
        ),
    )
    coverage: float | None = Field(
        default=None,
        description="Deprecated alias of confidence_coverage.",
    )
    low_confidence_attributes: list[str] = Field(default_factory=list)
    caution_flag: bool = False
    caution_reasons: list[str] = Field(default_factory=list)
    caution_threshold: float | None = None
    low_confidence_attribute_threshold: float | None = None
    min_coverage: float | None = None
    gender_confidence_supplied: bool = False
    gender_excluded_from_facial_aggregate: bool = True
    field_deprecations: dict[str, str] = Field(default_factory=dict)
    policy_name: str | None = None
    policy_description: str | None = None
    note: str


class RecommendationResponse(BaseModel):
    request_id: str
    schema_version: str = "1.0"
    artifact_version: str
    ranking_mode: Literal["standard", "confidence_aware"] = "standard"
    confidence_source: Literal["manual", "upstream", "unspecified"] = "unspecified"
    ranking_policy: RankingPolicyInfo
    overall_warnings: list[str] = Field(default_factory=list)
    input_quality: InputQualityInfo
    recommendation_confidence: None = Field(
        default=None,
        description="Calibrated recommendation confidence is not available.",
    )
    recommendation_confidence_status: Literal["not_calibrated"] = "not_calibrated"
    category_results: list[CategoryResult]
    skipped_categories: list[SkippedCategory] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
