from unittest.mock import patch

from django.contrib.messages import get_messages
from django.core.cache import cache
from django.test import override_settings
from pytest_django.asserts import assertTemplateUsed

from contacts.models import MenuReport
from school_menu.test import TestCase
from tests.contacts.factories import MenuReportFactory
from tests.school_menu.factories import SchoolFactory

# The test settings use DummyCache, which never stores anything, so a real backend is
# needed to exercise the rate limit at all (#292).
LOCMEM_CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
}


class ContactView(TestCase):
    def setup_method(self, method):
        cache.clear()

    def test_get(self):
        response = self.get("contacts:contact")

        self.response_200(response)
        assertTemplateUsed(response, "contacts/contact.html")

    def test_send_message(self):
        data = {
            "name": "Test Name",
            "email": "test@test.com",
            "message": "Vel rerum voluptatem aut accusantium ducimus ut optio eligendi sed minus maxime",
        }

        response = self.post("contacts:contact", data=data)
        self.response_302(response)

    def test_invalid_data(self):
        data = {}

        response = self.post("contacts:contact", data=data)

        assert "form" in response.context

    def test_honeypot_filled_is_rejected(self):
        data = {
            "name": "Test Name",
            "email": "test@test.com",
            "message": "Test Message",
            "website": "https://spam.example",
        }

        response = self.post("contacts:contact", data=data)

        self.response_200(response)
        form = response.context["form"]
        assert "Invio non disponibile al momento." in form.errors["website"]

    @override_settings(CACHES=LOCMEM_CACHES, CONTACT_RATE_LIMIT_MAX=2)
    def test_too_many_submissions_are_rate_limited(self):
        data = {
            "name": "Test Name",
            "email": "test@test.com",
            "message": "Test Message",
        }

        for _ in range(2):
            self.post("contacts:contact", data=data)
        response = self.post("contacts:contact", data=data)

        self.response_200(response)
        # [-1]: the two earlier POSTs redirected (302) without being followed, so their
        # own success messages are still queued unread ahead of this one.
        message = list(get_messages(response.wsgi_request))[-1].message
        assert message == "Troppe richieste da questo indirizzo. Riprova più tardi."

    @override_settings(CACHES=LOCMEM_CACHES, CONTACT_RATE_LIMIT_MAX=2)
    def test_rate_limit_is_scoped_per_ip(self):
        data = {
            "name": "Test Name",
            "email": "test@test.com",
            "message": "Test Message",
        }

        for _ in range(2):
            self.post("contacts:contact", data=data, extra={"REMOTE_ADDR": "10.0.0.1"})
        response = self.post(
            "contacts:contact", data=data, extra={"REMOTE_ADDR": "10.0.0.2"}
        )

        self.response_302(response)


class MenuReportView(TestCase):
    def setup_method(self, method):
        cache.clear()

    def test_get(self):
        user = self.make_user()
        school = SchoolFactory(user=user)

        response = self.get("contacts:menu_report", school_id=school.pk)

        self.response_200(response)
        assert response.context["school"] == school

    def test_post_with_success(self):
        user = self.make_user()
        school = SchoolFactory(user=user)
        data = {
            "name": "Test name",
            "message": "Test message ",
            "get_notified": True,
            "email": "user@test.com",
        }

        response = self.post("contacts:menu_report", school_id=school.pk, data=data)

        self.response_302(response)

    def test_post_with_get_notified_false(self):
        user = self.make_user()
        school = SchoolFactory(user=user)
        data = {
            "name": "Test name",
            "message": "Test message ",
            "get_notified": False,
            "email": "",
        }

        response = self.post("contacts:menu_report", school_id=school.pk, data=data)

        self.response_302(response)

    def test_post_records_notification_error_when_send_fails(self):
        # The report itself is the primary action and must survive a mail-provider
        # blip: the courtesy email to the receiver failing shouldn't lose the report
        # or break the response, only be recorded for the digest (#280).
        user = self.make_user()
        school = SchoolFactory(user=user)
        data = {
            "name": "Test name",
            "message": "Test message",
            "get_notified": False,
            "email": "",
        }

        with patch("contacts.views.send_mail", side_effect=Exception("boom")):
            response = self.post("contacts:menu_report", school_id=school.pk, data=data)

        self.response_302(response)
        report = MenuReport.objects.get()
        assert report.notification_error == "boom"

    def test_post_with_success_has_no_notification_error(self):
        user = self.make_user()
        school = SchoolFactory(user=user)
        data = {
            "name": "Test name",
            "message": "Test message",
            "get_notified": False,
            "email": "",
        }

        self.post("contacts:menu_report", school_id=school.pk, data=data)

        report = MenuReport.objects.get()
        assert report.notification_error == ""

    def test_honeypot_filled_is_rejected(self):
        user = self.make_user()
        school = SchoolFactory(user=user)
        data = {
            "name": "Test name",
            "message": "Test message",
            "get_notified": False,
            "email": "",
            "website": "https://spam.example",
        }

        response = self.post("contacts:menu_report", school_id=school.pk, data=data)

        self.response_200(response)
        form = response.context["form"]
        assert "Invio non disponibile al momento." in form.errors["website"]
        assert MenuReport.objects.count() == 0

    @override_settings(CACHES=LOCMEM_CACHES, CONTACT_RATE_LIMIT_MAX=2)
    def test_too_many_submissions_are_rate_limited(self):
        user = self.make_user()
        school = SchoolFactory(user=user)
        data = {
            "name": "Test name",
            "message": "Test message",
            "get_notified": False,
            "email": "",
        }

        for _ in range(2):
            self.post("contacts:menu_report", school_id=school.pk, data=data)
        response = self.post("contacts:menu_report", school_id=school.pk, data=data)

        self.response_200(response)
        # [-1]: the two earlier POSTs redirected (302) without being followed, so their
        # own success messages are still queued unread ahead of this one.
        message = list(get_messages(response.wsgi_request))[-1].message
        assert message == "Troppe richieste da questo indirizzo. Riprova più tardi."
        assert MenuReport.objects.count() == 2


