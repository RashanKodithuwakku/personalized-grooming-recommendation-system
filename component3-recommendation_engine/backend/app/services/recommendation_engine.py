"""Hybrid style recommendation and ranking engine."""

from __future__ import annotations

import math
from typing import Any, Literal

import numpy as np
import pandas as pd

from app.core.config import Settings
from app.core.exceptions import RecommendationNotReadyError
from app.core.logging import get_logger
from app.schemas.requests import ProfileFeatures, RecommendationRequest
from app.schemas.responses import (
    CategoryInputQualityInfo,
    CategoryResult,
    InputQualityInfo,
    RankingPolicyInfo,
    RecommendationItem,
    RecommendationResponse,
    SkippedCategory,
)
from app.services.artifact_loader import ArtifactBundle
from app.services.compatibility_rules import RuleEvaluation
from app.services.confidence_aware_rules import (
    adjust_rule_evaluation,
    facial_confidence_vector,
    hybrid_score_with_rule_term,
)
from app.services.eligibility import EligibilityService
from app.services.explanation_service import ExplanationService
from app.services.feature_builder import FeatureBuilder
from app.services.input_quality_service import InputQualityService

logger = get_logger(__name__)

RATING_MIN = 1.0
RATING_MAX = 5.0

RankingMode = Literal["standard", "confidence_aware"]


def clip_rating(value: float) -> float:
    return float(min(RATING_MAX, max(RATING_MIN, value)))


def compatibility_score_0_100(clipped_rating: float) -> float:
    """Rescale clipped predicted rating to 0–100.

    compatibility_score = 100 * (clipped_rating - 1) / 4

    This is a rescaled predicted rating, not accuracy or confidence.
    """
    return float(100.0 * (clipped_rating - RATING_MIN) / (RATING_MAX - RATING_MIN))


def normalize_predicted_compatibility(clipped_rating: float) -> float:
    """Map clipped 1–5 rating to [0, 1] for hybrid mixing."""
    return float((clipped_rating - RATING_MIN) / (RATING_MAX - RATING_MIN))


def tie_aware_rank_percentiles(scores: list[float]) -> list[float]:
    """Compute within-category rank percentiles with average ranks for ties.

    Higher raw ranker score => better rank => higher percentile.
    Single-candidate categories receive percentile 1.0.
    """
    n = len(scores)
    if n == 0:
        return []
    if n == 1:
        return [1.0]

    order = sorted(range(n), key=lambda i: (-scores[i],))
    percentiles = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and scores[order[j + 1]] == scores[order[i]]:
            j += 1
        # Average 1-based ranks for the tied group.
        avg_rank = (i + 1 + j + 1) / 2.0
        # Percentile: best rank (1) -> 1.0, worst rank (n) -> 1/n.
        percentile = (n - avg_rank + 1.0) / n
        for k in range(i, j + 1):
            percentiles[order[k]] = float(percentile)
        i = j + 1
    return percentiles


