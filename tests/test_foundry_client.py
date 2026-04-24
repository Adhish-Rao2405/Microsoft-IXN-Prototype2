"""Phase 11 — Unit tests for FoundryLocalClient.

All HTTP is mocked. No live Foundry Local required.
22 tests covering: env var resolution, request format, response extraction,
and all typed exception cases.
"""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from src.planning.foundry_client import (
    FoundryClientError,
    FoundryConnectionError,
    FoundryEmptyResponseError,
    FoundryHTTPStatusError,
    FoundryLocalClient,
    FoundryMalformedResponseError,
    FoundryTimeoutError,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SYSTEM = "You are a robot arm controller."
_USER = "Pick the red cube."

_VALID_CONTENT = '{"actions": [{"action": "pick_target", "parameters": {}}]}'


def _ok_response(content: str = _VALID_CONTENT) -> MagicMock:
    """Return a mock HTTP response with status 200 and JSON body."""
    body = json.dumps(
        {"choices": [{"message": {"content": content}}]}
    ).encode("utf-8")
    resp = MagicMock()
    resp.status = 200
    resp.read.return_value = body
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def _make_client(**kwargs) -> FoundryLocalClient:
    return FoundryLocalClient(**kwargs)


# ---------------------------------------------------------------------------
# 1. Default base URL when no env var is set
# ---------------------------------------------------------------------------


def test_default_base_url_no_env(monkeypatch):
    monkeypatch.delenv("FOUNDRY_LOCAL_BASE_URL", raising=False)
    monkeypatch.delenv("FOUNDY_LOCAL_BASE_URL", raising=False)
    with patch("urllib.request.urlopen", return_value=_ok_response()) as mock_open:
        _make_client().complete(_SYSTEM, _USER)
    url_used = mock_open.call_args[0][0].full_url
    assert url_used.startswith("http://127.0.0.1:8000")


# ---------------------------------------------------------------------------
# 2. Uses FOUNDRY_LOCAL_BASE_URL when present
# ---------------------------------------------------------------------------


def test_env_var_foundry_local_base_url(monkeypatch):
    monkeypatch.setenv("FOUNDRY_LOCAL_BASE_URL", "http://localhost:9999")
    monkeypatch.delenv("FOUNDY_LOCAL_BASE_URL", raising=False)
    with patch("urllib.request.urlopen", return_value=_ok_response()) as mock_open:
        _make_client().complete(_SYSTEM, _USER)
    url_used = mock_open.call_args[0][0].full_url
    assert url_used.startswith("http://localhost:9999")


# ---------------------------------------------------------------------------
# 3. Uses FOUNDY_LOCAL_BASE_URL alias when preferred env var is absent
# ---------------------------------------------------------------------------


def test_env_var_alias_foundy_local_base_url(monkeypatch):
    monkeypatch.delenv("FOUNDRY_LOCAL_BASE_URL", raising=False)
    monkeypatch.setenv("FOUNDY_LOCAL_BASE_URL", "http://alias-host:7777")
    with patch("urllib.request.urlopen", return_value=_ok_response()) as mock_open:
        _make_client().complete(_SYSTEM, _USER)
    url_used = mock_open.call_args[0][0].full_url
    assert url_used.startswith("http://alias-host:7777")


# ---------------------------------------------------------------------------
# 4. Preferred env var overrides alias
# ---------------------------------------------------------------------------


def test_preferred_env_var_overrides_alias(monkeypatch):
    monkeypatch.setenv("FOUNDRY_LOCAL_BASE_URL", "http://preferred:1111")
    monkeypatch.setenv("FOUNDY_LOCAL_BASE_URL", "http://alias:2222")
    with patch("urllib.request.urlopen", return_value=_ok_response()) as mock_open:
        _make_client().complete(_SYSTEM, _USER)
    url_used = mock_open.call_args[0][0].full_url
    assert url_used.startswith("http://preferred:1111")


# ---------------------------------------------------------------------------
# 5. Uses FOUNDRY_LOCAL_MODEL when present
# ---------------------------------------------------------------------------


def test_env_var_foundry_local_model(monkeypatch):
    monkeypatch.setenv("FOUNDRY_LOCAL_MODEL", "my-custom-model")
    with patch("urllib.request.urlopen", return_value=_ok_response()) as mock_open:
        _make_client().complete(_SYSTEM, _USER)
    sent_body = json.loads(mock_open.call_args[0][0].data)
    assert sent_body["model"] == "my-custom-model"


# ---------------------------------------------------------------------------
# 6. Uses default model when FOUNDRY_LOCAL_MODEL is absent
# ---------------------------------------------------------------------------


def test_default_model_no_env(monkeypatch):
    monkeypatch.delenv("FOUNDRY_LOCAL_MODEL", raising=False)
    with patch("urllib.request.urlopen", return_value=_ok_response()) as mock_open:
        _make_client().complete(_SYSTEM, _USER)
    sent_body = json.loads(mock_open.call_args[0][0].data)
    assert sent_body["model"] == "local-model"


# ---------------------------------------------------------------------------
# 7. Sends request to /v1/chat/completions
# ---------------------------------------------------------------------------


def test_sends_to_chat_completions_endpoint(monkeypatch):
    monkeypatch.delenv("FOUNDRY_LOCAL_BASE_URL", raising=False)
    monkeypatch.delenv("FOUNDY_LOCAL_BASE_URL", raising=False)
    with patch("urllib.request.urlopen", return_value=_ok_response()) as mock_open:
        _make_client().complete(_SYSTEM, _USER)
    url_used = mock_open.call_args[0][0].full_url
    assert url_used.endswith("/v1/chat/completions")


# ---------------------------------------------------------------------------
# 8. Sends temperature: 0
# ---------------------------------------------------------------------------


def test_sends_temperature_zero(monkeypatch):
    monkeypatch.delenv("FOUNDRY_LOCAL_BASE_URL", raising=False)
    monkeypatch.delenv("FOUNDY_LOCAL_BASE_URL", raising=False)
    with patch("urllib.request.urlopen", return_value=_ok_response()) as mock_open:
        _make_client().complete(_SYSTEM, _USER)
    sent_body = json.loads(mock_open.call_args[0][0].data)
    assert sent_body["temperature"] == 0


# ---------------------------------------------------------------------------
# 9. Sends max_completion_tokens
# ---------------------------------------------------------------------------


def test_sends_max_completion_tokens(monkeypatch):
    monkeypatch.delenv("FOUNDRY_LOCAL_BASE_URL", raising=False)
    monkeypatch.delenv("FOUNDY_LOCAL_BASE_URL", raising=False)
    with patch("urllib.request.urlopen", return_value=_ok_response()) as mock_open:
        _make_client(max_completion_tokens=128).complete(_SYSTEM, _USER)
    sent_body = json.loads(mock_open.call_args[0][0].data)
    assert sent_body["max_completion_tokens"] == 128
    assert "max_tokens" not in sent_body


# ---------------------------------------------------------------------------
# 10. Sends system and user messages correctly
# ---------------------------------------------------------------------------


def test_sends_system_and_user_messages(monkeypatch):
    monkeypatch.delenv("FOUNDRY_LOCAL_BASE_URL", raising=False)
    monkeypatch.delenv("FOUNDY_LOCAL_BASE_URL", raising=False)
    with patch("urllib.request.urlopen", return_value=_ok_response()) as mock_open:
        _make_client().complete(_SYSTEM, _USER)
    sent_body = json.loads(mock_open.call_args[0][0].data)
    messages = sent_body["messages"]
    assert messages[0] == {"role": "system", "content": _SYSTEM}
    assert messages[1] == {"role": "user", "content": _USER}


# ---------------------------------------------------------------------------
# 11. Extracts assistant message content correctly
# ---------------------------------------------------------------------------


def test_extracts_assistant_content(monkeypatch):
    monkeypatch.delenv("FOUNDRY_LOCAL_BASE_URL", raising=False)
    monkeypatch.delenv("FOUNDY_LOCAL_BASE_URL", raising=False)
    expected = '{"actions": [{"action": "wait", "parameters": {}}]}'
    with patch("urllib.request.urlopen", return_value=_ok_response(expected)):
        result = _make_client().complete(_SYSTEM, _USER)
    assert result == expected


# ---------------------------------------------------------------------------
# 12. Raises FoundryTimeoutError on timeout
# ---------------------------------------------------------------------------


def test_raises_timeout_error(monkeypatch):
    monkeypatch.delenv("FOUNDRY_LOCAL_BASE_URL", raising=False)
    monkeypatch.delenv("FOUNDY_LOCAL_BASE_URL", raising=False)
    with patch(
        "urllib.request.urlopen",
        side_effect=urllib.error.URLError(TimeoutError("timed out")),
    ):
        with pytest.raises(FoundryTimeoutError):
            _make_client().complete(_SYSTEM, _USER)


# ---------------------------------------------------------------------------
# 13. Raises FoundryConnectionError on connection failure
# ---------------------------------------------------------------------------


def test_raises_connection_error(monkeypatch):
    monkeypatch.delenv("FOUNDRY_LOCAL_BASE_URL", raising=False)
    monkeypatch.delenv("FOUNDY_LOCAL_BASE_URL", raising=False)
    with patch(
        "urllib.request.urlopen",
        side_effect=urllib.error.URLError("Connection refused"),
    ):
        with pytest.raises(FoundryConnectionError):
            _make_client().complete(_SYSTEM, _USER)


# ---------------------------------------------------------------------------
# 14. Raises FoundryHTTPStatusError on HTTP 500
# ---------------------------------------------------------------------------


def test_raises_http_status_error_on_500(monkeypatch):
    monkeypatch.delenv("FOUNDRY_LOCAL_BASE_URL", raising=False)
    monkeypatch.delenv("FOUNDY_LOCAL_BASE_URL", raising=False)
    http_err = urllib.error.HTTPError(
        url="http://127.0.0.1:8000/v1/chat/completions",
        code=500,
        msg="Internal Server Error",
        hdrs=None,
        fp=None,
    )
    with patch("urllib.request.urlopen", side_effect=http_err):
        with pytest.raises(FoundryHTTPStatusError) as exc_info:
            _make_client().complete(_SYSTEM, _USER)
    assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# 15. Raises FoundryMalformedResponseError on invalid JSON
# ---------------------------------------------------------------------------


def test_raises_malformed_on_invalid_json(monkeypatch):
    monkeypatch.delenv("FOUNDRY_LOCAL_BASE_URL", raising=False)
    monkeypatch.delenv("FOUNDY_LOCAL_BASE_URL", raising=False)
    bad_resp = MagicMock()
    bad_resp.status = 200
    bad_resp.read.return_value = b"not-json!!!"
    bad_resp.__enter__ = lambda s: s
    bad_resp.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=bad_resp):
        with pytest.raises(FoundryMalformedResponseError):
            _make_client().complete(_SYSTEM, _USER)