class ReportListView(TestCase):
    def test_get(self):
        user = self.make_user()
        school = SchoolFactory(user=user)
        report = MenuReportFactory(receiver=school.user)

        with self.login(user):
            response = self.get("contacts:report_list")

        self.response_200(response)
        assertTemplateUsed(response, "contacts/report-list.html")
        assert response.context["reports"][0] == report


class ReportDetailView(TestCase):
    def test_get(self):
        user = self.make_user()
        school = SchoolFactory(user=user)
        report = MenuReportFactory(receiver=school.user)

        with self.login(user):
            response = self.get("contacts:report_detail", report_id=report.pk)

        self.response_200(response)
        assertTemplateUsed(response, "contacts/report-detail.html")
        assert response.context["report"] == report


class ReportDeleteView(TestCase):
    def test_post(self):
        user = self.make_user()
        school = SchoolFactory(user=user)
        report = MenuReportFactory(receiver=school.user)

        with self.login(user):
            response = self.post("contacts:report_delete", report_id=report.pk)

        self.response_200(response)
        assertTemplateUsed(response, "contacts/report-list.html")
        assert MenuReport.objects.count() == 0

    def test_with_another_user(self):
        user1 = self.make_user("u1")
        user2 = self.make_user("u2")
        school = SchoolFactory(user=user1)
        report = MenuReportFactory(receiver=school.user)

        with self.login(user2):
            response = self.post("contacts:report_delete", report_id=report.pk)

        # 404 rather than a silent no-op 200: the report is not theirs to address at all,
        # and the same answer as a missing id gives nothing away (#246).
        self.response_404(response)
        assert MenuReport.objects.count() == 1


class ReportFeedbackView(TestCase):
    def test_get(self):
        user = self.make_user()
        school = SchoolFactory(user=user)
        report = MenuReportFactory(receiver=school.user)

        with self.login(user):
            response = self.get("contacts:report_feedback", report_id=report.pk)

        self.response_200(response)

    def test_post_with_success(self):
        user = self.make_user()
        school = SchoolFactory(user=user)
        report = MenuReportFactory(receiver=school.user)
        data = {"message": "Test message"}

        with self.login(user):
            response = self.post(
                "contacts:report_feedback", report_id=report.pk, data=data
            )

        self.response_302(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == "Risposta inviata con successo"
        report.refresh_from_db()
        assert report.feedback_sent_at is not None

    def test_post_records_error_and_no_timestamp_when_send_fails(self):
        user = self.make_user()
        school = SchoolFactory(user=user)
        report = MenuReportFactory(receiver=school.user)
        data = {"message": "Test message"}

        with patch("contacts.views.send_mail", side_effect=Exception("boom")):
            with self.login(user):
                response = self.post(
                    "contacts:report_feedback", report_id=report.pk, data=data
                )

        self.response_302(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert "boom" in str(message)
        report.refresh_from_db()
        assert report.feedback_sent_at is None

    def test_a_stranger_cannot_answer_someone_elses_report(self):
        """
        The report is fetched by id alone, so any logged-in user could POST here and make
        the site send an arbitrary message to the address on somebody else's report (#246).
        """
        from django.core import mail

        owner = self.make_user("owner@test.com")
        report = MenuReportFactory(receiver=owner, email="vittima@example.com")
        intruder = self.make_user("intruder@test.com")

        with self.login(intruder):
            response = self.post(
                "contacts:report_feedback",
                report_id=report.pk,
                data={"message": "messaggio non autorizzato"},
            )

        self.response_404(response)
        assert mail.outbox == []

    def test_a_stranger_cannot_open_the_feedback_form(self):
        owner = self.make_user("owner@test.com")
        report = MenuReportFactory(receiver=owner)
        intruder = self.make_user("intruder@test.com")

        with self.login(intruder):
            response = self.get("contacts:report_feedback", report_id=report.pk)

        self.response_404(response)

    def test_post_with_empty_message(self):
        user = self.make_user()
        school = SchoolFactory(user=user)
        report = MenuReportFactory(receiver=school.user)
        data = {"message": ""}

        with self.login(user):
            response = self.post(
                "contacts:report_feedback", report_id=report.pk, data=data
            )

        self.response_200(response)
        assert "form" in response.context
