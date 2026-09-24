import pytest
from django.test import Client
from django.urls import reverse

from tests.users.factories import UserFactory
from users.tokens import make_unsubscribe_token

pytestmark = pytest.mark.django_db


def test_get_with_valid_token_shows_confirmation_without_unsubscribing():
    """A GET (e.g. a mail client prefetching the link) must not flip the flag (#289)."""
    user = UserFactory(newsletter_opt_in=True)
    token = make_unsubscribe_token(user.pk)

    response = Client().get(reverse("users:newsletter_unsubscribe", args=[token]))

    assert response.status_code == 200
    assert response.context["state"] == "confirm"
    user.refresh_from_db()
    assert user.newsletter_opt_in is True


def test_post_with_valid_token_unsubscribes_and_confirms():
    user = UserFactory(newsletter_opt_in=True)
    token = make_unsubscribe_token(user.pk)

    response = Client().post(reverse("users:newsletter_unsubscribe", args=[token]))

    assert response.status_code == 200
    assert response.context["state"] == "done"
    user.refresh_from_db()
    assert user.newsletter_opt_in is False


def test_tampered_token_is_rejected_on_get_without_changing_state():
    user = UserFactory(newsletter_opt_in=True)
    token = make_unsubscribe_token(user.pk)
    tampered = token[:-1] + ("a" if token[-1] != "a" else "b")

    response = Client().get(reverse("users:newsletter_unsubscribe", args=[tampered]))

    assert response.status_code == 200
    assert response.context["state"] == "invalid"
    user.refresh_from_db()
    assert user.newsletter_opt_in is True


def test_tampered_token_is_rejected_on_post_without_changing_state():
    user = UserFactory(newsletter_opt_in=True)
    token = make_unsubscribe_token(user.pk)
    tampered = token[:-1] + ("a" if token[-1] != "a" else "b")

    response = Client().post(reverse("users:newsletter_unsubscribe", args=[tampered]))

    assert response.status_code == 200
    assert response.context["state"] == "invalid"
    user.refresh_from_db()
    assert user.newsletter_opt_in is True


def test_token_for_deleted_user_is_rejected():
    user = UserFactory()
    token = make_unsubscribe_token(user.pk)
    user.delete()

    response = Client().get(reverse("users:newsletter_unsubscribe", args=[token]))

    assert response.status_code == 200
    assert response.context["state"] == "invalid"


def test_no_login_required():
    user = UserFactory(newsletter_opt_in=True)
    token = make_unsubscribe_token(user.pk)

    client = Client()  # not logged in
    response = client.post(reverse("users:newsletter_unsubscribe", args=[token]))

    assert response.status_code == 200
    assert response.context["state"] == "done"
