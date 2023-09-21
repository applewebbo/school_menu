from import_export import resources

from .models import Meal


class MealResource(resources.ModelResource):
    class Meta:
        model = Meal
