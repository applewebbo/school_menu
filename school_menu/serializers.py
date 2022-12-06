from rest_framework import serializers

from .models import Meal


class MealSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meal
        fields = ["day", "first_course", "second_course", "fruit", "side_dish", "snack"]
