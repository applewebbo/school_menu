from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from school_menu.models import School


class SchoolSitemap(Sitemap):
    """Published school menu pages: the highest-value, most numerous public URLs (#271)."""

    changefreq = "daily"
    priority = 0.8

    def items(self):
        return School.objects.filter(is_published=True).only("slug").order_by("slug")

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
