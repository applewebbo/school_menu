from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from tablib import Dataset

from school_menu.models import DetailedMeal, School
from school_menu.resources import DetailedMealResource
from school_menu.utils import validate_dataset
from tests.school_menu.factories import SchoolFactory

User = get_user_model()


class Command(BaseCommand):
    help = "Import meals from CSV files"

    def handle(self, *args, **kwargs):
        # adding back superuser school
        self.stdout.write("Adding back superuser data...")
        superuser = User.objects.get(is_superuser=True)
        if not School.objects.filter(user=superuser).exists():
            school = SchoolFactory.create(
                user=superuser,
                name="Convitto Carlo Alberto",
                city="Novara",
                menu_type=School.Types.DETAILED,
                no_gluten=True,
                no_lactose=True,
                vegetarian=True,
                special=False,
            )
        else:
            school = School.objects.get(user=superuser)
            school.name = "Convitto Carlo Alberto"
            school.city = "Novara"
            school.menu_type = School.Types.DETAILED
            school.no_gluten = True
            school.no_lactose = True
            school.vegetarian = True
            school.special = False
            school.save()

        seasons = {
            "menu_estivo": DetailedMeal.Seasons.ESTIVO,
            "menu_invernale": DetailedMeal.Seasons.INVERNALE,
        }
        resource = DetailedMealResource()
        types = {
            "STANDARD": DetailedMeal.Types.STANDARD,
            "NO_GLUTEN": DetailedMeal.Types.GLUTEN_FREE,
            "NO_LACTOSE": DetailedMeal.Types.LACTOSE_FREE,
            "VEGETARIAN": DetailedMeal.Types.VEGETARIAN,
        }
        for folder, meal_type in types.items():
            for file_season, season in seasons.items():
                with open(
                    f"data/carlo_alberto/{folder}/{file_season}.csv",
                    encoding="utf-8",
                ) as f:
                    dataset = Dataset()
                    dataset.load(f.read(), format="csv")
                    validates, message = validate_dataset(dataset, school.menu_type)
                    result = resource.import_data(
                        dataset,
                        dry_run=True,
                        school=school,
                        season=season,
                        type=meal_type,
                    )

                    if validates:
                        if not result.has_errors():
                            DetailedMeal.objects.filter(
                                school=school, season=season, type=meal_type
                            ).delete()
                            result = resource.import_data(
                                dataset,
                                dry_run=False,
                                school=school,
                                season=season,
                                type=meal_type,
                            )
                            self.stdout.write(f"Importing {file_season} [{folder}]...")
                        else:
                            self.stdout.write(
                                self.style.ERROR(
                                    f"Import failed after validation for {file_season} [{folder}]: something wrong has happened.."
                                )
                            )
                    else:
                        self.stdout.write(
                            self.style.ERROR(
                                f"Validation failed for {file_season} [{folder}]: {message}"
                            )
                        )
