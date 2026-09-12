import pytest
from allauth.account.models import EmailAddress
from django import forms
from django.test import Client, override_settings
from django.urls import reverse
from django.utils.html import escape

from users.forms import MyCustomSignupForm
from users.models import User

pytestmark = pytest.mark.django_db

NON_FIELD_MESSAGE = "Registrazione non disponibile al momento."


def _signup_payload(**overrides):
    payload = {
        "email": "newcomer@test.com",
        "password1": "a-strong-passphrase-42",  # nosec B105
        "tc_agree": True,
    }
    payload.update(overrides)
    return payload


def test_signup_with_honeypot_filled_is_rejected():
    """A bot that fills every input, including the hidden one, never gets an account (#272)."""
    response = Client().post(
        reverse("account_signup"),
        data=_signup_payload(website="https://spam.example"),
    )

    form = response.context["form"]
    assert NON_FIELD_MESSAGE in form.errors["website"]
    assert not User.objects.filter(email="newcomer@test.com").exists()


def test_signup_with_honeypot_empty_succeeds():
    Client().post(reverse("account_signup"), data=_signup_payload())

    assert User.objects.filter(email="newcomer@test.com").exists()
    assert EmailAddress.objects.filter(
        email="newcomer@test.com", verified=False
    ).exists()


class _RefusingSignupForm(MyCustomSignupForm):
    """A signup form that fails on ``__all__`` instead of on a single field, so the
    test exercises the non-field-error branch of the template."""

    def clean(self):
        super().clean()
        raise forms.ValidationError(NON_FIELD_MESSAGE)


@override_settings(ACCOUNT_FORMS={"signup": f"{__name__}._RefusingSignupForm"})
def test_signup_non_field_error_is_shown_on_the_page():
    """The template rendered only the per-field errors, so an error allauth raises on
    ``__all__`` never reached the screen (#261)."""
    response = Client().post(
        reverse("account_signup"),
        data={
            "email": "newcomer@test.com",
            "password1": "a-strong-passphrase-42",  # nosec B105
        },
    )

    form = response.context["form"]
    assert NON_FIELD_MESSAGE in form.non_field_errors()
    assert escape(NON_FIELD_MESSAGE) in response.content.decode()
