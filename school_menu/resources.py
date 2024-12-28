from datetime import datetime

from import_export import resources
from import_export.fields import Field

from school_menu.utils import ChoicesWidget

from .models import AnnualMeal, DetailedMeal, Meal, SimpleMeal


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

    def before_import_row(self, row, **kwargs):
        # Convert Italian weekday names to numbers
        weekday_map = {
            "Lunedì": Meal.Days.LUNEDÌ,
            "Martedì": Meal.Days.MARTEDÌ,
            "Mercoledì": Meal.Days.MERCOLEDÌ,
            "Giovedì": Meal.Days.GIOVEDÌ,
            "Venerdì": Meal.Days.VENERDÌ,
        }

        if "giorno" in row:
            row["giorno"] = weekday_map.get(row["giorno"])

        # Check for existing meal with same week, day, school, season and type
        existing_meal = DetailedMeal.objects.filter(
            week=row.get("settimana"),
            day=row.get("giorno"),
            school=kwargs.get("school"),
            season=kwargs.get("season"),
            type=kwargs.get("type"),
        ).first()

        if existing_meal:
            # Set the id to force update instead of create
            row["id"] = existing_meal.id

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

    def before_import_row(self, row, **kwargs):
        # Convert Italian weekday names to numbers
        weekday_map = {
            "Lunedì": Meal.Days.LUNEDÌ,
            "Martedì": Meal.Days.MARTEDÌ,
            "Mercoledì": Meal.Days.MERCOLEDÌ,
            "Giovedì": Meal.Days.GIOVEDÌ,
            "Venerdì": Meal.Days.VENERDÌ,
        }

        if "giorno" in row:
            row["giorno"] = weekday_map.get(row["giorno"])

        # Check for existing meal with same week, day, school, season and type
        existing_meal = SimpleMeal.objects.filter(
            week=row.get("settimana"),
            day=row.get("giorno"),
            school=kwargs.get("school"),
            season=kwargs.get("season"),
            type=kwargs.get("type"),
        ).first()

        if existing_meal:
            # Set the id to force update instead of create
            row["id"] = existing_meal.id

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

        # Check for existing meal with same date and school
        existing_meal = AnnualMeal.objects.filter(
            date=row["date"],
            school=kwargs.get("school"),
            type=kwargs.get("type"),
        ).first()

        if existing_meal:
            # Set the id to force update instead of create
            row["id"] = existing_meal.id

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
            row.get("altro", ""),
        ]
        # Filter out empty items and join with newlines
        row["menu"] = "\n".join(item for item in menu_items if item)

        row["type"] = kwargs.get("type")

    def after_init_instance(self, instance, new, row, **kwargs):
        instance.school = kwargs.get("school")
        instance.type = kwargs.get("type")

    class Meta:
        model = AnnualMeal
        fields = ("id", "date", "menu", "day")


class AnnualMenuExportResource(resources.ModelResource):
    date = Field(attribute="date", column_name="data")
    giorno = Field(attribute="day")
    primo = Field()
    secondo = Field()
    contorno = Field()
    frutta = Field()
    altro = Field()

    def dehydrate_giorno(self, obj):
        weekday_map = {
            Meal.Days.LUNEDÌ: "Lunedì",
            Meal.Days.MARTEDÌ: "Martedì",
            Meal.Days.MERCOLEDÌ: "Mercoledì",
            Meal.Days.GIOVEDÌ: "Giovedì",
            Meal.Days.VENERDÌ: "Venerdì",
        }
        return weekday_map.get(obj.day, "")

    def dehydrate_primo(self, obj):
        return obj.menu.split("\n")[0] if obj.menu else ""

    def dehydrate_secondo(self, obj):
        return (
            obj.menu.split("\n")[1]
            if obj.menu and len(obj.menu.split("\n")) > 1
            else ""
        )

    def dehydrate_contorno(self, obj):
        return (
            obj.menu.split("\n")[2]
            if obj.menu and len(obj.menu.split("\n")) > 2
            else ""
        )

    def dehydrate_frutta(self, obj):
        return (
            obj.menu.split("\n")[3]
            if obj.menu and len(obj.menu.split("\n")) > 3
            else ""
        )

    def dehydrate_altro(self, obj):
        return (
            obj.menu.split("\n")[4]
            if obj.menu and len(obj.menu.split("\n")) > 4
            else ""
        )

    class Meta:
        model = AnnualMeal
        fields = ("date", "giorno", "primo", "secondo", "contorno", "frutta", "altro")