# ---------------------------------------------------------------------------
# 16. Raises FoundryMalformedResponseError when choices is missing
# ---------------------------------------------------------------------------


def test_raises_malformed_when_choices_missing(monkeypatch):
    monkeypatch.delenv("FOUNDRY_LOCAL_BASE_URL", raising=False)
    monkeypatch.delenv("FOUNDY_LOCAL_BASE_URL", raising=False)
    body = json.dumps({"result": "ok"}).encode("utf-8")
    resp = MagicMock()
    resp.status = 200
    resp.read.return_value = body
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=resp):
        with pytest.raises(FoundryMalformedResponseError):
            _make_client().complete(_SYSTEM, _USER)


# ---------------------------------------------------------------------------
# 17. Raises FoundryMalformedResponseError when choices is empty
# ---------------------------------------------------------------------------


def test_raises_malformed_when_choices_empty(monkeypatch):
    monkeypatch.delenv("FOUNDRY_LOCAL_BASE_URL", raising=False)
    monkeypatch.delenv("FOUNDY_LOCAL_BASE_URL", raising=False)
    body = json.dumps({"choices": []}).encode("utf-8")
    resp = MagicMock()
    resp.status = 200
    resp.read.return_value = body
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=resp):
        with pytest.raises(FoundryMalformedResponseError):
            _make_client().complete(_SYSTEM, _USER)


