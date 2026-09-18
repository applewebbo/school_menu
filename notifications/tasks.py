import json
import logging
from collections import Counter
from datetime import date, timedelta
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django_q.tasks import async_task
from pywebpush import WebPushException, webpush

from contacts.models import MenuReport
from notifications.models import (
    AnonymousMenuNotification,
    BroadcastNotification,
    DailyNotification,
    MonthlyDigest,
    NotificationDeliveryMarker,
)
from notifications.utils import build_menu_notification_payload
from school_menu.models import AnnualMeal, AuditLog, DetailedMeal, School, SimpleMeal

logger = logging.getLogger(__name__)

# Push endpoint is permanently gone (RFC 8030): prune the row. Deliberately NOT
# 401/403 — Apple returns 403 ExpiredProviderToken and FCM 401/403 for an auth /
# clock problem on our side, and pruning on those would wipe the whole table on a
# transient config issue (#269).
GONE_STATUS_CODES = frozenset({404, 410})
# Push service rejected our VAPID auth: our keys or server clock, never the
# subscription. Log loudly, keep the row (#269).
AUTH_REJECTED_STATUS_CODES = frozenset({401, 403})

# Comfortably longer than any plausible redelivery (bounded by Q_CLUSTER["retry"]), short
# enough not to matter if it's stale: the durable table backs it up on a cache miss (#270).
MARKER_CACHE_TTL_SECONDS = 60 * 60 * 24 * 2


def _marker_cache_key(
    subscription_endpoint: str, target_date: date, notification_time: str
) -> str:
    return f"notif-delivered:{subscription_endpoint}:{target_date.isoformat()}:{notification_time}"


def _already_delivered(
    subscription_endpoint: str, target_date: date, notification_time: str
) -> bool:
    """
    True if this subscriber already got this slot on this date (#270).

    Cache-first for speed (prod has Redis); falls back to the durable
    ``NotificationDeliveryMarker`` table so a cache eviction can't reopen the
    double-send window a redelivered task would otherwise exploit.
    """
    cache_key = _marker_cache_key(subscription_endpoint, target_date, notification_time)
    if cache.get(cache_key):
        return True
    exists = NotificationDeliveryMarker.objects.filter(
        subscription_endpoint=subscription_endpoint,
        target_date=target_date,
        notification_time=notification_time,
    ).exists()
    if exists:
        cache.set(cache_key, True, MARKER_CACHE_TTL_SECONDS)
    return exists


def _record_delivery(
    subscription_endpoint: str, target_date: date, notification_time: str
) -> None:
    """Mark a slot delivered so a redelivered run resumes instead of repeating it (#270)."""
    cache.set(
        _marker_cache_key(subscription_endpoint, target_date, notification_time),
        True,
        MARKER_CACHE_TTL_SECONDS,
    )
    NotificationDeliveryMarker.objects.get_or_create(
        subscription_endpoint=subscription_endpoint,
        target_date=target_date,
        notification_time=notification_time,
    )


def purge_notification_markers() -> None:
    """
    Scheduled task: prune delivery markers past their retention window (#270).

    Markers only matter for the few days a redelivery could plausibly land; kept
    indefinitely they'd just grow the table for no benefit.
    """
    cutoff = date.today() - timedelta(days=settings.NOTIFICATION_MARKER_RETENTION_DAYS)
    deleted, _ = NotificationDeliveryMarker.objects.filter(
        target_date__lt=cutoff
    ).delete()
    logger.info(
        f"[Notification] Pruned {deleted} delivery marker(s) older than {cutoff}."
    )


def _previous_month_range(today: date) -> tuple[date, date]:
    """Return (first day, last day) of the calendar month before ``today``."""
    period_end = today.replace(day=1) - timedelta(days=1)
    period_start = period_end.replace(day=1)
    return period_start, period_end


