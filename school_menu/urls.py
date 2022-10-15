from django.urls import path

from . import views

app_name = "school_menu"

urlpatterns = [
    path("", views.index, name="index"),
    path("get-menu/<int:week>/<int:day>", views.get_menu, name="get_menu"),
]
