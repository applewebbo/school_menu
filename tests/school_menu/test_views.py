from datetime import date, datetime

import time_machine
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from pytest_django.asserts import assertTemplateUsed

from contacts.models import MenuReport
from school_menu.models import AnnualMeal, DetailedMeal, Meal, School, SimpleMeal
from school_menu.test import TestCase
from school_menu.utils import calculate_week, get_current_date, get_season
from tests.school_menu.factories import (
    AnnualMealFactory,
    DetailedMealFactory,
    SchoolFactory,
    SimpleMealFactory,
)
from tests.users.factories import UserFactory


def create_formset_post_data(response, new_form_data=None):
    """Create the formset payload for a post() using the response obtained from a get() request."""
    if new_form_data is None:
        new_form_data = []
    csrf_token = response.context["csrf_token"]
    formset = response.context["formset"]
    prefix_template = formset.empty_form.prefix  # default is 'form-__prefix__'

    # Extract initial formset data
    management_form_data = formset.management_form.initial
    form_data_list = (
        formset.initial if formset.initial is not None else []
    )  # Ensure form_data_list is a list

    # Add new form data and update management form data
    form_data_list.extend(new_form_data)
    management_form_data["TOTAL_FORMS"] = len(form_data_list)

    # Initialize the post data dict
    post_data = dict(csrf_token=csrf_token)

    # Add properly prefixed management form fields
    for key, value in management_form_data.items():
        prefix = prefix_template.replace("__prefix__", "")
        post_data[prefix + key] = value

    # Add properly prefixed data form fields
    for index, form_data in enumerate(form_data_list):
        for key, value in form_data.items():
            prefix = prefix_template.replace("__prefix__", f"{index}-")
            post_data[prefix + key] = value

    return post_data


def get_test_meal(school):
    current_week, adjusted_day = get_current_date()
    bias = school.week_bias
    adjusted_week = calculate_week(current_week, bias)
    season = get_season(school)
    if school.annual_menu:
        test_meal = AnnualMeal.objects.get(school=school, date=datetime.now().date())
    else:
        if school.menu_type == School.Types.SIMPLE:
            test_meal = SimpleMeal.objects.get(
                school=school,
                week=adjusted_week,
                day=adjusted_day,
                season=season,
            )
        else:
            test_meal = DetailedMeal.objects.get(
                school=school,
                week=adjusted_week,
                day=adjusted_day,
                season=season,
            )

    return test_meal


class IndexView(TestCase):
    def test_get(self):
        response = self.get("school_menu:index")

        self.response_200(response)
        assertTemplateUsed(response, "index.html")

    def test_get_with_authenticated_user_and_no_school(self):
        user = self.make_user()
        redirect_url = self.reverse("school_menu:settings", pk=user.pk)

        with self.login(user):
            response = self.get("school_menu:index")

        assert response.status_code == 302
        assert response.url == redirect_url

    def test_get_with_authenticated_user(self):
        user = self.make_user()
        school = SchoolFactory(user=user)

        with self.login(user):
            response = self.get("school_menu:index")

        self.response_200(response)
        assert response.context["school"] == school

    def test_get_with_detailed_meal_setting(self):
        user = self.make_user()
        school = SchoolFactory(user=user, menu_type=School.Types.DETAILED)

        with self.login(user):
            response = self.get("school_menu:index")

        self.response_200(response)
        assert response.context["school"] == school

    def test_get_with_simple_meal_setting(self):
        user = self.make_user()
        school = SchoolFactory(user=user, menu_type=School.Types.SIMPLE)

        with self.login(user):
            response = self.get("school_menu:index")

        self.response_200(response)
        assert response.context["school"] == school

    @time_machine.travel("2025-04-14")  # Monday
    def test_get_with_annual_meal_setting(self):
        user = self.make_user()
        school = SchoolFactory(user=user, annual_menu=True)
        meal = AnnualMealFactory(school=school, date=date.today())

        with self.login(user):
            response = self.get("school_menu:index")

        self.response_200(response)
        assert response.context["school"] == school
        assert response.context["meal"] == meal

    @time_machine.travel("2025-08-20")
    def test_get_when_school_not_in_session(self):
        user = self.make_user()
        SchoolFactory(user=user, start_month=9, start_day=15, end_month=6, end_day=10)

        with self.login(user):
            response = self.get("school_menu:index")

        self.response_200(response)
        assert response.context["not_in_session"] is True

    @time_machine.travel("2025-04-14")  # Monday
    def test_get_with_no_meal_for_today(self):
        user = self.make_user()
        school = SchoolFactory(user=user)
        # Don't create a meal for today

        with self.login(user):
            response = self.get("school_menu:index")

        self.response_200(response)
        assert response.context["school"] == school
        assert response.context["meal"] is None


