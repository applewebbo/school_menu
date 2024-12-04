from django.contrib.messages import get_messages
from pytest_django.asserts import assertTemplateUsed

from contacts.models import MenuReport
from school_menu.test import TestCase
from tests.school_menu.factories import SchoolFactory
from tests.t_contacts.factories import MenuReportFactory


class ContactView(TestCase):
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


class MenuReportView(TestCase):
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

        self.response_200(response)
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
