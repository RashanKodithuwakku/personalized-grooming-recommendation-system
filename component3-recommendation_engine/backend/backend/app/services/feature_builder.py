"""Build candidate feature matrices in the exact model feature order."""

from __future__ import annotations

from typing import Any

import pandas as pd

from app.schemas.requests import ProfileFeatures
from app.services.artifact_loader import EXPECTED_MODEL_FEATURES


class FeatureBuilder:
    """Construct CatBoost input frames using verified feature names/order."""

    def __init__(self, feature_names: list[str] | None = None) -> None:
        self.feature_names = list(feature_names or EXPECTED_MODEL_FEATURES)
        if self.feature_names != EXPECTED_MODEL_FEATURES:
            # Still allow model-reported order if it matches expected set.
            if sorted(self.feature_names) != sorted(EXPECTED_MODEL_FEATURES):
                raise ValueError(
                    f"Unsupported feature names: {self.feature_names}"
                )

    def build_candidates(
        self,
        profile: ProfileFeatures,
        styles: pd.DataFrame,
    ) -> pd.DataFrame:
        """Return a DataFrame with one row per candidate style.

        Categorical columns are kept as strings. Numeric columns are float.
        Feature column order matches the loaded model contract exactly.
        """
        if styles.empty:
            return pd.DataFrame(columns=self.feature_names)

        profile_data = profile.model_dump()
        rows: list[dict[str, Any]] = []
        for _, style in styles.iterrows():
            row = {
                "face_length_ratio": float(profile_data["face_length_ratio"]),
                "jaw_width_ratio": float(profile_data["jaw_width_ratio"]),
                "upper_width_ratio": float(profile_data["upper_width_ratio"]),
                "lower_face_ratio": float(profile_data["lower_face_ratio"]),
                "symmetry": float(profile_data["symmetry"]),
                "face_shape": str(profile_data["face_shape"]),
                "jawline": str(profile_data["jawline"]),
                "forehead": str(profile_data["forehead"]),
                "hairline": str(profile_data["hairline"]),
                "gender": str(profile_data["gender"]),
                "style_id": str(style["style_id"]),
                "category": str(style["category"]),
            }
            rows.append(row)

        frame = pd.DataFrame(rows)
        # Enforce exact column order required by the model.
        frame = frame[self.feature_names]
        return frame

    def build_single(
        self,
        profile: ProfileFeatures,
        style_id: str,
        category: str,
    ) -> pd.DataFrame:
        styles = pd.DataFrame(
            [{"style_id": style_id, "category": category}]
        )
        return self.build_candidates(profile, styles)
