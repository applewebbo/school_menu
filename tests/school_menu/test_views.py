from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from pytest_django.asserts import assertTemplateUsed

from school_menu.models import DetailedMeal, Meal, School, SimpleMeal
from school_menu.test import TestCase
from school_menu.utils import calculate_week, get_current_date, get_season
from tests.school_menu.factories import (
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

    def test_get_with_is_published_false(self):
        school = SchoolFactory(is_published=False)
        response = self.get("school_menu:school_menu", slug=school.slug)

        self.response_200(response)
        assert response.context["not_published"]


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
        }

        with self.login(user):
            response = self.post("school_menu:school_create", data=data)
            school = School.objects.get(user=user)

        self.response_204(response)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == f"<strong>{ school.name }</strong> creata con successo"
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

    def test_school_update_with_success(self):
        user = self.make_user()
        school = SchoolFactory(user=user)
        data = {
            "name": "Test School",
            "city": "Milano",
            "season_choice": School.Seasons.INVERNALE,
            "week_bias": 1,
            "menu_type": School.Types.DETAILED,
        }

        with self.login(user):
            response = self.post("school_menu:school_update", data=data)

        self.response_204(response)
        school = School.objects.get(user=user)
        message = list(get_messages(response.wsgi_request))[0].message
        assert message == f"<strong>{ school.name }</strong> aggiornata con successo"
        assert school.city == "Milano"

    def test_school_update_with_invalid_data(self):
        user = self.make_user()
        SchoolFactory(user=user)
        data = {
            "name": "",
        }

        with self.login(user):
            response = self.post("school_menu:school_update", data=data)

        self.response_200(response)


class SchoolListView(TestCase):
    def test_get(self):
        SchoolFactory.create_batch(3)
        school = School.objects.first()

        response = self.get("school_menu:school_list")

        self.response_200(response)
        assertTemplateUsed(response, "school-list.html")
        assert school in response.context["schools"]


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

        assert response.status_code == 204
        assert "HX-Trigger" in response.headers
        assert SimpleMeal.objects.filter(school=school).count() == 0

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

    # def test_with_index_page_referer(self):
    #     self.get(
    #         "school_menu:search_schools",
    #         data={"q": "test"},
    #         extra={"HTTP_REFERER": "localhost:8000/"},
    #     )

    #     self.assertResponseHeaders({'HTTP_REFERER': 'localhost:8000/'})


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
