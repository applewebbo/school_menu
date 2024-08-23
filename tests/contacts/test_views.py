from pytest_django.asserts import assertTemplateUsed

from school_menu.test import TestCase


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
