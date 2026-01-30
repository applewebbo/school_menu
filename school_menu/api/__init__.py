from rest_framework.routers import DefaultRouter

from .viewsets import MenuViewSet, SchoolViewSet

router = DefaultRouter()
router.register(r"schools", SchoolViewSet, basename="school")
router.register(r"menu", MenuViewSet, basename="menu")
