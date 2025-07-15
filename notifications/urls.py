from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path(
        "settings/",
        views.notification_settings,
        name="notification_settings",
    ),
    path("save-anon-subscription/", views.save_subscription, name="save_subscription"),
    path(
        "delete-anon-subscription/",
        views.delete_subscription,
        name="delete_subscription",
    ),
    path("test-notification/", views.test_notification, name="test_notification"),
    path(
        "test-periodic-notifications/",
        views.test_periodic_notifications,
        name="test_periodic_notifications",
    ),
    path(
        "stop-periodic-notifications/",
        views.stop_periodic_notifications,
        name="stop_periodic_notifications",
    ),
    path(
        "buttons/<int:pk>/", views.notifications_buttons, name="notifications_buttons"
    ),
]
