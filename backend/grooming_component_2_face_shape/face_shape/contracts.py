"""Input and output contracts for face shape classification.

Canonical landmark names follow the Component 1 contract (`zygion_l`, not
`zygion_left`). Older aliases are accepted at the parse boundary.
"""

from typing import Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


FaceShapeName = Literal["oval", "round", "square", "oblong", "heart", "diamond"]
JawTypeName = Literal["angular", "rounded", "tapered"]
AppliedModifier = Literal["tfi", "jaw_type"]
CoordinateMode = Literal["pixel", "normalized"]
MorphologicalClass = Literal[
    "Hypereuryprosopic",
    "Euryprosopic",
    "Mesoprosopic",
    "Leptoprosopic",
    "Hyperleptoprosopic",
]

FACE_SHAPES: tuple[FaceShapeName, ...] = (
    "oval",
    "round",
    "square",
    "oblong",
    "heart",
    "diamond",
)

REQUIRED_LANDMARKS: tuple[str, ...] = (
    "nasion",
    "menton",
    "zygion_l",
    "zygion_r",
    "gonion_l",
    "gonion_r",
)

CORE_LANDMARKS: tuple[str, ...] = REQUIRED_LANDMARKS + (
    "frontotemporale_l",
    "frontotemporale_r",
)

OPTIONAL_SHAPE_LANDMARKS: tuple[str, ...] = (
    "frontotemporale_l",
    "frontotemporale_r",
    "trichion",
)

ROLL_LANDMARKS: tuple[str, ...] = ("endocanthion_l", "endocanthion_r")

LANDMARK_ALIASES: dict[str, str] = {
    "zygion_left": "zygion_l",
    "zygion_right": "zygion_r",
    "gonion_left": "gonion_l",
    "gonion_right": "gonion_r",
    "frontotemporale_left": "frontotemporale_l",
    "frontotemporale_right": "frontotemporale_r",
    "endocanthion_left": "endocanthion_l",
    "endocanthion_right": "endocanthion_r",
    "exocanthion_left": "exocanthion_l",
    "exocanthion_right": "exocanthion_r",
    "alare_left": "alare_l",
    "alare_right": "alare_r",
    "cheilion_left": "cheilion_l",
    "cheilion_right": "cheilion_r",
}

# Optional A/B extractor map. Production payloads use names, not indices.
MEDIAPIPE_FACE_MESH_INDEX: dict[str, int] = {
    "nasion": 168,
    "menton": 152,
    "zygion_l": 234,
    "zygion_r": 454,
    "gonion_l": 172,
    "gonion_r": 397,
    "frontotemporale_l": 103,
    "frontotemporale_r": 332,
    "glabella": 9,
    "subnasale": 2,
    "endocanthion_l": 133,
    "endocanthion_r": 362,
    "exocanthion_l": 33,
    "exocanthion_r": 263,
    "alare_l": 129,
    "alare_r": 358,
    "cheilion_l": 61,
    "cheilion_r": 291,
}


class LandmarkPoint(BaseModel):
    """A single frontal-image landmark from Component 1."""

    model_config = ConfigDict(extra="forbid")

    x: float | None = None
    y: float | None = None
    z: float | None = None
    xy: list[float] | None = None
    visible: bool = True
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def resolve_coordinates(self) -> "LandmarkPoint":
        if self.xy is not None:
            if len(self.xy) != 2:
                raise ValueError("xy must contain exactly two values")
            if not all(_is_finite(value) for value in self.xy):
                raise ValueError("landmark coordinates must be finite")
            self.x = float(self.xy[0])
            self.y = float(self.xy[1])
        if not self.visible:
            return self
        if self.x is None or self.y is None:
            raise ValueError("visible landmark needs x and y")
        values = (self.x, self.y) if self.z is None else (self.x, self.y, self.z)
        if not all(_is_finite(value) for value in values):
            raise ValueError("landmark coordinates must be finite")
        return self


class ImageSpec(BaseModel):
    """Frame size required when coordinates are normalised."""

    model_config = ConfigDict(extra="forbid")

    width: float = Field(gt=0)
    height: float = Field(gt=0)
    coordinate_mode: CoordinateMode = "pixel"


