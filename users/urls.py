from django.urls import path

from . import views

app_name = "users"
urlpatterns = [
    path("delete/", views.user_delete, name="user_delete"),
]