class SchoolMenuView(TestCase):
    def test_get_with_simple_menu(self):
        school = SchoolFactory(menu_type=School.Types.SIMPLE)
        response = self.get("school_menu:school_menu", slug=school.slug)

        self.response_200(response)
        assertTemplateUsed(response, "school-menu.html")
        assert response.context["school"] == school

    def test_get_with_detailed_menu(self):
        school = SchoolFactory(menu_type=School.Types.DETAILED)
        response = self.get("school_menu:school_menu", slug=school.slug)

        self.response_200(response)
        assertTemplateUsed(response, "school-menu.html")
        assert response.context["school"] == school

    @time_machine.travel("2025-04-14")  # Monday
    def test_get_with_annual_menu(self):
        school = SchoolFactory(annual_menu=True)
        AnnualMealFactory(school=school, date=date.today())
        response = self.get("school_menu:school_menu", slug=school.slug)

        self.response_200(response)
        assertTemplateUsed(response, "school-menu.html")
        assert response.context["school"] == school

    def test_get_with_is_published_false(self):
        school = SchoolFactory(is_published=False)
        response = self.get("school_menu:school_menu", slug=school.slug)

        self.response_200(response)
        assert response.context["not_published"]

    @time_machine.travel("2025-08-20")
    def test_get_when_school_not_in_session(self):
        school = SchoolFactory(start_month=9, start_day=15, end_month=6, end_day=10)
        response = self.get("school_menu:school_menu", slug=school.slug)

        self.response_200(response)
        assert response.context["not_in_session"] is True

    @time_machine.travel("2025-04-14")  # Monday
    def test_get_with_no_meal_for_today(self):
        school = SchoolFactory()
        # Don't create a meal for today
        response = self.get("school_menu:school_menu", slug=school.slug)

        self.response_200(response)
        assert response.context["school"] == school
        assert response.context["meal"] is None


class GetMenuView(TestCase):
    def test_get_with_simple_menu(self):
        school = SchoolFactory(
            menu_type=School.Types.SIMPLE, season_choice=School.Seasons.PRIMAVERILE
        )
        meal = SimpleMealFactory(
            school=school,
            day=1,
            week=1,
            menu="Pasta al Pomodoro",
            morning_snack="Crackers",
            afternoon_snack="Yogurt",
            season=School.Seasons.PRIMAVERILE,
            type=SimpleMeal.Types.STANDARD,
        )

        response = self.get("school_menu:get_menu", school.pk, 1, 1, "S")

        self.response_200(response)
        assert response.context["meal"] == meal

    import time_machine

    # ... (omitting unchanged parts of the file for brevity)

    @time_machine.travel("2025-04-12")  # Saturday
    def test_get_with_annual_menu(self):
        """Test get_menu view with an annual menu on a weekend"""
        # Create a school and meals
        school = SchoolFactory(annual_menu=True)
        next_monday = date(2025, 4, 14)  # Next Monday
        monday_meal = AnnualMealFactory(
            school=school, date=next_monday, type="S", is_active=True
        )

        # Call the view
        response = self.get("school_menu:get_menu", school.pk, 15, 1, "S")

        # Assertions
        self.response_200(response)
        assert response.context["meal"] == monday_meal

    def test_get_with_detailed_menu(self):
        school = SchoolFactory(
            menu_type=School.Types.DETAILED, season_choice=School.Seasons.PRIMAVERILE
        )
        meal = DetailedMealFactory(
            school=school,
            day=1,
            week=1,
            first_course="Pasta al Pomodoro",
            snack="Crackers",
            season=School.Seasons.PRIMAVERILE,
            type=DetailedMeal.Types.STANDARD,
        )

        response = self.get("school_menu:get_menu", school.pk, 1, 1, "S")

        self.response_200(response)
        assert response.context["meal"] == meal

    def test_get_with_meal_not_present(self):
        school = SchoolFactory(
            menu_type=School.Types.SIMPLE, season_choice=School.Seasons.PRIMAVERILE
        )

        response = self.get("school_menu:get_menu", school.pk, 1, 1, "S")

        self.response_200(response)
        assert response.context["meal"] is None


