"""FastAPI application entrypoint for Component 3."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import RequestIdFilter, get_logger, setup_logging
from app.services.artifact_loader import ArtifactLoader
from app.services.recommendation_engine import RecommendationEngine

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    setup_logging(settings.log_level)
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)

    loader = ArtifactLoader(settings)
    bundle = loader.load()
    app.state.settings = settings
    app.state.artifacts = bundle
    app.state.engine = RecommendationEngine(bundle, settings)

    if bundle.ready:
        logger.info(
            "Recommendation readiness=ready artifact_version=%s",
            bundle.artifact_version,
        )
    else:
        logger.error(
            "Recommendation readiness=not_ready diagnostics=%s",
            "; ".join(bundle.diagnostics),
        )
    yield
    logger.info("Shutting down application")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Component 3: Style Recommendation and Ranking Engine. "
            "Accepts structured facial attributes (JSON), ranks catalogue styles "
            "with CatBoost rankers, scores compatibility with a shared regressor, "
            "and returns hybrid-ordered recommendations with transparent explanations. "
            "Swagger UI is available at /docs."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=settings.cors_origin_regex,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    @app.middleware("http")
    async def attach_request_id(request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get("X-Request-ID") or "-"
        # Ensure log records in this request can carry the id when provided.
        for handler in logging_root_handlers():
            handler.addFilter(RequestIdFilter(request_id if request_id != "-" else "-"))
        response = await call_next(request)
        if request_id and request_id != "-":
            response.headers["X-Request-ID"] = request_id
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Do not echo full facial profiles in error logs.
        logger.warning(
            "validation_error path=%s error_count=%s",
            request.url.path,
            len(exc.errors()),
        )
        return JSONResponse(
            status_code=422,
            content={"detail": _serialize_validation_errors(exc.errors())},
        )

    app.include_router(router)
    return app


def logging_root_handlers():
    import logging

    return logging.getLogger().handlers


def _serialize_validation_errors(errors: list) -> list[dict]:
    """Make Pydantic error payloads JSON-safe (ctx may contain Exception objects)."""
    safe: list[dict] = []
    for error in errors:
        item = {
            "type": error.get("type"),
            "loc": list(error.get("loc", [])),
            "msg": error.get("msg"),
            "input": _safe_json_value(error.get("input")),
        }
        ctx = error.get("ctx")
        if isinstance(ctx, dict):
            item["ctx"] = {key: _safe_json_value(value) for key, value in ctx.items()}
        safe.append(item)
    return safe


def _safe_json_value(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [_safe_json_value(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _safe_json_value(v) for k, v in value.items()}
    return str(value)


app = create_app()
