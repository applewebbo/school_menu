from datetime import date
from unittest.mock import patch

import pytest
import time_machine
from django.contrib.messages import get_messages
from django.urls import reverse
from pywebpush import WebPushException

from notifications.models import AnonymousMenuNotification

pytestmark = pytest.mark.django_db


def test_save_subscription(client, school_factory):
    school = school_factory()
    url = reverse("notifications:save_subscription")
    data = {
        "school": school.pk,
        "subscription_info": '{"endpoint": "test_endpoint", "keys": {"p256dh": "test_p256dh", "auth": "test_auth"}}',
        "notification_time": AnonymousMenuNotification.PREVIOUS_DAY_6PM,
    }
    response = client.post(url, data)
    assert response.status_code == 204
    assert response["HX-Refresh"] == "true"
    assert AnonymousMenuNotification.objects.filter(school=school).exists()


def test_save_subscription_invalid_school(client):
    """Test save_subscription with an invalid school."""
    url = reverse("notifications:save_subscription")
    data = {
        "school": 999,
        "subscription_info": '{"endpoint": "test_endpoint", "keys": {"p256dh": "test_p256dh", "auth": "test_auth"}}',
        "notification_time": AnonymousMenuNotification.PREVIOUS_DAY_6PM,
    }
    response = client.post(url, data)
    assert response.status_code == 400
    form = response.context["form"]
    assert "school" in form.errors
    assert (
        "Scegli un'opzione valida. La scelta effettuata non compare tra quelle disponibili."
        in form.errors["school"][0]
    )


def test_save_subscription_missing_school(client):
    """Test save_subscription with a missing school."""
    url = reverse("notifications:save_subscription")
    data = {
        "subscription_info": '{"endpoint": "test_endpoint", "keys": {"p256dh": "test_p256dh", "auth": "test_auth"}}',
        "notification_time": AnonymousMenuNotification.PREVIOUS_DAY_6PM,
    }
    response = client.post(url, data)
    assert response.status_code == 400
    form = response.context["form"]
    assert "school" in form.errors
    assert "Campo obbligatorio." in form.errors["school"]


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


def test_delete_subscription_no_pk_in_session(client):
    """Test delete_subscription view when no pk is in session."""
    url = reverse("notifications:delete_subscription")
    response = client.post(url)
    assert response.status_code == 400
    assert response["HX-Refresh"] == "true"
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) == 1
    assert str(messages[0]) == "Nessuna sottoscrizione trovata."


def test_delete_subscription_invalid_pk(client):
    """Test eliminazione con pk non esistente."""
    session = client.session
    session["anon_notification_pk"] = 99999  # pk non esistente
    session.save()
    url = reverse("notifications:delete_subscription")
    response = client.post(url)
    assert response.status_code == 404


def test_delete_subscription_method_not_allowed(client):
    """Test richiesta non-POST."""
    url = reverse("notifications:delete_subscription")
    response = client.get(url)
    assert response.status_code == 405
    assert response["HX-Refresh"] == "true"
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) == 1
    assert str(messages[0]) == "Richiesta non valida."


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


def test_test_notification_no_pk_in_session(client):
    """Test test_notification view when no pk is in session."""
    url = reverse("notifications:test_notification")
    response = client.post(url)
    assert response.status_code == 200
    assert "Nessuna sottoscrizione trovata." in response.content.decode()


def test_test_notification_invalid_pk(client):
    """Test notifica di prova con pk non esistente."""
    session = client.session
    session["anon_notification_pk"] = 99999  # pk non esistente
    session.save()
    url = reverse("notifications:test_notification")
    response = client.post(url)
    if response.status_code == 404:
        # Risposta 404: template di errore standard
        assert (
            b"non esiste" in response.content.lower()
            or b"errore" in response.content.lower()
        )
    else:
        # Risposta 200: alert custom
        assert (
            b'role="alert"' in response.content or b'class="alert"' in response.content
        )
        assert (
            b"non esiste" in response.content.lower()
            or b"errore" in response.content.lower()
        )