class SettingView(TestCase):
    def test_get(self):
        user = self.make_user()
        SchoolFactory(user=user)

        with self.login(user):
            response = self.get("school_menu:settings", pk=user.pk)

        self.response_200(response)
        assertTemplateUsed(response, "settings.html")
        assert response.context["user"] == user

    def test_partial_reload(self):
        user = self.make_user()
        SchoolFactory(user=user)

        with self.login(user):
            response = self.get("school_menu:menu_settings", pk=user.pk)

        self.response_200(response)
        assert response.context["user"] == user

    def test_partial_reload_with_alt_menu(self):
        user = self.make_user()
        SchoolFactory(user=user)

        with self.login(user):
            response = self.get(
                "school_menu:menu_settings", pk=user.pk, data={"active_menu": "G"}
            )

        self.response_200(response)
        assert response.context["user"] == user
        assert response.context["menu_label"] == "No Glutine"

    def test_school_partial_view(self):
        user = self.make_user()
        school = SchoolFactory(user=user)

        with self.login(user):
            response = self.get("school_menu:school_view")

        self.response_200(response)
        assert response.context["school"] == school

    def test_school_create_with_success(self):
        user = self.make_user()
        data = {
            "name": "Test School",
            "city": "Milano",
            "season_choice": School.Seasons.INVERNALE,
            "week_bias": 1,
            "menu_type": School.Types.DETAILED,
            "start_date": date(2024, 9, 1),
            "end_date": date(2025, 6, 30),
        }

        with self.login(user):
            response = self.post("school_menu:school_create", data=data)
            school = School.objects.get(user=user)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == f"<strong>{school.name}</strong> creata con successo"
        assert School.objects.filter(user=user).count() == 1
        assert school.name == "Test School"

    def test_school_create_with_invalid_data(self):
        user = self.make_user()
        data = {
            "name": "",
        }

        with self.login(user):
            response = self.post("school_menu:school_create", data=data)

        self.response_200(response)
        assert School.objects.filter(user=user).count() == 0

    def test_school_create_get(self):
        user = self.make_user()

        with self.login(user):
            response = self.get("school_menu:school_create")

        self.response_200(response)
        assertTemplateUsed(response, "partials/school.html")
        assert "form" in response.context
        assert response.context["create"] is True

    def test_school_update_with_success(self):
        user = self.make_user()
        school = SchoolFactory(user=user)
        data = {
            "name": "Test School",
            "city": "Milano",
            "season_choice": School.Seasons.INVERNALE,
            "week_bias": 1,
            "menu_type": School.Types.DETAILED,
            "start_date": date(2024, 9, 1),
            "end_date": date(2025, 6, 30),
        }

        with self.login(user):
            response = self.post("school_menu:school_update", data=data)

        self.response_204(response)
        school = School.objects.get(user=user)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == f"<strong>{school.name}</strong> aggiornata con successo"
        assert school.city == "Milano"

    def test_school_update_get_after_school_year_ends(self):
        user = self.make_user()
        # School year ends on June 10th
        SchoolFactory(user=user, end_month=6, end_day=10)

        with self.login(user):
            # Travel to a date after the school year has ended
            with time_machine.travel("2025-08-20"):
                response = self.get("school_menu:school_update")

        self.response_200(response)
        assertTemplateUsed(response, "partials/school.html")
        assert "form" in response.context
        # Check that the end_date in the form is for the next year
        assert response.context["form"].initial["end_date"].year == 2026

    def test_school_update_with_invalid_data(self):
        user = self.make_user()
        SchoolFactory(user=user)
        data = {
            "name": "",
        }

        with self.login(user):
            response = self.post("school_menu:school_update", data=data)

        self.response_200(response)
        assert "form" in response.context

    def test_school_update_get_during_school_year(self):
        user = self.make_user()
        # School year ends on June 10th
        SchoolFactory(user=user, end_month=6, end_day=10)

        with self.login(user):
            # Travel to a date during the school year
            with time_machine.travel("2025-04-20"):
                response = self.get("school_menu:school_update")

        self.response_200(response)
        assertTemplateUsed(response, "partials/school.html")
        assert "form" in response.context
        # Check that the end_date in the form is for the current year
        assert response.context["form"].initial["end_date"].year == 2025

    def test_school_settings_partial(self):
        user = self.make_user()
        SchoolFactory(user=user)

        with self.login(user):
            response = self.get("school_menu:school_settings")

        self.response_200(response)
        assert "user" in response.context


class SchoolListView(TestCase):
    def test_get(self):
        SchoolFactory.create_batch(3)
        school = School.objects.first()

        response = self.get("school_menu:school_list")

        self.response_200(response)
        assertTemplateUsed(response, "school-list.html")
        assert school in response.context["schools"]

    def test_get_excluding_not_published(self):
        SchoolFactory()
        school_not_published = SchoolFactory(is_published=False)

        response = self.get("school_menu:school_list")

        self.response_200(response)
        assertTemplateUsed(response, "school-list.html")
        assert school_not_published not in response.context["schools"]


