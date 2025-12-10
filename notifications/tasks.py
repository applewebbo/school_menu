import json
import logging
from datetime import date, timedelta

from django.conf import settings
from django.utils import timezone
from pywebpush import WebPushException, webpush

from notifications.models import AnonymousMenuNotification, BroadcastNotification
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

    logger.info(
        f"[Notification Debug] Starting notification batch: "
        f"notification_time={notification_time}, today={today}, "
        f"is_previous_day={is_previous_day}, total_subscriptions={subscriptions.count()}"
    )

    for subscription in subscriptions:
        school = subscription.school
        target_date = today + timedelta(days=1) if is_previous_day else today

        logger.info(
            f"[Notification Debug] Processing subscription for school '{school.name}' "
            f"(ID={school.id}), target_date={target_date}, "
            f"weekday={target_date.strftime('%A')}"
        )

        # Check if school is in session
        if settings.ENABLE_SCHOOL_DATE_CHECK and not _is_school_in_session(
            school, target_date
        ):
            logger.info(
                f"Skipping notification for {school.name} on {target_date.strftime('%A')} "
                "as the school is not in session."
            )
            continue

        payload = build_menu_notification_payload(school, is_previous_day)

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


def send_broadcast_notification(broadcast_pk):
    """
    Send a broadcast notification to all matching subscriptions
    """
    try:
        broadcast = BroadcastNotification.objects.get(pk=broadcast_pk)
    except BroadcastNotification.DoesNotExist:
        logger.error(f"BroadcastNotification {broadcast_pk} not found")
        return

    try:
        # Build base query
        subscriptions = AnonymousMenuNotification.objects.filter(
            daily_notification=True
        )

        # Filter by schools if specified
        if broadcast.target_schools.exists():
            subscriptions = subscriptions.filter(
                school__in=broadcast.target_schools.all()
            )

        # Build payload
        payload = {
            "head": broadcast.title,
            "body": broadcast.message,
            "icon": "/static/img/notification-bell.png",
        }

        if broadcast.url:
            payload["url"] = broadcast.url
        else:
            payload["url"] = "/"

        # Send to all matching subscriptions
        success_count = 0
        failure_count = 0
        total_recipients = subscriptions.count()

        for subscription in subscriptions:
            try:
                send_test_notification(subscription.subscription_info, payload)
                success_count += 1
            except Exception as e:
                logger.error(
                    f"Failed to send broadcast to subscription {subscription.pk}: {e}"
                )
                failure_count += 1

        # Determine final status based on results (Option B)
        if total_recipients == 0:
            # No recipients found - still mark as SENT for audit trail
            final_status = BroadcastNotification.Status.SENT
        elif success_count == 0:
            # All sends failed
            final_status = BroadcastNotification.Status.FAILED
        elif failure_count > success_count:
            # More failures than successes
            final_status = BroadcastNotification.Status.FAILED
        else:
            # Success (even with some failures)
            final_status = BroadcastNotification.Status.SENT

        # Update broadcast record
        broadcast.sent_at = timezone.now()
        broadcast.status = final_status
        broadcast.recipients_count = total_recipients
        broadcast.success_count = success_count
        broadcast.failure_count = failure_count
        broadcast.save()

        logger.info(
            f"Broadcast '{broadcast.title}' completed with status {final_status}: "
            f"{success_count} success, {failure_count} failures"
        )

    except Exception as e:
        # Catch-all for unexpected errors during task execution
        logger.error(f"Unexpected error in send_broadcast_notification: {e}")

        # Mark as FAILED so admin knows something went wrong
        broadcast.status = BroadcastNotification.Status.FAILED
        broadcast.save()

        # Re-raise so Django-Q can log it
        raise
