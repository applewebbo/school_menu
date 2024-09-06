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
        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {deleted_count} users who have not logged in for a year."
            )
        )

        # Notify users who haven't logged in for 11 months
        users_to_notify = User.objects.filter(
            last_login__lte=eleven_months_ago, last_login__gt=one_year_ago
        )
        for user in users_to_notify:
            send_mail(
                "Account Inactivity Notice",
                "Abbiamo notato che non hai eseguito il login nel nostro sito negli ultimi 11 mesi. Se non hai ancora eseguito il login, ti invitiamo a farlo entro il prossimo mese, altrimenti il tuo account verrà eliminato. Grazie per aver utilizzato il nostro sito!",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Notified {users_to_notify.count()} users about account inactivity."
            )
        )
