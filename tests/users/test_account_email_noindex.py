"""
The allauth email-management page is login-gated account machinery, not content
worth a search listing, so it's excluded from indexing (#332).
"""

import pytest
from django.test import Client
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_account_email_has_noindex(user):
    client = Client()
    client.force_login(user)

    response = client.get(reverse("account_email"))

    assert response.status_code == 200
    assert b'<meta name="robots" content="noindex, nofollow">' in response.content
