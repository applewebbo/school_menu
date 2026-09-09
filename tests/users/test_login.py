import pytest
from django.test import Client
from django.urls import reverse
from django.utils.html import escape

from tests.users.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_wrong_password_shows_the_error_on_the_page():
    """allauth reports a bad login as a non-field error; the hand-built login
    template only rendered the per-field errors, so the message never reached the
    screen and the form looked like it had done nothing (#260).
    """
    user = UserFactory()

    response = Client().post(
        reverse("account_login"),
        data={"login": user.email, "password": "not-the-password"},  # nosec B105
    )

    form = response.context["form"]
    assert form.non_field_errors()
    assert escape(form.non_field_errors()[0]) in response.content.decode()
