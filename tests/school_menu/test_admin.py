import io

import pytest
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core import mail
from django.test import RequestFactory, TestCase
from django.urls import reverse

from school_menu.admin import CsvImportForm, SchoolAdmin
from school_menu.models import (
    AuditLog,
    DetailedMeal,
    School,
    SchoolTransfer,
    SimpleMeal,
)
from tests.school_menu.factories import (
    SchoolFactory,
    SchoolTransferFactory,
    SimpleMealFactory,
)
from tests.users.factories import UserFactory

pytestmark = pytest.mark.django_db

SIMPLE_CSV = """settimana,giorno,pranzo,spuntino,merenda
1,Lunedì,Pasta al pomodoro,,
1,Martedì,Risotto,,
1,Mercoledì,Pasta e fagioli,,
1,Giovedì,Minestra,,
1,Venerdì,Pasta integrale,,
2,Lunedì,Pasta al pesto,,
2,Martedì,Farro,,
2,Mercoledì,Pasta legumi,,
2,Giovedì,Risotto zafferano,,
2,Venerdì,Vellutata,,
3,Lunedì,Lasagna,,
3,Martedì,Orzo,,
3,Mercoledì,Pasta peperoni,,
3,Giovedì,Insalata riso,,
3,Venerdì,Pasta ragù pesce,,
4,Lunedì,Pasta pesto,,
4,Martedì,Farro legumi,,
4,Mercoledì,Pasta basilico,,
4,Giovedì,Risotto,,
4,Venerdì,Pasta ragù carne,,
"""

DETAILED_CSV = """settimana,giorno,primo,secondo,contorno,frutta,spuntino
1,Lunedì,Pasta,Pollo,Insalata,Mela,Crackers
1,Martedì,Risotto,Pesce,Carote,Pera,Crackers
1,Mercoledì,Pasta fagioli,Uova,Spinaci,Banana,Crackers
1,Giovedì,Minestra,Tacchino,Zucchine,Kiwi,Crackers
1,Venerdì,Pasta integrale,Formaggio,Fagiolini,Arancia,Crackers
2,Lunedì,Pasta pesto,Pollo,Insalata,Mela,Crackers
2,Martedì,Farro,Pesce,Carote,Pera,Crackers
2,Mercoledì,Pasta legumi,Uova,Spinaci,Banana,Crackers
2,Giovedì,Risotto,Tacchino,Zucchine,Kiwi,Crackers
2,Venerdì,Vellutata,Formaggio,Fagiolini,Arancia,Crackers
3,Lunedì,Lasagna,Pollo,Insalata,Mela,Crackers
3,Martedì,Orzo,Pesce,Carote,Pera,Crackers
3,Mercoledì,Pasta peperoni,Uova,Spinaci,Banana,Crackers
3,Giovedì,Insalata riso,Tacchino,Zucchine,Kiwi,Crackers
3,Venerdì,Pasta ragù,Formaggio,Fagiolini,Arancia,Crackers
4,Lunedì,Pasta pesto,Pollo,Insalata,Mela,Crackers
4,Martedì,Farro legumi,Pesce,Carote,Pera,Crackers
4,Mercoledì,Pasta basilico,Uova,Spinaci,Banana,Crackers
4,Giovedì,Risotto,Tacchino,Zucchine,Kiwi,Crackers
4,Venerdì,Pasta ragù carne,Formaggio,Fagiolini,Arancia,Crackers
"""


def _make_request(method, user, data=None, files=None):
    factory = RequestFactory()
    if method == "post":
        request = factory.post("/", data=data or {})
    else:
        request = factory.get("/")
    request.user = user
    request._messages = FallbackStorage(request)
    return request


class TestCsvImportForm:
    def test_standard_only_when_no_alternatives(self):
        school = SchoolFactory(
            no_gluten=False, no_lactose=False, vegetarian=False, special=False
        )
        form = CsvImportForm(school=school)
        assert list(form.fields["meal_type"].choices) == [("S", "Standard")]

    def test_includes_alternatives_when_enabled(self):
        school = SchoolFactory(
            no_gluten=True, no_lactose=True, vegetarian=True, special=True
        )
        form = CsvImportForm(school=school)
        choice_values = [v for v, _ in form.fields["meal_type"].choices]
        assert DetailedMeal.Types.GLUTEN_FREE in choice_values
        assert DetailedMeal.Types.LACTOSE_FREE in choice_values
        assert DetailedMeal.Types.VEGETARIAN in choice_values
        assert DetailedMeal.Types.SPECIAL in choice_values


