from import_export import resources

from .models import DetailedMeal


class DetailedMealResource(resources.ModelResource):
    class Meta:
        model = DetailedMeal