def test_test_notification_success(client, school_factory, monkeypatch):
    """Test invio notifica di prova riuscito."""
    school = school_factory()
    notification = AnonymousMenuNotification.objects.create(
        school=school,
        subscription_info={"endpoint": "test", "keys": {"p256dh": "a", "auth": "b"}},
    )
    session = client.session
    session["anon_notification_pk"] = notification.pk
    session.save()
    url = reverse("notifications:test_notification")

    def fake_webpush(*args, **kwargs):
        return None

    monkeypatch.setattr("notifications.tasks.send_test_notification", fake_webpush)
    response = client.post(url)
    assert response.status_code == 200
    # Verifica che sia presente un alert (messaggio per l'utente)
    assert b'role="alert"' in response.content or b'class="alert"' in response.content


@patch(
    "notifications.tasks.send_test_notification", side_effect=Exception("Generic Error")
)
def test_test_notification_generic_exception(mock_send, client, school_factory):
    """Test test_notification view with a generic exception."""
    school = school_factory()
    notification = AnonymousMenuNotification.objects.create(
        school=school,
        subscription_info={"endpoint": "test", "keys": {"p256dh": "a", "auth": "b"}},
    )
    session = client.session
    session["anon_notification_pk"] = notification.pk
    session.save()
    url = reverse("notifications:test_notification")
    response = client.post(url)
    assert response.status_code == 200
    assert (
        "Errore durante l'invio della notifica di prova." in response.content.decode()
    )


def test_notification_settings_with_invalid_session(client):
    """Testa la vista delle impostazioni con un pk non valido in sessione."""
    session = client.session
    session["anon_notification_pk"] = 999  # pk non esistente
    session.save()
    url = reverse("notifications:notification_settings")
    response = client.get(url)
    assert response.status_code == 404


def test_notifications_buttons(client, school_factory):
    """Testa la vista che restituisce i bottoni delle notifiche."""
    school = school_factory()
    notification = AnonymousMenuNotification.objects.create(
        school=school, subscription_info="test"
    )
    url = reverse("notifications:notifications_buttons", kwargs={"pk": notification.pk})
    response = client.get(url)
    assert response.status_code == 200
    assert b"Disabilita" in response.content


def test_toggle_daily_notification_no_session(client):
    """Test toggle senza pk in sessione."""
    url = reverse("notifications:toggle_daily_notification")
    response = client.post(url)
    assert response.status_code == 400


def test_toggle_daily_notification(client, school_factory):
    """Test toggle notifiche giornaliere."""
    school = school_factory()
    notification = AnonymousMenuNotification.objects.create(
        school=school, subscription_info="test", daily_notification=False
    )
    session = client.session
    session["anon_notification_pk"] = notification.pk
    session.save()
    url = reverse("notifications:toggle_daily_notification")
    response = client.post(url)
    assert response.status_code == 200
    notification.refresh_from_db()
    assert notification.daily_notification is True
    response = client.post(url)
    assert response.status_code == 200
    notification.refresh_from_db()
    assert notification.daily_notification is False


def test_change_school_get(client, school_factory):
    """Test GET per cambiare scuola."""
    school = school_factory()
    notification = AnonymousMenuNotification.objects.create(
        school=school, subscription_info="test"
    )
    url = reverse("notifications:change_school", kwargs={"pk": notification.pk})
    response = client.get(url)
    assert response.status_code == 200


def test_change_school_post_valid(client, school_factory):
    """Test POST per cambiare scuola con dati validi."""
    school1 = school_factory()
    school2 = school_factory()
    notification = AnonymousMenuNotification.objects.create(
        school=school1, subscription_info="test"
    )
    url = reverse("notifications:change_school", kwargs={"pk": notification.pk})
    data = {
        "school": school2.pk,
        "subscription_info": '{"endpoint": "test"}',
        "notification_time": notification.notification_time,
    }
    response = client.post(url, data)
    assert response.status_code == 200
    notification.refresh_from_db()
    assert notification.school == school2


def test_change_school_post_invalid(client, school_factory):
    """Test POST per cambiare scuola con dati non validi."""
    school = school_factory()
    notification = AnonymousMenuNotification.objects.create(
        school=school, subscription_info="test"
    )
    url = reverse("notifications:change_school", kwargs={"pk": notification.pk})
    response = client.post(url)
    assert response.status_code == 200