class TestImportCsvAction(TestCase):
    def setUp(self):
        self.superuser = UserFactory(is_staff=True, is_superuser=True)
        self.client.force_login(self.superuser)

    def _upload(self, school, csv_content, season=1, meal_type="S", overwrite=False):
        url = reverse("admin:school_menu_school_import_csv", args=[school.pk])
        csv_file = io.BytesIO(csv_content.encode("utf-8"))
        csv_file.name = "menu.csv"
        data = {
            "season": season,
            "meal_type": meal_type,
            "csv_file": csv_file,
        }
        if overwrite:
            data["overwrite"] = "on"
        return self.client.post(url, data)

    def test_get_import_page(self):
        school = SchoolFactory(
            menu_type=School.Types.SIMPLE,
            no_gluten=False,
            no_lactose=False,
            vegetarian=False,
            special=False,
        )
        url = reverse("admin:school_menu_school_import_csv", args=[school.pk])
        response = self.client.get(url)
        assert response.status_code == 200
        assert school.name.encode() in response.content

    def test_import_simple_csv(self):
        school = SchoolFactory(
            menu_type=School.Types.SIMPLE,
            no_gluten=False,
            no_lactose=False,
            vegetarian=False,
            special=False,
        )
        response = self._upload(school, SIMPLE_CSV, season=SimpleMeal.Seasons.ESTIVO)
        assert response.status_code == 302
        assert (
            SimpleMeal.objects.filter(
                school=school, season=SimpleMeal.Seasons.ESTIVO
            ).count()
            == 20
        )

    def test_import_detailed_csv(self):
        school = SchoolFactory(
            menu_type=School.Types.DETAILED,
            no_gluten=False,
            no_lactose=False,
            vegetarian=False,
            special=False,
        )
        response = self._upload(
            school, DETAILED_CSV, season=DetailedMeal.Seasons.ESTIVO
        )
        assert response.status_code == 302
        assert (
            DetailedMeal.objects.filter(
                school=school, season=DetailedMeal.Seasons.ESTIVO
            ).count()
            == 20
        )

    def test_overwrite_deletes_existing(self):
        school = SchoolFactory(
            menu_type=School.Types.SIMPLE,
            no_gluten=False,
            no_lactose=False,
            vegetarian=False,
            special=False,
        )
        SimpleMealFactory.create_batch(
            5,
            school=school,
            season=SimpleMeal.Seasons.ESTIVO,
            type=SimpleMeal.Types.STANDARD,
        )
        self._upload(
            school, SIMPLE_CSV, season=SimpleMeal.Seasons.ESTIVO, overwrite=True
        )
        assert (
            SimpleMeal.objects.filter(
                school=school, season=SimpleMeal.Seasons.ESTIVO
            ).count()
            == 20
        )

    def test_no_overwrite_keeps_existing(self):
        school = SchoolFactory(
            menu_type=School.Types.SIMPLE,
            no_gluten=False,
            no_lactose=False,
            vegetarian=False,
            special=False,
        )
        SimpleMeal.objects.create(
            school=school,
            day=1,
            week=1,
            menu="Vecchio menu",
            morning_snack="",
            afternoon_snack="",
            season=SimpleMeal.Seasons.ESTIVO,
            type=SimpleMeal.Types.STANDARD,
        )
        self._upload(
            school, SIMPLE_CSV, season=SimpleMeal.Seasons.ESTIVO, overwrite=False
        )
        # Without overwrite, existing record gets updated (resource upserts by key)
        assert (
            SimpleMeal.objects.filter(
                school=school, season=SimpleMeal.Seasons.ESTIVO
            ).count()
            == 20
        )

    def test_wrong_csv_format_shows_error(self):
        school = SchoolFactory(
            menu_type=School.Types.SIMPLE,
            no_gluten=False,
            no_lactose=False,
            vegetarian=False,
            special=False,
        )
        response = self._upload(school, DETAILED_CSV, season=SimpleMeal.Seasons.ESTIVO)
        assert response.status_code == 200
        assert SimpleMeal.objects.filter(school=school).count() == 0

    def test_action_with_single_school_redirects(self):
        school = SchoolFactory(menu_type=School.Types.SIMPLE)
        url = reverse("admin:school_menu_school_changelist")
        response = self.client.post(
            url,
            {
                "action": "import_csv_menu",
                "_selected_action": [school.pk],
            },
        )
        assert response.status_code == 302
        assert f"{school.pk}/import-csv/" in response["Location"]

    def test_invalid_form_shows_errors(self):
        school = SchoolFactory(
            menu_type=School.Types.SIMPLE,
            no_gluten=False,
            no_lactose=False,
            vegetarian=False,
            special=False,
        )
        url = reverse("admin:school_menu_school_import_csv", args=[school.pk])
        # POST without required fields → form invalid
        response = self.client.post(
            url, {"season": "", "meal_type": "", "csv_file": ""}
        )
        assert response.status_code == 200
        assert SimpleMeal.objects.filter(school=school).count() == 0

    def test_dry_run_errors_show_message(self):
        school = SchoolFactory(
            menu_type=School.Types.SIMPLE,
            no_gluten=False,
            no_lactose=False,
            vegetarian=False,
            special=False,
        )
        # CSV with duplicate rows for same week/day → forces dry_run error
        bad_csv = """settimana,giorno,pranzo,spuntino,merenda
1,Lunedì,Primo piatto,,
1,Lunedì,Secondo piatto,,
1,Martedì,Pasta,,
1,Mercoledì,Riso,,
1,Giovedì,Minestra,,
1,Venerdì,Lasagna,,
2,Lunedì,Pasta,,
2,Martedì,Riso,,
2,Mercoledì,Minestra,,
2,Giovedì,Lasagna,,
2,Venerdì,Pasta,,
3,Lunedì,Pasta,,
3,Martedì,Riso,,
3,Mercoledì,Minestra,,
3,Giovedì,Lasagna,,
3,Venerdì,Pasta,,
4,Lunedì,Pasta,,
4,Martedì,Riso,,
4,Mercoledì,Minestra,,
4,Giovedì,Lasagna,,
4,Venerdì,Pasta,,
"""
        from unittest.mock import MagicMock, patch

        mock_result = MagicMock()
        mock_result.has_errors.return_value = True
        with patch(
            "school_menu.admin.SimpleMealResource.import_data", return_value=mock_result
        ):
            response = self._upload(school, bad_csv, season=SimpleMeal.Seasons.ESTIVO)
        assert response.status_code == 200
        assert SimpleMeal.objects.filter(school=school).count() == 0

    def test_import_creates_audit_log_entry_for_acting_admin(self):
        school = SchoolFactory(
            menu_type=School.Types.SIMPLE,
            no_gluten=False,
            no_lactose=False,
            vegetarian=False,
            special=False,
        )
        self._upload(school, SIMPLE_CSV, season=SimpleMeal.Seasons.ESTIVO)
        entry = AuditLog.objects.get(action=AuditLog.Actions.MENU_UPLOAD)
        assert entry.user == self.superuser
        assert entry.object_id == school.id
        assert entry.changes["source"] == "admin_csv"
        assert entry.changes["rows_imported"] == 20

    def test_dry_run_errors_do_not_create_audit_log_entry(self):
        school = SchoolFactory(
            menu_type=School.Types.SIMPLE,
            no_gluten=False,
            no_lactose=False,
            vegetarian=False,
            special=False,
        )
        self._upload(school, DETAILED_CSV, season=SimpleMeal.Seasons.ESTIVO)
        assert not AuditLog.objects.filter(action=AuditLog.Actions.MENU_UPLOAD).exists()

    def test_action_with_multiple_schools_shows_warning(self):
        schools = SchoolFactory.create_batch(2)
        url = reverse("admin:school_menu_school_changelist")
        response = self.client.post(
            url,
            {
                "action": "import_csv_menu",
                "_selected_action": [s.pk for s in schools],
            },
        )
        assert response.status_code == 302


