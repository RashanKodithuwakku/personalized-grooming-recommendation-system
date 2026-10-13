"""Project-relative path resolution independent of the process working directory."""

from __future__ import annotations

from pathlib import Path

# backend/app/core/paths.py -> backend/
BACKEND_ROOT: Path = Path(__file__).resolve().parents[2]

DEFAULT_MODELS_DIR: Path = BACKEND_ROOT / "models"
DEFAULT_DATASETS_DIR: Path = BACKEND_ROOT / "datasets"
DEFAULT_CATALOGUE_PATH: Path = (
    DEFAULT_DATASETS_DIR / "generated_data" / "style_catalogue.csv"
)
DEFAULT_SCHEMA_PATH: Path = DEFAULT_MODELS_DIR / "gender_aware_schema.json"
DEFAULT_RUN_INFO_PATH: Path = DEFAULT_MODELS_DIR / "run_information.json"
DEFAULT_TRAINING_SUMMARY_PATH: Path = DEFAULT_MODELS_DIR / "training_summary.csv"
DEFAULT_EVALUATION_PATH: Path = DEFAULT_MODELS_DIR / "gender_evaluation.csv"
DEFAULT_DATASET_METADATA_PATH: Path = DEFAULT_DATASETS_DIR / "dataset_metadata.json"
DEFAULT_TRAIN_SPLIT_PATH: Path = (
    DEFAULT_DATASETS_DIR / "generated_data" / "splits" / "train.csv"
)
DEFAULT_TRAINING_PAIRS_PATH: Path = (
    DEFAULT_DATASETS_DIR / "generated_data" / "training_pairs.csv"
)
DEFAULT_RULE_PARAMETERS_PATH: Path = DEFAULT_DATASETS_DIR / "rating_parameters.json"
DEFAULT_TEST_PREDICTIONS_PATH: Path = DEFAULT_MODELS_DIR / "gender_test_predictions.csv"

# Nested model binaries directory (intentional layout).
DEFAULT_MODEL_BINARIES_DIR: Path = DEFAULT_MODELS_DIR / "models"

MODEL_FILENAMES: dict[str, str] = {
    "hair": "hair_ranker_gender_aware.cbm",
    "beard": "beard_ranker_gender_aware.cbm",
    "grooming": "grooming_ranker_gender_aware.cbm",
    "compatibility": "compatibility_scorer_gender_aware.cbm",
}
