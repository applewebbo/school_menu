from import_export import resources
from import_export.fields import Field

from .models import DetailedMeal, SimpleMeal


class DetailedMealResource(resources.ModelResource):
    # def init(self, school_id):
    #     self.school_id = school_id

    # def before_save_instance(self, instance, row, **kwargs):
    #     instance.school_id = self.school_id

    day = Field(attribute="get_day_display", column_name="giorno")
    week = Field(attribute="week", column_name="settimana")
    first_course = Field(attribute="first_course", column_name="primo")
    second_course = Field(attribute="second_course", column_name="secondo")
    side_dish = Field(attribute="side_dish", column_name="contorno")
    fruit = Field(attribute="fruit", column_name="frutta")
    snack = Field(attribute="snack", column_name="spuntino")

    class Meta:
        model = DetailedMeal
        fields = (
            "week",
            "day",
            "first_course",
            "second_course",
            "side_dish",
            "fruit",
            "snack",
        )


class SimpleMealResource(resources.ModelResource):
    day = Field(attribute="get_day_display", column_name="giorno")
    week = Field(attribute="week", column_name="settimana")
    menu = Field(attribute="menu", column_name="pranzo")
    snack = Field(attribute="snack", column_name="spuntino")

    class Meta:
        model = SimpleMeal
        fields = ("week", "day", "menu", "snack")
