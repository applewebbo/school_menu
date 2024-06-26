from pytest_django.asserts import assertTemplateUsed

from school_menu.models import School
from school_menu.test import TestCase
from tests.school_menu.factories import (
    DetailedMealFactory,
    SchoolFactory,
    SimpleMealFactory,
)


class IndexView(TestCase):
    def test_get(self):
        response = self.get("school_menu:index")

        self.assert_http_200_ok(response)
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

        self.assert_http_200_ok(response)
        assert response.context["school"] == school

    def test_get_with_detailed_meal_setting(self):
        user = self.make_user()
        school = SchoolFactory(user=user, menu_type=School.Types.DETAILED)

        with self.login(user):
            response = self.get("school_menu:index")

        self.assert_http_200_ok(response)
        assert response.context["school"] == school


class SchoolMenuView(TestCase):
    def test_get(self):
        school = SchoolFactory()
        response = self.get("school_menu:school_menu", slug=school.slug)

        self.assert_http_200_ok(response)
        assertTemplateUsed(response, "school-menu.html")
        assert response.context["school"] == school

    def test_get_with_detailed_menu(self):
        school = SchoolFactory(menu_type=School.Types.SIMPLE)
        response = self.get("school_menu:school_menu", slug=school.slug)

        self.assert_http_200_ok(response)
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

        self.assert_http_200_ok(response)
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

        self.assert_http_200_ok(response)
        assert response.context["meal"] == meal
