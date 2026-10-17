"""Input and output contracts for face shape classification.

Coordinates may be pixels or normalised image units. Later ratio features
cancel uniform scale, so this module does not convert units.
"""

from typing import Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


FaceShapeName = Literal["oval", "round", "square", "oblong", "heart", "diamond"]
JawTypeName = Literal["angular", "rounded", "tapered"]
AppliedModifier = Literal["tfi", "jaw_type"]

FACE_SHAPES: tuple[FaceShapeName, ...] = (
    "oval",
    "round",
    "square",
    "oblong",
    "heart",
    "diamond",
)

CORE_LANDMARKS: tuple[str, ...] = (
    "nasion",
    "menton",
    "zygion_left",
    "zygion_right",
    "gonion_left",
    "gonion_right",
    "frontotemporale_left",
    "frontotemporale_right",
)

# MediaPipe Face Mesh indices chosen as proxies for the eight core points.
# Trichion is produced by the hairline model and has no Face Mesh index.
MEDIAPIPE_FACE_MESH_INDEX: dict[str, int] = {
    "nasion": 168,
    "menton": 152,
    "zygion_left": 234,
    "zygion_right": 454,
    "gonion_left": 172,
    "gonion_right": 397,
    "frontotemporale_left": 103,
    "frontotemporale_right": 332,
}


class LandmarkPoint(BaseModel):
    """A single frontal-image landmark."""

    model_config = ConfigDict(extra="forbid")

    x: float
    y: float
    z: float | None = None

    @model_validator(mode="after")
    def coordinates_are_finite(self) -> "LandmarkPoint":
        values = (self.x, self.y) if self.z is None else (self.x, self.y, self.z)
        if not all(map(_is_finite, values)):
            raise ValueError("landmark coordinates must be finite")
        return self


class Tier1Landmarks(BaseModel):
    """Eight points required for MFI, JMI, and FZI."""

    model_config = ConfigDict(extra="forbid")

    nasion: LandmarkPoint
    menton: LandmarkPoint
    zygion_left: LandmarkPoint
    zygion_right: LandmarkPoint
    gonion_left: LandmarkPoint
    gonion_right: LandmarkPoint
    frontotemporale_left: LandmarkPoint
    frontotemporale_right: LandmarkPoint


class Tier2Landmarks(BaseModel):
    """Optional total-face-height point. Absence leaves TFI unused."""

    model_config = ConfigDict(extra="forbid")

    trichion: LandmarkPoint | None = None


class JawTypeObservation(BaseModel):
    """Jaw-type observation supplied by the landmark component."""

    model_config = ConfigDict(extra="forbid")

    label: JawTypeName
    confidence: float = Field(ge=0.0, le=1.0)


class ClassificationInput(BaseModel):
    """Typed request accepted by the face shape classifier."""

    model_config = ConfigDict(extra="forbid")

    tier1: Tier1Landmarks
    tier2: Tier2Landmarks = Field(default_factory=Tier2Landmarks)
    jaw_type: JawTypeObservation | None = None


class RatioFeatures(BaseModel):
    """Anthropometric ratios. Uncomputed values stay null."""

    model_config = ConfigDict(extra="forbid")

    mfi: float | None = None
    jmi: float | None = None
    fzi: float | None = None
    tfi: float | None = None


class FaceShapeResult(BaseModel):
    """Classifier output consumed by the recommendation component.

    Symmetry and balance scores are intentionally absent.
    """

    model_config = ConfigDict(extra="forbid")

    face_type: FaceShapeName
    face_type_confidence: dict[FaceShapeName, float]
    ratios: RatioFeatures
    modifiers_applied: list[AppliedModifier] = Field(default_factory=list)
    jaw_type: JawTypeObservation | None = None

    @model_validator(mode="after")
    def confidence_covers_every_class(self) -> "FaceShapeResult":
        missing = [name for name in FACE_SHAPES if name not in self.face_type_confidence]
        if missing:
            raise ValueError(f"confidence vector is missing: {', '.join(missing)}")
        if any(not _is_finite(value) or value < 0.0 for value in self.face_type_confidence.values()):
            raise ValueError("confidence values must be finite and non-negative")
        return self


def parse_named_landmarks(payload: Mapping[str, object]) -> ClassificationInput:
    """Build a classification input from a flat landmark map.

    Core names are required. ``trichion`` and ``jaw_type`` are optional.
    """

    missing = [name for name in CORE_LANDMARKS if name not in payload]
    if missing:
        raise ValueError(f"missing core landmarks: {', '.join(missing)}")

    try:
        tier1 = Tier1Landmarks.model_validate({name: payload[name] for name in CORE_LANDMARKS})
    except ValidationError as exc:
        raise ValueError(f"invalid core landmarks: {exc}") from exc

    tier2_payload: dict[str, object] = {}
    if "trichion" in payload and payload["trichion"] is not None:
        tier2_payload["trichion"] = payload["trichion"]

    body: dict[str, object] = {
        "tier1": tier1,
        "tier2": tier2_payload,
    }
    if "jaw_type" in payload and payload["jaw_type"] is not None:
        body["jaw_type"] = payload["jaw_type"]

    try:
        return ClassificationInput.model_validate(body)
    except ValidationError as exc:
        raise ValueError(f"invalid optional fields: {exc}") from exc


def _is_finite(value: float) -> bool:
    return value == value and value not in (float("inf"), float("-inf"))
