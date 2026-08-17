"""
Tests for the CSV import going through the editable review page (#254).

A valid CSV upload stages its rows on a `MenuImportDraft` and redirects to the very same
review page the AI import ends on; nothing is written until the user confirms.
"""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from test_plus.test import TestCase as TestPlusTestCase

from school_menu.models import (
    AnnualMeal,
    AuditLog,
    DetailedMeal,
    Meal,
    MenuImportDraft,
    School,
    SimpleMeal,
)
from tests.school_menu.factories import SchoolFactory
from tests.school_menu.import_review import confirm_import, staged_draft

pytestmark = pytest.mark.django_db

SIMPLE_CSV = """giorno,settimana,pranzo,spuntino,merenda
Lunedì,1,Pasta,Mela,Yogurt
Martedì,1,Riso,Banana,Crackers
"""
DETAILED_CSV = """giorno,settimana,primo,secondo,contorno,frutta,spuntino
Lunedì,1,Pasta,Pollo,Insalata,Mela,Yogurt
"""
ANNUAL_CSV = """data,primo,secondo,contorno,frutta,altro
01/01/2024,Pasta,Pollo,Insalata,Mela,Pane
02/01/2024,Riso,Pesce,Carote,Pera,Grissini
"""


def upload(content):
    return SimpleUploadedFile(
        "menu.csv", content.encode("utf-8"), content_type="text/csv"
    )


class TestWeeklyCsvReview(TestPlusTestCase):
    def setUp(self):
        self.user = self.make_user("owner@test.com")
        self.school = SchoolFactory(user=self.user, menu_type=School.Types.SIMPLE)

    def post_csv(self, content=SIMPLE_CSV):
        return self.client.post(
            reverse(
                "school_menu:upload_menu",
                kwargs={
                    "school_id": self.school.pk,
                    "meal_type": Meal.Types.STANDARD,
                },
            ),
            data={"file": upload(content), "season": School.Seasons.INVERNALE},
        )

    def test_a_valid_csv_is_staged_for_review_without_writing_anything(self):
        with self.login(self.user):
            response = self.post_csv()

        draft = staged_draft(self.school)
        assert draft.source == MenuImportDraft.Sources.CSV
        assert len(draft.rows) == 2
        assert not SimpleMeal.objects.filter(school=self.school).exists()
        # The upload form lives in an htmx modal, so leaving it needs an HX-Redirect.
        assert response.headers["HX-Redirect"] == reverse(
            "school_menu:menu_import_preview", args=[draft.pk]
        )

    def test_the_review_page_does_not_credit_the_assistant_for_a_csv(self):
        with self.login(self.user):
            self.post_csv()
            response = self.client.get(
                reverse(
                    "school_menu:menu_import_preview",
                    args=[staged_draft(self.school).pk],
                )
            )

        self.assertContains(response, "Pasta")
        self.assertNotContains(response, "letto dall'assistente")

    def test_confirming_imports_the_staged_rows(self):
        with self.login(self.user):
            self.post_csv()
            draft = staged_draft(self.school)
            response = confirm_import(self.client, self.school)

        draft.refresh_from_db()
        self.assertRedirects(
            response, reverse("school_menu:settings"), fetch_redirect_response=False
        )
        assert SimpleMeal.objects.filter(school=self.school).count() == 2
        assert draft.status == MenuImportDraft.Status.CONFIRMED

    def test_a_row_deselected_in_the_review_is_not_imported(self):
        with self.login(self.user):
            self.post_csv()
            confirm_import(self.client, self.school, deleted=(1,))

        menus = SimpleMeal.objects.filter(school=self.school).values_list(
            "menu", flat=True
        )
        assert list(menus) == ["Pasta"]

    def test_a_correction_made_in_the_review_is_what_gets_saved(self):
        with self.login(self.user):
            self.post_csv()
            confirm_import(
                self.client, self.school, overrides={0: {"pranzo": "Lasagne"}}
            )

        assert SimpleMeal.objects.filter(school=self.school, menu="Lasagne").exists()

    def test_the_audit_log_still_records_a_csv_import(self):
        with self.login(self.user):
            self.post_csv()
            confirm_import(self.client, self.school)

        audit = AuditLog.objects.get(action=AuditLog.Actions.MENU_UPLOAD)
        assert audit.changes["source"] == "csv"

    def test_a_second_upload_replaces_the_rows_waiting_for_review(self):
        """Otherwise the school piles up drafts and the user reviews a stale one."""
        with self.login(self.user):
            self.post_csv()
            self.post_csv(DETAILED_CSV.replace("primo", "pranzo"))

        assert (
            MenuImportDraft.objects.filter(
                school=self.school, status=MenuImportDraft.Status.READY
            ).count()
            == 1
        )

    def test_a_detailed_school_stages_detailed_rows(self):
        self.school.menu_type = School.Types.DETAILED
        self.school.save()

        with self.login(self.user):
            self.post_csv(DETAILED_CSV)
            assert staged_draft(self.school).kind == MenuImportDraft.Kinds.DETAILED
            confirm_import(self.client, self.school)

        assert DetailedMeal.objects.filter(school=self.school, first_course="Pasta")

    def test_an_invalid_csv_is_still_refused_without_staging_rows(self):
        with self.login(self.user):
            response = self.post_csv("giorno,settimana\nLunedì,1\n")

        assert not MenuImportDraft.objects.filter(
            status=MenuImportDraft.Status.READY
        ).exists()
        assert response.status_code == 200


class TestAnnualCsvReview(TestPlusTestCase):
    def setUp(self):
        self.user = self.make_user("owner@test.com")
        self.school = SchoolFactory(user=self.user, annual_menu=True)

    def post_csv(self, content=ANNUAL_CSV):
        return self.client.post(
            reverse(
                "school_menu:upload_annual_menu",
                kwargs={
                    "school_id": self.school.pk,
                    "meal_type": Meal.Types.STANDARD,
                },
            ),
            data={"file": upload(content)},
        )

    def test_an_annual_csv_is_staged_for_review(self):
        with self.login(self.user):
            response = self.post_csv()

        draft = staged_draft(self.school)
        assert draft.kind == MenuImportDraft.Kinds.ANNUAL
        assert draft.source == MenuImportDraft.Sources.CSV
        assert not AnnualMeal.objects.filter(school=self.school).exists()
        assert response.headers["HX-Redirect"] == reverse(
            "school_menu:menu_import_preview", args=[draft.pk]
        )

    def test_confirming_imports_the_annual_rows_with_their_dates(self):
        with self.login(self.user):
            self.post_csv()
            confirm_import(self.client, self.school)

        meals = AnnualMeal.objects.filter(school=self.school, is_active=True)
        assert meals.count() == 2
        assert meals.filter(menu__contains="Pasta").exists()

    def test_a_deselected_annual_row_is_not_imported(self):
        with self.login(self.user):
            self.post_csv()
            confirm_import(self.client, self.school, deleted=(1,))

        assert not AnnualMeal.objects.filter(
            school=self.school, is_active=True, menu__contains="Riso"
        ).exists()

    def test_the_annual_audit_log_still_records_a_csv_import(self):
        with self.login(self.user):
            self.post_csv()
            confirm_import(self.client, self.school)

        audit = AuditLog.objects.get(action=AuditLog.Actions.MENU_UPLOAD)
        assert audit.model_name == "AnnualMeal"
        assert audit.changes["source"] == "csv"
