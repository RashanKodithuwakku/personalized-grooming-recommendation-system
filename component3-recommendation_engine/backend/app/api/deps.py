"""FastAPI dependency providers."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request

from app.core.config import Settings, get_settings
from app.services.artifact_loader import ArtifactBundle
from app.services.recommendation_engine import RecommendationEngine


def get_app_settings() -> Settings:
    return get_settings()


def get_artifact_bundle(request: Request) -> ArtifactBundle:
    bundle = getattr(request.app.state, "artifacts", None)
    if bundle is None:
        raise HTTPException(status_code=503, detail="Artifacts not initialized")
    return bundle


def get_recommendation_engine(request: Request) -> RecommendationEngine:
    engine = getattr(request.app.state, "engine", None)
    if engine is None:
        raise HTTPException(status_code=503, detail="Recommendation engine not initialized")
    return engine


SettingsDep = Annotated[Settings, Depends(get_app_settings)]
ArtifactsDep = Annotated[ArtifactBundle, Depends(get_artifact_bundle)]
EngineDep = Annotated[RecommendationEngine, Depends(get_recommendation_engine)]
