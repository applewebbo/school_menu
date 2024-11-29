from django.urls import path

from . import views

app_name = "contacts"

urlpatterns = [
    path("", views.contact, name="contact"),
    path("menu/<int:school_id>/report/", views.menu_report, name="menu_report"),
]

htmx_urlpatterns = []

urlpatterns += htmx_urlpatterns