class TestUploadMenuView(TestCase):
    def test_upload_menu_get(self):
        user = self.make_user()
        school = SchoolFactory(user=user)

        with self.login(user):
            response = self.get(
                reverse(
                    "school_menu:upload_menu",
                    kwargs={"school_id": school.id, "meal_type": Meal.Types.STANDARD},
                )
            )

        assert response.status_code == 200
        assert "form" in response.context
        assert "school" in response.context

    def test_upload_menu_post_simple_success(self):
        user = self.make_user()
        school = SchoolFactory(user=user, menu_type=School.Types.SIMPLE)

        with self.login(user):
            url = reverse(
                "school_menu:upload_menu",
                kwargs={"school_id": school.id, "meal_type": Meal.Types.STANDARD},
            )
            csv_content = "giorno,settimana,pranzo,spuntino,merenda\nLunedì,1,Pasta al Pomodoro,Mela,Yogurt"
            data = {
                "file": SimpleUploadedFile(
                    "simple_menu.csv",
                    csv_content.encode("utf-8"),
                    content_type="text/csv",
                ),
                "season": School.Seasons.INVERNALE,
            }
            response = self.post(url, data=data)

        assert response.status_code == 204
        assert "HX-Refresh" in response.headers
        assert SimpleMeal.objects.filter(school=school).count() == 1

    def test_upload_menu_post_invalid_data(self):
        user = self.make_user()
        school = SchoolFactory(user=user)

        with self.login(user):
            url = reverse(
                "school_menu:upload_menu",
                kwargs={"school_id": school.id, "meal_type": Meal.Types.STANDARD},
            )
            data = {"season": School.Seasons.INVERNALE}  # Missing file
            response = self.post(url, data=data)

        assert response.status_code == 200
        assert "form" in response.context

    def test_upload_menu_post_invalid_csv(self):
        user = self.make_user()
        school = SchoolFactory(user=user)

        with self.login(user):
            url = reverse(
                "school_menu:upload_menu",
                kwargs={"school_id": school.id, "meal_type": Meal.Types.STANDARD},
            )
            csv_content = b"invalid,csv,content"
            data = {
                "file": SimpleUploadedFile(
                    "simple_menu.csv", csv_content, content_type="text/csv"
                ),
                "season": School.Seasons.INVERNALE,
            }
            response = self.post(url, data=data)

        assert response.status_code == 200
        response_text = response.content.decode()
        # The error message should mention format validation issues
        # (Could be about missing columns or invalid format)
        assert "Formato non valido" in response_text or "error_message" in str(
            response.context
        )
        assert SimpleMeal.objects.filter(school=school).count() == 0

    def test_upload_menu_post_invalid_csv_content(self):
        user = self.make_user()
        school = SchoolFactory(user=user, menu_type=School.Types.SIMPLE)

        with self.login(user):
            url = reverse(
                "school_menu:upload_menu",
                kwargs={"school_id": school.id, "meal_type": Meal.Types.STANDARD},
            )
            csv_content = "giorno,settimana,pranzo,spuntino\nLunedì,1,Pasta,Mela"  # Missing 'merenda' column
            data = {
                "file": SimpleUploadedFile(
                    "simple_menu.csv",
                    csv_content.encode("utf-8"),
                    content_type="text/csv",
                ),
                "season": School.Seasons.INVERNALE,
            }
            response = self.post(url, data=data)

        assert response.status_code == 200
        response_text = response.content.decode()
        # The error message should mention missing required columns
        assert (
            "Il file non contiene tutte le colonne richieste" in response_text
            or "Colonne mancanti" in response_text
        )
        assert SimpleMeal.objects.filter(school=school).count() == 0

    def test_upload_menu_post_generic_exception(self):
        user = self.make_user()
        school = SchoolFactory(user=user)

        with self.login(user):
            url = reverse(
                "school_menu:upload_menu",
                kwargs={"school_id": school.id, "meal_type": Meal.Types.STANDARD},
            )
            # This content will raise an exception when decoding
            csv_content = b"\x80"
            data = {
                "file": SimpleUploadedFile(
                    "simple_menu.csv",
                    csv_content,
                    content_type="text/csv",
                ),
                "season": School.Seasons.INVERNALE,
            }
            response = self.post(url, data=data)

        assert response.status_code == 204
        assert "HX-Trigger" in response.headers
        messages = list(get_messages(response.wsgi_request))
        assert len(messages) > 0
        # The error message should indicate a CSV validation error
        assert (
            "Il file CSV non è valido" in messages[0].message
            or "Errore" in messages[0].message
        )

    def test_upload_menu_post_detailed_success(self):
        user = self.make_user()
        school = School.objects.create(user=user, menu_type=School.Types.DETAILED)

        with self.login(user):
            url = reverse(
                "school_menu:upload_menu",
                kwargs={"school_id": school.id, "meal_type": Meal.Types.STANDARD},
            )
            csv_content = "settimana,giorno,primo,secondo,contorno,frutta,spuntino\n1,Lunedì,Pasta,Pollo,Insalata,Mela,Crostatina"
            data = {
                "file": SimpleUploadedFile(
                    "detailed_menu.csv",
                    csv_content.encode("utf-8"),
                    content_type="text/csv",
                ),
                "season": School.Seasons.INVERNALE,
            }
            response = self.post(url, data=data)

        assert response.status_code == 204
        assert "HX-Refresh" in response.headers
        assert DetailedMeal.objects.filter(school=school).count() == 1

    def test_upload_menu_post_semicolon_delimiter_simple(self):
        """Test uploading simple menu CSV with semicolon delimiter (Numbers export)"""
        user = self.make_user()
        school = SchoolFactory(user=user, menu_type=School.Types.SIMPLE)

        with self.login(user):
            url = reverse(
                "school_menu:upload_menu",
                kwargs={"school_id": school.id, "meal_type": Meal.Types.STANDARD},
            )
            csv_content = "giorno;settimana;pranzo;spuntino;merenda\nLunedì;1;Pasta al Pomodoro;Mela;Yogurt"
            data = {
                "file": SimpleUploadedFile(
                    "simple_menu_semicolon.csv",
                    csv_content.encode("utf-8"),
                    content_type="text/csv",
                ),
                "season": School.Seasons.INVERNALE,
            }
            response = self.post(url, data=data)

        assert response.status_code == 204
        assert "HX-Refresh" in response.headers
        assert SimpleMeal.objects.filter(school=school).count() == 1

    def test_upload_menu_post_semicolon_delimiter_detailed(self):
        """Test uploading detailed menu CSV with semicolon delimiter"""
        user = self.make_user()
        school = SchoolFactory(user=user, menu_type=School.Types.DETAILED)

        with self.login(user):
            url = reverse(
                "school_menu:upload_menu",
                kwargs={"school_id": school.id, "meal_type": Meal.Types.STANDARD},
            )
            csv_content = "settimana;giorno;primo;secondo;contorno;frutta;spuntino\n1;Lunedì;Pasta;Pollo;Insalata;Mela;Crostatina"
            data = {
                "file": SimpleUploadedFile(
                    "detailed_menu_semicolon.csv",
                    csv_content.encode("utf-8"),
                    content_type="text/csv",
                ),
                "season": School.Seasons.INVERNALE,
            }
            response = self.post(url, data=data)

        assert response.status_code == 204
        assert "HX-Refresh" in response.headers
        assert DetailedMeal.objects.filter(school=school).count() == 1

    def test_upload_menu_post_with_extra_unnamed_columns(self):
        """Test uploading CSV with extra unnamed columns (trailing commas)"""
        user = self.make_user()
        school = SchoolFactory(user=user, menu_type=School.Types.SIMPLE)

        with self.login(user):
            url = reverse(
                "school_menu:upload_menu",
                kwargs={"school_id": school.id, "meal_type": Meal.Types.STANDARD},
            )
            # CSV with trailing commas creating unnamed columns
            csv_content = "giorno,settimana,pranzo,spuntino,merenda,,,\nLunedì,1,Pasta al Pomodoro,Mela,Yogurt,,,\n"
            data = {
                "file": SimpleUploadedFile(
                    "simple_menu_extra_unnamed.csv",
                    csv_content.encode("utf-8"),
                    content_type="text/csv",
                ),
                "season": School.Seasons.INVERNALE,
            }
            response = self.post(url, data=data)

        assert response.status_code == 204
        assert "HX-Refresh" in response.headers
        assert SimpleMeal.objects.filter(school=school).count() == 1

    def test_upload_menu_post_with_extra_named_columns(self):
        """Test uploading CSV with extra named columns not in schema"""
        user = self.make_user()
        school = SchoolFactory(user=user, menu_type=School.Types.SIMPLE)

        with self.login(user):
            url = reverse(
                "school_menu:upload_menu",
                kwargs={"school_id": school.id, "meal_type": Meal.Types.STANDARD},
            )
            # CSV with extra columns not in schema
            csv_content = "giorno,settimana,pranzo,spuntino,merenda,extra1,extra2\nLunedì,1,Pasta,Mela,Yogurt,X,Y"
            data = {
                "file": SimpleUploadedFile(
                    "simple_menu_extra_named.csv",
                    csv_content.encode("utf-8"),
                    content_type="text/csv",
                ),
                "season": School.Seasons.INVERNALE,
            }
            response = self.post(url, data=data)

        assert response.status_code == 204
        assert "HX-Refresh" in response.headers
        assert SimpleMeal.objects.filter(school=school).count() == 1

    def test_upload_menu_post_with_quoted_fields(self):
        """Test uploading CSV with quoted fields containing commas"""
        user = self.make_user()
        school = SchoolFactory(user=user, menu_type=School.Types.SIMPLE)

        with self.login(user):
            url = reverse(
                "school_menu:upload_menu",
                kwargs={"school_id": school.id, "meal_type": Meal.Types.STANDARD},
            )
            # CSV with quoted fields containing commas
            csv_content = '"giorno","settimana","pranzo","spuntino","merenda"\n"Lunedì","1","Pasta al Pomodoro, Ragù","Mela, Pera","Yogurt"\n'
            data = {
                "file": SimpleUploadedFile(
                    "simple_menu_quoted.csv",
                    csv_content.encode("utf-8"),
                    content_type="text/csv",
                ),
                "season": School.Seasons.INVERNALE,
            }
            response = self.post(url, data=data)

        assert response.status_code == 204
        assert "HX-Refresh" in response.headers
        assert SimpleMeal.objects.filter(school=school).count() == 1
        # Verify the quoted content was preserved
        meal = SimpleMeal.objects.get(school=school)
        assert "Pasta al Pomodoro, Ragù" in meal.menu


