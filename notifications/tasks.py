import json
import logging

from django.conf import settings
from django.utils import timezone
from django_q.models import Schedule
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
        logger.error(f"Errore durante l'invio della notifica: {e}")
        raise
    except Exception as e:
        logger.error(f"Errore inatteso durante l'invio della notifica: {e}")
        raise
    logger.info("notifica di prova inviata")


def send_daily_menu_notification():
    """
    Invia una notifica con il menu del giorno a tutti gli iscritti.
    """
    logger.info("Invio notifiche giornaliere del menu...")
    subscriptions = AnonymousMenuNotification.objects.filter(daily_notification=True)
    for subscription in subscriptions:
        school = subscription.school
        payload = build_menu_notification_payload(school)
        payload["icon"] = "/static/img/notification-bell.png"
        payload["url"] = school.get_absolute_url()
        send_test_notification(subscription.subscription_info, payload)
    logger.info("Notifiche giornaliere del menu inviate.")


def schedule_daily_menu_notification():
    """
    Crea o aggiorna una schedulazione giornaliera per inviare il menu del giorno.
    """
    name = "daily_menu_notification"
    Schedule.objects.update_or_create(
        name=name,
        defaults={
            "func": "notifications.tasks.send_daily_menu_notification",
            "schedule_type": Schedule.DAILY,
            "next_run": timezone.now().replace(hour=12, minute=0, second=0),
            "repeats": -1,
        },
    )
