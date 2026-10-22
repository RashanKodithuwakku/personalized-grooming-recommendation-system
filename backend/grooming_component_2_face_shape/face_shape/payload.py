"""Component 1 request body used by the scoring pipeline."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from face_shape.contracts import (
    REQUIRED_LANDMARKS,
    ClassificationInput,
    ImageSpec,
    JawTypeObservation,
    LandmarkPoint,
    parse_named_landmarks,
)


# One Component 1 landmark: an xy pair, visibility, and extractor confidence.
class C1Landmark(BaseModel):
    model_config = ConfigDict(extra="forbid")

    xy: list[float] | None = None
    visible: bool = True
    confidence: float = Field(ge=0.0, le=1.0)


# Image size and whether the incoming coordinates are pixels or 0-1.
class ImageBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    width: float = Field(gt=0)
    height: float = Field(gt=0)
    coordinate_mode: Literal["pixel", "normalized"]
    mirrored_corrected: bool | None = None


# Capture quality from Component 1. A rejected status stops scoring.
# neutral_expression decides whether the mouth pair keeps full weight.
class QualityBlock(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: str
    confidence: float = Field(ge=0.0, le=1.0)
    neutral_expression: bool = True


# Head pose in degrees. Yaw beyond five degrees flags the symmetry
# score as limited. pose_ok false marks the whole profile limited.
class PoseBlock(BaseModel):
    model_config = ConfigDict(extra="allow")

    yaw: float
    pitch: float
    roll: float
    units: str = "degrees"
    pose_ok: bool = True


# Jaw category already decided by Component 1, plus an optional contour.
class JawlineBlock(BaseModel):
    model_config = ConfigDict(extra="allow")

    jaw_type: Literal["angular", "rounded", "tapered"]
    confidence: float = Field(ge=0.0, le=1.0)
    contour: list[list[float]] | None = None


# Hairline observation passed through to the profile for the frontend.
# The engine itself uses the trichion landmark, not this block.
class HairlineBlock(BaseModel):
    model_config = ConfigDict(extra="allow")

    visible: bool = True
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    pattern: str | None = None
    polyline: list[list[float]] | None = None


# Full Component 1 JSON accepted by POST /v1/profile.
class Component1Payload(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_version: str = "1.0.0"
    request_id: str
    image: ImageBlock
    quality: QualityBlock
    pose: PoseBlock
    landmarks: dict[str, C1Landmark]
    jawline: JawlineBlock
    hairline: HairlineBlock | None = None
    source: dict[str, Any] | None = None
    captured_at: str | None = None
    processing_notes: list[str] = Field(default_factory=list)
    error: dict[str, Any] | None = None


# Convert the Component 1 JSON into the classifier input: landmarks,
# jaw observation, and image size. Missing core points raise here.
def to_classification_input(payload: Component1Payload) -> ClassificationInput:
    named: dict[str, object] = {}
    for name, landmark in payload.landmarks.items():
        named[name] = LandmarkPoint(
            xy=landmark.xy,
            visible=landmark.visible,
            confidence=landmark.confidence,
        )
    missing = [name for name in REQUIRED_LANDMARKS if name not in named]
    if missing:
        raise ValueError(f"missing core landmarks: {', '.join(missing)}")
    named["jaw_type"] = JawTypeObservation(
        label=payload.jawline.jaw_type,
        confidence=payload.jawline.confidence,
    )
    named["image"] = ImageSpec(
        width=payload.image.width,
        height=payload.image.height,
        coordinate_mode=payload.image.coordinate_mode,
    )
    return parse_named_landmarks(named)
