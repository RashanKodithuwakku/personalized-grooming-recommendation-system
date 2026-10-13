"""Explicit eligibility rules for style candidates.

These are application defaults and model-coverage constraints, not
biological claims. Training exclusion of female beard rows does not by
itself enforce inference behavior; this module does.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from app.schemas.requests import PreferenceOptions, ProfileFeatures


@dataclass
class EligibilityDecision:
    include_category: bool
    skip_reason: str | None = None
    skip_status: str | None = None
    applied_rules: list[str] = field(default_factory=list)
    eligible_styles: pd.DataFrame = field(default_factory=pd.DataFrame)
    empty_reason: str | None = None


class EligibilityService:
    """Apply catalogue and preference filters before ranking."""

    def evaluate_category(
        self,
        category: str,
        profile: ProfileFeatures,
        preferences: PreferenceOptions,
        catalogue_category: pd.DataFrame,
    ) -> EligibilityDecision:
        applied: list[str] = []
        category = category.lower()

        # --- Beard coverage / preference rules ---
        if category == "beard":
            if preferences.include_beard is False:
                applied.append("explicit_include_beard_false")
                return EligibilityDecision(
                    include_category=False,
                    skip_reason=(
                        "Beard recommendations skipped because include_beard=false."
                    ),
                    skip_status="excluded_by_preference",
                    applied_rules=applied,
                )

            if profile.gender == "female" and preferences.include_beard is not True:
                applied.append("female_default_skip_beard")
                return EligibilityDecision(
                    include_category=False,
                    skip_reason=(
                        "Beard recommendations skipped for female profiles by default "
                        "when include_beard is not explicitly true. This is an "
                        "application default / model-coverage constraint, not a "
                        "biological claim."
                    ),
                    skip_status="default_gender_policy",
                    applied_rules=applied,
                )

            if profile.gender == "female" and preferences.include_beard is True:
                applied.append("female_beard_unsupported_model_coverage")
                return EligibilityDecision(
                    include_category=False,
                    skip_reason=(
                        "Unsupported model coverage for female beard recommendations. "
                        "The beard ranker was trained on male profiles only "
                        "(female beard training rows were excluded). An explicit "
                        "include_beard=true request is acknowledged but not treated "
                        "as a validated use case."
                    ),
                    skip_status="unsupported_model_coverage",
                    applied_rules=applied,
                )

            if profile.gender == "male" and preferences.include_beard is None:
                applied.append("male_default_allow_beard")

        styles = catalogue_category.copy()
        if styles.empty:
            return EligibilityDecision(
                include_category=True,
                applied_rules=applied,
                eligible_styles=styles,
                empty_reason=f"No catalogue styles for category={category}.",
            )

        # Catalogue gender restriction when present and not "none".
        if "gender_restriction" in styles.columns:
            before = len(styles)
            restriction = styles["gender_restriction"].astype(str).str.strip().str.lower()
            mask = restriction.isin(["", "none", "nan", "null"]) | (
                restriction == profile.gender
            )
            styles = styles.loc[mask].copy()
            if len(styles) != before:
                applied.append("catalogue_gender_restriction")

        # Facial-hair availability: only exclude styles that require facial hair.
        if preferences.facial_hair_available is False:
            before = len(styles)
            requires = styles["requires_facial_hair"].astype(bool)
            styles = styles.loc[~requires].copy()
            if len(styles) != before:
                applied.append("facial_hair_available_false_filter")
            # Clean-shaven / non-requiring styles remain eligible.

        # Excluded style IDs.
        if preferences.excluded_style_ids:
            before = len(styles)
            excluded = {sid.upper() for sid in preferences.excluded_style_ids}
            styles = styles.loc[~styles["style_id"].isin(excluded)].copy()
            if len(styles) != before:
                applied.append("excluded_style_ids")

        empty_reason = None
        if styles.empty:
            empty_reason = (
                f"No eligible {category} styles remain after applying eligibility rules."
            )

        return EligibilityDecision(
            include_category=True,
            applied_rules=applied,
            eligible_styles=styles.reset_index(drop=True),
            empty_reason=empty_reason,
        )
