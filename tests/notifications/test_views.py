import pytest
from django.urls import reverse

from notifications.models import AnonymousMenuNotification

pytestmark = pytest.mark.django_db


def test_save_subscription(client, school_factory):
    school = school_factory()
    url = reverse("notifications:save_subscription")
    data = {
        "school": school.pk,
        "subscription_info": '{"endpoint": "test_endpoint", "keys": {"p256dh": "test_p256dh", "auth": "test_auth"}}',
    }
    response = client.post(url, data)
    assert response.status_code == 204
    assert response["HX-Refresh"] == "true"
    assert AnonymousMenuNotification.objects.filter(school=school).exists()


def test_save_subscription_invalid_form(client):
    url = reverse("notifications:save_subscription")
    data = {
        "school": 999,  # Invalid school
        "subscription_info": "test_subscription_info",
    }
    response = client.post(url, data)
    assert response.status_code == 400
    assert response.content == b"error"


def test_notification_settings_no_session(client):
    url = reverse("notifications:notification_settings")
    response = client.get(url)
    assert response.status_code == 200
    assert b"form" in response.content or b"csrfmiddlewaretoken" in response.content


def test_notification_settings_with_session(client, school_factory):
    school = school_factory()
    notification = AnonymousMenuNotification.objects.create(
        school=school, subscription_info="test"
    )
    session = client.session
    session["anon_notification_pk"] = notification.pk
    session.save()
    url = reverse("notifications:notification_settings")
    response = client.get(url)
    assert response.status_code == 200
    assert b"form" in response.content or b"csrfmiddlewaretoken" in response.content
    # Verifica che il nome della scuola sia presente nel contenuto renderizzato (opzionale, dipende dal template)
    if hasattr(school, "name"):
        assert (
            school.name.encode() in response.content
            or str(school.pk).encode() in response.content
        )


def test_delete_subscription_success(client, school_factory):
    """Test eliminazione sottoscrizione con sessione valida."""
    school = school_factory()
    notification = AnonymousMenuNotification.objects.create(
        school=school, subscription_info="test"
    )
    session = client.session
    session["anon_notification_pk"] = notification.pk
    session.save()
    url = reverse("notifications:delete_subscription")
    response = client.post(url)
    assert response.status_code == 204
    assert response["HX-Refresh"] == "true"
    assert not AnonymousMenuNotification.objects.filter(pk=notification.pk).exists()
    assert "anon_notification_pk" not in client.session


def test_delete_subscription_no_session(client):
    """Test eliminazione senza pk in sessione."""
    url = reverse("notifications:delete_subscription")
    response = client.post(url)
    assert response.status_code == 400
    assert response["HX-Refresh"] == "true"


def test_delete_subscription_invalid_pk(client):
    """Test eliminazione con pk non esistente."""
    session = client.session
    session["anon_notification_pk"] = 99999  # pk non esistente
    session.save()
    url = reverse("notifications:delete_subscription")
    response = client.post(url)
    assert response.status_code == 404
    assert response["HX-Refresh"] == "true"


def test_delete_subscription_method_not_allowed(client):
    """Test richiesta non-POST."""
    url = reverse("notifications:delete_subscription")
    response = client.get(url)
    assert response.status_code == 405
    assert response["HX-Refresh"] == "true"


def test_delete_subscription_generic_exception(client, school_factory, monkeypatch):
    """Test gestione eccezione generica durante la cancellazione della notifica."""
    school = school_factory()
    notification = AnonymousMenuNotification.objects.create(
        school=school, subscription_info="test"
    )
    session = client.session
    session["anon_notification_pk"] = notification.pk
    session.save()
    url = reverse("notifications:delete_subscription")

    def raise_exception(*args, **kwargs):
        raise Exception("Errore generico")

    monkeypatch.setattr(AnonymousMenuNotification, "delete", raise_exception)
    response = client.post(url)
    assert response.status_code == 400
    assert response["HX-Refresh"] == "true"
