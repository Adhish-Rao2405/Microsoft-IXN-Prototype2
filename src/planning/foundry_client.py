"""Phase 11 — Foundry Local HTTP client adapter.

Thin, strict HTTP adapter that calls an OpenAI-compatible Foundry Local
endpoint and returns raw assistant content only.

Responsibilities:
- Resolve base URL and model from environment variables or constructor.
- POST to /v1/chat/completions with system + user messages.
- Return raw string content of choices[0].message.content.
- Convert all network / response failures into typed exceptions.

Forbidden responsibilities (do NOT add):
- JSON action parsing
- Schema validation
- JSON repair
- Action execution
- Safety checks
- Retries
- Fallback logic
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


# ---------------------------------------------------------------------------
# Typed exceptions
# ---------------------------------------------------------------------------


class FoundryClientError(Exception):
    """Base class for all Foundry client errors."""


class FoundryConnectionError(FoundryClientError):
    """Raised when the HTTP connection to Foundry Local fails."""


class FoundryTimeoutError(FoundryClientError):
    """Raised when the request to Foundry Local times out."""


class FoundryHTTPStatusError(FoundryClientError):
    """Raised when Foundry Local returns a non-200 HTTP status code."""

    def __init__(self, status_code: int, message: str = "") -> None:
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}: {message}")


class FoundryMalformedResponseError(FoundryClientError):
    """Raised when the response body is missing expected fields."""


class FoundryEmptyResponseError(FoundryClientError):
    """Raised when the assistant content is present but empty."""


# ---------------------------------------------------------------------------
# Default constants
# ---------------------------------------------------------------------------

_DEFAULT_BASE_URL = "http://127.0.0.1:8000"
_DEFAULT_MODEL = "local-model"


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class FoundryLocalClient:
    """Strict HTTP adapter for an OpenAI-compatible Foundry Local endpoint.

    Environment variables (checked at instantiation if not passed explicitly):
        FOUNDRY_LOCAL_BASE_URL   – preferred base URL
        FOUNDY_LOCAL_BASE_URL    – alias (typo variant, lower priority)
        FOUNDRY_LOCAL_MODEL      – model identifier

    Args:
        base_url: Override base URL.  ``None`` → resolve from env / default.
        model: Override model name.  ``None`` → resolve from env / default.
        timeout_seconds: Per-request timeout in seconds.  Default 5.0.
        max_completion_tokens: Cap on generated tokens.  Default 256.
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float = 5.0,
        max_completion_tokens: int = 256,
    ) -> None:
        self._base_url = base_url or self._resolve_base_url()
        self._model = model or self._resolve_model()
        self._timeout = timeout_seconds
        self._max_completion_tokens = max_completion_tokens

    # ── configuration resolution ─────────────────────────────────────────

    @staticmethod
    def _resolve_base_url() -> str:
        """Return base URL from env vars in priority order, or default."""
        return (
            os.environ.get("FOUNDRY_LOCAL_BASE_URL")
            or os.environ.get("FOUNDY_LOCAL_BASE_URL")
            or _DEFAULT_BASE_URL
        )

    @staticmethod
    def _resolve_model() -> str:
        """Return model from env var, or default."""
        return os.environ.get("FOUNDRY_LOCAL_MODEL") or _DEFAULT_MODEL

    # ── public interface ─────────────────────────────────────────────────

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Send *system_prompt* and *user_prompt* to Foundry Local.

        Returns the raw assistant content string only.
        Does not parse, validate, repair, or execute the content.

        Raises:
            FoundryConnectionError: Network is unreachable.
            FoundryTimeoutError: Request exceeded ``timeout_seconds``.
            FoundryHTTPStatusError: Server returned a non-200 status.
            FoundryMalformedResponseError: Response body is structurally invalid.
            FoundryEmptyResponseError: Assistant content is empty.
        """
        payload = self._build_payload(system_prompt, user_prompt)
        raw_body = self._post(payload)
        return self._extract_content(raw_body)

    # ── request building ─────────────────────────────────────────────────

    def _build_payload(self, system_prompt: str, user_prompt: str) -> bytes:
        data: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0,
            "max_completion_tokens": self._max_completion_tokens,
        }
        return json.dumps(data).encode("utf-8")

    # ── HTTP transport ────────────────────────────────────────────────────

    def _post(self, payload: bytes) -> bytes:
        """POST *payload* to the /v1/chat/completions endpoint.

        Returns the raw response body bytes.
        Converts all urllib errors to typed exceptions.
        """
        url = f"{self._base_url}/v1/chat/completions"
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                if resp.status != 200:
                    raise FoundryHTTPStatusError(resp.status)
                return resp.read()
        except FoundryClientError:
            raise
        except urllib.error.HTTPError as exc:
            raise FoundryHTTPStatusError(exc.code, str(exc.reason)) from exc
        except TimeoutError as exc:
            raise FoundryTimeoutError(str(exc)) from exc
        except urllib.error.URLError as exc:
            reason = exc.reason
            if isinstance(reason, TimeoutError) or "timed out" in str(reason).lower():
                raise FoundryTimeoutError(str(reason)) from exc
            raise FoundryConnectionError(str(reason)) from exc
        except OSError as exc:
            raise FoundryConnectionError(str(exc)) from exc

    # ── response extraction ───────────────────────────────────────────────

    def _extract_content(self, body: bytes) -> str:
        """Parse *body* and return assistant content.

        Raises:
            FoundryMalformedResponseError: Any structural problem.
            FoundryEmptyResponseError: Content is present but empty.
        """
        try:
            data = json.loads(body)
        except (json.JSONDecodeError, ValueError) as exc:
            raise FoundryMalformedResponseError(
                f"response is not valid JSON: {exc}"
            ) from exc

        if not isinstance(data, dict) or "choices" not in data:
            raise FoundryMalformedResponseError("response missing 'choices' field")

        choices = data["choices"]
        if not isinstance(choices, list) or len(choices) == 0:
            raise FoundryMalformedResponseError("'choices' is empty or not a list")

        first = choices[0]
        if not isinstance(first, dict) or "message" not in first:
            raise FoundryMalformedResponseError(
                "choices[0] missing 'message' field"
            )

        message = first["message"]
        if not isinstance(message, dict) or "content" not in message:
            raise FoundryMalformedResponseError(
                "choices[0].message missing 'content' field"
            )

        content = message["content"]
        if not content:
            raise FoundryEmptyResponseError(
                "assistant content is empty"
            )

        return content
