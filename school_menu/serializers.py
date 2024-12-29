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
    url = serializers.URLField(source="get_json_url", read_only=True)

    class Meta:
        model = School
        fields = ["name", "city", "url"]