# ---------------------------------------------------------------------------
# 18. Raises FoundryMalformedResponseError when message is missing
# ---------------------------------------------------------------------------


def test_raises_malformed_when_message_missing(monkeypatch):
    monkeypatch.delenv("FOUNDRY_LOCAL_BASE_URL", raising=False)
    monkeypatch.delenv("FOUNDY_LOCAL_BASE_URL", raising=False)
    body = json.dumps({"choices": [{"index": 0}]}).encode("utf-8")
    resp = MagicMock()
    resp.status = 200
    resp.read.return_value = body
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=resp):
        with pytest.raises(FoundryMalformedResponseError):
            _make_client().complete(_SYSTEM, _USER)


# ---------------------------------------------------------------------------
# 19. Raises FoundryMalformedResponseError when content is missing
# ---------------------------------------------------------------------------


def test_raises_malformed_when_content_missing(monkeypatch):
    monkeypatch.delenv("FOUNDRY_LOCAL_BASE_URL", raising=False)
    monkeypatch.delenv("FOUNDY_LOCAL_BASE_URL", raising=False)
    body = json.dumps({"choices": [{"message": {"role": "assistant"}}]}).encode("utf-8")
    resp = MagicMock()
    resp.status = 200
    resp.read.return_value = body
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=resp):
        with pytest.raises(FoundryMalformedResponseError):
            _make_client().complete(_SYSTEM, _USER)


