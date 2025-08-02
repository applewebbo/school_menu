import json
import logging

from django.conf import settings
from pywebpush import WebPushException, webpush

from notifications.models import AnonymousMenuNotification
from notifications.utils import build_menu_notification_payload

logger = logging.getLogger(__name__)


def send_test_notification(subscription_info, payload):
    """
    Task che invia una notifica di prova in maniera asincrona
    """
    try:
        webpush(
            subscription_info=subscription_info,
            data=json.dumps(payload),
            vapid_private_key=settings.WEBPUSH_SETTINGS["VAPID_PRIVATE_KEY"],
            vapid_claims={
                "sub": f"mailto:{settings.WEBPUSH_SETTINGS['VAPID_ADMIN_EMAIL']}"
            },
        )
        logger.info("Notifica di prova inviata con successo.")
    except WebPushException as e:
        # If a subscription is expired or invalid, it should be deleted
        if e.response.status_code in [404, 410]:
            logger.info(
                f"Subscription expired or invalid: {e.response.text}. Deleting..."
            )
            AnonymousMenuNotification.objects.filter(
                subscription_info=subscription_info
            ).delete()
        else:
            logger.error(f"Errore durante l'invio della notifica: {e}")
            raise
    except Exception as e:
        logger.error(f"Errore inatteso durante l'invio della notifica: {e}")
        raise
    logger.info("notifica di prova inviata")


def _send_menu_notifications(notification_time):
    """
    Sends menu notifications for a specific time.
    """
    logger.info(f"Invio notifiche per l'orario: {notification_time}...")
    subscriptions = AnonymousMenuNotification.objects.filter(
        daily_notification=True, notification_time=notification_time
    )
    for subscription in subscriptions:
        school = subscription.school
        # The payload needs to be built considering if it's the day before or the same day
        is_previous_day = (
            notification_time == AnonymousMenuNotification.PREVIOUS_DAY_6PM
        )
        payload = build_menu_notification_payload(school, is_previous_day)

        if not payload:
            logger.info(
                f"Nessun menu trovato per la scuola {school.name}, notifiche non inviate."
            )
            continue

        payload["icon"] = "/static/img/notification-bell.png"
        payload["url"] = school.get_absolute_url()
        send_test_notification(subscription.subscription_info, payload)
    logger.info(f"Notifiche per l'orario {notification_time} inviate.")


def send_previous_day_6pm_menu_notification():
    """
    Sends menu notifications for the next day at 6 PM.
    """
    _send_menu_notifications(AnonymousMenuNotification.PREVIOUS_DAY_6PM)


def send_same_day_9am_menu_notification():
    """
    Sends menu notifications for the current day at 9 AM.
    """
    _send_menu_notifications(AnonymousMenuNotification.SAME_DAY_9AM)


def send_same_day_12pm_menu_notification():
    """
    Sends menu notifications for the current day at 12 PM.
    """
    _send_menu_notifications(AnonymousMenuNotification.SAME_DAY_12PM)


def send_same_day_6pm_menu_notification():
    """
    Sends menu notifications for the current day at 6 PM.
    """
    _send_menu_notifications(AnonymousMenuNotification.SAME_DAY_6PM)
