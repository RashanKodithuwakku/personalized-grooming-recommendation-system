"""Application-specific exceptions."""

from __future__ import annotations


class ArtifactError(Exception):
    """Raised when required model or dataset artifacts are missing or invalid."""

    def __init__(self, message: str, diagnostics: list[str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.diagnostics = diagnostics or []


class RecommendationNotReadyError(Exception):
    """Raised when recommendation inference cannot run safely."""

    def __init__(self, message: str, diagnostics: list[str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.diagnostics = diagnostics or []


class ValidationContractError(Exception):
    """Raised for domain validation failures beyond Pydantic field checks."""

    def __init__(self, message: str, errors: list[str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.errors = errors or []
