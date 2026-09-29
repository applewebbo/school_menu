"""
Lets an already-registered user flip newsletter_opt_in from the account settings
page without waiting for an unsubscribe email to arrive first (#298).
"""

import pytest
from django.contrib.messages import get_messages
from django.test import Client
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_toggle_newsletter_requires_login():
    response = Client().post(reverse("users:toggle_newsletter"))

    assert response.status_code == 302
    assert response.url.startswith(reverse("account_login"))


def test_toggle_newsletter_get_redirects_to_settings(user):
    client = Client()
    client.force_login(user)

    response = client.get(reverse("users:toggle_newsletter"))

    assert response.status_code == 302
    assert response.url == reverse("school_menu:settings")


def test_toggle_newsletter_flips_opt_in_off_and_back_on(user):
    user.newsletter_opt_in = True
    user.save(update_fields=["newsletter_opt_in"])
    client = Client()
    client.force_login(user)

    response = client.post(reverse("users:toggle_newsletter"))

    user.refresh_from_db()
    assert user.newsletter_opt_in is False
    assert response.status_code == 200
    message = list(get_messages(response.wsgi_request))[0]
    assert "disattivata" in message.message

    response = client.post(reverse("users:toggle_newsletter"))

    user.refresh_from_db()
    assert user.newsletter_opt_in is True
    message = list(get_messages(response.wsgi_request))[0]
    assert "attivata" in message.message


def test_toggle_newsletter_response_swaps_messages_out_of_band(user):
    client = Client()
    client.force_login(user)

    response = client.post(reverse("users:toggle_newsletter"))

    assert b'hx-swap-oob="true"' in response.content
    assert b'id="messages"' in response.content
