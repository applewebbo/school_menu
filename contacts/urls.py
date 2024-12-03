from django.urls import path

from . import views

app_name = "contacts"

urlpatterns = [
    path("", views.contact, name="contact"),
    path("menu/<int:school_id>/report/", views.menu_report, name="menu_report"),
]

htmx_urlpatterns = [
    path("reports/", views.report_list, name="report_list"),
    path("report/<int:report_id>/", views.report_detail, name="report_detail"),
    path(
        "reports/feedback/<int:report_id>/",
        views.report_feedback,
        name="report_feedback",
    ),
    path("reports/delete/<int:report_id>/", views.report_delete, name="report_delete"),
]

urlpatterns += htmx_urlpatterns