def send_monthly_admin_digest() -> None:
    """
    Scheduled task: email admins a summary of last month's site activity (#280).

    Counts new schools (from AuditLog, since School has no creation timestamp),
    menu reports received (plus send errors and feedback replies sent, tracked on
    MenuReport since #280), and new anonymous notification subscriptions. Always
    sends and records a MonthlyDigest row, even with all-zero counts, so a quiet
    month is still visible proof the job ran.
    """
    period_start, period_end = _previous_month_range(date.today())

    new_schools = AuditLog.objects.filter(
        action=AuditLog.Actions.SCHOOL_CREATE,
        timestamp__date__range=(period_start, period_end),
    ).count()

    reports = MenuReport.objects.filter(
        created_at__date__range=(period_start, period_end)
    )
    menu_reports = reports.count()
    report_errors = reports.exclude(notification_error="").count()
    feedback_sent = reports.filter(feedback_sent_at__isnull=False).count()

    new_subscriptions = AnonymousMenuNotification.objects.filter(
        created_at__date__range=(period_start, period_end)
    ).count()

    # Plain-text fallback for clients that don't render HTML.
    message = (
        f"Riepilogo attivita' dal {period_start:%d/%m/%Y} al {period_end:%d/%m/%Y}\n\n"
        f"Nuove scuole registrate: {new_schools}\n"
        f"Segnalazioni ricevute: {menu_reports}\n"
        f"Errori di invio segnalazioni: {report_errors}\n"
        f"Risposte a segnalazioni inviate: {feedback_sent}\n"
        f"Nuove iscrizioni alle notifiche: {new_subscriptions}\n"
    )
    html_message = render_to_string(
        "notifications/emails/monthly_digest.html",
        {
            "period_start": period_start,
            "period_end": period_end,
            "new_schools": new_schools,
            "menu_reports": menu_reports,
            "report_errors": report_errors,
            "feedback_sent": feedback_sent,
            "new_subscriptions": new_subscriptions,
        },
    )
    email = EmailMultiAlternatives(
        subject=f"Riepilogo mensile attivita' - {period_start:%m/%Y}",
        body=message,
        from_email=None,
        to=[settings.ADMIN_EMAIL],
    )
    email.attach_alternative(html_message, "text/html")
    email.send()

    MonthlyDigest.objects.create(
        period_start=period_start,
        period_end=period_end,
        new_schools=new_schools,
        menu_reports=menu_reports,
        report_errors=report_errors,
        feedback_sent=feedback_sent,
        new_subscriptions=new_subscriptions,
    )
    logger.info(f"[MonthlyDigest] Sent digest for {period_start} - {period_end}.")


def send_test_notification(
    subscription_info: dict[str, Any], payload: dict[str, Any]
) -> str:
    """
    Send a single push notification.

    Args:
        subscription_info: Web push subscription information (endpoint, keys)
        payload: Notification payload with title, body, icon, etc.

    Returns:
        "sent" on success, "pruned" if the subscription was permanently gone and
        has been deleted.

    Raises:
        WebPushException: on a transient push failure (5xx, rate limit, network)
        Exception: for any unexpected error

    Note:
        - A TTL, request timeout and ``Urgency: high`` header are sent so the push
          service holds the message for a dozing device instead of dropping it (#265).
        - Permanently invalid subscriptions (see ``GONE_STATUS_CODES``) are deleted.
    """
    try:
        webpush(
            subscription_info=subscription_info,
            data=json.dumps(payload),
            vapid_private_key=settings.WEBPUSH_SETTINGS["VAPID_PRIVATE_KEY"],
            vapid_claims={
                "sub": f"mailto:{settings.WEBPUSH_SETTINGS['VAPID_ADMIN_EMAIL']}"
            },
            ttl=settings.WEBPUSH_TTL_SECONDS,
            timeout=settings.WEBPUSH_REQUEST_TIMEOUT,
            headers={"Urgency": "high"},
        )
        logger.info("Notifica di prova inviata con successo.")
    except WebPushException as e:
        status_code = getattr(e.response, "status_code", None)
        if status_code in GONE_STATUS_CODES:
            response_text = getattr(e.response, "text", "")
            logger.info(
                f"Subscription gone ({status_code}): {response_text}. Deleting..."
            )
            AnonymousMenuNotification.objects.filter(
                subscription_info=subscription_info
            ).delete()
            return "pruned"
        if status_code in AUTH_REJECTED_STATUS_CODES:
            logger.error(
                f"Push auth rejected ({status_code}): check VAPID keys and server "
                f"clock. Subscription kept. {e}"
            )
            raise
        logger.error(f"Errore durante l'invio della notifica: {e}")
        raise
    except Exception as e:
        logger.error(f"Errore inatteso durante l'invio della notifica: {e}")
        raise
    logger.info("notifica di prova inviata")
    return "sent"


