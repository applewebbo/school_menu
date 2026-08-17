"""
Tests for the paginated import review page (#255).

The server keeps rendering every row: pagination is what the page shows, so the assertions
are on the pager the context describes and on the fact that a confirm still carries rows
the user never scrolled to. How the pages look is verified visually, per the project rule.
"""

from datetime import date, timedelta

import pytest
from django.urls import reverse
from test_plus.test import TestCase as TestPlusTestCase

from school_menu.ai.normalise import WEEKDAYS
from school_menu.menu_import_views import PAGE_SIZE
from school_menu.models import AnnualMeal, Meal, MenuImportDraft, School, SimpleMeal
from tests.school_menu.factories import MenuImportDraftFactory, SchoolFactory
from tests.school_menu.import_review import confirm_payload

pytestmark = pytest.mark.django_db

READY = MenuImportDraft.Status.READY


def annual_rows(count, start=date(2026, 9, 1)):
    return [
        {
            "data": (start + timedelta(days=offset)).strftime("%d/%m/%Y"),
            "primo": f"Primo {offset}",
            "secondo": "Pollo",
            "contorno": "Insalata",
            "frutta": "Mela",
            "altro": "",
        }
        for offset in range(count)
    ]


def weekly_rows(count):
    return [
        {
            "giorno": WEEKDAYS[index % len(WEEKDAYS)],
            "settimana": index // len(WEEKDAYS) + 1,
            "pranzo": f"Pranzo {index}",
            "spuntino": "Mela",
            "merenda": "Yogurt",
        }
        for index in range(count)
    ]


class TestPager(TestPlusTestCase):
    def setUp(self):
        self.user = self.make_user("owner@test.com")

    def preview(self, draft):
        return self.client.get(
            reverse("school_menu:menu_import_preview", args=[draft.pk])
        )

    def annual_draft(self, count):
        school = SchoolFactory(user=self.user, annual_menu=True)
        return MenuImportDraftFactory(
            school=school,
            status=READY,
            kind=MenuImportDraft.Kinds.ANNUAL,
            meal_type=Meal.Types.STANDARD,
            rows=annual_rows(count),
        )

    def test_a_weekly_menu_never_gets_a_pager(self):
        """Four weeks of five days is exactly the page size, so the pager stays away."""
        school = SchoolFactory(user=self.user, menu_type=School.Types.SIMPLE)
        draft = MenuImportDraftFactory(
            school=school,
            status=READY,
            kind=MenuImportDraft.Kinds.SIMPLE,
            meal_type=Meal.Types.STANDARD,
            rows=weekly_rows(PAGE_SIZE),
        )

        with self.login(self.user):
            response = self.preview(draft)

        assert response.context["pages"] == []
        assert len(response.context["preview_rows"]) == PAGE_SIZE

    def test_an_annual_menu_is_split_into_pages_of_twenty(self):
        draft = self.annual_draft(45)

        with self.login(self.user):
            pages = self.preview(draft).context["pages"]

        assert [page["number"] for page in pages] == [1, 2, 3]
        assert [(page["first"], page["last"]) for page in pages] == [
            (1, 20),
            (21, 40),
            (41, 45),
        ]

    def test_every_row_knows_the_page_it_belongs_to(self):
        draft = self.annual_draft(45)

        with self.login(self.user):
            rows = self.preview(draft).context["preview_rows"]

        assert rows[0]["page"] == 1
        assert rows[PAGE_SIZE]["page"] == 2
        assert rows[-1]["page"] == 3

    def test_the_first_page_is_the_one_shown_when_nothing_is_wrong(self):
        draft = self.annual_draft(45)

        with self.login(self.user):
            response = self.preview(draft)

        assert response.context["current_page"] == 1
        assert response.context["total_rows"] == 45


class TestPagesWithErrors(TestPlusTestCase):
    def setUp(self):
        self.user = self.make_user("owner@test.com")
        self.school = SchoolFactory(user=self.user, annual_menu=True)
        self.draft = MenuImportDraftFactory(
            school=self.school,
            status=READY,
            kind=MenuImportDraft.Kinds.ANNUAL,
            meal_type=Meal.Types.STANDARD,
            rows=annual_rows(45),
        )

    def confirm(self, **kwargs):
        return self.client.post(
            reverse("school_menu:menu_import_confirm", args=[self.draft.pk]),
            data=confirm_payload(self.draft, **kwargs),
        )

    def test_a_failed_confirm_opens_on_the_page_holding_the_error(self):
        """Otherwise the user reads "correggi gli errori" with no error in sight."""
        with self.login(self.user):
            response = self.confirm(overrides={25: {"data": "non è una data"}})

        assert response.status_code == 200
        assert response.context["current_page"] == 2
        assert [page["number"] for page in response.context["pages"] if page["errors"]]
        assert not AnnualMeal.objects.filter(school=self.school).exists()

    def test_only_the_pages_carrying_an_error_are_marked(self):
        with self.login(self.user):
            response = self.confirm(
                overrides={0: {"data": "sbagliata"}, 42: {"data": "sbagliata"}}
            )

        marked = [
            page["number"] for page in response.context["pages"] if page["errors"]
        ]
        assert marked == [1, 3]

    def test_confirming_imports_the_rows_on_pages_never_visited(self):
        with self.login(self.user):
            self.confirm()

        assert (
            AnnualMeal.objects.filter(school=self.school, is_active=True).count() == 45
        )

    def test_a_row_deselected_on_the_last_page_is_left_out(self):
        with self.login(self.user):
            self.confirm(deleted=(44,))

        assert not AnnualMeal.objects.filter(
            school=self.school, is_active=True, menu__contains="Primo 44"
        ).exists()
        assert AnnualMeal.objects.filter(
            school=self.school, is_active=True, menu__contains="Primo 43"
        ).exists()


class TestWeeklyPagerIsUnaffected(TestPlusTestCase):
    def test_a_short_weekly_confirm_still_imports_everything(self):
        user = self.make_user("owner@test.com")
        school = SchoolFactory(user=user, menu_type=School.Types.SIMPLE)
        draft = MenuImportDraftFactory(
            school=school,
            status=READY,
            kind=MenuImportDraft.Kinds.SIMPLE,
            meal_type=Meal.Types.STANDARD,
            season=Meal.Seasons.INVERNALE,
            rows=weekly_rows(5),
        )

        with self.login(user):
            self.client.post(
                reverse("school_menu:menu_import_confirm", args=[draft.pk]),
                data=confirm_payload(draft),
            )

        assert SimpleMeal.objects.filter(school=school).count() == 5
