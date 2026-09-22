"""Site-wide URL wiring that doesn't belong to a single app."""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_well_known_change_password_redirects_to_account_change_password(client):
    """Password managers look up this RFC 8615 URL after a breach warning (#288)."""
    response = client.get("/.well-known/change-password")

    assert response.status_code == 302
    assert response.url == reverse("account_change_password")
