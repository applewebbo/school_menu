from django.urls import path

from . import views

app_name = "contacts"

urlpatterns = [
    path("", views.contact, name="contact"),
]

htmx_urlpatterns = []

urlpatterns += htmx_urlpatterns
