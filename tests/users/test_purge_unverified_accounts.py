"""Tests for the retention of never-verified accounts (#272)."""

import pytest
import time_machine
from allauth.account.models import EmailAddress
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from django_q.models import Schedule

from tests.school_menu.factories import SchoolFactory
from tests.users.factories import UserFactory
from users.management.commands.setup_unverified_account_purge_schedule import (
    SCHEDULE_NAME,
)
from users.models import User
from users.tasks import purge_unverified_accounts

pytestmark = pytest.mark.django_db

NOW = timezone.datetime(2026, 9, 12, 12, 0, tzinfo=timezone.get_current_timezone())


def aged(days=0, verified=False, **extra):
    """A user account created that far in the past, unverified unless told otherwise."""
    with time_machine.travel(NOW - timezone.timedelta(days=days)):
        user = UserFactory(**extra)
    EmailAddress.objects.filter(user=user).update(verified=verified)
    return user


@override_settings(UNVERIFIED_ACCOUNT_RETENTION_DAYS=7)
class TestPurgeUnverifiedAccounts(TestCase):
    def purge(self, **options):
        with time_machine.travel(NOW):
            call_command("purge_unverified_accounts", verbosity=0, **options)

    def test_an_old_unverified_account_is_removed(self):
        user = aged(days=8)

        self.purge()

        assert not User.objects.filter(pk=user.pk).exists()

    def test_a_recent_unverified_account_is_kept(self):
        user = aged(days=2)

        self.purge()

        assert User.objects.filter(pk=user.pk).exists()

    def test_an_old_verified_account_is_kept(self):
        user = aged(days=8, verified=True)

        self.purge()

        assert User.objects.filter(pk=user.pk).exists()

    def test_a_staff_account_is_never_removed(self):
        user = aged(days=8, is_staff=True)

        self.purge()

        assert User.objects.filter(pk=user.pk).exists()

    def test_a_superuser_account_is_never_removed(self):
        user = aged(days=8, is_superuser=True)

        self.purge()

        assert User.objects.filter(pk=user.pk).exists()

    def test_an_account_that_owns_a_school_is_never_removed(self):
        user = aged(days=8)
        SchoolFactory(user=user)

        self.purge()

        assert User.objects.filter(pk=user.pk).exists()

    def test_the_retention_window_is_configurable(self):
        user = aged(days=4)

        with override_settings(UNVERIFIED_ACCOUNT_RETENTION_DAYS=3):
            self.purge()

        assert not User.objects.filter(pk=user.pk).exists()

    def test_a_dry_run_reports_without_deleting(self):
        user = aged(days=8)

        self.purge(dry_run=True)

        assert User.objects.filter(pk=user.pk).exists()

    def test_the_command_reports_what_it_removed(self):
        aged(days=8)

        with time_machine.travel(NOW):
            call_command("purge_unverified_accounts")

        assert User.objects.count() == 0


@override_settings(UNVERIFIED_ACCOUNT_PURGE_SCHEDULE="0 4 * * *")
class TestSetupSchedule(TestCase):
    def test_the_schedule_is_created_from_the_settings(self):
        call_command("setup_unverified_account_purge_schedule", verbosity=0)

        schedule = Schedule.objects.get(name=SCHEDULE_NAME)
        assert schedule.func == "users.tasks.purge_unverified_accounts"
        assert schedule.cron == "0 4 * * *"
        assert schedule.schedule_type == Schedule.CRON
        assert schedule.repeats == -1

    def test_running_it_twice_updates_instead_of_duplicating(self):
        call_command("setup_unverified_account_purge_schedule", verbosity=0)

        with override_settings(UNVERIFIED_ACCOUNT_PURGE_SCHEDULE="0 5 * * *"):
            call_command("setup_unverified_account_purge_schedule", verbosity=0)

        assert Schedule.objects.get(name=SCHEDULE_NAME).cron == "0 5 * * *"

    def test_remove_deletes_the_schedule(self):
        call_command("setup_unverified_account_purge_schedule", verbosity=0)

        call_command("setup_unverified_account_purge_schedule", "--remove", verbosity=0)

        assert not Schedule.objects.filter(name=SCHEDULE_NAME).exists()

    def test_a_dry_run_changes_nothing(self):
        call_command("setup_unverified_account_purge_schedule", "--dry-run")

        assert not Schedule.objects.exists()

    def test_a_dry_run_removal_changes_nothing(self):
        call_command("setup_unverified_account_purge_schedule", verbosity=0)

        call_command("setup_unverified_account_purge_schedule", "--remove", "--dry-run")

        assert Schedule.objects.filter(name=SCHEDULE_NAME).exists()


@override_settings(UNVERIFIED_ACCOUNT_RETENTION_DAYS=7)
class TestScheduledTask(TestCase):
    def test_the_scheduled_task_purges(self):
        """What the schedule points at must do the same job as the command."""
        user = aged(days=8)

        with time_machine.travel(NOW):
            purge_unverified_accounts()

        assert not User.objects.filter(pk=user.pk).exists()
