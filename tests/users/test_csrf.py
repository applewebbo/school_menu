import pytest
from django.test import Client
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_login_csrf_behind_tls_terminating_proxy():
    """A login POST from an HTTPS browser behind a TLS-terminating reverse proxy
    (Coolify forwards ``X-Forwarded-Proto: https`` over plain HTTP) must not be
    rejected with a CSRF 403 due to a scheme mismatch on the Origin check.

    Reproduces the production-only ``403 Request aborted`` reported in #222.
    """
    client = Client(enforce_csrf_checks=True)
    login_url = reverse("account_login")

    # SERVER_PORT 443 mirrors the public HTTPS endpoint so the host has no port
    # suffix, matching the browser Origin header exactly.
    proxied = {"HTTP_X_FORWARDED_PROTO": "https", "SERVER_PORT": "443"}

    get_response = client.get(login_url, **proxied)
    csrf_token = get_response.cookies["csrftoken"].value

    response = client.post(
        login_url,
        data={
            "login": "nobody@example.com",
            "password": "wrong-password",  # nosec B105
            "csrfmiddlewaretoken": csrf_token,
        },
        HTTP_ORIGIN="https://testserver",
        **proxied,
    )

    assert response.status_code != 403
