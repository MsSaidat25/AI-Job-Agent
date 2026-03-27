"""Tests for src/llm_client.py -- client caching and failover logic."""
from unittest.mock import MagicMock, patch

import anthropic
import pytest

from src.llm_client import (
    _is_retryable,
    create_message_with_failover,
    get_llm_client,
)


@pytest.fixture(autouse=True)
def _reset_cached_clients():
    import src.llm_client as llm_client

    llm_client._primary_client = None
    llm_client._vertex_client = None
    yield
    llm_client._primary_client = None
    llm_client._vertex_client = None


class TestGetLlmClient:
    @patch("src.llm_client.LLM_API_KEY", "test-api-key")
    @patch("src.llm_client.USE_VERTEX_PRIMARY", False)
    def test_returns_anthropic_instance(self):
        client = get_llm_client()
        assert isinstance(client, anthropic.Anthropic)

    @patch("src.llm_client.USE_VERTEX_PRIMARY", False)
    def test_returns_same_instance(self):
        """Client should be cached (singleton)."""
        a = get_llm_client()
        b = get_llm_client()
        assert a is b

    @patch("src.llm_client.USE_VERTEX_PRIMARY", True)
    @patch("src.llm_client._get_vertex_client")
    def test_uses_vertex_when_primary_enabled(self, mock_get_vertex):
        vertex_client = MagicMock()
        mock_get_vertex.return_value = vertex_client

        client = get_llm_client()
        assert client is vertex_client
        mock_get_vertex.assert_called_once()


class TestIsRetryable:
    def test_timeout_is_retryable(self):
        exc = anthropic.APITimeoutError(request=MagicMock())
        assert _is_retryable(exc) is True

    def test_rate_limit_is_retryable(self):
        resp = MagicMock()
        resp.status_code = 429
        exc = anthropic.RateLimitError(
            message="rate limited", response=resp, body=None
        )
        assert _is_retryable(exc) is True

    def test_server_error_is_retryable(self):
        resp = MagicMock()
        resp.status_code = 500
        exc = anthropic.APIStatusError(
            message="server error", response=resp, body=None
        )
        assert _is_retryable(exc) is True

    def test_client_error_not_retryable(self):
        resp = MagicMock()
        resp.status_code = 400
        exc = anthropic.APIStatusError(
            message="bad request", response=resp, body=None
        )
        assert _is_retryable(exc) is False

    def test_generic_error_not_retryable(self):
        assert _is_retryable(ValueError("oops")) is False


class TestCreateMessageWithFailover:
    def test_success_returns_response(self):
        client = MagicMock()
        client.messages.create.return_value = "response"
        result = create_message_with_failover(client, model="m", max_tokens=10, messages=[])
        assert result == "response"

    def test_non_retryable_error_raises(self):
        client = MagicMock()
        client.messages.create.side_effect = ValueError("bad")
        with pytest.raises(ValueError):
            create_message_with_failover(client, model="m", max_tokens=10, messages=[])

    @patch("src.llm_client.USE_VERTEX_FAILOVER", True)
    @patch("src.llm_client.USE_VERTEX_PRIMARY", False)
    @patch("src.llm_client.VERTEX_PROJECT", "my-project")
    @patch("src.llm_client._get_vertex_client")
    def test_failover_on_timeout(self, mock_vertex):
        client = MagicMock()
        client.messages.create.side_effect = anthropic.APITimeoutError(
            request=MagicMock()
        )
        vertex_client = MagicMock()
        vertex_client.messages.create.return_value = "vertex_response"
        mock_vertex.return_value = vertex_client

        result = create_message_with_failover(
            client, model="m", max_tokens=10, messages=[]
        )
        assert result == "vertex_response"
        vertex_client.messages.create.assert_called_once()

    @patch("src.llm_client.USE_VERTEX_FAILOVER", False)
    @patch("src.llm_client.USE_VERTEX_PRIMARY", False)
    def test_no_failover_when_disabled(self):
        client = MagicMock()
        client.messages.create.side_effect = anthropic.APITimeoutError(
            request=MagicMock()
        )
        with pytest.raises(anthropic.APITimeoutError):
            create_message_with_failover(
                client, model="m", max_tokens=10, messages=[]
            )