def _deliver(subscription: AnonymousMenuNotification, payload: dict[str, Any]) -> str:
    """
    Send one menu notification, swallowing every error.

    A single failing or hanging endpoint must never abort the rest of the batch
    (#265), so this returns a status string and never raises:
    "sent", "pruned" (subscription deleted) or "failed" (transient error, logged).
    """
    try:
        return send_test_notification(subscription.subscription_info, payload)
    except Exception as e:
        logger.error(
            f"[Notification] Delivery failed for subscription {subscription.pk} "
            f"(school '{subscription.school.name}'): {e}"
        )
        return "failed"


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

    results: Counter[str] = Counter()

    for subscription in subscriptions:
        school = subscription.school
        target_date = today + timedelta(days=1) if is_previous_day else today
        endpoint = subscription.subscription_endpoint

        # Resume support (#270): a redelivered run reprocesses from the top, so skip
        # anyone this slot already reached for this date. Subscriptions predating the
        # endpoint hash (endpoint is nullable) can't be deduped and are always sent.
        if endpoint and _already_delivered(endpoint, target_date, notification_time):
            logger.info(
                f"[Notification Debug] Skipping subscription {subscription.pk} "
                f"for {school.name}: already delivered for {target_date} "
                f"slot {notification_time} (redelivery)."
            )
            continue

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

        payload = build_menu_notification_payload(
            school, is_previous_day, meal_type=subscription.meal_type
        )

        if payload is None:
            logger.info(
                f"Skipping notification for {school.name} on {target_date}: no meals found."
            )
            continue

        payload["icon"] = "/static/img/notification-bell.png"
        payload["url"] = school.get_absolute_url()
        # Per-school, per-day tag: a redelivered batch replaces the notification
        # instead of stacking a duplicate (matters most on iOS) (#269).
        payload["tag"] = f"menu-{school.id}-{target_date.isoformat()}"
        status = _deliver(subscription, payload)
        # Only a confirmed outcome earns the marker: a "failed" (transient) delivery
        # must stay unmarked so the next run, or redelivery, retries that subscriber.
        if endpoint and status in ("sent", "pruned"):
            _record_delivery(endpoint, target_date, notification_time)
        results[status] += 1

    logger.info(
        f"[Notification] Slot {notification_time}: "
        f"{results['sent']} sent, {results['failed']} failed, "
        f"{results['pruned']} pruned."
    )
    # Audit row: with Q_CLUSTER catch_up off, this is the only proof the slot ran (#268).
    DailyNotification.objects.create(
        notification_time=notification_time,
        sent_count=results["sent"],
        failed_count=results["failed"],
        pruned_count=results["pruned"],
    )
    logger.info(f"Notifiche per l'orario {notification_time} inviate.")


def _queue_menu_notifications(notification_time: str) -> None:
    """
    Re-queue the fan-out as its own async_task with a longer timeout (#266).

    The Django-Q2 Schedule fires one of the thin wrappers below; each does nothing but
    enqueue this, so the per-subscriber loop in ``_send_menu_notifications`` runs on
    ``NOTIFICATION_TASK_TIMEOUT`` instead of the cluster's 60s default and cannot be
    killed and redelivered mid-batch.
    """
    async_task(
        "notifications.tasks._send_menu_notifications",
        notification_time,
        timeout=settings.NOTIFICATION_TASK_TIMEOUT,
    )


def send_previous_day_6pm_menu_notification() -> None:
    """Scheduled task: queue tomorrow's 6 PM menu notifications."""
    _queue_menu_notifications(AnonymousMenuNotification.PREVIOUS_DAY_6PM)


def send_same_day_9am_menu_notification() -> None:
    """Scheduled task: queue today's 9 AM menu notifications."""
    _queue_menu_notifications(AnonymousMenuNotification.SAME_DAY_9AM)


def send_same_day_12pm_menu_notification() -> None:
    """Scheduled task: queue today's 12 PM menu notifications."""
    _queue_menu_notifications(AnonymousMenuNotification.SAME_DAY_12PM)


def send_same_day_6pm_menu_notification() -> None:
    """Scheduled task: queue today's 6 PM menu notifications."""
    _queue_menu_notifications(AnonymousMenuNotification.SAME_DAY_6PM)


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
