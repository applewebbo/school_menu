from django.urls import path
from django.views.generic import TemplateView

from . import views

app_name = "school_menu"

urlpatterns = [
    path("", views.index, name="index"),
    path("settings/<int:pk>/", views.settings_view, name="settings"),
    path("<slug:slug>", views.school_menu, name="school_menu"),
    path("get-menu/<int:week>/<int:day>/<int:type>", views.get_menu, name="get_menu"),
    path("info", TemplateView.as_view(template_name="pages/info.html"), name="info"),
    path("json_menu", views.json_menu, name="json_menu"),
]

htmx_urlpatterns = [
    path("school/", views.school_view, name="school_view"),
    path("school/create/", views.school_create, name="school_create"),
    path("school/update/", views.school_update, name="school_update"),
    path("settings/create/", views.settings_create, name="settings_create"),
    path("settings/update/", views.settings_update, name="settings_update"),
]

urlpatterns += htmx_urlpatterns
