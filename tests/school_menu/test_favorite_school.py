import time_machine

from school_menu.test import TestCase
from school_menu.views import FAVORITE_SCHOOL_COOKIE
from tests.school_menu.factories import SchoolFactory


class ToggleFavoriteSchoolView(TestCase):
    def test_get_not_allowed(self):
        school = SchoolFactory()
        response = self.get("school_menu:toggle_favorite_school", slug=school.slug)

        self.response_405(response)

    def test_anonymous_post_sets_cookie(self):
        school = SchoolFactory()
        response = self.post("school_menu:toggle_favorite_school", slug=school.slug)

        self.response_200(response)
        assert response.context["is_favorite"] is True
        assert response.cookies[FAVORITE_SCHOOL_COOKIE].value == school.slug

    def test_anonymous_post_again_clears_cookie(self):
        school = SchoolFactory()
        self.client.cookies[FAVORITE_SCHOOL_COOKIE] = school.slug

        response = self.post("school_menu:toggle_favorite_school", slug=school.slug)

        self.response_200(response)
        assert response.context["is_favorite"] is False
        assert response.cookies[FAVORITE_SCHOOL_COOKIE].value == ""

    def test_anonymous_post_replaces_previous_cookie(self):
        old_school = SchoolFactory()
        new_school = SchoolFactory()
        self.client.cookies[FAVORITE_SCHOOL_COOKIE] = old_school.slug

        response = self.post("school_menu:toggle_favorite_school", slug=new_school.slug)

        self.response_200(response)
        assert response.cookies[FAVORITE_SCHOOL_COOKIE].value == new_school.slug

    def test_authenticated_post_sets_favorite(self):
        user = self.make_user()
        other_school = SchoolFactory()

        with self.login(user):
            response = self.post(
                "school_menu:toggle_favorite_school", slug=other_school.slug
            )

        self.response_200(response)
        user.refresh_from_db()
        assert user.favorite_school == other_school
        assert response.context["is_favorite"] is True

    def test_authenticated_post_again_clears_favorite(self):
        user = self.make_user()
        other_school = SchoolFactory()
        user.favorite_school = other_school
        user.save()

        with self.login(user):
            response = self.post(
                "school_menu:toggle_favorite_school", slug=other_school.slug
            )

        self.response_200(response)
        user.refresh_from_db()
        assert user.favorite_school is None
        assert response.context["is_favorite"] is False

    def test_authenticated_post_replaces_previous_favorite(self):
        user = self.make_user()
        old_favorite = SchoolFactory()
        new_favorite = SchoolFactory()
        user.favorite_school = old_favorite
        user.save()

        with self.login(user):
            response = self.post(
                "school_menu:toggle_favorite_school", slug=new_favorite.slug
            )

        self.response_200(response)
        user.refresh_from_db()
        assert user.favorite_school == new_favorite

    def test_authenticated_post_on_own_school_forbidden(self):
        user = self.make_user()
        own_school = SchoolFactory(user=user)

        with self.login(user):
            response = self.post(
                "school_menu:toggle_favorite_school", slug=own_school.slug
            )

        self.response_403(response)

    def test_unknown_slug_returns_404(self):
        response = self.post("school_menu:toggle_favorite_school", slug="nope")

        self.response_404(response)


class SwitchHomeSchoolView(TestCase):
    def test_anonymous_redirected_to_login(self):
        response = self.get("school_menu:switch_home_school", target="favorite")

        self.response_302(response)

    def test_no_own_school_returns_404(self):
        user = self.make_user()

        with self.login(user):
            response = self.get("school_menu:switch_home_school", target="favorite")

        self.response_404(response)

    def test_target_favorite_without_favorite_set_returns_404(self):
        user = self.make_user()
        SchoolFactory(user=user)

        with self.login(user):
            response = self.get("school_menu:switch_home_school", target="favorite")

        self.response_404(response)

    def test_target_favorite_shows_favorite_school(self):
        user = self.make_user()
        SchoolFactory(user=user)
        favorite = SchoolFactory()
        user.favorite_school = favorite
        user.save()

        with self.login(user):
            response = self.get("school_menu:switch_home_school", target="favorite")

        self.response_200(response)
        assert response.context["school"] == favorite
        assert response.context["home_switch_target"] == "own"
        assert response.context["can_favorite"] is True
        assert response.context["is_favorite"] is True

    def test_target_own_shows_own_school(self):
        user = self.make_user()
        own_school = SchoolFactory(user=user)
        favorite = SchoolFactory()
        user.favorite_school = favorite
        user.save()

        with self.login(user):
            response = self.get("school_menu:switch_home_school", target="own")

        self.response_200(response)
        assert response.context["school"] == own_school
        assert response.context["home_switch_target"] == "favorite"
        assert response.context["can_favorite"] is False


