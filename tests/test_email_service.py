"""Tests for src/email_service.py -- email sending and template rendering."""
from unittest.mock import MagicMock, patch

from src.email_service import send_application_update, send_email, send_interview_reminder


class TestSendEmail:
    @patch("src.email_service.RESEND_API_KEY", "")
    def test_skips_when_no_api_key(self):
        """Should silently return None when RESEND_API_KEY is not set."""
        result = send_email(to="user@test.com", subject="Hi", html="<p>Hi</p>")
        assert result is None

    @patch("src.email_service.RESEND_API_KEY", "re_test_key")
    @patch("src.email_service._get_resend")
    def test_sends_email_successfully(self, mock_resend):
        mock_mod = MagicMock()
        mock_mod.Emails.send.return_value = {"id": "email-123"}
        mock_resend.return_value = mock_mod

        result = send_email(to="user@test.com", subject="Test", html="<p>Hi</p>")
        assert result == {"id": "email-123"}
        mock_mod.Emails.send.assert_called_once()
        call_args = mock_mod.Emails.send.call_args[0][0]
        assert call_args["to"] == ["user@test.com"]
        assert call_args["subject"] == "Test"

    @patch("src.email_service.RESEND_API_KEY", "re_test_key")
    @patch("src.email_service._get_resend")
    def test_handles_send_failure(self, mock_resend):
        mock_mod = MagicMock()
        mock_mod.Emails.send.side_effect = Exception("API error")
        mock_resend.return_value = mock_mod

        result = send_email(to="user@test.com", subject="Test", html="<p>Hi</p>")
        assert result is None


class TestSendApplicationUpdate:
    @patch("src.email_service.send_email")
    def test_uses_plain_text_subject(self, mock_send):
        """Subject should use raw text, not HTML-escaped text."""
        mock_send.return_value = {"id": "1"}
        send_application_update(
            to="u@test.com",
            job_title="Sr. Engineer & Lead",
            company="A&B Corp",
            new_status="interview_scheduled",
        )
        call_args = mock_send.call_args
        subject = call_args.kwargs.get("subject") or call_args[1].get("subject")
        # Subject should NOT contain &amp; (HTML entity)
        assert "&amp;" not in subject
        assert "Sr. Engineer & Lead" in subject

    @patch("src.email_service.send_email")
    def test_html_body_escapes_entities(self, mock_send):
        """HTML body should escape special characters."""
        mock_send.return_value = {"id": "1"}
        send_application_update(
            to="u@test.com",
            job_title="<script>alert('xss')</script>",
            company="Evil Corp",
            new_status="submitted",
        )
        call_args = mock_send.call_args
        html = call_args.kwargs.get("html") or call_args[1].get("html")
        assert "<script>" not in html
        assert "&lt;script&gt;" in html


class TestSendInterviewReminder:
    @patch("src.email_service.send_email")
    def test_uses_plain_text_subject(self, mock_send):
        mock_send.return_value = {"id": "1"}
        send_interview_reminder(
            to="u@test.com",
            job_title="Data & Analytics Lead",
            company="D&A Inc",
            interview_date="2026-04-01",
        )
        call_args = mock_send.call_args
        subject = call_args.kwargs.get("subject") or call_args[1].get("subject")
        assert "&amp;" not in subject
        assert "Data & Analytics Lead" in subject
