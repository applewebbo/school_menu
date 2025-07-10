import json
import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from django_q.models import Schedule
from pywebpush import WebPushException, webpush

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
    except Exception as e:
        logger.error(f"Errore inatteso durante l'invio della notifica: {e}")
    logger.info("notifica di prova inviata")


def schedule_periodic_notifications(subscription_info, payload, user_id):
    """
    Crea o aggiorna una schedulazione periodica che invia una notifica ogni minuto.
    """
    name = f"periodic_notification_{user_id}"
    now = timezone.now()
    Schedule.objects.update_or_create(
        name=name,
        defaults={
            "func": "notifications.tasks.send_test_notification",
            "args": f"{subscription_info},{payload}",
            "schedule_type": Schedule.MINUTES,
            "minutes": 1,
            "repeats": -1,  # infinito finché non viene stoppato
            "next_run": now + timedelta(seconds=5),
        },
    )


def stop_periodic_notifications(user_id):
    """
    Ferma la schedulazione periodica per l'utente specificato.
    """
    name = f"periodic_notification_{user_id}"
    print(name)
    Schedule.objects.filter(name=name).delete()
