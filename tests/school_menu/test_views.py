from unittest.mock import patch

from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from pytest_django.asserts import assertTemplateUsed

from school_menu.models import DetailedMeal, School, SimpleMeal
from school_menu.test import TestCase
from tests.school_menu.factories import (
    DetailedMealFactory,
    SchoolFactory,
    SimpleMealFactory,
)
from tests.users.factories import UserFactory


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


class SchoolMenuView(TestCase):
    def test_get(self):
        school = SchoolFactory()
        response = self.get("school_menu:school_menu", slug=school.slug)

        self.response_200(response)
        assertTemplateUsed(response, "school-menu.html")
        assert response.context["school"] == school

    def test_get_with_detailed_menu(self):
        school = SchoolFactory(menu_type=School.Types.SIMPLE)
        response = self.get("school_menu:school_menu", slug=school.slug)

        self.response_200(response)
        assertTemplateUsed(response, "school-menu.html")
        assert response.context["school"] == school


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
            snack="Crackers",
            season=School.Seasons.PRIMAVERILE,
        )

        response = self.get("school_menu:get_menu", 1, 1, 1, school.pk)

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
        )

        response = self.get("school_menu:get_menu", 1, 1, 1, school.pk)

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

        self.response_200(response)
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

        self.response_200(response)
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


class UploadMenuView(TestCase):
    def test_get(self):
        school = SchoolFactory()
        response = self.get("school_menu:upload_menu", school.pk)

        self.response_200(response)
        assertTemplateUsed(response, "upload-menu.html")
        assert response.context["school"] == school

    @patch("school_menu.views.import_menu")
    def test_post_with_valid_data(self, mock_import_menu):
        school = SchoolFactory()
        data = {
            "file": SimpleUploadedFile(
                "test_menu.xlsx",
                b"these are the file contents!",
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
            "season": School.Seasons.INVERNALE,
        }

        response = self.post("school_menu:upload_menu", school.pk, data=data)

        self.response_204(response)
        mock_import_menu.assert_called_once()

    def test_post_with_invalid_data(self):
        school = SchoolFactory()
        data = {
            "season": "WINTER",
        }

        response = self.post("school_menu:upload_menu", school.pk, data=data)

        self.response_200(response)
        assertTemplateUsed(response, "upload-menu.html")
        assert "form" in response.context
        assert "file" in response.context["form"].errors


class CreateWeeklyMenuView(TestCase):
    def test_get(self):
        user_factory = UserFactory  # noqa
        menu_types = [School.Types.SIMPLE, School.Types.DETAILED]
        for index, menu_type in enumerate(menu_types):
            user = self.make_user(index)
            school = SchoolFactory(menu_type=menu_type, user=user)

            with self.login(user):
                response = self.get("school_menu:create_weekly_menu", school.pk, 1, 1)

            self.response_200(response)
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
        school = SchoolFactory(user=user, menu_type=School.Types.SIMPLE)
        SimpleMealFactory.create_batch(5, school=school)

        with self.login(user):
            response = self.get("school_menu:create_weekly_menu", school.pk, 1, 1)

        self.response_200(response)
        assertTemplateUsed(response, "create-weekly-menu.html")
        assert response.context["school"] == school
        assert response.context["week"] == 1
        assert response.context["season"] == 1
        assert SimpleMeal.objects.filter(school=school).count() == 5