# ---------------------------------------------------------------------------
# 20. Raises FoundryEmptyResponseError when content is empty
# ---------------------------------------------------------------------------


def test_raises_empty_when_content_is_empty_string(monkeypatch):
    monkeypatch.delenv("FOUNDRY_LOCAL_BASE_URL", raising=False)
    monkeypatch.delenv("FOUNDY_LOCAL_BASE_URL", raising=False)
    with patch("urllib.request.urlopen", return_value=_ok_response("")):
        with pytest.raises(FoundryEmptyResponseError):
            _make_client().complete(_SYSTEM, _USER)


# ---------------------------------------------------------------------------
# 21. Does not parse JSON action content
# ---------------------------------------------------------------------------


def test_does_not_parse_json_action_content(monkeypatch):
    """Client returns raw string; caller is responsible for parsing."""
    monkeypatch.delenv("FOUNDRY_LOCAL_BASE_URL", raising=False)
    monkeypatch.delenv("FOUNDY_LOCAL_BASE_URL", raising=False)
    raw = '{"actions": [{"action": "pick_target", "parameters": {"target": "cube"}}]}'
    with patch("urllib.request.urlopen", return_value=_ok_response(raw)):
        result = _make_client().complete(_SYSTEM, _USER)
    # Result must be a plain string, not a parsed dict
    assert isinstance(result, str)
    assert result == raw


# ---------------------------------------------------------------------------
# 22. Does not repair invalid JSON action content
# ---------------------------------------------------------------------------


def test_does_not_repair_invalid_json_action_content(monkeypatch):
    """Malformed action JSON passes through as-is (not repaired)."""
    monkeypatch.delenv("FOUNDRY_LOCAL_BASE_URL", raising=False)
    monkeypatch.delenv("FOUNDY_LOCAL_BASE_URL", raising=False)
    malformed_action = '{"actions": [BROKEN JSON HERE'
    with patch("urllib.request.urlopen", return_value=_ok_response(malformed_action)):
        result = _make_client().complete(_SYSTEM, _USER)
    # Raw string is returned as-is; no repair attempted
    assert result == malformed_action
