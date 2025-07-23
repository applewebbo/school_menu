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
        "toggle-daily-notification/",
        views.toggle_daily_notification,
        name="toggle_daily_notification",
    ),
    path(
        "buttons/<int:pk>/", views.notifications_buttons, name="notifications_buttons"
    ),
    path("change-school/<int:pk>/", views.change_school, name="change_school"),
]