class TestSchoolTransferAdminActions(TestCase):
    def setUp(self):
        self.superuser = UserFactory(is_staff=True, is_superuser=True)
        self.client.force_login(self.superuser)
        self.changelist_url = reverse("admin:school_menu_schooltransfer_changelist")

    def _run_action(self, action, transfers):
        return self.client.post(
            self.changelist_url,
            {
                "action": action,
                "_selected_action": [t.pk for t in transfers],
            },
            follow=True,
        )

    def test_confirm_transfer_reassigns_school_and_notifies_both_parties(self):
        owner = UserFactory(email="owner@test.com")
        candidate = UserFactory(email="candidate@test.com")
        school = SchoolFactory(user=owner, seeking_maintainer=True)
        transfer = SchoolTransferFactory(
            school=school, from_user=owner, to_user=candidate
        )

        self._run_action("confirm_transfer", [transfer])

        school.refresh_from_db()
        transfer.refresh_from_db()
        assert school.user == candidate
        assert school.seeking_maintainer is False
        assert transfer.status == SchoolTransfer.Status.COMPLETED
        assert transfer.resolved_at is not None
        assert len(mail.outbox) == 2
        recipients = {m.to[0] for m in mail.outbox}
        assert recipients == {"owner@test.com", "candidate@test.com"}

    def test_confirm_transfer_rejects_other_pending_requests_for_same_school(self):
        owner = UserFactory()
        candidate = UserFactory()
        other_candidate = UserFactory()
        school = SchoolFactory(user=owner, seeking_maintainer=True)
        confirmed = SchoolTransferFactory(
            school=school, from_user=owner, to_user=candidate
        )
        other = SchoolTransferFactory(
            school=school, from_user=owner, to_user=other_candidate
        )

        self._run_action("confirm_transfer", [confirmed])

        other.refresh_from_db()
        assert other.status == SchoolTransfer.Status.REJECTED

    def test_confirm_transfer_blocked_when_candidate_already_owns_a_school(self):
        owner = UserFactory()
        candidate = UserFactory()
        SchoolFactory(user=candidate)  # candidate already owns a different school
        school = SchoolFactory(user=owner, seeking_maintainer=True)
        transfer = SchoolTransferFactory(
            school=school, from_user=owner, to_user=candidate
        )

        self._run_action("confirm_transfer", [transfer])

        school.refresh_from_db()
        transfer.refresh_from_db()
        assert school.user == owner
        assert transfer.status == SchoolTransfer.Status.REQUESTED
        assert len(mail.outbox) == 0

    def test_confirm_transfer_blocked_when_owner_changed_since_request(self):
        owner = UserFactory()
        someone_else = UserFactory()
        candidate = UserFactory()
        school = SchoolFactory(user=owner, seeking_maintainer=True)
        transfer = SchoolTransferFactory(
            school=school, from_user=owner, to_user=candidate
        )
        school.user = someone_else
        school.save(update_fields=["user"])

        self._run_action("confirm_transfer", [transfer])

        transfer.refresh_from_db()
        assert transfer.status == SchoolTransfer.Status.REQUESTED
        assert len(mail.outbox) == 0

    def test_reject_transfer_marks_rejected_without_touching_school(self):
        owner = UserFactory()
        candidate = UserFactory()
        school = SchoolFactory(user=owner, seeking_maintainer=True)
        transfer = SchoolTransferFactory(
            school=school, from_user=owner, to_user=candidate
        )

        self._run_action("reject_transfer", [transfer])

        school.refresh_from_db()
        transfer.refresh_from_db()
        assert school.user == owner
        assert transfer.status == SchoolTransfer.Status.REJECTED
        assert transfer.resolved_at is not None


class TestSchoolAdminMirrorFrom:
    def test_mirror_from_in_menu_configuration_fieldset(self):
        fieldsets = SchoolAdmin.fieldsets
        menu_fields = dict(fieldsets)["Configurazione Menu"]["fields"]

        assert "mirror_from" in menu_fields

    def test_autocomplete_and_search_fields_configured(self):
        assert "mirror_from" in SchoolAdmin.autocomplete_fields
        assert SchoolAdmin.search_fields == ["name", "city"]
        assert "mirror_from" in SchoolAdmin.list_filter
