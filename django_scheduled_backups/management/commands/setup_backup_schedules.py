"""Management command to setup backup schedules in Django-Q2."""

from django.core.management.base import BaseCommand, CommandError

from django_scheduled_backups.conf import (
    get_database_backup_config,
    get_media_backup_config,
    is_enabled,
)


class Command(BaseCommand):
    """Setup Django-Q2 schedules for database and media backups."""

    help = "Create or update Django-Q2 schedules for automated backups"

    def add_arguments(self, parser):
        parser.add_argument(
            "--remove",
            action="store_true",
            help="Remove existing backup schedules instead of creating them",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making changes",
        )

    def handle(self, *args, **options):
        """Execute the command."""
        if not is_enabled():
            raise CommandError(
                "Backup system is disabled in settings (SCHEDULED_BACKUPS['ENABLED'] = False)"
            )

        try:
            from django_q.models import Schedule
        except ImportError:
            raise CommandError(
                "Django-Q2 is not installed. Please install it: pip install django-q2"
            ) from None

        remove = options["remove"]
        dry_run = options["dry_run"]

        if remove:
            self._remove_schedules(Schedule, dry_run)
        else:
            self._create_schedules(Schedule, dry_run)

    def _create_schedules(self, Schedule, dry_run):
        """Create or update backup schedules."""
        database_config = get_database_backup_config()
        media_config = get_media_backup_config()

        created_count = 0
        updated_count = 0

        # Database backup schedule
        if database_config.get("enabled", True):
            schedule = database_config.get("schedule", "0 2 * * *")

            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[DRY RUN] Would create/update: Database Backup Schedule ({schedule})"
                    )
                )
            else:
                obj, created = Schedule.objects.update_or_create(
                    name="Database Backup",
                    defaults={
                        "func": "django_scheduled_backups.tasks.scheduled_database_backup",
                        "schedule_type": Schedule.CRON,
                        "cron": schedule,
                        "repeats": -1,  # Run indefinitely
                    },
                )
                if created:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✓ Created: Database Backup Schedule ({schedule})"
                        )
                    )
                else:
                    updated_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✓ Updated: Database Backup Schedule ({schedule})"
                        )
                    )

        # Media backup schedule
        if media_config.get("enabled", False):
            schedule = media_config.get("schedule", "0 3 * * 0")

            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[DRY RUN] Would create/update: Media Backup Schedule ({schedule})"
                    )
                )
            else:
                obj, created = Schedule.objects.update_or_create(
                    name="Media Backup",
                    defaults={
                        "func": "django_scheduled_backups.tasks.scheduled_media_backup",
                        "schedule_type": Schedule.CRON,
                        "cron": schedule,
                        "repeats": -1,  # Run indefinitely
                    },
                )
                if created:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✓ Created: Media Backup Schedule ({schedule})"
                        )
                    )
                else:
                    updated_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✓ Updated: Media Backup Schedule ({schedule})"
                        )
                    )

        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nSummary: {created_count} created, {updated_count} updated"
                )
            )
            self.stdout.write(
                "\nSchedules are now active. Ensure Django-Q2 cluster is running:"
            )
            self.stdout.write("  python manage.py qcluster")

    def _remove_schedules(self, Schedule, dry_run):
        """Remove backup schedules."""
        schedules = Schedule.objects.filter(
            name__in=["Database Backup", "Media Backup"]
        )

        if dry_run:
            for schedule in schedules:
                self.stdout.write(
                    self.style.WARNING(f"[DRY RUN] Would delete: {schedule.name}")
                )
        else:
            deleted = schedules.delete()[0]
            self.stdout.write(
                self.style.SUCCESS(f"✓ Removed {deleted} backup schedule(s)")
            )