class IndexFavoriteContext(TestCase):
    def test_authenticated_without_favorite_has_no_switch(self):
        user = self.make_user()
        SchoolFactory(user=user)

        with self.login(user):
            response = self.get("school_menu:index")

        self.response_200(response)
        assert response.context["show_switch"] is False
        assert response.context["show_school_header"] is False

    def test_authenticated_with_favorite_shows_switch_to_favorite(self):
        user = self.make_user()
        SchoolFactory(user=user)
        favorite = SchoolFactory()
        user.favorite_school = favorite
        user.save()

        with self.login(user):
            response = self.get("school_menu:index")

        self.response_200(response)
        assert response.context["show_switch"] is True
        assert response.context["home_switch_target"] == "favorite"
        assert response.context["show_school_header"] is True

    def test_anonymous_without_cookie_shows_welcome_page(self):
        response = self.get("school_menu:index")

        self.response_200(response)
        assert "school" not in response.context

    def test_anonymous_with_cookie_shows_favorite_school_menu(self):
        school = SchoolFactory()
        self.client.cookies[FAVORITE_SCHOOL_COOKIE] = school.slug

        response = self.get("school_menu:index")

        self.response_200(response)
        assert response.context["school"] == school
        assert response.context["can_favorite"] is True
        assert response.context["is_favorite"] is True
        assert response.context["show_switch"] is False

    def test_anonymous_with_stale_cookie_falls_back_and_clears_cookie(self):
        self.client.cookies[FAVORITE_SCHOOL_COOKIE] = "does-not-exist"

        response = self.get("school_menu:index")

        self.response_200(response)
        assert "school" not in response.context
        assert response.cookies[FAVORITE_SCHOOL_COOKIE].value == ""

    @time_machine.travel("2025-08-20")
    def test_anonymous_with_favorite_not_in_session(self):
        school = SchoolFactory(start_month=9, start_day=15, end_month=6, end_day=10)
        self.client.cookies[FAVORITE_SCHOOL_COOKIE] = school.slug

        response = self.get("school_menu:index")

        self.response_200(response)
        assert response.context["not_in_session"] is True
        assert response.context["school"] == school

    def test_anonymous_with_unpublished_favorite_falls_back(self):
        school = SchoolFactory(is_published=False)
        self.client.cookies[FAVORITE_SCHOOL_COOKIE] = school.slug

        response = self.get("school_menu:index")

        self.response_200(response)
        assert "school" not in response.context

    def test_anonymous_favorite_school_deleted_falls_back_without_error(self):
        school = SchoolFactory()
        self.client.cookies[FAVORITE_SCHOOL_COOKIE] = school.slug
        school.delete()

        response = self.get("school_menu:index")

        self.response_200(response)
        assert "school" not in response.context
        assert response.cookies[FAVORITE_SCHOOL_COOKIE].value == ""

    def test_authenticated_favorite_school_deleted_home_unaffected(self):
        user = self.make_user()
        SchoolFactory(user=user)
        favorite = SchoolFactory()
        user.favorite_school = favorite
        user.save()
        favorite.delete()

        with self.login(user):
            response = self.get("school_menu:index")

        self.response_200(response)
        user.refresh_from_db()
        assert user.favorite_school is None
        assert response.context["show_switch"] is False


class SchoolMenuFavoriteContext(TestCase):
    def test_anonymous_can_favorite_any_school(self):
        school = SchoolFactory()
        response = self.get("school_menu:school_menu", slug=school.slug)

        self.response_200(response)
        assert response.context["can_favorite"] is True
        assert response.context["is_favorite"] is False

    def test_authenticated_cannot_favorite_own_school(self):
        user = self.make_user()
        school = SchoolFactory(user=user)

        with self.login(user):
            response = self.get("school_menu:school_menu", slug=school.slug)

        self.response_200(response)
        assert response.context["can_favorite"] is False

    def test_authenticated_can_favorite_other_school(self):
        user = self.make_user()
        SchoolFactory(user=user)
        other_school = SchoolFactory()

        with self.login(user):
            response = self.get("school_menu:school_menu", slug=other_school.slug)

        self.response_200(response)
        assert response.context["can_favorite"] is True
        assert response.context["is_favorite"] is False


class GetMenuFavoriteContext(TestCase):
    def test_without_home_param_no_switch_but_heart_present(self):
        school = SchoolFactory()

        response = self.get("school_menu:get_menu", school.pk, 1, 1, "S")

        self.response_200(response)
        assert response.context["can_favorite"] is True
        assert "show_switch" not in response.context

    def test_with_home_param_carries_switch_state(self):
        user = self.make_user()
        SchoolFactory(user=user)
        favorite = SchoolFactory()
        user.favorite_school = favorite
        user.save()

        with self.login(user):
            response = self.get(
                f"{self.reverse('school_menu:get_menu', favorite.pk, 1, 1, 'S')}?home=1"
            )

        self.response_200(response)
        assert response.context["home"] is True
        assert response.context["show_switch"] is True
        assert response.context["home_switch_target"] == "own"
