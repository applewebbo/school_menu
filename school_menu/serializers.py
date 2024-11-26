from rest_framework import serializers

from .models import DetailedMeal, School


class DetailedMealSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetailedMeal
        fields = ["day", "first_course", "second_course", "fruit", "side_dish", "snack"]


class SchoolSerializer(serializers.ModelSerializer):
    url = serializers.URLField(source="get_absolute_url", read_only=True)

    class Meta:
        model = School
        fields = ["name", "city", "url"]
