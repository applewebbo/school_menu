"""
Register the daily menu-notification schedules in Django-Q2 (#267).

The four cron rows that fire the menu pushes used to live only in the prod admin, added
by hand: delete one, or bring up a fresh environment, and that time slot silently never
runs and its subscribers get nothing. This command is versioned and idempotent
(``update_or_create``) and runs from ``entrypoint.sh`` on every deploy. Modelled on
``setup_ai_import_schedule``.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

# schedule name -> (task path, key into settings.NOTIFICATION_SCHEDULE_CRONS)
SCHEDULES = {
    "Menu Notification - Previous Day 6PM": (
        "notifications.tasks.send_previous_day_6pm_menu_notification",
        "previous_day_6pm",
    ),
    "Menu Notification - Same Day 9AM": (
        "notifications.tasks.send_same_day_9am_menu_notification",
        "same_day_9am",
    ),
    "Menu Notification - Same Day 12PM": (
        "notifications.tasks.send_same_day_12pm_menu_notification",
        "same_day_12pm",
    ),
    "Menu Notification - Same Day 6PM": (
        "notifications.tasks.send_same_day_6pm_menu_notification",
        "same_day_6pm",
    ),
}


class Command(BaseCommand):
    """Create, update or remove the Django-Q2 schedules for the daily menu pushes."""

    help = "Create or update the Django-Q2 schedules that send the daily menu notifications"

    def add_arguments(self, parser):
        parser.add_argument(
            "--remove",
            action="store_true",
            help="Remove the schedules instead of creating them",
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
        for name, (task_path, cron_key) in SCHEDULES.items():
            cron = settings.NOTIFICATION_SCHEDULE_CRONS[cron_key]

            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[DRY RUN] Would create/update: {name} ({cron})"
                    )
                )
                continue

            _, created = Schedule.objects.update_or_create(
                name=name,
                defaults={
                    "func": task_path,
                    "schedule_type": Schedule.CRON,
                    "cron": cron,
                    "repeats": -1,  # Run indefinitely
                },
            )
            verb = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"✓ {verb}: {name} ({cron})"))

        self._drop_strays(Schedule, dry_run)

    def _drop_strays(self, Schedule, dry_run):
        """
        Delete any other schedule that fires one of our four tasks.

        The prod rows were added by hand before this command existed, under names we
        don't control. Left in place next to the rows we just upserted, every slot
        would fire twice and every subscriber would get two notifications.
        """
        known_tasks = {task_path for task_path, _ in SCHEDULES.values()}
        strays = Schedule.objects.filter(func__in=known_tasks).exclude(
            name__in=list(SCHEDULES)
        )
        names = sorted(strays.values_list("name", flat=True))
        if not names:
            return

        joined = ", ".join(names)
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"[DRY RUN] Would remove stray schedule(s): {joined}"
                )
            )
            return

        strays.delete()
        self.stdout.write(self.style.WARNING(f"✓ Removed stray schedule(s): {joined}"))

    def _remove(self, Schedule, dry_run):
        schedules = Schedule.objects.filter(name__in=list(SCHEDULES))

        if dry_run:
            for schedule in schedules:
                self.stdout.write(
                    self.style.WARNING(f"[DRY RUN] Would delete: {schedule.name}")
                )
            return

        deleted = schedules.delete()[0]
        self.stdout.write(self.style.SUCCESS(f"✓ Removed {deleted} schedule(s)"))
