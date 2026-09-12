from django.core.management import call_command


def purge_unverified_accounts():
    """
    Entry point for the scheduled retention run (#272).

    django-q schedules point at a dotted path, so the schedule targets this rather than
    the management command: the command stays the manual, inspectable way in (it has
    --dry-run), and the schedule keeps a stable path even if the command is renamed.
    """
    call_command("purge_unverified_accounts", verbosity=0)
