import pytest
from django import forms
from django.test import Client, override_settings
from django.urls import reverse
from django.utils.html import escape

from users.forms import MyCustomSignupForm

pytestmark = pytest.mark.django_db

NON_FIELD_MESSAGE = "Registrazione non disponibile al momento."


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
