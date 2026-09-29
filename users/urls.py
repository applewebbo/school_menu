from django.urls import path

from . import views

app_name = "users"
urlpatterns = [
    path("delete/", views.user_delete, name="user_delete"),
    path("newsletter/toggle/", views.toggle_newsletter, name="toggle_newsletter"),
    path(
        "newsletter/unsubscribe/<str:token>/",
        views.newsletter_unsubscribe,
        name="newsletter_unsubscribe",
    ),
]
