"""Run face-shape identification plus symmetry and balance scoring."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from face_shape.contracts import FaceShapeName, MorphologicalClass, RatioFeatures
from face_shape.geometry import prepare_landmarks
from face_shape.indices import DegenerateMeasurement
from face_shape.payload import Component1Payload, to_classification_input
from face_shape.score.balance import BalanceResult, score_balance
from face_shape.score.symmetry import PairDeviation, SymmetryResult, score_symmetry
from face_shape.thresholds import FZI_BROAD, FZI_NARROW
from face_shape.tier2 import classify_face


class ForeheadCategory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    width: Literal["broad", "average", "narrow"] | None = None
    height: Literal["high", "average", "low"] | None = None


class FacialProfile(BaseModel):
    """C3-facing profile. Composite weights are intentionally omitted."""

    model_config = ConfigDict(extra="forbid")

    request_id: str
    status: Literal["ok", "limited_analysis", "error"]
    error_code: str | None = None
    face_shape_class: MorphologicalClass | None = None
    mfi_value: float | None = None
    face_shape_label: FaceShapeName | None = None
    face_shape_confidence: dict[FaceShapeName, float] | None = None
    jawline_category: str | None = None
    forehead_category: ForeheadCategory | None = None
    hairline: dict[str, Any] | None = None
    jawline: dict[str, Any] | None = None
    anthropometric_ratios: RatioFeatures | None = None
    thirds: dict[str, float] = Field(default_factory=dict)
    fifths: dict[str, float] = Field(default_factory=dict)
    symmetry_score: float | None = None
    asymmetry_index: float | None = None
    per_pair_deviations: list[PairDeviation] = Field(default_factory=list)
    vertical_balance_score: float | None = None
    horizontal_balance_score: float | None = None
    balance_score: float | None = None
    reliability: float | None = None
    rationale: str | None = None
    processing_notes: list[str] = Field(default_factory=list)


def analyse_profile(payload: Component1Payload) -> FacialProfile:
    notes = list(payload.processing_notes)
    if payload.quality.status == "rejected" or payload.error is not None:
        code = "LOW_CONFIDENCE"
        if payload.error and "code" in payload.error:
            code = str(payload.error["code"])
        return FacialProfile(
            request_id=payload.request_id,
            status="error",
            error_code=code,
            processing_notes=notes,
        )

    try:
        sample = to_classification_input(payload)
        prepared = prepare_landmarks(sample)
        shape = classify_face(sample)
    except (ValueError, DegenerateMeasurement) as exc:
        return FacialProfile(
            request_id=payload.request_id,
            status="error",
            error_code="MISSING_LANDMARKS",
            processing_notes=notes + [str(exc)],
        )

    symmetry = score_symmetry(
        prepared,
        yaw=payload.pose.yaw,
        neutral_expression=payload.quality.neutral_expression,
    )
    balance = score_balance(prepared)
    notes.extend(shape.processing_notes)
    notes.extend(symmetry.notes)
    notes.extend(balance.notes)

    status: Literal["ok", "limited_analysis", "error"] = "ok"
    limited = {
        "limited_upper_third",
        "narrow_jaw_unresolved",
        "symmetry_pose_limited",
        "missing_frontotemporale",
    }
    if limited.intersection(notes) or not payload.pose.pose_ok:
        status = "limited_analysis"

    return FacialProfile(
        request_id=payload.request_id,
        status=status,
        face_shape_class=shape.face_shape_class,
        mfi_value=shape.ratios.mfi,
        face_shape_label=shape.face_type,
        face_shape_confidence=shape.face_type_confidence,
        jawline_category=payload.jawline.jaw_type,
        forehead_category=_forehead(shape.ratios, balance),
        hairline=payload.hairline.model_dump() if payload.hairline is not None else None,
        jawline=payload.jawline.model_dump(),
        anthropometric_ratios=shape.ratios,
        thirds=balance.thirds,
        fifths=balance.fifths,
        symmetry_score=symmetry.symmetry_score,
        asymmetry_index=symmetry.asymmetry_index,
        per_pair_deviations=list(symmetry.per_pair_deviations),
        vertical_balance_score=balance.vertical_balance_score,
        horizontal_balance_score=balance.horizontal_balance_score,
        balance_score=balance.balance_score,
        reliability=_reliability(payload.quality.confidence, payload.pose.pose_ok, notes),
        rationale=_rationale(shape.face_type, shape.face_type_confidence, symmetry, balance),
        processing_notes=notes,
    )


def _forehead(ratios: RatioFeatures, balance: BalanceResult) -> ForeheadCategory:
    width = None
    if ratios.fzi is not None:
        if ratios.fzi >= FZI_BROAD:
            width = "broad"
        elif ratios.fzi <= FZI_NARROW:
            width = "narrow"
        else:
            width = "average"
    height = None
    upper = balance.thirds.get("p1")
    if upper is not None:
        if upper >= 0.34:
            height = "high"
        elif upper <= 0.28:
            height = "low"
        else:
            height = "average"
    return ForeheadCategory(width=width, height=height)


def _reliability(quality: float, pose_ok: bool, notes: list[str]) -> float:
    value = quality
    if not pose_ok or "symmetry_pose_limited" in notes:
        value *= 0.8
    if "limited_upper_third" in notes:
        value *= 0.85
    if "missing_frontotemporale" in notes or "narrow_jaw_unresolved" in notes:
        value *= 0.85
    return max(0.0, min(1.0, value))


def _rationale(label, confidence, symmetry: SymmetryResult, balance: BalanceResult) -> str:
    parts = [f"everyday type {label}"]
    if confidence:
        parts.append(f"confidence {confidence[label]:.2f}")
    if symmetry.symmetry_score is not None:
        parts.append(f"symmetry {symmetry.symmetry_score:.2f}")
    if balance.balance_score is not None:
        parts.append(f"balance {balance.balance_score:.2f}")
    return "; ".join(parts)
