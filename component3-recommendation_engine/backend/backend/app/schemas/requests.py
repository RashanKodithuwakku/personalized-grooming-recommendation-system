"""Versioned recommendation request schemas."""

from __future__ import annotations

import math
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

CategoryLiteral = Literal["hair", "beard", "grooming"]
GenderLiteral = Literal["male", "female"]
RankingModeLiteral = Literal["standard", "confidence_aware"]
ConfidenceSourceLiteral = Literal["manual", "upstream", "unspecified"]

SUPPORTED_CATEGORIES: tuple[str, ...] = ("hair", "beard", "grooming")
SUPPORTED_GENDERS: tuple[str, ...] = ("male", "female")
SUPPORTED_RANKING_MODES: tuple[str, ...] = ("standard", "confidence_aware")
SUPPORTED_CONFIDENCE_SOURCES: tuple[str, ...] = (
    "manual",
    "upstream",
    "unspecified",
)

# Nine facial attributes used by weighted rules / confidence-aware scoring.
# Gender may appear in attribute_confidence for API compatibility but is not
# required for confidence_aware mode and is excluded from facial-rule weighting.
FACIAL_CONFIDENCE_KEYS: tuple[str, ...] = (
    "face_length_ratio",
    "jaw_width_ratio",
    "upper_width_ratio",
    "lower_face_ratio",
    "face_shape",
    "jawline",
    "forehead",
    "hairline",
    "symmetry",
)

# Training-contract categorical values observed in the gender-aware dataset.
SUPPORTED_FACE_SHAPES: tuple[str, ...] = (
    "diamond",
    "heart",
    "oblong",
    "oval",
    "round",
    "square",
)
SUPPORTED_JAWLINES: tuple[str, ...] = ("angular", "rounded", "soft")
SUPPORTED_FOREHEADS: tuple[str, ...] = ("high", "low", "medium")
SUPPORTED_HAIRLINES: tuple[str, ...] = (
    "receding",
    "rounded",
    "straight",
    "widows_peak",
)


def _normalize_token(value: str) -> str:
    return value.strip().lower()


def _require_finite(name: str, value: float) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{name} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be a finite number (NaN and Infinity rejected)")
    return number


class ProfileFeatures(BaseModel):
    """Facial attributes required by the CatBoost models.

    These fields match the gender-aware model feature contract.
    Missing essential attributes are rejected; values are never invented.
    """

    model_config = ConfigDict(extra="forbid")

    face_length_ratio: float
    jaw_width_ratio: float
    upper_width_ratio: float
    lower_face_ratio: float
    symmetry: float = Field(..., ge=0.0, le=1.0)
    face_shape: str
    jawline: str
    forehead: str
    hairline: str
    gender: str

    @field_validator(
        "face_length_ratio",
        "jaw_width_ratio",
        "upper_width_ratio",
        "lower_face_ratio",
        "symmetry",
        mode="before",
    )
    @classmethod
    def _finite_numeric(cls, value: Any, info: Any) -> float:
        return _require_finite(info.field_name, value)

    @field_validator("symmetry")
    @classmethod
    def _symmetry_bounds(cls, value: float) -> float:
        if value < 0.0 or value > 1.0:
            raise ValueError("symmetry must be within [0, 1]")
        return value

    @field_validator("face_shape", "jawline", "forehead", "hairline", "gender", mode="before")
    @classmethod
    def _normalize_categorical(cls, value: Any, info: Any) -> str:
        if value is None:
            raise ValueError(f"{info.field_name} is required")
        if not isinstance(value, str):
            raise ValueError(f"{info.field_name} must be a string")
        normalized = _normalize_token(value)
        if not normalized:
            raise ValueError(f"{info.field_name} must not be empty")
        return normalized

    @model_validator(mode="after")
    def _validate_supported_categoricals(self) -> ProfileFeatures:
        checks = {
            "face_shape": SUPPORTED_FACE_SHAPES,
            "jawline": SUPPORTED_JAWLINES,
            "forehead": SUPPORTED_FOREHEADS,
            "hairline": SUPPORTED_HAIRLINES,
            "gender": SUPPORTED_GENDERS,
        }
        errors: list[str] = []
        for field_name, allowed in checks.items():
            value = getattr(self, field_name)
            if value not in allowed:
                errors.append(
                    f"Unsupported {field_name}={value!r}. "
                    f"Supported values: {list(allowed)}"
                )
        if errors:
            raise ValueError("; ".join(errors))
        return self


