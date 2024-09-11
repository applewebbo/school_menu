from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

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
            send_mail(
                "Notifica di inattività",
                "Abbiamo notato che non hai effettuato nessuna attività sul nostro sito negli ultimi 12 mesi.\n Se intendi continuare ad utilizzare i nostri servizi, ti preghiamo di effettuare l'accesso al tuo account entro il prossimo mese.\n\nSe non intendi continuare ad utilizzare i nostri servizi, puoi cancellare il tuo account in qualsiasi momento.\n\nGrazie per aver utilizzato i nostri servizi.",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )

        # Prepare and send result email
        result_message = f"Controllo Utenti Inattivi su menu.webbografico.com\n\nUtenti totali: {total_users}\nUtenti cancellati: {deleted_count}\nUtenti avvisati: {notified_count}"
        self.stdout.write(self.style.SUCCESS(result_message))

        send_mail(
            "Controllo Utenti Inattivi su menu.webbografico.com",
            result_message,
            settings.DEFAULT_FROM_EMAIL,
            [settings.ADMIN_EMAIL],
            fail_silently=False,
        )

        self.stdout.write(self.style.SUCCESS("Results email sent to admin."))
        self.stdout.write(self.style.SUCCESS("Results email sent to admin."))
