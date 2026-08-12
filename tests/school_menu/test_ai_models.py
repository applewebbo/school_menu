"""Tests for the AI menu import models (#234)."""

import os
from datetime import date
from tempfile import TemporaryDirectory

import pytest
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings

from school_menu.models import MenuImportDraft, MenuImportQuota, School
from tests.school_menu.factories import MenuImportDraftFactory, SchoolFactory
from tests.users.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestMenuImportDraft(TestCase):
    def test_defaults(self):
        draft = MenuImportDraftFactory()

        assert draft.status == MenuImportDraft.Status.OFFERED
        assert draft.rows == []
        assert draft.warnings == []
        assert draft.completed_at is None

    def test_str_mentions_school_and_status(self):
        school = SchoolFactory(name="Scuola Verdi")
        draft = MenuImportDraftFactory(school=school, user=school.user)

        assert "Scuola Verdi" in str(draft)
        assert draft.get_status_display() in str(draft)

    def test_kind_from_school_uses_menu_type_for_weekly(self):
        simple = SchoolFactory(menu_type=School.Types.SIMPLE, annual_menu=False)
        detailed = SchoolFactory(menu_type=School.Types.DETAILED, annual_menu=False)

        assert MenuImportDraft.kind_from_school(simple) == MenuImportDraft.Kinds.SIMPLE
        assert (
            MenuImportDraft.kind_from_school(detailed) == MenuImportDraft.Kinds.DETAILED
        )

    def test_kind_from_school_prefers_annual(self):
        """An annual school always imports annual rows, whatever its menu_type says."""
        school = SchoolFactory(menu_type=School.Types.SIMPLE, annual_menu=True)

        assert MenuImportDraft.kind_from_school(school) == MenuImportDraft.Kinds.ANNUAL

    def test_is_annual(self):
        annual = MenuImportDraftFactory(kind=MenuImportDraft.Kinds.ANNUAL)
        weekly = MenuImportDraftFactory(kind=MenuImportDraft.Kinds.SIMPLE)

        assert annual.is_annual is True
        assert weekly.is_annual is False

    def test_deleting_the_school_deletes_its_drafts(self):
        draft = MenuImportDraftFactory()

        draft.school.delete()

        assert not MenuImportDraft.objects.filter(pk=draft.pk).exists()

    def test_deleting_the_draft_removes_the_uploaded_file(self):
        """Uploaded menus may carry third-party data: no draft, no file."""
        with (
            TemporaryDirectory() as media_root,
            override_settings(MEDIA_ROOT=media_root),
        ):
            draft = MenuImportDraftFactory()
            draft.source_file.save(
                "menu.csv", ContentFile(b"giorno,settimana\n"), save=True
            )
            path = draft.source_file.path
            assert os.path.exists(path)

            draft.delete()

            assert not os.path.exists(path)

    def test_deleting_a_draft_without_a_file_is_harmless(self):
        draft = MenuImportDraftFactory()

        draft.delete()

        assert not MenuImportDraft.objects.filter(pk=draft.pk).exists()


class TestMenuImportQuota(TestCase):
    def test_user_and_date_are_unique_together(self):
        user = UserFactory()
        MenuImportQuota.objects.create(user=user, date=date(2026, 9, 1))

        with pytest.raises(IntegrityError), transaction.atomic():
            MenuImportQuota.objects.create(user=user, date=date(2026, 9, 1))

    def test_only_one_global_row_per_day(self):
        """user=None is the site-wide bucket; SQL would allow duplicate NULLs without
        a dedicated partial constraint."""
        MenuImportQuota.objects.create(user=None, date=date(2026, 9, 1))

        with pytest.raises(IntegrityError), transaction.atomic():
            MenuImportQuota.objects.create(user=None, date=date(2026, 9, 1))

    def test_same_user_on_different_days_is_allowed(self):
        user = UserFactory()
        MenuImportQuota.objects.create(user=user, date=date(2026, 9, 1))
        MenuImportQuota.objects.create(user=user, date=date(2026, 9, 2))

        assert MenuImportQuota.objects.filter(user=user).count() == 2

    def test_count_starts_at_zero(self):
        quota = MenuImportQuota.objects.create(user=UserFactory(), date=date.today())

        assert quota.count == 0

    def test_str_distinguishes_the_global_bucket(self):
        user = UserFactory()
        user_quota = MenuImportQuota.objects.create(user=user, date=date(2026, 9, 1))
        global_quota = MenuImportQuota.objects.create(user=None, date=date(2026, 9, 1))

        assert user.email in str(user_quota)
        assert "globale" in str(global_quota)