class TestUploadAnnualMenuView(TestCase):
    def test_upload_annual_menu_get(self):
        user = self.make_user()
        school = SchoolFactory(user=user)

        with self.login(user):
            response = self.get(
                reverse(
                    "school_menu:upload_annual_menu",
                    kwargs={"school_id": school.id, "meal_type": Meal.Types.STANDARD},
                )
            )

        assert response.status_code == 200
        assert "form" in response.context
        assert "school" in response.context

    def test_upload_annual_menu_post_success(self):
        user = self.make_user()
        school = SchoolFactory(user=user)

        with self.login(user):
            url = reverse(
                "school_menu:upload_annual_menu",
                kwargs={"school_id": school.id, "meal_type": Meal.Types.STANDARD},
            )
            csv_content = "data,primo,secondo,contorno,frutta,altro\n01/01/2024,Pasta,Pollo,Insalata,Mela,Pane"
            data = {
                "file": SimpleUploadedFile(
                    "annual_menu.csv",
                    csv_content.encode("utf-8"),
                    content_type="text/csv",
                ),
            }
            response = self.post(url, data=data)

        assert response.status_code == 204
        assert "HX-Refresh" in response.headers
        assert AnnualMeal.objects.filter(school=school).count() == 1

    def test_upload_annual_menu_post_invalid_data(self):
        user = self.make_user()
        school = SchoolFactory(user=user)

        with self.login(user):
            url = reverse(
                "school_menu:upload_annual_menu",
                kwargs={"school_id": school.id, "meal_type": Meal.Types.STANDARD},
            )
            data = {}  # Missing file
            response = self.post(url, data=data)

        assert response.status_code == 200
        assert "form" in response.context

    def test_upload_annual_menu_post_invalid_csv_format(self):
        user = self.make_user()
        school = SchoolFactory(user=user)

        with self.login(user):
            url = reverse(
                "school_menu:upload_annual_menu",
                kwargs={"school_id": school.id, "meal_type": Meal.Types.STANDARD},
            )
            csv_content = "data,wrong,headers\n01/01/2024,Pasta,Pollo"
            data = {
                "file": SimpleUploadedFile(
                    "annual_menu.csv",
                    csv_content.encode("utf-8"),
                    content_type="text/csv",
                ),
            }
            response = self.post(url, data=data)

        assert response.status_code == 200
        response_text = response.content.decode()
        # The error message should mention missing required columns
        assert (
            "Il file non contiene tutte le colonne richieste" in response_text
            or "Colonne mancanti" in response_text
        )
        assert AnnualMeal.objects.filter(school=school).count() == 0

    def test_upload_annual_menu_post_invalid_csv(self):
        user = self.make_user()
        school = SchoolFactory(user=user)

        with self.login(user):
            url = reverse(
                "school_menu:upload_annual_menu",
                kwargs={"school_id": school.id, "meal_type": Meal.Types.STANDARD},
            )
            # This content will raise an exception when decoding
            csv_content = b"\x80"
            data = {
                "file": SimpleUploadedFile(
                    "annual_menu.csv", csv_content, content_type="text/csv"
                ),
            }
            response = self.post(url, data=data)

        assert response.status_code == 204
        assert "HX-Trigger" in response.headers
        messages = list(get_messages(response.wsgi_request))
        assert len(messages) > 0
        # The error message should indicate a CSV validation error
        assert (
            "Il file CSV non è valido" in messages[0].message
            or "Errore" in messages[0].message
        )
        assert AnnualMeal.objects.filter(school=school).count() == 0

    def test_upload_annual_menu_post_semicolon_delimiter(self):
        """Test uploading annual menu CSV with semicolon delimiter"""
        user = self.make_user()
        school = SchoolFactory(user=user)

        with self.login(user):
            url = reverse(
                "school_menu:upload_annual_menu",
                kwargs={"school_id": school.id, "meal_type": Meal.Types.STANDARD},
            )
            csv_content = "data;primo;secondo;contorno;frutta;altro\n01/01/2024;Pasta;Pollo;Insalata;Mela;Pane"
            data = {
                "file": SimpleUploadedFile(
                    "annual_menu_semicolon.csv",
                    csv_content.encode("utf-8"),
                    content_type="text/csv",
                ),
            }
            response = self.post(url, data=data)

        assert response.status_code == 204
        assert "HX-Refresh" in response.headers
        assert AnnualMeal.objects.filter(school=school).count() == 1

    def test_upload_annual_menu_post_with_extra_columns(self):
        """Test uploading annual menu CSV with extra columns"""
        user = self.make_user()
        school = SchoolFactory(user=user)

        with self.login(user):
            url = reverse(
                "school_menu:upload_annual_menu",
                kwargs={"school_id": school.id, "meal_type": Meal.Types.STANDARD},
            )
            # CSV with extra columns that should be ignored
            csv_content = "data,primo,secondo,contorno,frutta,altro,extra1,extra2\n01/01/2024,Pasta,Pollo,Insalata,Mela,Pane,X,Y"
            data = {
                "file": SimpleUploadedFile(
                    "annual_menu_extra.csv",
                    csv_content.encode("utf-8"),
                    content_type="text/csv",
                ),
            }
            response = self.post(url, data=data)

        assert response.status_code == 204
        assert "HX-Refresh" in response.headers
        assert AnnualMeal.objects.filter(school=school).count() == 1

    def test_upload_annual_menu_post_with_quoted_fields(self):
        """Test uploading annual menu CSV with quoted fields"""
        user = self.make_user()
        school = SchoolFactory(user=user)

        with self.login(user):
            url = reverse(
                "school_menu:upload_annual_menu",
                kwargs={"school_id": school.id, "meal_type": Meal.Types.STANDARD},
            )
            # CSV with quoted fields containing special characters
            csv_content = '"data","primo","secondo","contorno","frutta","altro"\n"01/01/2024","Pasta al Pomodoro, Ragù","Pollo arrosto","Insalata mista","Mela, Pera","Pane"\n'
            data = {
                "file": SimpleUploadedFile(
                    "annual_menu_quoted.csv",
                    csv_content.encode("utf-8"),
                    content_type="text/csv",
                ),
            }
            response = self.post(url, data=data)

        assert response.status_code == 204
        assert "HX-Refresh" in response.headers
        assert AnnualMeal.objects.filter(school=school).count() == 1
        # Verify quoted content was preserved
        meal = AnnualMeal.objects.get(school=school)
        assert "Pasta al Pomodoro, Ragù" in meal.menu