class PreferenceOptions(BaseModel):
    """Optional eligibility preferences (not model features)."""

    model_config = ConfigDict(extra="forbid")

    include_beard: bool | None = None
    facial_hair_available: bool | None = None
    excluded_style_ids: list[str] = Field(default_factory=list)

    @field_validator("excluded_style_ids", mode="before")
    @classmethod
    def _normalize_exclusions(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("excluded_style_ids must be a list")
        normalized: list[str] = []
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, str):
                raise ValueError("excluded_style_ids entries must be strings")
            token = item.strip().upper()
            if not token:
                continue
            if token not in seen:
                seen.add(token)
                normalized.append(token)
        return normalized


class RecommendationRequest(BaseModel):
    """Versioned recommendation request contract for Component 3.

    A future Component 2 image-analysis service should populate the same
    ``profile`` object. Optional operational fields stay separate from
    model features.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    profile: ProfileFeatures
    categories: list[CategoryLiteral] = Field(
        default_factory=lambda: ["hair", "beard", "grooming"],
        min_length=1,
    )
    top_n: Annotated[int, Field(ge=1, le=50)] = 5
    preferences: PreferenceOptions = Field(default_factory=PreferenceOptions)
    attribute_confidence: dict[str, float] | None = None
    ranking_mode: RankingModeLiteral = "standard"
    confidence_source: ConfidenceSourceLiteral = "unspecified"

    @field_validator("categories", mode="before")
    @classmethod
    def _normalize_categories(cls, value: Any) -> list[str]:
        if value is None:
            return list(SUPPORTED_CATEGORIES)
        if not isinstance(value, list) or not value:
            raise ValueError("categories must be a non-empty list")
        normalized: list[str] = []
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, str):
                raise ValueError("category values must be strings")
            token = _normalize_token(item)
            if token not in SUPPORTED_CATEGORIES:
                raise ValueError(
                    f"Unsupported category={token!r}. "
                    f"Supported categories: {list(SUPPORTED_CATEGORIES)}. "
                    "Unsupported categories are not remapped."
                )
            if token not in seen:
                seen.add(token)
                normalized.append(token)
        return normalized

    @field_validator("ranking_mode", mode="before")
    @classmethod
    def _normalize_ranking_mode(cls, value: Any) -> str:
        if value is None:
            return "standard"
        if not isinstance(value, str):
            raise ValueError("ranking_mode must be a string")
        token = _normalize_token(value)
        if token not in SUPPORTED_RANKING_MODES:
            raise ValueError(
                f"Unsupported ranking_mode={value!r}. "
                f"Supported values: {list(SUPPORTED_RANKING_MODES)}"
            )
        return token

    @field_validator("confidence_source", mode="before")
    @classmethod
    def _normalize_confidence_source(cls, value: Any) -> str:
        if value is None:
            return "unspecified"
        if not isinstance(value, str):
            raise ValueError("confidence_source must be a string")
        token = _normalize_token(value)
        if token not in SUPPORTED_CONFIDENCE_SOURCES:
            raise ValueError(
                f"Unsupported confidence_source={value!r}. "
                f"Supported values: {list(SUPPORTED_CONFIDENCE_SOURCES)}"
            )
        return token

    @field_validator("attribute_confidence")
    @classmethod
    def _validate_confidence_map(
        cls, value: dict[str, float] | None
    ) -> dict[str, float] | None:
        if value is None:
            return None
        allowed_keys = set(FACIAL_CONFIDENCE_KEYS) | {"gender"}
        cleaned: dict[str, float] = {}
        for raw_key, raw_val in value.items():
            if not isinstance(raw_key, str):
                raise ValueError("attribute_confidence keys must be strings")
            key = _normalize_token(raw_key)
            if key not in allowed_keys:
                raise ValueError(
                    f"Unknown attribute_confidence key={raw_key!r}. "
                    f"Allowed keys: {sorted(allowed_keys)}"
                )
            number = _require_finite(f"attribute_confidence[{key}]", raw_val)
            if number < 0.0 or number > 1.0:
                raise ValueError(
                    f"attribute_confidence[{key}] must be within [0, 1]"
                )
            cleaned[key] = number
        return cleaned

    @model_validator(mode="after")
    def _confidence_aware_requires_complete_facial_map(
        self,
    ) -> RecommendationRequest:
        if self.ranking_mode != "confidence_aware":
            return self
        if self.attribute_confidence is None:
            raise ValueError(
                "ranking_mode='confidence_aware' requires attribute_confidence "
                f"with all nine facial attributes: {list(FACIAL_CONFIDENCE_KEYS)}. "
                "Zero values are accepted; missing keys are not."
            )
        missing = [
            key
            for key in FACIAL_CONFIDENCE_KEYS
            if key not in self.attribute_confidence
        ]
        if missing:
            raise ValueError(
                "ranking_mode='confidence_aware' requires all nine facial "
                f"confidence values. Missing: {missing}. "
                "Gender confidence is optional and excluded from facial-rule "
                "weighting. Zero confidence is accepted."
            )
        return self
