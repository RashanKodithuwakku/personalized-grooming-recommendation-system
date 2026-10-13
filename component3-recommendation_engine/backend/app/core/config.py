"""Environment-backed application settings."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.paths import (
    BACKEND_ROOT,
    DEFAULT_CATALOGUE_PATH,
    DEFAULT_DATASETS_DIR,
    DEFAULT_MODELS_DIR,
    DEFAULT_RULE_PARAMETERS_PATH,
    DEFAULT_SCHEMA_PATH,
)


class Settings(BaseSettings):
    """Runtime configuration resolved relative to the backend project root."""

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Style Recommendation and Ranking Engine"
    app_version: str = "1.0.0"
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"

    models_dir: Path = DEFAULT_MODELS_DIR
    datasets_dir: Path = DEFAULT_DATASETS_DIR
    catalogue_path: Path = DEFAULT_CATALOGUE_PATH
    schema_path: Path = DEFAULT_SCHEMA_PATH
    # Recovered original parameters (datasets/rating_parameters.json).
    rule_parameters_path: Path | None = DEFAULT_RULE_PARAMETERS_PATH
    # Startup parity vs training_pairs.csv labels (can be disabled for fast boot).
    rule_parity_check_on_startup: bool = True

    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost",
            "http://localhost:3000",
            "http://localhost:8080",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8080",
        ]
    )
    cors_allow_credentials: bool = False

    catboost_thread_count: int = Field(default=1, ge=1, le=32)
    max_top_n: int = Field(default=20, ge=1, le=50)
    default_top_n: int = Field(default=5, ge=1, le=50)

    # Provisional engineering hybrid weights (not research-validated).
    # Without rule parameters: predicted_compat + rank_percentile.
    weight_predicted_compat_no_rules: float = Field(default=0.70, ge=0.0, le=1.0)
    weight_rank_percentile_no_rules: float = Field(default=0.30, ge=0.0, le=1.0)

    # With verified rule parameters.
    weight_predicted_compat_with_rules: float = Field(default=0.50, ge=0.0, le=1.0)
    weight_rank_percentile_with_rules: float = Field(default=0.30, ge=0.0, le=1.0)
    weight_rule_compat_with_rules: float = Field(default=0.20, ge=0.0, le=1.0)

    input_quality_caution_threshold: float = Field(default=0.60, ge=0.0, le=1.0)
    low_confidence_attribute_threshold: float = Field(default=0.50, ge=0.0, le=1.0)
    # Require full nine-attribute facial confidence coverage for "adequate".
    input_quality_min_coverage: float = Field(default=1.0, ge=0.0, le=1.0)

    # Empirical OOD warning padding (fraction of training range width).
    ood_range_padding: float = Field(default=0.0, ge=0.0, le=0.5)

    @field_validator(
        "models_dir",
        "datasets_dir",
        "catalogue_path",
        "schema_path",
        mode="before",
    )
    @classmethod
    def _resolve_path(cls, value: Any) -> Path:
        path = Path(value)
        if not path.is_absolute():
            path = (BACKEND_ROOT / path).resolve()
        return path

    @field_validator("rule_parameters_path", mode="before")
    @classmethod
    def _resolve_optional_path(cls, value: Any) -> Path | None:
        if value is None or value == "" or value == "None":
            return None
        path = Path(value)
        if not path.is_absolute():
            path = (BACKEND_ROOT / path).resolve()
        return path

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            items = [part.strip() for part in value.split(",")]
            return [item for item in items if item]
        return list(value)

    @model_validator(mode="after")
    def _validate_weight_sums(self) -> Settings:
        no_rules = (
            self.weight_predicted_compat_no_rules + self.weight_rank_percentile_no_rules
        )
        if abs(no_rules - 1.0) > 1e-6:
            raise ValueError(
                "Weights without rules must sum to 1.0 "
                f"(got {no_rules:.6f}). These are provisional engineering defaults."
            )
        with_rules = (
            self.weight_predicted_compat_with_rules
            + self.weight_rank_percentile_with_rules
            + self.weight_rule_compat_with_rules
        )
        if abs(with_rules - 1.0) > 1e-6:
            raise ValueError(
                "Weights with rules must sum to 1.0 "
                f"(got {with_rules:.6f}). These are provisional engineering defaults."
            )
        if self.default_top_n > self.max_top_n:
            raise ValueError("default_top_n cannot exceed max_top_n")
        if self.cors_allow_credentials and "*" in self.cors_origins:
            raise ValueError("Wildcard CORS origins are not allowed with credentials")
        return self

    def hybrid_weights(self, rules_available: bool) -> dict[str, float]:
        """Return the active provisional hybrid ordering weights."""
        if rules_available:
            return {
                "predicted_compatibility": self.weight_predicted_compat_with_rules,
                "rank_percentile": self.weight_rank_percentile_with_rules,
                "rule_compatibility": self.weight_rule_compat_with_rules,
            }
        return {
            "predicted_compatibility": self.weight_predicted_compat_no_rules,
            "rank_percentile": self.weight_rank_percentile_no_rules,
            "rule_compatibility": 0.0,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