class CreateWeeklyMenuView(TestCase):
    def test_get(self):
        user_factory = UserFactory  # noqa
        menu_types = [School.Types.SIMPLE, School.Types.DETAILED]
        for index, menu_type in enumerate(menu_types):
            user = self.make_user(index)
            school = SchoolFactory(menu_type=menu_type, user=user)

            with self.login(user):
                response = self.get(
                    "school_menu:create_weekly_menu", school.pk, 1, 1, "S"
                )

            self.response_200(response)
            assert "formset" in response.context
            assertTemplateUsed(response, "create-weekly-menu.html")
            assert response.context["school"] == school
            assert response.context["week"] == 1
            assert response.context["season"] == 1
            if menu_type == School.Types.SIMPLE:
                assert SimpleMeal.objects.filter(school=school).count() == 5
            else:
                assert DetailedMeal.objects.filter(school=school).count() == 5

    def test_get_with_meals_already_present(self):
        user = self.make_user()
        school = SchoolFactory(
            user=user,
            menu_type=School.Types.SIMPLE,
            no_gluten=False,
            no_lactose=False,
            vegetarian=False,
            special=False,
        )
        SimpleMealFactory.create_batch(5, school=school, type=Meal.Types.STANDARD)

        with self.login(user):
            response = self.get("school_menu:create_weekly_menu", school.pk, 1, 1, "S")

        self.response_200(response)
        assert "formset" in response.context
        assertTemplateUsed(response, "create-weekly-menu.html")
        assert response.context["school"] == school
        assert response.context["week"] == 1
        assert response.context["season"] == 1
        assert SimpleMeal.objects.filter(school=school).count() == 5

    def test_post_with_valid_data(self):
        user = self.make_user()
        school = SchoolFactory(menu_type=School.Types.SIMPLE, user=user)
        test_data = [
            {"id": 1, "day": 1, "menu": "Pasta al Pomodoro", "snack": "Crackers"},
            {"id": 2, "day": 2, "menu": "Riso al Sugo", "snack": "Yogurt"},
            {"id": 3, "day": 3, "menu": "Pasta al Pesto", "snack": "Frutta"},
            {"id": 4, "day": 4, "menu": "Riso al Tonno", "snack": "Crackers"},
            {"id": 5, "day": 5, "menu": "Pasta al Ragù", "snack": "Yogurt"},
        ]

        with self.login(user):
            response = self.get("school_menu:create_weekly_menu", school.pk, 1, 1, "S")
            self.response_200(response)
            post_data = create_formset_post_data(response, new_form_data=test_data)
            response = self.post(
                "school_menu:create_weekly_menu", school.pk, 1, 1, "S", data=post_data
            )

        self.response_302(response)
        assert response.url == self.reverse("school_menu:settings", school.user.pk)

    def test_post_with_invalid_data(self):
        user = self.make_user()
        school = SchoolFactory(menu_type=School.Types.SIMPLE, user=user)
        test_data = [
            {"id": 1, "day": 1, "menu": "Pasta al Pomodoro", "snack": "Crackers"},
            {"id": 2, "day": 2, "menu": "Riso al Sugo", "snack": "Yogurt"},
            {"id": 3, "day": 3, "menu": "Pasta al Pesto", "snack": "Frutta"},
            {"id": 4, "day": 4, "menu": "Riso al Tonno", "snack": "Crackers"},
            {"id": 5, "day": 5, "menu": "Pasta al Ragù", "snack": "Yogurt"},
        ]

        with self.login(user):
            response = self.get("school_menu:create_weekly_menu", school.pk, 1, 1, "S")
            self.response_200(response)
            post_data = create_formset_post_data(response, new_form_data=test_data)
            post_data["form-0-menu"] = ""
            response = self.post(
                "school_menu:create_weekly_menu", school.pk, 1, 1, "S", data=post_data
            )

        self.response_200(response)
        assert "formset" in response.context
        assert response.context["formset"].errors


