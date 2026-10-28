from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from school_menu.models import AnnualMeal, DetailedMeal, School, SimpleMeal


class SchoolSitemap(Sitemap):
    """Published school menu pages: the highest-value, most numerous public URLs (#271)."""

    changefreq = "daily"
    priority = 0.8

    def items(self):
        # Excludes pages with no actual menu content (empty/test schools), which
        # Google AdSense flags as "low value content" (#331). A mirroring school
        # (mirror_from) shows another school's meals, so its own emptiness isn't
        # what matters — resolve to the effective school via get_display_school().
        published = (
            School.objects.filter(is_published=True)
            .select_related("mirror_from")
            .order_by("slug")
        )
        detailed_ids = set(DetailedMeal.objects.values_list("school_id", flat=True))
        simple_ids = set(SimpleMeal.objects.values_list("school_id", flat=True))
        annual_ids = set(
            AnnualMeal.objects.filter(is_active=True).values_list(
                "school_id", flat=True
            )
        )

        def has_meals(school):
            effective = school.get_display_school()
            if effective.annual_menu:
                return effective.id in annual_ids
            if effective.menu_type == School.Types.SIMPLE:
                return effective.id in simple_ids
            return effective.id in detailed_ids

        return [school for school in published if has_meals(school)]

    def location(self, item):
        return item.get_absolute_url()


class StaticViewSitemap(Sitemap):
    """Low-churn public pages that don't need a School instance (#271)."""

    changefreq = "weekly"
    priority = 0.5

    def items(self):
        return ["school_menu:index", "school_menu:school_list", "school_menu:info"]

    def location(self, item):
        return reverse(item)


sitemaps = {
    "schools": SchoolSitemap,
    "static": StaticViewSitemap,
}
