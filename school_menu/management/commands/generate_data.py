import factory
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from school_menu.models import DetailedMeal, School, SimpleMeal
from tests.school_menu.factories import (
    DetailedMealFactory,
    SchoolFactory,
    SimpleMealFactory,
)
from tests.users.factories import UserFactory

NUMBER_OF_USERS = 30

User = get_user_model()


class Command(BaseCommand):
    help = "Generates dummy data for visual testing."

    @transaction.atomic
    @factory.Faker.override_default_locale("it_IT")
    def handle(self, *args, **kwargs):
        self.stdout.write("Deleting old data...")
        # deleting all user except superuser
        User.objects.exclude(is_superuser=True).delete()
        # deleting all school (except superuser) and cascading all meals
        superuser = User.objects.get(is_superuser=True)
        School.objects.exclude(user=superuser).delete()

        self.stdout.write("Creating new data...")
        # creating users with email=user_*@test.com and password=1234
        UserFactory.create_batch(NUMBER_OF_USERS)
        # creating schools
        for user in User.objects.exclude(is_superuser=True):
            SchoolFactory.create(user=user)
        # creating meals
        for school in School.objects.all():
            if school.menu_type == School.Types.SIMPLE:
                for season in SimpleMeal.Seasons.choices:
                    for week in SimpleMeal.Weeks.choices:
                        for day in SimpleMeal.Days.choices:
                            SimpleMealFactory.create(
                                school=school,
                                day=day[0],
                                week=week[0],
                                season=season[0],
                            )
            elif school.menu_type == School.Types.DETAILED:
                for season in DetailedMeal.Seasons.choices:
                    for week in DetailedMeal.Weeks.choices:
                        for day in DetailedMeal.Days.choices:
                            DetailedMealFactory.create(
                                school=school,
                                day=day[0],
                                week=week[0],
                                season=season[0],
                            )