class SchoolSearchView(TestCase):
    def setUp(self):
        self.test_school = SchoolFactory(name="Test School", city="Milano")
        SchoolFactory.create_batch(10)

    def test_get_with_school_name(self):
        response = self.get("school_menu:search_schools", data={"q": "test"})

        self.response_200(response)
        assert "Test School" in response.content.decode()

    def test_get_with_school_city(self):
        response = self.get("school_menu:search_schools", data={"q": "milano"})

        self.response_200(response)
        assert "Milano" in response.content.decode()

    def test_with_empty_input(self):
        response = self.get("school_menu:search_schools", data={"q": ""})

        self.response_200(response)

    def test_with_no_school_matching_search(self):
        response = self.get(
            "school_menu:search_schools", data={"q": "kjsdkjhsdkjhkslk"}
        )

        self.response_200(response)
        assert (
            "Nessuna scuola soddisfa i criteri di ricerca..."
            in response.content.decode()
        )

    def test_with_index_page_referer(self):
        response = self.get(
            "school_menu:search_schools",
            data={"q": "test"},
            extra={"HTTP_REFERER": "http://testserver/"},
        )
        self.response_200(response)
        self.assertContains(response, '<div id="school-list"')


class TestExportModalView(TestCase):
    def test_get_simple_menu(self):
        user = self.make_user()
        school = SchoolFactory(user=user, menu_type=School.Types.SIMPLE)
        SimpleMealFactory.create_batch(
            5, school=school, season=SimpleMeal.Seasons.ESTIVO, type=Meal.Types.STANDARD
        )

        response = self.get("school_menu:export_modal", school.pk, Meal.Types.STANDARD)

        self.response_200(response)
        assertTemplateUsed(response, "export-menu.html")
        assert response.context["school"] == school
        assert response.context["summer_meals"] is True

    def test_get_detailed_menu(self):
        user = self.make_user()
        school = SchoolFactory(user=user, menu_type=School.Types.DETAILED)
        DetailedMealFactory.create_batch(
            5,
            school=school,
            season=DetailedMeal.Seasons.INVERNALE,
            type=Meal.Types.STANDARD,
        )

        response = self.get("school_menu:export_modal", school.pk, Meal.Types.STANDARD)

        self.response_200(response)
        assertTemplateUsed(response, "export-menu.html")
        assert response.context["school"] == school
        assert response.context["winter_meals"] is True

    def test_get_annual_menu(self):
        user = self.make_user()
        school = SchoolFactory(user=user, annual_menu=True)
        AnnualMealFactory.create_batch(
            5,
            school=school,
            type=Meal.Types.STANDARD,
        )

        response = self.get("school_menu:export_modal", school.pk, Meal.Types.STANDARD)

        self.response_200(response)
        assertTemplateUsed(response, "export-menu.html")
        assert response.context["school"] == school
        assert response.context["annual_meals"] is True


