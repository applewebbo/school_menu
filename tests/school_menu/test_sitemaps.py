import pytest

from school_menu.models import School
from school_menu.test import TestCase
from tests.school_menu.factories import (
    AnnualMealFactory,
    DetailedMealFactory,
    SchoolFactory,
    SimpleMealFactory,
)

pytestmark = pytest.mark.django_db


class SitemapView(TestCase):
    def test_get_returns_xml(self):
        response = self.get("django.contrib.sitemaps.views.sitemap")

        self.response_200(response)
        assert response["Content-Type"] == "application/xml"

    def test_published_school_with_detailed_meal_is_listed(self):
        school = SchoolFactory(is_published=True, menu_type=School.Types.DETAILED)
        DetailedMealFactory(school=school)
        response = self.get("django.contrib.sitemaps.views.sitemap")

        self.assertContains(response, school.get_absolute_url())

    def test_published_school_with_simple_meal_is_listed(self):
        school = SchoolFactory(is_published=True, menu_type=School.Types.SIMPLE)
        SimpleMealFactory(school=school)
        response = self.get("django.contrib.sitemaps.views.sitemap")

        self.assertContains(response, school.get_absolute_url())

    def test_published_school_with_annual_meal_is_listed(self):
        school = SchoolFactory(is_published=True, annual_menu=True)
        AnnualMealFactory(school=school)
        response = self.get("django.contrib.sitemaps.views.sitemap")

        self.assertContains(response, school.get_absolute_url())

    def test_published_school_with_no_meals_is_not_listed(self):
        school = SchoolFactory(is_published=True)
        response = self.get("django.contrib.sitemaps.views.sitemap")

        self.assertNotContains(response, school.get_absolute_url())

    def test_unpublished_school_is_not_listed(self):
        school = SchoolFactory(is_published=False)
        response = self.get("django.contrib.sitemaps.views.sitemap")

        self.assertNotContains(response, school.get_absolute_url())

    def test_mirroring_school_with_no_own_meals_is_listed_if_source_has_meals(self):
        source = SchoolFactory(is_published=True, menu_type=School.Types.DETAILED)
        DetailedMealFactory(school=source)
        mirror = SchoolFactory(is_published=True, mirror_from=source)
        response = self.get("django.contrib.sitemaps.views.sitemap")

        self.assertContains(response, mirror.get_absolute_url())

    def test_mirroring_school_is_not_listed_if_source_has_no_meals(self):
        source = SchoolFactory(is_published=True)
        mirror = SchoolFactory(is_published=True, mirror_from=source)
        response = self.get("django.contrib.sitemaps.views.sitemap")

        self.assertNotContains(response, mirror.get_absolute_url())

    def test_static_pages_are_listed(self):
        response = self.get("django.contrib.sitemaps.views.sitemap")

        self.assertContains(response, self.reverse("school_menu:index"))
        self.assertContains(response, self.reverse("school_menu:school_list"))
        self.assertContains(response, self.reverse("school_menu:info"))
