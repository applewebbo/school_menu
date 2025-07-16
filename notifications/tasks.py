import json
import logging

from django.conf import settings
from django.utils import timezone
from django_q.models import Schedule
from pywebpush import WebPushException, webpush

from notifications.models import AnonymousMenuNotification
from school_menu.models import School
from school_menu.utils import (
    calculate_week,
    get_current_date,
    get_meals,
    get_meals_for_annual_menu,
    get_season,
)

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


def send_daily_menu_notification():
    """
    Invia una notifica con il menu del giorno a tutti gli iscritti.
    """
    logger.info("Invio notifiche giornaliere del menu...")
    subscriptions = AnonymousMenuNotification.objects.all()
    for subscription in subscriptions:
        school = subscription.school
        if school.annual_menu:
            _, meals_for_today = get_meals_for_annual_menu(school)
        else:
            current_week, day = get_current_date()
            season = get_season(school)
            week = calculate_week(current_week, school.week_bias)
            _, meals_for_today = get_meals(school, season, week, day)

        if meals_for_today:
            meal = meals_for_today.first()
            body_parts = []
            if school.annual_menu:
                body_parts.append(f"Pranzo: {meal.menu}")
                body_parts.append(f"Spuntino: {meal.snack}")
            elif school.menu_type == School.Types.SIMPLE:
                body_parts.append(f"Spuntino: {meal.morning_snack}")
                body_parts.append(f"Pranzo: {meal.menu}")
                body_parts.append(f"Merenda: {meal.afternoon_snack}")
            else:
                body_parts.append(f"Primo: {meal.first_course}")
                body_parts.append(f"Secondo: {meal.second_course}")
                body_parts.append(f"Contorno: {meal.side_dish}")

            body = "\n".join(body_parts)
            payload = {
                "head": f"Menu di oggi per {school.name}",
                "body": body,
                "icon": "/static/img/notification-bell.png",
                "url": school.get_absolute_url(),
            }
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