class Tier1Landmarks(BaseModel):
    """Points required for MFI and JMI. Frontotemporale may be absent."""

    model_config = ConfigDict(extra="forbid")

    nasion: LandmarkPoint
    menton: LandmarkPoint
    zygion_l: LandmarkPoint
    zygion_r: LandmarkPoint
    gonion_l: LandmarkPoint
    gonion_r: LandmarkPoint
    frontotemporale_l: LandmarkPoint | None = None
    frontotemporale_r: LandmarkPoint | None = None


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
    image: ImageSpec | None = None
    extra: dict[str, LandmarkPoint] = Field(default_factory=dict)


class RatioFeatures(BaseModel):
    """Anthropometric ratios. Uncomputed values stay null."""

    model_config = ConfigDict(extra="forbid")

    mfi: float | None = None
    jmi: float | None = None
    fzi: float | None = None
    tfi: float | None = None


class FaceShapeResult(BaseModel):
    """Classifier output consumed by the recommendation component."""

    model_config = ConfigDict(extra="forbid")

    face_type: FaceShapeName
    face_type_confidence: dict[FaceShapeName, float]
    ratios: RatioFeatures
    modifiers_applied: list[AppliedModifier] = Field(default_factory=list)
    jaw_type: JawTypeObservation | None = None
    face_shape_class: MorphologicalClass | None = None
    baseline_label: FaceShapeName | None = None
    processing_notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def confidence_covers_every_class(self) -> "FaceShapeResult":
        missing = [name for name in FACE_SHAPES if name not in self.face_type_confidence]
        if missing:
            raise ValueError(f"confidence vector is missing: {', '.join(missing)}")
        if any(not _is_finite(value) or value < 0.0 for value in self.face_type_confidence.values()):
            raise ValueError("confidence values must be finite and non-negative")
        return self


def canonical_landmark_name(name: str) -> str:
    return LANDMARK_ALIASES.get(name, name)


def parse_named_landmarks(payload: Mapping[str, object]) -> ClassificationInput:
    """Build a classification input from a flat landmark map.

    Canonical names and Component 1 aliases are accepted. ``trichion`` and
    ``jaw_type`` are optional. Invisible frontotemporale points omit FZI.
    """

    named = _canonical_payload(payload)
    missing = [name for name in REQUIRED_LANDMARKS if name not in named]
    if missing:
        raise ValueError(f"missing core landmarks: {', '.join(missing)}")

    try:
        body_tier1 = {name: named[name] for name in REQUIRED_LANDMARKS}
        for name in ("frontotemporale_l", "frontotemporale_r"):
            if name in named:
                body_tier1[name] = named[name]
        tier1 = Tier1Landmarks.model_validate(body_tier1)
    except ValidationError as exc:
        raise ValueError(f"invalid core landmarks: {exc}") from exc

    extra = {
        name: point
        for name, point in named.items()
        if name not in REQUIRED_LANDMARKS
        and name not in OPTIONAL_SHAPE_LANDMARKS
        and name != "jaw_type"
    }
    tier2_payload: dict[str, object] = {}
    if "trichion" in named:
        tier2_payload["trichion"] = named["trichion"]

    body: dict[str, object] = {
        "tier1": tier1,
        "tier2": tier2_payload,
        "extra": extra,
    }
    if "jaw_type" in named:
        body["jaw_type"] = named["jaw_type"]
    if "image" in named:
        body["image"] = named["image"]

    try:
        return ClassificationInput.model_validate(body)
    except ValidationError as exc:
        raise ValueError(f"invalid optional fields: {exc}") from exc


def _canonical_payload(payload: Mapping[str, object]) -> dict[str, object]:
    named: dict[str, object] = {}
    for key, value in payload.items():
        if key in {"jaw_type", "image"}:
            named[key] = value
            continue
        name = canonical_landmark_name(str(key))
        if value is None:
            continue
        named[name] = value
    return named


def usable_point(point: LandmarkPoint | None) -> LandmarkPoint | None:
    if point is None or not point.visible or point.x is None or point.y is None:
        return None
    return point


def _is_finite(value: float) -> bool:
    return value == value and value not in (float("inf"), float("-inf"))
