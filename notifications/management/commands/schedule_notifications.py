from django.core.management.base import BaseCommand

from notifications.tasks import schedule_daily_menu_notification


class Command(BaseCommand):
    help = "Schedule daily menu notifications"

    def handle(self, *args, **options):
        schedule_daily_menu_notification()
        self.stdout.write(
            self.style.SUCCESS("Successfully scheduled daily menu notifications")
        )
