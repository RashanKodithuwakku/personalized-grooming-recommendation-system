"""Build transparent, non-causal explanations without an LLM dependency."""

from __future__ import annotations

from app.schemas.responses import RecommendationExplanation, RuleContribution
from app.services.compatibility_rules import RuleEvaluation

PIPELINE_STAGES = [
    "eligibility_filtering",
    "category_catboost_ranker",
    "shared_compatibility_regressor",
    "weighted_facial_attribute_rules",
    "hybrid_ordering",
]


class ExplanationService:
    """Explain ranking sources and eligibility without inventing causal claims."""

    def build_item_explanation(
        self,
        *,
        style_name: str,
        category: str,
        requires_facial_hair: bool,
        applied_rules: list[str],
        rule_eval: RuleEvaluation,
        hybrid_weights: dict[str, float],
        rules_available: bool,
        ranking_mode: str = "standard",
        fallback_zero_coverage: bool = False,
        confidence_adjusted_rule_score: float | None = None,
        recommendation_support_score: float | None = None,
        rule_confidence_coverage: float | None = None,
        override_contributions: list[RuleContribution] | None = None,
    ) -> RecommendationExplanation:
        score_sources = {
            "raw_ranker_score": (
                f"CatBoost {category} ranker output for this candidate within "
                f"the {category} category only. Not a probability and not "
                "comparable across categories."
            ),
            "raw_predicted_compatibility_rating": (
                "Shared CatBoost compatibility regressor prediction on the "
                "training rating scale (approximately 1–5). Ratings in training "
                "were rule-generated, not human-reviewed."
            ),
            "compatibility_score": (
                "Rescaled predicted rating: 100 * (clipped_rating - 1) / 4. "
                "Original model compatibility on a 0–100 scale. "
                "Not measured accuracy and not confidence."
            ),
            "rule_compatibility_score": (
                "Original weighted rule agreement (0–1) from rating_parameters.json. "
                "Not adjusted by attribute confidence."
            ),
            "input_quality_score": (
                "Heuristic input reliability from supplied attribute confidence. "
                "Not a probability of style suitability and not calibrated "
                "recommendation_confidence."
            ),
            "recommendation_confidence": (
                "Unavailable (null / not_calibrated) until calibration evidence exists."
            ),
        }

        if ranking_mode == "confidence_aware" and not fallback_zero_coverage:
            score_sources["confidence_adjusted_rule_score"] = (
                "Confidence-adjusted rule compatibility: "
                "S_j / A where A = sum(w_i * c_i) and "
                "S_j = sum(w_i * c_i * s_ij). Replaces the rule term in "
                "hybrid_confidence_adjusted_rules_v1 only. Not calibrated confidence."
            )
            score_sources["recommendation_support_score"] = (
                "Heuristic confidence-weighted rule-support score S_j = "
                "sum(w_i * c_i * s_ij) on a 0–1 scale. Not a probability, accuracy, "
                "or calibrated recommendation confidence. Exposed with "
                "rule_confidence_coverage so a high adjusted score on low coverage "
                "is not mistaken for strong evidence."
            )
            score_sources["rule_confidence_coverage"] = (
                "A = sum(w_i * c_i) over the nine facial attributes for this "
                "category. Same for all candidates in the category."
            )
            score_sources["hybrid_score"] = (
                "Ordering score from hybrid_confidence_adjusted_rules_v1: "
                "mix of normalized predicted compatibility, rank percentile, and "
                "confidence_adjusted_rule_score "
                f"(weights={hybrid_weights}). Adjusts only the rule component; "
                "CatBoost models still consume profile values without uncertainty "
                "propagation. Not calibrated recommendation confidence."
            )
        else:
            score_sources["hybrid_score"] = (
                "Ordering score from the provisional hybrid mix of normalized "
                "predicted compatibility and within-category rank percentile"
                + (
                    " plus original rule_compatibility_score "
                    "(weighted_compatibility from rating_parameters.json)"
                    if rules_available and rule_eval.category_verified
                    else ""
                )
                + f". Weights={hybrid_weights}. Not a learned research formula "
                "and not input-quality confidence."
            )
            if fallback_zero_coverage:
                score_sources["confidence_adjusted_rule_score"] = (
                    "null because A = sum(w_i * c_i) = 0 (all-zero confidence "
                    "fallback). Ranking used original rule_compatibility_score."
                )
                score_sources["recommendation_support_score"] = (
                    "0 under all-zero confidence fallback (no reliable rule support)."
                )

        notes: list[str] = [
            "Explanations describe the active pipeline and score sources only.",
            "No causal claim such as 'this style suits your jawline' is made "
            "without a documented rule contribution or model attribution.",
            "Terminology: compatibility_score=rescaled predicted rating; "
            "rule_compatibility_score=original weighted rule agreement; "
            "confidence_adjusted_rule_score=confidence-weighted rule agreement; "
            "recommendation_support_score=heuristic confidence-weighted support; "
            "input_quality_score=heuristic input reliability; "
            "hybrid_score=final ranking score; "
            "recommendation_confidence=unavailable until calibrated.",
        ]
        if rule_confidence_coverage is not None:
            notes.append(
                f"rule_confidence_coverage(A)={rule_confidence_coverage}; "
                f"recommendation_support_score(S_j)={recommendation_support_score}; "
                f"confidence_adjusted_rule_score={confidence_adjusted_rule_score}."
            )
        if fallback_zero_coverage:
            notes.append(
                "All-zero facial confidence triggered standard-policy fallback; "
                "divide-by-zero was avoided."
            )

        contributions: list[RuleContribution] = []
        if override_contributions is not None:
            contributions = override_contributions
        elif rule_eval.score is not None and rule_eval.contributions:
            contributions = rule_eval.contributions

        if rule_eval.score is not None and contributions:
            notes.append(rule_eval.detail)
            if not rule_eval.category_verified:
                notes.append(
                    "Rule score was computed but this category is not parity-verified; "
                    "hybrid ordering does not include the rule term."
                )
        else:
            notes.append(
                "Weighted compatibility rules unavailable; "
                "hybrid ordering uses model scores only."
            )

        stages = list(PIPELINE_STAGES)
        if not (rules_available and rule_eval.category_verified):
            stages = [
                s for s in stages if s != "weighted_facial_attribute_rules"
            ]

        if ranking_mode == "confidence_aware" and not fallback_zero_coverage:
            summary = (
                f"{style_name} was selected after eligibility filtering, scored with "
                f"the {category} CatBoost ranker and shared compatibility regressor, "
                "compared with weighted facial-attribute rules, then ordered by "
                "hybrid_confidence_adjusted_rules_v1 using a confidence-adjusted "
                "rule term. This adjusts only the rule component; models still use "
                "supplied profile values without uncertainty propagation."
            )
        else:
            summary = (
                f"{style_name} was selected after eligibility filtering, then scored with "
                f"the {category} CatBoost ranker and the shared compatibility regressor"
                + (
                    ", compared with weighted facial-attribute rules,"
                    if rules_available and rule_eval.category_verified
                    else ","
                )
                + " and ordered by the provisional hybrid ranking policy."
            )
            if ranking_mode == "standard":
                summary += (
                    " Heuristic input-quality flagging does not change this hybrid score."
                )
            if fallback_zero_coverage:
                summary += (
                    " confidence_aware mode fell back to standard ranking because "
                    "rule confidence coverage was zero."
                )

        if requires_facial_hair:
            notes.append("Catalogue marks this style as requiring facial hair.")

        return RecommendationExplanation(
            summary=summary,
            pipeline_stages=stages,
            applied_eligibility_rules=list(applied_rules),
            requires_facial_hair=requires_facial_hair,
            score_sources=score_sources,
            rule_contributions=contributions,
            notes=notes,
        )
