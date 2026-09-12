import pytest

from school_menu.test import TestCase
from tests.school_menu.factories import SchoolFactory

pytestmark = pytest.mark.django_db


class SitemapView(TestCase):
    def test_get_returns_xml(self):
        response = self.get("django.contrib.sitemaps.views.sitemap")

        self.response_200(response)
        assert response["Content-Type"] == "application/xml"

    def test_published_school_is_listed(self):
        school = SchoolFactory(is_published=True)
        response = self.get("django.contrib.sitemaps.views.sitemap")

        self.assertContains(response, school.get_absolute_url())

    def test_unpublished_school_is_not_listed(self):
        school = SchoolFactory(is_published=False)
        response = self.get("django.contrib.sitemaps.views.sitemap")

        self.assertNotContains(response, school.get_absolute_url())

    def test_static_pages_are_listed(self):
        response = self.get("django.contrib.sitemaps.views.sitemap")

        self.assertContains(response, self.reverse("school_menu:index"))
        self.assertContains(response, self.reverse("school_menu:school_list"))
        self.assertContains(response, self.reverse("school_menu:info"))
