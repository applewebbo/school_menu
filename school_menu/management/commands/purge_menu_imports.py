"""
Retention for the AI menu import drafts (#234).

Two rules, for two reasons. Finished drafts are kept for a few days so a user can come
back to a preview, then removed because their rows are a copy of a menu that already
lives in the database. Offers the user never acted on go after a day: they still hold the
uploaded file, which may carry third-party data and has no purpose once the moment has
passed.

Deleting the row deletes the file with it, through the post_delete signal on the model.
"""

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from school_menu.models import MenuImportDraft

STALE_OFFER_HOURS = 24


class Command(BaseCommand):
    help = "Remove expired AI menu import drafts and the files they hold"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be removed without removing it",
        )

    def handle(self, *args, **options):
        now = timezone.now()
        retention = timezone.timedelta(
            days=settings.AI_MENU_IMPORT_DRAFT_RETENTION_DAYS
        )
        expired = Q(created_at__lt=now - retention)
        stale_offer = Q(
            status=MenuImportDraft.Status.OFFERED,
            created_at__lt=now - timezone.timedelta(hours=STALE_OFFER_HOURS),
        )
        drafts = MenuImportDraft.objects.filter(expired | stale_offer)

        count = drafts.count()
        if options["dry_run"]:
            self.stdout.write(f"{count} bozze da eliminare (dry run)")
            return

        # The post_delete receiver on the model removes each uploaded file: because a
        # receiver is connected, Django cannot take its fast-delete path and the signal
        # fires for every row.
        drafts.delete()
        self.stdout.write(self.style.SUCCESS(f"{count} bozze eliminate"))
