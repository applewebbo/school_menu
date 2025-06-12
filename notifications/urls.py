from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path(
        "anonymous-notification-settings/",
        views.notification_settings,
        name="notification_settings",
    ),
    path("save-anon-subscription/", views.save_subscription, name="save_subscription"),
]
