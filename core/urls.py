from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path
from django.views.generic.base import TemplateView

from school_menu.api import router as api_router
from school_menu.sitemaps import sitemaps
from school_menu.views import health_check
from users.views import (
    email_verification_sent,
    password_reset_done,
    password_reset_from_key_done,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    # Override three of allauth's own routes below (same name and path, so every
    # {% url %}/reverse() call is unaffected) with a redirect + toast instead of a
    # dedicated page: none of the three had anything to act on besides "go back" (#262).
    path(
        "accounts/confirm-email/",
        email_verification_sent,
        name="account_email_verification_sent",
    ),
    path(
        "accounts/password/reset/done/",
        password_reset_done,
        name="account_reset_password_done",
    ),
    path(
        "accounts/password/reset/key/done/",
        password_reset_from_key_done,
        name="account_reset_password_from_key_done",
    ),
    path("accounts/", include("allauth.urls")),
    path("health/", health_check, name="health_check"),
    path("api/v1/", include(api_router.urls)),
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    path("", include("school_menu.urls")),
    path("contacts/", include("contacts.urls")),
    path("users/", include("users.urls")),
    path("notifications/", include("notifications.urls")),
    path(
        "offline/",
        TemplateView.as_view(template_name="offline.html"),
        name="offline",
    ),
    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
    ),
    path("", include("pwa.urls")),
    path("webpush/", include("webpush.urls")),
    path("__reload__/", include("django_browser_reload.urls")),
]

if settings.DEBUG:
    urlpatterns += [path("silk/", include("silk.urls", namespace="silk"))]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
