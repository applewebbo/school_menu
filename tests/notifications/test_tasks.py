import pytest
from django_q.models import Schedule
from pywebpush import WebPushException

from notifications.tasks import (
    schedule_periodic_notifications,
    send_test_notification,
    stop_periodic_notifications,
)

pytestmark = pytest.mark.django_db


def test_send_test_notification_success_with_string_args(monkeypatch):
    """Test invio notifica di prova con successo."""

    def fake_webpush(*args, **kwargs):
        return None

    monkeypatch.setattr("notifications.tasks.webpush", fake_webpush)
    send_test_notification('{"test": "test"}', '{"test": "test"}')


def test_send_test_notification_success(monkeypatch):
    """Test invio notifica di prova con successo."""

    def fake_webpush(*args, **kwargs):
        return None

    monkeypatch.setattr("notifications.tasks.webpush", fake_webpush)
    send_test_notification({}, {})


def test_send_test_notification_webpush_exception(monkeypatch):
    """Test invio notifica di prova con WebPushException."""

    def fake_webpush(*args, **kwargs):
        raise WebPushException("test")

    monkeypatch.setattr("notifications.tasks.webpush", fake_webpush)
    with pytest.raises(WebPushException):
        send_test_notification({}, {})


def test_send_test_notification_generic_exception(monkeypatch):
    """Test invio notifica di prova con eccezione generica."""

    def fake_webpush(*args, **kwargs):
        raise ValueError("test")

    monkeypatch.setattr("notifications.tasks.webpush", fake_webpush)
    with pytest.raises(ValueError):
        send_test_notification({}, {})


def test_schedule_periodic_notifications(monkeypatch):
    """Test schedulazione notifiche periodiche."""

    def fake_update_or_create(*args, **kwargs):
        return None

    monkeypatch.setattr(Schedule.objects, "update_or_create", fake_update_or_create)
    schedule_periodic_notifications({}, {}, 1)


def test_stop_periodic_notifications(monkeypatch):
    """Test stop notifiche periodiche."""

    class MockQuerySet:
        def delete(self):
            pass

    def fake_filter(*args, **kwargs):
        return MockQuerySet()

    monkeypatch.setattr(Schedule.objects, "filter", fake_filter)
    stop_periodic_notifications(1)
