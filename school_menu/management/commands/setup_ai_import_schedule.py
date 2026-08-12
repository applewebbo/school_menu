"""
Management command to register the AI import retention schedule in Django-Q2 (#234).

Modelled on `setup_backup_schedules`: the schedule lives in the database, but the command
that creates it is versioned, so a fresh deploy does not depend on somebody remembering
to add it by hand in the admin. Running it again is safe — it updates the existing row.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

SCHEDULE_NAME = "AI Menu Import Purge"
TASK_PATH = "school_menu.tasks.purge_menu_import_drafts"


class Command(BaseCommand):
    """Create, update or remove the Django-Q2 schedule for the draft retention."""

    help = "Create or update the Django-Q2 schedule that purges AI menu import drafts"

    def add_arguments(self, parser):
        parser.add_argument(
            "--remove",
            action="store_true",
            help="Remove the schedule instead of creating it",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making changes",
        )

    def handle(self, *args, **options):
        try:
            from django_q.models import Schedule
        except ImportError:  # pragma: no cover - django-q2 is a hard dependency
            raise CommandError(
                "Django-Q2 is not installed. Please install it: pip install django-q2"
            ) from None

        if options["remove"]:
            self._remove(Schedule, options["dry_run"])
        else:
            self._create(Schedule, options["dry_run"])

    def _create(self, Schedule, dry_run):
        cron = settings.AI_MENU_IMPORT_PURGE_SCHEDULE

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"[DRY RUN] Would create/update: {SCHEDULE_NAME} ({cron})"
                )
            )
            return

        _, created = Schedule.objects.update_or_create(
            name=SCHEDULE_NAME,
            defaults={
                "func": TASK_PATH,
                "schedule_type": Schedule.CRON,
                "cron": cron,
                "repeats": -1,  # Run indefinitely
            },
        )
        verb = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"✓ {verb}: {SCHEDULE_NAME} ({cron})"))
        self.stdout.write(
            "\nThe schedule is now active. Ensure the Django-Q2 cluster is running:"
        )
        self.stdout.write("  python manage.py qcluster")

    def _remove(self, Schedule, dry_run):
        schedules = Schedule.objects.filter(name=SCHEDULE_NAME)

        if dry_run:
            for schedule in schedules:
                self.stdout.write(
                    self.style.WARNING(f"[DRY RUN] Would delete: {schedule.name}")
                )
            return

        deleted = schedules.delete()[0]
        self.stdout.write(self.style.SUCCESS(f"✓ Removed {deleted} schedule(s)"))
