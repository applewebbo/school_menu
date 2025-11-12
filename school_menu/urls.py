from django.urls import path
from django.views.generic import TemplateView

from . import views

app_name = "school_menu"

urlpatterns = [
    path("", views.index, name="index"),
    path("settings/<int:pk>/", views.settings_view, name="settings"),
    path("school_list", views.school_list, name="school_list"),
    path(
        "get-menu/<int:school_id>/<int:week>/<int:day>/<str:meal_type>/",
        views.get_menu,
        name="get_menu",
    ),
    path("info", TemplateView.as_view(template_name="pages/info.html"), name="info"),
    path(
        "privacy",
        TemplateView.as_view(template_name="pages/privacy.html"),
        name="privacy",
    ),
    path("help", TemplateView.as_view(template_name="pages/help.html"), name="help"),
    path("json/schools/", views.get_schools_json_list, name="get_schools_json_list"),
    path(
        "json/menu/<slug:slug>/",
        views.get_school_json_menu,
        name="get_school_json_menu",
    ),
    path("menu/<slug:slug>/", views.school_menu, name="school_menu"),
    path(
        "menu/<int:school_id>/<int:week>/<int:season>/<str:meal_type>/",
        views.create_weekly_menu,
        name="create_weekly_menu",
    ),
    path(
        "export/<int:school_id>/<int:season>/<str:meal_type>/",
        views.export_menu,
        name="export_menu",
    ),
]

htmx_urlpatterns = [
    path("school/", views.school_view, name="school_view"),
    path("school/create/", views.school_create, name="school_create"),
    path("school/update/", views.school_update, name="school_update"),
    path("school/delete/", views.school_delete, name="school_delete"),
    path(
        "menu/<int:school_id>/<str:meal_type>/upload/",
        views.upload_menu,
        name="upload_menu",
    ),
    path(
        "menu/<int:school_id>/<str:meal_type>/annual/upload/",
        views.upload_annual_menu,
        name="upload_annual_menu",
    ),
    path("settings/<int:pk>/menu/", views.menu_settings_partial, name="menu_settings"),
    path("settings/school/", views.school_settings_partial, name="school_settings"),
    path("search-schools/", views.search_schools, name="search_schools"),
    path(
        "export-modal/<int:school_id>/<str:meal_type>/",
        views.export_modal_view,
        name="export_modal",
    ),
    path("report-count/", views.menu_report_count, name="menu_report_count"),
]

urlpatterns += htmx_urlpatterns
