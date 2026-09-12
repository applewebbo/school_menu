"""
Retention for never-verified accounts (#272).

`ACCOUNT_EMAIL_VERIFICATION = "mandatory"` already stops an unverified user from ever
logging in, but django-allauth still creates the `User` row on signup POST before
verification happens — so a flood of bot signups with invented, unreachable addresses
still accumulates real rows in the database. Give a genuine user a reasonable window to
find the confirmation email (the window is also shown on the verification-sent page),
then remove accounts nobody ever confirmed.

Deleting the user cascades to their (unverified) EmailAddress rows. Staff, superusers
and anyone who somehow already owns a School are excluded as a safety net, even though
the mandatory verification gate means none of them should be reachable here in practice.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Remove accounts that never verified their email within the retention window"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be removed without removing it",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        cutoff = timezone.now() - timezone.timedelta(
            days=settings.UNVERIFIED_ACCOUNT_RETENTION_DAYS
        )
        candidates = User.objects.filter(
            date_joined__lt=cutoff,
            is_staff=False,
            is_superuser=False,
            school__isnull=True,
        ).exclude(emailaddress__verified=True)

        count = candidates.count()
        if options["dry_run"]:
            self.stdout.write(f"{count} account non verificati da eliminare (dry run)")
            return

        candidates.delete()
        self.stdout.write(
            self.style.SUCCESS(f"{count} account non verificati eliminati")
        )
