"""Phase 6 orchestration-layer errors."""

from __future__ import annotations


class PipelineError(Exception):
    """Raised for orchestration-layer misuse or malformed component output."""


class PipelineExecutionError(PipelineError):
    """Raised when execution fails after full validation."""