import json
import logging

from django.conf import settings
from django_q.models import Schedule
from pywebpush import WebPushException, webpush

logger = logging.getLogger(__name__)


def send_test_notification(subscription_info, payload):
    """
    Task che invia una notifica di prova in maniera asincrona
    """
    if isinstance(subscription_info, str):
        subscription_info = json.loads(subscription_info.replace("'", '"'))
    if isinstance(payload, str):
        payload = json.loads(payload.replace("'", '"'))

    try:
        webpush(
            subscription_info=subscription_info,
            data=payload,
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


def schedule_periodic_notifications(subscription_info, payload, user_id):
    """
    Crea o aggiorna una schedulazione periodica che invia una notifica ogni minuto.
    """
    name = f"periodic_notification_{user_id}"
    Schedule.objects.update_or_create(
        name=name,
        defaults={
            "func": "notifications.tasks.send_test_notification",
            "args": f"'{json.dumps(subscription_info)}', '{json.dumps(payload)}'",
            "schedule_type": Schedule.MINUTES,
            "minutes": 1,
            "repeats": -1,  # infinito finché non viene stoppato
        },
    )


def stop_periodic_notifications(user_id):
    """
    Ferma la schedulazione periodica per l'utente specificato.
    """
    name = f"periodic_notification_{user_id}"
    Schedule.objects.filter(name=name).delete()
