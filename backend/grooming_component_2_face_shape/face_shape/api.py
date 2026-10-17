"""HTTP mapping from Component 1 landmarks to a face-shape result.

The response carries the identified class, its confidence vector, the ratio
features, and any hairline or jawline payload supplied by Component 1.
Symmetry and balance are outside this endpoint.
"""

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from face_shape.contracts import (
    AppliedModifier,
    FaceShapeName,
    JawTypeObservation,
    LandmarkPoint,
    RatioFeatures,
    parse_named_landmarks,
)
from face_shape.indices import DegenerateMeasurement
from face_shape.tier2 import classify_face


class FaceShapeRequest(BaseModel):
    """Named landmarks already extracted by Component 1."""

    model_config = ConfigDict(extra="forbid")

    landmarks: dict[str, LandmarkPoint]
    jaw_type: JawTypeObservation | None = None
    hairline: dict[str, Any] | None = None
    jawline: dict[str, Any] | None = None


class FaceShapeResponse(BaseModel):
    """Identification result for the recommendation component."""

    model_config = ConfigDict(extra="forbid")

    face_type: FaceShapeName
    face_type_confidence: dict[FaceShapeName, float]
    ratios: RatioFeatures
    modifiers_applied: list[AppliedModifier] = Field(default_factory=list)
    jaw_type: JawTypeObservation | None = None
    hairline: dict[str, Any] | None = None
    jawline: dict[str, Any] | None = None


def create_app() -> FastAPI:
    app = FastAPI(title="Face shape classification")

    @app.post("/api/component-2/face-shape", response_model=FaceShapeResponse)
    def identify_face(body: FaceShapeRequest) -> FaceShapeResponse:
        payload: dict[str, object] = {
            name: point.model_dump() for name, point in body.landmarks.items()
        }
        if body.jaw_type is not None:
            payload["jaw_type"] = body.jaw_type.model_dump()
        try:
            sample = parse_named_landmarks(payload)
            result = classify_face(sample)
        except (ValueError, DegenerateMeasurement) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return FaceShapeResponse(
            face_type=result.face_type,
            face_type_confidence=result.face_type_confidence,
            ratios=result.ratios,
            modifiers_applied=result.modifiers_applied,
            jaw_type=result.jaw_type,
            hairline=body.hairline,
            jawline=body.jawline,
        )

    return app


app = create_app()
