"""Golden-path integration tests for all 7 routers."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _isolate_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_routers_golden.db"
    monkeypatch.setattr("config.settings.DB_PATH", db_path)
    monkeypatch.setattr("src.models.DB_PATH", db_path)
    monkeypatch.setattr("src.models_bootstrap.DB_PATH", db_path)
    monkeypatch.setattr("config.settings.DATABASE_URL", "")
    monkeypatch.setattr("config.settings.DATABASE_URL_FAILOVER", "")
    monkeypatch.setattr("src.models.DATABASE_URL", "")
    monkeypatch.setattr("src.models.DATABASE_URL_FAILOVER", "")
    monkeypatch.setattr("src.models_bootstrap.DATABASE_URL", "")
    monkeypatch.setattr("src.models_bootstrap.DATABASE_URL_FAILOVER", "")
    from src.models import reset_db_state, init_db
    reset_db_state()
    s = init_db()
    s.close()
    import api as api_mod
    monkeypatch.setattr(api_mod.limiter, "enabled", False)


@pytest.fixture
def client():
    from api import app
    return TestClient(app)


@pytest.fixture
def session_id(client):
    r = client.post("/api/session")
    assert r.status_code == 201
    return r.json()["session_id"]


def _setup_agent(session_id, monkeypatch):
    """Create a session with a mock agent that has all required attributes."""
    from unittest.mock import MagicMock
    from src.models import UserProfile

    profile = UserProfile(
        name="Test User",
        email="test@example.com",
        location="Berlin",
        skills=["Python", "FastAPI"],
        desired_roles=["Backend Engineer"],
    )

    with patch("src.agent.JobAgent.__init__", return_value=None):
        from api import app
        from fastapi.testclient import TestClient
        c = TestClient(app)
        c.post(
            "/api/profile",
            json={
                "name": "Test User",
                "email": "test@example.com",
                "location": "Berlin",
                "skills": ["Python", "FastAPI"],
                "desired_roles": ["Backend Engineer"],
            },
            headers={"X-Session-ID": session_id},
        )

    import src.session_store as ss
    agent = ss.get_sessions()[session_id]["agent"]
    agent.profile = profile

    mock_tracker = MagicMock()
    mock_tracker.compute_metrics.return_value = {
        "total": 5, "submitted": 3, "response_rate": 0.4,
        "interview_rate": 0.2, "offer_rate": 0.1,
    }
    mock_tracker.get_applications.return_value = []
    mock_tracker.get_application.return_value = None
    agent._tracker = mock_tracker
    agent._job_cache = {}
    agent._job_cache_max = 200
    agent._doc_gen = MagicMock()
    agent._search_engine = MagicMock()
    agent._market_svc = MagicMock()
    agent._career_dreamer = MagicMock()
    agent._client = MagicMock()
    agent._messages = []
    agent._max_history = 50

    return agent


class TestJobsRouter:
    @patch("src.agent.JobAgent.__init__", return_value=None)
    def test_search_jobs(self, mock_init, client, session_id, monkeypatch):
        _setup_agent(session_id, monkeypatch)
        # Mock the live search to return results (must be async)
        from routers import jobs as jobs_mod

        async def _fake_search(*a, **kw):  # type: ignore[no-untyped-def]
            return ("Found 2 jobs", ["j1", "j2"], {"j1": {}, "j2": {}})

        monkeypatch.setattr(jobs_mod, "search_jobs_live", _fake_search)
        r = client.post(
            "/api/jobs/search",
            json={"location_filter": "Berlin", "max_results": 5},
            headers={"X-Session-ID": session_id},
        )
        assert r.status_code == 200
        data = r.json()
        assert "response" in data
        assert "job_ids" in data


class TestChatRouter:
    @patch("src.agent.JobAgent.__init__", return_value=None)
    def test_chat_message(self, mock_init, client, session_id, monkeypatch):
        agent = _setup_agent(session_id, monkeypatch)
        agent.chat = MagicMock(return_value="Hello! How can I help?")
        r = client.post(
            "/api/chat",
            json={"message": "Hello"},
            headers={"X-Session-ID": session_id},
        )
        assert r.status_code == 200
        data = r.json()
        assert "response" in data
        assert data["response"] == "Hello! How can I help?"


class TestApplicationsRouter:
    @patch("src.agent.JobAgent.__init__", return_value=None)
    def test_track_application(self, mock_init, client, session_id, monkeypatch):
        agent = _setup_agent(session_id, monkeypatch)
        agent.chat = MagicMock(return_value="Application tracked successfully.")
        r = client.post(
            "/api/applications",
            json={"job_id": "test-job-1", "notes": "Applied via website"},
            headers={"X-Session-ID": session_id},
        )
        assert r.status_code == 201
        assert "response" in r.json()

    @patch("src.agent.JobAgent.__init__", return_value=None)
    def test_get_analytics(self, mock_init, client, session_id, monkeypatch):
        agent = _setup_agent(session_id, monkeypatch)
        agent.chat = MagicMock(return_value="Your success rate is 40%.")
        r = client.get(
            "/api/analytics",
            headers={"X-Session-ID": session_id},
        )
        assert r.status_code == 200
        assert "response" in r.json()


class TestDocumentsRouter:
    @patch("src.agent.JobAgent.__init__", return_value=None)
    def test_list_templates(self, mock_init, client, session_id, monkeypatch):
        _setup_agent(session_id, monkeypatch)
        r = client.get(
            "/api/documents/templates",
            headers={"X-Session-ID": session_id},
        )
        assert r.status_code == 200
        data = r.json()
        assert "templates" in data
        assert isinstance(data["templates"], list)


class TestDashboardRouter:
    @patch("src.agent.JobAgent.__init__", return_value=None)
    def test_dashboard_summary(self, mock_init, client, session_id, monkeypatch):
        _setup_agent(session_id, monkeypatch)
        r = client.get(
            "/api/dashboard/summary",
            headers={"X-Session-ID": session_id},
        )
        assert r.status_code == 200
        data = r.json()
        assert "total_applications" in data
        assert "response_rate" in data
        assert "by_status" in data

    @patch("src.agent.JobAgent.__init__", return_value=None)
    def test_dashboard_activity(self, mock_init, client, session_id, monkeypatch):
        _setup_agent(session_id, monkeypatch)
        r = client.get(
            "/api/dashboard/activity",
            headers={"X-Session-ID": session_id},
        )
        assert r.status_code == 200
        assert "activity" in r.json()


class TestKanbanRouter:
    @patch("src.agent.JobAgent.__init__", return_value=None)
    def test_kanban_board(self, mock_init, client, session_id, monkeypatch):
        _setup_agent(session_id, monkeypatch)
        r = client.get(
            "/api/kanban/board",
            headers={"X-Session-ID": session_id},
        )
        assert r.status_code == 200
        data = r.json()
        assert "columns" in data
        assert len(data["columns"]) == 7  # 7 ApplicationStatus values
        assert "total_cards" in data


class TestEmployerRouter:
    def test_employer_waitlist(self, client):
        r = client.post(
            "/api/employer/waitlist",
            json={"email": "hr@golden.com", "company_name": "Golden Corp"},
        )
        assert r.status_code == 201
        data = r.json()
        assert "message" in data
        assert data["position"] >= 1
