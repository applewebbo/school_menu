import json
import logging
from datetime import date, timedelta

from django.conf import settings
from pywebpush import WebPushException, webpush

from notifications.models import AnonymousMenuNotification
from notifications.utils import build_menu_notification_payload
from school_menu.models import AnnualMeal, DetailedMeal, SimpleMeal

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


def _has_menu_for_date(school, target_date):
    """
    Checks if a menu exists for a specific school on a given date.
    """
    day_of_week = target_date.weekday() + 1  # Monday is 1, Sunday is 7

    # Check for AnnualMeal first
    if AnnualMeal.objects.filter(
        school=school, date=target_date, is_active=True
    ).exists():
        return True

    # Check for SimpleMeal or DetailedMeal
    if school.menu_type == "S":
        return SimpleMeal.objects.filter(school=school, day=day_of_week).exists()
    else:
        return DetailedMeal.objects.filter(school=school, day=day_of_week).exists()


def _is_school_in_session(school, target_date):
    """
    Checks if the school is in session on a given date based on start/end month/day.
    """
    start_month = school.start_month
    start_day = school.start_day
    end_month = school.end_month
    end_day = school.end_day

    # Create comparable tuples for dates (month, day)
    today_tuple = (target_date.month, target_date.day)
    start_tuple = (start_month, start_day)
    end_tuple = (end_month, end_day)

    # Case 1: School year is within the same calendar year (e.g., Feb to June)
    if start_tuple <= end_tuple:
        return start_tuple <= today_tuple <= end_tuple
    # Case 2: School year spans across calendar years (e.g., Sept to June)
    else:
        return today_tuple >= start_tuple or today_tuple <= end_tuple


def _send_menu_notifications(notification_time):
    """
    Sends menu notifications for a specific time.
    """
    logger.info(f"Invio notifiche per l'orario: {notification_time}...")
    subscriptions = AnonymousMenuNotification.objects.filter(
        daily_notification=True, notification_time=notification_time
    )
    today = date.today()
    is_previous_day = notification_time == AnonymousMenuNotification.PREVIOUS_DAY_6PM

    for subscription in subscriptions:
        school = subscription.school
        target_date = today + timedelta(days=1) if is_previous_day else today

        # Check if school is in session
        if settings.ENABLE_SCHOOL_DATE_CHECK and not _is_school_in_session(
            school, target_date
        ):
            logger.info(
                f"Skipping notification for {school.name} on {target_date.strftime('%A')} "
                "as the school is not in session."
            )
            continue

        day_of_week = target_date.weekday()

        # Skip notifications on weekends if there's no specific menu
        # For PREVIOUS_DAY_6PM, check is on Friday (4) for Saturday's menu, and Saturday (5) for Sunday's menu
        # For SAME_DAY, check is on Saturday (5) and Sunday (6)
        is_weekend_check = (is_previous_day and day_of_week in [4, 5]) or (
            not is_previous_day and day_of_week in [5, 6]
        )

        if is_weekend_check and not _has_menu_for_date(school, target_date):
            logger.info(
                f"Skipping notification for {school.name} on {target_date.strftime('%A')} "
                "as there is no menu."
            )
            continue

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
