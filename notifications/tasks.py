import json
import logging
from datetime import date, timedelta
from typing import Any

from django.conf import settings
from django.utils import timezone
from pywebpush import WebPushException, webpush

from notifications.models import AnonymousMenuNotification, BroadcastNotification
from notifications.utils import build_menu_notification_payload
from school_menu.models import AnnualMeal, DetailedMeal, School, SimpleMeal

logger = logging.getLogger(__name__)


def send_test_notification(
    subscription_info: dict[str, Any], payload: dict[str, Any]
) -> None:
    """
    Send a test push notification asynchronously.

    Args:
        subscription_info: Web push subscription information (endpoint, keys)
        payload: Notification payload with title, body, icon, etc.

    Raises:
        WebPushException: If the push notification fails to send
        Exception: For any unexpected errors

    Note:
        Automatically deletes expired or invalid subscriptions (404/410 responses)
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


def _has_menu_for_date(school: School, target_date: date) -> bool:
    """
    Check if a menu exists for a specific school on a given date.

    Args:
        school: School instance to check
        target_date: Date to check for menu availability

    Returns:
        True if an active menu exists for the date, False otherwise

    Note:
        Checks AnnualMeal first, then SimpleMeal/DetailedMeal based on school type
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


def _is_school_in_session(school: School, target_date: date) -> bool:
    """
    Check if the school is in session on a given date.

    Uses the school's start_month/start_day and end_month/end_day to determine
    if the target date falls within the academic year.

    Args:
        school: School instance with session date configuration
        target_date: Date to check

    Returns:
        True if school is in session on target date, False otherwise

    Note:
        Handles academic years that span calendar years (e.g., Sept to June)
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


def _send_menu_notifications(notification_time: str) -> None:
    """
    Send menu notifications to all subscribers for a specific time slot.

    Args:
        notification_time: Notification time code (e.g., 'PD6', 'SD9', 'SD12', 'SD6')

    Note:
        - Skips notifications if school is not in session (when ENABLE_SCHOOL_DATE_CHECK=True)
        - Sends notifications for next day if notification_time is PREVIOUS_DAY_6PM
        - Automatically cleans up invalid subscriptions
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


def send_previous_day_6pm_menu_notification() -> None:
    """
    Send menu notifications for the next day at 6 PM.

    Scheduled task for Django-Q2 to send tomorrow's menu notifications.
    """
    _send_menu_notifications(AnonymousMenuNotification.PREVIOUS_DAY_6PM)


def send_same_day_9am_menu_notification() -> None:
    """
    Send menu notifications for the current day at 9 AM.

    Scheduled task for Django-Q2 to send today's menu notifications.
    """
    _send_menu_notifications(AnonymousMenuNotification.SAME_DAY_9AM)


def send_same_day_12pm_menu_notification() -> None:
    """
    Send menu notifications for the current day at 12 PM.

    Scheduled task for Django-Q2 to send today's menu notifications.
    """
    _send_menu_notifications(AnonymousMenuNotification.SAME_DAY_12PM)


def send_same_day_6pm_menu_notification() -> None:
    """
    Send menu notifications for the current day at 6 PM.

    Scheduled task for Django-Q2 to send today's menu notifications.
    """
    _send_menu_notifications(AnonymousMenuNotification.SAME_DAY_6PM)


def send_broadcast_notification(broadcast_pk: int) -> None:
    """
    Send a broadcast notification to all matching subscriptions.

    Args:
        broadcast_pk: Primary key of the BroadcastNotification to send

    Note:
        - Updates broadcast record with sent_at, status, and recipient counts
        - Marks as FAILED if broadcast not found or if most sends fail
        - Marks as SENT even if no recipients (for audit trail)
        - Automatically cleans up invalid subscriptions

    Raises:
        Exception: Re-raises unexpected errors for Django-Q2 logging
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