class RecommendationEngine:
    """Run the hybrid recommendation pipeline using loaded artifacts."""

    def __init__(self, bundle: ArtifactBundle, settings: Settings) -> None:
        self.bundle = bundle
        self.settings = settings
        self.eligibility = EligibilityService()
        self.explanations = ExplanationService()

    def ensure_ready(self) -> None:
        if not self.bundle.ready:
            raise RecommendationNotReadyError(
                "Recommendation engine is not ready",
                diagnostics=list(self.bundle.diagnostics),
            )

    def ranking_policy_info(
        self,
        *,
        ranking_mode: RankingMode = "standard",
        confidence_source: str = "unspecified",
        fallback_applied: bool = False,
        fallback_reason: str | None = None,
        rules_available: bool | None = None,
    ) -> RankingPolicyInfo:
        if rules_available is None:
            rules_available = bool(self.bundle.rules and self.bundle.rules.available)
        verified = (
            sorted(self.bundle.rules.verified_categories)
            if self.bundle.rules and self.bundle.rules.available
            else []
        )
        weights = self.settings.hybrid_weights(rules_available)

        active_mode: RankingMode = "standard"
        adjusts_rules = False
        fallback_policy_name = None

        if ranking_mode == "confidence_aware" and not fallback_applied and rules_available:
            active_mode = "confidence_aware"
            adjusts_rules = True
            name = "hybrid_confidence_adjusted_rules_v1"
            description = (
                "Confidence-aware hybrid ordering: "
                f"{weights.get('predicted_compatibility', 0.0):.2f} * "
                "normalized predicted compatibility + "
                f"{weights.get('rank_percentile', 0.0):.2f} * "
                "within-category rank percentile + "
                f"{weights.get('rule_compatibility', 0.0):.2f} * "
                "confidence_adjusted_rule_score "
                f"(verified categories={verified}). "
                "Adjusts only the rule component using manually/upstream-supplied "
                "attribute confidence. CatBoost models still consume profile values "
                "without uncertainty propagation. Not research-validated."
            )
        elif ranking_mode == "confidence_aware" and fallback_applied:
            active_mode = "standard"
            fallback_policy_name = (
                "hybrid_model_rank_rules_v1"
                if rules_available
                else "hybrid_model_rank_v1"
            )
            name = fallback_policy_name
            description = (
                "Fallback to standard hybrid ranking because confidence-aware "
                "rule coverage A = sum(w_i * c_i) was zero (all facial confidence "
                "values were zero, or effective weight sum was zero). "
                + (
                    "Provisional hybrid: "
                    f"{weights.get('predicted_compatibility', 0.0):.2f} * "
                    "normalized predicted compatibility + "
                    f"{weights.get('rank_percentile', 0.0):.2f} * "
                    "rank percentile + "
                    f"{weights.get('rule_compatibility', 0.0):.2f} * "
                    "original rule_compatibility_score."
                    if rules_available
                    else "Provisional hybrid without rule term."
                )
            )
        elif rules_available:
            name = "hybrid_model_rank_rules_v1"
            description = (
                "Provisional hybrid ordering for rule-verified categories: "
                "0.50 * normalized predicted compatibility + "
                "0.30 * within-category rank percentile + "
                "0.20 * normalized rule compatibility "
                f"(verified categories={verified}; weights configurable; "
                "not research-validated)."
            )
        else:
            name = "hybrid_model_rank_v1"
            description = (
                "Provisional hybrid ordering without verified rule parameters: "
                "0.70 * normalized predicted compatibility + "
                "0.30 * within-category rank percentile "
                "(weights configurable; not research-validated)."
            )

        return RankingPolicyInfo(
            policy_name=name,
            description=description,
            weights=weights,
            provisional=True,
            note=(
                "These are provisional application weights, not learned or "
                "research-validated weights, and not the original training formula. "
                "Rule parameters themselves remain provisional_unvalidated research "
                "artifacts even when dataset-label parity is verified. "
                "confidence_source is provenance only and does not change scores. "
                "recommendation_support_score is a heuristic confidence-weighted "
                "rule-support score, not a probability or calibrated confidence."
            ),
            requested_ranking_mode=ranking_mode,
            active_ranking_mode=active_mode,
            available_ranking_modes=["standard", "confidence_aware"],
            fallback_applied=fallback_applied,
            fallback_reason=fallback_reason,
            fallback_policy_name=fallback_policy_name,
            adjusts_rule_component_only=adjusts_rules,
            confidence_source=confidence_source,  # type: ignore[arg-type]
            confidence_source_affects_scores=False,
        )

    def recommend(
        self,
        request: RecommendationRequest,
        request_id: str,
    ) -> RecommendationResponse:
        self.ensure_ready()
        if request.top_n > self.settings.max_top_n:
            raise ValueError(f"top_n exceeds maximum of {self.settings.max_top_n}")

        warnings = self._ood_warnings(request.profile)
        rules_service = self.bundle.rules
        category_rule_weights = (
            rules_service.parameters.weights
            if rules_service is not None and rules_service.parameters is not None
            else None
        )
        quality_service = InputQualityService(
            caution_threshold=self.settings.input_quality_caution_threshold,
            low_confidence_attribute_threshold=(
                self.settings.low_confidence_attribute_threshold
            ),
            min_coverage=self.settings.input_quality_min_coverage,
            category_rule_weights=category_rule_weights,
        )
        quality_payload = quality_service.evaluate(
            attribute_confidence=request.attribute_confidence,
            requested_categories=list(request.categories),
        )
        if quality_payload["caution_flag"]:
            reasons = ", ".join(quality_payload.get("caution_reasons") or [])
            warnings.append(
                "Input quality caution ("
                f"assessment={quality_payload['assessment']}"
                + (f"; reasons={reasons}" if reasons else "")
                + "). This is confidence-aware flagging of Top-N results using an "
                "input-quality heuristic; it does not measure recommendation "
                "correctness. In ranking_mode=standard it does not reorder hybrid "
                "scores. In ranking_mode=confidence_aware the rule term may change "
                "ordering while quality flags remain visible. "
                "Unknown confidence is not treated as adequate quality."
            )

        ranking_mode: RankingMode = request.ranking_mode
        confidence_source = request.confidence_source
        facial_conf: dict[str, float] | None = None
        fallback_applied = False
        fallback_reason: str | None = None

        if ranking_mode == "confidence_aware":
            assert request.attribute_confidence is not None
            facial_conf = facial_confidence_vector(request.attribute_confidence)
            # All-zero facial confidence => A = 0 for every category weight vector.
            if all(value == 0.0 for value in facial_conf.values()):
                fallback_applied = True
                fallback_reason = (
                    "confidence_aware_zero_coverage_fallback: all nine facial "
                    "confidence values are 0, so A = sum(w_i * c_i) = 0. "
                    "Avoided divide-by-zero; fell back to standard ranking with "
                    "original rule_compatibility_score. "
                    "recommendation_support_score=0 and "
                    "confidence_adjusted_rule_score=null."
                )
                warnings.append(fallback_reason)

        rules_available = bool(rules_service and rules_service.available)
        policy = self.ranking_policy_info(
            ranking_mode=ranking_mode,
            confidence_source=confidence_source,
            fallback_applied=fallback_applied,
            fallback_reason=fallback_reason,
            rules_available=rules_available,
        )

        category_results: list[CategoryResult] = []
        skipped: list[SkippedCategory] = []
        category_quality_map = quality_payload.get("category_input_quality") or {}

        use_confidence_adjusted = (
            ranking_mode == "confidence_aware"
            and not fallback_applied
            and facial_conf is not None
        )

        for category in request.categories:
            cat_quality_raw = category_quality_map.get(category)
            if not cat_quality_raw:
                cat_quality_raw = quality_service._category_quality(
                    category,
                    {},
                    "not_provided",
                )
            disposition = quality_service.disposition_for_category(cat_quality_raw)

            # All-zero confidence_aware fallback always requires review.
            if fallback_applied:
                disposition = {
                    "recommendation_disposition": "review_required",
                    "disposition_reasons": [
                        "confidence_aware_zero_coverage_fallback",
                        *list(disposition.get("disposition_reasons") or []),
                    ],
                    "disposition_explanation": (
                        "ranking_mode=confidence_aware received an all-zero facial "
                        "confidence map. Ranking fell back to the standard hybrid "
                        "policy; review is required because rule confidence coverage "
                        "is zero."
                    ),
                }

            cat_quality_model = (
                CategoryInputQualityInfo(**{
                    k: v
                    for k, v in cat_quality_raw.items()
                    if k in CategoryInputQualityInfo.model_fields
                })
                if cat_quality_raw
                else None
            )

            catalogue = self.bundle.styles_by_category.get(category, pd.DataFrame())
            decision = self.eligibility.evaluate_category(
                category=category,
                profile=request.profile,
                preferences=request.preferences,
                catalogue_category=catalogue,
            )
            if not decision.include_category:
                skipped.append(
                    SkippedCategory(
                        category=category,
                        reason=decision.skip_reason or "Skipped",
                        status=decision.skip_status or "skipped",
                    )
                )
                category_results.append(
                    CategoryResult(
                        category=category,
                        status="skipped",
                        eligible_count=0,
                        returned_count=0,
                        recommendations=[],
                        empty_reason=decision.skip_reason,
                        applied_eligibility_rules=decision.applied_rules,
                        recommendation_disposition=disposition[
                            "recommendation_disposition"
                        ],
                        disposition_reasons=disposition["disposition_reasons"],
                        disposition_explanation=disposition[
                            "disposition_explanation"
                        ],
                        category_input_quality=cat_quality_model,
                    )
                )
                continue

            if decision.eligible_styles.empty:
                category_results.append(
                    CategoryResult(
                        category=category,
                        status="empty",
                        eligible_count=0,
                        returned_count=0,
                        recommendations=[],
                        empty_reason=decision.empty_reason,
                        applied_eligibility_rules=decision.applied_rules,
                        recommendation_disposition=disposition[
                            "recommendation_disposition"
                        ],
                        disposition_reasons=disposition["disposition_reasons"],
                        disposition_explanation=disposition[
                            "disposition_explanation"
                        ],
                        category_input_quality=cat_quality_model,
                    )
                )
                continue

            category_rules = bool(
                rules_service and rules_service.category_verified(category)
            )
            category_weights = self.settings.hybrid_weights(category_rules)
            items = self._rank_category(
                category=category,
                profile=request.profile,
                styles=decision.eligible_styles,
                top_n=request.top_n,
                applied_rules=decision.applied_rules,
                policy_weights=category_weights,
                rules_available=category_rules,
                use_confidence_adjusted=use_confidence_adjusted,
                facial_conf=facial_conf,
                fallback_zero_coverage=fallback_applied,
            )
            category_results.append(
                CategoryResult(
                    category=category,
                    status="ok",
                    eligible_count=len(decision.eligible_styles),
                    returned_count=len(items),
                    recommendations=items,
                    applied_eligibility_rules=decision.applied_rules,
                    recommendation_disposition=disposition[
                        "recommendation_disposition"
                    ],
                    disposition_reasons=disposition["disposition_reasons"],
                    disposition_explanation=disposition["disposition_explanation"],
                    category_input_quality=cat_quality_model,
                )
            )

        notes = [
            "Raw ranker scores are not probabilities and must not be compared across categories.",
            "compatibility_score is a rescaled predicted rating, not accuracy or confidence.",
            "rule_compatibility_score is original weighted rule agreement, not confidence.",
            "confidence_adjusted_rule_score adjusts only the rule term using supplied "
            "attribute confidence (ranking_mode=confidence_aware).",
            "recommendation_support_score is a heuristic confidence-weighted rule-support "
            "score (S_j), not a probability or calibrated recommendation confidence.",
            "hybrid_score is the ordering score; input_quality_score is heuristic input reliability.",
            "recommendation_confidence is null (status=not_calibrated) until calibration evidence exists.",
            "confidence_source is provenance only and does not change scores.",
            "Evaluation metrics in model metadata measure agreement with rule-generated ratings, "
            "not real-world human suitability accuracy.",
            "Human suitability validation and calibrated recommendation confidence remain unfinished research work.",
        ]
        if ranking_mode == "standard":
            notes.append(
                "ranking_mode=standard (default): confidence-aware Top-N flagging "
                "does not reorder candidates."
            )
        elif use_confidence_adjusted:
            notes.append(
                "ranking_mode=confidence_aware with policy "
                "hybrid_confidence_adjusted_rules_v1: only the rule hybrid term uses "
                "confidence_adjusted_rule_score. CatBoost models still use profile "
                "values without uncertainty propagation."
            )
        if fallback_applied:
            notes.append(fallback_reason or "Fell back to standard ranking policy.")
        if rules_available and rules_service is not None:
            notes.append(
                "Weighted compatibility rules enabled for verified categories "
                f"{sorted(rules_service.verified_categories)} using recovered "
                "rating_parameters.json (parameter_status="
                f"{rules_service.parameter_status}). "
                "Parity was checked against training_pairs.rating labels."
            )
            notes.append(
                "Rule parameters remain provisional_unvalidated; dataset-label "
                "parity does not imply human expert validation."
            )
        else:
            notes.append(
                "Weighted compatibility rules unavailable or unverified. "
                "Hybrid ordering uses model scores only for affected categories."
            )

        input_quality_fields = {
            key: value
            for key, value in quality_payload.items()
            if key in InputQualityInfo.model_fields
        }
        return RecommendationResponse(
            request_id=request_id,
            schema_version="1.0",
            artifact_version=self.bundle.artifact_version,
            ranking_mode=ranking_mode,
            confidence_source=confidence_source,
            ranking_policy=policy,
            overall_warnings=warnings,
            input_quality=InputQualityInfo(**input_quality_fields),
            recommendation_confidence=None,
            recommendation_confidence_status="not_calibrated",
            category_results=category_results,
            skipped_categories=skipped,
            notes=notes,
        )

    def input_quality_policy_info(self) -> dict[str, Any]:
        rules_service = self.bundle.rules
        category_rule_weights = (
            rules_service.parameters.weights
            if rules_service is not None and rules_service.parameters is not None
            else None
        )
        service = InputQualityService(
            caution_threshold=self.settings.input_quality_caution_threshold,
            low_confidence_attribute_threshold=(
                self.settings.low_confidence_attribute_threshold
            ),
            min_coverage=self.settings.input_quality_min_coverage,
            category_rule_weights=category_rule_weights,
        )
        return service.policy_capabilities()

    def _rank_category(
        self,
        *,
        category: str,
        profile: ProfileFeatures,
        styles: pd.DataFrame,
        top_n: int,
        applied_rules: list[str],
        policy_weights: dict[str, float],
        rules_available: bool,
        use_confidence_adjusted: bool = False,
        facial_conf: dict[str, float] | None = None,
        fallback_zero_coverage: bool = False,
    ) -> list[RecommendationItem]:
        ranker = self.bundle.rankers[category]
        scorer = self.bundle.scorer
        assert scorer is not None

        builder = FeatureBuilder(feature_names=ranker.feature_names)
        features = builder.build_candidates(profile, styles)

        thread_count = self.settings.catboost_thread_count
        ranker_scores = np.asarray(
            ranker.model.predict(features, thread_count=thread_count),
            dtype=float,
        )
        scorer_builder = FeatureBuilder(feature_names=scorer.feature_names)
        scorer_features = scorer_builder.build_candidates(profile, styles)
        raw_ratings = np.asarray(
            scorer.model.predict(scorer_features, thread_count=thread_count),
            dtype=float,
        )

        if len(ranker_scores) != len(styles) or len(raw_ratings) != len(styles):
            raise RuntimeError(
                f"Model output length mismatch for category={category}"
            )

        percentiles = tie_aware_rank_percentiles(ranker_scores.tolist())
        category_weights_list: list[float] | None = None
        if (
            self.bundle.rules is not None
            and self.bundle.rules.parameters is not None
            and category in self.bundle.rules.parameters.weights
        ):
            category_weights_list = list(
                self.bundle.rules.parameters.weights[category]
            )

        records: list[dict[str, Any]] = []

        for idx, (_, style) in enumerate(styles.iterrows()):
            raw_rank = float(ranker_scores[idx])
            raw_rating = float(raw_ratings[idx])
            if not math.isfinite(raw_rank) or not math.isfinite(raw_rating):
                raise RuntimeError(
                    f"Non-finite model output for style_id={style['style_id']}"
                )
            display_rating = clip_rating(raw_rating)
            compat_score = compatibility_score_0_100(display_rating)
            norm_pred = normalize_predicted_compatibility(display_rating)
            percentile = percentiles[idx]

            if self.bundle.rules is not None:
                rule_eval = self.bundle.rules.evaluate(
                    profile=profile,
                    style_id=str(style["style_id"]),
                    category=category,
                    style_meta=style.to_dict(),
                )
            else:
                rule_eval = RuleEvaluation(
                    available=False,
                    score=None,
                    contributions=[],
                    status="unavailable",
                    detail="Rules service not initialized",
                )

            rule_score = None
            if rule_eval.score is not None and (
                rule_eval.category_verified or rule_eval.available
            ):
                rule_score = float(rule_eval.score)

            rule_confidence_coverage = None
            recommendation_support_score = None
            confidence_adjusted_rule_score = None
            explanation_contributions = rule_eval.contributions
            rule_term_for_hybrid = (
                rule_score
                if rules_available and rule_eval.category_verified and rule_score is not None
                else None
            )

            if (
                (use_confidence_adjusted or fallback_zero_coverage)
                and facial_conf is not None
                and category_weights_list is not None
                and rule_eval.contributions
                and rule_score is not None
            ):
                adjusted = adjust_rule_evaluation(
                    weights=category_weights_list,
                    facial_conf=facial_conf,
                    original_contributions=rule_eval.contributions,
                    original_score=rule_score,
                )
                rule_confidence_coverage = adjusted["rule_confidence_coverage"]
                recommendation_support_score = adjusted[
                    "recommendation_support_score"
                ]
                confidence_adjusted_rule_score = adjusted[
                    "confidence_adjusted_rule_score"
                ]
                explanation_contributions = adjusted["contributions"]
                if use_confidence_adjusted and confidence_adjusted_rule_score is not None:
                    rule_term_for_hybrid = confidence_adjusted_rule_score
                # fallback_zero_coverage keeps original rule_term_for_hybrid

            hybrid = hybrid_score_with_rule_term(
                normalized_predicted_compatibility=norm_pred,
                rank_percentile=percentile,
                rule_term=rule_term_for_hybrid,
                weights=policy_weights,
            )

            requires_fh = bool(style.get("requires_facial_hair", False))
            explanation = self.explanations.build_item_explanation(
                style_name=str(style["style_name"]),
                category=category,
                requires_facial_hair=requires_fh,
                applied_rules=applied_rules,
                rule_eval=rule_eval,
                hybrid_weights=policy_weights,
                rules_available=rules_available,
                ranking_mode=(
                    "confidence_aware" if use_confidence_adjusted else "standard"
                ),
                fallback_zero_coverage=fallback_zero_coverage,
                confidence_adjusted_rule_score=confidence_adjusted_rule_score,
                recommendation_support_score=recommendation_support_score,
                rule_confidence_coverage=rule_confidence_coverage,
                override_contributions=explanation_contributions,
            )

            records.append(
                {
                    "style_id": str(style["style_id"]),
                    "style_name": str(style["style_name"]),
                    "category": category,
                    "raw_ranker_score": raw_rank,
                    "raw_predicted_compatibility_rating": raw_rating,
                    "display_compatibility_rating": display_rating,
                    "compatibility_score": compat_score,
                    "rank_percentile": percentile,
                    "normalized_predicted_compatibility": norm_pred,
                    "rule_compatibility_score": rule_score,
                    "rule_confidence_coverage": rule_confidence_coverage,
                    "recommendation_support_score": recommendation_support_score,
                    "confidence_adjusted_rule_score": confidence_adjusted_rule_score,
                    "hybrid_score": float(hybrid),
                    "requires_facial_hair": requires_fh,
                    "explanation": explanation,
                }
            )

        records.sort(key=lambda r: (-r["hybrid_score"], r["style_id"]))
        top = records[:top_n]
        items: list[RecommendationItem] = []
        for rank, row in enumerate(top, start=1):
            items.append(
                RecommendationItem(
                    rank=rank,
                    style_id=row["style_id"],
                    style_name=row["style_name"],
                    category=row["category"],
                    raw_ranker_score=row["raw_ranker_score"],
                    raw_predicted_compatibility_rating=row[
                        "raw_predicted_compatibility_rating"
                    ],
                    display_compatibility_rating=row["display_compatibility_rating"],
                    compatibility_score=row["compatibility_score"],
                    rank_percentile=row["rank_percentile"],
                    normalized_predicted_compatibility=row[
                        "normalized_predicted_compatibility"
                    ],
                    rule_compatibility_score=row["rule_compatibility_score"],
                    rule_confidence_coverage=row["rule_confidence_coverage"],
                    recommendation_support_score=row["recommendation_support_score"],
                    confidence_adjusted_rule_score=row[
                        "confidence_adjusted_rule_score"
                    ],
                    hybrid_score=row["hybrid_score"],
                    requires_facial_hair=row["requires_facial_hair"],
                    explanation=row["explanation"],
                )
            )
        return items

    def _ood_warnings(self, profile: ProfileFeatures) -> list[str]:
        warnings: list[str] = []
        ranges = self.bundle.empirical_numeric_ranges
        if not ranges:
            return warnings
        payload = profile.model_dump()
        for feature, stats in ranges.items():
            value = float(payload[feature])
            low = stats["min"]
            high = stats["max"]
            if value < low or value > high:
                warnings.append(
                    f"Out-of-distribution warning for {feature}={value:.6f}: "
                    f"outside empirical training range [{low:.6f}, {high:.6f}]. "
                    "These are empirical training ranges, not biological limits."
                )
        return warnings
