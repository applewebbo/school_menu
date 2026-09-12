"""
The allauth pages that had nothing to act on besides "go back" were replaced with a
redirect + toast instead of a dedicated page behind the app's navbar (#262).
"""

import pytest
from django.contrib.messages import get_messages
from django.test import Client
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_email_verification_sent_redirects_home_with_a_toast():
    response = Client().get(reverse("account_email_verification_sent"))

    assert response.status_code == 302
    assert response.url == reverse("school_menu:index")
    message = list(get_messages(response.wsgi_request))[0]
    assert "7 giorni" in message.message


def test_password_reset_done_redirects_home_with_a_toast():
    response = Client().get(reverse("account_reset_password_done"))

    assert response.status_code == 302
    assert response.url == reverse("school_menu:index")
    message = list(get_messages(response.wsgi_request))[0]
    assert "email" in message.message


def test_password_reset_from_key_done_redirects_to_login_with_a_toast():
    response = Client().get(reverse("account_reset_password_from_key_done"))

    assert response.status_code == 302
    assert response.url == reverse("account_login")
    message = list(get_messages(response.wsgi_request))[0]
    assert "Password cambiata" in message.message
