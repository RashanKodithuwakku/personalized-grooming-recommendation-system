"""Load and validate models, schema, catalogue, and metadata once at startup."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
from catboost import CatBoostRanker, CatBoostRegressor

from app.core.config import Settings
from app.core.exceptions import ArtifactError
from app.core.logging import get_logger
from app.core.paths import (
    DEFAULT_DATASET_METADATA_PATH,
    DEFAULT_EVALUATION_PATH,
    DEFAULT_MODEL_BINARIES_DIR,
    DEFAULT_RUN_INFO_PATH,
    DEFAULT_TRAIN_SPLIT_PATH,
    DEFAULT_TRAINING_PAIRS_PATH,
    DEFAULT_TRAINING_SUMMARY_PATH,
    MODEL_FILENAMES,
)
from app.schemas.requests import (
    SUPPORTED_CATEGORIES,
    SUPPORTED_FACE_SHAPES,
    SUPPORTED_FOREHEADS,
    SUPPORTED_GENDERS,
    SUPPORTED_HAIRLINES,
    SUPPORTED_JAWLINES,
)
from app.services.compatibility_rules import CompatibilityRulesService

logger = get_logger(__name__)

EXPECTED_PROFILE_FEATURES = [
    "face_length_ratio",
    "jaw_width_ratio",
    "upper_width_ratio",
    "lower_face_ratio",
    "symmetry",
    "face_shape",
    "jawline",
    "forehead",
    "hairline",
    "gender",
]
EXPECTED_MODEL_FEATURES = EXPECTED_PROFILE_FEATURES + ["style_id", "category"]
EXPECTED_CATEGORICAL_FEATURES = [
    "face_shape",
    "jawline",
    "forehead",
    "hairline",
    "gender",
    "style_id",
    "category",
]
NUMERIC_FEATURES = [
    "face_length_ratio",
    "jaw_width_ratio",
    "upper_width_ratio",
    "lower_face_ratio",
    "symmetry",
]


@dataclass
class LoadedModel:
    name: str
    role: str
    filename: str
    path: Path
    model: CatBoostRanker | CatBoostRegressor
    feature_names: list[str]
    categorical_indices: list[int]
    categorical_names: list[str]
    sha256: str


@dataclass
class ArtifactBundle:
    ready: bool = False
    diagnostics: list[str] = field(default_factory=list)
    schema: dict[str, Any] = field(default_factory=dict)
    catalogue: pd.DataFrame = field(default_factory=pd.DataFrame)
    styles_by_category: dict[str, pd.DataFrame] = field(default_factory=dict)
    styles_by_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    rankers: dict[str, LoadedModel] = field(default_factory=dict)
    scorer: LoadedModel | None = None
    run_information: dict[str, Any] = field(default_factory=dict)
    dataset_metadata: dict[str, Any] = field(default_factory=dict)
    training_summary: pd.DataFrame = field(default_factory=pd.DataFrame)
    evaluation: pd.DataFrame = field(default_factory=pd.DataFrame)
    empirical_numeric_ranges: dict[str, dict[str, float]] = field(default_factory=dict)
    artifact_version: str = "unknown"
    rules: CompatibilityRulesService | None = None
    model_binaries_dir: Path | None = None

    def models_loaded_map(self) -> dict[str, bool]:
        return {
            "hair": "hair" in self.rankers,
            "beard": "beard" in self.rankers,
            "grooming": "grooming" in self.rankers,
            "compatibility": self.scorer is not None,
        }


class ArtifactLoader:
    """Validates and loads inference artifacts. Never invents model output."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.bundle = ArtifactBundle()

    def load(self) -> ArtifactBundle:
        diagnostics: list[str] = []
        try:
            self.bundle.schema = self._load_schema()
            self._validate_schema(self.bundle.schema)
        except ArtifactError as exc:
            diagnostics.append(exc.message)
            diagnostics.extend(exc.diagnostics)

        try:
            catalogue = self._load_catalogue()
            self.bundle.catalogue = catalogue
            self.bundle.styles_by_category = {
                category: catalogue.loc[catalogue["category"] == category].copy()
                for category in SUPPORTED_CATEGORIES
            }
            self.bundle.styles_by_id = {
                row["style_id"]: row.to_dict() for _, row in catalogue.iterrows()
            }
        except ArtifactError as exc:
            diagnostics.append(exc.message)
            diagnostics.extend(exc.diagnostics)

        binaries_dir = self.settings.models_dir / "models"
        if not binaries_dir.exists():
            # Fall back to explicit nested default if models_dir already points there.
            if DEFAULT_MODEL_BINARIES_DIR.exists():
                binaries_dir = DEFAULT_MODEL_BINARIES_DIR
            else:
                diagnostics.append(
                    f"Model binaries directory missing under {self.settings.models_dir.name}/models"
                )
        self.bundle.model_binaries_dir = binaries_dir

        for category in ("hair", "beard", "grooming"):
            try:
                loaded = self._load_ranker(category, binaries_dir)
                self.bundle.rankers[category] = loaded
            except ArtifactError as exc:
                diagnostics.append(exc.message)
                diagnostics.extend(exc.diagnostics)

        try:
            self.bundle.scorer = self._load_scorer(binaries_dir)
        except ArtifactError as exc:
            diagnostics.append(exc.message)
            diagnostics.extend(exc.diagnostics)

        self.bundle.run_information = self._safe_load_json(DEFAULT_RUN_INFO_PATH)
        self.bundle.dataset_metadata = self._safe_load_json(DEFAULT_DATASET_METADATA_PATH)
        self.bundle.training_summary = self._safe_load_csv(DEFAULT_TRAINING_SUMMARY_PATH)
        self.bundle.evaluation = self._safe_load_csv(DEFAULT_EVALUATION_PATH)
        self.bundle.empirical_numeric_ranges = self._compute_empirical_ranges()
        self.bundle.artifact_version = self._compute_artifact_version()
        catalogue_ids: set[str] = set()
        if not self.bundle.catalogue.empty and "style_id" in self.bundle.catalogue.columns:
            catalogue_ids = set(
                self.bundle.catalogue["style_id"].astype(str).str.upper().tolist()
            )
        self.bundle.rules = CompatibilityRulesService(
            rule_parameters_path=self.settings.rule_parameters_path,
            catalogue_style_ids=catalogue_ids,
            training_pairs_path=DEFAULT_TRAINING_PAIRS_PATH,
            run_parity_check=bool(self.settings.rule_parity_check_on_startup),
        )
        if self.bundle.rules.available:
            logger.info(
                "Weighted rules available verified_categories=%s parameter_status=%s",
                sorted(self.bundle.rules.verified_categories),
                self.bundle.rules.parameter_status,
            )
            if self.bundle.rules.parity_report is not None:
                report = self.bundle.rules.parity_report
                logger.info(
                    "Rule parity checked_rows=%s mae=%s max_abs_error=%s mismatches=%s",
                    report.checked_rows,
                    report.mae,
                    report.max_abs_error,
                    report.mismatches,
                )
        elif self.bundle.rules.load_diagnostics:
            # Rules absence/failure is a capability limitation, not model unreadiness.
            logger.warning(
                "Weighted rules unavailable: %s",
                "; ".join(self.bundle.rules.load_diagnostics),
            )

        hash_diagnostics = self._verify_model_hashes()
        diagnostics.extend(hash_diagnostics)

        hard_diagnostics = [
            d
            for d in diagnostics
            if not d.startswith("Model hash mismatch")
        ]
        ready = (
            len(hard_diagnostics) == 0
            and len(self.bundle.rankers) == 3
            and self.bundle.scorer is not None
            and not self.bundle.catalogue.empty
            and bool(self.bundle.schema)
        )
        # Hash mismatches are reported in diagnostics but do not block readiness
        # when models load and feature contracts already matched.

        self.bundle.ready = ready
        self.bundle.diagnostics = diagnostics
        if ready:
            logger.info(
                "Artifacts loaded successfully artifact_version=%s models=%s",
                self.bundle.artifact_version,
                list(self.bundle.rankers.keys()) + ["compatibility"],
            )
        else:
            logger.error("Artifact loading failed: %s", "; ".join(diagnostics))
        return self.bundle

    def _load_schema(self) -> dict[str, Any]:
        path = self.settings.schema_path
        if not path.exists():
            raise ArtifactError(
                "Schema file missing",
                diagnostics=[f"Expected schema at models/{path.name}"],
            )
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ArtifactError(
                "Schema file invalid",
                diagnostics=[f"Could not parse {path.name}: {exc}"],
            ) from exc

    def _validate_schema(self, schema: dict[str, Any]) -> None:
        diagnostics: list[str] = []
        for key, expected in (
            ("profile_features", EXPECTED_PROFILE_FEATURES),
            ("model_features", EXPECTED_MODEL_FEATURES),
            ("categorical_features", EXPECTED_CATEGORICAL_FEATURES),
        ):
            actual = schema.get(key)
            if actual != expected:
                diagnostics.append(
                    f"Schema {key} mismatch. expected={expected} actual={actual}"
                )
        categories = schema.get("categories")
        if list(categories or []) != list(SUPPORTED_CATEGORIES):
            diagnostics.append(
                f"Schema categories mismatch: {categories}"
            )
        genders = schema.get("gender_values")
        if list(genders or []) != list(SUPPORTED_GENDERS):
            diagnostics.append(f"Schema gender_values mismatch: {genders}")
        if diagnostics:
            raise ArtifactError("Schema validation failed", diagnostics=diagnostics)

    def _load_catalogue(self) -> pd.DataFrame:
        path = self.settings.catalogue_path
        if not path.exists():
            raise ArtifactError(
                "Catalogue missing",
                diagnostics=[f"Expected catalogue at {path.name}"],
            )
        try:
            df = pd.read_csv(path)
        except Exception as exc:  # noqa: BLE001
            raise ArtifactError(
                "Catalogue unreadable",
                diagnostics=[str(exc)],
            ) from exc
        required = {
            "style_id",
            "category",
            "style_name",
            "requires_facial_hair",
            "gender_restriction",
        }
        missing = required - set(df.columns)
        if missing:
            raise ArtifactError(
                "Catalogue schema incomplete",
                diagnostics=[f"Missing columns: {sorted(missing)}"],
            )
        if df.empty:
            raise ArtifactError("Catalogue is empty", diagnostics=["no styles"])
        df = df.copy()
        df["style_id"] = df["style_id"].astype(str).str.strip().str.upper()
        df["category"] = df["category"].astype(str).str.strip().str.lower()
        df["style_name"] = df["style_name"].astype(str)
        df["requires_facial_hair"] = df["requires_facial_hair"].map(self._as_bool)
        if "availability_constraints_validated" in df.columns:
            df["availability_constraints_validated"] = df[
                "availability_constraints_validated"
            ].map(self._as_bool)
        if df["style_id"].duplicated().any():
            dupes = df.loc[df["style_id"].duplicated(), "style_id"].tolist()
            raise ArtifactError(
                "Catalogue has duplicate style_id values",
                diagnostics=[f"duplicates={dupes}"],
            )
        unknown_categories = sorted(set(df["category"]) - set(SUPPORTED_CATEGORIES))
        if unknown_categories:
            raise ArtifactError(
                "Catalogue contains unsupported categories",
                diagnostics=[f"unknown={unknown_categories}"],
            )
        for category in SUPPORTED_CATEGORIES:
            if df.loc[df["category"] == category].empty:
                raise ArtifactError(
                    "Catalogue missing expected category",
                    diagnostics=[f"category={category} has no styles"],
                )
        return df

    @staticmethod
    def _as_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        text = str(value).strip().lower()
        return text in {"1", "true", "yes", "y"}

    def _load_ranker(self, category: str, binaries_dir: Path) -> LoadedModel:
        filename = MODEL_FILENAMES[category]
        path = binaries_dir / filename
        if not path.exists():
            raise ArtifactError(
                f"Ranker model missing for {category}",
                diagnostics=[f"Missing file models/models/{filename}"],
            )
        # thread_count is applied at predict-time (CatBoost 1.2.x has no
        # set_thread_count on loaded Ranker/Regressor objects).
        model = CatBoostRanker(thread_count=self.settings.catboost_thread_count)
        try:
            model.load_model(str(path))
        except Exception as exc:  # noqa: BLE001
            raise ArtifactError(
                f"Failed to load ranker {filename}",
                diagnostics=[str(exc)],
            ) from exc
        return self._wrap_model(
            name=f"{category}_ranker",
            role="ranker",
            filename=filename,
            path=path,
            model=model,
        )

    def _load_scorer(self, binaries_dir: Path) -> LoadedModel:
        filename = MODEL_FILENAMES["compatibility"]
        path = binaries_dir / filename
        if not path.exists():
            raise ArtifactError(
                "Compatibility scorer missing",
                diagnostics=[f"Missing file models/models/{filename}"],
            )
        model = CatBoostRegressor(thread_count=self.settings.catboost_thread_count)
        try:
            model.load_model(str(path))
        except Exception as exc:  # noqa: BLE001
            raise ArtifactError(
                f"Failed to load scorer {filename}",
                diagnostics=[str(exc)],
            ) from exc
        return self._wrap_model(
            name="compatibility_scorer",
            role="regressor",
            filename=filename,
            path=path,
            model=model,
        )

    def _wrap_model(
        self,
        name: str,
        role: str,
        filename: str,
        path: Path,
        model: CatBoostRanker | CatBoostRegressor,
    ) -> LoadedModel:
        feature_names = list(model.feature_names_)
        if feature_names != EXPECTED_MODEL_FEATURES:
            raise ArtifactError(
                f"Feature contract mismatch for {filename}",
                diagnostics=[
                    f"expected={EXPECTED_MODEL_FEATURES}",
                    f"actual={feature_names}",
                ],
            )
        cat_indices = list(model.get_cat_feature_indices())
        cat_names = [feature_names[i] for i in cat_indices]
        if cat_names != EXPECTED_CATEGORICAL_FEATURES:
            # Allow same set with matching indices relative to feature_names.
            if sorted(cat_names) != sorted(EXPECTED_CATEGORICAL_FEATURES):
                raise ArtifactError(
                    f"Categorical feature mismatch for {filename}",
                    diagnostics=[
                        f"expected={EXPECTED_CATEGORICAL_FEATURES}",
                        f"actual={cat_names}",
                    ],
                )
            # Order must match model indices; keep model's order but warn via diagnostic
            # only if relative order differs from schema order.
            if cat_names != EXPECTED_CATEGORICAL_FEATURES:
                logger.warning(
                    "Categorical order for %s is %s (schema order %s); "
                    "using model order for inference.",
                    filename,
                    cat_names,
                    EXPECTED_CATEGORICAL_FEATURES,
                )
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return LoadedModel(
            name=name,
            role=role,
            filename=filename,
            path=path,
            model=model,
            feature_names=feature_names,
            categorical_indices=cat_indices,
            categorical_names=cat_names,
            sha256=digest,
        )

    def _verify_model_hashes(self) -> list[str]:
        diagnostics: list[str] = []
        hashes = self.bundle.run_information.get("model_hashes", {})
        if not hashes:
            return diagnostics
        loaded = list(self.bundle.rankers.values())
        if self.bundle.scorer is not None:
            loaded.append(self.bundle.scorer)
        for item in loaded:
            expected = hashes.get(item.filename)
            if expected and expected != item.sha256:
                diagnostics.append(
                    f"Model hash mismatch for {item.filename}: "
                    f"expected={expected[:12]}... actual={item.sha256[:12]}..."
                )
        return diagnostics

    def _compute_artifact_version(self) -> str:
        parts: list[str] = []
        for category in ("hair", "beard", "grooming"):
            loaded = self.bundle.rankers.get(category)
            if loaded:
                parts.append(loaded.sha256[:12])
        if self.bundle.scorer:
            parts.append(self.bundle.scorer.sha256[:12])
        if not parts:
            return "unavailable"
        return "ga-" + "-".join(parts)

    def _compute_empirical_ranges(self) -> dict[str, dict[str, float]]:
        """Derive empirical training ranges for OOD warnings (not biological limits)."""
        ranges: dict[str, dict[str, float]] = {}
        train_path = DEFAULT_TRAIN_SPLIT_PATH
        if not train_path.exists():
            return ranges
        try:
            # Read only numeric profile columns to avoid loading full pair table memory heavily.
            usecols = ["profile_id"] + NUMERIC_FEATURES
            df = pd.read_csv(train_path, usecols=lambda c: c in usecols)
            # Deduplicate by profile to avoid style-pair inflation.
            if "profile_id" in df.columns:
                df = df.drop_duplicates(subset=["profile_id"])
            for col in NUMERIC_FEATURES:
                if col not in df.columns:
                    continue
                series = pd.to_numeric(df[col], errors="coerce").dropna()
                if series.empty:
                    continue
                ranges[col] = {
                    "min": float(series.min()),
                    "max": float(series.max()),
                    "mean": float(series.mean()),
                }
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not compute empirical ranges: %s", exc)
        return ranges

    @staticmethod
    def _safe_load_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _safe_load_csv(path: Path) -> pd.DataFrame:
        if not path.exists():
            return pd.DataFrame()
        try:
            return pd.read_csv(path)
        except Exception:  # noqa: BLE001
            return pd.DataFrame()


def supported_categorical_values() -> dict[str, list[str]]:
    return {
        "face_shape": list(SUPPORTED_FACE_SHAPES),
        "jawline": list(SUPPORTED_JAWLINES),
        "forehead": list(SUPPORTED_FOREHEADS),
        "hairline": list(SUPPORTED_HAIRLINES),
        "gender": list(SUPPORTED_GENDERS),
        "category": list(SUPPORTED_CATEGORIES),
    }
