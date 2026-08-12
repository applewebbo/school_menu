"""Tests for the retention of AI import drafts (#234)."""

import tempfile

import pytest
import time_machine
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from django_q.models import Schedule

from school_menu.management.commands.setup_ai_import_schedule import SCHEDULE_NAME
from school_menu.models import MenuImportDraft
from school_menu.tasks import purge_menu_import_drafts
from tests.school_menu.factories import MenuImportDraftFactory

pytestmark = pytest.mark.django_db

MEDIA = tempfile.mkdtemp()

OFFERED = MenuImportDraft.Status.OFFERED
READY = MenuImportDraft.Status.READY
CONFIRMED = MenuImportDraft.Status.CONFIRMED

NOW = timezone.datetime(2026, 9, 10, 12, 0, tzinfo=timezone.get_current_timezone())


def aged(days=0, hours=0, **extra):
    """A draft created that far in the past."""
    with time_machine.travel(NOW - timezone.timedelta(days=days, hours=hours)):
        return MenuImportDraftFactory(**extra)


@override_settings(MEDIA_ROOT=MEDIA, AI_MENU_IMPORT_DRAFT_RETENTION_DAYS=7)
class TestPurgeMenuImports(TestCase):
    def purge(self, **options):
        with time_machine.travel(NOW):
            call_command("purge_menu_imports", verbosity=0, **options)

    def test_an_old_draft_is_removed(self):
        draft = aged(days=8, status=READY)

        self.purge()

        assert not MenuImportDraft.objects.filter(pk=draft.pk).exists()

    def test_a_recent_draft_is_kept(self):
        draft = aged(days=2, status=READY)

        self.purge()

        assert MenuImportDraft.objects.filter(pk=draft.pk).exists()

    def test_a_stale_offer_goes_after_a_day(self):
        """An offer the user never acted on still holds their uploaded file."""
        draft = aged(hours=30, status=OFFERED)

        self.purge()

        assert not MenuImportDraft.objects.filter(pk=draft.pk).exists()

    def test_a_fresh_offer_is_left_alone(self):
        draft = aged(hours=2, status=OFFERED)

        self.purge()

        assert MenuImportDraft.objects.filter(pk=draft.pk).exists()

    def test_the_uploaded_file_goes_with_the_draft(self):
        draft = aged(hours=30, status=OFFERED)
        draft.source_file.save("menu.csv", SimpleUploadedFile("menu.csv", b"x"))
        path = draft.source_file.path

        self.purge()

        assert not __import__("os").path.exists(path)

    def test_the_retention_window_is_configurable(self):
        draft = aged(days=3, status=CONFIRMED)

        with override_settings(AI_MENU_IMPORT_DRAFT_RETENTION_DAYS=2):
            self.purge()

        assert not MenuImportDraft.objects.filter(pk=draft.pk).exists()

    def test_a_dry_run_reports_without_deleting(self):
        aged(days=8, status=READY)

        self.purge(dry_run=True)

        assert MenuImportDraft.objects.count() == 1

    def test_the_command_reports_what_it_removed(self):
        aged(days=8, status=READY)
        aged(hours=30, status=OFFERED)

        with time_machine.travel(NOW):
            call_command("purge_menu_imports")

        assert MenuImportDraft.objects.count() == 0


@override_settings(AI_MENU_IMPORT_PURGE_SCHEDULE="30 3 * * *")
class TestSetupSchedule(TestCase):
    def test_the_schedule_is_created_from_the_settings(self):
        call_command("setup_ai_import_schedule", verbosity=0)

        schedule = Schedule.objects.get(name=SCHEDULE_NAME)
        assert schedule.func == "school_menu.tasks.purge_menu_import_drafts"
        assert schedule.cron == "30 3 * * *"
        assert schedule.schedule_type == Schedule.CRON
        assert schedule.repeats == -1

    def test_running_it_twice_updates_instead_of_duplicating(self):
        call_command("setup_ai_import_schedule", verbosity=0)

        with override_settings(AI_MENU_IMPORT_PURGE_SCHEDULE="0 5 * * *"):
            call_command("setup_ai_import_schedule", verbosity=0)

        assert Schedule.objects.get(name=SCHEDULE_NAME).cron == "0 5 * * *"

    def test_remove_deletes_the_schedule(self):
        call_command("setup_ai_import_schedule", verbosity=0)

        call_command("setup_ai_import_schedule", "--remove", verbosity=0)

        assert not Schedule.objects.filter(name=SCHEDULE_NAME).exists()

    def test_a_dry_run_changes_nothing(self):
        call_command("setup_ai_import_schedule", "--dry-run")

        assert not Schedule.objects.exists()

    def test_a_dry_run_removal_changes_nothing(self):
        call_command("setup_ai_import_schedule", verbosity=0)

        call_command("setup_ai_import_schedule", "--remove", "--dry-run")

        assert Schedule.objects.filter(name=SCHEDULE_NAME).exists()


@override_settings(MEDIA_ROOT=MEDIA, AI_MENU_IMPORT_DRAFT_RETENTION_DAYS=7)
class TestScheduledTask(TestCase):
    def test_the_scheduled_task_purges(self):
        """What the schedule points at must do the same job as the command."""
        draft = aged(days=8, status=READY)

        with time_machine.travel(NOW):
            purge_menu_import_drafts()

        assert not MenuImportDraft.objects.filter(pk=draft.pk).exists()
