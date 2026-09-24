from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.urls import reverse
from django_q.tasks import async_task

from notifications.models import Newsletter
from notifications.tasks import _build_newsletter_email


class Command(BaseCommand):
    help = "Send a saved Newsletter to its audience, or preview it to a single test address"

    def add_arguments(self, parser):
        parser.add_argument("newsletter_id", type=int)
        parser.add_argument(
            "--test",
            metavar="EMAIL",
            help=(
                "Send a one-off preview to this address only; does not touch "
                "recipients, counts, or the newsletter's status"
            ),
        )

    def handle(self, *args, **options):
        try:
            newsletter = Newsletter.objects.get(pk=options["newsletter_id"])
        except Newsletter.DoesNotExist as e:
            raise CommandError(
                f"Newsletter {options['newsletter_id']} not found"
            ) from e

        if options["test"]:
            self._send_test(newsletter, options["test"])
            return

        if newsletter.status in (Newsletter.Status.SENT, Newsletter.Status.SENDING):
            raise CommandError(
                f"'{newsletter.subject}' already sent or currently sending"
            )

        async_task("notifications.tasks.send_newsletter", newsletter.pk)
        newsletter.status = Newsletter.Status.SENDING
        newsletter.save()
        self.stdout.write(
            self.style.SUCCESS(f"Sending newsletter '{newsletter.subject}'...")
        )

    def _send_test(self, newsletter, test_email):
        # Placeholder unsubscribe link: a well-formed but unsigned token, so a click
        # lands on the "invalid link" page instead of actually unsubscribing whoever
        # happens to own that test address.
        unsubscribe_url = (
            f"{settings.SITE_URL}"
            f"{reverse('users:newsletter_unsubscribe', args=['anteprima'])}"
        )
        email = _build_newsletter_email(
            newsletter.subject, newsletter.body_html, test_email, unsubscribe_url
        )
        email.send()
        self.stdout.write(self.style.SUCCESS(f"Test newsletter sent to {test_email}"))
