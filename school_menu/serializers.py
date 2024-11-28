from rest_framework import serializers

from .models import DetailedMeal, School, SimpleMeal


class DetailedMealSerializer(serializers.ModelSerializer):
    menu = serializers.SerializerMethodField()

    def get_menu(self, obj):
        return f"{obj.first_course}, {obj.second_course}, {obj.fruit}, {obj.side_dish}"

    class Meta:
        model = DetailedMeal
        fields = ["day", "menu", "snack"]


class SimpleMealSerializer(serializers.ModelSerializer):
    menu = serializers.SerializerMethodField()

    def get_menu(self, obj):
        return obj.menu.replace("\n", ", ").strip()

    class Meta:
        model = SimpleMeal
        fields = ["day", "menu", "snack"]


class SchoolSerializer(serializers.ModelSerializer):
    url = serializers.URLField(source="get_absolute_url", read_only=True)

    class Meta:
        model = School
        fields = ["name", "city", "url"]
