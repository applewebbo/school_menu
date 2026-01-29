"""Notification status utilities for school menu management."""

from django.shortcuts import get_object_or_404

from notifications.models import AnonymousMenuNotification
from school_menu.models import School


def get_notifications_status(pk: int | None, school: School) -> bool:
    """
    Check if daily notifications are enabled for a given subscription.

    Args:
        pk: AnonymousMenuNotification primary key (can be None)
        school: School instance to verify against

    Returns:
        True if notification exists, belongs to the school, and has
        daily_notification enabled. False otherwise.

    Raises:
        Http404: If pk is provided but notification not found
    """
    if pk:
        notification = get_object_or_404(AnonymousMenuNotification, pk=pk)
        if notification.school == school and notification.daily_notification:
            return True
    return False
