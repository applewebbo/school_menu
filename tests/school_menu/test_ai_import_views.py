"""Tests for the AI import fallback, polling and editable preview (#234).

`Q_CLUSTER["sync"] = True` in test settings, so posting to the start view runs the whole
chain — quota, task, extraction — with only the network call replaced by a fake client.
"""

import tempfile

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from test_plus.test import TestCase as TestPlusTestCase

from school_menu.models import (
    AnnualMeal,
    Meal,
    MenuImportDraft,
    MenuImportQuota,
    School,
    SimpleMeal,
)
from tests.school_menu import ai_fakes
from tests.school_menu.factories import MenuImportDraftFactory, SchoolFactory

pytestmark = pytest.mark.django_db

FAKES = "tests.school_menu.ai_fakes."
MEDIA = tempfile.mkdtemp()

OFFERED = MenuImportDraft.Status.OFFERED
PENDING = MenuImportDraft.Status.PENDING
READY = MenuImportDraft.Status.READY
FAILED = MenuImportDraft.Status.FAILED
CONFIRMED = MenuImportDraft.Status.CONFIRMED

VALID_CSV = b"""giorno,settimana,pranzo,spuntino,merenda
Luned\xc3\xac,1,Pasta,Mela,Yogurt
"""
BROKEN_CSV = b"giorno,settimana\nLunedi,1,troppe,colonne\n"


def ai_settings(client_class="RecordingClient", **extra):
    ai_fakes.RecordingClient.text = ai_fakes.SIMPLE_PAYLOAD
    for candidate in vars(ai_fakes).values():
        if isinstance(candidate, type) and issubclass(
            candidate, ai_fakes.BaseFakeClient
        ):
            candidate.reset()
    options = {
        "AI_MENU_IMPORT_ENABLED": True,
        "AI_MENU_IMPORT_CLIENT": FAKES + client_class,
        "AI_MENU_IMPORT_MAX_RETRIES": 0,
        "AI_MENU_IMPORT_USER_DAILY_LIMIT": 5,
        "AI_MENU_IMPORT_GLOBAL_DAILY_LIMIT": 5,
        "MEDIA_ROOT": MEDIA,
    }
    options.update(extra)
    return override_settings(**options)


def upload(name, content):
    return SimpleUploadedFile(name, content, content_type="application/octet-stream")


class TestFallbackOffer(TestPlusTestCase):
    def url(self, school):
        return reverse(
            "school_menu:upload_menu",
            kwargs={"school_id": school.pk, "meal_type": Meal.Types.STANDARD},
        )

    def post(self, school, name, content, season=School.Seasons.INVERNALE):
        return self.client.post(
            self.url(school),
            data={"file": upload(name, content), "season": season},
        )

    def setUp(self):
        self.user = self.make_user("owner@test.com")
        self.school = SchoolFactory(user=self.user, menu_type=School.Types.SIMPLE)

    def test_a_valid_csv_never_creates_a_draft(self):
        """The classic path must stay free: no draft, no call, no quota."""
        with ai_settings(), self.login(self.user):
            response = self.post(self.school, "menu.csv", VALID_CSV)

        assert response.status_code == 204
        assert not MenuImportDraft.objects.exists()
        assert ai_fakes.RecordingClient.calls == []

    def test_an_unreadable_csv_offers_the_assistant_with_the_file_kept(self):
        with ai_settings(), self.login(self.user):
            response = self.post(self.school, "menu.csv", BROKEN_CSV)

        draft = MenuImportDraft.objects.get()
        assert draft.status == OFFERED
        assert draft.source_file
        assert draft.source_filename == "menu.csv"
        self.assertContains(response, "Interpreta con l'assistente")

    def test_a_pdf_is_offered_without_an_error_message(self):
        """A PDF is not a mistake: it is the whole point of the feature."""
        with ai_settings(), self.login(self.user):
            response = self.post(self.school, "menu.pdf", b"%PDF-1.4")

        assert MenuImportDraft.objects.get().status == OFFERED
        self.assertNotContains(response, "Il file CSV non è valido")

    def test_the_draft_kind_follows_the_school(self):
        self.school.menu_type = School.Types.DETAILED
        self.school.save()

        with ai_settings(), self.login(self.user):
            self.post(self.school, "menu.pdf", b"%PDF-1.4")

        assert MenuImportDraft.objects.get().kind == MenuImportDraft.Kinds.DETAILED

    def test_a_second_failed_upload_replaces_the_first_offer(self):
        """Otherwise every retry leaves another uploaded menu on disk."""
        with ai_settings(), self.login(self.user):
            self.post(self.school, "menu.pdf", b"%PDF-1.4")
            self.post(self.school, "altro.pdf", b"%PDF-1.4")

        draft = MenuImportDraft.objects.get()
        assert draft.source_filename == "altro.pdf"

    def test_without_the_assistant_a_pdf_is_simply_refused(self):
        with ai_settings(AI_MENU_IMPORT_ENABLED=False), self.login(self.user):
            response = self.post(self.school, "menu.pdf", b"%PDF-1.4")

        assert not MenuImportDraft.objects.exists()
        self.assertContains(response, "formato csv")

    def test_without_the_assistant_a_broken_csv_still_reports_the_error(self):
        with ai_settings(AI_MENU_IMPORT_ENABLED=False), self.login(self.user):
            response = self.post(self.school, "menu.csv", BROKEN_CSV)

        assert not MenuImportDraft.objects.exists()
        self.assertContains(response, "Il file CSV non è valido")

    def test_an_oversized_file_is_refused_by_the_form(self):
        with (
            ai_settings(AI_MENU_IMPORT_MAX_FILE_SIZE=10),
            self.login(self.user),
        ):
            response = self.post(self.school, "menu.pdf", b"%PDF-1.4 abbastanza lungo")

        assert not MenuImportDraft.objects.exists()
        self.assertContains(response, "non può superare")


