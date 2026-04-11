"""Tests that PII never reaches the LLM via the agent loop."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.models import UserProfile


_PII_FIELDS = {"name", "email", "phone", "id", "portfolio_url", "linkedin_url",
               "created_at", "preferred_currency", "work_history"}
_PROTECTED_FIELDS = {"gender", "sex", "age", "race", "ethnicity", "religion",
                     "nationality", "marital_status", "disability"}


@pytest.fixture(autouse=True)
def _isolate_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_privacy_agent.db"
    monkeypatch.setattr("config.settings.DB_PATH", db_path)
    monkeypatch.setattr("src.models.DB_PATH", db_path)
    monkeypatch.setattr("src.models_bootstrap.DB_PATH", db_path)
    monkeypatch.setattr("config.settings.DATABASE_URL", "")
    monkeypatch.setattr("config.settings.DATABASE_URL_FAILOVER", "")
    monkeypatch.setattr("src.models.DATABASE_URL", "")
    monkeypatch.setattr("src.models.DATABASE_URL_FAILOVER", "")
    monkeypatch.setattr("src.models_bootstrap.DATABASE_URL", "")
    monkeypatch.setattr("src.models_bootstrap.DATABASE_URL_FAILOVER", "")
    from src.models import reset_db_state
    reset_db_state()


def _make_profile(**overrides: object) -> UserProfile:
    defaults: dict[str, object] = {
        "name": "Alice Smith",
        "email": "alice@secret.com",
        "phone": "+1-555-867-5309",
        "location": "Berlin, Germany",
        "skills": ["Python", "FastAPI"],
        "desired_roles": ["Backend Engineer"],
    }
    defaults.update(overrides)
    return UserProfile(**defaults)  # type: ignore[arg-type]


def _mock_end_turn_response(text: str = "Done.") -> MagicMock:
    """Return a mock that looks like a Claude end_turn response."""
    from anthropic.types import TextBlock
    block = TextBlock(type="text", text=text)
    resp = MagicMock()
    resp.stop_reason = "end_turn"
    resp.content = [block]
    return resp


class TestPIINeverReachesLLM:
    @patch("src.agent.create_message_with_failover")
    @patch("src.agent.get_llm_client")
    def test_system_prompt_excludes_pii(self, mock_client: MagicMock, mock_create: MagicMock) -> None:
        mock_create.return_value = _mock_end_turn_response("Hello!")
        mock_client.return_value = MagicMock()

        from src.agent import JobAgent
        agent = JobAgent(profile=_make_profile())
        agent.chat("hello")

        call_kwargs = mock_create.call_args
        system_text: str = call_kwargs.kwargs.get("system", "") or call_kwargs[1].get("system", "")

        assert "alice@secret.com" not in system_text
        assert "Alice Smith" not in system_text
        assert "555-867-5309" not in system_text

        # Safe fields SHOULD be present
        assert "Python" in system_text
        assert "Berlin" in system_text

    @patch("src.agent.create_message_with_failover")
    @patch("src.agent.get_llm_client")
    def test_safe_profile_dict_strips_pii_and_protected(self, mock_client: MagicMock, mock_create: MagicMock) -> None:
        mock_create.return_value = _mock_end_turn_response()
        mock_client.return_value = MagicMock()

        from src.agent import JobAgent
        agent = JobAgent(profile=_make_profile())
        safe = agent._safe_profile_dict()

        for field in _PII_FIELDS:
            assert field not in safe, f"PII field '{field}' leaked into safe profile"
        for field in _PROTECTED_FIELDS:
            assert field not in safe, f"Protected field '{field}' leaked into safe profile"

        assert "skills" in safe
        assert "location" in safe
        assert "experience_level" in safe

    @patch("src.agent.create_message_with_failover")
    @patch("src.agent.get_llm_client")
    def test_messages_never_contain_raw_pii(self, mock_client: MagicMock, mock_create: MagicMock) -> None:
        mock_create.return_value = _mock_end_turn_response("I found jobs for you.")
        mock_client.return_value = MagicMock()

        from src.agent import JobAgent
        agent = JobAgent(profile=_make_profile())
        agent.chat("Find me Python jobs in Berlin")

        call_kwargs = mock_create.call_args
        messages = call_kwargs.kwargs.get("messages") or call_kwargs[1].get("messages", [])
        messages_str = str(messages)

        assert "alice@secret.com" not in messages_str
        assert "555-867-5309" not in messages_str
