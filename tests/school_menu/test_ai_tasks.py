"""Tests for the background extraction task (#234).

In test settings `Q_CLUSTER["sync"] = True`, so `async_task` runs the task inline: these
tests exercise the real dispatch, the real task and the real extraction pipeline, with
only the network call replaced by a fake client.
"""

import os
import tempfile

import pytest
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.utils import timezone

from school_menu.models import Meal, MenuImportDraft, MenuImportQuota
from school_menu.services.ai_quota import QuotaExceeded
from school_menu.tasks import process_menu_import_draft, queue_menu_import
from tests.school_menu import ai_fakes
from tests.school_menu.factories import MenuImportDraftFactory

pytestmark = pytest.mark.django_db

FAKES = "tests.school_menu.ai_fakes."
MEDIA = tempfile.mkdtemp()

OFFERED = MenuImportDraft.Status.OFFERED
PENDING = MenuImportDraft.Status.PENDING
READY = MenuImportDraft.Status.READY
FAILED = MenuImportDraft.Status.FAILED
CONFIRMED = MenuImportDraft.Status.CONFIRMED


def ai_settings(client_class="RecordingClient", **extra):
    ai_fakes.RecordingClient.text = ai_fakes.SIMPLE_PAYLOAD
    for candidate in vars(ai_fakes).values():
        if isinstance(candidate, type) and issubclass(
            candidate, ai_fakes.BaseFakeClient
        ):
            candidate.reset()
    options = {
        "AI_MENU_IMPORT_CLIENT": FAKES + client_class,
        "AI_MENU_IMPORT_MAX_RETRIES": 0,
        "MEDIA_ROOT": MEDIA,
    }
    options.update(extra)
    return override_settings(**options)


def make_draft(status=PENDING, content=b"giorno;pranzo", filename="menu.csv", **extra):
    draft = MenuImportDraftFactory(status=status, source_filename=filename, **extra)
    draft.source_file.save(filename, ContentFile(content), save=True)
    return draft


class TestProcessDraft(TestCase):
    def test_a_readable_file_produces_rows(self):
        with ai_settings():
            draft = make_draft()

            process_menu_import_draft(draft.pk)

        draft.refresh_from_db()
        assert draft.status == READY
        assert draft.rows[0]["giorno"] == "Lunedì"
        assert draft.usage == ai_fakes.USAGE
        assert draft.completed_at is not None

    def test_warnings_are_stored_for_the_preview(self):
        with ai_settings():
            ai_fakes.RecordingClient.text = (
                '{"righe": [{"giorno": "Lunedì", "settimana": 1},'
                ' {"giorno": "Sabato", "settimana": 1}]}'
            )
            draft = make_draft()

            process_menu_import_draft(draft.pk)

        draft.refresh_from_db()
        assert draft.warnings

    def test_the_uploaded_file_is_deleted_once_it_has_been_read(self):
        """Menus carry third-party data: it must not sit on disk after the extraction."""
        with ai_settings():
            draft = make_draft()
            path = draft.source_file.path

            process_menu_import_draft(draft.pk)

        draft.refresh_from_db()
        assert not draft.source_file
        assert not os.path.exists(path)

    def test_the_file_is_deleted_even_when_the_extraction_fails(self):
        with ai_settings("UpstreamErrorClient"):
            draft = make_draft()

            process_menu_import_draft(draft.pk)

        draft.refresh_from_db()
        assert draft.status == FAILED
        assert not draft.source_file

    def test_the_season_of_the_draft_reaches_the_model(self):
        """The user picked it in the upload modal; a file holding both seasons needs it."""
        with ai_settings():
            draft = make_draft(season=Meal.Seasons.INVERNALE)

            process_menu_import_draft(draft.pk)

        instruction = ai_fakes.RecordingClient.calls[0]["system_instruction"]
        assert "Estrai soltanto il menu invernale" in instruction

    def test_the_kind_of_the_draft_drives_the_extraction(self):
        with ai_settings():
            ai_fakes.RecordingClient.text = ai_fakes.ANNUAL_PAYLOAD
            draft = make_draft(kind=MenuImportDraft.Kinds.ANNUAL)

            process_menu_import_draft(draft.pk)

        draft.refresh_from_db()
        assert draft.rows[0]["data"] == "01/09/2026"

    def test_a_draft_that_is_no_longer_pending_is_left_alone(self):
        """django-q can redeliver a task: reprocessing would overwrite the user's edits."""
        with ai_settings():
            draft = make_draft(status=CONFIRMED)

            process_menu_import_draft(draft.pk)

        draft.refresh_from_db()
        assert draft.status == CONFIRMED
        assert draft.rows == []
        assert ai_fakes.RecordingClient.calls == []

    def test_a_missing_draft_is_not_an_error(self):
        with ai_settings():
            process_menu_import_draft(999999)


