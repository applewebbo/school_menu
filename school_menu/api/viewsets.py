from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import viewsets

from school_menu.models import School
from school_menu.serializers import SchoolMenuSerializer, SchoolSerializer


class SchoolViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for published schools list."""

    queryset = School.objects.filter(is_published=True).order_by("name", "city")
    serializer_class = SchoolSerializer
    lookup_field = "slug"

    @method_decorator(cache_page(86400, key_prefix="api_v1_schools"))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class MenuViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for school menus."""

    queryset = School.objects.all()
    serializer_class = SchoolMenuSerializer
    lookup_field = "slug"

    @method_decorator(cache_page(86400, key_prefix="api_v1_menu"))
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
