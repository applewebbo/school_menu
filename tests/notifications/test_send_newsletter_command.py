from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from notifications.models import Newsletter
from tests.notifications.factories import NewsletterFactory

pytestmark = pytest.mark.django_db


class TestSendNewsletterCommand:
    def test_missing_newsletter_raises(self):
        with pytest.raises(CommandError):
            call_command("send_newsletter", "999999")

    @patch("notifications.management.commands.send_newsletter.async_task")
    def test_dispatches_async_task_and_marks_sending(self, mock_async_task):
        newsletter = NewsletterFactory(status=Newsletter.Status.DRAFT)

        call_command("send_newsletter", str(newsletter.pk))

        mock_async_task.assert_called_once_with(
            "notifications.tasks.send_newsletter", newsletter.pk
        )
        newsletter.refresh_from_db()
        assert newsletter.status == Newsletter.Status.SENDING

    @patch("notifications.management.commands.send_newsletter.async_task")
    def test_already_sent_raises(self, mock_async_task):
        newsletter = NewsletterFactory(status=Newsletter.Status.SENT)

        with pytest.raises(CommandError):
            call_command("send_newsletter", str(newsletter.pk))

        mock_async_task.assert_not_called()

    def test_test_flag_sends_a_single_preview_without_touching_state(self, mailoutbox):
        newsletter = NewsletterFactory(
            subject="Anteprima", body_html="<p>Ciao</p>", status=Newsletter.Status.DRAFT
        )

        out = StringIO()
        call_command(
            "send_newsletter",
            str(newsletter.pk),
            "--test=preview@test.com",
            stdout=out,
        )

        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == ["preview@test.com"]
        assert mailoutbox[0].subject == "Anteprima"

        newsletter.refresh_from_db()
        assert newsletter.status == Newsletter.Status.DRAFT
        assert newsletter.recipients_count == 0
        assert newsletter.sent_at is None
        assert "preview@test.com" in out.getvalue()

    def test_test_flag_uses_a_placeholder_unsubscribe_link(self, mailoutbox):
        newsletter = NewsletterFactory(body_html="<p>Ciao</p>")

        call_command("send_newsletter", str(newsletter.pk), "--test=preview@test.com")

        html_body = mailoutbox[0].alternatives[0][0]
        assert "anteprima" in html_body

    def test_test_flag_works_even_when_already_sent(self, mailoutbox):
        """A test preview must stay usable to re-check content after the real send."""
        newsletter = NewsletterFactory(status=Newsletter.Status.SENT)

        call_command("send_newsletter", str(newsletter.pk), "--test=preview@test.com")

        assert len(mailoutbox) == 1
