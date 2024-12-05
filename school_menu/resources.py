from import_export import resources
from import_export.fields import Field

from school_menu.utils import ChoicesWidget

from .models import DetailedMeal, SimpleMeal


class DetailedMealResource(resources.ModelResource):
    day = Field(
        attribute="day",
        column_name="giorno",
        widget=ChoicesWidget(DetailedMeal.Days.choices),
    )
    week = Field(attribute="week", column_name="settimana")
    first_course = Field(attribute="first_course", column_name="primo")
    second_course = Field(attribute="second_course", column_name="secondo")
    side_dish = Field(attribute="side_dish", column_name="contorno")
    fruit = Field(attribute="fruit", column_name="frutta")
    snack = Field(attribute="snack", column_name="spuntino")

    def after_init_instance(self, instance, new, row, **kwargs):
        instance.school = kwargs.get("school")
        instance.season = kwargs.get("season")

    class Meta:
        model = DetailedMeal
        fields = (
            "id",
            "week",
            "day",
            "first_course",
            "second_course",
            "side_dish",
            "fruit",
            "snack",
        )


class SimpleMealResource(resources.ModelResource):
    day = Field(
        attribute="day",
        column_name="giorno",
        widget=ChoicesWidget(SimpleMeal.Days.choices),
    )
    week = Field(attribute="week", column_name="settimana")
    menu = Field(attribute="menu", column_name="pranzo")
    morning_snack = Field(attribute="morning_snack", column_name="spuntino")
    afternoon_snack = Field(attribute="afternoon_snack", column_name="merenda")

    def after_init_instance(self, instance, new, row, **kwargs):
        instance.school = kwargs.get("school")
        instance.season = kwargs.get("season")

    class Meta:
        model = SimpleMeal
        fields = (
            "id",
            "week",
            "day",
            "menu",
            "morning_snack",
            "afternoon_snack",
        )
