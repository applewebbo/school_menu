from django.urls import path
from django.views.generic import TemplateView

from . import views

app_name = "school_menu"

urlpatterns = [
    path("", views.index, name="index"),
    path("get-menu/<int:week>/<int:day>/<int:type>", views.get_menu, name="get_menu"),
    path("info", TemplateView.as_view(template_name="pages/info.html"), name="info"),
    path("json_menu", views.json_menu, name="json_menu"),
]
