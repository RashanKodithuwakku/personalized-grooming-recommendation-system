"""Heuristic input-reliability policy for upstream attribute confidence.

This is confidence-aware flagging of Top-N results using an input-quality
heuristic. It is not calibrated recommendation confidence and does not
reorder hybrid ranking scores.
"""

from __future__ import annotations

from typing import Any, Literal

from app.services.compatibility_rules import EXPECTED_TERM_ORDER

# Nine facial attributes used by weighted compatibility rules.
# Gender is an eligibility/model input and is excluded from this aggregate.
FACIAL_CONFIDENCE_ATTRIBUTES: tuple[str, ...] = tuple(EXPECTED_TERM_ORDER)
EXPECTED_FACIAL_CONFIDENCE_COUNT = len(FACIAL_CONFIDENCE_ATTRIBUTES)
assert EXPECTED_FACIAL_CONFIDENCE_COUNT == 9

Assessment = Literal["unknown", "insufficient_coverage", "low", "adequate"]
ConfidenceStatus = Literal["not_provided", "partial", "complete"]
Disposition = Literal["standard", "review_required"]


def _round6(value: float) -> float:
    return round(float(value), 6)


class InputQualityService:
    """Compute global and category-level heuristic input-quality assessments."""

    def __init__(
        self,
        *,
        caution_threshold: float,
        low_confidence_attribute_threshold: float,
        min_coverage: float = 1.0,
        category_rule_weights: dict[str, list[float]] | None = None,
    ) -> None:
        if not (0.0 <= caution_threshold <= 1.0):
            raise ValueError("caution_threshold must be within [0, 1]")
        if not (0.0 <= low_confidence_attribute_threshold <= 1.0):
            raise ValueError(
                "low_confidence_attribute_threshold must be within [0, 1]"
            )
        if not (0.0 <= min_coverage <= 1.0):
            raise ValueError("min_coverage must be within [0, 1]")
        self.caution_threshold = float(caution_threshold)
        self.low_confidence_attribute_threshold = float(
            low_confidence_attribute_threshold
        )
        self.min_coverage = float(min_coverage)
        self.category_rule_weights = category_rule_weights or {}

    def evaluate(
        self,
        attribute_confidence: dict[str, float] | None,
        requested_categories: list[str],
    ) -> dict[str, Any]:
        facial_conf = self._facial_only(attribute_confidence)
        provided = sorted(facial_conf.keys())
        missing = sorted(set(FACIAL_CONFIDENCE_ATTRIBUTES) - set(provided))
        observed = len(provided)
        coverage = _round6(observed / EXPECTED_FACIAL_CONFIDENCE_COUNT)

        gender_confidence_supplied = bool(
            attribute_confidence and "gender" in attribute_confidence
        )

        if observed == 0:
            status: ConfidenceStatus = "not_provided"
            score = None
            # Equal-weight global weight coverage is zero when nothing supplied.
            weight_coverage = 0.0
        elif observed < EXPECTED_FACIAL_CONFIDENCE_COUNT:
            status = "partial"
            score = self._equal_weight_score(facial_conf)
            weight_coverage = _round6(observed / EXPECTED_FACIAL_CONFIDENCE_COUNT)
        else:
            status = "complete"
            score = self._equal_weight_score(facial_conf)
            weight_coverage = 1.0

        low_attrs = sorted(
            key
            for key, value in facial_conf.items()
            if value < self.low_confidence_attribute_threshold
        )
        assessment, assessment_reasons = self._assessment(
            status=status,
            coverage=coverage,
            score=score,
            low_attrs=low_attrs,
        )
        caution_flag = assessment != "adequate"
        caution_reasons = list(assessment_reasons)
        if status == "not_provided":
            caution_reasons = ["confidence_not_provided"]

        category_quality = {
            category: self._category_quality(category, facial_conf, status)
            for category in requested_categories
        }

        note = self._note(status, gender_confidence_supplied)
        # Deprecated aliases must exactly match canonical facial-confidence fields.
        return {
            "confidence_status": status,
            "assessment": assessment,
            "assessment_reasons": assessment_reasons,
            "input_quality_score": score,
            "confidence_attributes_provided": provided,
            "confidence_attributes_missing": missing,
            "confidence_coverage": coverage,
            "confidence_weight_coverage": weight_coverage,
            "observed_attribute_count": observed,
            "expected_attribute_count": EXPECTED_FACIAL_CONFIDENCE_COUNT,
            # Deprecated aliases (exact same values as canonical fields).
            "attributes_provided": provided,
            "attributes_missing": missing,
            "coverage": coverage,
            "low_confidence_attributes": low_attrs,
            "caution_flag": caution_flag,
            "caution_reasons": caution_reasons,
            "caution_threshold": self.caution_threshold,
            "low_confidence_attribute_threshold": (
                self.low_confidence_attribute_threshold
            ),
            "min_coverage": self.min_coverage,
            "gender_confidence_supplied": gender_confidence_supplied,
            "gender_excluded_from_facial_aggregate": True,
            "category_input_quality": category_quality,
            "field_deprecations": {
                "attributes_provided": (
                    "Deprecated alias of confidence_attributes_provided. "
                    "Lists attributes with supplied confidence values, not "
                    "missing facial measurements."
                ),
                "attributes_missing": (
                    "Deprecated alias of confidence_attributes_missing. "
                    "Lists facial attributes without upstream confidence, "
                    "not missing required profile values."
                ),
                "coverage": (
                    "Deprecated alias of confidence_coverage "
                    "(observed facial confidence count / 9)."
                ),
            },
            "note": note,
            "policy_name": "confidence_aware_topn_flagging_v1",
            "policy_description": (
                "Confidence-aware flagging of Top-N results using an "
                "input-quality heuristic. Hybrid ranking scores are unchanged; "
                "results are labeled standard or review_required."
            ),
        }

    def disposition_for_category(
        self, category_quality: dict[str, Any]
    ) -> dict[str, Any]:
        assessment = category_quality["assessment"]
        if assessment == "adequate":
            return {
                "recommendation_disposition": "standard",
                "disposition_reasons": [],
                "disposition_explanation": (
                    "All nine facial confidence values were supplied and the "
                    "category heuristic input-quality score meets the configured "
                    "threshold. Ranking scores are unchanged."
                ),
            }
        reasons = list(category_quality.get("assessment_reasons") or [])
        explanation = {
            "unknown": (
                "No upstream facial attribute confidence was supplied. "
                "Recommendations are still returned for manual-input demos, "
                "but review is required because input reliability is unknown."
            ),
            "insufficient_coverage": (
                "Facial attribute confidence coverage is incomplete. "
                "Missing confidence values are not filled with zeros or ones. "
                "Top-N results are flagged review_required."
            ),
            "low": (
                "Facial confidence coverage is complete, but the category "
                "heuristic input-quality score is below the configured threshold "
                "or one or more attributes are below the low-confidence threshold. "
                "Top-N results are flagged review_required."
            ),
        }.get(
            assessment,
            "Top-N results are flagged review_required by the input-quality heuristic.",
        )
        return {
            "recommendation_disposition": "review_required",
            "disposition_reasons": reasons,
            "disposition_explanation": explanation,
        }

    @staticmethod
    def _facial_only(
        attribute_confidence: dict[str, float] | None,
    ) -> dict[str, float]:
        if not attribute_confidence:
            return {}
        return {
            key: float(value)
            for key, value in attribute_confidence.items()
            if key in FACIAL_CONFIDENCE_ATTRIBUTES
        }

    @staticmethod
    def _equal_weight_score(facial_conf: dict[str, float]) -> float:
        # Equal weights over supplied facial attributes only.
        return _round6(sum(facial_conf.values()) / len(facial_conf))

    def _assessment(
        self,
        *,
        status: ConfidenceStatus,
        coverage: float,
        score: float | None,
        low_attrs: list[str],
    ) -> tuple[Assessment, list[str]]:
        # Precedence: unknown > insufficient_coverage > low > adequate
        if status == "not_provided":
            return "unknown", ["confidence_not_provided"]
        if status == "partial" or coverage < self.min_coverage:
            reasons = ["insufficient_confidence_coverage"]
            if low_attrs:
                reasons.append("low_confidence_attributes")
            return "insufficient_coverage", reasons
        reasons: list[str] = []
        if score is not None and score < self.caution_threshold:
            reasons.append("input_quality_below_threshold")
        if low_attrs:
            reasons.append("low_confidence_attributes")
        if reasons:
            return "low", reasons
        return "adequate", []

    def _category_quality(
        self,
        category: str,
        facial_conf: dict[str, float],
        global_status: ConfidenceStatus,
    ) -> dict[str, Any]:
        weights = self.category_rule_weights.get(category)
        if weights is None or len(weights) != EXPECTED_FACIAL_CONFIDENCE_COUNT:
            # Fallback equal weights if rules unavailable for the category.
            weights = [1.0 / EXPECTED_FACIAL_CONFIDENCE_COUNT] * (
                EXPECTED_FACIAL_CONFIDENCE_COUNT
            )

        provided = sorted(facial_conf.keys())
        missing = sorted(set(FACIAL_CONFIDENCE_ATTRIBUTES) - set(provided))
        observed = len(provided)
        coverage = _round6(observed / EXPECTED_FACIAL_CONFIDENCE_COUNT)

        supplied_weight = 0.0
        weighted_conf = 0.0
        for idx, attr in enumerate(FACIAL_CONFIDENCE_ATTRIBUTES):
            if attr in facial_conf:
                w = float(weights[idx])
                supplied_weight += w
                weighted_conf += w * float(facial_conf[attr])

        if observed == 0:
            status: ConfidenceStatus = "not_provided"
            score = None
            weight_coverage = 0.0
        else:
            status = (
                "complete"
                if observed == EXPECTED_FACIAL_CONFIDENCE_COUNT
                else "partial"
            )
            score = _round6(weighted_conf / supplied_weight) if supplied_weight > 0 else None
            weight_coverage = _round6(supplied_weight)

        # Keep category status consistent with global when nothing was supplied.
        if global_status == "not_provided":
            status = "not_provided"

        low_attrs = sorted(
            key
            for key, value in facial_conf.items()
            if value < self.low_confidence_attribute_threshold
        )
        assessment, reasons = self._assessment(
            status=status,
            coverage=coverage,
            score=score,
            low_attrs=low_attrs,
        )
        return {
            "category": category,
            "confidence_status": status,
            "assessment": assessment,
            "assessment_reasons": reasons,
            "input_quality_score": score,
            "observed_attribute_count": observed,
            "expected_attribute_count": EXPECTED_FACIAL_CONFIDENCE_COUNT,
            "confidence_coverage": coverage,
            "confidence_weight_coverage": weight_coverage,
            "confidence_attributes_provided": provided,
            "confidence_attributes_missing": missing,
            "low_confidence_attributes": low_attrs,
            "rule_weights_used": {
                FACIAL_CONFIDENCE_ATTRIBUTES[i]: float(weights[i])
                for i in range(EXPECTED_FACIAL_CONFIDENCE_COUNT)
            },
            "note": (
                "Category input_quality_score = "
                "sum(weight_i * confidence_i) / sum(weight_i) over supplied "
                "facial confidence attributes using that category's rule weights. "
                "Gender confidence is excluded. Not calibrated suitability confidence."
            ),
        }

    @staticmethod
    def _note(status: ConfidenceStatus, gender_supplied: bool) -> str:
        base = (
            "input_quality_score is a heuristic input-reliability summary over the "
            "nine facial attributes used by weighted compatibility rules. "
            "It is not calibrated recommendation confidence and not a probability "
            "of style suitability. Missing confidence is not the same as missing "
            "required facial profile values. Confidence values are never manufactured "
            "from facial ratios, symmetry, gender, or model scores."
        )
        if status == "not_provided":
            base = (
                "Upstream facial attribute confidence was not provided. "
                "input_quality_score is null; confidence_coverage is 0. "
                "No confidence values were manufactured. "
            ) + base
        if gender_supplied:
            base += (
                " Gender confidence was accepted for API compatibility but is "
                "excluded from the nine-attribute facial aggregate."
            )
        base += (
            " Deprecated fields attributes_provided/attributes_missing/coverage "
            "are aliases of the confidence_* fields and refer to confidence "
            "coverage, not missing measurements."
        )
        return base

    def policy_capabilities(self) -> dict[str, Any]:
        return {
            "policy_name": "confidence_aware_topn_flagging_v1",
            "description": (
                "Confidence-aware flagging of Top-N results using an input-quality "
                "heuristic. Does not reorder candidates or calibrate recommendation "
                "confidence."
            ),
            "facial_attributes": list(FACIAL_CONFIDENCE_ATTRIBUTES),
            "expected_attribute_count": EXPECTED_FACIAL_CONFIDENCE_COUNT,
            "gender_excluded_from_facial_aggregate": True,
            "caution_threshold": self.caution_threshold,
            "low_confidence_attribute_threshold": (
                self.low_confidence_attribute_threshold
            ),
            "min_coverage": self.min_coverage,
            "assessment_precedence": [
                "unknown (no facial confidence)",
                "insufficient_coverage (partial / below min_coverage)",
                "low (complete but below threshold or low attributes)",
                "adequate (complete and meets thresholds)",
            ],
            "disposition_values": ["standard", "review_required"],
            "recommendation_confidence_status": "not_calibrated",
            "limitations": [
                "Not calibrated recommendation confidence.",
                "Does not multiply hybrid scores by profile quality.",
                "Does not invent confidence from profile measurements.",
                "Human suitability validation remains unfinished research work.",
            ],
        }