class TestExportMenuView(TestCase):
    def test_get_simple_menu(self):
        user = self.make_user()
        school = SchoolFactory(user=user, menu_type=School.Types.SIMPLE)
        SimpleMeal.objects.create(
            school=school,
            week=1,
            day=1,
            menu="Pasta",
            morning_snack="Apple",
            afternoon_snack="Orange",
            season=SimpleMeal.Seasons.ESTIVO,
        )

        with self.login(user):
            response = self.get(
                "school_menu:export_menu",
                school_id=school.pk,
                season=SimpleMeal.Seasons.ESTIVO,
                meal_type=Meal.Types.STANDARD,
            )

        self.response_200(response)
        assert response["Content-Type"] == "text/csv"
        assert b"Pasta" in response.content
        assert b"Apple" in response.content

    def test_get_detailed_menu(self):
        user = self.make_user()
        school = SchoolFactory(user=user, menu_type=School.Types.DETAILED)
        DetailedMeal.objects.create(
            school=school,
            week=1,
            day=1,
            first_course="Soup",
            second_course="Fish",
            side_dish="Salad",
            snack="Fruit",
            season=DetailedMeal.Seasons.ESTIVO,
        )
        with self.login(user):
            response = self.get(
                "school_menu:export_menu",
                school_id=school.pk,
                season=SimpleMeal.Seasons.ESTIVO,
                meal_type=Meal.Types.STANDARD,
            )

        self.response_200(response)
        assert response["Content-Type"] == "text/csv"
        assert b"Soup" in response.content
        assert b"Fish" in response.content
        assert b"Salad" in response.content
        assert b"Fruit" in response.content

    def test_get_annual_menu(self):
        user = self.make_user()
        school = SchoolFactory(user=user, annual_menu=True)
        AnnualMealFactory.create_batch(5, school=school, type=Meal.Types.STANDARD)
        meal = AnnualMeal.objects.first()
        first_course = meal.menu.split("\n")[0]

        with self.login(user):
            response = self.get(
                "school_menu:export_menu",
                school_id=school.pk,
                season=meal.season,
                meal_type=Meal.Types.STANDARD,
            )

        self.response_200(response)
        assert response["Content-Type"] == "text/csv"
        assert first_course in response.content.decode("utf-8")


class JsonSchoolsListView(TestCase):
    def test_get(self):
        SchoolFactory.create_batch(3)
        school = School.objects.first()

        response = self.get("school_menu:get_schools_json_list")
        data = response.json()

        self.response_200(response)
        assert school.name in [s["name"] for s in data]


class JsonSchoolMenuView(TestCase):
    def test_get_with_simple_menu(self):
        user = self.make_user()
        school = SchoolFactory(user=user, menu_type=School.Types.SIMPLE)
        for season in SimpleMeal.Seasons.choices:
            for week in SimpleMeal.Weeks.choices:
                for day in SimpleMeal.Days.choices:
                    SimpleMealFactory.create(
                        school=school,
                        day=day[0],
                        week=week[0],
                        season=season[0],
                    )
        test_meal = get_test_meal(school)
        test_meal.menu = test_meal.menu.replace("\n", ", ").strip()

        response = self.get("school_menu:get_school_json_menu", school.slug)
        data = response.json()

        self.response_200(response)
        assert test_meal.morning_snack in [
            meal["morning_snack"] for meal in data["meals"]
        ]
        assert test_meal.menu in [meal["menu"] for meal in data["meals"]]

    def test_get_with_detailed_menu(self):
        user = self.make_user()
        school = SchoolFactory(user=user, menu_type=School.Types.DETAILED)
        for season in DetailedMeal.Seasons.choices:
            for week in DetailedMeal.Weeks.choices:
                for day in DetailedMeal.Days.choices:
                    DetailedMealFactory.create(
                        school=school,
                        day=day[0],
                        week=week[0],
                        season=season[0],
                    )
        test_meal = get_test_meal(school)

        response = self.get("school_menu:get_school_json_menu", school.slug)
        data = response.json()

        self.response_200(response)
        assert test_meal.snack in [meal["snack"] for meal in data["meals"]]
        expected_menu = f"{test_meal.first_course}, {test_meal.second_course}, {test_meal.fruit}, {test_meal.side_dish}"
        assert expected_menu in [s["menu"] for s in data["meals"]]

    def test_get_with_annual_menu(self):
        user = self.make_user()
        school = SchoolFactory(user=user, annual_menu=True)

        # Create AnnualMeal objects for testing, using date instead of week/day/season
        from datetime import date, timedelta

        today = date.today()
        for i in range(7):  # Create meals for a week
            AnnualMealFactory.create(
                school=school,
                date=today + timedelta(days=i),
            )

        test_meal = get_test_meal(
            school
        )  # Make sure get_test_meal handles the date field

        response = self.get("school_menu:get_school_json_menu", school.slug)
        data = response.json()

        self.response_200(response)
        # Assertions for annual menu data
        assert test_meal.menu.replace("\n", ", ").replace("\r", " ").strip() in [
            meal["menu"] for meal in data["meals"]
        ]
        assert test_meal.snack in [meal["snack"] for meal in data["meals"]]


class TestMenuReportCountView(TestCase):
    def test_get(self):
        user = self.make_user()
        MenuReport.objects.create(
            receiver=user, name="Test name", message="Test message"
        )

        with self.login(user):
            response = self.get("school_menu:menu_report_count")

        self.response_200(response)
