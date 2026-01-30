from rest_framework import serializers

from .models import AnnualMeal, DetailedMeal, School, SimpleMeal


class DetailedMealSerializer(serializers.ModelSerializer):
    menu = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()

    def get_menu(self, obj):
        """Return a string with only items different from - or empty"""
        menu_items = [obj.first_course, obj.second_course, obj.fruit, obj.side_dish]
        return ", ".join(item for item in menu_items if item != "-" and item.strip())

    def get_type(self, obj):
        return obj.get_type_display()

    class Meta:
        model = DetailedMeal
        fields = ["day", "menu", "snack", "type"]


class SimpleMealSerializer(serializers.ModelSerializer):
    menu = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()

    def get_menu(self, obj):
        return obj.menu.replace("\n", ", ").replace("\r", " ").strip()

    def get_type(self, obj):
        return obj.get_type_display()

    class Meta:
        model = SimpleMeal
        fields = ["day", "morning_snack", "menu", "afternoon_snack", "type"]


class AnnualMealSerializer(serializers.ModelSerializer):
    menu = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()

    def get_menu(self, obj):
        return obj.menu.replace("\n", ", ").replace("\r", " ").strip()

    def get_type(self, obj):
        return obj.get_type_display()

    class Meta:
        model = AnnualMeal
        fields = ["day", "date", "menu", "snack", "type"]


class SchoolSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    def get_url(self, obj):
        """Return API v1 menu URL for this school."""
        from django.urls import reverse

        request = self.context.get("request")
        url = reverse("menu-detail", kwargs={"slug": obj.slug})

        if request is not None:
            return request.build_absolute_uri(url)
        return url

    class Meta:
        model = School
        fields = ["name", "city", "url"]


class SchoolMenuSerializer(serializers.ModelSerializer):
    """Serializer for school menu with weekly meals data."""

    menu = serializers.SerializerMethodField()
    types_menu = serializers.SerializerMethodField()

    def get_menu(self, obj):
        """Return menu data based on school menu type."""
        from school_menu.utils.calendar import (
            calculate_week,
            get_current_date,
            get_season,
        )
        from school_menu.utils.meals import get_meals, get_meals_for_annual_menu

        current_week, adjusted_day = get_current_date()
        adjusted_week = calculate_week(current_week, obj.week_bias)
        season = get_season(obj)

        if obj.annual_menu:
            weekly_meals, _ = get_meals_for_annual_menu(obj)
            return AnnualMealSerializer(weekly_meals, many=True).data

        weekly_meals, _ = get_meals(
            school=obj, week=adjusted_week, season=season, day=adjusted_day
        )

        if obj.menu_type == School.Types.SIMPLE:
            return SimpleMealSerializer(weekly_meals, many=True).data

        return DetailedMealSerializer(weekly_meals, many=True).data

    def get_types_menu(self, obj):
        """Return alternative menu types configuration."""
        from school_menu.utils.calendar import (
            calculate_week,
            get_current_date,
            get_season,
        )
        from school_menu.utils.meals import build_types_menu, get_meals

        current_week, adjusted_day = get_current_date()
        adjusted_week = calculate_week(current_week, obj.week_bias)
        season = get_season(obj)
        weekly_meals, _ = get_meals(
            school=obj, week=adjusted_week, season=season, day=adjusted_day
        )

        return build_types_menu(weekly_meals, obj, adjusted_week, season)

    class Meta:
        model = School
        fields = ["name", "city", "menu", "types_menu"]
