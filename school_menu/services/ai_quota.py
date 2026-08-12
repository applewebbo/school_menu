"""
Daily quota for the AI menu import (#234).

The Gemini key belongs to the site, so a single account must not be able to drain the
shared free-tier allowance. Two buckets are enforced on every request: one per user and
one site-wide (stored with user=None).
"""

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from school_menu.models import MenuImportQuota

USER_SCOPE = "user"
GLOBAL_SCOPE = "global"

MESSAGES = {
    USER_SCOPE: (
        "Hai raggiunto il limite giornaliero di importazioni con l'AI. "
        "Riprova domani oppure carica un file CSV."
    ),
    GLOBAL_SCOPE: (
        "Il limite giornaliero di importazioni con l'AI del sito è stato raggiunto. "
        "Riprova domani oppure carica un file CSV."
    ),
}


class QuotaExceeded(Exception):
    """Raised when either the per-user or the site-wide daily cap is reached."""

    def __init__(self, scope):
        self.scope = scope
        super().__init__(MESSAGES[scope])


def _buckets():
    """The buckets to charge, in order: the user's own, then the site-wide one."""
    return (
        (USER_SCOPE, settings.AI_MENU_IMPORT_USER_DAILY_LIMIT),
        (GLOBAL_SCOPE, settings.AI_MENU_IMPORT_GLOBAL_DAILY_LIMIT),
    )


def _owner(scope, user):
    return user if scope == USER_SCOPE else None


@transaction.atomic
def consume(user):
    """
    Charge one AI import to the user and to the site, or raise QuotaExceeded.

    The increment is a conditional UPDATE (`WHERE count < limit`) rather than a
    read-then-write, so two concurrent requests cannot both take the last slot. Being
    inside a transaction, a failure on the site-wide bucket also rolls back the user
    increment: nobody loses a slot to a cap they did not hit.
    """
    today = timezone.localdate()
    for scope, limit in _buckets():
        row, _ = MenuImportQuota.objects.get_or_create(
            user=_owner(scope, user), date=today
        )
        updated = MenuImportQuota.objects.filter(pk=row.pk, count__lt=limit).update(
            count=F("count") + 1
        )
        if not updated:
            raise QuotaExceeded(scope)


def refund(user):
    """
    Give back a slot after an infrastructure failure (timeout, upstream error).

    Never call this for a response that was actually produced, such as invalid JSON or
    an empty result: those consumed tokens upstream and must still count.
    """
    today = timezone.localdate()
    for scope, _limit in _buckets():
        MenuImportQuota.objects.filter(
            user=_owner(scope, user), date=today, count__gt=0
        ).update(count=F("count") - 1)


def remaining(user):
    """How many imports the user can still start today, site-wide cap included."""
    today = timezone.localdate()
    left = []
    for scope, limit in _buckets():
        used = (
            MenuImportQuota.objects.filter(user=_owner(scope, user), date=today)
            .values_list("count", flat=True)
            .first()
            or 0
        )
        left.append(limit - used)
    return max(min(left), 0)