class TestFailures(TestCase):
    def test_the_error_is_stored_with_a_message_for_the_user(self):
        with ai_settings("InvalidJsonClient"):
            draft = make_draft()

            process_menu_import_draft(draft.pk)

        draft.refresh_from_db()
        assert draft.status == FAILED
        assert draft.error_code == "INVALID_RESPONSE"
        assert draft.error_message

    def test_an_empty_result_is_reported_as_such(self):
        with ai_settings("EmptyClient"):
            draft = make_draft()

            process_menu_import_draft(draft.pk)

        draft.refresh_from_db()
        assert draft.error_code == "EMPTY"

    def test_an_unsupported_file_never_reaches_the_client(self):
        with ai_settings():
            draft = make_draft(filename="menu.docx")

            process_menu_import_draft(draft.pk)

        draft.refresh_from_db()
        assert draft.error_code == "UNSUPPORTED"
        assert ai_fakes.RecordingClient.calls == []

    def test_an_unexpected_exception_never_leaves_the_draft_pending(self):
        """Anything unforeseen must still end the draft, or the user polls forever."""
        with ai_settings("RecordingClient"):
            draft = make_draft()
            draft.source_file.delete(save=True)

            process_menu_import_draft(draft.pk)

        draft.refresh_from_db()
        assert draft.status == FAILED
        assert draft.error_code == "UNKNOWN"
        # Nothing the user can act on, so they get a code support can find in the logs.
        assert "ERR-" in draft.error_message

    def test_an_infrastructure_failure_gives_the_quota_slot_back(self):
        """Nothing was produced upstream, so the user should not pay for it."""
        with ai_settings("UpstreamErrorClient"):
            draft = make_draft()
            quota = MenuImportQuota.objects.create(
                user=draft.user, date=timezone.localdate(), count=1
            )

            process_menu_import_draft(draft.pk)

        draft.refresh_from_db()
        quota.refresh_from_db()
        assert draft.error_code == "UPSTREAM"
        assert quota.count == 0

    def test_a_produced_but_unusable_answer_keeps_costing_a_slot(self):
        """It burned tokens upstream: refunding it would make a bad file free to retry."""
        with ai_settings("InvalidJsonClient"):
            draft = make_draft()
            quota = MenuImportQuota.objects.create(
                user=draft.user, date=timezone.localdate(), count=1
            )

            process_menu_import_draft(draft.pk)

        quota.refresh_from_db()
        assert quota.count == 1


class TestQueue(TestCase):
    @override_settings(
        AI_MENU_IMPORT_USER_DAILY_LIMIT=2, AI_MENU_IMPORT_GLOBAL_DAILY_LIMIT=2
    )
    def test_queueing_charges_the_quota_and_runs_the_extraction(self):
        with ai_settings():
            draft = make_draft(status=OFFERED)

            queue_menu_import(draft)

        draft.refresh_from_db()
        assert draft.status == READY
        assert MenuImportQuota.objects.get(user=draft.user).count == 1

    @override_settings(
        AI_MENU_IMPORT_USER_DAILY_LIMIT=0, AI_MENU_IMPORT_GLOBAL_DAILY_LIMIT=5
    )
    def test_a_full_quota_leaves_the_draft_untouched(self):
        with ai_settings():
            draft = make_draft(status=OFFERED)

            with pytest.raises(QuotaExceeded):
                queue_menu_import(draft)

        draft.refresh_from_db()
        assert draft.status == OFFERED
        assert draft.source_file
        assert ai_fakes.RecordingClient.calls == []

    @override_settings(
        AI_MENU_IMPORT_USER_DAILY_LIMIT=2, AI_MENU_IMPORT_GLOBAL_DAILY_LIMIT=2
    )
    def test_the_task_id_is_stored_so_the_draft_can_be_followed(self):
        with ai_settings():
            draft = make_draft(status=OFFERED)

            queue_menu_import(draft)

        draft.refresh_from_db()
        assert draft.task_id
