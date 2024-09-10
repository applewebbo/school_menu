from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

User = get_user_model()


class Command(BaseCommand):
    help = "Check if users have logged in at least once in 11 months. Send an email to the user if they haven't to notify them that their account will be deleted in 1 month. Delete users who haven't logged in in 1 year."

    def handle(self, *args, **options):
        now = timezone.now()
        eleven_months_ago = now - timedelta(days=330)
        one_year_ago = now - timedelta(days=365)

        # Delete users who haven't logged in for a year
        users_to_delete = User.objects.filter(last_login__lte=one_year_ago)
        deleted_count = users_to_delete.count()
        users_to_delete.delete()

        # Notify users who haven't logged in for 11 months
        users_to_notify = User.objects.filter(
            last_login__lte=eleven_months_ago, last_login__gt=one_year_ago
        )
        notified_count = users_to_notify.count()
        for user in users_to_notify:
            send_mail(
                "Account Inactivity Notice",
                "Your account has been inactive for 11 months. It will be deleted in 1 month if you do not log in.",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )

        # Prepare and send result email
        result_message = f"Controllo Utenti Inattivi su menu.webbografico.com\n\nUtenti cancellati: {deleted_count}\nUtenti avvisati: {notified_count}"
        self.stdout.write(self.style.SUCCESS(result_message))

        send_mail(
            "Controllo Utenti Inattivi su menu.webbografico.com",
            result_message,
            settings.DEFAULT_FROM_EMAIL,
            [settings.ADMIN_EMAIL],  # Assuming you have an ADMIN_EMAIL setting
            fail_silently=False,
        )

        self.stdout.write(self.style.SUCCESS("Results email sent to admin."))