class TestAnnualFallbackOffer(TestPlusTestCase):
    def setUp(self):
        self.user = self.make_user("owner@test.com")
        self.school = SchoolFactory(user=self.user, annual_menu=True)

    def test_an_annual_school_gets_an_annual_draft(self):
        url = reverse(
            "school_menu:upload_annual_menu",
            kwargs={"school_id": self.school.pk, "meal_type": Meal.Types.STANDARD},
        )

        with ai_settings(), self.login(self.user):
            self.client.post(url, data={"file": upload("menu.pdf", b"%PDF-1.4")})

        assert MenuImportDraft.objects.get().kind == MenuImportDraft.Kinds.ANNUAL


class TestStartAndStatus(TestPlusTestCase):
    def setUp(self):
        self.user = self.make_user("owner@test.com")
        self.school = SchoolFactory(user=self.user, menu_type=School.Types.SIMPLE)

    def make_offer(self, **extra):
        draft = MenuImportDraftFactory(
            school=self.school, status=OFFERED, source_filename="menu.csv", **extra
        )
        draft.source_file.save(
            "menu.csv", SimpleUploadedFile("menu.csv", VALID_CSV), save=True
        )
        return draft

    def start(self, draft):
        return self.client.post(reverse("school_menu:ai_import_start", args=[draft.pk]))

    def test_starting_runs_the_extraction_and_shows_the_preview_link(self):
        with ai_settings(), self.login(self.user):
            draft = self.make_offer()
            response = self.start(draft)

        draft.refresh_from_db()
        assert draft.status == READY
        self.assertContains(response, "Rivedi il menu")

    def test_a_full_quota_leaves_the_offer_in_place(self):
        with (
            ai_settings(AI_MENU_IMPORT_USER_DAILY_LIMIT=0),
            self.login(self.user),
        ):
            draft = self.make_offer()
            response = self.start(draft)

        draft.refresh_from_db()
        assert draft.status == OFFERED
        self.assertContains(response, "limite giornaliero")

    def test_a_draft_can_only_be_started_once(self):
        with ai_settings(), self.login(self.user):
            draft = self.make_offer()
            self.start(draft)
            response = self.start(draft)

        assert response.status_code == 404
        assert MenuImportQuota.objects.get(user=self.user).count == 1

    def test_a_failed_extraction_is_reported_to_the_user(self):
        with ai_settings("UpstreamErrorClient"), self.login(self.user):
            draft = self.make_offer()
            response = self.start(draft)

        draft.refresh_from_db()
        assert draft.status == FAILED
        self.assertContains(response, draft.error_message)

    def test_a_pending_draft_keeps_polling(self):
        with ai_settings(), self.login(self.user):
            draft = MenuImportDraftFactory(school=self.school, status=PENDING)
            response = self.client.get(
                reverse("school_menu:ai_import_status", args=[draft.pk])
            )

        self.assertContains(response, "hx-get")

    def test_a_finished_draft_stops_polling(self):
        with ai_settings(), self.login(self.user):
            draft = MenuImportDraftFactory(school=self.school, status=READY)
            response = self.client.get(
                reverse("school_menu:ai_import_status", args=[draft.pk])
            )

        self.assertNotContains(response, "hx-get")

    def test_another_user_cannot_see_a_draft(self):
        """Uploaded menus can carry third-party data: a wrong owner is a 404, not a leak."""
        stranger = self.make_user("stranger@test.com")

        with ai_settings(), self.login(stranger):
            draft = MenuImportDraftFactory(school=self.school, status=READY)
            response = self.client.get(
                reverse("school_menu:ai_import_status", args=[draft.pk])
            )

        assert response.status_code == 404

    def test_cancelling_drops_the_draft_and_its_file(self):
        with ai_settings(), self.login(self.user):
            draft = self.make_offer()
            path = draft.source_file.path
            response = self.client.post(
                reverse("school_menu:ai_import_cancel", args=[draft.pk])
            )

        assert response.status_code == 204
        assert not MenuImportDraft.objects.exists()
        assert not __import__("os").path.exists(path)


