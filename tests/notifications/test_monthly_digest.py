from datetime import date, datetime

import pytest
import time_machine
from django.conf import settings
from django.core import mail
from django.utils import timezone

from contacts.models import MenuReport
from notifications.models import MonthlyDigest
from notifications.tasks import send_monthly_admin_digest
from tests.contacts.factories import MenuReportFactory
from tests.notifications.factories import AnonymousMenuNotificationFactory
from tests.school_menu.factories import AuditLogFactory
from tests.users.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestSendMonthlyAdminDigest:
    def test_counts_previous_month_activity_and_sends_email(self):
        user = UserFactory()

        with time_machine.travel(datetime(2026, 8, 15, 10, 0), tick=False):
            AuditLogFactory.create_batch(2)
            MenuReportFactory.create_batch(2, receiver=user)
            MenuReportFactory(receiver=user, notification_error="boom")
            answered = MenuReportFactory(receiver=user)
            answered.feedback_sent_at = timezone.now()
            answered.save(update_fields=["feedback_sent_at"])
            AnonymousMenuNotificationFactory.create_batch(3)

        # Outside the reporting window (current month): must not be counted.
        with time_machine.travel(datetime(2026, 9, 5, 10, 0), tick=False):
            AuditLogFactory()
            MenuReportFactory(receiver=user)
            AnonymousMenuNotificationFactory()

        with time_machine.travel(datetime(2026, 9, 1, 6, 0), tick=False):
            send_monthly_admin_digest()

        digest = MonthlyDigest.objects.get()
        assert digest.period_start == date(2026, 8, 1)
        assert digest.period_end == date(2026, 8, 31)
        assert digest.new_schools == 2
        assert digest.menu_reports == 4
        assert digest.report_errors == 1
        assert digest.feedback_sent == 1
        assert digest.new_subscriptions == 3

        assert len(mail.outbox) == 1
        sent = mail.outbox[0]
        assert sent.to == [settings.ADMIN_EMAIL]
        assert "2" in sent.body
        assert "4" in sent.body

        html_body, mimetype = sent.alternatives[0]
        assert mimetype == "text/html"
        assert ">2<" in html_body
        assert ">4<" in html_body
        assert "#2e8401" in html_body

    def test_no_activity_still_sends_a_zeroed_digest(self):
        with time_machine.travel(datetime(2026, 9, 1, 6, 0), tick=False):
            send_monthly_admin_digest()

        digest = MonthlyDigest.objects.get()
        assert digest.new_schools == 0
        assert digest.menu_reports == 0
        assert digest.report_errors == 0
        assert digest.feedback_sent == 0
        assert digest.new_subscriptions == 0
        assert len(mail.outbox) == 1

    def test_does_not_count_reports_without_errors_as_errors(self):
        user = UserFactory()
        with time_machine.travel(datetime(2026, 8, 10, 10, 0), tick=False):
            MenuReportFactory(receiver=user)

        with time_machine.travel(datetime(2026, 9, 1, 6, 0), tick=False):
            send_monthly_admin_digest()

        digest = MonthlyDigest.objects.get()
        assert digest.menu_reports == 1
        assert digest.report_errors == 0
        assert MenuReport.objects.count() == 1
