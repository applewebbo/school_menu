from django.urls import reverse
from pytest_django.asserts import assertTemplateUsed

from school_menu.releases import RELEASES
from school_menu.test import TestCase


class ReleasesPageTest(TestCase):
    def test_page_renders(self):
        response = self.get("school_menu:releases")
        self.response_200(response)
        assertTemplateUsed(response, "pages/releases.html")

    def test_context_carries_the_release_list(self):
        response = self.get("school_menu:releases")
        assert response.context["releases"] == RELEASES

    def test_footer_version_links_to_the_page(self):
        response = self.get("school_menu:index")
        assert reverse("school_menu:releases") in response.content.decode()


class ReleasesDataTest(TestCase):
    def test_every_entry_is_well_formed(self):
        for entry in RELEASES:
            assert entry["version"]
            assert not entry["version"].startswith("v")
            assert 2 <= len(entry["notes"]) <= 4
            assert all(note.strip() for note in entry["notes"])

    def test_entries_are_ordered_newest_first(self):
        dates = [entry["date"] for entry in RELEASES]
        assert dates == sorted(dates, reverse=True)
