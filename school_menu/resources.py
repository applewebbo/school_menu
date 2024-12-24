from datetime import datetime

from import_export import resources
from import_export.fields import Field

from school_menu.utils import ChoicesWidget

from .models import AnnualMeal, DetailedMeal, SimpleMeal


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
        instance.type = kwargs.get("type")

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
        instance.type = kwargs.get("type")

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


class DetailedMealExportResource(resources.ModelResource):
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
            "week",
            "day",
            "first_course",
            "second_course",
            "side_dish",
            "fruit",
            "snack",
        )


class SimpleMealExportResource(resources.ModelResource):
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
            "week",
            "day",
            "menu",
            "morning_snack",
            "afternoon_snack",
        )


class AnnualMenuResource(resources.ModelResource):
    date = Field(attribute="date")
    menu = Field(attribute="menu")
    day = Field(attribute="day")

    def before_import_row(self, row, **kwargs):
        # Skip 'giorno' column and get date from 'data'
        date_str = row.get("data")
        if date_str:
            date_obj = datetime.strptime(date_str, "%d/%m/%Y")
            row["date"] = date_obj.date()
        # Get weekday as integer (0-6) and add 1 to match Meal.Days values (1-5)
        weekday = date_obj.weekday() + 1
        # Only assign if it's a weekday (1-5)
        if 1 <= weekday <= 5:
            row["day"] = weekday

        # Join all menu fields with newlines
        menu_items = [
            row.get("primo", ""),
            row.get("secondo", ""),
            row.get("contorno", ""),
            row.get("frutta", ""),
            row.get("pane", ""),
        ]
        # Filter out empty items and join with newlines
        row["menu"] = "\n".join(item for item in menu_items if item)

    def after_init_instance(self, instance, new, row, **kwargs):
        instance.school = kwargs.get("school")

    class Meta:
        model = AnnualMeal
        fields = ("id", "date", "menu", "day")


class AnnualMenuExportResource(resources.ModelResource):
    date = Field(attribute="date")
    menu = Field(attribute="menu")

    def before_import_row(self, row, **kwargs):
        # Skip 'giorno' column and get date from 'data'
        date_str = row.get("data")
        if date_str:
            date_obj = datetime.strptime(date_str, "%d/%m/%Y")
            row["date"] = date_obj.date()

        # Join all menu fields with newlines
        menu_items = [
            row.get("primo", ""),
            row.get("secondo", ""),
            row.get("contorno", ""),
            row.get("frutta", ""),
            row.get("altro", ""),
        ]
        # Filter out empty items and join with newlines
        row["menu"] = "\n".join(item for item in menu_items if item)

    def after_init_instance(self, instance, new, row, **kwargs):
        instance.school = kwargs.get("school")

    class Meta:
        model = AnnualMeal
        fields = ("date", "menu")
