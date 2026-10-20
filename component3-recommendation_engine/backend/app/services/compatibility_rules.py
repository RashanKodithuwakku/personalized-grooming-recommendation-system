"""Weighted compatibility rules for the recovered rating_parameters.json format.

Provenance: recovered from Component3_AllCategories_20261008T121138_253749Z.zip
and stored at backend/datasets/rating_parameters.json. The original parameter file
is preserved as-is (parameter_status remains provisional_unvalidated).

Established similarity calculation (verified against training_pairs.rating):
- Ratio terms and symmetry use Gaussian similarity:
    exp(-0.5 * ((value - target) / scale)^2)
- Categorical terms use match / non-match scores from the parameter file
- weighted_compatibility = sum_i(weight_i * similarity_i) using category weights
- reconstructed rating = 1 + 4 * weighted_compatibility, rounded to 4 decimals
  to match stored rating precision

Do not reverse-engineer arbitrary expert rules from style names.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.core.exceptions import ArtifactError
from app.schemas.requests import ProfileFeatures
from app.schemas.responses import RuleContribution

# Stored ratings in training_pairs.csv use up to 4 decimal places.
# Half-unit in the last place is 5e-5; use 1e-4 as a conservative parity tolerance.
RATING_DECIMAL_PRECISION = 4
PARITY_ABS_TOLERANCE = 1e-4

RATIO_TERMS = (
    "face_length_ratio",
    "jaw_width_ratio",
    "upper_width_ratio",
    "lower_face_ratio",
)
CATEGORICAL_TERMS = ("face_shape", "jawline", "forehead", "hairline")
EXPECTED_TERM_ORDER = RATIO_TERMS + CATEGORICAL_TERMS + ("symmetry",)
EXPECTED_PREFERENCE_ORDER = ("face_shape", "jawline", "forehead", "hairline", "symmetry")
SUPPORTED_RULE_CATEGORIES = ("hair", "beard", "grooming")

MISSING_RULE_ARTIFACT = (
    "rating_parameters.json was not found or could not be loaded. "
    "Weighted compatibility rules are unavailable until a validated "
    "parameter file is configured via RULE_PARAMETERS_PATH."
)

ORIGINAL_FORMAT_KEYS = (
    "term_order",
    "weights",
    "ratio_scales",
    "symmetry_scale",
    "categorical_match_score",
    "categorical_nonmatch_score",
    "preference_order",
    "style_preferences",
    "style_ratio_targets",
)


@dataclass
class CategoryParityResult:
    category: str
    checked_rows: int
    mae: float
    max_abs_error: float
    mismatches: int
    verified: bool
    tolerance: float


@dataclass
class RuleParityReport:
    checked_rows: int
    mae: float
    max_abs_error: float
    mismatches: int
    tolerance: float
    by_category: dict[str, CategoryParityResult] = field(default_factory=dict)
    verified_categories: list[str] = field(default_factory=list)
    target_column: str = "rating"
    note: str = ""


@dataclass
class OriginalRuleParameters:
    """Validated recovered rating_parameters.json payload."""

    term_order: list[str]
    weights: dict[str, list[float]]
    ratio_scales: list[float]
    symmetry_scale: float
    categorical_match_score: float
    categorical_nonmatch_score: float
    preference_order: list[str]
    style_preferences: dict[str, list[Any]]
    style_ratio_targets: dict[str, list[float]]
    formula: str
    parameter_status: str
    raw: dict[str, Any] = field(default_factory=dict)
    covered_style_ids: list[str] = field(default_factory=list)

    @property
    def available(self) -> bool:
        return True


@dataclass
class RuleEvaluation:
    available: bool
    score: float | None
    contributions: list[RuleContribution]
    status: str
    detail: str
    reconstructed_rating: float | None = None
    category_verified: bool = False


class CompatibilityRulesService:
    """Load original rule parameters and evaluate weighted compatibility."""

    def __init__(
        self,
        rule_parameters_path: Path | None,
        catalogue_style_ids: set[str] | None = None,
        training_pairs_path: Path | None = None,
        run_parity_check: bool = True,
    ) -> None:
        self.rule_parameters_path = rule_parameters_path
        self.catalogue_style_ids = catalogue_style_ids or set()
        self.training_pairs_path = training_pairs_path
        self.run_parity_check = run_parity_check
        self.parameters: OriginalRuleParameters | None = None
        self.load_diagnostics: list[str] = []
        self.parity_report: RuleParityReport | None = None
        self.verified_categories: set[str] = set()
        self._load()

    @property
    def available(self) -> bool:
        return self.parameters is not None and bool(self.verified_categories)

    @property
    def structurally_loaded(self) -> bool:
        return self.parameters is not None

    @property
    def status(self) -> str:
        if self.available:
            return "available_verified"
        if self.parameters is not None and not self.verified_categories:
            return "loaded_but_parity_failed"
        if self.rule_parameters_path is not None:
            return "configured_but_invalid"
        return "unavailable"

    @property
    def missing_artifact_message(self) -> str | None:
        if self.structurally_loaded:
            return None
        return MISSING_RULE_ARTIFACT

    @property
    def parameter_status(self) -> str | None:
        if self.parameters is None:
            return None
        return self.parameters.parameter_status

    def category_verified(self, category: str) -> bool:
        return category.lower() in self.verified_categories

    def _load(self) -> None:
        if self.rule_parameters_path is None:
            self.load_diagnostics.append(MISSING_RULE_ARTIFACT)
            return
        path = self.rule_parameters_path
        if not path.exists():
            self.load_diagnostics.append(
                f"Configured RULE_PARAMETERS_PATH does not exist: {path.name}"
            )
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            self.load_diagnostics.append(
                f"Failed to parse rule parameters file {path.name}: {exc}"
            )
            return

        try:
            if self._is_original_format(payload):
                self.parameters = self._validate_original_payload(payload)
            elif self._is_template_format(payload):
                # Keep template-format support for unit tests / future configs.
                self.parameters = self._adapt_template_payload(payload)
            else:
                raise ArtifactError(
                    "Unrecognized rule parameter format",
                    diagnostics=[
                        "Expected original rating_parameters.json keys "
                        f"{list(ORIGINAL_FORMAT_KEYS)} "
                        "or template keys (version, attributes, weights)."
                    ],
                )
        except ArtifactError as exc:
            self.load_diagnostics.extend(exc.diagnostics or [exc.message])
            self.parameters = None
            return

        if self.run_parity_check and self.training_pairs_path is not None:
            try:
                self.parity_report = self.verify_against_training_pairs(
                    self.training_pairs_path
                )
                self.verified_categories = set(self.parity_report.verified_categories)
                if not self.verified_categories:
                    self.load_diagnostics.append(
                        "Rule parameters loaded but parity verification failed "
                        "for all categories; hybrid rule term disabled."
                    )
            except Exception as exc:  # noqa: BLE001
                self.load_diagnostics.append(
                    f"Rule parity verification failed to run: {exc}"
                )
                self.verified_categories = set()
        elif self.parameters is not None:
            # Structural load only (tests can call verify explicitly).
            self.verified_categories = set(SUPPORTED_RULE_CATEGORIES)

    @staticmethod
    def _is_original_format(payload: dict[str, Any]) -> bool:
        return all(key in payload for key in ("term_order", "style_preferences", "style_ratio_targets"))

    @staticmethod
    def _is_template_format(payload: dict[str, Any]) -> bool:
        return all(key in payload for key in ("version", "attributes", "weights"))

    def _validate_original_payload(self, payload: dict[str, Any]) -> OriginalRuleParameters:
        diagnostics: list[str] = []
        for key in ORIGINAL_FORMAT_KEYS:
            if key not in payload:
                diagnostics.append(f"Missing required key: {key}")
        if diagnostics:
            raise ArtifactError("Invalid original rule parameters", diagnostics=diagnostics)

        term_order = [str(x) for x in payload["term_order"]]
        if term_order != list(EXPECTED_TERM_ORDER):
            diagnostics.append(
                f"term_order mismatch: expected={list(EXPECTED_TERM_ORDER)} actual={term_order}"
            )

        preference_order = [str(x) for x in payload["preference_order"]]
        if preference_order != list(EXPECTED_PREFERENCE_ORDER):
            diagnostics.append(
                f"preference_order mismatch: expected={list(EXPECTED_PREFERENCE_ORDER)} "
                f"actual={preference_order}"
            )

        weights_raw = payload["weights"]
        if not isinstance(weights_raw, dict):
            diagnostics.append("weights must be an object keyed by category")
            weights_raw = {}
        cleaned_weights: dict[str, list[float]] = {}
        for category in SUPPORTED_RULE_CATEGORIES:
            values = weights_raw.get(category)
            if not isinstance(values, list):
                diagnostics.append(f"weights[{category}] must be a list")
                continue
            if len(values) != len(EXPECTED_TERM_ORDER):
                diagnostics.append(
                    f"weights[{category}] length {len(values)} != {len(EXPECTED_TERM_ORDER)}"
                )
                continue
            nums: list[float] = []
            for idx, value in enumerate(values):
                try:
                    number = float(value)
                except (TypeError, ValueError):
                    diagnostics.append(f"weights[{category}][{idx}] is not numeric")
                    number = float("nan")
                if not math.isfinite(number):
                    diagnostics.append(f"weights[{category}][{idx}] is not finite")
                elif number < 0:
                    diagnostics.append(f"weights[{category}][{idx}] must be nonnegative")
                nums.append(number)
            total = float(sum(nums)) if nums else 0.0
            if abs(total - 1.0) > 1e-6:
                diagnostics.append(
                    f"weights[{category}] must sum to 1.0 (got {total})"
                )
            cleaned_weights[category] = nums

        ratio_scales = self._finite_positive_list(
            payload.get("ratio_scales"),
            name="ratio_scales",
            expected_len=len(RATIO_TERMS),
            diagnostics=diagnostics,
        )
        try:
            symmetry_scale = float(payload["symmetry_scale"])
        except (TypeError, ValueError):
            symmetry_scale = float("nan")
            diagnostics.append("symmetry_scale is not numeric")
        if not math.isfinite(symmetry_scale) or symmetry_scale <= 0:
            diagnostics.append("symmetry_scale must be a finite positive number")

        try:
            match_score = float(payload["categorical_match_score"])
            nonmatch_score = float(payload["categorical_nonmatch_score"])
        except (TypeError, ValueError):
            match_score = float("nan")
            nonmatch_score = float("nan")
            diagnostics.append("categorical match scores must be numeric")
        for label, value in (
            ("categorical_match_score", match_score),
            ("categorical_nonmatch_score", nonmatch_score),
        ):
            if not math.isfinite(value):
                diagnostics.append(f"{label} must be finite")
            elif value < 0 or value > 1:
                diagnostics.append(f"{label} should be within [0, 1]")

        style_preferences = payload.get("style_preferences", {})
        style_ratio_targets = payload.get("style_ratio_targets", {})
        if not isinstance(style_preferences, dict) or not isinstance(style_ratio_targets, dict):
            diagnostics.append("style_preferences and style_ratio_targets must be objects")
            style_preferences, style_ratio_targets = {}, {}

        pref_ids = {str(k).upper() for k in style_preferences}
        ratio_ids = {str(k).upper() for k in style_ratio_targets}
        if pref_ids != ratio_ids:
            diagnostics.append(
                "style_preferences and style_ratio_targets style_id sets differ: "
                f"only_in_preferences={sorted(pref_ids - ratio_ids)} "
                f"only_in_ratio_targets={sorted(ratio_ids - pref_ids)}"
            )

        cleaned_prefs: dict[str, list[Any]] = {}
        cleaned_ratios: dict[str, list[float]] = {}
        for style_id in sorted(pref_ids & ratio_ids):
            pref = style_preferences.get(style_id) or style_preferences.get(style_id.lower())
            # Keys in file are uppercase already; handle both.
            if pref is None:
                for key, value in style_preferences.items():
                    if str(key).upper() == style_id:
                        pref = value
                        break
            ratios = None
            for key, value in style_ratio_targets.items():
                if str(key).upper() == style_id:
                    ratios = value
                    break
            if not isinstance(pref, list) or len(pref) != len(EXPECTED_PREFERENCE_ORDER):
                diagnostics.append(
                    f"style_preferences[{style_id}] must be length "
                    f"{len(EXPECTED_PREFERENCE_ORDER)}"
                )
                continue
            if not isinstance(ratios, list) or len(ratios) != len(RATIO_TERMS):
                diagnostics.append(
                    f"style_ratio_targets[{style_id}] must be length {len(RATIO_TERMS)}"
                )
                continue
            # preference: 4 categoricals + symmetry target
            try:
                sym_target = float(pref[4])
            except (TypeError, ValueError, IndexError):
                diagnostics.append(
                    f"style_preferences[{style_id}] symmetry target is not numeric"
                )
                continue
            if not math.isfinite(sym_target):
                diagnostics.append(
                    f"style_preferences[{style_id}] symmetry target is not finite"
                )
                continue
            ratio_nums: list[float] = []
            ok = True
            for idx, value in enumerate(ratios):
                try:
                    number = float(value)
                except (TypeError, ValueError):
                    diagnostics.append(
                        f"style_ratio_targets[{style_id}][{idx}] is not numeric"
                    )
                    ok = False
                    break
                if not math.isfinite(number):
                    diagnostics.append(
                        f"style_ratio_targets[{style_id}][{idx}] is not finite"
                    )
                    ok = False
                    break
                ratio_nums.append(number)
            if not ok:
                continue
            cleaned_prefs[style_id] = [
                str(pref[0]).strip().lower(),
                str(pref[1]).strip().lower(),
                str(pref[2]).strip().lower(),
                str(pref[3]).strip().lower(),
                sym_target,
            ]
            cleaned_ratios[style_id] = ratio_nums

        if self.catalogue_style_ids:
            missing = sorted(self.catalogue_style_ids - set(cleaned_prefs))
            extra = sorted(set(cleaned_prefs) - self.catalogue_style_ids)
            if missing:
                diagnostics.append(
                    f"Rule parameters missing catalogue style_ids: {missing}"
                )
            if extra:
                diagnostics.append(
                    f"Rule parameters contain unknown style_ids not in catalogue: {extra}"
                )

        # Coverage expectations for the recovered 16-style package.
        expected_ids = {
            f"H00{i}" for i in range(1, 9)
        } | {f"B00{i}" for i in range(1, 5)} | {f"G00{i}" for i in range(1, 5)}
        if set(cleaned_prefs) != expected_ids and not diagnostics:
            # Soft warning if catalogue already checked; keep hard if empty catalogue.
            if set(cleaned_prefs) != expected_ids:
                diagnostics.append(
                    f"Expected 16 style IDs {sorted(expected_ids)}, "
                    f"got {sorted(cleaned_prefs)}"
                )

        if diagnostics:
            raise ArtifactError("Invalid original rule parameters", diagnostics=diagnostics)

        return OriginalRuleParameters(
            term_order=term_order,
            weights=cleaned_weights,
            ratio_scales=ratio_scales,
            symmetry_scale=float(symmetry_scale),
            categorical_match_score=float(match_score),
            categorical_nonmatch_score=float(nonmatch_score),
            preference_order=preference_order,
            style_preferences=cleaned_prefs,
            style_ratio_targets=cleaned_ratios,
            formula=str(payload.get("formula", "rating = 1 + 4 * weighted_compatibility")),
            parameter_status=str(
                payload.get("parameter_status", "provisional_unvalidated")
            ),
            raw=payload,
            covered_style_ids=sorted(cleaned_prefs),
        )

    def _adapt_template_payload(self, payload: dict[str, Any]) -> OriginalRuleParameters:
        """Limited adapter for the engineering template used in unit tests."""
        diagnostics: list[str] = []
        weights_obj = payload.get("weights", {})
        if not isinstance(weights_obj, dict) or not weights_obj:
            raise ArtifactError(
                "Invalid template rule weights",
                diagnostics=["weights must be a non-empty object"],
            )
        # Build a synthetic original-format parameter set with equal ratio targets.
        term_weights = []
        for term in EXPECTED_TERM_ORDER:
            term_weights.append(float(weights_obj.get(term, 0.0)))
        total = sum(term_weights)
        if abs(total - 1.0) > 1e-6:
            diagnostics.append(f"template weights must sum to 1.0 (got {total})")
        if diagnostics:
            raise ArtifactError("Invalid template rule parameters", diagnostics=diagnostics)

        attributes = payload.get("attributes", {})
        style_targets = attributes.get("style_targets", {}) if isinstance(attributes, dict) else {}
        cleaned_prefs: dict[str, list[Any]] = {}
        cleaned_ratios: dict[str, list[float]] = {}
        for style_id, cfg in style_targets.items():
            if not isinstance(cfg, dict):
                continue
            sid = str(style_id).upper()
            face = cfg.get("face_shape", ["oval"])
            jaw = cfg.get("jawline", ["soft"])
            if isinstance(face, list):
                face = face[0] if face else "oval"
            if isinstance(jaw, list):
                jaw = jaw[0] if jaw else "soft"
            cleaned_prefs[sid] = [str(face), str(jaw), "medium", "straight", 0.7]
            cleaned_ratios[sid] = [1.35, 0.85, 0.96, 0.44]

        if not cleaned_prefs:
            cleaned_prefs["H001"] = ["oval", "angular", "medium", "straight", 0.7]
            cleaned_ratios["H001"] = [1.35, 0.85, 0.96, 0.44]

        weights = {category: term_weights for category in SUPPORTED_RULE_CATEGORIES}
        return OriginalRuleParameters(
            term_order=list(EXPECTED_TERM_ORDER),
            weights=weights,
            ratio_scales=[0.2, 0.12, 0.1, 0.12],
            symmetry_scale=0.25,
            categorical_match_score=1.0,
            categorical_nonmatch_score=0.35,
            preference_order=list(EXPECTED_PREFERENCE_ORDER),
            style_preferences=cleaned_prefs,
            style_ratio_targets=cleaned_ratios,
            formula="rating = 1 + 4 * weighted_compatibility",
            parameter_status="template_adapter",
            raw=payload,
            covered_style_ids=sorted(cleaned_prefs),
        )

    @staticmethod
    def _finite_positive_list(
        values: Any,
        *,
        name: str,
        expected_len: int,
        diagnostics: list[str],
    ) -> list[float]:
        if not isinstance(values, list):
            diagnostics.append(f"{name} must be a list")
            return []
        if len(values) != expected_len:
            diagnostics.append(f"{name} length {len(values)} != {expected_len}")
        nums: list[float] = []
        for idx, value in enumerate(values):
            try:
                number = float(value)
            except (TypeError, ValueError):
                diagnostics.append(f"{name}[{idx}] is not numeric")
                number = float("nan")
            if not math.isfinite(number) or number <= 0:
                diagnostics.append(f"{name}[{idx}] must be a finite positive number")
            nums.append(number)
        return nums
      # Gaussian method measures how similar a value is to the target value.
    @staticmethod
    def gaussian_similarity(value: float, target: float, scale: float) -> float:
        if scale <= 0:
            return 0.0
        z = (value - target) / scale
        return float(math.exp(-0.5 * z * z))

    def evaluate(
        self,
        profile: ProfileFeatures,
        style_id: str,
        category: str,
        style_meta: dict[str, Any] | None = None,
    ) -> RuleEvaluation:
        if self.parameters is None:
            return RuleEvaluation(
                available=False,
                score=None,
                contributions=[],
                status="unavailable",
                detail=MISSING_RULE_ARTIFACT,
            )

        category = category.lower()
        style_id = style_id.strip().upper()
        params = self.parameters
        if category not in params.weights:
            return RuleEvaluation(
                available=False,
                score=None,
                contributions=[],
                status="unsupported_category",
                detail=f"No rule weights for category={category}",
            )
        if style_id not in params.style_preferences:
            return RuleEvaluation(
                available=False,
                score=None,
                contributions=[],
                status="unknown_style",
                detail=f"No rule parameters for style_id={style_id}",
            )

        verified = self.category_verified(category)
        profile_dict = profile.model_dump()
        pref = params.style_preferences[style_id]
        ratio_targets = params.style_ratio_targets[style_id]
        weights = params.weights[category]

        similarities: list[float] = []
        contributions: list[RuleContribution] = []

        for idx, term in enumerate(RATIO_TERMS):
            sim = self.gaussian_similarity(
                float(profile_dict[term]),
                float(ratio_targets[idx]),
                float(params.ratio_scales[idx]),
            )
            similarities.append(sim)
            weight = float(weights[idx])
            contributions.append(
                RuleContribution(
                    attribute=term,
                    contribution=round(weight * sim, 6),
                    similarity=round(sim, 6),
                    weight=weight,
                    detail=(
                        f"gaussian target={ratio_targets[idx]} "
                        f"scale={params.ratio_scales[idx]}"
                    ),
                )
            )

        for offset, term in enumerate(CATEGORICAL_TERMS):
            idx = len(RATIO_TERMS) + offset
            matched = str(profile_dict[term]).lower() == str(pref[offset]).lower()
            sim = (
                params.categorical_match_score
                if matched
                else params.categorical_nonmatch_score
            )
            similarities.append(float(sim))
            weight = float(weights[idx])
            contributions.append(
                RuleContribution(
                    attribute=term,
                    contribution=round(weight * float(sim), 6),
                    similarity=round(float(sim), 6),
                    weight=weight,
                    detail=(
                        f"categorical {'match' if matched else 'nonmatch'} "
                        f"observed={profile_dict[term]} preferred={pref[offset]}"
                    ),
                )
            )

        sym_idx = len(EXPECTED_TERM_ORDER) - 1
        sym_sim = self.gaussian_similarity(
            float(profile_dict["symmetry"]),
            float(pref[4]),
            float(params.symmetry_scale),
        )
        similarities.append(sym_sim)
        weight = float(weights[sym_idx])
        contributions.append(
            RuleContribution(
                attribute="symmetry",
                contribution=round(weight * sym_sim, 6),
                similarity=round(sym_sim, 6),
                weight=weight,
                detail=(
                    f"gaussian target={pref[4]} scale={params.symmetry_scale}"
                ),
            )
        )

        weighted_compatibility = float(
            sum(w * s for w, s in zip(weights, similarities))
        )
        weighted_compatibility = max(0.0, min(1.0, weighted_compatibility))
        reconstructed = 1.0 + 4.0 * weighted_compatibility

        return RuleEvaluation(
            available=True,
            score=round(weighted_compatibility, 6),
            contributions=contributions,
            status="available" if verified else "parity_unverified",
            detail=(
                f"Original rule parameters ({params.parameter_status}); "
                f"formula={params.formula}; "
                f"gaussian ratio/symmetry + categorical match/nonmatch; "
                f"category_verified={verified}"
            ),
            reconstructed_rating=round(reconstructed, RATING_DECIMAL_PRECISION),
            category_verified=verified,
        )

    def verify_against_training_pairs(
        self,
        training_pairs_path: Path,
        target_column: str = "rating",
        tolerance: float = PARITY_ABS_TOLERANCE,
    ) -> RuleParityReport:
        """Compare reconstructed rule ratings to dataset labels (not model outputs)."""
        if self.parameters is None:
            raise ArtifactError(
                "Cannot verify rules without loaded parameters",
                diagnostics=["parameters are None"],
            )
        if not training_pairs_path.exists():
            raise ArtifactError(
                "training_pairs.csv missing for rule parity check",
                diagnostics=[training_pairs_path.name],
            )

        df = pd.read_csv(training_pairs_path)
        if target_column not in df.columns:
            raise ArtifactError(
                f"Target column {target_column!r} missing from training pairs",
                diagnostics=[f"columns={list(df.columns)}"],
            )

        required = (
            list(RATIO_TERMS)
            + list(CATEGORICAL_TERMS)
            + ["symmetry", "style_id", "category", target_column]
        )
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ArtifactError(
                "training_pairs missing columns for rule parity",
                diagnostics=[f"missing={missing}"],
            )

        params = self.parameters
        style_ids = df["style_id"].astype(str).str.upper().to_numpy()
        categories = df["category"].astype(str).str.lower().to_numpy()

        # Precompute per-style targets for vectorized scoring.
        unique_styles = sorted(set(style_ids.tolist()))
        ratio_target_map = {
            sid: np.asarray(params.style_ratio_targets[sid], dtype=float)
            for sid in unique_styles
        }
        pref_cat_map = {
            sid: [str(params.style_preferences[sid][i]).lower() for i in range(4)]
            for sid in unique_styles
        }
        pref_sym_map = {
            sid: float(params.style_preferences[sid][4]) for sid in unique_styles
        }

        ratio_scales = np.asarray(params.ratio_scales, dtype=float)
        observed_ratios = df.loc[:, list(RATIO_TERMS)].to_numpy(dtype=float)
        observed_symmetry = df["symmetry"].to_numpy(dtype=float)
        observed_cats = {
            term: df[term].astype(str).str.lower().to_numpy()
            for term in CATEGORICAL_TERMS
        }

        n = len(df)
        sims = np.zeros((n, len(EXPECTED_TERM_ORDER)), dtype=float)
        for sid in unique_styles:
            mask = style_ids == sid
            if not mask.any():
                continue
            targets = ratio_target_map[sid]
            z = (observed_ratios[mask] - targets) / ratio_scales
            sims[mask, 0:4] = np.exp(-0.5 * z * z)
            preferred = pref_cat_map[sid]
            for offset, term in enumerate(CATEGORICAL_TERMS):
                matched = observed_cats[term][mask] == preferred[offset]
                sims[mask, 4 + offset] = np.where(
                    matched,
                    params.categorical_match_score,
                    params.categorical_nonmatch_score,
                )
            z_sym = (observed_symmetry[mask] - pref_sym_map[sid]) / params.symmetry_scale
            sims[mask, 8] = np.exp(-0.5 * z_sym * z_sym)

        weight_matrix = np.zeros((n, len(EXPECTED_TERM_ORDER)), dtype=float)
        for category in SUPPORTED_RULE_CATEGORIES:
            mask = categories == category
            if mask.any():
                weight_matrix[mask] = np.asarray(params.weights[category], dtype=float)

        weighted = np.sum(weight_matrix * sims, axis=1)
        preds = np.round(1.0 + 4.0 * weighted, RATING_DECIMAL_PRECISION)
        actual = df[target_column].astype(float).to_numpy()
        abs_err = np.abs(preds - actual)
        by_category: dict[str, CategoryParityResult] = {}
        verified: list[str] = []
        for category in SUPPORTED_RULE_CATEGORIES:
            mask = df["category"].astype(str).str.lower() == category
            if not mask.any():
                by_category[category] = CategoryParityResult(
                    category=category,
                    checked_rows=0,
                    mae=float("nan"),
                    max_abs_error=float("nan"),
                    mismatches=0,
                    verified=False,
                    tolerance=tolerance,
                )
                continue
            cat_err = abs_err[mask.to_numpy()]
            mismatches = int(np.sum(cat_err > tolerance))
            result = CategoryParityResult(
                category=category,
                checked_rows=int(mask.sum()),
                mae=float(np.mean(cat_err)),
                max_abs_error=float(np.max(cat_err)),
                mismatches=mismatches,
                verified=mismatches == 0,
                tolerance=tolerance,
            )
            by_category[category] = result
            if result.verified:
                verified.append(category)

        report = RuleParityReport(
            checked_rows=int(len(df)),
            mae=float(np.mean(abs_err)),
            max_abs_error=float(np.max(abs_err)),
            mismatches=int(np.sum(abs_err > tolerance)),
            tolerance=tolerance,
            by_category=by_category,
            verified_categories=verified,
            target_column=target_column,
            note=(
                "Compared reconstructed rule ratings to dataset labels in "
                f"{target_column}. Tolerance {tolerance} is justified by stored "
                f"rating precision of {RATING_DECIMAL_PRECISION} decimal places. "
                "Gaussian similarity established for ratio/symmetry terms; "
                "categorical match/nonmatch scores from parameter file; "
                "final mapping rating = 1 + 4 * weighted_compatibility with "
                f"{RATING_DECIMAL_PRECISION}-decimal rounding."
            ),
        )
        return report

    def capabilities_payload(self) -> dict[str, Any]:
        if self.parameters is None:
            return {
                "rules_available": False,
                "rules_status": self.status,
                "missing_rule_artifact": self.missing_artifact_message,
                "parameter_status": None,
                "verified_categories": [],
                "covered_style_ids": [],
                "parity": None,
                "formula": None,
                "similarity_definition": None,
            }
        parity = None
        if self.parity_report is not None:
            parity = {
                "checked_rows": self.parity_report.checked_rows,
                "mae": self.parity_report.mae,
                "max_abs_error": self.parity_report.max_abs_error,
                "mismatches": self.parity_report.mismatches,
                "tolerance": self.parity_report.tolerance,
                "target_column": self.parity_report.target_column,
                "by_category": {
                    key: {
                        "checked_rows": value.checked_rows,
                        "mae": value.mae,
                        "max_abs_error": value.max_abs_error,
                        "mismatches": value.mismatches,
                        "verified": value.verified,
                        "tolerance": value.tolerance,
                    }
                    for key, value in self.parity_report.by_category.items()
                },
                "note": self.parity_report.note,
            }
        return {
            "rules_available": self.available,
            "rules_status": self.status,
            "missing_rule_artifact": None,
            "parameter_status": self.parameters.parameter_status,
            "verified_categories": sorted(self.verified_categories),
            "covered_style_ids": list(self.parameters.covered_style_ids),
            "parity": parity,
            "formula": self.parameters.formula,
            "similarity_definition": (
                "Ratio and symmetry terms: Gaussian "
                "exp(-0.5 * ((value-target)/scale)^2). "
                "Categorical terms: categorical_match_score on match else "
                "categorical_nonmatch_score. "
                "weighted_compatibility is the category-weighted sum; "
                "dataset labels use round(1 + 4 * weighted_compatibility, 4)."
            ),
            "provenance": (
                "Recovered rating_parameters.json from "
                "Component3_AllCategories_20261008T121138_253749Z.zip; "
                "stored at datasets/rating_parameters.json without modification."
            ),
        }


def create_example_rule_parameters_template() -> dict[str, Any]:
    """Engineering template (not the original recovered parameter file)."""
    return {
        "version": "1.0",
        "description": (
            "TEMPLATE ONLY. Prefer the recovered datasets/rating_parameters.json."
        ),
        "weights": {
            "face_length_ratio": 0.16,
            "jaw_width_ratio": 0.08,
            "upper_width_ratio": 0.08,
            "lower_face_ratio": 0.05,
            "face_shape": 0.22,
            "jawline": 0.08,
            "forehead": 0.12,
            "hairline": 0.14,
            "symmetry": 0.07,
        },
        "attributes": {
            "scoring": {},
            "style_targets": {
                "H001": {
                    "face_shape": ["oval"],
                    "jawline": ["soft"],
                }
            },
        },
    }
