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
    # Golden-path tests use the legacy X-Session-ID flow; force AUTH_ENABLED=false
    # so src.auth.get_current_user_id reads the X-Session-ID header rather than
    # requiring a Bearer token. See P0.7 fix and tests/test_auth_bearer.py for
    # the dedicated Bearer flow coverage.
    monkeypatch.setattr("config.settings.AUTH_ENABLED", False)
    monkeypatch.setattr("src.auth.AUTH_ENABLED", False)
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


class TestSaveJobRace:
    """P1: saving the same job twice (or in a race) must stay idempotent."""

    @patch("src.agent.JobAgent.__init__", return_value=None)
    def test_save_same_job_twice_is_idempotent(self, mock_init, client, session_id, monkeypatch):
        agent = _setup_agent(session_id, monkeypatch)
        agent._job_cache["race-job-1"] = {
            "job_title": "Staff Engineer",
            "employer_name": "Acme",
            "job_city": "Berlin",
            "job_description": "Important stuff.",
            "job_apply_link": "https://acme.example/apply/1",
            "_source": "test",
        }

        r1 = client.post(
            "/api/jobs/race-job-1/save",
            headers={"X-Session-ID": session_id},
        )
        assert r1.status_code == 200, r1.text
        assert r1.json()["saved"] is True

        # Second save must not 500 and must still report saved=True.
        r2 = client.post(
            "/api/jobs/race-job-1/save",
            headers={"X-Session-ID": session_id},
        )
        assert r2.status_code == 200, r2.text
        body2 = r2.json()
        assert body2["saved"] is True
        assert "already saved" in body2["message"].lower()

        # The saved-jobs list must still report exactly one row (the
        # unique (user_id, job_id) index prevents the duplicate insert).
        r3 = client.get(
            "/api/jobs/saved",
            headers={"X-Session-ID": session_id},
        )
        assert r3.status_code == 200
        data = r3.json()
        assert data["total"] == 1
        assert data["jobs"][0]["id"] == "race-job-1"

    @patch("src.agent.JobAgent.__init__", return_value=None)
    def test_save_job_integrity_error_returns_already_saved(
        self, mock_init, client, session_id, monkeypatch
    ):
        """Simulate a concurrent insert: force commit() to raise IntegrityError.

        The handler must catch it and respond with 200 "already saved"
        instead of bubbling a 500. This is the race-authoritative behaviour
        we rely on in place of the old check-then-insert pattern.
        """
        from sqlalchemy.exc import IntegrityError

        agent = _setup_agent(session_id, monkeypatch)
        agent._job_cache["race-job-2"] = {
            "job_title": "Senior SWE",
            "employer_name": "Beta",
            "job_city": "Remote",
            "job_description": "Important stuff.",
            "job_apply_link": "https://beta.example/apply/2",
            "_source": "test",
        }

        from src.models import init_db
        real_init_db = init_db
        call_count = {"n": 0}

        def _wrapped_init_db():
            db = real_init_db()
            real_commit = db.commit

            def _fake_commit():
                # Raise IntegrityError on the commit that tries to persist
                # the SavedJobORM row to simulate a concurrent winner.
                if call_count["n"] == 0:
                    call_count["n"] += 1
                    raise IntegrityError("UNIQUE constraint failed", None, Exception())
                return real_commit()

            db.commit = _fake_commit  # type: ignore[method-assign]
            return db

        monkeypatch.setattr("routers.jobs.init_db", _wrapped_init_db, raising=False)
        # Patch the name actually imported inside the handler (local import).
        import src.models as m
        monkeypatch.setattr(m, "init_db", _wrapped_init_db)

        r = client.post(
            "/api/jobs/race-job-2/save",
            headers={"X-Session-ID": session_id},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["saved"] is True
        assert "already saved" in body["message"].lower()


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
