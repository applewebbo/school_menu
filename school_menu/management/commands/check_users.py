from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from school_menu.tasks import _send_html_email

User = get_user_model()


class Command(BaseCommand):
    help = "Check if users have logged in at least once in 12 months. Send an email to the user if they haven't to notify them that their account will be deleted in 1 month. Delete users who haven't logged in in 13 months."

    def handle(self, *args, **options):
        now = timezone.now()
        one_year_ago = now - timedelta(days=365)
        thirteen_months_ago = now - timedelta(days=395)

        # Get total number of users
        total_users = User.objects.count()

        # Delete users who haven't logged in for 13 months
        users_to_delete = User.objects.filter(last_login__lte=thirteen_months_ago)
        deleted_count = users_to_delete.count()
        users_to_delete.delete()

        # Notify users who haven't logged in for 12 months
        users_to_notify = User.objects.filter(
            last_login__lte=one_year_ago, last_login__gt=thirteen_months_ago
        )
        notified_count = users_to_notify.count()
        for user in users_to_notify:
            _send_html_email(
                user.email,
                subject="Notifica di inattività",
                template="school_menu/emails/user_inactivity_notice.html",
                context={},
            )

        # Prepare and send result email
        self.stdout.write(
            self.style.SUCCESS(
                f"Controllo Utenti Inattivi su menuscolastico.it\n\n"
                f"Utenti totali: {total_users}\n"
                f"Utenti cancellati: {deleted_count}\n"
                f"Utenti avvisati: {notified_count}"
            )
        )

        _send_html_email(
            settings.ADMIN_EMAIL,
            subject="Controllo Utenti Inattivi su menuscolastico.it",
            template="school_menu/emails/inactive_users_report.html",
            context={
                "total_users": total_users,
                "deleted_count": deleted_count,
                "notified_count": notified_count,
            },
        )

        self.stdout.write(self.style.SUCCESS("Results email sent to admin."))
        self.stdout.write(self.style.SUCCESS("Results email sent to admin."))