class TestPreviewAndConfirm(TestPlusTestCase):
    def setUp(self):
        self.user = self.make_user("owner@test.com")
        self.school = SchoolFactory(user=self.user, menu_type=School.Types.SIMPLE)

    def make_ready(self, rows=None, status=READY, **extra):
        return MenuImportDraftFactory(
            school=self.school,
            status=status,
            season=Meal.Seasons.INVERNALE,
            meal_type=Meal.Types.STANDARD,
            rows=rows
            or [
                {
                    "giorno": "Lunedì",
                    "settimana": 1,
                    "pranzo": "Pasta",
                    "spuntino": "Mela",
                    "merenda": "Yogurt",
                }
            ],
            **extra,
        )

    def payload(self, rows, deleted=()):
        data = {
            "form-TOTAL_FORMS": str(len(rows)),
            "form-INITIAL_FORMS": str(len(rows)),
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
        }
        for index, row in enumerate(rows):
            for key, value in row.items():
                data[f"form-{index}-{key}"] = value
            if index in deleted:
                data[f"form-{index}-DELETE"] = "on"
        return data

    def confirm(self, draft, data):
        return self.client.post(
            reverse("school_menu:ai_import_confirm", args=[draft.pk]), data=data
        )

    def test_the_preview_shows_the_rows_and_the_warnings(self):
        with self.login(self.user):
            draft = self.make_ready(warnings=["Riga 3: giorno non riconosciuto"])
            response = self.client.get(
                reverse("school_menu:ai_import_preview", args=[draft.pk])
            )

        self.assertContains(response, "Pasta")
        self.assertContains(response, "giorno non riconosciuto")

    def test_only_a_ready_draft_can_be_previewed(self):
        with self.login(self.user):
            draft = MenuImportDraftFactory(school=self.school, status=PENDING)
            response = self.client.get(
                reverse("school_menu:ai_import_preview", args=[draft.pk])
            )

        assert response.status_code == 404

    def test_confirming_writes_the_rows_and_closes_the_draft(self):
        with self.login(self.user):
            draft = self.make_ready()
            response = self.confirm(
                draft,
                self.payload(
                    [
                        {
                            "giorno": "Lunedì",
                            "settimana": "1",
                            "pranzo": "Pasta",
                            "spuntino": "Mela",
                            "merenda": "Yogurt",
                        }
                    ]
                ),
            )

        draft.refresh_from_db()
        assert response.status_code == 204
        assert draft.status == CONFIRMED
        assert SimpleMeal.objects.filter(school=self.school, menu="Pasta").exists()

    def test_a_correction_made_by_the_user_is_what_gets_saved(self):
        """The whole point of the preview: the AI proposes, the user decides."""
        with self.login(self.user):
            draft = self.make_ready()
            self.confirm(
                draft,
                self.payload(
                    [
                        {
                            "giorno": "Lunedì",
                            "settimana": "1",
                            "pranzo": "Risotto",
                            "spuntino": "",
                            "merenda": "",
                        }
                    ]
                ),
            )

        assert (
            SimpleMeal.objects.get(school=self.school, week=1, day=1).menu == "Risotto"
        )

    def test_a_deleted_row_is_not_imported(self):
        with self.login(self.user):
            draft = self.make_ready()
            self.confirm(
                draft,
                self.payload(
                    [
                        {
                            "giorno": "Lunedì",
                            "settimana": "1",
                            "pranzo": "Pasta",
                            "spuntino": "",
                            "merenda": "",
                        },
                        {
                            "giorno": "Martedì",
                            "settimana": "1",
                            "pranzo": "Riso",
                            "spuntino": "",
                            "merenda": "",
                        },
                    ],
                    deleted=[1],
                ),
            )

        assert not SimpleMeal.objects.filter(school=self.school, menu="Riso").exists()

    def test_deleting_every_row_leaves_nothing_to_import(self):
        with self.login(self.user):
            draft = self.make_ready()
            response = self.confirm(
                draft,
                self.payload(
                    [
                        {
                            "giorno": "Lunedì",
                            "settimana": "1",
                            "pranzo": "Pasta",
                            "spuntino": "",
                            "merenda": "",
                        }
                    ],
                    deleted=[0],
                ),
            )

        draft.refresh_from_db()
        assert draft.status == READY
        self.assertContains(response, "nessuna riga")

    def test_an_invalid_correction_comes_back_for_a_fix(self):
        with self.login(self.user):
            draft = self.make_ready()
            response = self.confirm(
                draft,
                self.payload(
                    [
                        {
                            "giorno": "Domenica",
                            "settimana": "1",
                            "pranzo": "Pasta",
                            "spuntino": "",
                            "merenda": "",
                        }
                    ]
                ),
            )

        draft.refresh_from_db()
        assert draft.status == READY
        assert not SimpleMeal.objects.filter(school=self.school).exists()
        self.assertContains(response, "Salva il menu")

    def test_a_menu_type_changed_since_the_extraction_is_caught(self):
        """The draft holds simple rows; the school now expects detailed ones."""
        with self.login(self.user):
            draft = self.make_ready()
            self.school.menu_type = School.Types.DETAILED
            self.school.save()
            response = self.confirm(
                draft,
                self.payload(
                    [
                        {
                            "giorno": "Lunedì",
                            "settimana": "1",
                            "pranzo": "Pasta",
                            "spuntino": "",
                            "merenda": "",
                        }
                    ]
                ),
            )

        draft.refresh_from_db()
        assert draft.status == READY
        assert not SimpleMeal.objects.filter(school=self.school).exists()
        self.assertContains(response, "Menu Semplice")

    def test_a_confirmed_draft_cannot_be_confirmed_again(self):
        with self.login(self.user):
            draft = self.make_ready(status=CONFIRMED)
            response = self.confirm(draft, self.payload([]))

        assert response.status_code == 404

    def test_another_user_cannot_confirm_a_draft(self):
        stranger = self.make_user("stranger@test.com")

        with self.login(stranger):
            draft = self.make_ready()
            response = self.confirm(draft, self.payload([]))

        assert response.status_code == 404


