from import_export import resources

from .models import DetailedMeal, SimpleMeal


class DetailedMealResource(resources.ModelResource):
    # def init(self, school_id):
    #     self.school_id = school_id

    # def before_save_instance(self, instance, row, **kwargs):
    #     instance.school_id = self.school_id

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
    class Meta:
        model = SimpleMeal
        fields = ("week", "day", "menu", "snack")