@patch("notifications.views.build_menu_notification_payload", return_value=None)
def test_test_notification_no_payload(mock_build, client, school_factory):
    """
    Testa l'invio di una notifica di prova quando non c'è un menu per il giorno.
    In questo caso, la vista dovrebbe costruire un payload di fallback.
    """
    school = school_factory()
    notification = AnonymousMenuNotification.objects.create(
        school=school,
        subscription_info={"endpoint": "test", "keys": {"p256dh": "a", "auth": "b"}},
    )
    session = client.session
    session["anon_notification_pk"] = notification.pk
    session.save()
    url = reverse("notifications:test_notification")
    with patch("notifications.views.async_task") as mock_async_task:
        response = client.post(url)
        assert response.status_code == 200
        assert "Notifica di prova inviata in background" in response.content.decode()
        mock_async_task.assert_called_once()
        # Verifica che il payload di fallback sia stato usato
        payload = mock_async_task.call_args[0][2]
        assert payload["head"] == "Notifica di prova"
        assert (
            payload["body"] == "Nessun menu previsto per oggi, ma la notifica funziona!"
        )


@patch(
    "notifications.views.async_task",
    side_effect=WebPushException("WebPush Error"),
)
def test_test_notification_webpush_exception(mock_async_task, client, school_factory):
    """Test test_notification view with a WebPushException."""
    school = school_factory()
    notification = AnonymousMenuNotification.objects.create(
        school=school,
        subscription_info={"endpoint": "test", "keys": {"p256dh": "a", "auth": "b"}},
    )
    session = client.session
    session["anon_notification_pk"] = notification.pk
    session.save()
    url = reverse("notifications:test_notification")
    response = client.post(url)
    assert response.status_code == 200
    assert (
        "Errore durante l'invio della notifica di prova." in response.content.decode()
    )


@time_machine.travel("2025-08-04")
def test_test_notification_with_payload(client, school_factory, annual_meal_factory):
    """
    Testa l'invio di una notifica di prova quando c'è un menu per il giorno.
    """
    school = school_factory(annual_menu=True)
    # Create a meal for today for the school
    annual_meal_factory(school=school, date=date.today(), is_active=True)
    notification = AnonymousMenuNotification.objects.create(
        school=school,
        subscription_info={"endpoint": "test", "keys": {"p256dh": "a", "auth": "b"}},
    )
    session = client.session
    session["anon_notification_pk"] = notification.pk
    session.save()
    url = reverse("notifications:test_notification")
    with patch("notifications.views.async_task") as mock_async_task:
        response = client.post(url)
        assert response.status_code == 200
        assert "Notifica di prova inviata in background" in response.content.decode()
        mock_async_task.assert_called_once()
        # Verifica che il payload corretto sia stato usato
        payload = mock_async_task.call_args[0][2]
        assert payload["head"] != "Notifica di prova"
        assert "body" in payload


# Tests for duplicate prevention and cookie-based recovery (issue #190)


def test_save_subscription_prevents_duplicates(client, school_factory):
    """Test that saving the same subscription twice updates instead of creating duplicate."""
    school = school_factory()
    url = reverse("notifications:save_subscription")
    subscription_info = '{"endpoint": "https://example.com/push/endpoint1", "keys": {"p256dh": "test_p256dh", "auth": "test_auth"}}'

    # First subscription
    data = {
        "school": school.pk,
        "subscription_info": subscription_info,
        "notification_time": AnonymousMenuNotification.PREVIOUS_DAY_6PM,
    }
    response = client.post(url, data)
    assert response.status_code == 204
    assert AnonymousMenuNotification.objects.count() == 1
    first_notification = AnonymousMenuNotification.objects.first()

    # Second subscription with same endpoint but different school/time
    school2 = school_factory()
    data["school"] = school2.pk
    data["notification_time"] = AnonymousMenuNotification.SAME_DAY_12PM
    response = client.post(url, data)
    assert response.status_code == 204

    # Should still have only 1 notification (updated, not created)
    assert AnonymousMenuNotification.objects.count() == 1
    updated_notification = AnonymousMenuNotification.objects.first()

    # Same pk (updated existing record)
    assert updated_notification.pk == first_notification.pk
    # But with updated values
    assert updated_notification.school == school2
    assert (
        updated_notification.notification_time
        == AnonymousMenuNotification.SAME_DAY_12PM
    )