class TestAnnualPreview(TestPlusTestCase):
    def setUp(self):
        self.user = self.make_user("owner@test.com")
        self.school = SchoolFactory(user=self.user, annual_menu=True)

    def test_an_annual_draft_is_imported_with_its_dates(self):
        with self.login(self.user):
            draft = MenuImportDraftFactory(
                school=self.school,
                status=READY,
                kind=MenuImportDraft.Kinds.ANNUAL,
                meal_type=Meal.Types.STANDARD,
                rows=[
                    {
                        "data": "01/09/2026",
                        "primo": "Pasta",
                        "secondo": "Pollo",
                        "contorno": "Insalata",
                        "frutta": "Mela",
                        "altro": "",
                    }
                ],
            )
            response = self.client.post(
                reverse("school_menu:ai_import_confirm", args=[draft.pk]),
                data={
                    "form-TOTAL_FORMS": "1",
                    "form-INITIAL_FORMS": "1",
                    "form-MIN_NUM_FORMS": "0",
                    "form-MAX_NUM_FORMS": "1000",
                    "form-0-data": "01/09/2026",
                    "form-0-primo": "Pasta",
                    "form-0-secondo": "Pollo",
                    "form-0-contorno": "Insalata",
                    "form-0-frutta": "Mela",
                    "form-0-altro": "",
                },
            )

        assert response.status_code == 204
        assert AnnualMeal.objects.filter(school=self.school).exists()
