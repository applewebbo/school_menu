import factory
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from school_menu.models import DetailedMeal, School, SimpleMeal
from tests.school_menu.factories import SchoolFactory
from tests.users.factories import UserFactory

NUMBER_OF_USERS = 50

User = get_user_model()


class Command(BaseCommand):
    help = "Generates dummy data for visual testing."

    @transaction.atomic
    @factory.Faker.override_default_locale("it_IT")
    def handle(self, *args, **kwargs):
        self.stdout.write("Deleting old data...")
        # deleting all user except superuser
        User.objects.exclude(is_superuser=True).delete()
        # deleting all trips, notes, links, places
        models = [School, DetailedMeal, SimpleMeal]
        for model in models:
            model.objects.all().delete()

        self.stdout.write("Creating new data...")
        # creating users with email=user_*@test.com and password=1234
        UserFactory.create_batch(NUMBER_OF_USERS)
        # creating schools
        for user in User.objects.all():
            SchoolFactory.create(user=user)