def test_save_subscription_sets_persistent_cookie(client, school_factory):
    """Test that save_subscription sets a persistent cookie for recovery."""
    school = school_factory()
    url = reverse("notifications:save_subscription")
    data = {
        "school": school.pk,
        "subscription_info": '{"endpoint": "https://example.com/push/endpoint2", "keys": {"p256dh": "test_p256dh", "auth": "test_auth"}}',
        "notification_time": AnonymousMenuNotification.SAME_DAY_12PM,
    }
    response = client.post(url, data)
    assert response.status_code == 204

    # Check that cookie was set
    assert "subscription_endpoint" in response.cookies
    cookie = response.cookies["subscription_endpoint"]

    # Cookie should have long expiry (1 year = 31536000 seconds)
    assert cookie["max-age"] == 365 * 24 * 60 * 60
    assert cookie["httponly"]
    assert cookie["samesite"] == "Lax"

    # Cookie value should be the hashed endpoint
    notification = AnonymousMenuNotification.objects.first()
    assert cookie.value == notification.subscription_endpoint


def test_delete_subscription_clears_cookie(client, school_factory):
    """Test that delete_subscription clears the persistent cookie."""
    school = school_factory()
    notification = AnonymousMenuNotification.objects.create(
        school=school,
        subscription_info={
            "endpoint": "https://example.com/push/endpoint3",
            "keys": {"p256dh": "a", "auth": "b"},
        },
    )
    session = client.session
    session["anon_notification_pk"] = notification.pk
    session.save()

    # Set the cookie manually (simulating it was set during save_subscription)
    client.cookies["subscription_endpoint"] = notification.subscription_endpoint

    url = reverse("notifications:delete_subscription")
    response = client.post(url)
    assert response.status_code == 204

    # Check that cookie was deleted
    assert response.cookies["subscription_endpoint"].value == ""


def test_notification_settings_recovers_from_cookie(client, school_factory):
    """Test that notification_settings recovers session from persistent cookie when session is missing."""
    school = school_factory()
    notification = AnonymousMenuNotification.objects.create(
        school=school,
        subscription_info={
            "endpoint": "https://example.com/push/endpoint4",
            "keys": {"p256dh": "a", "auth": "b"},
        },
    )

    # Simulate: user has cookie but no session (session expired)
    client.cookies["subscription_endpoint"] = notification.subscription_endpoint
    # Explicitly don't set session

    url = reverse("notifications:notification_settings")
    response = client.get(url)
    assert response.status_code == 200

    # Session should have been recovered
    assert client.session.get("anon_notification_pk") == notification.pk

    # Notification should be in context
    assert "notification" in response.context
    assert response.context["notification"] == notification


def test_notification_settings_clears_invalid_cookie(client):
    """Test that notification_settings clears cookie if subscription doesn't exist."""
    # Set a cookie with a hash that doesn't match any subscription
    client.cookies["subscription_endpoint"] = "invalid_hash_that_does_not_exist"

    url = reverse("notifications:notification_settings")
    response = client.get(url)
    assert response.status_code == 200

    # Cookie should be cleared
    assert response.cookies["subscription_endpoint"].value == ""

    # Session should not be set
    assert "anon_notification_pk" not in client.session


def test_save_subscription_without_endpoint(client, school_factory):
    """Test that save_subscription fails gracefully if subscription_info lacks endpoint."""
    school = school_factory()
    url = reverse("notifications:save_subscription")
    data = {
        "school": school.pk,
        "subscription_info": '{"keys": {"p256dh": "test_p256dh", "auth": "test_auth"}}',  # Missing endpoint
        "notification_time": AnonymousMenuNotification.SAME_DAY_12PM,
    }
    response = client.post(url, data)

    # Should return 400 error
    assert response.status_code == 400

    # No notification should be created
    assert AnonymousMenuNotification.objects.count() == 0


def test_save_subscription_shows_updated_message(client, school_factory):
    """Test that save_subscription shows 'updated' message for existing subscriptions."""
    school = school_factory()
    url = reverse("notifications:save_subscription")
    subscription_info = '{"endpoint": "https://example.com/push/endpoint5", "keys": {"p256dh": "test_p256dh", "auth": "test_auth"}}'

    # First subscription
    data = {
        "school": school.pk,
        "subscription_info": subscription_info,
        "notification_time": AnonymousMenuNotification.PREVIOUS_DAY_6PM,
    }
    response = client.post(url, data)
    messages = list(get_messages(response.wsgi_request))
    assert len(messages) == 1
    assert "abilitate" in str(messages[0])

    # Second subscription with same endpoint
    response = client.post(url, data)
    messages = list(get_messages(response.wsgi_request))
    # Should have 2 messages total (1 from first, 1 from second)
    assert len(messages) == 2
    assert "aggiornate" in str(messages[1])
